from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import AuthenticatedUser, get_current_user
from app.core.database import get_db
from app.models import HealingSuggestion, TeamRole
from app.schemas import HealingSuggestionResponse
from app.services.access_service import access_service
from app.services.selector_healing_service import selector_healing_service

router = APIRouter(tags=["healing"])


@router.get("/results/{result_id}/healing-suggestions", response_model=list[HealingSuggestionResponse])
async def list_healing_suggestions(
    result_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await access_service.ensure_result_access(db, auth.user, result_id, TeamRole.VIEWER)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    result = (
        await db.execute(
            select(HealingSuggestion).where(HealingSuggestion.test_run_result_id == result_id)
        )
    ).scalars().all()
    return [
        HealingSuggestionResponse(
            id=s.id,
            generated_test_id=s.generated_test_id,
            failed_selector=s.failed_selector,
            suggested_selector=s.suggested_selector,
            confidence_score=s.confidence_score,
            rationale=s.rationale,
            approved=s.approved,
            created_at=s.created_at,
        )
        for s in result
    ]


async def _authorize_healing_action(db: AsyncSession, auth: AuthenticatedUser, suggestion_id: str):
    suggestion = (
        await db.execute(select(HealingSuggestion).where(HealingSuggestion.id == suggestion_id))
    ).scalar_one_or_none()
    if not suggestion or not suggestion.test_run_result_id:
        raise HTTPException(status_code=404, detail="Healing suggestion not found")
    try:
        await access_service.ensure_result_access(
            db, auth.user, suggestion.test_run_result_id, TeamRole.ADMIN
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return suggestion


@router.post("/healing-suggestions/{suggestion_id}/approve", response_model=HealingSuggestionResponse)
async def approve_healing(
    suggestion_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _authorize_healing_action(db, auth, suggestion_id)
    suggestion = await selector_healing_service.approve(db, suggestion_id)
    return HealingSuggestionResponse(
        id=suggestion.id,
        generated_test_id=suggestion.generated_test_id,
        failed_selector=suggestion.failed_selector,
        suggested_selector=suggestion.suggested_selector,
        confidence_score=suggestion.confidence_score,
        rationale=suggestion.rationale,
        approved=suggestion.approved,
        created_at=suggestion.created_at,
    )


@router.post("/healing-suggestions/{suggestion_id}/reject", response_model=HealingSuggestionResponse)
async def reject_healing(
    suggestion_id: str,
    auth: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _authorize_healing_action(db, auth, suggestion_id)
    suggestion = await selector_healing_service.reject(db, suggestion_id)
    return HealingSuggestionResponse(
        id=suggestion.id,
        generated_test_id=suggestion.generated_test_id,
        failed_selector=suggestion.failed_selector,
        suggested_selector=suggestion.suggested_selector,
        confidence_score=suggestion.confidence_score,
        rationale=suggestion.rationale,
        approved=suggestion.approved,
        created_at=suggestion.created_at,
    )
