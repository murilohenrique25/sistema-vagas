"""Resume routes: create/update and retrieve resumes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import CurrentUser, get_current_user
from app.core.database import get_session
from app.schemas.resume import PDFImportResponse, ResumeCreate, ResumeResponse
from app.services.ai_service_client import (
    AIServiceClient,
    AIServiceError,
    AIServiceTimeoutError,
    AIServiceUnavailableError,
)
from app.services.resume_service import ResumeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resumes", tags=["resumes"])

# PDF import constants
MAX_PDF_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_PDF_PAGES = 10
PDF_MAGIC_BYTES = b"%PDF"


def _require_candidate(current_user: CurrentUser) -> None:
    """Ensure the current user is a candidate."""
    if current_user.role != "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas candidatos podem acessar currículos",
        )


@router.get(
    "/me",
    response_model=ResumeResponse,
    summary="Obter currículo do candidato autenticado",
    description="Retorna o currículo completo do candidato autenticado com todas as seções.",
)
async def get_my_resume(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ResumeResponse:
    """Get the authenticated candidate's resume."""
    _require_candidate(current_user)

    service = ResumeService(session)
    resume = await service.get_resume(current_user.id)

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Currículo não encontrado",
        )

    return ResumeResponse.model_validate(resume)


@router.get(
    "/candidate/{candidate_id}",
    response_model=ResumeResponse,
    summary="Ver currículo de um candidato (empregador)",
    description="Permite ao empregador visualizar o currículo de um candidato que se candidatou às suas vagas.",
)
async def get_candidate_resume(
    candidate_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ResumeResponse:
    """Get a candidate's resume (employer access)."""
    from uuid import UUID

    if current_user.role not in ("employer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas empregadores podem visualizar currículos de candidatos",
        )

    service = ResumeService(session)
    resume = await service.get_resume(UUID(candidate_id))

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Currículo não encontrado para este candidato",
        )

    return ResumeResponse.model_validate(resume)


@router.post(
    "",
    response_model=ResumeResponse,
    summary="Criar ou atualizar currículo",
    description="Cria um novo currículo ou atualiza o existente do candidato autenticado.",
    responses={
        201: {"description": "Currículo criado com sucesso"},
        200: {"description": "Currículo atualizado com sucesso"},
    },
)
async def create_or_update_resume(
    data: ResumeCreate,
    response: Response,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ResumeResponse:
    """Create or update the authenticated candidate's resume."""
    _require_candidate(current_user)

    service = ResumeService(session)
    resume, created = await service.create_or_update_resume(current_user.id, data)

    if created:
        response.status_code = status.HTTP_201_CREATED
    else:
        response.status_code = status.HTTP_200_OK

    return ResumeResponse.model_validate(resume)



def _count_pdf_pages(file_bytes: bytes) -> int | None:
    """Count pages in a PDF by inspecting content.

    Uses a simple heuristic based on /Type /Page occurrences.
    Returns None if page count cannot be determined.
    """
    try:
        # Count /Type /Page entries (each page object has this)
        # This is a simple heuristic; more robust parsing would use a PDF library
        content = file_bytes
        count = 0
        idx = 0
        while True:
            # Look for /Type /Page (but not /Type /Pages which is the page tree)
            idx = content.find(b"/Type /Page", idx)
            if idx == -1:
                break
            # Check it's not /Type /Pages
            after = content[idx : idx + 15]
            if b"/Type /Pages" not in after:
                count += 1
            idx += 11
        return count if count > 0 else None
    except Exception:
        return None


@router.post(
    "/import-pdf",
    response_model=PDFImportResponse,
    summary="Importar currículo via PDF com extração por IA",
    description=(
        "Faz upload de um arquivo PDF de currículo e utiliza o serviço de IA "
        "para extrair dados estruturados. Os dados extraídos são retornados "
        "para pré-preenchimento do formulário. Campos que a IA não conseguir "
        "extrair serão retornados como null."
    ),
    responses={
        200: {"description": "Dados extraídos com sucesso (pode ter campos null)"},
        400: {"description": "Arquivo inválido (não é PDF, tamanho excedido, etc.)"},
        503: {"description": "Serviço de IA indisponível - preenchimento manual necessário"},
        504: {"description": "Timeout na extração - preenchimento manual necessário"},
    },
)
async def import_pdf(
    file: UploadFile = File(..., description="Arquivo PDF do currículo (max 5MB, max 10 páginas)"),
    current_user: CurrentUser = Depends(get_current_user),
) -> PDFImportResponse:
    """Import resume from PDF using AI extraction.

    Validates the uploaded file (extension, header, size, pages) and sends
    it to the AI microservice for structured data extraction.

    If the AI service times out (60s) or is unavailable, returns a response
    indicating fallback to manual form filling.
    """
    _require_candidate(current_user)

    # Validate file extension
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas arquivos com extensão .pdf são aceitos",
        )

    # Read file content
    file_bytes = await file.read()

    # Validate file size (max 5MB)
    if len(file_bytes) > MAX_PDF_SIZE_BYTES:
        size_mb = len(file_bytes) / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Arquivo excede o tamanho máximo de 5 MB. Tamanho recebido: {size_mb:.1f} MB",
        )

    # Validate PDF header (magic bytes)
    if not file_bytes.startswith(PDF_MAGIC_BYTES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo não é um PDF válido. O cabeçalho do arquivo não corresponde ao formato PDF",
        )

    # Validate page count (max 10 pages)
    page_count = _count_pdf_pages(file_bytes)
    if page_count is not None and page_count > MAX_PDF_PAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PDF excede o máximo de {MAX_PDF_PAGES} páginas. Páginas detectadas: {page_count}",
        )

    # Call AI service for extraction
    ai_client = AIServiceClient()

    try:
        extracted_data = await ai_client.extract_pdf(
            file_bytes=file_bytes,
            filename=file.filename,
        )

        # Map AI service response to our response schema
        return PDFImportResponse(
            personal_data={
                "full_name": extracted_data.get("personal_data", {}).get("full_name"),
                "contact_email": extracted_data.get("personal_data", {}).get("contact_email"),
                "phone": extracted_data.get("personal_data", {}).get("phone"),
                "location": extracted_data.get("personal_data", {}).get("location"),
            },
            experiences=[
                {
                    "company": exp.get("company"),
                    "position": exp.get("position"),
                    "start_date": exp.get("start_date"),
                    "end_date": exp.get("end_date"),
                    "description": exp.get("description"),
                }
                for exp in extracted_data.get("experiences", [])
            ],
            educations=[
                {
                    "institution": edu.get("institution"),
                    "course": edu.get("course"),
                    "degree": edu.get("degree"),
                    "start_date": edu.get("start_date"),
                    "end_date": edu.get("end_date"),
                }
                for edu in extracted_data.get("educations", [])
            ],
            skills=[
                {
                    "name": skill.get("name"),
                    "proficiency": skill.get("proficiency"),
                }
                for skill in extracted_data.get("skills", [])
            ],
            certifications=[
                {
                    "name": cert.get("name"),
                    "issuer": cert.get("issuer"),
                    "obtained_at": cert.get("obtained_at"),
                }
                for cert in extracted_data.get("certifications", [])
            ],
            languages=[
                {
                    "language": lang.get("language"),
                    "fluency": lang.get("fluency"),
                }
                for lang in extracted_data.get("languages", [])
            ],
            extraction_complete=True,
            message="Dados extraídos com sucesso. Revise e confirme as informações.",
        )

    except AIServiceTimeoutError:
        logger.warning("AI service timed out for PDF import by user %s", current_user.id)
        return PDFImportResponse(
            extraction_complete=False,
            message=(
                "A extração não pôde ser concluída dentro do tempo limite de 60 segundos. "
                "Você pode tentar novamente ou preencher o currículo manualmente."
            ),
        )

    except AIServiceUnavailableError:
        logger.error("AI service unavailable for PDF import by user %s", current_user.id)
        return PDFImportResponse(
            extraction_complete=False,
            message=(
                "O serviço de extração está indisponível no momento. "
                "Você pode tentar novamente mais tarde ou preencher o currículo manualmente."
            ),
        )

    except AIServiceError as e:
        logger.error(
            "AI service error during PDF import for user %s: %s",
            current_user.id,
            e.message,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro no serviço de extração: {e.message}",
        )
