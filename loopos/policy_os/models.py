"""Structured Policy OS models."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

PolicyActionType = Literal[
    "allow",
    "deny",
    "require_approval",
    "modify",
    "prefer_tool",
    "require_review",
]
PolicySeverity = Literal["info", "low", "medium", "high", "critical"]
ConditionOperator = Literal[
    "equals",
    "not_equals",
    "contains",
    "regex",
    "in",
    "exists",
    "risk_at_least",
    "lt",
    "lte",
    "gt",
    "gte",
]
PolicyRiskLevel = Literal["low", "medium", "high", "blocked"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PolicyCondition(BaseModel):
    """A simple condition or an all/any compound group."""

    field: str | None = None
    operator: ConditionOperator = "equals"
    value: Any = None
    all: list["PolicyCondition"] = Field(default_factory=list)
    any: list["PolicyCondition"] = Field(default_factory=list)


class PolicyAction(BaseModel):
    """Action emitted by a matching policy rule."""

    type: PolicyActionType
    reason_code: str
    constraints: dict[str, Any] = Field(default_factory=dict)
    tool_preferences: dict[str, Any] = Field(default_factory=dict)
    memory_filters: dict[str, Any] = Field(default_factory=dict)
    render_hints: dict[str, Any] = Field(default_factory=dict)
    audit_required: bool = False

    @field_validator("reason_code")
    @classmethod
    def reason_code_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason_code is required")
        return value


class PolicyRule(BaseModel):
    """Single policy rule."""

    id: str
    description: str = ""
    scope: str
    priority: int = 500
    severity: PolicySeverity = "low"
    tags: list[str] = Field(default_factory=list)
    enabled: bool = True
    conditions: list[PolicyCondition] = Field(default_factory=list)
    actions: list[PolicyAction] = Field(default_factory=list)

    @field_validator("id", "scope")
    @classmethod
    def non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value


class PolicyPack(BaseModel):
    """Loadable policy pack."""

    id: str
    name: str
    version: str = "0.1.0"
    description: str = ""
    priority: int = 500
    rules: list[PolicyRule] = Field(default_factory=list)


class PolicyRequest(BaseModel):
    """Input evaluated by the policy engine."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    scope: str
    subject: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    risk_level: PolicyRiskLevel = "low"
    actor: str = "runtime"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class PolicyContext(BaseModel):
    """Typed kernel context supplied to Policy OS."""

    phase: str
    task: dict[str, Any] = Field(default_factory=dict)
    state: dict[str, Any] = Field(default_factory=dict)
    instruction: dict[str, Any] = Field(default_factory=dict)
    syscall: dict[str, Any] = Field(default_factory=dict)
    memory: dict[str, Any] = Field(default_factory=dict)
    runtime: dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(BaseModel):
    """Resolved decision returned by Policy OS."""

    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    allowed: bool
    action: PolicyActionType
    severity: PolicySeverity = "info"
    risk: PolicyRiskLevel = "low"
    requires_approval: bool = False
    reason_codes: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    tool_preferences: dict[str, Any] = Field(default_factory=dict)
    memory_filters: dict[str, Any] = Field(default_factory=dict)
    render_hints: dict[str, Any] = Field(default_factory=dict)
    audit_required: bool = False
    matched_rules: list[str] = Field(default_factory=list)

    @property
    def renderer_hints(self) -> dict[str, Any]:
        """Kernel-prompt spelling retained without breaking render_hints callers."""

        return self.render_hints
