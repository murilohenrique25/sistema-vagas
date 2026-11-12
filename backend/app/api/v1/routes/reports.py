from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.v1.dependencies import CurrentUser,get_current_user
from app.core.database import get_session
from app.models.job_report import JobReport
from app.models.job import Job
from app.models.enums import JobStatus
from app.schemas.report import JobReportCreate,JobReportResponse

router=APIRouter(prefix="/jobs",tags=["reports"])
@router.post("/{job_id}/reports",response_model=JobReportResponse,status_code=201)
async def report_job(job_id:UUID,data:JobReportCreate,user:CurrentUser=Depends(get_current_user),session:AsyncSession=Depends(get_session)):
    job = (await session.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
    if not job or job.status != JobStatus.active:
        raise HTTPException(status_code=404, detail="Vaga não encontrada ou indisponível")
    report=JobReport(job_id=job_id,reporter_id=user.id,reason=data.reason,details=data.details)
    session.add(report)
    try: await session.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=409,detail="Você já denunciou esta vaga") from exc
    return JobReportResponse.model_validate(report)
