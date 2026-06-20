"""Safe trace summaries for planner context."""

from typing import Any


def compact_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep references and summaries while excluding raw process output."""

    return {
        key: payload[key]
        for key in ("id", "type", "kind", "summary", "success", "reason_code")
        if key in payload
    }

