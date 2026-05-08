from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import UTC, datetime
from secrets import compare_digest
from typing import Any, cast

from app.config import Settings
from app.schemas.auth import OperatorTokenRead, OperatorTokenRequest


class OperatorAuthError(ValueError):
    """Raised when operator session authentication fails."""


def create_operator_token(settings: Settings, request: OperatorTokenRequest) -> OperatorTokenRead:
    if not settings.operator_session_auth_configured:
        raise OperatorAuthError("Operator session authentication is not configured.")
    if not compare_digest(request.login_secret, settings.operator_login_secret):
        raise OperatorAuthError("Invalid operator login secret.")

    now = int(time.time())
    expires_at_epoch = now + settings.operator_token_ttl_seconds
    payload = {
        "actor_id": request.actor_id,
        "exp": expires_at_epoch,
        "iat": now,
        "role": "operator",
        "typ": "jobfinder-operator",
    }
    token = _sign_payload(payload, settings.operator_token_secret)
    return OperatorTokenRead(
        access_token=token,
        actor_id=request.actor_id,
        expires_at=datetime.fromtimestamp(expires_at_epoch, tz=UTC),
    )


def verify_operator_token(settings: Settings, token: str) -> dict[str, Any] | None:
    if not settings.operator_session_auth_configured:
        return None
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
    except ValueError:
        return None

    expected_signature = _signature(encoded_payload, settings.operator_token_secret)
    if not compare_digest(encoded_signature, expected_signature):
        return None
    try:
        payload = cast(dict[str, Any], json.loads(_b64decode(encoded_payload)))
    except (json.JSONDecodeError, ValueError):
        return None
    if payload.get("typ") != "jobfinder-operator" or payload.get("role") != "operator":
        return None
    expires_at = payload.get("exp")
    if not isinstance(expires_at, int) or expires_at <= int(time.time()):
        return None
    actor_id = payload.get("actor_id")
    if not isinstance(actor_id, str) or not actor_id:
        return None
    return payload


def _sign_payload(payload: dict[str, Any], secret: str) -> str:
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    return f"{encoded_payload}.{_signature(encoded_payload, secret)}"


def _signature(encoded_payload: str, secret: str) -> str:
    digest = hmac.new(secret.encode(), encoded_payload.encode(), hashlib.sha256).digest()
    return _b64encode(digest)


def _b64encode(value: str | bytes) -> str:
    raw = value.encode() if isinstance(value, str) else value
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64decode(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}").decode()
