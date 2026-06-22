"""Governed freedom / capability / outcome metadata.

The freedom layer constrains **authority**, not thought. It exposes:

* :class:`FreedomLevel` - the canonical F0-F5 taxonomy that controls
  which governance gates are active.
* :class:`FreedomBudget` - the per-session resource envelope (steps,
  tool calls, network calls, wall-clock).
* :class:`CapabilityBoundary` - the allowed filesystem, network, git,
  database, provider, and memory surface.
* :class:`OutcomeContract` - the deliverables, acceptance criteria,
  halt conditions, and evidence required for a completion claim.

The layer is consumed by ACI, ALI, and the runtime. It never imports
``loopos.kernel.*`` and never touches ``KernelLoopEngine``.
"""

from loopos.freedom.boundary import (
    AuthorityDecision,
    BoundaryContext,
    CapabilityBoundary,
    check_authority,
)
from loopos.freedom.contracts import (
    AcceptanceCriterion,
    HaltCondition,
    OutcomeContract,
    OutcomeEvidence,
    OutcomeStatus,
)
from loopos.freedom.models import (
    FreedomBudget,
    FreedomLevel,
    FreedomPolicy,
    freedom_at_least,
    freedom_rank,
)

__all__ = [
    "AcceptanceCriterion",
    "AuthorityDecision",
    "BoundaryContext",
    "CapabilityBoundary",
    "FreedomBudget",
    "FreedomLevel",
    "FreedomPolicy",
    "HaltCondition",
    "OutcomeContract",
    "OutcomeEvidence",
    "OutcomeStatus",
    "check_authority",
    "freedom_at_least",
    "freedom_rank",
]
