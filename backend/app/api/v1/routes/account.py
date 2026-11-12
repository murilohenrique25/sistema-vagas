"""Authenticated account settings and erasure routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import CurrentUser, get_current_user
from app.core.database import get_session
from app.schemas.account import DeleteAccountRequest, DeleteAccountResponse
from app.services.account_deletion_service import AccountDeletionService


router = APIRouter(prefix="/account", tags=["account"])


@router.delete("", response_model=DeleteAccountResponse)
async def delete_my_account(
    data: DeleteAccountRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DeleteAccountResponse:
    await AccountDeletionService(session).delete_account(user.id, data.confirmation, data.password)
    return DeleteAccountResponse(message="Conta e dados associados excluídos permanentemente")

