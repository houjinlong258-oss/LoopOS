"""Governed freedom and budget models."""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---- Freedom levels ------------------------------------------------------

FreedomLevel = Literal[
    "F0_DETERMINISTIC",
    "F1_TOOL_CHOICE",
    "F2_PLAN_FREEDOM",
    "F3_STRATEGY_FREEDOM",
    "F4_RESEARCH_FREEDOM",
    "F5_AUTONOMOUS_PROJECT",
]

# Each level inherits the constraints of every level below it. The
# constant list is the source of truth for "promote"/"demote" logic
# in capability boundary checks.
FREEDOM_LEVELS: tuple[FreedomLevel, ...] = (
    "F0_DETERMINISTIC",
    "F1_TOOL_CHOICE",
    "F2_PLAN_FREEDOM",
    "F3_STRATEGY_FREEDOM",
    "F4_RESEARCH_FREEDOM",
    "F5_AUTONOMOUS_PROJECT",
)

# Default authority map: a level implies the next level down is also
# active. The boundary check uses this to decide whether a request
# needs explicit approval at a higher level.
_FREEDOM_RANK: dict[FreedomLevel, int] = {
    level: index for index, level in enumerate(FREEDOM_LEVELS)
}


def freedom_rank(level: FreedomLevel) -> int:
    return _FREEDOM_RANK[level]


def freedom_at_least(actual: FreedomLevel, required: FreedomLevel) -> bool:
    return _FREEDOM_RANK[actual] >= _FREEDOM_RANK[required]


# ---- Budget --------------------------------------------------------------


class FreedomBudget(BaseModel):
    """Resource envelope for one governed session.

    The budget is enforced at the boundary, not the policy layer, so
    the runtime can short-circuit over-budget requests before they
    reach Policy OS.
    """

    model_config = ConfigDict(extra="forbid")

    budget_id: str = Field(default_factory=lambda: str(uuid4()))
    max_steps: int = Field(default=20, ge=1)
    max_tool_calls: int = Field(default=64, ge=0)
    max_network_calls: int = Field(default=0, ge=0)
    max_wall_clock_seconds: int = Field(default=1800, ge=1)
    max_database_mutations: int = Field(default=0, ge=0)
    max_filesystem_writes: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _enforce_level_sane_defaults(self) -> "FreedomBudget":
        # F0 must not allow arbitrary mutations.
        if self.max_database_mutations < 0:
            raise ValueError("max_database_mutations must be non-negative")
        if self.max_filesystem_writes < 0:
            raise ValueError("max_filesystem_writes must be non-negative")
        return self

    def with_level(self, level: FreedomLevel) -> "FreedomBudget":
        """Return a copy whose caps are set to the level's defaults.

        The level defaults are the *ceiling* for that level. The
        resulting budget never loosens a caller-supplied cap and
        never exceeds the level's ceiling.
        """

        ceilings: dict[FreedomLevel, dict[str, int]] = {
            "F0_DETERMINISTIC": {
                "max_network_calls": 0,
                "max_database_mutations": 0,
                "max_filesystem_writes": 0,
            },
            "F1_TOOL_CHOICE": {
                "max_network_calls": 0,
                "max_database_mutations": 0,
                "max_filesystem_writes": 4,
            },
            "F2_PLAN_FREEDOM": {
                "max_network_calls": 0,
                "max_database_mutations": 2,
                "max_filesystem_writes": 16,
            },
            "F3_STRATEGY_FREEDOM": {
                "max_network_calls": 0,
                "max_database_mutations": 8,
                "max_filesystem_writes": 64,
            },
            "F4_RESEARCH_FREEDOM": {
                "max_network_calls": 8,
                "max_database_mutations": 16,
                "max_filesystem_writes": 128,
            },
            "F5_AUTONOMOUS_PROJECT": {
                "max_network_calls": 32,
                "max_database_mutations": 64,
                "max_filesystem_writes": 512,
            },
        }
        step_ceiling = {
            "F0_DETERMINISTIC": 4,
            "F1_TOOL_CHOICE": 8,
            "F2_PLAN_FREEDOM": 16,
            "F3_STRATEGY_FREEDOM": 32,
            "F4_RESEARCH_FREEDOM": 64,
            "F5_AUTONOMOUS_PROJECT": 128,
        }[level]
        payload = self.model_dump()
        for key, ceiling in ceilings[level].items():
            # The level's ceiling is the upper bound; an existing
            # caller-supplied cap can only lower the result.
            payload[key] = min(int(payload[key]), int(ceiling))
        payload["max_steps"] = min(self.max_steps, step_ceiling)
        return FreedomBudget.model_validate(payload)


# ---- Policy -------------------------------------------------------------


class FreedomPolicy(BaseModel):
    """Freedom profile applied to one session or workspace."""

    model_config = ConfigDict(extra="forbid")

    level: FreedomLevel = "F0_DETERMINISTIC"
    require_human_approval_for: list[str] = Field(
        default_factory=lambda: [
            "release_tag",
            "database_mutation",
            "production",
        ]
    )
    allow_network: bool = False
    allow_privilege_escalation: bool = False
    allow_database_mutation: bool = False
    allow_release_tag_changes: bool = False
    max_filesystem_write_bytes: int = Field(default=0, ge=0)
    allowed_filesystem_roots: list[str] = Field(default_factory=list)
    allowed_database_paths: list[str] = Field(default_factory=list)
    allowed_network_hosts: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("require_human_approval_for")
    @classmethod
    def normalize_actions(cls, value: list[str]) -> list[str]:
        return [str(v).strip() for v in value if str(v).strip()]
