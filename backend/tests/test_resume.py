"""Tests for Resume schemas, service, and routes."""

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.models.enums import DegreeLevel, FluencyLevel, ProficiencyLevel
from app.schemas.resume import (
    CertificationCreate,
    EducationCreate,
    ExperienceCreate,
    LanguageCreate,
    ResumeCreate,
    ResumeResponse,
    SkillCreate,
)


class TestExperienceCreate:
    """Tests for ExperienceCreate schema validation."""

    def test_valid_experience(self):
        """Valid experience is accepted."""
        exp = ExperienceCreate(
            company="Acme Corp",
            position="Developer",
            start_date=date(2020, 1, 1),
            end_date=date(2022, 12, 31),
            description="Built stuff",
        )
        assert exp.company == "Acme Corp"
        assert exp.position == "Developer"

    def test_experience_without_end_date(self):
        """Experience without end_date (current job) is valid."""
        exp = ExperienceCreate(
            company="Acme Corp",
            position="Developer",
            start_date=date(2020, 1, 1),
        )
        assert exp.end_date is None

    def test_description_max_2000_chars(self):
        """Description exceeding 2000 characters is rejected."""
        with pytest.raises(ValidationError, match="2000 caracteres"):
            ExperienceCreate(
                company="Acme Corp",
                position="Developer",
                start_date=date(2020, 1, 1),
                description="x" * 2001,
            )

    def test_description_exactly_2000_chars(self):
        """Description with exactly 2000 characters is accepted."""
        exp = ExperienceCreate(
            company="Acme Corp",
            position="Developer",
            start_date=date(2020, 1, 1),
            description="x" * 2000,
        )
        assert len(exp.description) == 2000


class TestEducationCreate:
    """Tests for EducationCreate schema validation."""

    def test_valid_education(self):
        """Valid education is accepted."""
        edu = EducationCreate(
            institution="Universidade ABC",
            course="Ciência da Computação",
            degree=DegreeLevel.bachelor,
            start_date=date(2016, 2, 1),
            end_date=date(2020, 12, 15),
        )
        assert edu.institution == "Universidade ABC"
        assert edu.degree == DegreeLevel.bachelor

    def test_education_without_end_date(self):
        """Education without end_date (ongoing) is valid."""
        edu = EducationCreate(
            institution="Universidade ABC",
            course="Mestrado",
            degree=DegreeLevel.master,
            start_date=date(2023, 3, 1),
        )
        assert edu.end_date is None


class TestSkillCreate:
    """Tests for SkillCreate schema validation."""

    def test_valid_skill(self):
        """Valid skill is accepted."""
        skill = SkillCreate(name="Python", proficiency=ProficiencyLevel.advanced)
        assert skill.name == "Python"
        assert skill.proficiency == ProficiencyLevel.advanced


class TestCertificationCreate:
    """Tests for CertificationCreate schema validation."""

    def test_valid_certification(self):
        """Valid certification is accepted."""
        cert = CertificationCreate(
            name="AWS Solutions Architect",
            issuer="Amazon",
            obtained_at=date(2023, 6, 1),
        )
        assert cert.name == "AWS Solutions Architect"

    def test_certification_without_obtained_at(self):
        """Certification without date is valid."""
        cert = CertificationCreate(name="Cert", issuer="Issuer")
        assert cert.obtained_at is None


class TestLanguageCreate:
    """Tests for LanguageCreate schema validation."""

    def test_valid_language(self):
        """Valid language is accepted."""
        lang = LanguageCreate(language="Inglês", fluency=FluencyLevel.advanced)
        assert lang.language == "Inglês"
        assert lang.fluency == FluencyLevel.advanced


class TestResumeCreate:
    """Tests for ResumeCreate schema validation."""

    def _make_experience(self) -> ExperienceCreate:
        return ExperienceCreate(
            company="Acme", position="Dev", start_date=date(2020, 1, 1)
        )

    def _make_education(self) -> EducationCreate:
        return EducationCreate(
            institution="Uni",
            course="CS",
            degree=DegreeLevel.bachelor,
            start_date=date(2016, 1, 1),
        )

    def test_valid_resume_with_experience(self):
        """Resume with experience and no education is valid."""
        resume = ResumeCreate(
            full_name="João Silva",
            contact_email="joao@example.com",
            experiences=[self._make_experience()],
        )
        assert resume.full_name == "João Silva"

    def test_valid_resume_with_education(self):
        """Resume with education and no experience is valid."""
        resume = ResumeCreate(
            full_name="Maria Santos",
            contact_email="maria@example.com",
            educations=[self._make_education()],
        )
        assert resume.full_name == "Maria Santos"

    def test_valid_resume_with_both(self):
        """Resume with both experience and education is valid."""
        resume = ResumeCreate(
            full_name="Test User",
            contact_email="test@example.com",
            experiences=[self._make_experience()],
            educations=[self._make_education()],
        )
        assert len(resume.experiences) == 1
        assert len(resume.educations) == 1

    def test_no_experience_and_no_education_rejected(self):
        """Resume without any experience or education is rejected."""
        with pytest.raises(ValidationError, match="pelo menos uma experiência ou formação"):
            ResumeCreate(
                full_name="Test User",
                contact_email="test@example.com",
            )

    def test_full_name_max_200_chars(self):
        """Full name exceeding 200 characters is rejected."""
        with pytest.raises(ValidationError, match="200 caracteres"):
            ResumeCreate(
                full_name="x" * 201,
                contact_email="test@example.com",
                experiences=[self._make_experience()],
            )

    def test_full_name_exactly_200_chars(self):
        """Full name with exactly 200 characters is accepted."""
        resume = ResumeCreate(
            full_name="x" * 200,
            contact_email="test@example.com",
            experiences=[self._make_experience()],
        )
        assert len(resume.full_name) == 200

    def test_full_name_empty_rejected(self):
        """Empty full name is rejected."""
        with pytest.raises(ValidationError, match="obrigatório"):
            ResumeCreate(
                full_name="   ",
                contact_email="test@example.com",
                experiences=[self._make_experience()],
            )

    def test_invalid_email_rejected(self):
        """Invalid email format is rejected."""
        with pytest.raises(ValidationError):
            ResumeCreate(
                full_name="Test User",
                contact_email="not-an-email",
                experiences=[self._make_experience()],
            )

    def test_experiences_max_30(self):
        """More than 30 experiences are rejected."""
        with pytest.raises(ValidationError, match="30 experiências"):
            ResumeCreate(
                full_name="Test User",
                contact_email="test@example.com",
                experiences=[self._make_experience() for _ in range(31)],
            )

    def test_educations_max_30(self):
        """More than 30 educations are rejected."""
        with pytest.raises(ValidationError, match="30 formações"):
            ResumeCreate(
                full_name="Test User",
                contact_email="test@example.com",
                experiences=[self._make_experience()],
                educations=[self._make_education() for _ in range(31)],
            )

    def test_skills_max_30(self):
        """More than 30 skills are rejected."""
        with pytest.raises(ValidationError, match="30 habilidades"):
            ResumeCreate(
                full_name="Test User",
                contact_email="test@example.com",
                experiences=[self._make_experience()],
                skills=[
                    SkillCreate(name=f"Skill{i}", proficiency=ProficiencyLevel.beginner)
                    for i in range(31)
                ],
            )

    def test_certifications_max_30(self):
        """More than 30 certifications are rejected."""
        with pytest.raises(ValidationError, match="30 certificações"):
            ResumeCreate(
                full_name="Test User",
                contact_email="test@example.com",
                experiences=[self._make_experience()],
                certifications=[
                    CertificationCreate(name=f"Cert{i}", issuer="Issuer")
                    for i in range(31)
                ],
            )

    def test_languages_max_30(self):
        """More than 30 languages are rejected."""
        with pytest.raises(ValidationError, match="30 idiomas"):
            ResumeCreate(
                full_name="Test User",
                contact_email="test@example.com",
                experiences=[self._make_experience()],
                languages=[
                    LanguageCreate(language=f"Lang{i}", fluency=FluencyLevel.basic)
                    for i in range(31)
                ],
            )

    def test_optional_fields(self):
        """Optional fields (phone, location, summary) can be omitted."""
        resume = ResumeCreate(
            full_name="Test User",
            contact_email="test@example.com",
            experiences=[self._make_experience()],
        )
        assert resume.phone is None
        assert resume.location is None
        assert resume.summary is None

    def test_full_resume_with_all_sections(self):
        """Resume with all sections populated is valid."""
        resume = ResumeCreate(
            full_name="Full User",
            contact_email="full@example.com",
            phone="+5511999999999",
            location="São Paulo, SP",
            summary="Desenvolvedor experiente",
            experiences=[self._make_experience()],
            educations=[self._make_education()],
            skills=[SkillCreate(name="Python", proficiency=ProficiencyLevel.expert)],
            certifications=[CertificationCreate(name="AWS", issuer="Amazon")],
            languages=[LanguageCreate(language="Inglês", fluency=FluencyLevel.advanced)],
        )
        assert len(resume.experiences) == 1
        assert len(resume.educations) == 1
        assert len(resume.skills) == 1
        assert len(resume.certifications) == 1
        assert len(resume.languages) == 1


class TestResumeService:
    """Tests for ResumeService."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()
        session.refresh = AsyncMock()
        return session

    def _make_resume_data(self) -> ResumeCreate:
        return ResumeCreate(
            full_name="João Silva",
            contact_email="joao@example.com",
            phone="+5511999999999",
            location="São Paulo",
            experiences=[
                ExperienceCreate(
                    company="Acme Corp",
                    position="Developer",
                    start_date=date(2020, 1, 1),
                    description="Built great things",
                )
            ],
            educations=[
                EducationCreate(
                    institution="Universidade ABC",
                    course="CS",
                    degree=DegreeLevel.bachelor,
                    start_date=date(2016, 1, 1),
                )
            ],
            skills=[SkillCreate(name="Python", proficiency=ProficiencyLevel.advanced)],
        )

    async def test_get_resume_returns_none_when_not_found(self, mock_session):
        """get_resume returns None when user has no resume."""
        from app.services.resume_service import ResumeService

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ResumeService(mock_session)
        result = await service.get_resume(uuid.uuid4())
        assert result is None

    async def test_get_resume_returns_resume_when_exists(self, mock_session):
        """get_resume returns the resume when it exists."""
        from app.models.resume import Resume
        from app.services.resume_service import ResumeService

        mock_resume = MagicMock(spec=Resume)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_resume
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ResumeService(mock_session)
        result = await service.get_resume(uuid.uuid4())
        assert result is mock_resume

    async def test_create_resume_adds_to_session(self, mock_session):
        """create_or_update_resume adds a new resume to the session when none exists."""
        from app.services.resume_service import ResumeService

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ResumeService(mock_session)
        data = self._make_resume_data()
        resume, created = await service.create_or_update_resume(uuid.uuid4(), data)

        mock_session.add.assert_called_once()
        assert created is True

    async def test_update_resume_clears_sections(self, mock_session):
        """create_or_update_resume clears existing sections on update."""
        from app.models.resume import Resume
        from app.services.resume_service import ResumeService

        user_id = uuid.uuid4()
        existing_resume = MagicMock(spec=Resume)
        existing_resume.id = uuid.uuid4()
        existing_resume.experiences = MagicMock()
        existing_resume.educations = MagicMock()
        existing_resume.skills = MagicMock()
        existing_resume.certifications = MagicMock()
        existing_resume.languages = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_resume
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ResumeService(mock_session)
        data = self._make_resume_data()
        resume, created = await service.create_or_update_resume(user_id, data)

        # Verify that existing sections were cleared
        existing_resume.experiences.clear.assert_called_once()
        existing_resume.educations.clear.assert_called_once()
        existing_resume.skills.clear.assert_called_once()
        existing_resume.certifications.clear.assert_called_once()
        existing_resume.languages.clear.assert_called_once()
        assert created is False


class TestResumeRoutes:
    """Tests for resume API routes authorization."""

    def test_require_candidate_rejects_employer(self):
        """Employer role is rejected when accessing resume endpoints."""
        from fastapi import HTTPException
        from app.api.v1.routes.resumes import _require_candidate
        from app.api.v1.dependencies import CurrentUser

        employer = CurrentUser(user_id=uuid.uuid4(), role="employer")
        with pytest.raises(HTTPException) as exc_info:
            _require_candidate(employer)
        assert exc_info.value.status_code == 403

    def test_require_candidate_accepts_candidate(self):
        """Candidate role is accepted."""
        from app.api.v1.routes.resumes import _require_candidate
        from app.api.v1.dependencies import CurrentUser

        candidate = CurrentUser(user_id=uuid.uuid4(), role="candidate")
        # Should not raise
        _require_candidate(candidate)
