"""Encrypted account secret helpers."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from saas_crawler.storage import settings


class SecretKeyError(RuntimeError):
    pass


def _fernet() -> Fernet:
    key = settings.CRAWLER_SECRET_KEY.strip()
    if not key:
        raise SecretKeyError("CRAWLER_SECRET_KEY is required for account secret encryption.")
    try:
        raw = base64.urlsafe_b64decode(key)
        if len(raw) == 32:
            return Fernet(key.encode())
    except Exception:
        pass
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str) -> str:
    return _fernet().decrypt(value.encode("ascii")).decode("utf-8")


def mask_value(value: str | None, *, keep_start: int = 3, keep_end: int = 3) -> str | None:
    if not value:
        return None
    if len(value) <= keep_start + keep_end:
        return "*" * len(value)
    return f"{value[:keep_start]}{'*' * 6}{value[-keep_end:]}"
