"""Resume schemas for request/response validation."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.enums import DegreeLevel, FluencyLevel, ProficiencyLevel
from app.schemas.base import BaseSchema, TimestampSchema


class ExperienceCreate(BaseModel):
    """Schema for creating an experience entry."""

    company: str
    position: str
    start_date: date
    end_date: date | None = None
    description: str | None = None

    @field_validator("description")
    @classmethod
    def validate_description_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 2000:
            raise ValueError("Descrição deve ter no máximo 2000 caracteres")
        return v


class EducationCreate(BaseModel):
    """Schema for creating an education entry."""

    institution: str
    course: str
    degree: DegreeLevel
    start_date: date
    end_date: date | None = None


class SkillCreate(BaseModel):
    """Schema for creating a skill entry."""

    name: str
    proficiency: ProficiencyLevel


class CertificationCreate(BaseModel):
    """Schema for creating a certification entry."""

    name: str
    issuer: str
    obtained_at: date | None = None


class LanguageCreate(BaseModel):
    """Schema for creating a language entry."""

    language: str
    fluency: FluencyLevel


class ResumeCreate(BaseModel):
    """Schema for creating or updating a resume."""

    full_name: str
    contact_email: EmailStr
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    experiences: list[ExperienceCreate] = []
    educations: list[EducationCreate] = []
    skills: list[SkillCreate] = []
    certifications: list[CertificationCreate] = []
    languages: list[LanguageCreate] = []

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        if len(v) > 200:
            raise ValueError("Nome completo deve ter no máximo 200 caracteres")
        if not v.strip():
            raise ValueError("Nome completo é obrigatório")
        return v.strip()

    @field_validator("experiences")
    @classmethod
    def validate_experiences_max(cls, v: list[ExperienceCreate]) -> list[ExperienceCreate]:
        if len(v) > 30:
            raise ValueError("Máximo de 30 experiências permitidas")
        return v

    @field_validator("educations")
    @classmethod
    def validate_educations_max(cls, v: list[EducationCreate]) -> list[EducationCreate]:
        if len(v) > 30:
            raise ValueError("Máximo de 30 formações permitidas")
        return v

    @field_validator("skills")
    @classmethod
    def validate_skills_max(cls, v: list[SkillCreate]) -> list[SkillCreate]:
        if len(v) > 30:
            raise ValueError("Máximo de 30 habilidades permitidas")
        return v

    @field_validator("certifications")
    @classmethod
    def validate_certifications_max(cls, v: list[CertificationCreate]) -> list[CertificationCreate]:
        if len(v) > 30:
            raise ValueError("Máximo de 30 certificações permitidas")
        return v

    @field_validator("languages")
    @classmethod
    def validate_languages_max(cls, v: list[LanguageCreate]) -> list[LanguageCreate]:
        if len(v) > 30:
            raise ValueError("Máximo de 30 idiomas permitidos")
        return v

    @model_validator(mode="after")
    def validate_at_least_one_experience_or_education(self) -> "ResumeCreate":
        if not self.experiences and not self.educations:
            raise ValueError("É necessário pelo menos uma experiência ou formação")
        return self


# Response schemas


class ExperienceResponse(BaseSchema):
    """Schema for experience in responses."""

    id: UUID
    company: str
    position: str
    start_date: date
    end_date: date | None = None
    description: str | None = None
    sort_order: int


class EducationResponse(BaseSchema):
    """Schema for education in responses."""

    id: UUID
    institution: str
    course: str
    degree: DegreeLevel
    start_date: date
    end_date: date | None = None
    sort_order: int


class SkillResponse(BaseSchema):
    """Schema for skill in responses."""

    id: UUID
    name: str
    proficiency: ProficiencyLevel


class CertificationResponse(BaseSchema):
    """Schema for certification in responses."""

    id: UUID
    name: str
    issuer: str
    obtained_at: date | None = None


class LanguageResponse(BaseSchema):
    """Schema for language in responses."""

    id: UUID
    language: str
    fluency: FluencyLevel


class ResumeResponse(TimestampSchema):
    """Schema for resume responses."""

    id: UUID
    user_id: UUID
    full_name: str
    contact_email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    experiences: list[ExperienceResponse] = []
    educations: list[EducationResponse] = []
    skills: list[SkillResponse] = []
    certifications: list[CertificationResponse] = []
    languages: list[LanguageResponse] = []


# PDF Import schemas


class PersonalDataExtracted(BaseModel):
    """Personal data extracted from PDF by AI."""

    full_name: str | None = None
    contact_email: str | None = None
    phone: str | None = None
    location: str | None = None


class ExperienceExtracted(BaseModel):
    """Experience entry extracted from PDF by AI."""

    company: str | None = None
    position: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None


class EducationExtracted(BaseModel):
    """Education entry extracted from PDF by AI."""

    institution: str | None = None
    course: str | None = None
    degree: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class SkillExtracted(BaseModel):
    """Skill entry extracted from PDF by AI."""

    name: str | None = None
    proficiency: str | None = None


class CertificationExtracted(BaseModel):
    """Certification entry extracted from PDF by AI."""

    name: str | None = None
    issuer: str | None = None
    obtained_at: str | None = None


class LanguageExtracted(BaseModel):
    """Language entry extracted from PDF by AI."""

    language: str | None = None
    fluency: str | None = None


class PDFImportResponse(BaseModel):
    """Response from PDF import containing extracted resume data for form pre-fill.

    Fields with null values indicate the AI could not extract that data,
    and should be highlighted for manual completion.
    """

    personal_data: PersonalDataExtracted = Field(default_factory=PersonalDataExtracted)
    experiences: list[ExperienceExtracted] = Field(default_factory=list)
    educations: list[EducationExtracted] = Field(default_factory=list)
    skills: list[SkillExtracted] = Field(default_factory=list)
    certifications: list[CertificationExtracted] = Field(default_factory=list)
    languages: list[LanguageExtracted] = Field(default_factory=list)
    extraction_complete: bool = Field(
        default=True,
        description="Indicates if the extraction completed successfully. False means fallback to manual.",
    )
    message: str | None = Field(
        default=None,
        description="Optional message about the extraction result (e.g., timeout warning).",
    )


class PDFImportErrorResponse(BaseModel):
    """Error response for PDF import validation failures."""

    detail: str
    error_code: str | None = None
