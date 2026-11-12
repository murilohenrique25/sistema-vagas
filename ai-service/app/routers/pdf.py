"""PDF extraction router for resume parsing."""

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.resume import ExtractedResume
from app.services.pdf_extractor import extract_from_pdf, extract_text_from_pdf

logger = logging.getLogger(__name__)

router = APIRouter()

# Constants
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_PAGES = 10


@router.post("/extract-pdf", response_model=ExtractedResume)
async def extract_pdf(file: UploadFile = File(...)) -> ExtractedResume:
    """Extract structured resume data from a PDF file.

    Accepts a PDF file upload (multipart/form-data), validates the file,
    extracts text content, and uses LangChain/OpenAI to parse into
    structured resume data.

    Validations:
    - File must be a PDF (content type or extension check)
    - Max file size: 5 MB (returns 413)
    - Max pages: 10 (returns 422)

    Returns structured resume data with null for fields that cannot be extracted.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=422,
            detail="Only PDF files are accepted. Please upload a file with .pdf extension.",
        )

    if file.content_type and file.content_type != "application/pdf":
        raise HTTPException(
            status_code=422,
            detail="Invalid file content type. Only application/pdf is accepted.",
        )

    # Read file content
    file_bytes = await file.read()

    # Validate file size
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds the maximum allowed size of 5 MB. Received: {len(file_bytes) / (1024 * 1024):.1f} MB.",
        )

    # Validate it's a real PDF (check magic bytes)
    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=422,
            detail="The file does not appear to be a valid PDF document.",
        )

    # Validate page count
    try:
        _text, num_pages = extract_text_from_pdf(file_bytes)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Failed to read PDF: {e}",
        )

    if num_pages > MAX_PAGES:
        raise HTTPException(
            status_code=422,
            detail=f"PDF exceeds the maximum of {MAX_PAGES} pages. Received: {num_pages} pages.",
        )

    # Extract structured data
    try:
        result = await extract_from_pdf(file_bytes)
    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="PDF extraction timed out. Please try again later.",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=str(e),
        )
    except Exception:
        logger.exception("Unexpected error during PDF extraction")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during PDF extraction.",
        )

    return result
