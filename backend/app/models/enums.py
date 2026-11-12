"""Enum definitions for all model fields."""

import enum


class UserRole(str, enum.Enum):
    """User roles in the platform."""
    employer = "employer"
    candidate = "candidate"
    admin = "admin"


class JobModality(str, enum.Enum):
    """Job modality options."""
    remote = "remote"
    hybrid = "hybrid"
    onsite = "onsite"


class ContractType(str, enum.Enum):
    """Contract type options."""
    clt = "clt"
    pj = "pj"
    temporary = "temporary"
    internship = "internship"


class JobStatus(str, enum.Enum):
    """Job status options."""
    active = "active"
    inactive = "inactive"
    closed = "closed"
    draft = "draft"


class DegreeLevel(str, enum.Enum):
    """Education degree levels."""
    high_school = "high_school"
    bachelor = "bachelor"
    master = "master"
    doctorate = "doctorate"
    technical = "technical"


class ProficiencyLevel(str, enum.Enum):
    """Skill proficiency levels."""
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"


class FluencyLevel(str, enum.Enum):
    """Language fluency levels."""
    basic = "basic"
    intermediate = "intermediate"
    advanced = "advanced"
    native = "native"


class ApplicationStatus(str, enum.Enum):
    """Application status options."""
    received = "received"
    in_review = "in_review"
    interview = "interview"
    technical_test = "technical_test"
    proposal = "proposal"
    hired = "hired"
    rejected = "rejected"
    cancelled = "cancelled"


class TokenTransactionType(str, enum.Enum):
    """Token transaction types."""
    credit = "credit"
    debit = "debit"
    refund = "refund"


class SubscriptionPlan(str, enum.Enum):
    """Subscription plan options."""
    free = "free"
    professional = "professional"
    enterprise = "enterprise"


class SubscriptionStatus(str, enum.Enum):
    """Subscription status options."""
    active = "active"
    suspended = "suspended"
    cancelled = "cancelled"


class PaymentMethod(str, enum.Enum):
    """Payment method options."""
    pix = "pix"
    credit_card = "credit_card"
    checkout_pro = "checkout_pro"


class PaymentStatus(str, enum.Enum):
    """Payment status options."""
    pending = "pending"
    confirmed = "confirmed"
    failed = "failed"
    expired = "expired"
    cancelled = "cancelled"


class NotificationChannel(str, enum.Enum):
    """Notification channel options."""
    platform = "platform"
    email = "email"
    both = "both"


class DeliveryStatus(str, enum.Enum):
    """Notification delivery status."""
    pending = "pending"
    sent = "sent"
    failed = "failed"


class AIAnalysisType(str, enum.Enum):
    """AI analysis type options."""
    candidate_analysis = "candidate_analysis"
    job_matching = "job_matching"


class AIAnalysisStatus(str, enum.Enum):
    """AI analysis status options."""
    processing = "processing"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"
