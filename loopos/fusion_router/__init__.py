"""LoopOS Fusion Router / Mad Dog Mode.

The Fusion Router is the **escalation layer** above the default
single-model agent loop. It is *not* the default execution path:
the default remains ``single model -> ACI -> ALI -> Kernel ->
Trace``. Fusion Router activates only when there is evidence
that normal execution is insufficient (explicit user request,
repeated failure, no progress, large refactor, nasty bug,
release blocker, high user dissatisfaction, model mismatch).

This package implements the v0.2 planning layer of Fusion Router:

* :mod:`loopos.fusion_router.models` -- typed contracts
  (:class:`FusionMode`, :class:`FusionTrigger`,
  :class:`FusionTaskProfile`, :class:`ModelCapabilityProfile`,
  :class:`FusionRoleAssignment`, :class:`FusionPlan`,
  :class:`FusionVerdict`).
* :mod:`loopos.fusion_router.scoring` -- deterministic score
  calculation, mode selection, escalation check.
* :mod:`loopos.fusion_router.roles` -- role-to-capability
  matching, capability profile derivation, role assignment.
* :mod:`loopos.fusion_router.router` -- the
  :class:`FusionRouter` that wires scoring + role assignment
  into a :class:`FusionPlan`.
* :mod:`loopos.fusion_router.trace` -- bridge to the existing
  :class:`loopos.kernel.trace.TraceStore` (no new trace kind).
* :mod:`loopos.fusion_router.cli` -- internal CLI helpers used
  by the ``fusion-router`` and ``mad-dog`` CLI commands.

The router is **planning-only** in v0.2. Live multi-provider
fanout, model debate loops, automatic paid API spending, TUI,
gateway, and ACP integration are explicitly deferred to v0.3+
per the master prompt.

The router is **conservative in authority** even though it is
**aggressive in reasoning**. Fusion Router recommends ACI
commands; only ACI / Kernel / Syscall Router may execute
governed commands.
"""

from loopos.fusion_router.models import (
    FUSION_MODES,
    FUSION_ROLES,
    FUSION_TRIGGER_REASONS,
    FUSION_TRIGGER_SOURCES,
    FusionMode,
    FusionPlan,
    FusionRole,
    FusionRoleAssignment,
    FusionTaskProfile,
    FusionTrigger,
    FusionTriggerReason,
    FusionTriggerSource,
    FusionVerdict,
    ModelCapabilityProfile,
)
from loopos.fusion_router.persistence import (
    FusionPlanStore,
    list_plans,
    list_verdicts,
    load_plan,
    load_verdict,
)
from loopos.fusion_router.router import FusionRouter
from loopos.fusion_router.runner import (
    FusionRunResult,
    FusionRunner,
    describe_plan_mode,
)

__all__ = [
    "FUSION_MODES",
    "FUSION_ROLES",
    "FUSION_TRIGGER_REASONS",
    "FUSION_TRIGGER_SOURCES",
    "FusionMode",
    "FusionPlan",
    "FusionPlanStore",
    "FusionRole",
    "FusionRoleAssignment",
    "FusionRunResult",
    "FusionRouter",
    "FusionRunner",
    "FusionTaskProfile",
    "FusionTrigger",
    "FusionTriggerReason",
    "FusionTriggerSource",
    "FusionVerdict",
    "ModelCapabilityProfile",
    "describe_plan_mode",
    "list_plans",
    "list_verdicts",
    "load_plan",
    "load_verdict",
]