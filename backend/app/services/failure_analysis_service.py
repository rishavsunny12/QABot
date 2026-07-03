from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import GeneratedTest, Project, TestRunResult
from app.services.ai_client import ai_client
from app.services.billing_service import billing_service

logger = get_logger("FailureAnalysisService")

FAILURE_CATEGORIES = [
    "selector drift",
    "app bug",
    "flaky timing issue",
    "navigation mismatch",
    "auth/session issue",
    "backend/API issue",
    "environment issue",
]


class FailureAnalysisService:
    """Generate AI failure summaries after test failures."""

    async def analyze(
        self,
        db: AsyncSession,
        result: TestRunResult,
        test: GeneratedTest,
    ) -> str:
        if ai_client.enabled:
            summary = await self._ai_analyze(db, result, test)
            if summary:
                return summary
        return self._fallback_summary(result)

    async def _ai_analyze(
        self, db: AsyncSession, result: TestRunResult, test: GeneratedTest
    ) -> str:
        system = (
            "You are a QA failure analyst. Return JSON with keys: "
            "summary (string), root_cause (string), confidence (0-1 float), "
            "category (one of the failure categories), next_action (string)."
        )
        user = (
            f"Test: {test.name}\n"
            f"Error: {result.error_message}\n"
            f"Category hint: {result.failure_category}\n"
            f"Categories: {FAILURE_CATEGORIES}"
        )
        data = await ai_client.complete_json(system, user)
        if not data:
            return self._fallback_summary(result)

        project = (
            await db.execute(select(Project).where(Project.id == test.project_id))
        ).scalar_one_or_none()
        if project and project.team_id:
            await billing_service.record_usage(db, project.team_id, "ai_calls", project_id=test.project_id)

        result.failure_category = data.get("category", result.failure_category)
        return (
            f"{data.get('summary', 'Test failed')}\n\n"
            f"Root cause: {data.get('root_cause', 'Unknown')}\n"
            f"Confidence: {data.get('confidence', 0.5)}\n"
            f"Next action: {data.get('next_action', 'Review failure artifacts')}"
        )

    def _fallback_summary(self, result: TestRunResult) -> str:
        category = result.failure_category or "environment issue"
        return (
            f"Test failed with category: {category}.\n\n"
            f"Error: {(result.error_message or 'No error message')[:500]}\n\n"
            f"Next action: Review screenshot and trace artifacts, then update selectors or fix the app."
        )


failure_analysis_service = FailureAnalysisService()
