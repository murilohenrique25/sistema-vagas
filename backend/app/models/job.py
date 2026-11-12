"""Job model."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.models.enums import ContractType, JobModality, JobStatus


class Job(Base, UUIDMixin, TimestampMixin):
    """Jobs table."""

    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_status_deadline", "status", "deadline"),
        Index("ix_jobs_company_id_status", "company_id", "status"),
        Index(
            "ix_jobs_fulltext_search",
            "search_vector",
            postgresql_using="gin",
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    modality: Mapped[JobModality] = mapped_column(nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    responsibilities: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_skills: Mapped[str | None] = mapped_column(Text, nullable=True)
    optional_skills: Mapped[str | None] = mapped_column(Text, nullable=True)
    benefits: Mapped[str | None] = mapped_column(Text, nullable=True)
    contract_type: Mapped[ContractType] = mapped_column(nullable=False)
    salary_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[JobStatus] = mapped_column(nullable=False, default=JobStatus.draft)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Full-text search vector (plain column, updated via trigger or application code)
    search_vector = mapped_column(TSVECTOR, nullable=True)

    # Relationships
    company = relationship("Company", back_populates="jobs")
    applications = relationship("Application", back_populates="job", lazy="selectin")
    highlights = relationship("JobHighlight", back_populates="job", lazy="selectin")
    ai_analyses = relationship("AIAnalysis", back_populates="job", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, title={self.title}, status={self.status})>"
