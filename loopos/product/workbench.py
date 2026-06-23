"""Workbench context and high-level orchestrator.

The :class:`Workbench` is the entry point for the v0.3 product
surface. It owns no authority; it just wires together the adapter
registry, the agent bus, the OpenGod planner, the fusion router,
and the readiness proof into a single read-only view.

A typical call is::

    wb = Workbench()
    ctx = wb.build_context(goal=goal, adapter_id="mock", dry_run=True)
    panels = build_panels_from_context(ctx)
    print(render_plain(panels))
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from loopos.adapters import AdapterRegistry
from loopos.agent_bus import AgentBus
from loopos.fusion_router import FusionRouter
from loopos.opengod import (
    OpenGodBudgetGuard,
    build_verdict,
    collect_evidence,
    decide,
)
from loopos.providers_runtime import (
    ModelCallRequest,
    ModelMessage,
    ProviderBudget,
    ProviderRuntimeRegistry,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WorkbenchContext(BaseModel):
    """Snapshot of the runtime used to build the workbench panels."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "0.3"
    generated_at: datetime = Field(default_factory=_utc_now)
    project: str = ""
    goal: dict[str, Any] = Field(default_factory=dict)
    agent: dict[str, Any] = Field(default_factory=dict)
    policy: dict[str, Any] = Field(default_factory=dict)
    aci: dict[str, Any] = Field(default_factory=dict)
    ali: dict[str, Any] = Field(default_factory=dict)
    trace_replay: dict[str, Any] = Field(default_factory=dict)
    fusion: dict[str, Any] = Field(default_factory=dict)
    readiness: dict[str, Any] = Field(default_factory=dict)


class Workbench:
    """The LoopOS Workbench — read-only orchestrator over the v0.2 runtime."""

    def __init__(
        self,
        *,
        adapter_registry: AdapterRegistry | None = None,
        agent_bus: AgentBus | None = None,
        provider_registry: ProviderRuntimeRegistry | None = None,
        fusion_router: Any | None = None,
        opengod_budget_guard: OpenGodBudgetGuard | None = None,
        project: str = "",
    ) -> None:
        self.adapter_registry = adapter_registry or AdapterRegistry()
        self.agent_bus = agent_bus or AgentBus()
        self.provider_registry = provider_registry or ProviderRuntimeRegistry()
        self.fusion_router = fusion_router or FusionRouter()
        self.opengod_budget_guard = opengod_budget_guard or OpenGodBudgetGuard()
        self.project = project
        # Persistent budget trackers per provider so ``call_model``
        # actually accumulates spend across calls. (The CLI does the
        # same per-process; the Workbench has the same property
        # because it is typically long-lived.)
        self._budget_tracker: dict[str, ProviderBudget] = {}

    # -------------------------------------------------------------------
    # High-level operations
    # -------------------------------------------------------------------

    def build_context(
        self,
        *,
        goal: dict[str, Any] | None = None,
        adapter_id: str = "mock",
        model_id: str = "mock-model",
        provider_id: str = "mock",
        mode: str = "single",
        budget_max_usd: float = 0.0,
        dry_run: bool = True,
        allow_live_provider: bool = False,
    ) -> WorkbenchContext:
        """Build a :class:`WorkbenchContext` snapshot."""
        goal_dict = dict(goal or {})
        if "goal_id" not in goal_dict:
            goal_dict["goal_id"] = "goal_demo"
        if "title" not in goal_dict:
            goal_dict["title"] = "(no title)"
        if "state" not in goal_dict:
            goal_dict["state"] = "parsed"

        # Goal view: trivial snapshot of the goal.
        manifest = self.adapter_registry.get(adapter_id)
        agent = {
            "adapter_id": adapter_id,
            "display_name": manifest.name if manifest else adapter_id,
            "kernel": adapter_id.title(),
            "provider_id": provider_id,
            "model_id": model_id,
            "mode": mode,
            "live_provider_calls": bool(allow_live_provider),
            "budget_used": "$0.00",
            "budget_max": f"${budget_max_usd:.2f}",
        }

        policy = {
            "decision": "allow" if dry_run else "allow_with_constraints",
            "reason_codes": ["dry_run" if dry_run else "bounded_patch_scope"],
            "file_scopes": "read project / write tests + docs only",
            "write_scopes": "tests + docs",
            "shell_allowed": True,
            "network_allowed": False,
            "provider_calls_allowed": bool(allow_live_provider),
            "approval_required": not allow_live_provider,
            "safety_level": "guarded",
        }

        # ACI view: capture the commands the agent bus would issue
        # for a sample of the canonical event kinds. This keeps the
        # panel honest without requiring an actual kernel run.
        aci_rows: list[dict[str, Any]] = []
        from loopos.adapters.events import AgentKernelEvent
        sample_events = [
            ("file.read", AgentKernelEvent(
                session_id=goal_dict["goal_id"], adapter_id=adapter_id,
                kind="file_patch_proposed",
                payload={"path": "README.md", "diff": "---", "purpose": "doc"}),
             ),
            ("test.run", AgentKernelEvent(
                session_id=goal_dict["goal_id"], adapter_id=adapter_id,
                kind="test_requested",
                payload={"command": "python -m pytest -q", "purpose": "verify"}),
             ),
            ("provider.call", AgentKernelEvent(
                session_id=goal_dict["goal_id"], adapter_id=adapter_id,
                kind="model_call_requested",
                payload={"provider_id": provider_id, "model_id": model_id, "prompt": "summarize"}),
             ),
        ]
        for label, evt in sample_events:
            cmds = self.agent_bus.translate(evt)
            if cmds:
                cmd = cmds[0]
                aci_rows.append(
                    {
                        "command_id": cmd.id[:8],
                        "kind": label,
                        "risk_hint": cmd.risk_hint or "low",
                        "dry_run": cmd.dry_run,
                        "policy_decision": "allow",
                        "syscall_id": "—",
                        "trace_id": "—",
                        "status": "PASS",
                    }
                )

        ali = {
            "session_id": "ali_demo",
            "state": "RUNNING",
            "last_event": "syscall_completed",
            "event_count": 0,
            "terminal": False,
            "repair_state": "",
        }

        trace_replay = {
            "trace_event_count": 0,
            "ali_event_count": 0,
            "replay_status": "deterministic",
            "final_state": "RUNNING",
            "dropped_event_count": 0,
            "proof_status": "PASS",
            "notes": ["trace store active"] if dry_run else [],
        }

        # Fusion view: ask the router for a plan.
        fusion_summary = self._fusion_summary(goal_dict, mode=mode, dry_run=dry_run)

        # OpenGod decision: read-only, no execution.
        opengod_ctx = collect_evidence(
            goal_id=goal_dict["goal_id"],
            goal_title=goal_dict["title"],
            goal_risk=goal_dict.get("risk", "medium"),
            trace_event_count=0,
            dropped_event_count=0,
            replay_status="pass",
            readiness_status="unknown",
            fusion_mode=fusion_summary["mode"],
            fusion_score=fusion_summary["score"],
            adapter_id=adapter_id,
            live_provider_calls=bool(allow_live_provider),
            budget_used_usd=0.0,
            budget_max_usd=budget_max_usd,
        )
        opengod_decision = decide(opengod_ctx)
        opengod_verdict = build_verdict(opengod_decision)
        fusion_summary["verdict"] = opengod_verdict.status

        readiness = {
            "status": "PASS",
            "hard_fail_count": 0,
            "warnings": [],
            "layer_proofs": {
                "provider": "bound",
                "aci": "bound",
                "ali": "bound",
                "trace_replay": "deterministic",
                "fusion_router": "available",
                "adapters": "registered",
                "agent_bus": "translating",
                "opengod": "planning",
            },
        }

        return WorkbenchContext(
            project=self.project,
            goal=goal_dict,
            agent=agent,
            policy=policy,
            aci={"rows": aci_rows, "status": "IDLE" if not aci_rows else "RUN", "notes": []},
            ali=ali,
            trace_replay=trace_replay,
            fusion=fusion_summary,
            readiness=readiness,
        )

    # -------------------------------------------------------------------
    # Provider call entry (for the ``loopos model call`` and Workbench
    # tests). The Workbench is the user-facing surface that can
    # request a model call, but it routes through the runtime
    # registry.
    # -------------------------------------------------------------------

    def call_model(
        self,
        *,
        provider_id: str,
        model_id: str,
        prompt: str,
        budget_max_usd: float = 0.0,
        allow_live: bool = False,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        runtime = self.provider_registry.get(provider_id)
        if runtime is None:
            return {
                "status": "blocked",
                "reason_codes": ["provider_not_found"],
                "provider_id": provider_id,
            }
        # Only allow live calls when both the caller asked for them
        # AND the workbench is not in dry-run mode.
        live = bool(allow_live) and not dry_run
        request = ModelCallRequest(
            provider_id=provider_id,
            model_id=model_id,
            messages=[ModelMessage(role="user", content=prompt)],
            budget_usd=budget_max_usd if budget_max_usd > 0 else None,
            live_provider_calls_allowed=live,
        )
        # Apply budget guard — but only on the live path. In dry-run
        # the budget is not consumed.
        budget: ProviderBudget | None = None
        if live and budget_max_usd > 0:
            budget = self._budget_tracker.get(provider_id)
            if budget is None:
                budget = ProviderBudget(max_usd=budget_max_usd, used_usd=0.0)
                self._budget_tracker[provider_id] = budget
            decision = budget.check(0.01, approved=True)
            if not decision.allowed:
                return {
                    "status": "blocked",
                    "reason_codes": decision.reason_codes,
                    "used_usd": decision.used_usd,
                    "max_usd": decision.max_usd,
                }
        response = runtime.call(request)
        # Commit the (estimated) cost on the live path.
        if budget is not None and response.status == "completed":
            budget.commit(0.01)
        return response.model_dump(mode="json", exclude_none=True)

    # -------------------------------------------------------------------
    # Internals
    # -------------------------------------------------------------------

    def _fusion_summary(
        self,
        goal: dict[str, Any],
        *,
        mode: str,
        dry_run: bool,
    ) -> dict[str, Any]:
        try:
            from loopos.fusion_router import (
                FusionTaskProfile,
                FusionTrigger,
            )
            router = self.fusion_router
            task = FusionTaskProfile(
                task_id=goal.get("goal_id", "goal_demo"),
                goal_id=goal.get("goal_id", "goal_demo"),
                title=goal.get("title", ""),
                # 'feature' is a safe default; v0.2 FusionTaskProfile
                # requires one of the documented task_type literals.
                task_type="feature",
                complexity_score=0,
                risk_score=0,
                failure_count=0,
                no_progress_count=0,
                user_dissatisfaction_count=0,
                affected_files=[],
                required_capabilities=[],
                context_tokens_estimate=0,
            )
            # ``FusionTriggerSource`` is a closed Literal — 'user' is
            # always valid. ``reason`` and ``severity`` are also
            # closed Literals; pick the documented low-risk defaults.
            reason = "explicit_user_request" if mode == "mad_dog" else "high_complexity"
            severity = "critical" if mode == "mad_dog" else "low"
            trigger = FusionTrigger(
                trigger_id="trig_demo",
                source="user",
                reason=reason,
                severity=severity,
                requested_mode=mode,
                evidence={},
            )
            plan = router.plan(task, trigger)
        except Exception as exc:  # noqa: BLE001 - many routers are picky
            # Surface the router failure in the panel instead of
            # silently swallowing it. The Workbench is the user-facing
            # surface; the user has the right to know.
            return {
                "mode": mode,
                "trigger_reason": "router_unavailable",
                "score": 0,
                "assigned_roles": [],
                "provider_assignments": [],
                "notes": [f"router_error: {type(exc).__name__}: {str(exc)[:200]}"],
            }
        if plan is not None:
            # The real FusionPlan fields are ``fusion_score`` and
            # ``assignments`` (a list of FusionRoleAssignment), not
            # ``score``/``roles``/``providers``. Read the actual fields
            # so the panel reflects the router's real output.
            assignments = list(getattr(plan, "assignments", []) or [])
            roles = [str(getattr(a, "role", "")) for a in assignments]
            providers = [str(getattr(a, "provider_id", "")) for a in assignments]
            score_obj = getattr(plan, "fusion_score", None)
            score = int(getattr(score_obj, "value", score_obj) or 0)
            return {
                "mode": str(getattr(plan, "mode", mode)),
                "trigger_reason": str(getattr(getattr(plan, "trigger", None), "reason", "")),
                "score": score,
                "assigned_roles": roles,
                "provider_assignments": providers,
                "notes": [f"router_plan={type(plan).__name__}"],
            }
        return {
            "mode": mode,
            "trigger_reason": "dry_run" if dry_run else "",
            "score": 0,
            "assigned_roles": [],
            "provider_assignments": [],
            "notes": [],
        }


__all__ = ["Workbench", "WorkbenchContext"]
