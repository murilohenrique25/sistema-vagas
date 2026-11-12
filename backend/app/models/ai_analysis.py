"""AIAnalysis model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import UUIDMixin
from app.models.enums import AIAnalysisStatus, AIAnalysisType


class AIAnalysis(Base, UUIDMixin):
    """AI analyses table."""

    __tablename__ = "ai_analyses"

    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=True
    )
    type: Mapped[AIAnalysisType] = mapped_column(nullable=False)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tokens_consumed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[AIAnalysisStatus] = mapped_column(
        nullable=False, default=AIAnalysisStatus.processing
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    requester = relationship("User", foreign_keys=[requester_id])
    job = relationship("Job", back_populates="ai_analyses")

    def __repr__(self) -> str:
        return f"<AIAnalysis(id={self.id}, type={self.type}, status={self.status})>"
