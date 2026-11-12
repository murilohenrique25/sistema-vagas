"""Tests for candidate analyzer service and endpoint.

Covers:
- Successful analysis with multiple candidates (mocked LLM)
- 200 candidate limit validation (endpoint level)
- Timeout handling per candidate
- Score range validation (0-100)
- Result sorting by score descending
- Structured output validation (strengths 1-5, concerns 1-5, justification max 500 chars)
"""

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.candidate_analyzer import (
    CandidateAnalyzer,
    CandidateAnalysisResult,
    ANALYSIS_PROMPT,
)


# --- Test fixtures ---


def make_candidate(candidate_id: str, name: str = "Test User", skills: list | None = None):
    """Helper to create candidate data dicts."""
    return {
        "candidate_id": candidate_id,
        "full_name": name,
        "location": "São Paulo, SP",
        "experiences": [
            {
                "company": "Tech Corp",
                "position": "Developer",
                "start_date": "2020-01",
                "end_date": "2023-06",
                "description": "Backend development with Python",
            }
        ],
        "educations": [
            {
                "institution": "USP",
                "course": "Computer Science",
                "degree": "bachelor",
                "start_date": "2016-01",
                "end_date": "2020-01",
            }
        ],
        "skills": skills or [{"name": "Python", "proficiency": "advanced"}],
        "certifications": [],
        "languages": [{"language": "English", "fluency": "advanced"}],
    }


def make_job():
    """Helper to create job requirements dict."""
    return {
        "title": "Senior Python Developer",
        "modality": "remote",
        "location": "São Paulo, SP",
        "responsibilities": "Develop and maintain backend services",
        "required_skills": "Python, FastAPI, PostgreSQL, 5+ years experience",
        "optional_skills": "Docker, Kubernetes, AWS",
        "contract_type": "clt",
    }


def make_analysis_result(score: int = 75) -> CandidateAnalysisResult:
    """Helper to create a mock LLM analysis result."""
    return CandidateAnalysisResult(
        score=score,
        strengths=["Strong Python skills", "Relevant experience"],
        concerns=["No Docker experience"],
        justification="Good candidate with relevant backend experience but lacks containerization skills.",
    )


# --- CandidateAnalyzer Unit Tests ---


class TestCandidateAnalyzerUnit:
    """Unit tests for the CandidateAnalyzer class."""

    def test_format_job_data(self):
        """Test job data formatting for prompt template."""
        analyzer = CandidateAnalyzer()
        job = make_job()
        formatted = analyzer._format_job_data(job)

        assert formatted["job_title"] == "Senior Python Developer"
        assert formatted["job_modality"] == "remote"
        assert formatted["job_location"] == "São Paulo, SP"
        assert formatted["job_responsibilities"] == "Develop and maintain backend services"
        assert formatted["job_required_skills"] == "Python, FastAPI, PostgreSQL, 5+ years experience"
        assert formatted["job_optional_skills"] == "Docker, Kubernetes, AWS"
        assert formatted["job_contract_type"] == "clt"

    def test_format_job_data_with_missing_fields(self):
        """Test job data formatting with missing fields defaults to N/A."""
        analyzer = CandidateAnalyzer()
        job = {"title": "Developer"}
        formatted = analyzer._format_job_data(job)

        assert formatted["job_title"] == "Developer"
        assert formatted["job_modality"] == "N/A"
        assert formatted["job_location"] == "N/A"

    def test_format_candidate_data(self):
        """Test candidate data formatting for prompt template."""
        analyzer = CandidateAnalyzer()
        candidate = make_candidate("c-1", "Maria Costa")
        formatted = analyzer._format_candidate_data(candidate)

        assert formatted["candidate_name"] == "Maria Costa"
        assert formatted["candidate_location"] == "São Paulo, SP"
        assert "Tech Corp" in formatted["candidate_experiences"]
        assert "USP" in formatted["candidate_educations"]
        assert "Python" in formatted["candidate_skills"]
        assert "English" in formatted["candidate_languages"]

    def test_format_candidate_data_empty_sections(self):
        """Test candidate data formatting with empty sections."""
        analyzer = CandidateAnalyzer()
        candidate = {
            "candidate_id": "c-empty",
            "full_name": "Empty User",
            "location": None,
            "experiences": [],
            "educations": [],
            "skills": [],
            "certifications": [],
            "languages": [],
        }
        formatted = analyzer._format_candidate_data(candidate)

        assert formatted["candidate_name"] == "Empty User"
        assert "Nenhuma experiência informada" in formatted["candidate_experiences"]
        assert "Nenhuma formação informada" in formatted["candidate_educations"]
        assert "Nenhuma habilidade informada" in formatted["candidate_skills"]
        assert "Nenhuma certificação informada" in formatted["candidate_certifications"]
        assert "Nenhum idioma informado" in formatted["candidate_languages"]

    def test_format_candidate_data_with_resume_key(self):
        """Test candidate data formatting when data is nested under 'resume' key."""
        analyzer = CandidateAnalyzer()
        candidate = {
            "candidate_id": "c-nested",
            "resume": {
                "personal_data": {"full_name": "Nested User", "location": "Rio, RJ"},
                "experiences": [{"company": "Nested Co", "position": "Dev", "start_date": "2021-01", "end_date": "2023-01", "description": "Work"}],
                "educations": [],
                "skills": [{"name": "Java", "proficiency": "intermediate"}],
                "certifications": [],
                "languages": [],
            },
        }
        formatted = analyzer._format_candidate_data(candidate)

        assert formatted["candidate_name"] == "Nested User"
        assert formatted["candidate_location"] == "Rio, RJ"
        assert "Java" in formatted["candidate_skills"]

    @pytest.mark.asyncio
    async def test_analyze_single_candidate_success(self):
        """Test successful single candidate analysis with mocked LLM."""
        analyzer = CandidateAnalyzer()
        mock_result = make_analysis_result(score=82)

        with patch.object(analyzer, "_get_chain") as mock_chain:
            mock_chain.return_value = AsyncMock(ainvoke=AsyncMock(return_value=mock_result))
            result = await analyzer.analyze_single_candidate(make_job(), make_candidate("c-1"))

        assert result is not None
        assert result.score == 82
        assert len(result.strengths) == 2
        assert len(result.concerns) == 1
        assert len(result.justification) <= 500

    @pytest.mark.asyncio
    async def test_analyze_single_candidate_timeout(self):
        """Test that timeout per candidate returns None."""
        analyzer = CandidateAnalyzer()
        analyzer._timeout = 0.01  # Very short timeout for testing

        async def slow_invoke(*args, **kwargs):
            await asyncio.sleep(1)
            return make_analysis_result()

        with patch.object(analyzer, "_get_chain") as mock_chain:
            mock_chain.return_value = AsyncMock(ainvoke=slow_invoke)
            result = await analyzer.analyze_single_candidate(make_job(), make_candidate("c-1"))

        assert result is None

    @pytest.mark.asyncio
    async def test_analyze_single_candidate_llm_error(self):
        """Test that LLM errors are handled gracefully returning None."""
        analyzer = CandidateAnalyzer()

        with patch.object(analyzer, "_get_chain") as mock_chain:
            mock_chain.return_value = AsyncMock(
                ainvoke=AsyncMock(side_effect=Exception("LLM API error"))
            )
            result = await analyzer.analyze_single_candidate(make_job(), make_candidate("c-1"))

        assert result is None

    @pytest.mark.asyncio
    async def test_analyze_candidates_multiple_success(self):
        """Test successful analysis of multiple candidates."""
        analyzer = CandidateAnalyzer()

        results_map = {
            0: make_analysis_result(score=90),
            1: make_analysis_result(score=65),
            2: make_analysis_result(score=80),
        }
        call_count = {"value": 0}

        async def mock_invoke(*args, **kwargs):
            idx = call_count["value"]
            call_count["value"] += 1
            return results_map[idx]

        candidates = [
            make_candidate("c-1", "Alice"),
            make_candidate("c-2", "Bob"),
            make_candidate("c-3", "Charlie"),
        ]

        with patch.object(analyzer, "_get_chain") as mock_chain:
            mock_chain.return_value = AsyncMock(ainvoke=mock_invoke)
            results = await analyzer.analyze_candidates(make_job(), candidates)

        assert len(results) == 3
        # Verify sorted by score descending
        assert results[0]["score"] == 90
        assert results[1]["score"] == 80
        assert results[2]["score"] == 65
        # Verify all have completed status
        assert all(r["status"] == "completed" for r in results)

    @pytest.mark.asyncio
    async def test_analyze_candidates_timeout_handling(self):
        """Test that timeout candidates get status='timeout' with score 0."""
        analyzer = CandidateAnalyzer()
        analyzer._timeout = 0.01  # Very short timeout

        async def slow_invoke(*args, **kwargs):
            await asyncio.sleep(1)
            return make_analysis_result()

        candidates = [make_candidate("c-timeout")]

        with patch.object(analyzer, "_get_chain") as mock_chain:
            mock_chain.return_value = AsyncMock(ainvoke=slow_invoke)
            results = await analyzer.analyze_candidates(make_job(), candidates)

        assert len(results) == 1
        assert results[0]["candidate_id"] == "c-timeout"
        assert results[0]["status"] == "timeout"
        assert results[0]["score"] == 0
        assert "Análise não pôde ser concluída" in results[0]["concerns"]

    @pytest.mark.asyncio
    async def test_analyze_candidates_mixed_success_and_timeout(self):
        """Test mixed results: some succeed, some timeout."""
        analyzer = CandidateAnalyzer()
        analyzer._timeout = 0.05

        call_count = {"value": 0}

        async def mixed_invoke(*args, **kwargs):
            idx = call_count["value"]
            call_count["value"] += 1
            if idx == 1:
                # Second candidate times out
                await asyncio.sleep(1)
                return make_analysis_result()
            return make_analysis_result(score=70 + idx * 10)

        candidates = [
            make_candidate("c-1", "Alice"),
            make_candidate("c-2", "Bob"),
            make_candidate("c-3", "Charlie"),
        ]

        with patch.object(analyzer, "_get_chain") as mock_chain:
            mock_chain.return_value = AsyncMock(ainvoke=mixed_invoke)
            results = await analyzer.analyze_candidates(make_job(), candidates)

        assert len(results) == 3
        # Completed candidates should be sorted above timeout
        completed = [r for r in results if r["status"] == "completed"]
        timed_out = [r for r in results if r["status"] == "timeout"]
        assert len(completed) == 2
        assert len(timed_out) == 1
        assert timed_out[0]["candidate_id"] == "c-2"
        # All sorted by score descending
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_analyze_candidates_empty_list(self):
        """Test that an empty candidate list returns empty results."""
        analyzer = CandidateAnalyzer()
        results = await analyzer.analyze_candidates(make_job(), [])
        assert results == []

    @pytest.mark.asyncio
    async def test_analyze_candidates_results_sorted_descending(self):
        """Test that results are always sorted by score descending."""
        analyzer = CandidateAnalyzer()

        scores_to_return = [30, 95, 50, 10, 75]
        call_count = {"value": 0}

        async def mock_invoke(*args, **kwargs):
            idx = call_count["value"]
            call_count["value"] += 1
            return make_analysis_result(score=scores_to_return[idx])

        candidates = [make_candidate(f"c-{i}") for i in range(5)]

        with patch.object(analyzer, "_get_chain") as mock_chain:
            mock_chain.return_value = AsyncMock(ainvoke=mock_invoke)
            results = await analyzer.analyze_candidates(make_job(), candidates)

        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)
        assert scores == [95, 75, 50, 30, 10]


# --- CandidateAnalysisResult Pydantic Model Tests ---


class TestCandidateAnalysisResultModel:
    """Tests for the structured output Pydantic model."""

    def test_valid_result(self):
        """Test creating a valid CandidateAnalysisResult."""
        result = CandidateAnalysisResult(
            score=85,
            strengths=["Strong Python", "Good architecture knowledge"],
            concerns=["No AWS experience"],
            justification="Solid developer with good fundamentals.",
        )
        assert result.score == 85
        assert len(result.strengths) == 2
        assert len(result.concerns) == 1

    def test_score_boundary_zero(self):
        """Test score at minimum boundary (0)."""
        result = CandidateAnalysisResult(
            score=0,
            strengths=["Willingness to learn"],
            concerns=["No relevant experience", "No matching skills"],
            justification="Does not meet any requirements.",
        )
        assert result.score == 0

    def test_score_boundary_hundred(self):
        """Test score at maximum boundary (100)."""
        result = CandidateAnalysisResult(
            score=100,
            strengths=["Perfect match in all criteria"],
            concerns=["Overqualified potentially"],
            justification="Exceeds all requirements.",
        )
        assert result.score == 100

    def test_score_below_zero_rejected(self):
        """Test that score below 0 is rejected by validation."""
        with pytest.raises(Exception):
            CandidateAnalysisResult(
                score=-1,
                strengths=["Test"],
                concerns=["Test"],
                justification="Invalid score",
            )

    def test_score_above_hundred_rejected(self):
        """Test that score above 100 is rejected by validation."""
        with pytest.raises(Exception):
            CandidateAnalysisResult(
                score=101,
                strengths=["Test"],
                concerns=["Test"],
                justification="Invalid score",
            )

    def test_strengths_min_one_required(self):
        """Test that at least 1 strength is required."""
        with pytest.raises(Exception):
            CandidateAnalysisResult(
                score=50,
                strengths=[],
                concerns=["Test"],
                justification="No strengths provided",
            )

    def test_strengths_max_five(self):
        """Test that more than 5 strengths are rejected."""
        with pytest.raises(Exception):
            CandidateAnalysisResult(
                score=50,
                strengths=["s1", "s2", "s3", "s4", "s5", "s6"],
                concerns=["Test"],
                justification="Too many strengths",
            )

    def test_concerns_min_one_required(self):
        """Test that at least 1 concern is required."""
        with pytest.raises(Exception):
            CandidateAnalysisResult(
                score=50,
                strengths=["Test"],
                concerns=[],
                justification="No concerns provided",
            )

    def test_concerns_max_five(self):
        """Test that more than 5 concerns are rejected."""
        with pytest.raises(Exception):
            CandidateAnalysisResult(
                score=50,
                strengths=["Test"],
                concerns=["c1", "c2", "c3", "c4", "c5", "c6"],
                justification="Too many concerns",
            )

    def test_justification_max_500_chars(self):
        """Test that justification over 500 chars is rejected."""
        with pytest.raises(Exception):
            CandidateAnalysisResult(
                score=50,
                strengths=["Test"],
                concerns=["Test"],
                justification="x" * 501,
            )

    def test_justification_exactly_500_chars_accepted(self):
        """Test that justification at exactly 500 chars is accepted."""
        result = CandidateAnalysisResult(
            score=50,
            strengths=["Test"],
            concerns=["Test"],
            justification="x" * 500,
        )
        assert len(result.justification) == 500


# --- Endpoint Integration Tests ---


class TestAnalyzeCandidatesEndpoint:
    """Integration tests for POST /analyze-candidates endpoint."""

    @pytest.mark.asyncio
    async def test_rejects_empty_candidates(self):
        """Test that the endpoint rejects requests with no candidates."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/analyze-candidates",
                json={"job_id": "job-1", "candidate_ids": []},
            )

        assert response.status_code == 400
        assert "At least one candidate" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_rejects_over_200_candidates(self):
        """Test that the endpoint rejects requests with more than 200 candidates."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/analyze-candidates",
                json={
                    "job_id": "job-1",
                    "candidate_ids": [f"c-{i}" for i in range(201)],
                },
            )

        assert response.status_code == 400
        assert "200" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_accepts_exactly_200_candidates(self):
        """Test that the endpoint accepts exactly 200 candidates."""
        candidates = [
            make_candidate(f"c-{i}", f"Candidate {i}") for i in range(200)
        ]

        mock_result = make_analysis_result(score=50)

        with patch(
            "app.services.candidate_analyzer.CandidateAnalyzer._get_chain"
        ) as mock_chain:
            mock_chain.return_value = AsyncMock(
                ainvoke=AsyncMock(return_value=mock_result)
            )
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/analyze-candidates",
                    json={
                        "job_requirements": make_job(),
                        "candidates": [
                            {
                                "candidate_id": f"c-{i}",
                                "full_name": f"Candidate {i}",
                                "experiences": [],
                                "educations": [],
                                "skills": [],
                                "certifications": [],
                                "languages": [],
                            }
                            for i in range(200)
                        ],
                    },
                    timeout=120,
                )

        assert response.status_code == 200
        data = response.json()
        assert data["total_candidates"] == 200

    @pytest.mark.asyncio
    async def test_requires_job_id_or_requirements(self):
        """Test that either job_id or job_requirements must be provided."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/analyze-candidates",
                json={
                    "candidates": [
                        {
                            "candidate_id": "c-1",
                            "full_name": "Test",
                            "experiences": [],
                            "educations": [],
                            "skills": [],
                            "certifications": [],
                            "languages": [],
                        }
                    ]
                },
            )

        assert response.status_code == 400
        assert "job_id" in response.json()["detail"] or "job_requirements" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_successful_analysis_with_direct_data(self):
        """Test successful analysis when job_requirements and candidates are provided directly."""
        mock_result = make_analysis_result(score=78)

        with patch(
            "app.services.candidate_analyzer.CandidateAnalyzer._get_chain"
        ) as mock_chain:
            mock_chain.return_value = AsyncMock(
                ainvoke=AsyncMock(return_value=mock_result)
            )
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/analyze-candidates",
                    json={
                        "job_requirements": make_job(),
                        "candidates": [
                            {
                                "candidate_id": "c-1",
                                "full_name": "Alice Developer",
                                "experiences": [
                                    {"company": "Tech", "position": "Dev", "start_date": "2020-01", "end_date": "2023-01", "description": "Python dev"}
                                ],
                                "educations": [{"institution": "USP", "course": "CS", "degree": "bachelor"}],
                                "skills": [{"name": "Python", "proficiency": "advanced"}],
                                "certifications": [],
                                "languages": [{"language": "English", "fluency": "advanced"}],
                            }
                        ],
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "provided"
        assert data["total_candidates"] == 1
        assert len(data["results"]) == 1
        result = data["results"][0]
        assert result["candidate_id"] == "c-1"
        assert result["score"] == 78
        assert result["status"] == "completed"
        assert 1 <= len(result["strengths"]) <= 5
        assert 1 <= len(result["concerns"]) <= 5
        assert len(result["justification"]) <= 500

    @pytest.mark.asyncio
    async def test_response_sorted_by_score_descending(self):
        """Test that response results are sorted by score descending."""
        scores = [40, 90, 60]
        call_count = {"value": 0}

        async def mock_invoke(*args, **kwargs):
            idx = call_count["value"]
            call_count["value"] += 1
            return make_analysis_result(score=scores[idx])

        with patch(
            "app.services.candidate_analyzer.CandidateAnalyzer._get_chain"
        ) as mock_chain:
            mock_chain.return_value = AsyncMock(ainvoke=mock_invoke)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/analyze-candidates",
                    json={
                        "job_requirements": make_job(),
                        "candidates": [
                            {
                                "candidate_id": f"c-{i}",
                                "full_name": f"Candidate {i}",
                                "experiences": [],
                                "educations": [],
                                "skills": [],
                                "certifications": [],
                                "languages": [],
                            }
                            for i in range(3)
                        ],
                    },
                )

        assert response.status_code == 200
        data = response.json()
        result_scores = [r["score"] for r in data["results"]]
        assert result_scores == sorted(result_scores, reverse=True)
        assert result_scores == [90, 60, 40]

    @pytest.mark.asyncio
    async def test_timeout_candidate_in_response(self):
        """Test that timed-out candidates appear in response with status='timeout'."""
        analyzer_timeout = 0.01

        async def slow_invoke(*args, **kwargs):
            await asyncio.sleep(1)
            return make_analysis_result()

        with patch(
            "app.services.candidate_analyzer.CandidateAnalyzer._get_chain"
        ) as mock_chain, patch(
            "app.services.candidate_analyzer.candidate_analyzer._timeout", analyzer_timeout
        ):
            mock_chain.return_value = AsyncMock(ainvoke=slow_invoke)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/analyze-candidates",
                    json={
                        "job_requirements": make_job(),
                        "candidates": [
                            {
                                "candidate_id": "c-slow",
                                "full_name": "Slow Candidate",
                                "experiences": [],
                                "educations": [],
                                "skills": [],
                                "certifications": [],
                                "languages": [],
                            }
                        ],
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["total_candidates"] == 1
        result = data["results"][0]
        assert result["candidate_id"] == "c-slow"
        assert result["status"] == "timeout"
        assert result["score"] == 0
