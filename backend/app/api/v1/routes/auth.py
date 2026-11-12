"""Authentication routes: register, login, refresh."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.auth import (
    LoginRequest,
    EmailRequest,
    MessageResponse,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenRequest,
    TokenResponse,
    TotpCodeRequest,
    TotpSetupResponse,
)
from app.services.account_security_service import AccountSecurityService
from app.api.v1.dependencies import CurrentUser, require_admin
from app.models.user import User
from app.core.totp import new_secret, uri, verify as verify_totp
from app.core.secrets import encrypt_secret, decrypt_secret
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar novo usuário",
    description="Registra um novo usuário e envia um link de confirmação de e-mail.",
)
async def register(
    data: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> RegisterResponse:
    """Register a new user pending email verification."""
    auth_service = AuthService(session)
    return await auth_service.register(data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login do usuário",
    description="Autentica o usuário com email e senha, retornando access token (15min) e refresh token (7 dias).",
)
async def login(
    data: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Authenticate user and return JWT token pair."""
    auth_service = AuthService(session)
    return await auth_service.login(data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renovar access token",
    description="Utiliza o refresh token para gerar um novo par de tokens sem exigir reautenticação.",
)
async def refresh(
    data: RefreshRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Refresh access token using a valid refresh token."""
    auth_service = AuthService(session)
    return await auth_service.refresh_token(data.refresh_token)


@router.post("/email-verification/request", response_model=MessageResponse)
async def request_email_verification(
    data: EmailRequest, session: AsyncSession = Depends(get_session)
) -> MessageResponse:
    service = AccountSecurityService(session)
    return MessageResponse(message=await service.request_email_verification(data.email))


@router.post("/email-verification/confirm", response_model=MessageResponse)
async def confirm_email_verification(
    data: TokenRequest, session: AsyncSession = Depends(get_session)
) -> MessageResponse:
    service = AccountSecurityService(session)
    return MessageResponse(message=await service.verify_email(data.token))


@router.post("/password/forgot", response_model=MessageResponse)
async def forgot_password(
    data: EmailRequest, session: AsyncSession = Depends(get_session)
) -> MessageResponse:
    service = AccountSecurityService(session)
    return MessageResponse(message=await service.request_password_reset(data.email))


@router.post("/password/reset", response_model=MessageResponse)
async def reset_password(
    data: PasswordResetRequest, session: AsyncSession = Depends(get_session)
) -> MessageResponse:
    service = AccountSecurityService(session)
    return MessageResponse(message=await service.reset_password(data.token, data.new_password))

@router.post("/2fa/setup", response_model=TotpSetupResponse)
async def setup_2fa(admin: CurrentUser=Depends(require_admin), session: AsyncSession=Depends(get_session)):
    user=await session.get(User,admin.id); secret=new_secret(); user.totp_secret=encrypt_secret(secret); user.totp_enabled=False
    return TotpSetupResponse(secret=secret,otpauth_uri=uri(secret,user.email))

@router.post("/2fa/confirm", response_model=MessageResponse)
async def confirm_2fa(data:TotpCodeRequest,admin:CurrentUser=Depends(require_admin),session:AsyncSession=Depends(get_session)):
    user=await session.get(User,admin.id); secret=decrypt_secret(user.totp_secret)
    if not secret or not verify_totp(secret,data.code): raise HTTPException(status_code=400,detail="Código inválido")
    user.totp_enabled=True; user.session_version+=1
    return MessageResponse(message="Autenticação em dois fatores ativada. Entre novamente.")
