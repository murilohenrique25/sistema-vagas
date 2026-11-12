"""Email verification and password reset with hashed, single-use tokens."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models.account_action_token import AccountActionToken
from app.models.user import User
from app.services.email_sender import get_email_sender

EMAIL_VERIFICATION = "email_verification"
PASSWORD_RESET = "password_reset"
GENERIC_VERIFY_MESSAGE = "Se a conta existir e ainda precisar de confirmação, enviaremos as instruções."
GENERIC_RESET_MESSAGE = "Se o e-mail estiver cadastrado, enviaremos as instruções para redefinir a senha."
INVALID_TOKEN_MESSAGE = "Este link é inválido, já foi utilizado ou expirou. Solicite um novo link."


class AccountSecurityService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def request_email_verification(self, email: str) -> str:
        user = await self._get_user_by_email(email)
        if user and user.is_active and not user.email_verified_at:
            await self.send_email_verification(user)
        return GENERIC_VERIFY_MESSAGE

    async def send_email_verification(self, user: User) -> None:
        """Issue and send a verification link for a known new user."""
        token = await self._issue_token(
            user,
            EMAIL_VERIFICATION,
            timedelta(hours=settings.email_verification_expire_hours),
        )
        url = self._frontend_url("/verify-email", token)
        await get_email_sender().send_email(
            user.email,
            "Confirme seu e-mail — Recruta IA",
            f"Olá, {user.name}. Confirme seu e-mail acessando: {url}\n"
            f"O link expira em {settings.email_verification_expire_hours} horas e só pode ser usado uma vez.",
        )

    async def verify_email(self, raw_token: str) -> str:
        token = await self._consume_token(raw_token, EMAIL_VERIFICATION)
        user = await self.session.get(User, token.user_id, with_for_update=True)
        if not user or not user.is_active:
            raise self._invalid_token_error()
        user.email_verified_at = datetime.now(timezone.utc)
        await self._invalidate_tokens(user.id, EMAIL_VERIFICATION)
        await self.session.flush()
        return "E-mail confirmado com sucesso. Você já pode entrar."

    async def request_password_reset(self, email: str) -> str:
        user = await self._get_user_by_email(email)
        if user and user.is_active and user.password_hash:
            token = await self._issue_token(
                user,
                PASSWORD_RESET,
                timedelta(minutes=settings.password_reset_expire_minutes),
            )
            url = self._frontend_url("/reset-password", token)
            await get_email_sender().send_email(
                user.email,
                "Redefina sua senha — Recruta IA",
                f"Olá, {user.name}. Redefina sua senha acessando: {url}\n"
                f"O link expira em {settings.password_reset_expire_minutes} minutos e só pode ser usado uma vez.",
            )
        return GENERIC_RESET_MESSAGE

    async def reset_password(self, raw_token: str, new_password: str) -> str:
        token = await self._consume_token(raw_token, PASSWORD_RESET)
        user = await self.session.get(User, token.user_id, with_for_update=True)
        if not user or not user.is_active:
            raise self._invalid_token_error()
        user.password_hash = hash_password(new_password)
        user.failed_login_attempts = 0
        user.locked_until = None
        user.session_version += 1
        await self._invalidate_tokens(user.id, PASSWORD_RESET)
        await self.session.flush()
        return "Senha redefinida com sucesso. Entre com sua nova senha."

    async def _issue_token(self, user: User, purpose: str, lifetime: timedelta) -> str:
        await self._invalidate_tokens(user.id, purpose)
        raw_token = secrets.token_urlsafe(32)
        self.session.add(
            AccountActionToken(
                user_id=user.id,
                purpose=purpose,
                token_hash=self._hash_token(raw_token),
                expires_at=datetime.now(timezone.utc) + lifetime,
            )
        )
        await self.session.flush()
        return raw_token

    async def _consume_token(self, raw_token: str, purpose: str) -> AccountActionToken:
        if not raw_token or len(raw_token) > 500:
            raise self._invalid_token_error()
        result = await self.session.execute(
            select(AccountActionToken)
            .where(
                AccountActionToken.token_hash == self._hash_token(raw_token),
                AccountActionToken.purpose == purpose,
            )
            .with_for_update()
        )
        token = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if not token or token.used_at is not None or token.expires_at <= now:
            raise self._invalid_token_error()
        token.used_at = now
        await self.session.flush()
        return token

    async def _invalidate_tokens(self, user_id: object, purpose: str) -> None:
        await self.session.execute(
            update(AccountActionToken)
            .where(
                AccountActionToken.user_id == user_id,
                AccountActionToken.purpose == purpose,
                AccountActionToken.used_at.is_(None),
            )
            .values(used_at=datetime.now(timezone.utc))
        )

    async def _get_user_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email.strip().lower()))
        return result.scalar_one_or_none()

    @staticmethod
    def _frontend_url(path: str, token: str) -> str:
        return f"{settings.frontend_url.rstrip('/')}{path}?{urlencode({'token': token})}"

    @staticmethod
    def _invalid_token_error() -> HTTPException:
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_TOKEN_MESSAGE)
