from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.services.email_sender import SMTPEmailSender


@pytest.mark.asyncio
async def test_smtp_ssl_sender_authenticates_and_sends_message(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "email-ssl.com.br")
    monkeypatch.setattr(settings, "smtp_port", 465)
    monkeypatch.setattr(settings, "smtp_username", "sender@example.com")
    monkeypatch.setattr(settings, "smtp_password", "secret")
    monkeypatch.setattr(settings, "smtp_use_ssl", True)
    monkeypatch.setattr(settings, "smtp_use_tls", False)
    monkeypatch.setattr(settings, "email_from", "sender@example.com")
    monkeypatch.setattr(settings, "email_from_name", "Recruta IA")
    monkeypatch.setattr(settings, "email_reply_to", "support@example.com")

    client = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = client
    with patch("app.services.email_sender.smtplib.SMTP_SSL", return_value=context) as smtp:
        assert await SMTPEmailSender().send_email("user@example.com", "Teste", "Mensagem") is True

    smtp.assert_called_once_with("email-ssl.com.br", 465, timeout=settings.smtp_timeout_seconds)
    client.login.assert_called_once_with("sender@example.com", "secret")
    message = client.send_message.call_args.args[0]
    assert message["From"] == "Recruta IA <sender@example.com>"
    assert message["Reply-To"] == "support@example.com"


@pytest.mark.asyncio
async def test_smtp_failure_is_reported_without_leaking_exception(monkeypatch):
    monkeypatch.setattr(settings, "smtp_use_ssl", True)
    with patch("app.services.email_sender.smtplib.SMTP_SSL", side_effect=OSError("offline")):
        assert await SMTPEmailSender().send_email("user@example.com", "Teste", "Mensagem") is False
