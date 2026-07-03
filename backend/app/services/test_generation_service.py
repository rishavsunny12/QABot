
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models import Element, Flow, GeneratedTest, GeneratedTestStatus, Project
from app.services.ai_client import ai_client
from app.services.artifact_service import artifact_service
from playwright_utils.spec_generator import generate_spec_file, write_spec

logger = get_logger("TestGenerationService")


class TestGenerationService:
    """Generate Playwright tests from inferred flows."""

    async def generate_tests(
        self,
        db: AsyncSession,
        project_id: str,
        flow_ids: list[str] | None = None,
    ) -> list[GeneratedTest]:
        query = (
            select(Flow)
            .options(selectinload(Flow.steps))
            .where(Flow.project_id == project_id)
        )
        if flow_ids:
            query = query.where(Flow.id.in_(flow_ids))
        flows = (await db.execute(query)).scalars().all()

        project = (await db.execute(select(Project).where(Project.id == project_id))).scalar_one()
        tests_dir = artifact_service.tests_dir(project_id)
        generated: list[GeneratedTest] = []

        for flow in flows:
            steps, assertions = await self._build_steps(db, flow, project.base_url)
            ai_data = await self._ai_enhance(flow.name, steps)
            test_title = ai_data.get("test_title", f"Verify {flow.name}")
            extra_assertions = ai_data.get("assertions", [])

            spec_content = generate_spec_file(
                flow_name=flow.name,
                test_title=test_title,
                steps=steps,
                assertions=assertions + extra_assertions,
            )
            safe_name = "".join(c if c.isalnum() else "_" for c in flow.name.lower())
            file_path = tests_dir / f"{safe_name}_{flow.id[:8]}.spec.ts"
            write_spec(file_path, spec_content)
            rel_path = artifact_service.to_relative(file_path)

            test = GeneratedTest(
                project_id=project_id,
                flow_id=flow.id,
                name=test_title,
                file_path=rel_path,
                version=1,
                status=GeneratedTestStatus.READY.value,
            )
            db.add(test)
            generated.append(test)

        await db.commit()
        logger.log("tests_generated", f"Generated {len(generated)} tests", project_id=project_id)
        return generated

    async def _build_steps(
        self, db: AsyncSession, flow: Flow, base_url: str
    ) -> tuple[list[dict], list[dict]]:
        steps: list[dict] = []
        assertions: list[dict] = []

        for step in sorted(flow.steps, key=lambda s: s.step_order):
            if step.action_type == "navigate":
                url = step.expected_result_json.get("url", base_url)
                pattern = step.expected_result_json.get("url_pattern", ".*")
                steps.append(
                    {
                        "order": step.step_order,
                        "description": f"Navigate to {url}",
                        "action_type": "navigate",
                        "url": url,
                        "url_pattern": pattern.replace("/", "\\/"),
                    }
                )
            elif step.target_element_id:
                element = await db.get(Element, step.target_element_id)
                if not element:
                    continue
                selector = element.selector_primary
                if step.action_type == "click":
                    steps.append(
                        {
                            "order": step.step_order,
                            "description": f"Click {element.text_content or selector}",
                            "action_type": "click",
                            "selector": selector,
                        }
                    )
                elif step.action_type == "assert_visible":
                    assertions.append(
                        {
                            "description": f"Verify {element.text_content or 'element'} is visible",
                            "selector": selector,
                            "matcher": "toBeVisible",
                            "expected": "",
                        }
                    )
                elif step.action_type == "fill":
                    steps.append(
                        {
                            "order": step.step_order,
                            "description": f"Fill {element.text_content or selector}",
                            "action_type": "fill",
                            "selector": selector,
                            "value": "test-value",
                        }
                    )
        return steps, assertions

    async def _ai_enhance(self, flow_name: str, steps: list[dict]) -> dict:
        if not ai_client.enabled:
            return {"test_title": f"Verify {flow_name}", "assertions": []}

        system = (
            "You are a QA engineer. Return JSON with keys: test_title (string), "
            "assertions (array of {description, selector, matcher, expected}). "
            "Keep assertions minimal and practical."
        )
        user = f"Flow: {flow_name}\nSteps: {steps}"
        result = await ai_client.complete_json(system, user)
        return result or {"test_title": f"Verify {flow_name}", "assertions": []}

    async def export_test(self, db: AsyncSession, test_id: str) -> tuple[str, str]:
        test = (await db.execute(select(GeneratedTest).where(GeneratedTest.id == test_id))).scalar_one()
        abs_path = artifact_service.resolve_path(test.file_path)
        content = abs_path.read_text(encoding="utf-8")
        return test.name, content


test_generation_service = TestGenerationService()
