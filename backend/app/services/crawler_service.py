from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import get_logger
from app.models import Element, Page, PageTransition, Project
from app.services.artifact_service import artifact_service
from app.services.billing_service import billing_service
from app.services.auth_session_service import auth_session_service
from playwright_utils.crawler import PlaywrightCrawler

logger = get_logger("CrawlerService")


class CrawlerService:
    """Orchestrate Playwright crawl and persist results."""

    async def run_crawl(self, db: AsyncSession, project_id: str, job_id: str) -> dict:
        result = await db.execute(
            select(Project)
            .options(selectinload(Project.credentials))
            .where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        project.crawl_status = "running"
        project.crawl_job_id = job_id
        await db.commit()

        crawl_dir = artifact_service.crawl_dir(project_id)
        login_fn = await auth_session_service.create_login_fn(project)

        crawler = PlaywrightCrawler(
            base_url=project.base_url,
            allowed_domains=project.allowed_domains_json or [],
            output_dir=crawl_dir,
            max_pages=settings.crawl_max_pages,
            max_depth=settings.crawl_max_depth,
            seed_urls=project.seed_urls_json or [project.base_url],
        )

        try:
            crawl_result = await crawler.crawl(login_fn=login_fn)
        except Exception as exc:
            project.crawl_status = "failed"
            await db.commit()
            logger.log("crawl_failed", str(exc), job_id=job_id, project_id=project_id)
            raise

        await db.execute(delete(PageTransition).where(PageTransition.project_id == project_id))
        page_ids = await db.execute(select(Page.id).where(Page.project_id == project_id))
        for row in page_ids.scalars():
            await db.execute(delete(Element).where(Element.page_id == row))
        await db.execute(delete(Page).where(Page.project_id == project_id))

        url_to_page_id: dict[str, str] = {}
        for page_data in crawl_result["pages"]:
            rel_screenshot = artifact_service.to_relative(page_data["screenshot_path"])
            page = Page(
                project_id=project_id,
                url=page_data["url"],
                title=page_data.get("title"),
                dom_hash=page_data.get("dom_hash"),
                screenshot_path=rel_screenshot,
            )
            db.add(page)
            await db.flush()
            url_to_page_id[page_data["url"]] = page.id

            for el_data in page_data.get("elements", []):
                element = Element(
                    page_id=page.id,
                    element_type=el_data["element_type"],
                    text_content=el_data.get("text_content"),
                    aria_label=el_data.get("aria_label"),
                    selector_primary=el_data["selector_primary"],
                    selector_fallbacks_json=el_data.get("selector_fallbacks", []),
                    dom_signature_json=el_data.get("dom_signature_json", {}),
                )
                db.add(element)

        project.crawl_status = "completed"
        project.crawl_pages_count = crawl_result["pages_count"]
        project.crawl_elements_count = crawl_result["elements_count"]
        if project.team_id:
            await billing_service.record_usage(
                db,
                project.team_id,
                "crawl_pages",
                quantity=crawl_result["pages_count"],
                project_id=project_id,
            )
        await db.commit()

        logger.log(
            "crawl_completed",
            f"Crawled {crawl_result['pages_count']} pages",
            job_id=job_id,
            project_id=project_id,
        )
        return crawl_result


crawler_service = CrawlerService()
