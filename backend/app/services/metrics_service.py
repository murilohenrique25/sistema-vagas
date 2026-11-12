"""Metrics and KPIs service for admin dashboard."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_analysis import AIAnalysis
from app.models.application import Application, ApplicationStatusHistory
from app.models.enums import (
    AIAnalysisStatus,
    ApplicationStatus,
    PaymentStatus,
    SubscriptionPlan,
)
from app.models.job import Job
from app.models.subscription import Payment, Subscription
from app.models.token import TokenTransaction
from app.models.user import User
from app.schemas.metrics import (
    AIMetricsResponse,
    FinancialMetricsResponse,
    MetricsPeriod,
    PlatformKPIsResponse,
)


def _calculate_date_range(period: MetricsPeriod) -> tuple[date, date]:
    """Calculate start and end date based on the period."""
    today = date.today()
    end_date = today

    if period == MetricsPeriod.daily:
        start_date = today
    elif period == MetricsPeriod.weekly:
        start_date = today - timedelta(days=7)
    elif period == MetricsPeriod.monthly:
        start_date = today - timedelta(days=30)
    elif period == MetricsPeriod.quarterly:
        start_date = today - timedelta(days=90)
    elif period == MetricsPeriod.yearly:
        start_date = today - timedelta(days=365)
    else:
        start_date = today - timedelta(days=30)

    return start_date, end_date


async def get_platform_kpis(
    session: AsyncSession, period: MetricsPeriod
) -> PlatformKPIsResponse:
    """Calculate platform KPIs for the given period.

    KPIs:
    - Total vagas publicadas
    - Total candidaturas realizadas
    - Taxa de contratação (%)
    - Tempo médio de contratação (dias)
    """
    start_date, end_date = _calculate_date_range(period)

    start_dt = datetime.combine(start_date, datetime.min.time()).replace(
        tzinfo=timezone.utc
    )
    end_dt = datetime.combine(end_date, datetime.max.time()).replace(
        tzinfo=timezone.utc
    )

    # Total jobs published in period
    jobs_query = select(func.count(Job.id)).where(
        Job.created_at >= start_dt,
        Job.created_at <= end_dt,
    )
    total_jobs = (await session.execute(jobs_query)).scalar_one() or 0

    # Total applications in period
    apps_query = select(func.count(Application.id)).where(
        Application.applied_at >= start_dt,
        Application.applied_at <= end_dt,
    )
    total_applications = (await session.execute(apps_query)).scalar_one() or 0

    # Hiring rate: hired / total applications in period
    hired_query = select(func.count(Application.id)).where(
        Application.applied_at >= start_dt,
        Application.applied_at <= end_dt,
        Application.status == ApplicationStatus.hired,
    )
    total_hired = (await session.execute(hired_query)).scalar_one() or 0

    if total_applications > 0:
        hiring_rate = Decimal(total_hired * 100) / Decimal(total_applications)
        hiring_rate = hiring_rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        hiring_rate = Decimal("0.00")

    # Average hiring time: days between job creation and "hired" status change
    # We look at ApplicationStatusHistory where new_status = hired in the period
    avg_time_query = select(
        func.avg(
            func.extract(
                "epoch",
                ApplicationStatusHistory.changed_at - Job.created_at,
            )
            / 86400  # Convert seconds to days
        )
    ).select_from(
        ApplicationStatusHistory.__table__.join(
            Application.__table__,
            ApplicationStatusHistory.application_id == Application.id,
        ).join(
            Job.__table__,
            Application.job_id == Job.id,
        )
    ).where(
        ApplicationStatusHistory.new_status == ApplicationStatus.hired,
        ApplicationStatusHistory.changed_at >= start_dt,
        ApplicationStatusHistory.changed_at <= end_dt,
    )

    avg_hiring_time = (await session.execute(avg_time_query)).scalar_one()

    avg_hiring_time_days: Decimal | None = None
    if avg_hiring_time is not None:
        avg_hiring_time_days = Decimal(str(avg_hiring_time)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    return PlatformKPIsResponse(
        period=period,
        start_date=start_date,
        end_date=end_date,
        total_jobs_published=total_jobs,
        total_applications=total_applications,
        hiring_rate=hiring_rate,
        avg_hiring_time_days=avg_hiring_time_days,
    )


async def get_financial_metrics(
    session: AsyncSession, period: MetricsPeriod
) -> FinancialMetricsResponse:
    """Calculate financial metrics for the given period.

    Metrics:
    - Receita total (tokens + assinaturas)
    - Receita com tokens
    - Receita com assinaturas
    - Ticket médio
    """
    start_date, end_date = _calculate_date_range(period)

    start_dt = datetime.combine(start_date, datetime.min.time()).replace(
        tzinfo=timezone.utc
    )
    end_dt = datetime.combine(end_date, datetime.max.time()).replace(
        tzinfo=timezone.utc
    )

    # All confirmed payments in period
    payments_query = select(
        func.coalesce(func.sum(Payment.amount), Decimal("0.00")).label("total"),
        func.count(Payment.id).label("count"),
    ).where(
        Payment.status == PaymentStatus.confirmed,
        Payment.created_at >= start_dt,
        Payment.created_at <= end_dt,
    )
    result = await session.execute(payments_query)
    row = result.one()
    total_revenue = row.total or Decimal("0.00")
    total_transactions = row.count or 0

    # Token revenue: payments linked to token purchases
    # We identify token purchases by checking TokenTransaction credits in the period
    # But simpler: use payments that are associated with token purchases
    # For simplicity, we'll categorize based on a heuristic:
    # Subscription payments have a reference to subscription, token purchases to tokens
    # Since we don't have an explicit "purpose" field, let's use all confirmed payments
    # and separate by checking if user has subscription payments in period

    # Subscription revenue: payments from users who had subscription upgrades
    # For a practical approach, we'll estimate:
    # - Subscription revenue = payments where user has active non-free subscription
    # - Token revenue = total - subscription revenue
    # This is a simplification. In production, you'd add a "purpose" field to Payment.

    # Get subscription payment amounts (users with non-free active subscriptions)
    sub_revenue_query = select(
        func.coalesce(func.sum(Payment.amount), Decimal("0.00"))
    ).select_from(
        Payment.__table__.join(
            Subscription.__table__,
            and_(
                Payment.user_id == Subscription.user_id,
                Subscription.plan != SubscriptionPlan.free,
            ),
        )
    ).where(
        Payment.status == PaymentStatus.confirmed,
        Payment.created_at >= start_dt,
        Payment.created_at <= end_dt,
    )
    subscription_revenue = (await session.execute(sub_revenue_query)).scalar_one() or Decimal("0.00")

    token_revenue = total_revenue - subscription_revenue
    if token_revenue < Decimal("0.00"):
        token_revenue = Decimal("0.00")

    # Average ticket
    if total_transactions > 0:
        avg_ticket = total_revenue / Decimal(total_transactions)
        avg_ticket = avg_ticket.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        avg_ticket = Decimal("0.00")

    return FinancialMetricsResponse(
        period=period,
        start_date=start_date,
        end_date=end_date,
        total_revenue=total_revenue,
        token_revenue=token_revenue,
        subscription_revenue=subscription_revenue,
        avg_ticket=avg_ticket,
        total_transactions=total_transactions,
    )


async def get_ai_metrics(
    session: AsyncSession, period: MetricsPeriod
) -> AIMetricsResponse:
    """Calculate AI metrics for the given period.

    Metrics:
    - Total de análises realizadas
    - Consumo total de tokens para IA
    - Média de Score de Aderência
    - Taxa de utilização por plano
    """
    start_date, end_date = _calculate_date_range(period)

    start_dt = datetime.combine(start_date, datetime.min.time()).replace(
        tzinfo=timezone.utc
    )
    end_dt = datetime.combine(end_date, datetime.max.time()).replace(
        tzinfo=timezone.utc
    )

    # Total analyses and token consumption
    analyses_query = select(
        func.count(AIAnalysis.id).label("total"),
        func.coalesce(func.sum(AIAnalysis.tokens_consumed), 0).label("tokens"),
    ).where(
        AIAnalysis.created_at >= start_dt,
        AIAnalysis.created_at <= end_dt,
        AIAnalysis.status == AIAnalysisStatus.completed,
    )
    result = await session.execute(analyses_query)
    row = result.one()
    total_analyses = row.total or 0
    total_tokens_consumed = row.tokens or 0

    # Average score from AI analysis results (candidate_analysis type)
    # The result field is JSONB, scores are stored in result -> candidates -> score
    # For simplicity, we extract from the result JSONB where available
    # In practice, the average score would be computed from individual scores in result
    avg_score_query = select(
        func.avg(AIAnalysis.tokens_consumed)  # placeholder - real impl would parse JSONB
    ).where(
        AIAnalysis.created_at >= start_dt,
        AIAnalysis.created_at <= end_dt,
        AIAnalysis.status == AIAnalysisStatus.completed,
        AIAnalysis.result.isnot(None),
    )

    # A more practical approach: count analyses per subscription plan
    # Utilization by plan: percentage of analyses from each plan
    plan_query = select(
        Subscription.plan,
        func.count(AIAnalysis.id).label("count"),
    ).select_from(
        AIAnalysis.__table__.join(
            User.__table__,
            AIAnalysis.requester_id == User.id,
        ).outerjoin(
            Subscription.__table__,
            and_(
                User.id == Subscription.user_id,
                Subscription.status == "active",
            ),
        )
    ).where(
        AIAnalysis.created_at >= start_dt,
        AIAnalysis.created_at <= end_dt,
        AIAnalysis.status == AIAnalysisStatus.completed,
    ).group_by(Subscription.plan)

    plan_result = await session.execute(plan_query)
    plan_rows = plan_result.all()

    utilization_by_plan: dict[str, Decimal] = {}
    if total_analyses > 0:
        for plan_row in plan_rows:
            plan_name = plan_row.plan.value if plan_row.plan else "free"
            pct = Decimal(plan_row.count * 100) / Decimal(total_analyses)
            utilization_by_plan[plan_name] = pct.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
    else:
        for plan in SubscriptionPlan:
            utilization_by_plan[plan.value] = Decimal("0.00")

    # For avg_score, we'd need to parse JSONB results.
    # As a practical placeholder, set to None if no data
    avg_score: Decimal | None = None

    return AIMetricsResponse(
        period=period,
        start_date=start_date,
        end_date=end_date,
        total_analyses=total_analyses,
        total_tokens_consumed=total_tokens_consumed,
        avg_score=avg_score,
        utilization_by_plan=utilization_by_plan,
    )
