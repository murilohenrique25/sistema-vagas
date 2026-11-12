"""FastAPI application factory and configuration."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import v1_router
from app.core.config import settings
from app.core.redis import close_redis_pool, get_redis, init_redis_pool
from sqlalchemy import text
import httpx


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    await init_redis_pool()
    yield
    # Shutdown
    await close_redis_pool()
    from app.core.database import engine

    await engine.dispose()


def create_app() -> FastAPI:
    """Application factory that creates and configures the FastAPI instance."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "API da Plataforma Inteligente de Recrutamento com IA. "
            "Gerencia vagas, candidaturas, currículos, análises de IA e carteira em reais."
        ),
        debug=settings.debug,
        lifespan=lifespan,
        openapi_url=settings.openapi_url,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        openapi_tags=[
            {"name": "health", "description": "Health check endpoints"},
            {"name": "auth", "description": "Autenticação e registro de usuários"},
            {"name": "jobs", "description": "Cadastro e gerenciamento de vagas"},
            {"name": "resumes", "description": "Gestão de currículos"},
            {"name": "applications", "description": "Processo de candidatura"},
            {"name": "ai", "description": "Funcionalidades de inteligência artificial"},
            {"name": "payments", "description": "Carteira e Checkout Pro"},
            {"name": "notifications", "description": "Sistema de notificações"},
            {"name": "admin", "description": "Painel administrativo"},
        ],
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include versioned router
    app.include_router(v1_router)

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.middleware("http")
    async def rate_limit_sensitive_routes(request, call_next):
        limits = {
            "/v1/auth/login": 10, "/v1/auth/register": 5,
            "/v1/auth/email-verification/request": 3,
            "/v1/auth/email-verification/confirm": 10,
            "/v1/auth/password/forgot": 3,
            "/v1/auth/password/reset": 10,
            "/v1/account": 5,
            "/v1/jobs": 10,
            "/v1/payments/checkout/wallet": 10,
            "/v1/ai/analyze-candidates": 20, "/v1/ai/job-matching": 20,
        }
        path = request.url.path
        method = request.method.upper()
        limit = limits.get(path)
        # Browsing/searching jobs is public and must not share the publishing quota.
        if path == "/v1/jobs" and method != "POST":
            limit = None
        if method == "POST" and path.startswith("/v1/jobs/") and path.endswith("/reports"):
            limit = 5
        if limit:
            client_ip = request.client.host if request.client else "unknown"
            key = f"rate:{method}:{path}:{client_ip}"
            try:
                redis = get_redis()
                count = await redis.incr(key)
                if count == 1:
                    await redis.expire(key, 60)
                if count > limit:
                    return JSONResponse(status_code=429, content={"detail": "Muitas solicitações. Tente novamente em instantes."})
            except Exception:
                pass
        return await call_next(request)

    @app.get("/health", tags=["health"])
    async def root_health():
        """Root health check endpoint."""
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
        }

    @app.get("/ready", tags=["health"])
    async def readiness():
        from app.core.database import async_session_factory
        from app.core.redis import get_redis
        checks = {"database": False, "redis": False, "ai": False}
        try:
            async with async_session_factory() as session:
                await session.execute(text("SELECT 1"))
            checks["database"] = True
        except Exception:
            pass
        try:
            checks["redis"] = bool(await get_redis().ping())
        except Exception:
            pass
        try:
            headers = {"X-Internal-Service-Token": settings.internal_service_token} if settings.internal_service_token else {}
            async with httpx.AsyncClient(timeout=3) as client:
                response = await client.get(f"{settings.ai_service_url}/health", headers=headers)
            checks["ai"] = response.status_code == 200
        except Exception:
            pass
        if not all(checks.values()):
            from fastapi import HTTPException
            raise HTTPException(status_code=503, detail=checks)
        return {"status": "ready", "dependencies": checks}

    return app


app = create_app()
