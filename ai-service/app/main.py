from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import ai, health, pdf
from app.security import require_internal_service

app = FastAPI(
    title="AI Recruitment Service",
    description="Microsserviço de IA para extração de PDF, análise de candidatos e compatibilidade de vagas",
    version=settings.service_version,
)

# CORS middleware for internal communication with backend principal
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.backend_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(ai.router, dependencies=[Depends(require_internal_service)])
app.include_router(pdf.router, dependencies=[Depends(require_internal_service)])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.ai_service_host,
        port=settings.ai_service_port,
        reload=True,
    )
