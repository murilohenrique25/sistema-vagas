"""Email sender abstraction and dev implementation.

Provides an interface for sending emails and a mock/dev implementation
that logs emails without real SMTP connectivity.
"""

import asyncio
import logging
import smtplib
from abc import ABC, abstractmethod
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailSenderBase(ABC):
    """Abstract interface for sending emails."""

    @abstractmethod
    async def send_email(self, to: str, subject: str, body: str) -> bool:
        """Send an email.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            body: Email body content.

        Returns:
            True if email was sent successfully, False otherwise.
        """
        ...


class DevEmailSender(EmailSenderBase):
    """Development email sender that logs emails instead of sending them.

    Used in development/testing environments where no real SMTP is configured.
    """

    async def send_email(self, to: str, subject: str, body: str) -> bool:
        """Log the email details instead of actually sending.

        Always returns True to simulate successful delivery in dev mode.
        """
        logger.info(
            "📧 [DEV EMAIL] To: %s | Subject: %s | Body: %s",
            to,
            subject,
            body[:200],
        )
        return True


class SMTPEmailSender(EmailSenderBase):
    """Authenticated SMTP sender for transactional messages."""

    async def send_email(self, to: str, subject: str, body: str) -> bool:
        try:
            await asyncio.to_thread(self._send_sync, to, subject, body)
            return True
        except Exception:
            logger.exception("Falha ao enviar e-mail SMTP para %s", to)
            return False

    def _send_sync(self, to: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = formataddr((settings.email_from_name, settings.email_from))
        message["To"] = to
        message["Subject"] = subject
        if settings.email_reply_to:
            message["Reply-To"] = settings.email_reply_to
        message.set_content(body)

        smtp_class = smtplib.SMTP_SSL if settings.smtp_use_ssl else smtplib.SMTP
        with smtp_class(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds) as client:
            if settings.smtp_use_tls:
                client.ehlo()
                client.starttls()
                client.ehlo()
            client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(message)


# Singleton instance used across the application
_email_sender: EmailSenderBase | None = None


def get_email_sender() -> EmailSenderBase:
    """Get the configured email sender instance.

    Returns:
        The email sender instance (DevEmailSender by default).
    """
    global _email_sender
    if _email_sender is None:
        _email_sender = SMTPEmailSender() if settings.smtp_enabled else DevEmailSender()
    return _email_sender


def set_email_sender(sender: EmailSenderBase) -> None:
    """Override the email sender (useful for testing).

    Args:
        sender: The email sender implementation to use.
    """
    global _email_sender
    _email_sender = sender
