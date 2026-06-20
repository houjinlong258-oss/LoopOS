"""Letta-inspired adapter stub."""

from __future__ import annotations

import importlib.util
from typing import Any

from loopos.memory.belief_store import MemoryItem


class LettaAdapter:
    """Optional adapter for future Letta memory import/export."""

    def is_available(self) -> bool:
        return importlib.util.find_spec("letta") is not None

    def to_memory_block(self, item: MemoryItem) -> dict[str, Any]:
        return {
            "label": item.type,
            "value": item.content,
            "confidence": item.confidence,
            "metadata": {"source": item.source, "tags": item.tags},
        }
