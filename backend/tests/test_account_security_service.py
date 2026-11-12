"""Security tests for expiring, single-use account action links."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.account_action_token import AccountActionToken
from app.models.enums import UserRole
from app.models.user import User
from app.services.account_security_service import (
    AccountSecurityService,
    EMAIL_VERIFICATION,
    GENERIC_RESET_MESSAGE,
    PASSWORD_RESET,
)


def user() -> User:
    return User(
        id=uuid.uuid4(), email="secure@example.com", password_hash="hash",
        name="Secure User", role=UserRole.candidate, is_active=True,
        failed_login_attempts=0,
    )


def action_token(raw: str, purpose: str, *, expires_delta: timedelta, used=False) -> AccountActionToken:
    return AccountActionToken(
        id=uuid.uuid4(), user_id=uuid.uuid4(), purpose=purpose,
        token_hash=AccountSecurityService._hash_token(raw),
        expires_at=datetime.now(timezone.utc) + expires_delta,
        used_at=datetime.now(timezone.utc) if used else None,
    )


@pytest.fixture
def session():
    value = AsyncMock()
    value.add = MagicMock()
    value.flush = AsyncMock()
    return value


async def test_issued_token_is_stored_only_as_hash(session):
    service = AccountSecurityService(session)
    raw = await service._issue_token(user(), EMAIL_VERIFICATION, timedelta(hours=24))
    stored = session.add.call_args.args[0]
    assert raw != stored.token_hash
    assert stored.token_hash == service._hash_token(raw)
    assert len(stored.token_hash) == 64


async def test_token_is_marked_used_when_consumed(session):
    stored = action_token("valid-token", PASSWORD_RESET, expires_delta=timedelta(minutes=5))
    result = MagicMock()
    result.scalar_one_or_none.return_value = stored
    session.execute = AsyncMock(return_value=result)

    consumed = await AccountSecurityService(session)._consume_token("valid-token", PASSWORD_RESET)
    assert consumed.used_at is not None


@pytest.mark.parametrize("stored", [
    action_token("expired", PASSWORD_RESET, expires_delta=timedelta(seconds=-1)),
    action_token("used", PASSWORD_RESET, expires_delta=timedelta(minutes=5), used=True),
])
async def test_expired_or_used_token_is_rejected(session, stored):
    result = MagicMock()
    result.scalar_one_or_none.return_value = stored
    session.execute = AsyncMock(return_value=result)
    raw = "expired" if stored.token_hash == AccountSecurityService._hash_token("expired") else "used"

    with pytest.raises(HTTPException) as exc_info:
        await AccountSecurityService(session)._consume_token(raw, PASSWORD_RESET)
    assert exc_info.value.status_code == 400
    assert "utilizado ou expirou" in exc_info.value.detail


async def test_unknown_email_has_same_neutral_response(session):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result)

    response = await AccountSecurityService(session).request_password_reset("unknown@example.com")
    assert response == GENERIC_RESET_MESSAGE
    session.add.assert_not_called()


@patch("app.services.account_security_service.get_email_sender")
async def test_new_request_invalidates_previous_link(mock_sender, session):
    account = user()
    result = MagicMock()
    result.scalar_one_or_none.return_value = account
    session.execute = AsyncMock(return_value=result)
    mock_sender.return_value.send_email = AsyncMock(return_value=True)

    await AccountSecurityService(session).request_password_reset(account.email)

    # First execute invalidates every unused previous reset token before adding the new one.
    assert session.execute.await_count >= 2
    assert session.add.call_count == 1
    mock_sender.return_value.send_email.assert_awaited_once()
