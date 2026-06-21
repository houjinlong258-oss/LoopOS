"""Plugin manifest and audit contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

PluginType = Literal[
    "provider", "skill", "policy", "gateway", "mcp", "execution_backend", "benchmark", "agent_role"
]
PluginRisk = Literal["low", "medium", "high", "blocked"]


class PluginManifest(BaseModel):
    schema_version: str = "1.0"
    id: str
    type: PluginType
    name: str
    description: str = ""
    version: str
    license: str | None = None
    entrypoint: str | None = None
    documentation: str | None = None
    compatibility: dict[str, str] = Field(default_factory=dict)
    required_tools: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    risk_level: PluginRisk = "low"
    maintainers: list[str] = Field(default_factory=list)
    tests: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id", "name", "version")
    @classmethod
    def required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("plugin id, name, and version are required")
        return value


class PluginAuditResult(BaseModel):
    schema_version: str = "1.0"
    plugin_id: str
    safe: bool
    risk_level: PluginRisk
    findings: list[str] = Field(default_factory=list)
    permissions_reviewed: list[str] = Field(default_factory=list)
    permission_explanations: dict[str, str] = Field(default_factory=dict)
    risk_explanation: str = ""
    examples_validated: bool = False
