"""Redaction helpers for screenshots, clipboard, and UI text."""

from __future__ import annotations

import re


SECRET_RE = re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*\S+")


def redact_text(text: str) -> str:
    return SECRET_RE.sub(r"\1=[REDACTED]", text)


def redacted_clipboard_placeholder() -> str:
    return "[REDACTED_CLIPBOARD]"


def redacted_screenshot_ref(raw_ref: str = "screen") -> str:
    return f"redacted://{raw_ref}"


__all__ = ["redact_text", "redacted_clipboard_placeholder", "redacted_screenshot_ref"]
