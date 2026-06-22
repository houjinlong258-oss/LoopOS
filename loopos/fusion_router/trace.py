"""Trace bridge between the Fusion Router and the kernel trace store.

The router is planning-only in v0.2. To make plans and verdicts
durable and auditable, this module records them as trace
events using the existing :class:`loopos.kernel.trace.TraceStore`.

The router does **not** introduce a new ``TraceKind``. Both
``fusion.plan`` and ``fusion.verdict`` events are recorded as
``kind="signal"`` (a pre-existing kernel trace kind) with the
``type`` discriminator set to ``"fusion.plan"`` or
``"fusion.verdict"``. Legacy trace consumers can filter without
parsing payloads.

The bridge never calls live provider APIs; the only side
effects are ``TraceStore.append`` calls.
"""

from __future__ import annotations

from typing import Any

from loopos.fusion_router.models import FusionPlan, FusionVerdict
from loopos.kernel.trace import TraceEvent, TraceStore

FUSION_PLAN_EVENT_TYPE = "fusion.plan"
FUSION_VERDICT_EVENT_TYPE = "fusion.verdict"

# Canonical payload key order for deterministic serialisation.
_PLAN_KEY_ORDER: tuple[str, ...] = (
    "fusion_id",
    "mode",
    "fusion_score",
    "trigger",
    "task_profile",
    "max_rounds",
    "budget_limit",
    "stop_conditions",
    "live_provider_calls_allowed",
    "trace_required",
    "recommended_aci_commands",
    "assignments",
)

_VERDICT_KEY_ORDER: tuple[str, ...] = (
    "fusion_id",
    "status",
    "confidence",
    "risks",
    "required_actions",
    "reason_codes",
    "trace_ids",
    "winning_plan_id",
)


def _ordered(payload: dict[str, Any], order: tuple[str, ...]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in order:
        if key in payload:
            out[key] = payload[key]
    extras = sorted(k for k in payload if k not in out)
    for key in extras:
        out[key] = payload[key]
    return out


def record_fusion_plan(
    plan: FusionPlan,
    *,
    run_id: str,
    step: int,
    trace_store: TraceStore,
) -> TraceEvent:
    """Append a ``fusion.plan`` trace event.

    The payload is the structured FusionPlan serialised in the
    canonical key order so a replay consumer can rebuild the
    plan deterministically.
    """

    payload = _ordered(
        plan.model_dump(mode="json"),
        _PLAN_KEY_ORDER,
    )
    return trace_store.append(
        "signal",
        run_id=run_id,
        step=step,
        payload=payload,
        event_type=FUSION_PLAN_EVENT_TYPE,
    )


def record_fusion_verdict(
    verdict: FusionVerdict,
    *,
    run_id: str,
    step: int,
    trace_store: TraceStore,
) -> TraceEvent:
    """Append a ``fusion.verdict`` trace event."""

    payload = _ordered(
        verdict.model_dump(mode="json"),
        _VERDICT_KEY_ORDER,
    )
    return trace_store.append(
        "signal",
        run_id=run_id,
        step=step,
        payload=payload,
        event_type=FUSION_VERDICT_EVENT_TYPE,
    )


def replay_fusion_plans(
    trace_store: TraceStore,
    *,
    run_id: str,
) -> list[dict[str, Any]]:
    """Read persisted FusionPlan payloads from the trace store."""

    out: list[dict[str, Any]] = []
    for event in trace_store.list(run_id=run_id):
        if event.type != FUSION_PLAN_EVENT_TYPE:
            continue
        out.append(_ordered(dict(event.payload), _PLAN_KEY_ORDER))
    return out


def replay_fusion_verdicts(
    trace_store: TraceStore,
    *,
    run_id: str,
) -> list[dict[str, Any]]:
    """Read persisted FusionVerdict payloads from the trace store."""

    out: list[dict[str, Any]] = []
    for event in trace_store.list(run_id=run_id):
        if event.type != FUSION_VERDICT_EVENT_TYPE:
            continue
        out.append(_ordered(dict(event.payload), _VERDICT_KEY_ORDER))
    return out


__all__ = [
    "FUSION_PLAN_EVENT_TYPE",
    "FUSION_VERDICT_EVENT_TYPE",
    "record_fusion_plan",
    "record_fusion_verdict",
    "replay_fusion_plans",
    "replay_fusion_verdicts",
]