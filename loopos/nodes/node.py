"""Node model for the local control plane."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from loopos.nodes.capabilities import Capability, DEFAULT_LOCAL_CAPABILITIES


NodeType = Literal[
    "local_computer",
    "browser",
    "sandbox_runner",
    "ci_runner",
    "mobile_future",
    "external_agent_future",
]


class Node(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(default_factory=lambda: f"node_{uuid4().hex[:10]}")
    node_type: NodeType = "local_computer"
    capabilities: list[Capability] = Field(default_factory=lambda: list(DEFAULT_LOCAL_CAPABILITIES))
    local: bool = True
    paired: bool = True
    healthy: bool = True
    last_heartbeat_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


__all__ = ["Node", "NodeType"]
