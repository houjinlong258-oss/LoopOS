"""Workbench — build panels from a runtime context.

The :func:`build_panels_from_context` function is the bridge between
the workbench runtime (adapter, agent bus, kernel, trace, fusion,
readiness) and the workbench views. It takes a :class:`WorkbenchContext`
and returns a :class:`PanelLayout` that the renderer can serialise.

The function is **pure**: same context -> same panels. It does not
mutate the context and does not dispatch any commands.
"""

from __future__ import annotations


from loopos.product.panel_layout import (
    DEFAULT_PANEL_ORDER,
)
from loopos.product.views import (
    AciView,
    AgentView,
    AliView,
    FusionView,
    GoalView,
    PanelLayout,
    PolicyView,
    ReadinessView,
    TraceReplayView,
)
from loopos.product.workbench import WorkbenchContext


def build_panels_from_context(context: WorkbenchContext) -> PanelLayout:
    """Return a :class:`PanelLayout` populated from ``context``."""
    return PanelLayout(
        goal=_build_goal(context),
        agent=_build_agent(context),
        policy=_build_policy(context),
        aci=_build_aci(context),
        ali=_build_ali(context),
        trace_replay=_build_trace_replay(context),
        fusion=_build_fusion(context),
        readiness=_build_readiness(context),
    )


def panel_order() -> tuple[str, ...]:
    """The fixed render order of the workbench panels."""
    return DEFAULT_PANEL_ORDER


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_goal(context: WorkbenchContext) -> GoalView:
    goal = context.goal or {}
    return GoalView(
        title=goal.get("title", "") or "(no goal)",
        status=goal.get("state", "parsed"),
        notes=[f"id={goal.get('goal_id', 'goal_???')}"],
        data={
            "goal_id": goal.get("goal_id", "goal_???"),
            "title": goal.get("title", ""),
            "intent": goal.get("intent", ""),
            "acceptance": goal.get("acceptance", ""),
            "risk": goal.get("risk", "medium"),
            "state": goal.get("state", "parsed"),
            "progress": goal.get("progress", ""),
        },
    )


def _build_agent(context: WorkbenchContext) -> AgentView:
    agent = context.agent or {}
    return AgentView(
        title=agent.get("display_name", "Mock Agent"),
        status=agent.get("mode", "single"),
        notes=[
            f"adapter={agent.get('adapter_id', 'mock')}",
            f"provider={agent.get('provider_id', 'mock')}",
        ],
        data={
            "adapter_id": agent.get("adapter_id", "mock"),
            "kernel": agent.get("kernel", "Mock"),
            "provider_id": agent.get("provider_id", "mock"),
            "model_id": agent.get("model_id", "mock-model"),
            "mode": agent.get("mode", "single"),
            "live_provider_calls": agent.get("live_provider_calls", False),
            "budget_used": agent.get("budget_used", "$0.00"),
            "budget_max": agent.get("budget_max", "$0.00"),
        },
    )


def _build_policy(context: WorkbenchContext) -> PolicyView:
    policy = context.policy or {}
    return PolicyView(
        title="Policy OS",
        status=policy.get("decision", "allow"),
        notes=policy.get("reason_codes", []) or ["bounded_patch_scope"],
        data={
            "file_scopes": policy.get("file_scopes", "read project / write tests + docs only"),
            "write_scopes": policy.get("write_scopes", "tests + docs"),
            "shell_allowed": policy.get("shell_allowed", True),
            "network_allowed": policy.get("network_allowed", False),
            "provider_calls_allowed": policy.get("provider_calls_allowed", False),
            "approval_required": policy.get("approval_required", True),
            "safety_level": policy.get("safety_level", "guarded"),
            "decision": policy.get("decision", "allow"),
            "reason_codes": policy.get("reason_codes", []) or ["bounded_patch_scope"],
        },
    )


def _build_aci(context: WorkbenchContext) -> AciView:
    aci = context.aci or {}
    rows = aci.get("rows", [])
    return AciView(
        title="ACI Commands",
        status=aci.get("status", "IDLE"),
        notes=aci.get("notes", []) or [],
        data={
            "rows": rows,
            "command_count": len(rows),
        },
    )


def _build_ali(context: WorkbenchContext) -> AliView:
    ali = context.ali or {}
    return AliView(
        title=ali.get("session_id", "ali_???"),
        status=ali.get("state", "CREATED"),
        notes=ali.get("reason_codes", []) or [],
        data={
            "session_id": ali.get("session_id", "ali_???"),
            "state": ali.get("state", "CREATED"),
            "last_event": ali.get("last_event", "ali.session_created"),
            "event_count": ali.get("event_count", 0),
            "terminal": ali.get("terminal", False),
            "repair_state": ali.get("repair_state", ""),
        },
    )


def _build_trace_replay(context: WorkbenchContext) -> TraceReplayView:
    tr = context.trace_replay or {}
    return TraceReplayView(
        title="Trace / Replay",
        status=tr.get("replay_status", "deterministic"),
        notes=tr.get("notes", []) or [],
        data={
            "trace_event_count": tr.get("trace_event_count", 0),
            "ali_event_count": tr.get("ali_event_count", 0),
            "replay_status": tr.get("replay_status", "deterministic"),
            "final_state": tr.get("final_state", "RUNNING"),
            "dropped_event_count": tr.get("dropped_event_count", 0),
            "proof_status": tr.get("proof_status", "PASS"),
        },
    )


def _build_fusion(context: WorkbenchContext) -> FusionView:
    fusion = context.fusion or {}
    return FusionView(
        title="Fusion Router",
        status=fusion.get("mode", "single"),
        notes=fusion.get("notes", []) or [],
        data={
            "mode": fusion.get("mode", "single"),
            "trigger_reason": fusion.get("trigger_reason", ""),
            "score": fusion.get("score", 0),
            "assigned_roles": fusion.get("assigned_roles", []),
            "provider_assignments": fusion.get("provider_assignments", []),
            "verdict": fusion.get("verdict", "ok"),
        },
    )


def _build_readiness(context: WorkbenchContext) -> ReadinessView:
    rd = context.readiness or {}
    return ReadinessView(
        title="Readiness",
        status=rd.get("status", "PASS"),
        notes=rd.get("warnings", []) or [],
        data={
            "status": rd.get("status", "PASS"),
            "hard_fail_count": rd.get("hard_fail_count", 0),
            "warnings": rd.get("warnings", []) or [],
            "layer_proofs": rd.get("layer_proofs", {}) or {},
        },
    )


__all__ = ["build_panels_from_context", "panel_order"]
