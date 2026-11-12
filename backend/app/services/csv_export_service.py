"""CSV export service for admin data exports."""

import csv
import io
from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.job import Job
from app.models.subscription import Payment
from app.models.user import User

# Maximum records per CSV export
MAX_CSV_RECORDS = 50_000


async def export_users_csv(session: AsyncSession) -> AsyncGenerator[str, None]:
    """Export users data as CSV stream.

    Yields CSV content line by line for streaming response.
    Max 50,000 records.
    """
    query = select(User).order_by(User.created_at.desc()).limit(MAX_CSV_RECORDS)
    result = await session.execute(query)
    users = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    header = ["id", "email", "name", "role", "is_active", "created_at"]
    writer.writerow(header)
    yield output.getvalue()
    output.seek(0)
    output.truncate(0)

    # Data rows
    for user in users:
        writer.writerow([
            str(user.id),
            user.email,
            user.name,
            user.role.value if hasattr(user.role, "value") else user.role,
            user.is_active,
            user.created_at.isoformat() if user.created_at else "",
        ])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)


async def export_jobs_csv(session: AsyncSession) -> AsyncGenerator[str, None]:
    """Export jobs data as CSV stream.

    Yields CSV content line by line for streaming response.
    Max 50,000 records.
    """
    query = select(Job).order_by(Job.created_at.desc()).limit(MAX_CSV_RECORDS)
    result = await session.execute(query)
    jobs = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    header = [
        "id", "company_id", "title", "modality", "location",
        "contract_type", "salary_min", "salary_max", "status",
        "deadline", "created_at",
    ]
    writer.writerow(header)
    yield output.getvalue()
    output.seek(0)
    output.truncate(0)

    # Data rows
    for job in jobs:
        writer.writerow([
            str(job.id),
            str(job.company_id),
            job.title,
            job.modality.value if hasattr(job.modality, "value") else job.modality,
            job.location or "",
            job.contract_type.value if hasattr(job.contract_type, "value") else job.contract_type,
            str(job.salary_min) if job.salary_min else "",
            str(job.salary_max) if job.salary_max else "",
            job.status.value if hasattr(job.status, "value") else job.status,
            job.deadline.isoformat() if job.deadline else "",
            job.created_at.isoformat() if job.created_at else "",
        ])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)


async def export_applications_csv(session: AsyncSession) -> AsyncGenerator[str, None]:
    """Export applications data as CSV stream.

    Yields CSV content line by line for streaming response.
    Max 50,000 records.
    """
    query = (
        select(Application).order_by(Application.applied_at.desc()).limit(MAX_CSV_RECORDS)
    )
    result = await session.execute(query)
    applications = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    header = ["id", "job_id", "candidate_id", "status", "applied_at", "updated_at"]
    writer.writerow(header)
    yield output.getvalue()
    output.seek(0)
    output.truncate(0)

    # Data rows
    for app in applications:
        writer.writerow([
            str(app.id),
            str(app.job_id),
            str(app.candidate_id),
            app.status.value if hasattr(app.status, "value") else app.status,
            app.applied_at.isoformat() if app.applied_at else "",
            app.updated_at.isoformat() if app.updated_at else "",
        ])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)


async def export_payments_csv(session: AsyncSession) -> AsyncGenerator[str, None]:
    """Export payments data as CSV stream.

    Yields CSV content line by line for streaming response.
    Max 50,000 records.
    """
    query = select(Payment).order_by(Payment.created_at.desc()).limit(MAX_CSV_RECORDS)
    result = await session.execute(query)
    payments = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    header = [
        "id", "user_id", "amount", "method", "status",
        "external_reference", "confirmed_at", "created_at",
    ]
    writer.writerow(header)
    yield output.getvalue()
    output.seek(0)
    output.truncate(0)

    # Data rows
    for payment in payments:
        writer.writerow([
            str(payment.id),
            str(payment.user_id),
            str(payment.amount),
            payment.method.value if hasattr(payment.method, "value") else payment.method,
            payment.status.value if hasattr(payment.status, "value") else payment.status,
            payment.external_reference or "",
            payment.confirmed_at.isoformat() if payment.confirmed_at else "",
            payment.created_at.isoformat() if payment.created_at else "",
        ])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)
