"""Application and ApplicationStatusHistory models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import UUIDMixin
from app.models.enums import ApplicationStatus


class Application(Base, UUIDMixin):
    """Applications table."""

    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("job_id", "candidate_id", name="uq_applications_job_candidate"),
        Index("ix_applications_job_id_status", "job_id", "status"),
        Index("ix_applications_candidate_id_status", "candidate_id", "status"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        nullable=False, default=ApplicationStatus.received
    )
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    # Relationships
    job = relationship("Job", back_populates="applications")
    candidate = relationship("User", back_populates="applications")
    status_history = relationship(
        "ApplicationStatusHistory", back_populates="application", lazy="selectin", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Application(id={self.id}, status={self.status})>"


class ApplicationStatusHistory(Base, UUIDMixin):
    """Application status history table."""

    __tablename__ = "application_status_history"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    previous_status: Mapped[ApplicationStatus | None] = mapped_column(nullable=True)
    new_status: Mapped[ApplicationStatus] = mapped_column(nullable=False)
    changed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    application = relationship("Application", back_populates="status_history")
    user = relationship("User", foreign_keys=[changed_by])

    def __repr__(self) -> str:
        return f"<ApplicationStatusHistory(id={self.id}, {self.previous_status} -> {self.new_status})>"
