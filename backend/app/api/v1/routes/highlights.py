"""Highlight routes for job highlighting functionality."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import CurrentUser, get_current_user
from app.core.database import get_session
from app.schemas.highlight import (
    ActivateHighlightRequest,
    HighlightListResponse,
    HighlightResponse,
)
from app.services.highlight_service import HighlightService

router = APIRouter(prefix="/highlights", tags=["highlights"])


@router.post(
    "",
    response_model=HighlightResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ativar destaque em uma vaga",
    description=(
        "Ativa um destaque de 7 dias em uma vaga. "
        "Se o empregador possui plano Enterprise, o destaque é gratuito. "
        "Caso contrário, será debitado 1 token de destaque. "
        "Limite de 20 vagas em destaque simultâneas."
    ),
)
async def activate_highlight(
    body: ActivateHighlightRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> HighlightResponse:
    """Activate a highlight for a job (Req 12.1)."""
    service = HighlightService(session)
    highlight = await service.activate_highlight(
        user_id=current_user.id,
        job_id=body.job_id,
    )
    return HighlightResponse(
        id=highlight.id,
        job_id=highlight.job_id,
        activated_at=highlight.activated_at,
        expires_at=highlight.expires_at,
        is_active=highlight.is_active,
    )


@router.get(
    "",
    response_model=HighlightListResponse,
    summary="Listar vagas em destaque ativas",
    description="Retorna todas as vagas com destaque ativo no momento.",
)
async def list_active_highlights(
    session: AsyncSession = Depends(get_session),
) -> HighlightListResponse:
    """List all currently active highlighted jobs."""
    service = HighlightService(session)
    highlights = await service.get_active_highlights()
    items = [
        HighlightResponse(
            id=h.id,
            job_id=h.job_id,
            activated_at=h.activated_at,
            expires_at=h.expires_at,
            is_active=h.is_active,
        )
        for h in highlights
    ]
    return HighlightListResponse(items=items, total=len(items))


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desativar destaque de uma vaga",
    description="Remove o destaque de uma vaga antes do prazo de expiração.",
)
async def deactivate_highlight(
    job_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Deactivate a highlight early (Req 12.3)."""
    service = HighlightService(session)
    await service.deactivate_highlight(
        user_id=current_user.id,
        job_id=job_id,
    )
