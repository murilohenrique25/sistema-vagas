"""Authentication schemas for request/response validation."""

import re
from typing import Literal

from pydantic import BaseModel, field_validator

from app.models.enums import UserRole


def validate_strong_password(value: str) -> str:
    """Apply the password policy shared by registration and reset."""
    if len(value) < 8:
        raise ValueError("A senha deve ter no mínimo 8 caracteres")
    if len(value.encode("utf-8")) > 72:
        raise ValueError("A senha deve ter no máximo 72 bytes")
    if not re.search(r"[A-Z]", value):
        raise ValueError("A senha deve conter pelo menos uma letra maiúscula")
    if not re.search(r"[a-z]", value):
        raise ValueError("A senha deve conter pelo menos uma letra minúscula")
    if not re.search(r"\d", value):
        raise ValueError("A senha deve conter pelo menos um número")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?~`]", value):
        raise ValueError("A senha deve conter pelo menos um caractere especial")
    return value


class RegisterRequest(BaseModel):
    """Schema for user registration."""

    email: str
    password: str
    name: str
    role: UserRole
    accept_terms: Literal[True]
    accept_privacy: Literal[True]

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        """Validate email format according to RFC 5322 simplified pattern."""
        pattern = r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
        if not re.match(pattern, v):
            raise ValueError("Formato de email inválido")
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets strength requirements."""
        return validate_strong_password(v)


class LoginRequest(BaseModel):
    """Schema for user login."""

    email: str
    password: str
    otp_code: str | None = None

class TotpCodeRequest(BaseModel):
    code: str

class TotpSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str


class TokenResponse(BaseModel):
    """Schema for token pair response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Schema for token refresh."""

    refresh_token: str


class MessageResponse(BaseModel):
    """Generic response for account-security actions."""

    message: str


class RegisterResponse(MessageResponse):
    """Registration acknowledgement; authentication starts after verification."""

    email: str


class EmailRequest(BaseModel):
    """Request containing an email without exposing account existence."""

    email: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class TokenRequest(BaseModel):
    """Request containing a signed action token."""

    token: str


class PasswordResetRequest(TokenRequest):
    """Complete a password reset using a single-use token."""

    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        return validate_strong_password(value)
