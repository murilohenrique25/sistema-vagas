"""Authentication service with registration, login, and token management."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, RegisterResponse, TokenResponse
from app.services.account_security_service import AccountSecurityService
from app.core.secrets import decrypt_secret
from app.core.totp import verify as verify_totp

# Constants for account lockout
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


class AuthService:
    """Service handling authentication logic."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(self, data: RegisterRequest) -> RegisterResponse:
        """Register a new user with validated email and password.

        - Validates email uniqueness
        - Hashes password with bcrypt + random salt
        - Creates user record
        - Sends a single-use email verification link
        """
        # Check for duplicate email
        existing_user = await self._get_user_by_email(data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este email já está em uso",
            )

        # Hash password with bcrypt (includes random salt)
        password_hash = hash_password(data.password)

        # Create user
        user = User(
            email=data.email.lower(),
            password_hash=password_hash,
            name=data.name,
            role=data.role,
            is_active=True,
            failed_login_attempts=0,
            terms_accepted_at=datetime.now(timezone.utc),
            privacy_accepted_at=datetime.now(timezone.utc),
            legal_version="2026-09-28",
        )
        self.session.add(user)
        await self.session.flush()

        await AccountSecurityService(self.session).send_email_verification(user)
        return RegisterResponse(
            email=user.email,
            message="Cadastro realizado. Enviamos um link de confirmação para seu e-mail.",
        )

    async def login(self, data: LoginRequest) -> TokenResponse:
        """Authenticate user and return JWT token pair.

        - Checks account lockout status
        - Verifies credentials without revealing email existence
        - Locks account after 5 failed attempts in 15 minutes
        - Resets failed attempts on successful login
        """
        user = await self._get_user_by_email(data.email.lower())

        # Generic error message that doesn't reveal if email exists (Req 1.5)
        invalid_credentials_error = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

        if not user:
            # Don't reveal that email doesn't exist
            raise invalid_credentials_error

        # Check if account is locked (Req 1.6)
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Conta temporariamente bloqueada. Tente novamente em 15 minutos.",
            )

        # Verify password
        if not user.password_hash or not verify_password(data.password, user.password_hash):
            # Increment failed attempts
            user.failed_login_attempts += 1

            # Lock account after 5 failed attempts (Req 1.6)
            if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                user.locked_until = datetime.now(timezone.utc) + timedelta(
                    minutes=LOCKOUT_DURATION_MINUTES
                )

            await self.session.flush()
            raise invalid_credentials_error

        # Check if user is active
        if not user.is_active:
            raise invalid_credentials_error

        if not user.email_verified_at:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Confirme seu e-mail antes de entrar.",
            )
        if user.role.value == "admin" and user.totp_enabled:
            secret = decrypt_secret(user.totp_secret)
            if not data.otp_code or not secret or not verify_totp(secret, data.otp_code):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Código de autenticação em dois fatores obrigatório ou inválido")

        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        await self.session.flush()

        # Generate JWT token pair
        access_token, refresh_token = create_token_pair(user.id, user.role.value, user.session_version or 0)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Validate refresh token and issue new access token.

        - Decodes and validates the refresh token
        - Returns new token pair if valid
        - Returns 401 if expired/invalid (client should redirect to login - Req 1.7)
        """
        payload = decode_token(refresh_token)

        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de refresh inválido ou expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de refresh inválido ou expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de refresh inválido ou expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            parsed_user_id = UUID(user_id)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de refresh inválido ou expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = await self.session.get(User, parsed_user_id)
        if not user or not user.is_active or not user.email_verified_at:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de refresh inválido ou expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if payload.get("sv", 0) != (user.session_version or 0):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão expirada. Entre novamente.")
        access_token, new_refresh_token = create_token_pair(user.id, user.role.value, user.session_version or 0)

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
        )

    @staticmethod
    def validate_token(token: str) -> dict:
        """Decode and validate a JWT access token.

        Returns the payload if valid, raises HTTPException otherwise.
        """
        payload = decode_token(token)

        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido ou expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido ou expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload

    async def _get_user_by_email(self, email: str) -> User | None:
        """Retrieve user by email address."""
        result = await self.session.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()
