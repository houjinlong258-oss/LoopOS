"""Project Memory OS models.

Project memory is compressed project-training signal, not chat history.
The models below keep enough structure for the MemoryCompiler to build
small role-specific context packets and prevent repeated failures.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from loopos.agent_language.roles import AgentRole


ProjectMemoryKind = Literal[
    "working",
    "objective",
    "decision",
    "failure",
    "test",
    "code_map",
    "procedure",
    "agent",
    "delivery",
]
ProjectMemoryStatus = Literal["active", "superseded", "rejected", "conflicted"]


class ProjectMemoryItem(BaseModel):
    """Base record for project-training memory."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"pmem_{uuid4().hex[:10]}")
    type: ProjectMemoryKind
    content: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = Field(default=1, ge=1)
    tags: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    status: ProjectMemoryStatus = "active"


class WorkingMemory(ProjectMemoryItem):
    type: Literal["working"] = "working"


class ObjectiveMemory(ProjectMemoryItem):
    type: Literal["objective"] = "objective"
    objective_id: str | None = None


class DecisionMemory(ProjectMemoryItem):
    type: Literal["decision"] = "decision"
    decision: str = ""
    rationale: str = ""


class FailureMemory(ProjectMemoryItem):
    type: Literal["failure"] = "failure"
    failed_attempt: str
    failure_reason: str
    related_files: list[str] = Field(default_factory=list)
    related_tests: list[str] = Field(default_factory=list)
    avoid_repeating: str
    next_time: str


class TestMemory(ProjectMemoryItem):
    __test__ = False

    type: Literal["test"] = "test"
    test_name: str = ""
    result: Literal["passed", "failed", "not_run", "simulated"] = "not_run"


class CodeMapMemory(ProjectMemoryItem):
    type: Literal["code_map"] = "code_map"
    path: str = ""
    owner: str = ""


class ProcedureMemory(ProjectMemoryItem):
    type: Literal["procedure"] = "procedure"
    steps: list[str] = Field(default_factory=list)


class AgentMemory(ProjectMemoryItem):
    type: Literal["agent"] = "agent"
    role: AgentRole | None = None


class DeliveryMemory(ProjectMemoryItem):
    type: Literal["delivery"] = "delivery"
    delivery_gap: str = ""


class TokenBudgetLedger(BaseModel):
    """Rough token accounting without depending on a tokenizer."""

    model_config = ConfigDict(extra="forbid")

    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0
    context_packet_tokens: int = 0
    saved_tokens_estimate: int = 0

    @classmethod
    def estimate(
        cls,
        *,
        input_text: str = "",
        output_text: str = "",
        context_text: str = "",
        avoided_text: str = "",
    ) -> "TokenBudgetLedger":
        return cls(
            estimated_input_tokens=_estimate_tokens(input_text),
            estimated_output_tokens=_estimate_tokens(output_text),
            context_packet_tokens=_estimate_tokens(context_text),
            saved_tokens_estimate=_estimate_tokens(avoided_text),
        )


class ContextPacket(BaseModel):
    """Minimal role-specific context emitted by MemoryCompiler.

    v0.4.0 closeout: the packet carries ``selected_memory`` and
    ``omitted_memory_reason`` so the loop can audit what was
    included and what was dropped, not just the curated
    ``relevant_*`` strings.
    """

    model_config = ConfigDict(extra="forbid")

    packet_id: str = Field(default_factory=lambda: f"ctx_{uuid4().hex[:10]}")
    target_role: AgentRole
    goal_summary: str
    current_gap: str
    relevant_decisions: list[str] = Field(default_factory=list)
    relevant_failures: list[str] = Field(default_factory=list)
    relevant_tests: list[str] = Field(default_factory=list)
    relevant_files: list[str] = Field(default_factory=list)
    avoid_repeating: list[str] = Field(default_factory=list)
    expected_output: str = ""
    token_budget: int = Field(default=900, ge=1)
    estimated_tokens: int = 0
    ledger: TokenBudgetLedger = Field(default_factory=TokenBudgetLedger)
    # v0.4.0 closeout — what was kept and what was dropped.
    selected_memory: list[ProjectMemoryItem] = Field(default_factory=list)
    omitted_memory_reason: list[str] = Field(default_factory=list)
    # v0.4.0 closeout — the join key the loop uses to write the
    # packet into memory_context_packets.jsonl.
    run_id: str | None = None
    iteration_index: int = 0
    trace_id: str | None = None


def _estimate_tokens(text: str) -> int:
    text = text.strip()
    if not text:
        return 0
    return max(1, len(text) // 4)


__all__ = [
    "AgentMemory",
    "CodeMapMemory",
    "ContextPacket",
    "DecisionMemory",
    "DeliveryMemory",
    "FailureMemory",
    "ObjectiveMemory",
    "ProcedureMemory",
    "ProjectMemoryItem",
    "ProjectMemoryKind",
    "ProjectMemoryStatus",
    "TestMemory",
    "TokenBudgetLedger",
    "WorkingMemory",
]
