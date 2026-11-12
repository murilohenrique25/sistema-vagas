from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field

class JobReportCreate(BaseModel):
    reason: Literal["fraud","discrimination","misleading","spam","other"]
    details: str | None = Field(default=None,max_length=1000)
class JobReportResponse(BaseModel):
    id: UUID; job_id: UUID; reporter_id: UUID; reason: str; details: str|None; status: str; created_at: datetime
    model_config={"from_attributes":True}
class JobReportStatusUpdate(BaseModel):
    status: Literal["reviewed","dismissed","actioned"]
