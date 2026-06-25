"""Gateway node and capability registry."""

from __future__ import annotations

from loopos.nodes.capabilities import Capability, DEFAULT_LOCAL_CAPABILITIES
from loopos.nodes.heartbeat import heartbeat
from loopos.nodes.node import Node, NodeType
from loopos.nodes.pairing import pair_node, pairing_required
from loopos.nodes.registry import NodeRegistry

__all__ = [
    "Capability",
    "DEFAULT_LOCAL_CAPABILITIES",
    "Node",
    "NodeRegistry",
    "NodeType",
    "heartbeat",
    "pair_node",
    "pairing_required",
]
