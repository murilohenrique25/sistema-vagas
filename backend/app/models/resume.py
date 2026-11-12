"""Resume and related models (Experiences, Educations, Skills, Certifications, Languages)."""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.models.enums import DegreeLevel, FluencyLevel, ProficiencyLevel


class Resume(Base, UUIDMixin, TimestampMixin):
    """Resumes table."""

    __tablename__ = "resumes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="resumes")
    experiences = relationship(
        "Experience", back_populates="resume", lazy="selectin", cascade="all, delete-orphan"
    )
    educations = relationship(
        "Education", back_populates="resume", lazy="selectin", cascade="all, delete-orphan"
    )
    skills = relationship(
        "Skill", back_populates="resume", lazy="selectin", cascade="all, delete-orphan"
    )
    certifications = relationship(
        "Certification", back_populates="resume", lazy="selectin", cascade="all, delete-orphan"
    )
    languages = relationship(
        "Language", back_populates="resume", lazy="selectin", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Resume(id={self.id}, full_name={self.full_name})>"


class Experience(Base, UUIDMixin):
    """Experiences table."""

    __tablename__ = "experiences"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    resume = relationship("Resume", back_populates="experiences")

    def __repr__(self) -> str:
        return f"<Experience(id={self.id}, company={self.company}, position={self.position})>"


class Education(Base, UUIDMixin):
    """Educations table."""

    __tablename__ = "educations"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    course: Mapped[str] = mapped_column(String(255), nullable=False)
    degree: Mapped[DegreeLevel] = mapped_column(nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    resume = relationship("Resume", back_populates="educations")

    def __repr__(self) -> str:
        return f"<Education(id={self.id}, institution={self.institution})>"


class Skill(Base, UUIDMixin):
    """Skills table."""

    __tablename__ = "skills"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    proficiency: Mapped[ProficiencyLevel] = mapped_column(nullable=False)

    # Relationships
    resume = relationship("Resume", back_populates="skills")

    def __repr__(self) -> str:
        return f"<Skill(id={self.id}, name={self.name})>"


class Certification(Base, UUIDMixin):
    """Certifications table."""

    __tablename__ = "certifications"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer: Mapped[str] = mapped_column(String(255), nullable=False)
    obtained_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationships
    resume = relationship("Resume", back_populates="certifications")

    def __repr__(self) -> str:
        return f"<Certification(id={self.id}, name={self.name})>"


class Language(Base, UUIDMixin):
    """Languages table."""

    __tablename__ = "languages"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    language: Mapped[str] = mapped_column(String(100), nullable=False)
    fluency: Mapped[FluencyLevel] = mapped_column(nullable=False)

    # Relationships
    resume = relationship("Resume", back_populates="languages")

    def __repr__(self) -> str:
        return f"<Language(id={self.id}, language={self.language})>"
