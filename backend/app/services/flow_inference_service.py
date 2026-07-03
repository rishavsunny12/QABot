from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models import Flow, FlowStep, Page

logger = get_logger("FlowInferenceService")


class FlowInferenceService:
    """Infer user flows from crawl data using heuristics."""

    async def infer_flows(self, db: AsyncSession, project_id: str) -> list[Flow]:

        await db.execute(delete(FlowStep).where(FlowStep.flow_id.in_(
            select(Flow.id).where(Flow.project_id == project_id)
        )))
        await db.execute(delete(Flow).where(Flow.project_id == project_id))
        await db.flush()

        pages_result = await db.execute(
            select(Page)
            .options(selectinload(Page.elements))
            .where(Page.project_id == project_id)
        )
        pages = pages_result.scalars().all()
        if not pages:
            return []

        flows: list[Flow] = []

        login_flow = self._detect_login_flow(project_id, pages)
        if login_flow:
            flows.append(await self._persist_flow(db, login_flow))

        dashboard_flow = self._detect_dashboard_flow(project_id, pages)
        if dashboard_flow:
            flows.append(await self._persist_flow(db, dashboard_flow))

        nav_flows = self._detect_navigation_flows(project_id, pages)
        for nav_flow in nav_flows[:3]:
            flows.append(await self._persist_flow(db, nav_flow))

        create_flow = self._detect_create_flow(project_id, pages)
        if create_flow:
            flows.append(await self._persist_flow(db, create_flow))

        logout_flow = self._detect_logout_flow(project_id, pages)
        if logout_flow:
            flows.append(await self._persist_flow(db, logout_flow))

        await db.commit()
        logger.log("flows_inferred", f"Inferred {len(flows)} flows", project_id=project_id)
        return flows

    async def _persist_flow(self, db: AsyncSession, flow_data: dict) -> Flow:
        flow = Flow(
            project_id=flow_data["project_id"],
            name=flow_data["name"],
            risk_level=flow_data.get("risk_level", "low"),
            confidence_score=flow_data.get("confidence_score", 0.7),
            requires_auth=flow_data.get("requires_auth", False),
            destructive=flow_data.get("destructive", False),
        )
        db.add(flow)
        await db.flush()

        for step_data in flow_data.get("steps", []):
            step = FlowStep(
                flow_id=flow.id,
                step_order=step_data["step_order"],
                action_type=step_data["action_type"],
                target_element_id=step_data.get("target_element_id"),
                expected_result_json=step_data.get("expected_result", {}),
            )
            db.add(step)
        await db.flush()
        return flow

    def _detect_login_flow(self, project_id: str, pages: list[Page]) -> dict | None:
        login_pages = [p for p in pages if any(k in (p.url or "").lower() for k in ("login", "signin", "auth"))]
        if not login_pages:
            login_pages = [p for p in pages if any(
                el.element_type in ("input",) for el in p.elements
            )]
        if not login_pages:
            return None

        page = login_pages[0]
        steps = [
            {
                "step_order": 1,
                "action_type": "navigate",
                "target_element_id": None,
                "expected_result": {"url": page.url, "url_pattern": page.url.split("/")[-1] or ".*"},
            }
        ]
        submit_el = next(
            (el for el in page.elements if el.element_type == "button" and "log" in (el.text_content or "").lower()),
            None,
        )
        if submit_el:
            steps.append(
                {
                    "step_order": 2,
                    "action_type": "click",
                    "target_element_id": submit_el.id,
                    "expected_result": {"transition": "authenticated"},
                }
            )

        return {
            "project_id": project_id,
            "name": "Login Flow",
            "risk_level": "low",
            "confidence_score": 0.85,
            "requires_auth": False,
            "destructive": False,
            "steps": steps,
        }

    def _detect_dashboard_flow(self, project_id: str, pages: list[Page]) -> dict | None:
        dashboard_pages = [
            p for p in pages
            if any(k in (p.title or "").lower() or k in p.url.lower() for k in ("dashboard", "home", "app"))
        ]
        if not dashboard_pages:
            dashboard_pages = pages[:1]
        page = dashboard_pages[0]
        heading = next((el for el in page.elements if el.element_type in ("h1", "h2")), None)

        steps = [
            {
                "step_order": 1,
                "action_type": "navigate",
                "target_element_id": None,
                "expected_result": {"url": page.url},
            }
        ]
        if heading:
            steps.append(
                {
                    "step_order": 2,
                    "action_type": "assert_visible",
                    "target_element_id": heading.id,
                    "expected_result": {"visible": True},
                }
            )

        return {
            "project_id": project_id,
            "name": "Dashboard Flow",
            "risk_level": "low",
            "confidence_score": 0.8,
            "requires_auth": True,
            "destructive": False,
            "steps": steps,
        }

    def _detect_navigation_flows(self, project_id: str, pages: list[Page]) -> list[dict]:
        flows = []
        for page in pages[:5]:
            nav_links = [el for el in page.elements if el.element_type == "a" and el.text_content]
            for link in nav_links[:2]:
                flows.append(
                    {
                        "project_id": project_id,
                        "name": f"Navigate to {link.text_content[:30]}",
                        "risk_level": "low",
                        "confidence_score": 0.65,
                        "requires_auth": False,
                        "destructive": False,
                        "steps": [
                            {
                                "step_order": 1,
                                "action_type": "navigate",
                                "target_element_id": None,
                                "expected_result": {"url": page.url},
                            },
                            {
                                "step_order": 2,
                                "action_type": "click",
                                "target_element_id": link.id,
                                "expected_result": {"transition": link.text_content},
                            },
                        ],
                    }
                )
        return flows

    def _detect_create_flow(self, project_id: str, pages: list[Page]) -> dict | None:
        for page in pages:
            create_btn = next(
                (
                    el
                    for el in page.elements
                    if el.element_type in ("button", "a")
                    and any(k in (el.text_content or "").lower() for k in ("create", "add", "new"))
                ),
                None,
            )
            if create_btn:
                return {
                    "project_id": project_id,
                    "name": "Create Item Flow",
                    "risk_level": "medium",
                    "confidence_score": 0.7,
                    "requires_auth": True,
                    "destructive": False,
                    "steps": [
                        {
                            "step_order": 1,
                            "action_type": "navigate",
                            "target_element_id": None,
                            "expected_result": {"url": page.url},
                        },
                        {
                            "step_order": 2,
                            "action_type": "click",
                            "target_element_id": create_btn.id,
                            "expected_result": {"transition": "form"},
                        },
                    ],
                }
        return None

    def _detect_logout_flow(self, project_id: str, pages: list[Page]) -> dict | None:
        for page in pages:
            logout_el = next(
                (
                    el
                    for el in page.elements
                    if any(k in (el.text_content or "").lower() for k in ("logout", "sign out", "log out"))
                ),
                None,
            )
            if logout_el:
                return {
                    "project_id": project_id,
                    "name": "Logout Flow",
                    "risk_level": "medium",
                    "confidence_score": 0.75,
                    "requires_auth": True,
                    "destructive": True,
                    "steps": [
                        {
                            "step_order": 1,
                            "action_type": "navigate",
                            "target_element_id": None,
                            "expected_result": {"url": page.url},
                        },
                        {
                            "step_order": 2,
                            "action_type": "click",
                            "target_element_id": logout_el.id,
                            "expected_result": {"transition": "logged_out"},
                        },
                    ],
                }
        return None


flow_inference_service = FlowInferenceService()
