"""JobHighlight model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import UUIDMixin


class JobHighlight(Base, UUIDMixin):
    """Job highlights table."""

    __tablename__ = "job_highlights"
    __table_args__ = (
        Index("ix_job_highlights_is_active_expires_at", "is_active", "expires_at"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False
    )
    activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    job = relationship("Job", back_populates="highlights")

    def __repr__(self) -> str:
        return f"<JobHighlight(id={self.id}, is_active={self.is_active})>"
