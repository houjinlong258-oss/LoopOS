"""Loop state, observations, and evaluation models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from loopos.core.isa import Instruction

RunStatus = Literal["pending", "running", "succeeded", "failed", "cancelled", "blocked"]
EvaluationStatus = Literal["continue", "succeeded", "failed", "blocked"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Observation(BaseModel):
    """Structured result from executing an instruction or tool."""

    success: bool
    summary: str
    stdout: str = ""
    stderr: str = ""
    return_code: int | None = None
    duration_ms: int = 0
    timed_out: bool = False
    command: str | None = None
    cwd: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class Evaluation(BaseModel):
    """Evaluator output used to transition state."""

    status: EvaluationStatus
    score_delta: float = 0.0
    summary: str = ""
    memory_refs: list[str] = Field(default_factory=list)


class ToolHistoryEntry(BaseModel):
    """Compact audit record for executed tools or terminal commands."""

    instruction_id: str
    op: str
    success: bool
    command: str | None = None
    tool: str | None = None
    summary: str
    created_at: datetime = Field(default_factory=utc_now)


class LoopState(BaseModel):
    """Mutable state for one LoopOS run."""

    run_id: str = Field(default_factory=lambda: str(uuid4()))
    goal: str
    status: RunStatus = "pending"
    step_index: int = 0
    progress_score: float = 0.0
    current_instruction: Instruction | None = None
    last_observation: Observation | None = None
    errors: list[str] = Field(default_factory=list)
    tool_history: list[ToolHistoryEntry] = Field(default_factory=list)
    memory_refs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("goal")
    @classmethod
    def goal_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("goal is required")
        return value

    def apply(
        self,
        instruction: Instruction,
        observation: Observation,
        evaluation: Evaluation,
    ) -> "LoopState":
        """Apply one loop step and return self for convenience."""

        self.current_instruction = instruction
        self.last_observation = observation
        self.step_index += 1
        self.progress_score = max(0.0, min(1.0, self.progress_score + evaluation.score_delta))
        self.memory_refs.extend(ref for ref in evaluation.memory_refs if ref not in self.memory_refs)

        if observation.error:
            self.errors.append(observation.error)
        elif not observation.success:
            self.errors.append(observation.summary)

        self.tool_history.append(
            ToolHistoryEntry(
                instruction_id=instruction.id,
                op=instruction.op,
                success=observation.success,
                command=observation.command,
                tool=instruction.args.get("tool") if isinstance(instruction.args.get("tool"), str) else None,
                summary=observation.summary,
            )
        )

        if evaluation.status == "succeeded":
            self.status = "succeeded"
            self.progress_score = max(self.progress_score, 1.0)
        elif evaluation.status == "failed":
            self.status = "failed"
        elif evaluation.status == "blocked":
            self.status = "blocked"
        else:
            self.status = "running"

        self.updated_at = utc_now()
        return self

    @property
    def is_terminal(self) -> bool:
        return self.status in {"succeeded", "failed", "cancelled", "blocked"}
