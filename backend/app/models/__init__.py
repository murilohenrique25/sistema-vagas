"""SQLAlchemy models package.

All models are imported here so Alembic can detect them for migrations.
"""

from app.core.database import Base  # noqa: F401
from app.models.enums import (  # noqa: F401
    AIAnalysisStatus,
    AIAnalysisType,
    ApplicationStatus,
    ContractType,
    DegreeLevel,
    DeliveryStatus,
    FluencyLevel,
    JobModality,
    JobStatus,
    NotificationChannel,
    PaymentMethod,
    PaymentStatus,
    ProficiencyLevel,
    SubscriptionPlan,
    SubscriptionStatus,
    TokenTransactionType,
    UserRole,
)
from app.models.user import User  # noqa: F401
from app.models.company import Company  # noqa: F401
from app.models.job import Job  # noqa: F401
from app.models.resume import (  # noqa: F401
    Resume,
    Experience,
    Education,
    Skill,
    Certification,
    Language,
)
from app.models.application import Application, ApplicationStatusHistory  # noqa: F401
from app.models.token import TokenTransaction, TokenConfig, TokenPackage  # noqa: F401
from app.models.subscription import Subscription, Payment  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.job_highlight import JobHighlight  # noqa: F401
from app.models.ai_analysis import AIAnalysis  # noqa: F401
from app.models.wallet import WalletTransaction  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.account_action_token import AccountActionToken  # noqa: F401
from app.models.job_report import JobReport  # noqa: F401

__all__ = [
    "Base",
    # Enums
    "AIAnalysisStatus",
    "AIAnalysisType",
    "ApplicationStatus",
    "ContractType",
    "DegreeLevel",
    "DeliveryStatus",
    "FluencyLevel",
    "JobModality",
    "JobStatus",
    "NotificationChannel",
    "PaymentMethod",
    "PaymentStatus",
    "ProficiencyLevel",
    "SubscriptionPlan",
    "SubscriptionStatus",
    "TokenTransactionType",
    "UserRole",
    # Models
    "User",
    "Company",
    "Job",
    "Resume",
    "Experience",
    "Education",
    "Skill",
    "Certification",
    "Language",
    "Application",
    "ApplicationStatusHistory",
    "TokenTransaction",
    "TokenConfig",
    "TokenPackage",
    "Subscription",
    "Payment",
    "WalletTransaction",
    "Notification",
    "JobHighlight",
    "AIAnalysis",
    "AuditLog",
    "AccountActionToken",
    "JobReport",
]
