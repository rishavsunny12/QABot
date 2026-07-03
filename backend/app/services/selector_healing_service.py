from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models import Element, GeneratedTest, HealingSuggestion, Page, TestRunResult
from app.services.ai_client import ai_client

logger = get_logger("SelectorHealingService")


class SelectorHealingService:
    """Propose selector healing alternatives without auto-applying."""

    async def suggest_healing(
        self,
        db: AsyncSession,
        result: TestRunResult,
        test: GeneratedTest,
    ) -> HealingSuggestion | None:
        failed_selector = self._extract_failed_selector(result.error_message or "")
        if not failed_selector:
            failed_selector = "unknown"

        alternatives = await self._find_alternatives(db, test.project_id, failed_selector)
        if not alternatives:
            return None

        best = alternatives[0]
        rationale = await self._build_rationale(failed_selector, best)

        suggestion = HealingSuggestion(
            generated_test_id=test.id,
            test_run_result_id=result.id,
            failed_selector=failed_selector,
            suggested_selector=best["selector"],
            confidence_score=best["score"],
            rationale=rationale,
            approved=None,
        )
        db.add(suggestion)
        await db.flush()
        logger.log("healing_suggested", f"Suggested selector: {best['selector']}", project_id=test.project_id)
        return suggestion

    def _extract_failed_selector(self, error: str) -> str:
        for marker in ('locator("', "locator('", 'getByRole(', 'getByTestId('):
            if marker in error:
                start = error.index(marker)
                return error[start : start + 120].split("\n")[0]
        return error[:120] if error else ""

    async def _find_alternatives(
        self, db: AsyncSession, project_id: str, failed_selector: str
    ) -> list[dict]:
        pages = (
            await db.execute(
                select(Page).options(selectinload(Page.elements)).where(Page.project_id == project_id)
            )
        ).scalars().all()

        candidates: list[dict] = []
        for page in pages:
            for element in page.elements:
                score = self._score_selector(failed_selector, element)
                if score > 0.3:
                    for sel in [element.selector_primary, *element.selector_fallbacks_json]:
                        candidates.append({"selector": sel, "score": score, "element_id": element.id})

        candidates.sort(key=lambda c: c["score"], reverse=True)
        seen: set[str] = set()
        unique: list[dict] = []
        for c in candidates:
            if c["selector"] not in seen:
                seen.add(c["selector"])
                unique.append(c)
        return unique[:5]

    def _score_selector(self, failed: str, element: Element) -> float:
        scores = []
        for text in [element.text_content, element.aria_label, element.selector_primary]:
            if text:
                scores.append(SequenceMatcher(None, failed.lower(), text.lower()).ratio())
        sig = element.dom_signature_json or {}
        if sig.get("role") and sig["role"] in failed.lower():
            scores.append(0.6)
        return max(scores) if scores else 0.0

    async def _build_rationale(self, failed: str, best: dict) -> str:
        if ai_client.enabled:
            system = "Return JSON with key rationale (string) explaining why the suggested selector is better."
            user = f"Failed: {failed}\nSuggested: {best['selector']}\nScore: {best['score']}"
            data = await ai_client.complete_json(system, user)
            if data.get("rationale"):
                return data["rationale"]
        return (
            f"Suggested selector '{best['selector']}' matched with confidence {best['score']:.2f} "
            f"based on role, label, and text similarity from crawl history."
        )

    async def approve(self, db: AsyncSession, suggestion_id: str) -> HealingSuggestion:
        suggestion = (
            await db.execute(select(HealingSuggestion).where(HealingSuggestion.id == suggestion_id))
        ).scalar_one()
        suggestion.approved = True

        test = (
            await db.execute(
                select(GeneratedTest).where(GeneratedTest.id == suggestion.generated_test_id)
            )
        ).scalar_one()
        test.version += 1

        from app.services.artifact_service import artifact_service

        spec_path = artifact_service.resolve_path(test.file_path)
        if spec_path.exists():
            content = spec_path.read_text(encoding="utf-8")
            content = content.replace(suggestion.failed_selector, suggestion.suggested_selector)
            spec_path.write_text(content, encoding="utf-8")

        await db.commit()
        return suggestion

    async def reject(self, db: AsyncSession, suggestion_id: str) -> HealingSuggestion:
        suggestion = (
            await db.execute(select(HealingSuggestion).where(HealingSuggestion.id == suggestion_id))
        ).scalar_one()
        suggestion.approved = False
        await db.commit()
        return suggestion


selector_healing_service = SelectorHealingService()
