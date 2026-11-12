"""Tests for the /match-jobs endpoint and job matching service."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.job_matcher import (
    JobMatchAnalysis,
    JobMatchResult,
    _format_candidate_profile,
    _format_jobs_data,
    match_candidate_to_jobs,
)


# --- Test Data Fixtures ---


@pytest.fixture
def sample_resume():
    """Sample candidate resume data."""
    return {
        "personal_data": {
            "full_name": "João Silva",
            "contact_email": "joao@email.com",
            "phone": "(11) 99999-0000",
            "location": "São Paulo, SP",
        },
        "experiences": [
            {
                "company": "Tech Corp",
                "position": "Desenvolvedor Python Senior",
                "start_date": "2020-01",
                "end_date": None,
                "description": "Desenvolvimento de APIs REST com FastAPI e Django",
            },
            {
                "company": "StartupXYZ",
                "position": "Desenvolvedor Backend",
                "start_date": "2018-03",
                "end_date": "2019-12",
                "description": "Microserviços em Python e Node.js",
            },
        ],
        "educations": [
            {
                "institution": "USP",
                "course": "Ciência da Computação",
                "degree": "bachelor",
                "start_date": "2014-02",
                "end_date": "2018-12",
            }
        ],
        "skills": [
            {"name": "Python", "proficiency": "expert"},
            {"name": "FastAPI", "proficiency": "advanced"},
            {"name": "PostgreSQL", "proficiency": "advanced"},
            {"name": "Docker", "proficiency": "intermediate"},
        ],
        "certifications": [
            {"name": "AWS Solutions Architect", "issuer": "Amazon", "obtained_at": "2022-06"}
        ],
        "languages": [
            {"language": "Português", "fluency": "native"},
            {"language": "Inglês", "fluency": "advanced"},
        ],
    }


@pytest.fixture
def sample_jobs():
    """Sample active jobs data."""
    return [
        {
            "id": "job-001",
            "title": "Desenvolvedor Python Senior",
            "modality": "remote",
            "location": "São Paulo, SP",
            "responsibilities": "Desenvolver APIs REST, implementar microserviços",
            "required_skills": "Python, FastAPI, PostgreSQL, Docker",
            "optional_skills": "Kubernetes, AWS",
            "contract_type": "clt",
            "salary_min": 12000.0,
            "salary_max": 18000.0,
        },
        {
            "id": "job-002",
            "title": "Data Engineer",
            "modality": "hybrid",
            "location": "Rio de Janeiro, RJ",
            "responsibilities": "Construir pipelines de dados, ETL, data lake",
            "required_skills": "Python, Spark, Airflow, SQL",
            "optional_skills": "Databricks, Snowflake",
            "contract_type": "clt",
            "salary_min": 15000.0,
            "salary_max": 22000.0,
        },
        {
            "id": "job-003",
            "title": "Designer UX/UI",
            "modality": "onsite",
            "location": "Curitiba, PR",
            "responsibilities": "Criar protótipos, realizar pesquisas com usuários",
            "required_skills": "Figma, Adobe XD, Design Thinking, UX Research",
            "optional_skills": "HTML, CSS",
            "contract_type": "pj",
            "salary_min": 8000.0,
            "salary_max": 12000.0,
        },
    ]


# --- Endpoint Tests ---


class TestMatchJobsEndpoint:
    """Tests for the POST /match-jobs endpoint."""

    @pytest.mark.asyncio
    async def test_match_jobs_rejects_empty_candidate_id(self):
        """Test that match-jobs rejects empty candidate_id."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/match-jobs",
                json={
                    "candidate_id": "",
                    "resume": {"experiences": []},
                    "active_jobs": [{"id": "job-1", "title": "Dev"}],
                },
            )

        assert response.status_code == 400
        assert "Candidate ID" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_match_jobs_rejects_no_jobs(self):
        """Test that match-jobs rejects when no active jobs are provided or available."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/match-jobs",
                json={
                    "candidate_id": "candidate-123",
                    "resume": {"experiences": [{"company": "X", "position": "Dev"}]},
                    "active_jobs": [],
                },
            )

        assert response.status_code == 400
        assert "Nenhuma vaga" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_match_jobs_returns_sorted_results(self, sample_resume, sample_jobs):
        """Test that results are sorted by compatibility descending."""
        mock_results = [
            {
                "job_id": "job-001",
                "compatibility_percentage": 85,
                "justifications": ["Forte match com Python e FastAPI"],
                "improvement_suggestions": [],
            },
            {
                "job_id": "job-002",
                "compatibility_percentage": 60,
                "justifications": ["Python relevante"],
                "improvement_suggestions": ["Aprender Spark"],
            },
        ]

        with patch(
            "app.routers.ai.match_candidate_to_jobs",
            new_callable=AsyncMock,
            return_value=mock_results,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/match-jobs",
                    json={
                        "candidate_id": "candidate-123",
                        "resume": sample_resume,
                        "active_jobs": sample_jobs,
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["candidate_id"] == "candidate-123"
        assert len(data["matches"]) == 2
        # Service returns sorted, endpoint passes through
        assert data["matches"][0]["compatibility_percentage"] >= data["matches"][1]["compatibility_percentage"]

    @pytest.mark.asyncio
    async def test_match_jobs_handles_timeout(self, sample_resume, sample_jobs):
        """Test that 408 is returned when analysis times out."""
        with patch(
            "app.routers.ai.match_candidate_to_jobs",
            new_callable=AsyncMock,
            side_effect=asyncio.TimeoutError(),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/match-jobs",
                    json={
                        "candidate_id": "candidate-123",
                        "resume": sample_resume,
                        "active_jobs": sample_jobs,
                    },
                )

        assert response.status_code == 408
        assert "30 segundos" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_match_jobs_handles_llm_error(self, sample_resume, sample_jobs):
        """Test that 500 is returned when LLM analysis fails."""
        with patch(
            "app.routers.ai.match_candidate_to_jobs",
            new_callable=AsyncMock,
            side_effect=Exception("OpenAI API error"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/match-jobs",
                    json={
                        "candidate_id": "candidate-123",
                        "resume": sample_resume,
                        "active_jobs": sample_jobs,
                    },
                )

        assert response.status_code == 500
        assert "Falha na análise" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_match_jobs_returns_empty_matches_when_no_compatibility(
        self, sample_resume, sample_jobs
    ):
        """Test that empty matches list is returned when no jobs match >= 10%."""
        with patch(
            "app.routers.ai.match_candidate_to_jobs",
            new_callable=AsyncMock,
            return_value=[],  # All filtered out
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/match-jobs",
                    json={
                        "candidate_id": "candidate-123",
                        "resume": sample_resume,
                        "active_jobs": sample_jobs,
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["matches"] == []

    @pytest.mark.asyncio
    async def test_match_jobs_fetches_from_backend_when_no_resume_provided(self):
        """Test that backend is called when resume is not provided directly."""
        mock_resume = {
            "personal_data": {"full_name": "Test User"},
            "experiences": [{"company": "X", "position": "Dev"}],
            "skills": [{"name": "Python", "proficiency": "advanced"}],
            "educations": [],
            "certifications": [],
            "languages": [],
        }

        with patch(
            "app.routers.ai.backend_client.get_resume",
            new_callable=AsyncMock,
            return_value=mock_resume,
        ) as mock_get_resume, patch(
            "app.routers.ai.match_candidate_to_jobs",
            new_callable=AsyncMock,
            return_value=[],
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/match-jobs",
                    json={
                        "candidate_id": "candidate-456",
                        "active_jobs": [{"id": "job-1", "title": "Dev Python"}],
                    },
                )

        assert response.status_code == 200
        mock_get_resume.assert_called_once_with("candidate-456")

    @pytest.mark.asyncio
    async def test_match_jobs_fetches_jobs_from_backend_when_not_provided(self):
        """Test that active jobs are fetched from backend when not provided."""
        mock_jobs = [
            {"id": "job-1", "title": "Dev Python", "required_skills": "Python"}
        ]

        with patch(
            "app.routers.ai.backend_client.get_active_jobs",
            new_callable=AsyncMock,
            return_value=mock_jobs,
        ) as mock_get_jobs, patch(
            "app.routers.ai.match_candidate_to_jobs",
            new_callable=AsyncMock,
            return_value=[],
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/match-jobs",
                    json={
                        "candidate_id": "candidate-789",
                        "resume": {
                            "personal_data": {"full_name": "Test"},
                            "experiences": [],
                            "skills": [{"name": "Python"}],
                        },
                    },
                )

        assert response.status_code == 200
        mock_get_jobs.assert_called_once()

    @pytest.mark.asyncio
    async def test_match_jobs_validates_response_structure(self, sample_resume, sample_jobs):
        """Test that response contains all required fields."""
        mock_results = [
            {
                "job_id": "job-001",
                "compatibility_percentage": 75,
                "justifications": ["Experiência sólida em Python", "AWS certificado"],
                "improvement_suggestions": ["Obter certificação Kubernetes"],
            },
        ]

        with patch(
            "app.routers.ai.match_candidate_to_jobs",
            new_callable=AsyncMock,
            return_value=mock_results,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/match-jobs",
                    json={
                        "candidate_id": "candidate-123",
                        "resume": sample_resume,
                        "active_jobs": sample_jobs,
                    },
                )

        assert response.status_code == 200
        data = response.json()
        match = data["matches"][0]
        assert "job_id" in match
        assert "compatibility_percentage" in match
        assert "justifications" in match
        assert "improvement_suggestions" in match
        assert 0 <= match["compatibility_percentage"] <= 100
        assert len(match["justifications"]) >= 1
        assert len(match["improvement_suggestions"]) <= 5


# --- Service Unit Tests ---


class TestJobMatcherService:
    """Tests for the job_matcher service functions."""

    def test_format_candidate_profile_with_full_data(self, sample_resume):
        """Test formatting a complete candidate profile."""
        result = _format_candidate_profile(sample_resume)
        assert "João Silva" in result
        assert "São Paulo" in result
        assert "Desenvolvedor Python Senior" in result
        assert "USP" in result
        assert "Python" in result
        assert "AWS Solutions Architect" in result
        assert "Inglês" in result

    def test_format_candidate_profile_with_empty_data(self):
        """Test formatting an empty profile returns fallback message."""
        result = _format_candidate_profile({})
        assert "sem dados cadastrados" in result

    def test_format_candidate_profile_with_partial_data(self):
        """Test formatting a profile with only some sections filled."""
        resume = {
            "personal_data": {"full_name": "Maria"},
            "skills": [{"name": "JavaScript", "proficiency": "advanced"}],
        }
        result = _format_candidate_profile(resume)
        assert "Maria" in result
        assert "JavaScript" in result

    def test_format_jobs_data(self, sample_jobs):
        """Test formatting job data for the LLM prompt."""
        result = _format_jobs_data(sample_jobs)
        assert "job-001" in result
        assert "Desenvolvedor Python Senior" in result
        assert "Data Engineer" in result
        assert "Designer UX/UI" in result
        assert "remote" in result
        assert "Python, FastAPI" in result

    def test_format_jobs_data_empty_list(self):
        """Test formatting an empty jobs list."""
        result = _format_jobs_data([])
        assert result == ""

    def test_format_jobs_data_minimal_job(self):
        """Test formatting a job with only required fields."""
        jobs = [{"id": "job-x", "title": "Test Job"}]
        result = _format_jobs_data(jobs)
        assert "job-x" in result
        assert "Test Job" in result

    @pytest.mark.asyncio
    async def test_match_candidate_to_jobs_returns_empty_for_no_jobs(self, sample_resume):
        """Test that empty list is returned when no jobs are provided."""
        result = await match_candidate_to_jobs(sample_resume, [])
        assert result == []

    @pytest.mark.asyncio
    async def test_match_candidate_to_jobs_filters_low_compatibility(self, sample_resume):
        """Test that jobs with compatibility < 10% are filtered out."""
        mock_analysis = JobMatchAnalysis(
            matches=[
                JobMatchResult(
                    job_id="job-001",
                    compatibility_percentage=85,
                    justifications=["Strong Python match"],
                    improvement_suggestions=["Learn Kubernetes"],
                ),
                JobMatchResult(
                    job_id="job-003",
                    compatibility_percentage=5,  # Should be filtered
                    justifications=["Very low relevance"],
                    improvement_suggestions=["Learn Figma", "Study UX"],
                ),
            ]
        )

        with patch(
            "app.services.job_matcher.get_structured_llm"
        ) as mock_get_structured:
            mock_structured = AsyncMock()
            mock_structured.ainvoke = AsyncMock(return_value=mock_analysis)
            mock_get_structured.return_value = mock_structured

            # Patch the chain execution
            with patch(
                "app.services.job_matcher.JOB_MATCHING_PROMPT"
            ) as mock_prompt:
                mock_chain = AsyncMock()
                mock_chain.ainvoke = AsyncMock(return_value=mock_analysis)
                mock_prompt.__or__ = lambda self, other: mock_chain

                result = await match_candidate_to_jobs(
                    sample_resume,
                    [
                        {"id": "job-001", "title": "Dev Python"},
                        {"id": "job-003", "title": "Designer"},
                    ],
                    timeout_seconds=30,
                )

        # Only job-001 should be returned (>= 10%)
        assert len(result) == 1
        assert result[0]["job_id"] == "job-001"
        assert result[0]["compatibility_percentage"] == 85

    @pytest.mark.asyncio
    async def test_match_candidate_to_jobs_sorts_by_percentage(self, sample_resume):
        """Test that results are sorted by compatibility percentage descending."""
        mock_analysis = JobMatchAnalysis(
            matches=[
                JobMatchResult(
                    job_id="job-001",
                    compatibility_percentage=60,
                    justifications=["Good match"],
                    improvement_suggestions=[],
                ),
                JobMatchResult(
                    job_id="job-002",
                    compatibility_percentage=90,
                    justifications=["Excellent match"],
                    improvement_suggestions=[],
                ),
                JobMatchResult(
                    job_id="job-003",
                    compatibility_percentage=40,
                    justifications=["Partial match"],
                    improvement_suggestions=["Develop more skills"],
                ),
            ]
        )

        with patch(
            "app.services.job_matcher.get_structured_llm"
        ) as mock_get_structured:
            mock_structured = AsyncMock()
            mock_structured.ainvoke = AsyncMock(return_value=mock_analysis)
            mock_get_structured.return_value = mock_structured

            with patch(
                "app.services.job_matcher.JOB_MATCHING_PROMPT"
            ) as mock_prompt:
                mock_chain = AsyncMock()
                mock_chain.ainvoke = AsyncMock(return_value=mock_analysis)
                mock_prompt.__or__ = lambda self, other: mock_chain

                result = await match_candidate_to_jobs(
                    sample_resume,
                    [
                        {"id": "job-001", "title": "Job A"},
                        {"id": "job-002", "title": "Job B"},
                        {"id": "job-003", "title": "Job C"},
                    ],
                    timeout_seconds=30,
                )

        assert len(result) == 3
        assert result[0]["compatibility_percentage"] == 90
        assert result[1]["compatibility_percentage"] == 60
        assert result[2]["compatibility_percentage"] == 40

    @pytest.mark.asyncio
    async def test_match_candidate_to_jobs_timeout(self, sample_resume, sample_jobs):
        """Test that TimeoutError is raised when analysis exceeds timeout."""
        with patch(
            "app.services.job_matcher.get_structured_llm"
        ) as mock_get_structured:
            mock_structured = AsyncMock()

            async def slow_invoke(*args, **kwargs):
                await asyncio.sleep(5)
                return JobMatchAnalysis(matches=[])

            mock_structured.ainvoke = slow_invoke
            mock_get_structured.return_value = mock_structured

            with patch(
                "app.services.job_matcher.JOB_MATCHING_PROMPT"
            ) as mock_prompt:
                mock_chain = AsyncMock()
                mock_chain.ainvoke = slow_invoke
                mock_prompt.__or__ = lambda self, other: mock_chain

                with pytest.raises(asyncio.TimeoutError):
                    await match_candidate_to_jobs(
                        sample_resume,
                        sample_jobs,
                        timeout_seconds=1,  # Very short timeout to trigger
                    )
