"""Planning-only runner that routes FusionPlan through KernelLoopEngine.

The runner is the *opt-in* adapter that turns a
:class:`FusionPlan.recommended_aci_commands` into a sequence of
:class:`loopos.aci.AgentCommand` objects and routes them through
:class:`loopos.kernel.loop_engine.KernelLoopEngine.submit_agent_command`.

It is **planning-only**: actual execution still flows through
``KernelLoopEngine.submit_agent_command`` which uses the kernel
runtime's policy engine + syscall router. The runner does not
construct a kernel runtime implicitly; tests inject a
``kernel_engine`` they already own.

Public surface:

* :class:`FusionRunner` -- the adapter.
* :meth:`FusionRunner.run` -- execute all recommended ACI commands
  against the supplied kernel engine + sessions. Returns a
  :class:`FusionRunResult`.
* :meth:`FusionRunner.dry_run` -- produce a structured
  planning-only result without dispatching.

If no ``kernel_engine`` is supplied, the runner returns a
structured dry-run result rather than raising an exception, so
``fusion-router status`` callers that have not yet wired a
kernel can still inspect the plan.

The runner never:

* calls a live provider API;
* spawns subprocesses;
* mutates files outside the FusionPlanStore root.

The runner is **conservative in authority**. Even when invoked
explicitly, every recommended command flows through the kernel
runtime's policy engine + syscall router, so Policy OS remains
the single source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from loopos.aci.models import AgentCommand, AgentCommandResult
from loopos.ali.models import AgentLoopEventRecord, AgentLoopSession
from loopos.ali.session import apply_event, create_session
from loopos.fusion_router.models import FusionPlan
from loopos.fusion_router.persistence import FusionPlanStore
from loopos.fusion_router.scoring import select_fusion_mode


class _KernelEngineLike(Protocol):
    """Minimal Protocol for the kernel engine we accept.

    ``KernelLoopEngine`` matches this Protocol. Tests inject a
    stub that records calls without spinning up a runtime.
    """

    def submit_agent_command(
        self,
        command: AgentCommand,
        session: AgentLoopSession,
        *,
        aci_runner: Any = None,
        fsm: Any = None,
    ) -> AgentCommandResult: ...


@dataclass(frozen=True)
class FusionRunResult:
    """Structured outcome of running a :class:`FusionPlan`.

    ``status`` mirrors the verdict status vocabulary:
    ``accepted``, ``rejected``, ``needs_repair``,
    ``needs_replan``, ``ask_user`` plus ``planning_only`` when
    no kernel was supplied.

    ``records`` is the ordered list of
    :class:`AgentLoopEventRecord` values returned by the kernel
    integration. ``results`` is the ordered list of
    :class:`AgentCommandResult` objects.

    When the runner falls back to planning-only, ``records`` and
    ``results`` are empty and the ``fallback_reason`` explains why.
    """

    fusion_id: str
    mode: str
    status: str
    confidence: float = 0.0
    records: list[AgentLoopEventRecord] = field(default_factory=list)
    results: list[AgentCommandResult] = field(default_factory=list)
    trace_ids: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    fallback_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "fusion_id": self.fusion_id,
            "mode": self.mode,
            "status": self.status,
            "confidence": self.confidence,
            "records": [
                {
                    "seq": r.seq,
                    "event": r.event,
                    "reason_code": r.reason_code,
                    "next_state": r.next_state,
                    "payload": dict(r.payload),
                    "created_at": r.created_at.isoformat(),
                }
                for r in self.records
            ],
            "results": [
                {
                    "command_id": r.command_id,
                    "status": r.status,
                    "success": r.success,
                    "reason_codes": list(r.reason_codes),
                    "trace_id": r.trace_id,
                }
                for r in self.results
            ],
            "trace_ids": list(self.trace_ids),
            "reason_codes": list(self.reason_codes),
            "fallback_reason": self.fallback_reason,
        }


def _command_from_template(
    fusion_id: str,
    template: dict[str, Any],
    *,
    goal_id: str | None,
) -> AgentCommand:
    """Translate a recommended command dict into an :class:`AgentCommand`.

    The router recommends commands as dicts (so the FusionPlan
    model does not need to import the ACI package). The runner
    turns each dict into a typed :class:`AgentCommand` so the
    kernel integration receives the canonical typed input.
    """

    kind = str(template.get("kind", "noop"))
    purpose = str(template.get("purpose", f"fusion:{fusion_id}"))
    role = str(template.get("role", "primary"))
    # Some kinds (``file.read`` etc.) require a non-empty command
    # string. The router recommends ``file.read`` for inspection
    # actions and ``file.patch`` for draft actions, so we supply a
    # placeholder command string the kernel can override via
    # ``args`` if needed. ``noop`` / ``provider_select`` /
    # ``explain_only`` kinds allow an empty command per the ACI
    # schema.
    no_command_kinds = frozenset({"noop", "provider_select", "explain_only"})
    raw_command = str(template.get("command", ""))
    if kind not in no_command_kinds and not raw_command.strip():
        raw_command = f"[fusion:{fusion_id}] {kind} (placeholder; caller supplies content)"
    return AgentCommand(
        goal_id=goal_id or f"fusion-{fusion_id}",
        purpose=f"[fusion:{fusion_id}] role={role} {purpose}",
        kind=kind,  # type: ignore[arg-type]
        command=raw_command,
        args=dict(template.get("args", {}) or {}),
        dry_run=bool(template.get("dry_run", True)),
        metadata={
            "fusion_id": fusion_id,
            "role": role,
            "sequence": int(template.get("sequence", 0)),
            "trigger_reason": template.get("trigger_reason", ""),
            "execution_owner": "fusion-router",
        },
    )


class FusionRunner:
    """Opt-in adapter that routes :class:`FusionPlan` through the kernel.

    The runner takes a :class:`FusionPlan` and, when invoked
    explicitly, walks ``recommended_aci_commands`` and dispatches
    each one through the supplied kernel engine. The kernel
    integration (``KernelLoopEngine.submit_agent_command``) is
    the *only* path that ever invokes Policy OS + Syscall Router,
    so the runner never bypasses governance.

    If no ``kernel_engine`` is supplied, the runner returns a
    structured dry-run result rather than raising. The CLI uses
    this to keep ``fusion-router status`` and ``mad-dog status``
    working in environments where no kernel is wired.
    """

    def __init__(
        self,
        *,
        kernel_engine: _KernelEngineLike | None = None,
        store: FusionPlanStore | None = None,
        session_factory: Any = None,
    ) -> None:
        self.kernel_engine = kernel_engine
        self.store = store or FusionPlanStore()
        self._session_factory = session_factory or create_session

    # ------------------------------------------------------------------
    # Plan execution
    # ------------------------------------------------------------------

    def run(
        self,
        plan: FusionPlan,
        *,
        sessions: dict[str, AgentLoopSession] | None = None,
        execution_enabled: bool = True,
    ) -> FusionRunResult:
        """Run the recommended commands through the supplied kernel engine.

        When ``execution_enabled`` is False or ``kernel_engine``
        is None, the runner returns a structured dry-run result.
        When ``sessions`` is supplied, the runner reuses the
        existing sessions per role instead of creating new ones.
        """

        # Persist the plan up front so the audit trail is durable
        # even if downstream execution fails.
        self.store.save_plan(plan)

        if not execution_enabled or self.kernel_engine is None:
            return FusionRunResult(
                fusion_id=plan.fusion_id,
                mode=plan.mode,
                status="planning_only",
                confidence=0.0,
                fallback_reason=(
                    "kernel_engine not supplied; returning planning-only result"
                    if self.kernel_engine is None
                    else "execution_enabled=False"
                ),
            )

        assert self.kernel_engine is not None
        sessions = sessions or {}
        records: list[AgentLoopEventRecord] = []
        results: list[AgentCommandResult] = []
        trace_ids: list[str] = []
        reason_codes: list[str] = []
        for template in plan.recommended_aci_commands:
            role = str(template.get("role", "primary"))
            session = sessions.get(role) or self._session_factory(
                goal_id=plan.task_profile.goal_id or plan.task_profile.task_id,
            )
            if not session.events:
                apply_event(session, "goal_submitted")
            command = _command_from_template(
                plan.fusion_id, template,
                goal_id=plan.task_profile.goal_id,
            )
            result = self.kernel_engine.submit_agent_command(command, session)
            records.extend(
                session.events[max(-len(records) - 2, 0) :]  # noqa: E501 - last 2
            )
            results.append(result)
            if result.trace_id:
                trace_ids.append(result.trace_id)
            reason_codes.extend(result.reason_codes)

        status = _decide_status(results)
        confidence = _compute_confidence(results)
        verdict = self.kernel_engine  # type: ignore[assignment]
        # We do NOT call kernel_engine.create_verdict because the
        # runner is not the owner of verdicts; the CLI can build
        # one via FusionRouter.create_verdict. We just return the
        # structured FusionRunResult.
        del verdict
        return FusionRunResult(
            fusion_id=plan.fusion_id,
            mode=plan.mode,
            status=status,
            confidence=confidence,
            records=records,
            results=results,
            trace_ids=trace_ids,
            reason_codes=reason_codes,
        )

    def dry_run(self, plan: FusionPlan) -> FusionRunResult:
        """Structured planning-only result without dispatching.

        Useful when the caller wants the projected commands + a
        stable summary without invoking the kernel.
        """

        self.store.save_plan(plan)
        projected_statuses = [
            template.get("kind", "noop") for template in plan.recommended_aci_commands
        ]
        return FusionRunResult(
            fusion_id=plan.fusion_id,
            mode=plan.mode,
            status="planning_only",
            confidence=0.0,
            fallback_reason="dry_run",
            reason_codes=[
                f"projected_command_{i}:{kind}"
                for i, kind in enumerate(projected_statuses)
            ],
        )

    # ------------------------------------------------------------------
    # Convenience constructors
    # ------------------------------------------------------------------

    @staticmethod
    def build_runner(
        *,
        kernel_engine: _KernelEngineLike | None = None,
        root: str | Path | None = None,
    ) -> "FusionRunner":
        """Build a runner with a default store rooted at ``root``."""

        return FusionRunner(
            kernel_engine=kernel_engine,
            store=FusionPlanStore(root=root) if root is not None else FusionPlanStore(),
        )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _decide_status(results: list[AgentCommandResult]) -> str:
    if not results:
        return "planning_only"
    if any(r.status == "blocked" for r in results):
        if any(r.status == "approval_required" for r in results):
            return "ask_user"
        return "rejected"
    if any(r.status == "failed" for r in results):
        if any(r.evaluation.repairable for r in results):
            return "needs_repair"
        if any(r.progress.no_progress for r in results):
            return "needs_replan"
        return "rejected"
    if all(r.success for r in results):
        return "accepted"
    return "needs_repair"


def _compute_confidence(results: list[AgentCommandResult]) -> float:
    if not results:
        return 0.0
    successes = sum(1 for r in results if r.success)
    return round(successes / len(results), 4)


# ---------------------------------------------------------------------------
# Mode classification helper (small wrapper for callers)
# ---------------------------------------------------------------------------


def describe_plan_mode(plan: FusionPlan) -> dict[str, Any]:
    """Return a small structured description of the plan's mode.

    Pure data; the CLI uses it to print a one-line summary.
    """

    selected = select_fusion_mode(plan.fusion_score, plan.trigger)
    return {
        "fusion_id": plan.fusion_id,
        "mode": plan.mode,
        "selected_mode": selected,
        "fusion_score": plan.fusion_score,
        "max_rounds": plan.max_rounds,
        "live_provider_calls_allowed": plan.live_provider_calls_allowed,
        "stop_conditions": list(plan.stop_conditions),
    }


__all__ = [
    "FusionRunResult",
    "FusionRunner",
    "describe_plan_mode",
]