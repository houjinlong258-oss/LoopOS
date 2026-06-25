"""In-memory node registry."""

from __future__ import annotations

from typing import List

from loopos.nodes.capabilities import Capability
from loopos.nodes.heartbeat import heartbeat
from loopos.nodes.node import Node
from loopos.nodes.pairing import pairing_required


class NodeRegistry:
    """Declare and query runtime nodes."""

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self.register(Node())

    def register(self, node: Node) -> Node:
        if pairing_required(node):
            raise ValueError("non-local node requires pairing")
        self._nodes[node.node_id] = node
        return node

    def list(self) -> List[Node]:
        return list(self._nodes.values())

    def nodes_with(self, capability: Capability) -> List[Node]:
        return [node for node in self._nodes.values() if capability in node.capabilities]

    def heartbeat(self, node_id: str, *, healthy: bool = True) -> Node:
        node = self._nodes[node_id]
        updated = heartbeat(node, healthy=healthy)
        self._nodes[node_id] = updated
        return updated


__all__ = ["NodeRegistry"]
