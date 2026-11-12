"""Application schemas for request/response validation."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ApplicationStatus


class ApplicationCreate(BaseModel):
    """Schema for creating an application (candidate applies to a job)."""

    job_id: UUID


class ApplicationResponse(BaseModel):
    """Schema for application response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    candidate_id: UUID
    status: ApplicationStatus
    applied_at: datetime
    updated_at: Optional[datetime] = None

    # Nested info for listing
    job_title: Optional[str] = None
    company_name: Optional[str] = None


class ApplicationListResponse(BaseModel):
    """Schema for application list item with job/company info."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    candidate_id: UUID
    status: ApplicationStatus
    applied_at: datetime
    updated_at: Optional[datetime] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    candidate_name: Optional[str] = None


class ApplicationStatusUpdate(BaseModel):
    """Schema for updating application status (employer workflow)."""

    status: ApplicationStatus


class PaginatedApplicationsResponse(BaseModel):
    """Paginated response for applications."""

    items: list[ApplicationListResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
