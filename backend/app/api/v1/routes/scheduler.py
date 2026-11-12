"""Scheduler routes for automated background tasks."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import CurrentUser, get_current_user
from app.core.database import get_session
from app.schemas.highlight import ExpireHighlightsResponse
from app.schemas.notification import ProcessQueueResponse, RetryNotificationsResponse
from app.services.highlight_service import HighlightService
from app.services.job_service import JobService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.post(
    "/close-expired-jobs",
    summary="Encerrar vagas expiradas",
    description=(
        "Encerra automaticamente todas as vagas ativas cujo prazo de encerramento "
        "já passou. Deve ser chamado periodicamente por um job scheduler (cron). "
        "Apenas administradores podem executar manualmente."
    ),
)
async def close_expired_jobs(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Close all jobs that have passed their deadline.

    This endpoint is designed to be called by a scheduled task (cron job)
    or manually by an admin. It closes all active jobs whose deadline has passed.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem executar esta ação",
        )

    job_service = JobService(session)
    closed_count = await job_service.close_expired_jobs()
    return {
        "message": f"{closed_count} vaga(s) encerrada(s) automaticamente",
        "closed_count": closed_count,
    }


@router.post(
    "/expire-highlights",
    response_model=ExpireHighlightsResponse,
    summary="Expirar destaques de vagas vencidos",
    description=(
        "Expira automaticamente todos os destaques de vagas cujo período de 7 dias "
        "já passou. Notifica o empregador sobre a expiração. "
        "Deve ser chamado periodicamente por um job scheduler (cron)."
    ),
)
async def expire_highlights(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ExpireHighlightsResponse:
    """Expire all highlights past their 7-day duration (Req 12.3)."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem executar esta ação",
        )

    service = HighlightService(session)
    expired_count = await service.expire_highlights()
    return ExpireHighlightsResponse(
        expired_count=expired_count,
        message=f"{expired_count} destaque(s) expirado(s) automaticamente",
    )


@router.post(
    "/process-notification-queue",
    response_model=ProcessQueueResponse,
    summary="Processar fila de notificações",
    description=(
        "Processa notificações pendentes na fila Redis. "
        "Envia notificações via plataforma e/ou e-mail conforme configurado. "
        "SLA de 5 minutos para envio (Req 13.1-13.6). "
        "Deve ser chamado periodicamente por um job scheduler (a cada 1-2 min)."
    ),
)
async def process_notification_queue(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProcessQueueResponse:
    """Process pending notifications from the Redis queue."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem executar esta ação",
        )

    service = NotificationService(session)
    processed = await service.process_notification_queue()
    return ProcessQueueResponse(
        processed_count=processed,
        message=f"{processed} notificação(ões) processada(s)",
    )


@router.post(
    "/retry-failed-notifications",
    response_model=RetryNotificationsResponse,
    summary="Retentar notificações com falha",
    description=(
        "Retenta envio de notificações que falharam, respeitando o limite "
        "de 3 tentativas adicionais com intervalo mínimo de 5 minutos (Req 13.7). "
        "Notificações que falharam em todas as tentativas são registradas como "
        "falha e exibidas no próximo acesso do usuário (Req 13.8). "
        "Deve ser chamado periodicamente por um job scheduler (a cada 5 min)."
    ),
)
async def retry_failed_notifications(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RetryNotificationsResponse:
    """Retry notifications that failed delivery."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem executar esta ação",
        )

    service = NotificationService(session)
    retried = await service.retry_failed_notifications()
    return RetryNotificationsResponse(
        retried_count=retried,
        message=f"{retried} notificação(ões) retentada(s)",
    )



@router.post(
    "/notify-expiring-jobs",
    summary="Notificar vagas próximas do encerramento",
    description=(
        "Verifica vagas ativas com prazo de encerramento em 7 dias e envia "
        "notificação ao empregador responsável (Req 13.6). "
        "Deve ser chamado diariamente por um job scheduler (cron)."
    ),
)
async def notify_expiring_jobs(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Notify employers about jobs expiring in 7 days (Req 13.6)."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem executar esta ação",
        )

    job_service = JobService(session)
    notified_count = await job_service.notify_expiring_jobs()
    return {
        "message": f"{notified_count} empregador(es) notificado(s) sobre vagas expirando",
        "notified_count": notified_count,
    }
