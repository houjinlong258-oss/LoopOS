"""v0.4 procedure skill contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProcedureSkill(BaseModel):
    """Reusable project-training instruction pack."""

    model_config = ConfigDict(extra="forbid")

    skill_id: str
    title: str
    steps: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


__all__ = ["ProcedureSkill"]
