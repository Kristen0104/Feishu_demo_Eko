"""Token helpers for backend-issued login sessions."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from ...config import settings


def issue_access_token(payload: dict[str, Any], expires_minutes: int | None = None) -> str:
    now = int(time.time())
    expires_minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    data = {
        **payload,
        "iat": now,
        "exp": now + expires_minutes * 60,
        "iss": "eko",
    }
    encoded = _b64url(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    signature = _sign(encoded)
    return f"eko.{encoded}.{signature}"


def decode_access_token(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != "eko":
        raise ValueError("Invalid access token format")

    encoded, signature = parts[1], parts[2]
    expected = _sign(encoded)
    if not hmac.compare_digest(signature, expected):
        raise ValueError("Invalid access token signature")

    payload = json.loads(_unb64url(encoded).decode("utf-8"))
    exp = int(payload.get("exp", 0))
    if exp and exp < int(time.time()):
        raise ValueError("Access token expired")
    return payload


def parse_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise ValueError("Missing Authorization header")
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise ValueError("Authorization header must use Bearer scheme")
    return authorization[len(prefix) :].strip()


def _sign(encoded: str) -> str:
    digest = hmac.new(settings.SECRET_KEY.encode("utf-8"), encoded.encode("utf-8"), hashlib.sha256).digest()
    return _b64url(digest)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64url(data: str) -> bytes:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))
