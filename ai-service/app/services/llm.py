from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph

from app.config import settings


def get_llm(temperature: float | None = None) -> ChatOpenAI:
    """Create and return a configured ChatOpenAI instance.

    Args:
        temperature: Override for the model temperature. Defaults to config value.

    Returns:
        Configured ChatOpenAI instance ready for use with LangChain.
    """
    kwargs: dict = {
        "model": settings.openai_model,
        "api_key": settings.openai_api_key,
        "temperature": temperature if temperature is not None else settings.openai_temperature,
    }
    # Allow pointing to OpenAI-compatible providers (Groq, Gemini, OpenRouter, ...)
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url

    return ChatOpenAI(**kwargs)


def get_structured_llm(schema, temperature: float | None = None):
    """Return an LLM wrapped for structured output using the configured method.

    Uses `settings.openai_structured_output_method` (default "function_calling")
    so it works with providers that don't support OpenAI's native `json_schema`
    response format (e.g. several Groq models).

    Args:
        schema: A Pydantic model or schema describing the expected output.
        temperature: Optional override for the model temperature.

    Returns:
        A runnable that returns instances of `schema`.
    """
    llm = get_llm(temperature=temperature)
    return llm.with_structured_output(
        schema, method=settings.openai_structured_output_method
    )


class BaseState(TypedDict):
    """Base state for LangGraph workflows.

    All AI processing pipelines (PDF extraction, candidate analysis,
    job matching) extend this base state.
    """
    input: str
    output: str
    error: str


class PDFExtractionState(TypedDict):
    """State for PDF extraction workflow."""
    pdf_text: str
    extracted_data: dict
    error: str


class CandidateAnalysisState(TypedDict):
    """State for candidate analysis workflow."""
    job_requirements: dict
    candidate_resumes: list[dict]
    scores: list[dict]
    error: str


class JobMatchingState(TypedDict):
    """State for job matching workflow."""
    candidate_profile: dict
    active_jobs: list[dict]
    matches: list[dict]
    error: str


def create_graph_builder(state_type: type = BaseState) -> StateGraph:
    """Create a LangGraph StateGraph builder for AI workflows.

    This provides the foundation for building AI processing pipelines
    (PDF extraction, candidate analysis, job matching) using LangGraph.

    Args:
        state_type: The TypedDict class defining the graph state.
                    Defaults to BaseState. Use PDFExtractionState,
                    CandidateAnalysisState, or JobMatchingState for
                    specific workflows.

    Returns:
        A StateGraph builder configured with the given state type.
    """
    return StateGraph(state_type)
