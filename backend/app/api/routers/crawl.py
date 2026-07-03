from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.access import authorize_project
from app.core.auth_deps import AuthenticatedUser, get_current_user
from app.core.database import get_db
from app.models import Flow, Page, PageTransition, TeamRole
from app.schemas import (
    CrawlStatusResponse,
    FlowGraphResponse,
    FlowResponse,
    FlowStepResponse,
    GraphEdge,
    GraphNode,
    PageResponse,
    ElementResponse,
)
from app.tasks.crawl_tasks import run_crawl_task

router = APIRouter(tags=["crawl"])


@router.post("/projects/{project_id}/crawl")
async def start_crawl(
    project_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await authorize_project(db, auth, project_id, TeamRole.MEMBER)

    task = run_crawl_task.delay(project_id)
    project.crawl_status = "queued"
    project.crawl_job_id = task.id
    await db.commit()
    return {"job_id": task.id, "status": "queued"}


@router.get("/projects/{project_id}/crawl-status", response_model=CrawlStatusResponse)
async def crawl_status(
    project_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await authorize_project(db, auth, project_id, TeamRole.VIEWER)
    return CrawlStatusResponse(
        status=project.crawl_status,
        job_id=project.crawl_job_id,
        pages_count=project.crawl_pages_count,
        elements_count=project.crawl_elements_count,
    )


@router.get("/projects/{project_id}/pages", response_model=list[PageResponse])
async def list_pages(
    project_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await authorize_project(db, auth, project_id, TeamRole.VIEWER)
    result = await db.execute(
        select(Page)
        .options(selectinload(Page.elements))
        .where(Page.project_id == project_id)
        .order_by(Page.discovered_at.desc())
    )
    pages = []
    for page in result.scalars().all():
        pages.append(
            PageResponse(
                id=page.id,
                project_id=page.project_id,
                url=page.url,
                title=page.title,
                screenshot_path=page.screenshot_path,
                discovered_at=page.discovered_at,
                elements=[
                    ElementResponse(
                        id=e.id,
                        page_id=e.page_id,
                        element_type=e.element_type,
                        text_content=e.text_content,
                        aria_label=e.aria_label,
                        selector_primary=e.selector_primary,
                        selector_fallbacks=e.selector_fallbacks_json or [],
                    )
                    for e in page.elements
                ],
            )
        )
    return pages


@router.get("/projects/{project_id}/flows", response_model=list[FlowResponse])
async def list_flows(
    project_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await authorize_project(db, auth, project_id, TeamRole.VIEWER)
    result = await db.execute(
        select(Flow)
        .options(selectinload(Flow.steps))
        .where(Flow.project_id == project_id)
        .order_by(Flow.confidence_score.desc())
    )
    return [
        FlowResponse(
            id=f.id,
            project_id=f.project_id,
            name=f.name,
            risk_level=f.risk_level,
            confidence_score=f.confidence_score,
            requires_auth=f.requires_auth,
            destructive=f.destructive,
            created_at=f.created_at,
            steps=[
                FlowStepResponse(
                    id=s.id,
                    step_order=s.step_order,
                    action_type=s.action_type,
                    target_element_id=s.target_element_id,
                    expected_result=s.expected_result_json or {},
                )
                for s in sorted(f.steps, key=lambda x: x.step_order)
            ],
        )
        for f in result.scalars().all()
    ]


@router.get("/projects/{project_id}/flow-graph", response_model=FlowGraphResponse)
async def flow_graph(
    project_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await authorize_project(db, auth, project_id, TeamRole.VIEWER)
    pages = (
        await db.execute(select(Page).where(Page.project_id == project_id))
    ).scalars().all()
    transitions = (
        await db.execute(select(PageTransition).where(PageTransition.project_id == project_id))
    ).scalars().all()
    flows = (
        await db.execute(
            select(Flow).options(selectinload(Flow.steps)).where(Flow.project_id == project_id)
        )
    ).scalars().all()

    nodes = [
        GraphNode(id=p.id, label=p.title or p.url.split("/")[-1] or p.url, url=p.url) for p in pages
    ]
    edges = [
        GraphEdge(id=t.id, source=t.from_page_id, target=t.to_page_id, label=t.action_type)
        for t in transitions
    ]

    if not edges and len(pages) > 1:
        for i in range(len(pages) - 1):
            edges.append(
                GraphEdge(
                    id=f"edge-{i}",
                    source=pages[i].id,
                    target=pages[i + 1].id,
                    label="link",
                )
            )

    flow_responses = [
        FlowResponse(
            id=f.id,
            project_id=f.project_id,
            name=f.name,
            risk_level=f.risk_level,
            confidence_score=f.confidence_score,
            requires_auth=f.requires_auth,
            destructive=f.destructive,
            created_at=f.created_at,
            steps=[
                FlowStepResponse(
                    id=s.id,
                    step_order=s.step_order,
                    action_type=s.action_type,
                    target_element_id=s.target_element_id,
                    expected_result=s.expected_result_json or {},
                )
                for s in sorted(f.steps, key=lambda x: x.step_order)
            ],
        )
        for f in flows
    ]

    return FlowGraphResponse(nodes=nodes, edges=edges, flows=flow_responses)
