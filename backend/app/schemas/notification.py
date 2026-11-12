"""Notification schemas for API request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import DeliveryStatus, NotificationChannel


class NotificationResponse(BaseModel):
    """Schema for a notification in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    message: str
    channel: NotificationChannel
    is_read: bool
    delivery_attempts: int
    delivery_status: DeliveryStatus
    sent_at: datetime | None = None
    read_at: datetime | None = None
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Paginated list of notifications."""

    items: list[NotificationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UnreadCountResponse(BaseModel):
    """Response for unread notification count."""

    unread_count: int


class MarkAsReadResponse(BaseModel):
    """Response after marking a notification as read."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_read: bool
    read_at: datetime | None = None


class ProcessQueueResponse(BaseModel):
    """Response from processing the notification queue."""

    processed_count: int
    message: str


class RetryNotificationsResponse(BaseModel):
    """Response from retrying failed notifications."""

    retried_count: int
    message: str
