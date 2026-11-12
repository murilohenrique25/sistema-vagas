"""PDF extraction service using pdfplumber and LangChain."""

import asyncio
import io
import logging

import pdfplumber
from langchain_core.prompts import ChatPromptTemplate

from app.config import settings
from app.schemas.resume import (
    CertificationData,
    EducationData,
    ExperienceData,
    ExtractedResume,
    LanguageData,
    PersonalData,
    SkillData,
)
from app.services.llm import get_llm

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an expert resume parser. Extract structured data from the resume text below.
Return a JSON object with the following structure. Use null for any field you cannot determine.

{{
  "personal_data": {{
    "full_name": "string or null",
    "contact_email": "string or null",
    "phone": "string or null",
    "location": "string or null"
  }},
  "experiences": [
    {{
      "company": "string or null",
      "position": "string or null",
      "start_date": "YYYY-MM or YYYY-MM-DD or null",
      "end_date": "YYYY-MM or YYYY-MM-DD or null (null if current position)",
      "description": "string or null"
    }}
  ],
  "educations": [
    {{
      "institution": "string or null",
      "course": "string or null",
      "degree": "string or null (e.g., bachelor, master, doctorate, technical, high_school)",
      "start_date": "YYYY-MM or YYYY-MM-DD or null",
      "end_date": "YYYY-MM or YYYY-MM-DD or null"
    }}
  ],
  "skills": [
    {{
      "name": "string or null",
      "proficiency": "string or null (beginner, intermediate, advanced, expert)"
    }}
  ],
  "certifications": [
    {{
      "name": "string or null",
      "issuer": "string or null",
      "obtained_at": "YYYY-MM or YYYY-MM-DD or null"
    }}
  ],
  "languages": [
    {{
      "language": "string or null",
      "fluency": "string or null (basic, intermediate, advanced, native)"
    }}
  ]
}}

Important rules:
- Extract ALL experiences, educations, skills, certifications, and languages found.
- If a section is not present in the resume, return an empty list for that section.
- Use null for individual fields that cannot be determined.
- Return ONLY the JSON object, no additional text.""",
        ),
        ("human", "Resume text:\n\n{resume_text}"),
    ]
)


def extract_text_from_pdf(file_bytes: bytes) -> tuple[str, int]:
    """Extract text content from PDF bytes.

    Returns:
        Tuple of (extracted text, number of pages).

    Raises:
        ValueError: If the PDF cannot be read or has no extractable text.
    """
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            num_pages = len(pdf.pages)
            text_parts = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            text = "\n\n".join(text_parts)
    except Exception as e:
        raise ValueError(f"Failed to read PDF file: {e}") from e

    if not text.strip():
        raise ValueError("No extractable text found in the PDF")

    return text, num_pages


def _parse_llm_response(response_text: str) -> ExtractedResume:
    """Parse the LLM JSON response into an ExtractedResume model.

    Handles malformed responses gracefully by returning empty/null fields.
    """
    import json

    # Strip markdown code block markers if present
    content = response_text.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("LLM returned invalid JSON, returning empty resume")
        return ExtractedResume()

    # Parse personal data
    personal_raw = data.get("personal_data", {}) or {}
    personal_data = PersonalData(
        full_name=personal_raw.get("full_name"),
        contact_email=personal_raw.get("contact_email"),
        phone=personal_raw.get("phone"),
        location=personal_raw.get("location"),
    )

    # Parse experiences
    experiences = [
        ExperienceData(
            company=exp.get("company"),
            position=exp.get("position"),
            start_date=exp.get("start_date"),
            end_date=exp.get("end_date"),
            description=exp.get("description"),
        )
        for exp in (data.get("experiences") or [])
        if isinstance(exp, dict)
    ]

    # Parse educations
    educations = [
        EducationData(
            institution=edu.get("institution"),
            course=edu.get("course"),
            degree=edu.get("degree"),
            start_date=edu.get("start_date"),
            end_date=edu.get("end_date"),
        )
        for edu in (data.get("educations") or [])
        if isinstance(edu, dict)
    ]

    # Parse skills
    skills = [
        SkillData(
            name=skill.get("name"),
            proficiency=skill.get("proficiency"),
        )
        for skill in (data.get("skills") or [])
        if isinstance(skill, dict)
    ]

    # Parse certifications
    certifications = [
        CertificationData(
            name=cert.get("name"),
            issuer=cert.get("issuer"),
            obtained_at=cert.get("obtained_at"),
        )
        for cert in (data.get("certifications") or [])
        if isinstance(cert, dict)
    ]

    # Parse languages
    languages = [
        LanguageData(
            language=lang.get("language"),
            fluency=lang.get("fluency"),
        )
        for lang in (data.get("languages") or [])
        if isinstance(lang, dict)
    ]

    return ExtractedResume(
        personal_data=personal_data,
        experiences=experiences,
        educations=educations,
        skills=skills,
        certifications=certifications,
        languages=languages,
    )


async def extract_from_pdf(file_bytes: bytes) -> ExtractedResume:
    """Extract structured resume data from PDF bytes using LLM.

    Args:
        file_bytes: Raw PDF file content.

    Returns:
        ExtractedResume with structured data. Fields that cannot be extracted are null.

    Raises:
        ValueError: If the PDF cannot be read or parsed.
        TimeoutError: If extraction exceeds the configured timeout.
    """
    # Extract text from PDF (synchronous, but fast)
    text, _num_pages = extract_text_from_pdf(file_bytes)

    # Truncate very long texts to avoid token limits (approx 15k chars)
    max_chars = 15000
    if len(text) > max_chars:
        text = text[:max_chars]

    # Build the LLM chain
    llm = get_llm()
    chain = EXTRACTION_PROMPT | llm

    # Run with timeout
    try:
        result = await asyncio.wait_for(
            chain.ainvoke({"resume_text": text}),
            timeout=settings.pdf_extraction_timeout,
        )
    except asyncio.TimeoutError:
        raise TimeoutError("PDF extraction timed out after 60 seconds")

    # Parse the LLM response
    response_text = result.content if hasattr(result, "content") else str(result)
    return _parse_llm_response(response_text)
