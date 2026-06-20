"""Zep-inspired adapter stub."""

from __future__ import annotations

import importlib.util
from typing import Any

from loopos.memory.belief_store import MemoryItem


class ZepAdapter:
    """Optional adapter for future temporal memory integrations."""

    def is_available(self) -> bool:
        return (
            importlib.util.find_spec("zep_python") is not None
            or importlib.util.find_spec("zep_cloud") is not None
        )

    def to_session_memory(
        self,
        item: MemoryItem,
        *,
        session_id: str,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "session_id": session_id,
            "user_id": user_id,
            "content": item.content,
            "role": item.type,
            "created_at": item.created_at,
            "metadata": {"confidence": item.confidence, "tags": item.tags},
        }
