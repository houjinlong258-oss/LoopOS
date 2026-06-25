"""Node pairing policy."""

from __future__ import annotations

from loopos.nodes.node import Node


def pairing_required(node: Node) -> bool:
    return not node.local and not node.paired


def pair_node(node: Node, code: str) -> Node:
    if not code.strip():
        raise ValueError("pairing code is required")
    return node.model_copy(update={"paired": True})


__all__ = ["pair_node", "pairing_required"]
