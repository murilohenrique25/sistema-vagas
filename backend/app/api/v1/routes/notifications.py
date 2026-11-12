"""Notification routes for user notification management.

Endpoints:
- GET /v1/notifications - Get user's notifications (paginated, newest first)
- GET /v1/notifications/unread-count - Get count of unread notifications
- PATCH /v1/notifications/{id}/read - Mark notification as read
"""

import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import CurrentUser, get_current_user
from app.core.database import get_session
from app.schemas.notification import (
    MarkAsReadResponse,
    NotificationListResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="Listar notificações do usuário",
    description=(
        "Retorna as notificações do usuário autenticado de forma paginada, "
        "ordenadas da mais recente para a mais antiga. "
        "Inclui notificações pendentes/falhas para exibição no próximo acesso (Req 13.8)."
    ),
)
async def get_notifications(
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> NotificationListResponse:
    """Get paginated notifications for the current user."""
    service = NotificationService(session)
    notifications, total = await service.get_user_notifications(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Contagem de notificações não lidas",
    description="Retorna a quantidade de notificações não lidas do usuário autenticado.",
)
async def get_unread_count(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UnreadCountResponse:
    """Get the count of unread notifications for the current user."""
    service = NotificationService(session)
    count = await service.get_unread_count(user_id=current_user.id)
    return UnreadCountResponse(unread_count=count)


@router.patch(
    "/{notification_id}/read",
    response_model=MarkAsReadResponse,
    summary="Marcar notificação como lida",
    description="Marca uma notificação específica como lida para o usuário autenticado.",
)
async def mark_notification_as_read(
    notification_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MarkAsReadResponse:
    """Mark a specific notification as read."""
    service = NotificationService(session)
    try:
        notification = await service.mark_as_read(
            notification_id=notification_id,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return MarkAsReadResponse(
        id=notification.id,
        is_read=notification.is_read,
        read_at=notification.read_at,
    )
