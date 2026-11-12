"""Tests for AuthService: registration, login, token refresh, and lockout."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, RefreshRequest
from app.services.auth_service import AuthService, MAX_FAILED_ATTEMPTS, LOCKOUT_DURATION_MINUTES


class TestPasswordHashing:
    """Tests for bcrypt password hashing with random salt."""

    def test_hash_password_produces_bcrypt_hash(self):
        """Hash should be a bcrypt hash starting with $2b$."""
        hashed = hash_password("TestPass1!")
        assert hashed.startswith("$2b$")

    def test_verify_correct_password(self):
        """verify_password returns True for correct password."""
        pw = "ValidPass1!"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True

    def test_verify_wrong_password(self):
        """verify_password returns False for wrong password."""
        hashed = hash_password("ValidPass1!")
        assert verify_password("WrongPass1!", hashed) is False

    def test_different_hashes_for_same_password(self):
        """Same password hashed twice produces different results (random salt)."""
        pw = "ValidPass1!"
        h1 = hash_password(pw)
        h2 = hash_password(pw)
        assert h1 != h2

    def test_hash_not_equal_to_original(self):
        """Stored hash is never equal to the original password."""
        pw = "TestPass1!"
        hashed = hash_password(pw)
        assert hashed != pw


class TestJWTTokens:
    """Tests for JWT token creation and validation."""

    def test_create_access_token(self):
        """Access token contains correct type and claims."""
        uid = uuid.uuid4()
        token = create_access_token(uid, "candidate")
        payload = decode_token(token)
        assert payload is not None
        assert payload["type"] == "access"
        assert payload["sub"] == str(uid)
        assert payload["role"] == "candidate"

    def test_create_refresh_token(self):
        """Refresh token contains correct type and claims."""
        uid = uuid.uuid4()
        token = create_refresh_token(uid, "employer")
        payload = decode_token(token)
        assert payload is not None
        assert payload["type"] == "refresh"
        assert payload["sub"] == str(uid)
        assert payload["role"] == "employer"

    def test_create_token_pair(self):
        """create_token_pair returns both access and refresh tokens."""
        uid = uuid.uuid4()
        access, refresh = create_token_pair(uid, "admin")
        access_payload = decode_token(access)
        refresh_payload = decode_token(refresh)
        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"

    def test_decode_invalid_token_returns_none(self):
        """Invalid token returns None when decoded."""
        assert decode_token("not.a.valid.token") is None

    def test_decode_tampered_token_returns_none(self):
        """Token with tampered signature returns None."""
        uid = uuid.uuid4()
        token = create_access_token(uid, "candidate")
        # Tamper with the token
        tampered = token[:-5] + "XXXXX"
        assert decode_token(tampered) is None


class TestRegisterSchema:
    """Tests for RegisterRequest schema validation."""

    def test_valid_registration(self):
        """Valid email and password are accepted."""
        req = RegisterRequest(
            email="user@example.com",
            password="ValidPass1!",
            name="John Doe",
            role="candidate", accept_terms=True, accept_privacy=True,
        )
        assert req.email == "user@example.com"

    def test_legal_acceptance_is_required(self):
        """Registration cannot proceed without both explicit legal acknowledgements."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="user@example.com", password="ValidPass1!", name="User",
                role="candidate", accept_terms=False, accept_privacy=True,
            )

    def test_email_normalized_to_lowercase(self):
        """Email is normalized to lowercase."""
        req = RegisterRequest(
            email="User@EXAMPLE.com",
            password="ValidPass1!",
            name="Test",
            role="candidate", accept_terms=True, accept_privacy=True,
        )
        assert req.email == "user@example.com"

    def test_invalid_email_rejected(self):
        """Invalid email format is rejected."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="email"):
            RegisterRequest(
                email="not-an-email",
                password="ValidPass1!",
                name="Test",
                role="candidate", accept_terms=True, accept_privacy=True,
            )

    def test_password_min_8_chars(self):
        """Password shorter than 8 characters is rejected."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="8 caracteres"):
            RegisterRequest(
                email="test@example.com",
                password="Aa1!",
                name="Test",
                role="candidate", accept_terms=True, accept_privacy=True,
            )

    def test_password_requires_uppercase(self):
        """Password without uppercase letter is rejected."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="maiúscula"):
            RegisterRequest(
                email="test@example.com",
                password="validpass1!",
                name="Test",
                role="candidate", accept_terms=True, accept_privacy=True,
            )

    def test_password_requires_lowercase(self):
        """Password without lowercase letter is rejected."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="minúscula"):
            RegisterRequest(
                email="test@example.com",
                password="VALIDPASS1!",
                name="Test",
                role="candidate", accept_terms=True, accept_privacy=True,
            )

    def test_password_requires_number(self):
        """Password without a number is rejected."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="número"):
            RegisterRequest(
                email="test@example.com",
                password="ValidPass!",
                name="Test",
                role="candidate", accept_terms=True, accept_privacy=True,
            )

    def test_password_requires_special_char(self):
        """Password without special character is rejected."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="especial"):
            RegisterRequest(
                email="test@example.com",
                password="ValidPass1a",
                name="Test",
                role="candidate", accept_terms=True, accept_privacy=True,
            )


class TestAuthServiceRegister:
    """Tests for AuthService.register method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()
        return session

    @patch("app.services.account_security_service.get_email_sender")
    async def test_register_success(self, mock_email_sender, mock_session):
        """Successful registration requires email confirmation before login."""
        mock_email_sender.return_value.send_email = AsyncMock(return_value=True)
        # Mock no existing user (email not taken)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = AuthService(mock_session)
        data = RegisterRequest(
            email="new@example.com",
            password="ValidPass1!",
            name="New User",
            role="candidate", accept_terms=True, accept_privacy=True,
        )

        result = await service.register(data)
        assert result.email == "new@example.com"
        assert "confirmação" in result.message
        assert mock_session.add.call_count == 2

    async def test_register_duplicate_email_rejected(self, mock_session):
        """Registration with existing email raises 409."""
        from fastapi import HTTPException

        existing_user = User(
            id=uuid.uuid4(),
            email="existing@example.com",
            password_hash="hash",
            name="Existing",
            role=UserRole.candidate,
            is_active=True,
            failed_login_attempts=0,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = AuthService(mock_session)
        data = RegisterRequest(
            email="existing@example.com",
            password="ValidPass1!",
            name="Test",
            role="candidate", accept_terms=True, accept_privacy=True,
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.register(data)
        assert exc_info.value.status_code == 409
        assert "email já está em uso" in exc_info.value.detail


class TestAuthServiceLogin:
    """Tests for AuthService.login method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        session.flush = AsyncMock()
        return session

    def _create_user(self, password="ValidPass1!", failed_attempts=0, locked_until=None, is_active=True):
        """Helper to create a test user."""
        user = User(
            id=uuid.uuid4(),
            email="user@example.com",
            password_hash=hash_password(password),
            name="Test User",
            role=UserRole.candidate,
            is_active=is_active,
            failed_login_attempts=failed_attempts,
            locked_until=locked_until,
            email_verified_at=datetime.now(timezone.utc),
        )
        return user

    async def test_login_success(self, mock_session):
        """Successful login returns tokens and resets attempts."""
        user = self._create_user()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = AuthService(mock_session)
        data = LoginRequest(email="user@example.com", password="ValidPass1!")

        result = await service.login(data)
        assert result.access_token
        assert result.refresh_token
        assert user.failed_login_attempts == 0
        assert user.locked_until is None

    async def test_login_rejects_unverified_email(self, mock_session):
        """Correct credentials cannot bypass email verification."""
        from fastapi import HTTPException

        user = self._create_user()
        user.email_verified_at = None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await AuthService(mock_session).login(
                LoginRequest(email="user@example.com", password="ValidPass1!")
            )
        assert exc_info.value.status_code == 403

    async def test_login_wrong_password(self, mock_session):
        """Wrong password raises 401 without revealing email exists."""
        from fastapi import HTTPException

        user = self._create_user()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = AuthService(mock_session)
        data = LoginRequest(email="user@example.com", password="WrongPass1!")

        with pytest.raises(HTTPException) as exc_info:
            await service.login(data)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Credenciais inválidas"

    async def test_login_nonexistent_email_same_error(self, mock_session):
        """Non-existent email returns same error as wrong password (Req 1.5)."""
        from fastapi import HTTPException

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = AuthService(mock_session)
        data = LoginRequest(email="nonexistent@example.com", password="AnyPass1!")

        with pytest.raises(HTTPException) as exc_info:
            await service.login(data)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Credenciais inválidas"

    async def test_login_increments_failed_attempts(self, mock_session):
        """Failed login increments failed_login_attempts counter."""
        from fastapi import HTTPException

        user = self._create_user(failed_attempts=2)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = AuthService(mock_session)
        data = LoginRequest(email="user@example.com", password="WrongPass1!")

        with pytest.raises(HTTPException):
            await service.login(data)
        assert user.failed_login_attempts == 3

    async def test_login_locks_after_5_attempts(self, mock_session):
        """Account locked after 5 failed attempts (Req 1.6)."""
        from fastapi import HTTPException

        user = self._create_user(failed_attempts=4)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = AuthService(mock_session)
        data = LoginRequest(email="user@example.com", password="WrongPass1!")

        with pytest.raises(HTTPException):
            await service.login(data)
        assert user.failed_login_attempts == 5
        assert user.locked_until is not None

    async def test_login_locked_account_rejected(self, mock_session):
        """Locked account raises 423 error."""
        from fastapi import HTTPException

        locked_until = datetime.now(timezone.utc) + timedelta(minutes=10)
        user = self._create_user(failed_attempts=5, locked_until=locked_until)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = AuthService(mock_session)
        data = LoginRequest(email="user@example.com", password="ValidPass1!")

        with pytest.raises(HTTPException) as exc_info:
            await service.login(data)
        assert exc_info.value.status_code == 423
        assert "bloqueada" in exc_info.value.detail

    async def test_login_expired_lockout_allows_login(self, mock_session):
        """Account with expired lockout allows login."""
        locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        user = self._create_user(failed_attempts=5, locked_until=locked_until)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = AuthService(mock_session)
        data = LoginRequest(email="user@example.com", password="ValidPass1!")

        result = await service.login(data)
        assert result.access_token
        assert user.failed_login_attempts == 0
        assert user.locked_until is None


class TestAuthServiceRefreshToken:
    """Tests for AuthService.refresh_token method."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    async def test_refresh_valid_token(self, mock_session):
        """Valid refresh token returns new token pair."""
        uid = uuid.uuid4()
        refresh = create_refresh_token(uid, "candidate")

        mock_session.get = AsyncMock(return_value=User(
            id=uid,
            email="verified@example.com",
            name="Verified",
            role=UserRole.candidate,
            is_active=True,
            email_verified_at=datetime.now(timezone.utc),
        ))
        service = AuthService(mock_session)
        result = await service.refresh_token(refresh)
        assert result.access_token
        assert result.refresh_token

    async def test_refresh_invalid_token_raises_401(self, mock_session):
        """Invalid refresh token raises 401."""
        from fastapi import HTTPException

        service = AuthService(mock_session)
        with pytest.raises(HTTPException) as exc_info:
            await service.refresh_token("invalid.token.here")
        assert exc_info.value.status_code == 401

    async def test_refresh_with_access_token_raises_401(self, mock_session):
        """Using access token for refresh raises 401 (Req 1.7)."""
        from fastapi import HTTPException

        uid = uuid.uuid4()
        access = create_access_token(uid, "candidate")

        service = AuthService(mock_session)
        with pytest.raises(HTTPException) as exc_info:
            await service.refresh_token(access)
        assert exc_info.value.status_code == 401


class TestValidateToken:
    """Tests for AuthService.validate_token static method."""

    def test_validate_valid_access_token(self):
        """Valid access token returns payload."""
        uid = uuid.uuid4()
        token = create_access_token(uid, "candidate")
        payload = AuthService.validate_token(token)
        assert payload["sub"] == str(uid)
        assert payload["type"] == "access"

    def test_validate_invalid_token_raises_401(self):
        """Invalid token raises 401."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            AuthService.validate_token("invalid")
        assert exc_info.value.status_code == 401

    def test_validate_refresh_token_raises_401(self):
        """Refresh token rejected by validate_token (expects access type)."""
        from fastapi import HTTPException
        uid = uuid.uuid4()
        refresh = create_refresh_token(uid, "candidate")
        with pytest.raises(HTTPException) as exc_info:
            AuthService.validate_token(refresh)
        assert exc_info.value.status_code == 401
