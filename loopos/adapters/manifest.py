"""Agent Kernel Manifest.

Every adapter declares a manifest that states *what it can do* and
*what authority it requires*. The registry enforces that external
adapters never claim direct shell or direct file-write authority; all
real-world effects must flow through ACI / Policy OS / Trace.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

AdapterKind = Literal["native", "external_cli", "external_api", "spec_only"]


class AgentKernelCapabilitiesModel(BaseModel):
    """Declared capabilities of an adapter (manifest form)."""

    model_config = ConfigDict(extra="forbid")

    streaming_events: bool = True
    file_patch: bool = False
    shell_request: bool = False
    model_call_request: bool = False
    snapshot_resume: bool = False


class AgentKernelAuthority(BaseModel):
    """Authority boundary an adapter requires.

    For any non-native adapter the validator forces
    ``direct_shell=False`` and ``direct_file_write=False`` and forces
    ``requires_aci`` / ``requires_policy`` / ``requires_trace`` True.
    An adapter cannot opt out of governance.
    """

    model_config = ConfigDict(extra="forbid")

    direct_shell: bool = False
    direct_file_write: bool = False
    requires_aci: bool = True
    requires_policy: bool = True
    requires_trace: bool = True


class AgentKernelManifest(BaseModel):
    """Declarative manifest describing an agent kernel adapter."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["0.3"] = "0.3"
    adapter_id: str
    name: str
    version: str = "0.3.0"
    kind: AdapterKind = "external_cli"
    entrypoint: str = ""
    status: Literal["ready", "available", "spec_only", "disabled"] = "available"
    notes: str = ""
    capabilities: AgentKernelCapabilitiesModel = Field(default_factory=AgentKernelCapabilitiesModel)
    authority: AgentKernelAuthority = Field(default_factory=AgentKernelAuthority)

    @field_validator("adapter_id", "name")
    @classmethod
    def _required(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("value is required and must be non-empty")
        return value

    @field_validator("adapter_id")
    @classmethod
    def _canonical(cls, value: str) -> str:
        return value.strip().lower()

    @model_validator(mode="after")
    def _enforce_governance(self) -> "AgentKernelManifest":
        """External adapters cannot claim direct authority."""
        if self.kind != "native":
            if self.authority.direct_shell:
                raise ValueError("external adapter cannot claim direct_shell authority")
            if self.authority.direct_file_write:
                raise ValueError("external adapter cannot claim direct_file_write authority")
            # Force governance flags on for any external adapter.
            object.__setattr__(self.authority, "requires_aci", True)
            object.__setattr__(self.authority, "requires_policy", True)
            object.__setattr__(self.authority, "requires_trace", True)
        return self

    def to_json(self) -> str:
        return self.model_dump_json(exclude_none=False)

    @classmethod
    def from_json(cls, raw: str | bytes | dict[str, Any]) -> "AgentKernelManifest":
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        if isinstance(raw, str):
            data = json.loads(raw)
        else:
            data = raw
        return cls.model_validate(data)


__all__ = [
    "AdapterKind",
    "AgentKernelAuthority",
    "AgentKernelCapabilitiesModel",
    "AgentKernelManifest",
]
