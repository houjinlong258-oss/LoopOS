"""Secret redaction + usage helpers.

The single most important guarantee of the provider runtime is that
**secrets never leak** into trace, logs, or error messages. This module
provides the redaction primitive used at every boundary.
"""

from __future__ import annotations

import os
import re

# Environment variables that hold provider secrets.
SECRET_ENV_KEYS: tuple[str, ...] = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "DEEPSEEK_API_KEY",
    "QWEN_API_KEY",
    "OPENROUTER_API_KEY",
)

_REDACTION = "***REDACTED***"

# Common API-key shapes (sk-..., long bearer tokens). Conservative on
# purpose: we would rather over-redact than leak.
_KEY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{8,}", re.IGNORECASE),
    re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)[A-Za-z0-9_\-\.]{8,}"),
)


def redact_secrets(text: str) -> str:
    """Return ``text`` with any known secret values redacted.

    Redacts (1) the live values of known secret environment variables,
    and (2) common API-key token shapes.
    """
    if not text:
        return text
    redacted = text
    # Redact live env values first (exact match).
    for key in SECRET_ENV_KEYS:
        value = os.environ.get(key)
        if value and value in redacted:
            redacted = redacted.replace(value, _REDACTION)
    # Then redact by shape.
    for pattern in _KEY_PATTERNS:
        if pattern.pattern.startswith("(?i)(api"):
            redacted = pattern.sub(r"\1" + _REDACTION, redacted)
        else:
            redacted = pattern.sub(_REDACTION, redacted)
    return redacted


def read_api_key(env_key: str) -> str | None:
    """Read an API key from the environment only."""
    value = os.environ.get(env_key)
    if value and value.strip():
        return value.strip()
    return None


__all__ = ["redact_secrets", "read_api_key", "SECRET_ENV_KEYS"]
