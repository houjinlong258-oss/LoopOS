"""LoopOS v0.3 OpenGod — strategic planning layer.

OpenGod is a **planning-only** strategic meta-agent. It observes
the current state of the runtime (goal, trace, fusion plan,
adapter state, readiness proof) and emits a strategic decision.
It never executes, never opens a network connection, never writes
a file.

.. important::

    **OpenGod is NOT wired into the AIL execution authority on
    v0.3.** The KernelLoopEngine's
    ``compile_next_ail()`` step does not consult
    ``OpenGodDecision``. OpenGod is a parallel decision system
    that can be invoked from the CLI (``loopos opengod ...``) or
    surfaced through the Workbench; its verdicts are observed,
    not enforced, by the runtime loop.

    Bridging OpenGod -> AIL is a documented v0.4 item (see
    ``docs/v0-3-opengod-boundary.md``). Until then, OpenGod
    *plans*, the kernel *decides*.

The package split mirrors the documented v0.3 plan:

* ``models`` — decision / context / verdict pydantic models.
* ``evidence`` — read-only evidence snapshot from the runtime.
* ``decision`` — strategy selection logic.
* ``verdict`` — final actionable verdict object.
* ``budget`` — guard rails (no auto-spend).
"""

from __future__ import annotations

from loopos.opengod.models import (
    OpenGodContext,
    OpenGodDecision,
    OpenGodDecisionKind,
    OpenGodVerdict,
    OpenGodVerdictStatus,
)
from loopos.opengod.evidence import OpenGodEvidence, collect_evidence
from loopos.opengod.decision import decide
from loopos.opengod.verdict import build_verdict
from loopos.opengod.budget import OpenGodBudgetGuard, BudgetAssessment

__all__ = [
    "OpenGodContext",
    "OpenGodDecision",
    "OpenGodDecisionKind",
    "OpenGodVerdict",
    "OpenGodVerdictStatus",
    "OpenGodEvidence",
    "collect_evidence",
    "decide",
    "build_verdict",
    "OpenGodBudgetGuard",
    "BudgetAssessment",
]
