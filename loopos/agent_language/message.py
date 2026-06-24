"""LAIL message model.

LAIL is a structured, low-token signal language. It carries optimization
signals between LoopOS agents; it never executes actions and never embeds
syscall requests.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Self
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from loopos.agent_language.roles import AgentRole


class Actionability(str, Enum):
    NONE = "none"
    ADVISORY = "advisory"
    PROPOSAL = "proposal"
    COMMITMENT_REQUIRED = "commitment_required"


FORBIDDEN_PAYLOAD_KEYS = {
    "syscall",
    "shell",
    "command",
    "cmd",
    "network_call",
    "database_write",
    "release_operation",
    "file_mutation",
    "execute",
    "dispatch",
}


class AgentMessage(BaseModel):
    """A non-executing LAIL signal exchanged inside the loop."""

    model_config = ConfigDict(extra="forbid")

    message_id: str = Field(default_factory=lambda: f"lail_{uuid4().hex[:10]}")
    trace_id: str
    iteration_id: str | int
    from_role: AgentRole
    to_role: AgentRole | list[AgentRole]
    signal_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    quality_delta: float | None = None
    token_cost: int | None = Field(default=None, ge=0)
    communication_distance: int | None = Field(default=None, ge=0)
    actionability: Actionability = Actionability.NONE
    requires_commitment: bool = False
    authority_delta: Literal["none"] = "none"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("payload")
    @classmethod
    def payload_must_not_embed_actions(cls, value: dict[str, Any]) -> dict[str, Any]:
        leaked = _find_forbidden_keys(value)
        if leaked:
            raise ValueError(f"LAIL payload contains executable fields: {sorted(leaked)}")
        return value

    @model_validator(mode="after")
    def commitment_flag_matches_actionability(self) -> Self:
        if self.actionability == Actionability.COMMITMENT_REQUIRED:
            self.requires_commitment = True
        if self.requires_commitment and self.authority_delta != "none":
            raise ValueError("LAIL authority_delta must remain 'none' before commitment")
        return self

    def recipients(self) -> list[AgentRole]:
        if isinstance(self.to_role, list):
            return list(self.to_role)
        return [self.to_role]

    def token_estimate(self) -> int:
        text = self.model_dump_json()
        return max(1, len(text) // 4)


def _find_forbidden_keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key).lower()
            if key_text in FORBIDDEN_PAYLOAD_KEYS:
                found.add(key_text)
            found.update(_find_forbidden_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_find_forbidden_keys(child))
    return found


__all__ = ["Actionability", "AgentMessage", "FORBIDDEN_PAYLOAD_KEYS"]
