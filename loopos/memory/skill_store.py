"""Skill memory store and extraction helpers."""

from __future__ import annotations

import json
import builtins
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Sequence
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from loopos.core.state import utc_now
from loopos.memory.event_log import Event


class Skill(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    trigger_tags: list[str] = Field(default_factory=list)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    source_run_id: str | None = None
    source_runs: list[str] = Field(default_factory=list)
    confidence: float = 0.8
    status: Literal["active", "disabled", "superseded"] = "active"
    success_count: int = Field(default=1, ge=0)
    failure_count: int = Field(default=0, ge=0)
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    version: int = 1

    @field_validator("confidence")
    @classmethod
    def confidence_range(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("confidence must be between 0 and 1")
        return value

    @field_validator("name", "description")
    @classmethod
    def non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value

    @model_validator(mode="after")
    def synchronize_stats(self) -> "Skill":
        if self.source_run_id and self.source_run_id not in self.source_runs:
            self.source_runs.append(self.source_run_id)
        if self.source_run_id is None and self.source_runs:
            self.source_run_id = self.source_runs[0]
        total = self.success_count + self.failure_count
        self.success_rate = self.success_count / total if total else 0.0
        return self


class SkillStore:
    """JSONL-backed reusable skill store."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, skill: Skill) -> Skill:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(skill.model_dump_json() + "\n")
        return skill

    def upsert(self, skill: Skill) -> Skill:
        """Append a new version; list() resolves the latest row per id."""

        return self.add(skill)

    def list(self) -> list[Skill]:
        if not self.path.exists():
            return []
        skills: dict[str, Skill] = {}
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    skill = Skill.model_validate(json.loads(line))
                    skills[skill.id] = skill
        return list(skills.values())

    def find_by_tags(
        self, tags: Sequence[str], *, min_confidence: float = 0.5
    ) -> builtins.list[Skill]:
        tag_set: set[str] = set(tags)
        return [
            skill
            for skill in self.list()
            if skill.status == "active"
            and skill.confidence >= min_confidence
            and tag_set.intersection(skill.trigger_tags)
        ]


def extract_skill_from_events(
    events: list[Event],
    *,
    name: str,
    description: str,
    trigger_tags: list[str],
) -> Skill:
    """Compress successful instruction events into a reusable skill."""

    steps: list[dict[str, Any]] = []
    run_id = events[0].run_id if events else None
    for event in events:
        if event.type == "instruction_planned":
            steps.append(event.payload)
    return Skill(
        name=name,
        description=description,
        trigger_tags=trigger_tags,
        steps=steps,
        source_run_id=run_id,
        confidence=0.75 if steps else 0.4,
    )
