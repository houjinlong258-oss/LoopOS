"""Governed skill proposal contracts."""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from loopos.core.state import utc_now
from loopos.memory.skill_store import Skill

SkillProposalStatus = Literal["pending", "accepted", "rejected", "merged"]


class SkillProposal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    proposed_skill: Skill
    source_run_id: str
    source_event_ids: list[str]
    rationale: str
    status: SkillProposalStatus = "pending"
    decision_reasons: list[str] = Field(default_factory=list)
    created_at: object = Field(default_factory=utc_now)
    decided_at: object | None = None

    @field_validator("source_run_id", "rationale")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("skill proposal fields cannot be empty")
        return value

