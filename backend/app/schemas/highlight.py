"""Schemas for highlight-related requests and responses."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ActivateHighlightRequest(BaseModel):
    """Request body to activate a highlight on a job."""

    job_id: uuid.UUID = Field(..., description="ID da vaga a ser destacada")


class HighlightResponse(BaseModel):
    """Response representing an active highlight."""

    id: uuid.UUID
    job_id: uuid.UUID
    activated_at: datetime
    expires_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class HighlightListResponse(BaseModel):
    """Response containing a list of active highlights."""

    items: list[HighlightResponse]
    total: int


class ExpireHighlightsResponse(BaseModel):
    """Response from the expire-highlights scheduler endpoint."""

    expired_count: int
    message: str
