"""Outcome contracts for the freedom layer.

An :class:`OutcomeContract` is the contract an agent must satisfy to
claim completion of a session. The contract is data: deliverables,
acceptance criteria, halt conditions, evidence, and non-goals. A
contract without a corresponding :class:`OutcomeEvidence` cannot
close a session in a halt-success state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

OutcomeStatus = Literal["pending", "in_progress", "satisfied", "failed", "blocked"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AcceptanceCriterion(BaseModel):
    """Single acceptance criterion inside an :class:`OutcomeContract`."""

    model_config = ConfigDict(extra="forbid")

    criterion_id: str = Field(default_factory=lambda: str(uuid4()))
    description: str
    required: bool = True


class HaltCondition(BaseModel):
    """Single halt condition inside an :class:`OutcomeContract`."""

    model_config = ConfigDict(extra="forbid")

    condition_id: str = Field(default_factory=lambda: str(uuid4()))
    description: str
    triggers_halt: bool = True


class OutcomeContract(BaseModel):
    """The contract an agent must satisfy to claim completion.

    The contract is intentionally rich enough to carry acceptance
    criteria, halt conditions, deliverables, non-goals, and the
    evidence kinds the contract needs. It is also the data
    structure that propagates into ACI and ALI commands.
    """

    model_config = ConfigDict(extra="forbid")

    contract_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str = ""
    deliverables: list[str] = Field(default_factory=list)
    acceptance_criteria: list[AcceptanceCriterion] = Field(default_factory=list)
    halt_conditions: list[HaltCondition] = Field(default_factory=list)
    evidence_kinds: list[str] = Field(
        default_factory=lambda: [
            "test_report",
            "command_output",
            "review_artifact",
        ]
    )
    non_goals: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    status: OutcomeStatus = "pending"
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    @field_validator("title")
    @classmethod
    def title_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("title is required")
        return value

    def required_evidence_kinds(self) -> list[str]:
        return list(self.evidence_kinds)


class OutcomeEvidence(BaseModel):
    """The evidence collected for a contract during a session.

    The session carries an :class:`OutcomeEvidence` per contract. The
    contract is "satisfied" only when every required evidence kind is
    present and every required acceptance criterion has a status of
    ``"passed"``.
    """

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(default_factory=lambda: str(uuid4()))
    contract_id: str
    collected: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    criterion_status: dict[str, OutcomeStatus] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)

    def is_complete(self, contract: OutcomeContract) -> bool:
        if any(missing for missing in (self.missing,)):
            return False
        for kind in contract.evidence_kinds:
            if kind not in self.collected:
                return False
        for criterion in contract.acceptance_criteria:
            if not criterion.required:
                continue
            status = self.criterion_status.get(criterion.criterion_id, "pending")
            if status != "satisfied":
                return False
        return True
