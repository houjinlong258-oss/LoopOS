"""Belief and preference memory store."""

from __future__ import annotations

import json
import builtins
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Sequence
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from loopos.core.state import utc_now

MemoryType = Literal["belief", "preference", "fact", "failure", "note", "skill", "user_model"]
MemoryStatus = Literal["active", "superseded", "rejected", "conflicted"]
MemoryLayer = Literal["working", "episodic", "semantic", "belief", "skill", "user_model"]
MemoryScope = Literal["run", "project", "user", "global"]


class MemoryItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid4()))
    type: MemoryType
    content: str
    confidence: float
    source: str
    layer: MemoryLayer = "belief"
    scope: MemoryScope = "project"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    version: int = 1
    tags: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    status: MemoryStatus = "active"
    metadata: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    decay_score: float = 1.0

    @field_validator("confidence")
    @classmethod
    def confidence_range(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("confidence must be between 0 and 1")
        return value

    @field_validator("content", "source")
    @classmethod
    def non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value

    @field_validator("decay_score")
    @classmethod
    def decay_score_range(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("decay_score must be between 0 and 1")
        return value

    @field_validator("tags")
    @classmethod
    def canonical_tags(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for tag in value:
            normalized = tag.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
        return result


class BeliefStore:
    """JSONL-backed memory item store."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, item: MemoryItem) -> MemoryItem:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(item.model_dump_json() + "\n")
        return item

    def list(self, *, status: MemoryStatus | None = None) -> list[MemoryItem]:
        if not self.path.exists():
            return []
        items: list[MemoryItem] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                item = MemoryItem.model_validate(json.loads(line))
                if status is None or item.status == status:
                    items.append(item)
        return items

    def query_by_tags(
        self,
        tags: Sequence[str],
        *,
        min_confidence: float = 0.0,
        status: MemoryStatus = "active",
    ) -> builtins.list[MemoryItem]:
        tag_set: set[str] = set(tags)
        return [
            item
            for item in self.list(status=status)
            if item.confidence >= min_confidence and tag_set.intersection(item.tags)
        ]
