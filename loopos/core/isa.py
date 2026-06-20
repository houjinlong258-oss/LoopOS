"""Typed AI-ISA instruction schema."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

InstructionOp = Literal[
    "PLAN",
    "CALL_TOOL",
    "EXEC_TERMINAL",
    "OBSERVE",
    "EVALUATE",
    "UPDATE_STATE",
    "STORE_MEMORY",
    "EXTRACT_SKILL",
    "TERMINATE",
]

RiskLevel = Literal["low", "medium", "high", "blocked"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InstructionSafety(BaseModel):
    """Safety metadata attached to every AI-ISA instruction."""

    risk_level: RiskLevel = "low"
    requires_approval: bool = False
    allowed_paths: list[str] = Field(default_factory=list)
    blocked_patterns: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def blocked_requires_approval(self) -> "InstructionSafety":
        if self.risk_level == "blocked" and not self.requires_approval:
            raise ValueError("blocked instructions must set requires_approval=true")
        return self


class ExpectedObservation(BaseModel):
    """Expected execution outcome for planning and evaluation."""

    success_criteria: list[str] = Field(default_factory=list)
    failure_criteria: list[str] = Field(default_factory=list)
    timeout_seconds: int | None = None

    @field_validator("timeout_seconds")
    @classmethod
    def timeout_must_be_positive(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("timeout_seconds must be positive")
        return value


class Instruction(BaseModel):
    """Single AI-ISA instruction."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()))
    op: InstructionOp
    created_at: datetime = Field(default_factory=_utc_now)
    reason_code: str
    args: dict[str, Any] = Field(default_factory=dict)
    safety: InstructionSafety = Field(default_factory=InstructionSafety)
    expected_observation: ExpectedObservation | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("reason_code")
    @classmethod
    def reason_code_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason_code is required")
        return value

    @model_validator(mode="after")
    def validate_required_args(self) -> "Instruction":
        issues = validate_instruction_for_mvp(self)
        if issues:
            raise ValueError("; ".join(issues))
        return self


def parse_instruction(raw: str | dict[str, Any]) -> Instruction:
    """Parse a JSON string or mapping into an Instruction."""

    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"instruction is not valid JSON: {exc}") from exc
    else:
        data = raw
    return Instruction.model_validate(data)


def instruction_to_json(instruction: Instruction) -> str:
    """Serialize an instruction to stable JSON."""

    return instruction.model_dump_json(exclude_none=True)


def validate_instruction_for_mvp(instruction: Instruction) -> list[str]:
    """Return MVP validation issues without mutating the instruction."""

    issues: list[str] = []
    if instruction.op == "EXEC_TERMINAL":
        cmd = instruction.args.get("cmd")
        if not isinstance(cmd, str) or not cmd.strip():
            issues.append("EXEC_TERMINAL requires args.cmd")
    if instruction.op == "CALL_TOOL":
        tool = instruction.args.get("tool")
        if not isinstance(tool, str) or not tool.strip():
            issues.append("CALL_TOOL requires args.tool")
    if instruction.op == "TERMINATE":
        reason = instruction.args.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            issues.append("TERMINATE requires args.reason")
    if instruction.safety.risk_level == "blocked" and not instruction.safety.requires_approval:
        issues.append("blocked risk_level requires approval metadata")
    return issues


def make_instruction(
    op: InstructionOp,
    reason_code: str,
    args: dict[str, Any] | None = None,
    *,
    risk_level: RiskLevel = "low",
    requires_approval: bool = False,
    expected_observation: ExpectedObservation | None = None,
    metadata: dict[str, Any] | None = None,
) -> Instruction:
    """Small helper for deterministic policies and tests."""

    return Instruction(
        op=op,
        reason_code=reason_code,
        args=args or {},
        safety=InstructionSafety(
            risk_level=risk_level,
            requires_approval=requires_approval,
        ),
        expected_observation=expected_observation,
        metadata=metadata or {},
    )
