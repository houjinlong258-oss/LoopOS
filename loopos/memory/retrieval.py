"""Memory retrieval and ranking."""

from __future__ import annotations

from datetime import datetime, timezone

from loopos.memory.belief_store import MemoryItem


class MemoryRetriever:
    """Rank memory by confidence, recency, and tag overlap."""

    def __init__(self, items: list[MemoryItem]) -> None:
        self.items = items

    def retrieve(
        self,
        query_tags: list[str],
        *,
        query_text: str = "",
        limit: int = 5,
        min_confidence: float = 0.0,
    ) -> list[MemoryItem]:
        query_set = set(query_tags)
        query_terms = set(query_text.lower().split())
        candidates = [
            item
            for item in self.items
            if item.status == "active" and item.confidence >= min_confidence
        ]
        ranked = sorted(
            candidates,
            key=lambda item: self._score(item, query_set, query_terms),
            reverse=True,
        )
        return ranked[:limit]

    @staticmethod
    def _score(item: MemoryItem, query_tags: set[str], query_terms: set[str] | None = None) -> float:
        overlap = len(query_tags.intersection(item.tags)) / max(len(query_tags), 1)
        terms = query_terms or set()
        content_terms = set(item.content.lower().split())
        lexical = len(terms.intersection(content_terms)) / max(len(terms), 1) if terms else 0.0
        created_at = item.created_at
        if isinstance(created_at, str):
            created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        elif isinstance(created_at, datetime):
            created_dt = created_at
        else:
            created_dt = datetime.now(timezone.utc)
        age_days = max((datetime.now(timezone.utc) - created_dt).total_seconds() / 86400, 0)
        recency = 1 / (1 + age_days)
        usage_signal = min(item.usage_count / 10, 1.0)
        return (
            (item.confidence * 0.45)
            + (overlap * 0.2)
            + (recency * 0.15)
            + (usage_signal * 0.1)
            + (lexical * 0.1)
        ) * item.decay_score
