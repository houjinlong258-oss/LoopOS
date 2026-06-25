"""Skill optimizer adapter model."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SkillOptimizerAdapter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter_id: str = "skill_optimizer"
    model_only: bool = True


__all__ = ["SkillOptimizerAdapter"]
