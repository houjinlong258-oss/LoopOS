"""Trace-safe redaction for database samples."""

from __future__ import annotations

import re
from typing import Any

from loopos.data_guard.models import RedactedSample

_SENSITIVE_KEYS = (
    "password", "passwd", "secret", "token", "api_key", "apikey", "access_key",
    "refresh_token", "session", "cookie", "ssn", "id_card", "phone", "email",
    "address", "credit_card", "card_number", "bank", "payment", "salary", "medical", "health",
)


def redact_rows(
    table: str,
    rows: list[dict[str, Any]],
    *,
    policy_decision_id: str = "",
) -> RedactedSample:
    redacted_fields: set[str] = set()
    safe_rows: list[dict[str, Any]] = []
    for row in rows:
        safe: dict[str, Any] = {}
        for key, value in row.items():
            lowered = key.lower()
            if any(marker in lowered for marker in _SENSITIVE_KEYS):
                safe[key] = _placeholder(lowered)
                redacted_fields.add(key)
            else:
                safe[key] = _redact_inline(value)
        safe_rows.append(safe)
    columns = list(dict.fromkeys(key for row in rows for key in row))
    return RedactedSample(
        table=table,
        columns=columns,
        rows=safe_rows,
        redacted_fields=sorted(redacted_fields),
        policy_decision_id=policy_decision_id,
    )


def _placeholder(key: str) -> str:
    if "email" in key:
        return "[REDACTED_EMAIL]"
    if "phone" in key:
        return "[REDACTED_PHONE]"
    return "[REDACTED_SECRET]"


def _redact_inline(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[REDACTED_EMAIL]", value)
    return re.sub(r"(?<!\d)(?:\+?\d[\d -]{7,}\d)(?!\d)", "[REDACTED_PHONE]", value)
