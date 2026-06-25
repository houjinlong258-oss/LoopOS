"""Node heartbeat updates."""

from __future__ import annotations

from datetime import datetime, timezone

from loopos.nodes.node import Node


def heartbeat(node: Node, *, healthy: bool = True) -> Node:
    return node.model_copy(
        update={
            "healthy": healthy,
            "last_heartbeat_at": datetime.now(timezone.utc).isoformat(),
        }
    )


__all__ = ["heartbeat"]
