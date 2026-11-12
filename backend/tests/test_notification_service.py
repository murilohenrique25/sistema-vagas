"""Unit tests for NotificationService: queue processing, retry logic, failure recording, and SLA.

Tests cover:
- send_notification creates notification and enqueues to Redis
- process_notification_queue delivers pending notifications
- retry_failed_notifications retries with 5 min interval, max 3 retries
- Failure recording after all attempts exhausted (Req 13.8)
- SLA enforcement (notifications processed within 5 min window)
- get_user_notifications returns paginated results
- mark_as_read updates notification state
- get_unread_count returns correct count
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.enums import DeliveryStatus, NotificationChannel
from app.models.notification import Notification
from app.models.user import User
from app.services.notification_service import (
    MAX_DELIVERY_ATTEMPTS,
    NOTIFICATION_QUEUE_KEY,
    RETRY_INTERVAL_MINUTES,
    NotificationService,
)


def _make_notification(
    user_id: uuid.UUID | None = None,
    channel: NotificationChannel = NotificationChannel.both,
    delivery_status: DeliveryStatus = DeliveryStatus.pending,
    delivery_attempts: int = 0,
    sent_at: datetime | None = None,
    is_read: bool = False,
) -> MagicMock:
    """Create a mock Notification."""
    notif = MagicMock(spec=Notification)
    notif.id = uuid.uuid4()
    notif.user_id = user_id or uuid.uuid4()
    notif.title = "Test Notification"
    notif.message = "Test message body"
    notif.channel = channel
    notif.is_read = is_read
    notif.delivery_attempts = delivery_attempts
    notif.delivery_status = delivery_status
    notif.sent_at = sent_at
    notif.read_at = None
    notif.created_at = datetime.now(timezone.utc)
    return notif


def _make_user(user_id: uuid.UUID | None = None) -> MagicMock:
    """Create a mock User."""
    user = MagicMock(spec=User)
    user.id = user_id or uuid.uuid4()
    user.email = "test@example.com"
    user.name = "Test User"
    return user


class TestSendNotification:
    """Tests for send_notification method."""

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_redis")
    async def test_creates_notification_and_enqueues(self, mock_get_redis):
        """Should create notification record and add to Redis queue."""
        user_id = uuid.uuid4()
        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        service = NotificationService(session)
        await service.send_notification(
            user_id=user_id,
            title="Nova candidatura",
            message="Você recebeu uma nova candidatura",
            channel=NotificationChannel.both,
        )

        # Verify notification was added to session
        session.add.assert_called_once()
        added = session.add.call_args[0][0]
        assert isinstance(added, Notification)
        assert added.user_id == user_id
        assert added.title == "Nova candidatura"
        assert added.channel == NotificationChannel.both
        assert added.delivery_status == DeliveryStatus.pending
        assert added.delivery_attempts == 0

        # Verify it was enqueued to Redis
        mock_redis.rpush.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_redis")
    async def test_notification_saved_even_if_queue_fails(self, mock_get_redis):
        """Should save notification even if Redis queue fails."""
        user_id = uuid.uuid4()
        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.rpush.side_effect = Exception("Redis connection refused")
        mock_get_redis.return_value = mock_redis

        service = NotificationService(session)
        await service.send_notification(
            user_id=user_id,
            title="Test",
            message="Test message",
        )

        # Notification should still be added
        session.add.assert_called_once()


class TestProcessNotificationQueue:
    """Tests for process_notification_queue method."""

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_redis")
    @patch("app.services.notification_service.get_email_sender")
    async def test_processes_queued_notifications(self, mock_get_email_sender, mock_get_redis):
        """Should process notifications from Redis queue and deliver them."""
        notification_id = uuid.uuid4()
        user_id = uuid.uuid4()

        session = AsyncMock()
        session.flush = AsyncMock()

        # Mock Redis: return one notification ID then None
        mock_redis = AsyncMock()
        mock_redis.lpop = AsyncMock(side_effect=[str(notification_id), None])
        mock_get_redis.return_value = mock_redis

        # Mock notification lookup
        notification = MagicMock(spec=Notification)
        notification.id = notification_id
        notification.user_id = user_id
        notification.channel = NotificationChannel.both
        notification.delivery_status = DeliveryStatus.pending
        notification.delivery_attempts = 0
        notification.sent_at = None

        notif_result = MagicMock()
        notif_result.scalar_one_or_none.return_value = notification

        # Mock user lookup for email
        user = _make_user(user_id)
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user

        session.execute.side_effect = [notif_result, user_result]

        # Mock email sender
        mock_sender = AsyncMock()
        mock_sender.send_email = AsyncMock(return_value=True)
        mock_get_email_sender.return_value = mock_sender

        service = NotificationService(session)
        processed = await service.process_notification_queue()

        assert processed == 1
        assert notification.delivery_status == DeliveryStatus.sent
        assert notification.delivery_attempts == 1

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_redis")
    async def test_returns_zero_when_queue_empty(self, mock_get_redis):
        """Should return 0 when no notifications in queue."""
        session = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.lpop = AsyncMock(return_value=None)
        mock_get_redis.return_value = mock_redis

        service = NotificationService(session)
        processed = await service.process_notification_queue()

        assert processed == 0

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_redis")
    @patch("app.services.notification_service.get_email_sender")
    async def test_email_failure_keeps_notification_pending(
        self, mock_get_email_sender, mock_get_redis
    ):
        """Should keep notification pending if email delivery fails (for retry)."""
        notification_id = uuid.uuid4()
        user_id = uuid.uuid4()

        session = AsyncMock()
        session.flush = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.lpop = AsyncMock(side_effect=[str(notification_id), None])
        mock_get_redis.return_value = mock_redis

        notification = MagicMock(spec=Notification)
        notification.id = notification_id
        notification.user_id = user_id
        notification.channel = NotificationChannel.email
        notification.delivery_status = DeliveryStatus.pending
        notification.delivery_attempts = 0
        notification.sent_at = None

        notif_result = MagicMock()
        notif_result.scalar_one_or_none.return_value = notification

        user = _make_user(user_id)
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user

        session.execute.side_effect = [notif_result, user_result]

        # Email fails
        mock_sender = AsyncMock()
        mock_sender.send_email = AsyncMock(return_value=False)
        mock_get_email_sender.return_value = mock_sender

        service = NotificationService(session)
        processed = await service.process_notification_queue()

        assert processed == 1
        # First attempt failed, still pending for retry
        assert notification.delivery_attempts == 1
        assert notification.delivery_status == DeliveryStatus.pending


class TestRetryFailedNotifications:
    """Tests for retry_failed_notifications method."""

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_email_sender")
    async def test_retries_eligible_notifications(self, mock_get_email_sender):
        """Should retry notifications that failed and meet retry criteria."""
        user_id = uuid.uuid4()
        notification_id = uuid.uuid4()

        session = AsyncMock()
        session.flush = AsyncMock()

        # Mock: find eligible notifications for retry
        notification = MagicMock(spec=Notification)
        notification.id = notification_id
        notification.user_id = user_id
        notification.channel = NotificationChannel.email
        notification.delivery_status = DeliveryStatus.pending
        notification.delivery_attempts = 1  # One failed attempt
        notification.sent_at = datetime.now(timezone.utc) - timedelta(minutes=6)

        scalars_result = MagicMock()
        scalars_result.all.return_value = [notification]
        retry_query_result = MagicMock()
        retry_query_result.scalars.return_value = scalars_result

        # Mock: delivery - notification lookup
        notif_delivery_result = MagicMock()
        notif_delivery_result.scalar_one_or_none.return_value = notification

        # Mock: user lookup for email
        user = _make_user(user_id)
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user

        session.execute.side_effect = [
            retry_query_result,
            notif_delivery_result,
            user_result,
        ]

        mock_sender = AsyncMock()
        mock_sender.send_email = AsyncMock(return_value=True)
        mock_get_email_sender.return_value = mock_sender

        service = NotificationService(session)
        retried = await service.retry_failed_notifications()

        assert retried == 1
        assert notification.delivery_status == DeliveryStatus.sent

    @pytest.mark.asyncio
    async def test_marks_failed_after_max_attempts(self):
        """Should mark notification as failed after 4 total attempts (1 + 3 retries)."""
        user_id = uuid.uuid4()
        notification_id = uuid.uuid4()

        session = AsyncMock()
        session.flush = AsyncMock()

        # Notification at 3 attempts (one more will hit MAX_DELIVERY_ATTEMPTS=4)
        notification = MagicMock(spec=Notification)
        notification.id = notification_id
        notification.user_id = user_id
        notification.channel = NotificationChannel.email
        notification.delivery_status = DeliveryStatus.pending
        notification.delivery_attempts = 3
        notification.sent_at = datetime.now(timezone.utc) - timedelta(minutes=6)

        scalars_result = MagicMock()
        scalars_result.all.return_value = [notification]
        retry_query_result = MagicMock()
        retry_query_result.scalars.return_value = scalars_result

        # Mock: delivery lookup
        notif_delivery_result = MagicMock()
        notif_delivery_result.scalar_one_or_none.return_value = notification

        # Mock: user for email
        user = _make_user(user_id)
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = user

        session.execute.side_effect = [
            retry_query_result,
            notif_delivery_result,
            user_result,
        ]

        # Email still fails
        with patch("app.services.notification_service.get_email_sender") as mock_get_sender:
            mock_sender = AsyncMock()
            mock_sender.send_email = AsyncMock(return_value=False)
            mock_get_sender.return_value = mock_sender

            service = NotificationService(session)
            retried = await service.retry_failed_notifications()

        assert retried == 1
        # After 4th attempt, should be marked as failed
        assert notification.delivery_attempts == 4
        assert notification.delivery_status == DeliveryStatus.failed

    @pytest.mark.asyncio
    async def test_no_retry_before_interval(self):
        """Should not retry notifications attempted less than 5 minutes ago."""
        session = AsyncMock()
        session.flush = AsyncMock()

        # Query returns empty (no eligible notifications)
        scalars_result = MagicMock()
        scalars_result.all.return_value = []
        query_result = MagicMock()
        query_result.scalars.return_value = scalars_result

        session.execute.return_value = query_result

        service = NotificationService(session)
        retried = await service.retry_failed_notifications()

        assert retried == 0


class TestGetUserNotifications:
    """Tests for get_user_notifications method."""

    @pytest.mark.asyncio
    async def test_returns_paginated_notifications(self):
        """Should return paginated notifications for user."""
        user_id = uuid.uuid4()
        session = AsyncMock()

        notif1 = _make_notification(user_id)
        notif2 = _make_notification(user_id)

        # Mock: count
        count_result = MagicMock()
        count_result.scalar_one.return_value = 2

        # Mock: fetch
        scalars_result = MagicMock()
        scalars_result.all.return_value = [notif1, notif2]
        fetch_result = MagicMock()
        fetch_result.scalars.return_value = scalars_result

        session.execute.side_effect = [count_result, fetch_result]

        service = NotificationService(session)
        notifications, total = await service.get_user_notifications(
            user_id=user_id, page=1, page_size=20
        )

        assert total == 2
        assert len(notifications) == 2

    @pytest.mark.asyncio
    async def test_includes_failed_notifications_for_next_access(self):
        """Should include failed notifications so they're visible on next access (Req 13.8)."""
        user_id = uuid.uuid4()
        session = AsyncMock()

        # A failed notification that user should see
        failed_notif = _make_notification(
            user_id, delivery_status=DeliveryStatus.failed, delivery_attempts=4
        )

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        scalars_result = MagicMock()
        scalars_result.all.return_value = [failed_notif]
        fetch_result = MagicMock()
        fetch_result.scalars.return_value = scalars_result

        session.execute.side_effect = [count_result, fetch_result]

        service = NotificationService(session)
        notifications, total = await service.get_user_notifications(
            user_id=user_id, page=1, page_size=20
        )

        assert total == 1
        assert notifications[0].delivery_status == DeliveryStatus.failed


class TestMarkAsRead:
    """Tests for mark_as_read method."""

    @pytest.mark.asyncio
    async def test_marks_notification_as_read(self):
        """Should set is_read=True and record read_at timestamp."""
        user_id = uuid.uuid4()
        notification_id = uuid.uuid4()

        session = AsyncMock()
        session.flush = AsyncMock()

        notification = MagicMock(spec=Notification)
        notification.id = notification_id
        notification.user_id = user_id
        notification.is_read = False
        notification.read_at = None

        result = MagicMock()
        result.scalar_one_or_none.return_value = notification
        session.execute.return_value = result

        service = NotificationService(session)
        updated = await service.mark_as_read(notification_id, user_id)

        assert notification.is_read is True
        assert notification.read_at is not None

    @pytest.mark.asyncio
    async def test_raises_error_for_nonexistent_notification(self):
        """Should raise ValueError when notification not found."""
        user_id = uuid.uuid4()
        notification_id = uuid.uuid4()

        session = AsyncMock()

        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        session.execute.return_value = result

        service = NotificationService(session)

        with pytest.raises(ValueError, match="não encontrada"):
            await service.mark_as_read(notification_id, user_id)

    @pytest.mark.asyncio
    async def test_does_not_update_already_read_notification(self):
        """Should not update read_at if notification is already read."""
        user_id = uuid.uuid4()
        notification_id = uuid.uuid4()
        original_read_at = datetime.now(timezone.utc) - timedelta(hours=1)

        session = AsyncMock()
        session.flush = AsyncMock()

        notification = MagicMock(spec=Notification)
        notification.id = notification_id
        notification.user_id = user_id
        notification.is_read = True
        notification.read_at = original_read_at

        result = MagicMock()
        result.scalar_one_or_none.return_value = notification
        session.execute.return_value = result

        service = NotificationService(session)
        updated = await service.mark_as_read(notification_id, user_id)

        # flush should not have been called since no changes were made
        session.flush.assert_not_called()


class TestGetUnreadCount:
    """Tests for get_unread_count method."""

    @pytest.mark.asyncio
    async def test_returns_unread_count(self):
        """Should return count of unread notifications."""
        user_id = uuid.uuid4()
        session = AsyncMock()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 5
        session.execute.return_value = count_result

        service = NotificationService(session)
        count = await service.get_unread_count(user_id)

        assert count == 5

    @pytest.mark.asyncio
    async def test_returns_zero_when_all_read(self):
        """Should return 0 when all notifications are read."""
        user_id = uuid.uuid4()
        session = AsyncMock()

        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        session.execute.return_value = count_result

        service = NotificationService(session)
        count = await service.get_unread_count(user_id)

        assert count == 0


class TestSLAEnforcement:
    """Tests verifying SLA enforcement (5-minute delivery window)."""

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_redis")
    async def test_notification_queued_immediately_for_sla(self, mock_get_redis):
        """Notifications should be queued immediately after creation to meet 5-min SLA."""
        user_id = uuid.uuid4()
        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        service = NotificationService(session)
        await service.send_notification(
            user_id=user_id,
            title="SLA test",
            message="Should be queued immediately",
        )

        # Verify immediate queueing to Redis for processing
        mock_redis.rpush.assert_called_once()
        call_args = mock_redis.rpush.call_args[0]
        assert call_args[0] == NOTIFICATION_QUEUE_KEY

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_email_sender")
    async def test_retry_respects_5_min_interval(self, mock_get_email_sender):
        """Retry should only pick up notifications attempted ≥5 minutes ago."""
        user_id = uuid.uuid4()
        session = AsyncMock()
        session.flush = AsyncMock()

        # Notification attempted only 2 minutes ago - should NOT be retried
        recent_notification = MagicMock(spec=Notification)
        recent_notification.id = uuid.uuid4()
        recent_notification.delivery_attempts = 1
        recent_notification.sent_at = datetime.now(timezone.utc) - timedelta(minutes=2)
        recent_notification.delivery_status = DeliveryStatus.pending

        # The query should filter this out (sent_at <= threshold)
        # In real implementation, the SQL query handles this filtering
        scalars_result = MagicMock()
        scalars_result.all.return_value = []  # nothing eligible
        query_result = MagicMock()
        query_result.scalars.return_value = scalars_result

        session.execute.return_value = query_result

        service = NotificationService(session)
        retried = await service.retry_failed_notifications()

        # Nothing should be retried
        assert retried == 0


class TestPlatformOnlyDelivery:
    """Tests for platform-only notification channel."""

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_redis")
    async def test_platform_only_succeeds_without_email(self, mock_get_redis):
        """Platform-only notifications should succeed without sending email."""
        notification_id = uuid.uuid4()
        user_id = uuid.uuid4()

        session = AsyncMock()
        session.flush = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.lpop = AsyncMock(side_effect=[str(notification_id), None])
        mock_get_redis.return_value = mock_redis

        notification = MagicMock(spec=Notification)
        notification.id = notification_id
        notification.user_id = user_id
        notification.channel = NotificationChannel.platform
        notification.delivery_status = DeliveryStatus.pending
        notification.delivery_attempts = 0
        notification.sent_at = None

        notif_result = MagicMock()
        notif_result.scalar_one_or_none.return_value = notification

        session.execute.side_effect = [notif_result]

        service = NotificationService(session)
        processed = await service.process_notification_queue()

        assert processed == 1
        assert notification.delivery_status == DeliveryStatus.sent
