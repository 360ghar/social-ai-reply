"""Fernet-based encryption for secrets storage."""

import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import get_settings


def _build_fernet() -> Fernet:
    settings = get_settings()
    if not settings.encryption_key:
        raise RuntimeError("ENCRYPTION_KEY must be set to use encryption features. Generate one with: python -c \"import base64, hashlib, secrets; print(base64.urlsafe_b64encode(hashlib.sha256(secrets.token_bytes(32)).digest()).decode())\"")
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.encryption_key.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_text(value: str) -> str:
    return _build_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_text(value: str) -> str:
    return _build_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
