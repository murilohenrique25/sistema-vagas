"""Pydantic models for structured resume extraction."""

from pydantic import BaseModel, Field


class PersonalData(BaseModel):
    """Personal information extracted from a resume."""

    full_name: str | None = Field(None, description="Candidate's full name")
    contact_email: str | None = Field(None, description="Contact email address")
    phone: str | None = Field(None, description="Phone number")
    location: str | None = Field(None, description="City/State or full address")


class ExperienceData(BaseModel):
    """Professional experience entry extracted from a resume."""

    company: str | None = Field(None, description="Company name")
    position: str | None = Field(None, description="Job title/position")
    start_date: str | None = Field(None, description="Start date (format: YYYY-MM or YYYY-MM-DD)")
    end_date: str | None = Field(None, description="End date (format: YYYY-MM or YYYY-MM-DD, null if current)")
    description: str | None = Field(None, description="Description of responsibilities and achievements")


class EducationData(BaseModel):
    """Education entry extracted from a resume."""

    institution: str | None = Field(None, description="Educational institution name")
    course: str | None = Field(None, description="Course or field of study")
    degree: str | None = Field(None, description="Degree level (e.g., bachelor, master, doctorate)")
    start_date: str | None = Field(None, description="Start date (format: YYYY-MM or YYYY-MM-DD)")
    end_date: str | None = Field(None, description="End date (format: YYYY-MM or YYYY-MM-DD)")


class SkillData(BaseModel):
    """Skill entry extracted from a resume."""

    name: str | None = Field(None, description="Skill name")
    proficiency: str | None = Field(None, description="Proficiency level (beginner, intermediate, advanced, expert)")


class CertificationData(BaseModel):
    """Certification entry extracted from a resume."""

    name: str | None = Field(None, description="Certification name")
    issuer: str | None = Field(None, description="Issuing organization")
    obtained_at: str | None = Field(None, description="Date obtained (format: YYYY-MM or YYYY-MM-DD)")


class LanguageData(BaseModel):
    """Language entry extracted from a resume."""

    language: str | None = Field(None, description="Language name")
    fluency: str | None = Field(None, description="Fluency level (basic, intermediate, advanced, native)")


class ExtractedResume(BaseModel):
    """Complete structured data extracted from a resume PDF."""

    personal_data: PersonalData = Field(default_factory=PersonalData)
    experiences: list[ExperienceData] = Field(default_factory=list)
    educations: list[EducationData] = Field(default_factory=list)
    skills: list[SkillData] = Field(default_factory=list)
    certifications: list[CertificationData] = Field(default_factory=list)
    languages: list[LanguageData] = Field(default_factory=list)
