"""Job schemas for request/response validation."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ContractType, JobModality, JobStatus


# --- Enums for sorting ---


class JobSortField(str, Enum):
    """Available sort fields for job listing."""

    date = "date"
    salary = "salary"
    relevance = "relevance"


class SortOrder(str, Enum):
    """Sort order direction."""

    asc = "asc"
    desc = "desc"


# --- Generic paginated response ---

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response schema."""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class JobCreate(BaseModel):
    """Schema for creating a new job."""

    title: str
    modality: JobModality
    location: str
    responsibilities: str
    required_skills: str
    contract_type: ContractType
    deadline: date
    optional_skills: Optional[str] = None
    benefits: Optional[str] = None
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Title must be at most 150 characters."""
        if not v or not v.strip():
            raise ValueError("O título é obrigatório")
        if len(v) > 150:
            raise ValueError("O título deve ter no máximo 150 caracteres")
        return v.strip()

    @field_validator("deadline")
    @classmethod
    def validate_deadline(cls, v: date) -> date:
        """Deadline must be at least 1 day in the future and at most 180 days."""
        today = date.today()
        days_diff = (v - today).days
        if days_diff < 1:
            raise ValueError("O prazo deve ser no mínimo 1 dia no futuro")
        if days_diff > 180:
            raise ValueError("O prazo deve ser no máximo 180 dias no futuro")
        return v

    @field_validator("salary_min", "salary_max")
    @classmethod
    def validate_salary(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Salary must be positive if provided."""
        if v is not None and v < 0:
            raise ValueError("O salário não pode ser negativo")
        return v


class JobUpdate(BaseModel):
    """Schema for updating a job. All fields are optional."""

    title: Optional[str] = None
    modality: Optional[JobModality] = None
    location: Optional[str] = None
    responsibilities: Optional[str] = None
    required_skills: Optional[str] = None
    contract_type: Optional[ContractType] = None
    deadline: Optional[date] = None
    optional_skills: Optional[str] = None
    benefits: Optional[str] = None
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        """Title must be at most 150 characters if provided."""
        if v is not None:
            if not v.strip():
                raise ValueError("O título não pode ser vazio")
            if len(v) > 150:
                raise ValueError("O título deve ter no máximo 150 caracteres")
            return v.strip()
        return v

    @field_validator("deadline")
    @classmethod
    def validate_deadline(cls, v: Optional[date]) -> Optional[date]:
        """Deadline must be at least 1 day in the future and at most 180 days if provided."""
        if v is not None:
            today = date.today()
            days_diff = (v - today).days
            if days_diff < 1:
                raise ValueError("O prazo deve ser no mínimo 1 dia no futuro")
            if days_diff > 180:
                raise ValueError("O prazo deve ser no máximo 180 dias no futuro")
        return v


class JobExtendDeadline(BaseModel):
    """Schema for extending a job's deadline."""

    new_date: date

    @field_validator("new_date")
    @classmethod
    def validate_new_date(cls, v: date) -> date:
        """New date must be between 1 and 180 days from now."""
        today = date.today()
        days_diff = (v - today).days
        if days_diff < 1:
            raise ValueError("A nova data deve ser no mínimo 1 dia no futuro")
        if days_diff > 180:
            raise ValueError("A nova data deve ser no máximo 180 dias no futuro")
        return v


class JobStatusUpdate(BaseModel):
    """Schema for changing job status."""

    status: JobStatus


class JobSearchFilters(BaseModel):
    """Schema for job search query parameters."""

    # Text search (min 2 chars)
    q: Optional[str] = Field(None, min_length=2, description="Texto de busca (mínimo 2 caracteres)")

    # Filters
    modality: Optional[JobModality] = Field(None, description="Filtro por modalidade")
    location: Optional[str] = Field(None, description="Filtro por localização")
    salary_min: Optional[Decimal] = Field(None, ge=0, description="Salário mínimo da faixa")
    salary_max: Optional[Decimal] = Field(None, description="Salário máximo da faixa")
    contract_type: Optional[ContractType] = Field(None, description="Filtro por regime de contratação")

    # Sorting
    sort_by: JobSortField = Field(JobSortField.date, description="Campo de ordenação")
    sort_order: SortOrder = Field(SortOrder.desc, description="Direção da ordenação")

    # Pagination
    page: int = Field(1, ge=1, description="Número da página")
    page_size: int = Field(20, ge=1, le=100, description="Itens por página")


class JobResponse(BaseModel):
    """Schema for job response serialization."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    title: str
    modality: JobModality
    location: Optional[str] = None
    responsibilities: Optional[str] = None
    required_skills: Optional[str] = None
    optional_skills: Optional[str] = None
    benefits: Optional[str] = None
    contract_type: ContractType
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    status: JobStatus
    deadline: Optional[date] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_highlighted: bool = False
