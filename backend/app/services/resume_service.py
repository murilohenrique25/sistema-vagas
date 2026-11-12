"""Resume service with CRUD operations for resumes and all sections."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume import (
    Certification,
    Education,
    Experience,
    Language,
    Resume,
    Skill,
)
from app.schemas.resume import ResumeCreate


class ResumeService:
    """Service handling resume operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_resume(self, user_id: UUID) -> Resume | None:
        """Get the user's resume with all sections loaded.

        Returns None if no resume exists for the user.
        """
        result = await self.session.execute(
            select(Resume).where(Resume.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_or_update_resume(self, user_id: UUID, data: ResumeCreate) -> tuple[Resume, bool]:
        """Create or update (upsert) the user's resume with all sections.

        If a resume already exists for the user, it replaces all sections.

        Returns:
            Tuple of (resume, created) where created is True if a new resume was created.
        """
        existing_resume = await self.get_resume(user_id)

        if existing_resume:
            resume = await self._update_resume(existing_resume, data)
            return resume, False
        else:
            resume = await self._create_resume(user_id, data)
            return resume, True

    async def _create_resume(self, user_id: UUID, data: ResumeCreate) -> Resume:
        """Create a new resume with all sections."""
        resume = Resume(
            user_id=user_id,
            full_name=data.full_name,
            contact_email=data.contact_email,
            phone=data.phone,
            location=data.location,
            summary=data.summary,
        )
        self.session.add(resume)
        await self.session.flush()

        # Add all sections
        self._add_experiences(resume, data)
        self._add_educations(resume, data)
        self._add_skills(resume, data)
        self._add_certifications(resume, data)
        self._add_languages(resume, data)

        await self.session.flush()
        await self.session.refresh(resume)
        return resume

    async def _update_resume(self, resume: Resume, data: ResumeCreate) -> Resume:
        """Update existing resume, replacing all sections."""
        # Update main fields
        resume.full_name = data.full_name
        resume.contact_email = data.contact_email
        resume.phone = data.phone
        resume.location = data.location
        resume.summary = data.summary

        # Clear existing sections (cascade handles deletion)
        resume.experiences.clear()
        resume.educations.clear()
        resume.skills.clear()
        resume.certifications.clear()
        resume.languages.clear()

        await self.session.flush()

        # Add new sections
        self._add_experiences(resume, data)
        self._add_educations(resume, data)
        self._add_skills(resume, data)
        self._add_certifications(resume, data)
        self._add_languages(resume, data)

        await self.session.flush()
        await self.session.refresh(resume)
        return resume

    def _add_experiences(self, resume: Resume, data: ResumeCreate) -> None:
        """Add experience entries to the resume."""
        for i, exp in enumerate(data.experiences):
            experience = Experience(
                resume_id=resume.id,
                company=exp.company,
                position=exp.position,
                start_date=exp.start_date,
                end_date=exp.end_date,
                description=exp.description,
                sort_order=i,
            )
            resume.experiences.append(experience)

    def _add_educations(self, resume: Resume, data: ResumeCreate) -> None:
        """Add education entries to the resume."""
        for i, edu in enumerate(data.educations):
            education = Education(
                resume_id=resume.id,
                institution=edu.institution,
                course=edu.course,
                degree=edu.degree,
                start_date=edu.start_date,
                end_date=edu.end_date,
                sort_order=i,
            )
            resume.educations.append(education)

    def _add_skills(self, resume: Resume, data: ResumeCreate) -> None:
        """Add skill entries to the resume."""
        for skill_data in data.skills:
            skill = Skill(
                resume_id=resume.id,
                name=skill_data.name,
                proficiency=skill_data.proficiency,
            )
            resume.skills.append(skill)

    def _add_certifications(self, resume: Resume, data: ResumeCreate) -> None:
        """Add certification entries to the resume."""
        for cert_data in data.certifications:
            certification = Certification(
                resume_id=resume.id,
                name=cert_data.name,
                issuer=cert_data.issuer,
                obtained_at=cert_data.obtained_at,
            )
            resume.certifications.append(certification)

    def _add_languages(self, resume: Resume, data: ResumeCreate) -> None:
        """Add language entries to the resume."""
        for lang_data in data.languages:
            language = Language(
                resume_id=resume.id,
                language=lang_data.language,
                fluency=lang_data.fluency,
            )
            resume.languages.append(language)
