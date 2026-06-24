"""LoopOS Action Boundary: the v0.4.0 boundary layer.

> Policy gates actions, not ideas.
> Syscall gates side effects, not reasoning.

This package is a **thin compatibility / documentation layer** over
the existing ``loopos.policy_os`` and ``loopos.syscalls`` packages.
It does not re-implement safety. It gives the v0.4.0 loop engine a
single, import-stable surface for the action boundary.

The boundary is real. It is intact. It runs whenever the loop wants
to do something with a side effect. It just no longer occupies the
first screen of the product — that screen now belongs to the loop.
"""

from __future__ import annotations

from loopos.boundary.action_boundary import (
    ActionBoundary,
    ActionBoundaryDecision,
)
from loopos.boundary.commitment import CommitmentGate

__all__ = [
    "ActionBoundary",
    "ActionBoundaryDecision",
    "CommitmentGate",
]
