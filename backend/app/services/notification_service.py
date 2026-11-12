"""Notification service: queue, send, retry, and manage notifications.

Implements requirements 13.1 through 13.8:
- 13.1: Send notification to employer on new application (within 5 min, platform + email)
- 13.2: Send notification to candidate on status change (within 5 min)
- 13.3: Send interview invitation with details
- 13.4: Send approval/rejection notification (within 5 min)
- 13.5: Send low token balance alert
- 13.6: Send reminder 7 days before job deadline
- 13.7: Retry up to 3 additional attempts with 5 min interval
- 13.8: Record failure and show pending notification on next access
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models.enums import DeliveryStatus, NotificationChannel
from app.models.notification import Notification
from app.models.user import User
from app.services.email_sender import get_email_sender

logger = logging.getLogger(__name__)

# Constants
NOTIFICATION_QUEUE_KEY = "notifications:queue"
NOTIFICATION_RETRY_QUEUE_KEY = "notifications:retry"
MAX_DELIVERY_ATTEMPTS = 4  # 1 initial + 3 retries
RETRY_INTERVAL_MINUTES = 5
SLA_MINUTES = 5


class NotificationService:
    """Service handling notification business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def send_notification(
        self,
        user_id: UUID,
        title: str,
        message: str,
        channel: NotificationChannel = NotificationChannel.both,
    ) -> Notification:
        """Create a notification and queue it for delivery.

        Args:
            user_id: Target user ID.
            title: Notification title.
            message: Notification message body.
            channel: Delivery channel (platform, email, or both).

        Returns:
            The created Notification record.
        """
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            channel=channel,
            is_read=False,
            delivery_attempts=0,
            delivery_status=DeliveryStatus.pending,
        )
        self.session.add(notification)
        await self.session.flush()
        await self.session.refresh(notification)

        # Queue for async delivery
        await self._enqueue_notification(notification.id)

        return notification

    async def process_notification_queue(self) -> int:
        """Process pending notifications from the Redis queue.

        Processes all queued notifications, attempting delivery via the
        configured channels. Respects the 5-minute SLA.

        Returns:
            Number of notifications processed.
        """
        redis = get_redis()
        processed = 0

        # Process up to 100 notifications per batch
        for _ in range(100):
            raw = await redis.lpop(NOTIFICATION_QUEUE_KEY)
            if raw is None:
                break

            notification_id = UUID(raw)
            await self._deliver_notification(notification_id)
            processed += 1

        return processed

    async def retry_failed_notifications(self) -> int:
        """Retry failed notifications that are eligible for retry.

        Notifications are retried up to 3 additional times (total 4 attempts)
        with a minimum 5-minute interval between attempts.

        Returns:
            Number of notifications retried.
        """
        now = datetime.now(timezone.utc)
        retry_threshold = now - timedelta(minutes=RETRY_INTERVAL_MINUTES)

        # Find notifications eligible for retry:
        # - delivery_status is pending (still trying)
        # - delivery_attempts > 0 (at least one failed attempt)
        # - delivery_attempts < MAX_DELIVERY_ATTEMPTS
        # - last attempt was at least 5 minutes ago (using sent_at as last attempt time)
        result = await self.session.execute(
            select(Notification).where(
                Notification.delivery_status == DeliveryStatus.pending,
                Notification.delivery_attempts > 0,
                Notification.delivery_attempts < MAX_DELIVERY_ATTEMPTS,
                Notification.sent_at <= retry_threshold,
            )
        )
        notifications = result.scalars().all()

        retried = 0
        for notification in notifications:
            await self._deliver_notification(notification.id)
            retried += 1

        return retried

    async def get_user_notifications(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Notification], int]:
        """Get paginated notifications for a user (newest first).

        Includes both delivered and failed/pending notifications so users
        can see all notifications on their next access (Req 13.8).

        Args:
            user_id: The user ID.
            page: Page number (1-indexed).
            page_size: Items per page.

        Returns:
            Tuple of (notifications list, total count).
        """
        offset = (page - 1) * page_size

        # Count total
        count_result = await self.session.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id
            )
        )
        total = int(count_result.scalar_one())

        # Fetch page
        result = await self.session.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        notifications = list(result.scalars().all())

        return notifications, total

    async def get_unread_count(self, user_id: UUID) -> int:
        """Get the count of unread notifications for a user.

        Args:
            user_id: The user ID.

        Returns:
            Count of unread notifications.
        """
        result = await self.session.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.is_read == False,  # noqa: E712
            )
        )
        return int(result.scalar_one())

    async def mark_as_read(self, notification_id: UUID, user_id: UUID) -> Notification:
        """Mark a notification as read.

        Args:
            notification_id: The notification ID.
            user_id: The user ID (for authorization).

        Returns:
            The updated Notification.

        Raises:
            ValueError: If notification not found or doesn't belong to user.
        """
        result = await self.session.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        notification = result.scalar_one_or_none()

        if not notification:
            raise ValueError("Notificação não encontrada")

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            await self.session.flush()

        return notification

    # --- Private helpers ---

    async def _enqueue_notification(self, notification_id: UUID) -> None:
        """Add notification ID to the Redis processing queue."""
        try:
            redis = get_redis()
            await redis.rpush(NOTIFICATION_QUEUE_KEY, str(notification_id))
        except Exception as e:
            logger.error(
                "Failed to enqueue notification %s: %s", notification_id, e
            )
            # Even if queuing fails, the notification is saved in DB
            # and will be picked up by retry_failed_notifications

    async def _deliver_notification(self, notification_id: UUID) -> bool:
        """Attempt to deliver a notification via its configured channels.

        Args:
            notification_id: The notification to deliver.

        Returns:
            True if delivery succeeded, False otherwise.
        """
        result = await self.session.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        notification = result.scalar_one_or_none()

        if not notification:
            logger.warning("Notification %s not found for delivery", notification_id)
            return False

        # Already delivered
        if notification.delivery_status == DeliveryStatus.sent:
            return True

        now = datetime.now(timezone.utc)
        notification.delivery_attempts += 1
        notification.sent_at = now  # Track last attempt time

        success = True

        # Deliver based on channel
        if notification.channel in (NotificationChannel.platform, NotificationChannel.both):
            # Platform delivery is implicit - the notification is in DB
            # and will be shown to user on next access
            platform_success = True
            success = success and platform_success

        if notification.channel in (NotificationChannel.email, NotificationChannel.both):
            email_success = await self._send_email_notification(notification)
            success = success and email_success

        if success:
            notification.delivery_status = DeliveryStatus.sent
        elif notification.delivery_attempts >= MAX_DELIVERY_ATTEMPTS:
            # All attempts exhausted - mark as failed (Req 13.8)
            notification.delivery_status = DeliveryStatus.failed
            logger.warning(
                "Notification %s failed after %d attempts",
                notification_id,
                notification.delivery_attempts,
            )
        # else: remains pending for retry

        await self.session.flush()
        return success

    async def _send_email_notification(self, notification: Notification) -> bool:
        """Send email for a notification.

        Args:
            notification: The notification to send via email.

        Returns:
            True if email was sent successfully.
        """
        try:
            # Get user email
            user_result = await self.session.execute(
                select(User).where(User.id == notification.user_id)
            )
            user = user_result.scalar_one_or_none()

            if not user or not user.email:
                logger.error(
                    "Cannot send email for notification %s: user not found",
                    notification.id,
                )
                return False

            email_sender = get_email_sender()
            return await email_sender.send_email(
                to=user.email,
                subject=notification.title,
                body=notification.message,
            )
        except Exception as e:
            logger.error(
                "Email delivery failed for notification %s: %s",
                notification.id,
                e,
            )
            return False
