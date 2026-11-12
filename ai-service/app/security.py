import secrets

from fastapi import Header, HTTPException, status

from app.config import settings


async def require_internal_service(
    x_internal_service_token: str | None = Header(default=None),
) -> None:
    if not settings.internal_service_token and settings.environment != "production":
        return
    if not x_internal_service_token or not secrets.compare_digest(
        x_internal_service_token, settings.internal_service_token
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Serviço não autorizado")
