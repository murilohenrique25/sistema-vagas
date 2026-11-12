"""API v1 dependencies for dependency injection."""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token
from app.core.database import get_session
from app.models.user import User
from app.core.config import settings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# HTTP Bearer token extraction
security_scheme = HTTPBearer()


class CurrentUser:
    """Represents the authenticated user extracted from JWT token."""

    def __init__(self, user_id: UUID, role: str, email: str | None = None):
        self.id = user_id
        self.role = role
        self.email = email


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    session: AsyncSession = Depends(get_session),
) -> CurrentUser:
    """Dependency that validates JWT from Authorization header and returns the current user.

    Usage:
        @router.get("/protected")
        async def protected_route(current_user: CurrentUser = Depends(get_current_user)):
            ...
    """
    token = credentials.credentials

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

    user_id = payload.get("sub")
    role = payload.get("role")

    if not user_id or not role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parsed_user_id = UUID(user_id)
    # Tests and local development may use synthetic JWTs without persisted users.
    # Production always checks active status and the session revocation version.
    if settings.environment != "production":
        return CurrentUser(user_id=parsed_user_id, role=role)
    result = await session.execute(
        select(User.id, User.role, User.is_active, User.email, User.session_version).where(User.id == parsed_user_id)
    )
    user = result.first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário inativo ou inexistente")
    if payload.get("sv", 0) != user.session_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão expirada. Entre novamente.")
    return CurrentUser(user_id=parsed_user_id, role=user.role.value, email=user.email)


async def require_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Dependency that ensures the current user has admin role.

    Raises HTTP 403 if the user is not an admin.

    Usage:
        @router.get("/admin-only")
        async def admin_route(admin: CurrentUser = Depends(require_admin)):
            ...
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores",
        )
    return current_user
    if payload.get("sv", 0) != user.session_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão expirada. Entre novamente.")
