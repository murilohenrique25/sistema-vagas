from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.enums import UserRole
from app.models.user import User
from app.schemas.company import normalize_and_validate_cnpj
from app.services.account_deletion_service import AccountDeletionService


def test_cnpj_check_digits_accept_known_active_company():
    assert normalize_and_validate_cnpj("59.542.925/0001-07") == "59542925000107"


@pytest.mark.parametrize("value", ["59.542.925/0001-08", "11.111.111/1111-11", "123"])
def test_cnpj_check_digits_reject_invalid_values(value):
    with pytest.raises(ValueError):
        normalize_and_validate_cnpj(value)


@pytest.mark.asyncio
async def test_account_deletion_requires_exact_confirmation():
    session = AsyncMock()
    service = AccountDeletionService(session)
    with pytest.raises(HTTPException) as exc:
        await service.delete_account(uuid4(), "excluir", None)
    assert exc.value.status_code == 400
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_oauth_candidate_account_is_deleted_transactionally():
    user = User(id=uuid4(), email="candidate@example.com", name="Candidate", role=UserRole.candidate, password_hash=None)
    first_result = MagicMock()
    first_result.scalar_one_or_none.return_value = user
    session = AsyncMock()
    session.execute.side_effect = [first_result] + [MagicMock() for _ in range(25)]

    await AccountDeletionService(session).delete_account(user.id, "EXCLUIR MINHA CONTA", None)

    assert session.execute.await_count >= 15
    session.flush.assert_awaited_once()
