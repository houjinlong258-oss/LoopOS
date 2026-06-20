"""MCP-like type contracts."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ToolRiskLevel = Literal["low", "medium", "high", "blocked"]
ToolHandler = Callable[["ToolCall"], "ToolResult"]


class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    risk_level: ToolRiskLevel = "low"
    requires_approval: bool = False
    tags: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def name_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("tool name is required")
        return value


class ToolCall(BaseModel):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    success: bool
    name: str
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    risk_level: ToolRiskLevel = "low"
    requires_approval: bool = False


class RegisteredTool(BaseModel):
    spec: ToolSpec
    handler: ToolHandler

    model_config = {"arbitrary_types_allowed": True}


class ToolRegistry:
    """In-memory registry for ToolSpec and handler pairs."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, spec: ToolSpec, handler: ToolHandler) -> None:
        if spec.name in self._tools:
            raise ValueError(f"tool already registered: {spec.name}")
        self._tools[spec.name] = RegisteredTool(spec=spec, handler=handler)

    def list_tools(self) -> list[ToolSpec]:
        return [tool.spec for tool in self._tools.values()]

    def resolve(self, name: str) -> RegisteredTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"unknown tool: {name}") from exc
