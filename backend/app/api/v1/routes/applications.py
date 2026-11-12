"""Application routes: apply, list, cancel, status change (workflow)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import CurrentUser, get_current_user
from app.core.database import get_session
from app.schemas.application import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationStatusUpdate,
    PaginatedApplicationsResponse,
)
from app.services.application_service import ApplicationService

router = APIRouter(prefix="/applications", tags=["applications"])


def _require_candidate(current_user: CurrentUser) -> None:
    """Ensure the current user is a candidate."""
    if current_user.role != "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas candidatos podem realizar esta ação",
        )


def _require_employer(current_user: CurrentUser) -> None:
    """Ensure the current user is an employer."""
    if current_user.role != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas empregadores podem realizar esta ação",
        )


@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Candidatar-se a uma vaga",
    description=(
        "Registra uma nova candidatura. Requer currículo cadastrado, "
        "vaga ativa e sem candidatura duplicada."
    ),
)
async def apply_to_job(
    data: ApplicationCreate,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApplicationResponse:
    """Create a new application (candidate applies to a job)."""
    _require_candidate(current_user)

    service = ApplicationService(session)
    application = await service.apply(current_user.id, data.job_id)
    return ApplicationResponse.model_validate(application)


@router.get(
    "/me",
    response_model=PaginatedApplicationsResponse,
    summary="Minhas candidaturas",
    description=(
        "Lista as candidaturas do candidato autenticado, ordenadas por data "
        "de candidatura decrescente, com 20 itens por página."
    ),
)
async def list_my_applications(
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PaginatedApplicationsResponse:
    """List candidate's applications with pagination."""
    _require_candidate(current_user)

    service = ApplicationService(session)
    return await service.get_candidate_applications(
        current_user.id, page=page, page_size=page_size
    )


@router.patch(
    "/{application_id}/status",
    response_model=ApplicationResponse,
    summary="Alterar status da candidatura (empregador)",
    description=(
        "Altera o status de uma candidatura seguindo o workflow definido. "
        "Transições progressivas: Recebida → Em análise → Entrevista → Teste técnico → Proposta → Contratado. "
        "Reprovação é permitida de qualquer status exceto Contratado e Cancelado. "
        "Cancelamento é permitido de qualquer status exceto Contratado."
    ),
)
async def change_application_status(
    application_id: UUID,
    data: ApplicationStatusUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApplicationResponse:
    """Change application status (employer workflow)."""
    _require_employer(current_user)

    service = ApplicationService(session)
    application = await service.change_status(
        application_id, data.status, changed_by=current_user.id
    )
    return ApplicationResponse.model_validate(application)


@router.patch(
    "/{application_id}/cancel",
    response_model=ApplicationResponse,
    summary="Cancelar candidatura",
    description=(
        "Cancela uma candidatura ativa. Não é possível cancelar candidaturas "
        "com status final (Contratado ou Reprovado)."
    ),
)
async def cancel_application(
    application_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApplicationResponse:
    """Cancel an application."""
    _require_candidate(current_user)

    service = ApplicationService(session)
    application = await service.cancel(application_id, current_user.id)
    return ApplicationResponse.model_validate(application)
