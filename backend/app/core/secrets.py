"""Encryption helpers for secrets managed through the admin panel."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _cipher() -> Fernet:
    source = settings.payment_settings_encryption_key or settings.jwt_secret_key
    key = base64.urlsafe_b64encode(hashlib.sha256(source.encode()).digest())
    return Fernet(key)


def encrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    if value.startswith("enc:v1:"):
        return value
    return "enc:v1:" + _cipher().encrypt(value.encode()).decode()


def decrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    if not value.startswith("enc:v1:"):
        return value  # compatibility with values saved before encryption was introduced
    try:
        return _cipher().decrypt(value.removeprefix("enc:v1:").encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError("Não foi possível descriptografar a credencial de pagamento") from exc
