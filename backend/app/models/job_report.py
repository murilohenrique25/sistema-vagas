"""Reports submitted against job postings."""
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.base import UUIDMixin

class JobReport(Base, UUIDMixin):
    __tablename__="job_reports"
    __table_args__=(UniqueConstraint("job_id","reporter_id",name="uq_job_reporter"),)
    job_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey("jobs.id",ondelete="CASCADE"),nullable=False)
    reporter_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey("users.id",ondelete="CASCADE"),nullable=False)
    reason: Mapped[str]=mapped_column(String(50),nullable=False)
    details: Mapped[str|None]=mapped_column(String(1000))
    status: Mapped[str]=mapped_column(String(20),default="pending",nullable=False,index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)
