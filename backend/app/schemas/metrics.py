"""Metrics and KPI schemas for admin panel."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class MetricsPeriod(str, Enum):
    """Time period options for metrics filtering."""

    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"


class PlatformKPIsResponse(BaseModel):
    """Platform KPIs response."""

    period: MetricsPeriod
    start_date: date
    end_date: date
    total_jobs_published: int = Field(description="Total de vagas publicadas no período")
    total_applications: int = Field(description="Total de candidaturas realizadas no período")
    hiring_rate: Decimal = Field(
        description="Taxa de contratação (% com 2 casas decimais)"
    )
    avg_hiring_time_days: Decimal | None = Field(
        default=None,
        description="Tempo médio de contratação em dias",
    )


class FinancialMetricsResponse(BaseModel):
    """Financial metrics response."""

    period: MetricsPeriod
    start_date: date
    end_date: date
    total_revenue: Decimal = Field(description="Receita total no período")
    token_revenue: Decimal = Field(description="Receita com tokens")
    subscription_revenue: Decimal = Field(description="Receita com assinaturas")
    avg_ticket: Decimal = Field(description="Ticket médio por transação")
    total_transactions: int = Field(description="Total de transações no período")


class AIMetricsResponse(BaseModel):
    """AI metrics response."""

    period: MetricsPeriod
    start_date: date
    end_date: date
    total_analyses: int = Field(description="Total de análises realizadas")
    total_tokens_consumed: int = Field(description="Consumo total de tokens para IA")
    avg_score: Decimal | None = Field(
        default=None,
        description="Média de Score de Aderência (2 casas decimais)",
    )
    utilization_by_plan: dict[str, Decimal] = Field(
        default_factory=dict,
        description="Taxa de utilização por plano (%)",
    )
