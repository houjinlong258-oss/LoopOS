"""Memory proposal models."""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from loopos.core.state import utc_now
from loopos.memory.belief_store import MemoryItem

ProposalStatus = Literal["pending", "accepted", "rejected", "merged"]


class MemoryProposal(BaseModel):
    """Governed candidate write for long-term memory."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid4()))
    proposed_item: MemoryItem
    source: str
    source_run_id: str | None = None
    source_event_ids: list[str] = Field(default_factory=list)
    rationale: str
    status: ProposalStatus = "pending"
    decision_reasons: list[str] = Field(default_factory=list)
    created_at: object = Field(default_factory=utc_now)
    decided_at: object | None = None

    @field_validator("source", "rationale")
    @classmethod
    def non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value
