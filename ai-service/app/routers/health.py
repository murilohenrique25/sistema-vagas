from fastapi import APIRouter

from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint for the AI microservice.

    Returns service status, configuration info (without secrets),
    and dependency readiness checks.
    """
    dependencies = {
        "openai": bool(settings.openai_api_key),
        "backend": bool(settings.backend_base_url),
    }

    # Overall status is healthy only if critical dependencies are configured
    all_configured = all(dependencies.values())

    return {
        "status": "healthy" if all_configured else "degraded",
        "service": settings.service_name,
        "version": settings.service_version,
        "openai_model": settings.openai_model,
        "openai_configured": dependencies["openai"],
        "backend_url": settings.backend_base_url,
        "backend_configured": dependencies["backend"],
        "dependencies": dependencies,
    }
