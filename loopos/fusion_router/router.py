"""The Fusion Router.

The router is the deterministic, planning-only entry point for
the Fusion Router / Mad Dog Mode layer. It composes the scoring
module and the role-assignment module into a
:class:`FusionPlan`, and exposes four operations:

* :meth:`FusionRouter.plan` -- build a FusionPlan without
  executing anything.
* :meth:`FusionRouter.explain` -- return a structured rationale
  for the activation decision (used by the CLI ``explain``
  subcommand).
* :meth:`FusionRouter.dry_run` -- build a plan and the
  recommended ACI commands, but never dispatch.
* :meth:`FusionRouter.create_verdict` -- record a structured
  judgment on a plan.

Hard rules (per master prompt):

* The router never calls a live provider API. It only reads the
  metadata-only :mod:`loopos.providers` registry.
* The router never executes shell / subprocess / file edits.
* Recommended ACI commands are dicts; only ACI / Kernel /
  Syscall Router may execute governed commands.
* v0.2 default is ``single`` mode; explicit user request is the
  only override of the scoring threshold.
"""

from __future__ import annotations

from typing import Any

from loopos.fusion_router.models import (
    FusionMode,
    FusionPlan,
    FusionTaskProfile,
    FusionTrigger,
    FusionTriggerReason,
    FusionVerdict,
    FusionVerdictStatus,
    ModelCapabilityProfile,
)
from loopos.fusion_router.roles import (
    assign_roles,
    required_roles_for_mode,
)
from loopos.fusion_router.scoring import (
    calculate_fusion_score,
    score_breakdown,
    select_fusion_mode,
)


# Default recommended ACI command templates. Each mode maps to a
# sequence of high-level actions the agent should take. The
# templates are intentionally small and serialise as plain
# dicts so the FusionPlan model does not need to import the ACI
# package.

_RECOMMENDED_TEMPLATES: dict[FusionMode, tuple[dict[str, Any], ...]] = {
    "single": (
        {"kind": "noop", "purpose": "baseline", "role": "primary"},
    ),
    "pair": (
        {"kind": "file.read", "purpose": "inspect context", "role": "coder"},
        {"kind": "noop", "purpose": "review patch", "role": "reviewer"},
    ),
    "committee": (
        {"kind": "file.read", "purpose": "inspect context", "role": "planner"},
        {"kind": "file.patch", "purpose": "draft minimal change", "role": "coder"},
        {"kind": "noop", "purpose": "review patch", "role": "reviewer"},
    ),
    "attack": (
        {"kind": "file.read", "purpose": "map failure surface", "role": "planner"},
        {"kind": "file.patch", "purpose": "propose minimal patch", "role": "coder"},
        {"kind": "noop", "purpose": "break patch", "role": "bug_hunter"},
        {"kind": "noop", "purpose": "attempt adversarial tests", "role": "test_breaker"},
        {"kind": "noop", "purpose": "judge verdict", "role": "judge"},
    ),
    "mad_dog": (
        {"kind": "file.read", "purpose": "inspect context", "role": "planner"},
        {"kind": "noop", "purpose": "architecture review", "role": "architect"},
        {"kind": "noop", "purpose": "break patch", "role": "bug_hunter"},
        {"kind": "file.patch", "purpose": "propose minimal patch", "role": "coder"},
        {"kind": "noop", "purpose": "attempt adversarial tests", "role": "test_breaker"},
        {"kind": "noop", "purpose": "security review", "role": "security_guard"},
        {"kind": "noop", "purpose": "simplify diff", "role": "simplifier"},
        {"kind": "noop", "purpose": "review patch", "role": "reviewer"},
        {"kind": "noop", "purpose": "judge verdict", "role": "judge"},
        {"kind": "noop", "purpose": "summarize verdict", "role": "summarizer"},
    ),
}


_MAX_ROUNDS: dict[FusionMode, int] = {
    "single": 1,
    "pair": 1,
    "committee": 2,
    "attack": 3,
    "mad_dog": 4,
}


class FusionRouter:
    """Deterministic Fusion Router.

    The router takes a :class:`FusionTaskProfile` and a
    :class:`FusionTrigger` and produces a :class:`FusionPlan`
    plus an optional structured explain / verdict payload. It is
    the only place that wires scoring + role assignment +
    recommended ACI templates together.
    """

    def __init__(
        self,
        *,
        profiles: list[ModelCapabilityProfile] | None = None,
    ) -> None:
        self._profiles = list(profiles or [])

    # ------------------------------------------------------------------
    # Profile management
    # ------------------------------------------------------------------

    def set_profiles(self, profiles: list[ModelCapabilityProfile]) -> None:
        """Replace the registry profile cache."""

        self._profiles = list(profiles)

    def register_provider(
        self,
        profile: ModelCapabilityProfile,
    ) -> None:
        """Register one capability profile (overwrites on provider_id+model_id)."""

        for index, existing in enumerate(self._profiles):
            if (
                existing.provider_id == profile.provider_id
                and existing.model_id == profile.model_id
            ):
                self._profiles[index] = profile
                return
        self._profiles.append(profile)

    # ------------------------------------------------------------------
    # Plan / explain / dry-run / verdict
    # ------------------------------------------------------------------

    def plan(
        self,
        task: FusionTaskProfile,
        trigger: FusionTrigger,
    ) -> FusionPlan:
        """Build a :class:`FusionPlan` without executing anything."""

        score = calculate_fusion_score(task, trigger)
        mode = select_fusion_mode(score, trigger)
        assignments = assign_roles(
            task, mode, self._profiles, trigger=trigger,
        )
        commands = self._recommended_commands(task, trigger, mode)
        return FusionPlan(
            mode=mode,
            trigger=trigger,
            task_profile=task,
            fusion_score=score,
            assignments=assignments,
            max_rounds=_MAX_ROUNDS[mode],
            budget_limit={
                "max_roles": len(assignments),
                "max_rounds": _MAX_ROUNDS[mode],
                "live_provider_calls_allowed": False,
            },
            stop_conditions=self._stop_conditions(mode),
            recommended_aci_commands=list(commands),
            trace_required=True,
            live_provider_calls_allowed=False,
        )

    def explain(
        self,
        task: FusionTaskProfile,
        trigger: FusionTrigger,
    ) -> dict[str, Any]:
        """Return a structured explanation for the activation decision.

        The dict is the JSON payload the CLI's ``explain`` and
        ``fusion-router status`` subcommands emit.
        """

        breakdown = score_breakdown(task, trigger)
        score = calculate_fusion_score(task, trigger)
        mode = select_fusion_mode(score, trigger)
        roles = required_roles_for_mode(mode, task.task_type, trigger)
        return {
            "activation_decision": "escalate" if mode != "single" else "single",
            "fusion_score": score,
            "selected_mode": mode,
            "trigger_reasons": [
                {"source": trigger.source, "reason": trigger.reason,
                 "severity": trigger.severity},
            ],
            "available_providers": [
                {"provider_id": profile.provider_id, "model_id": profile.model_id}
                for profile in self._profiles
            ],
            "required_roles": list(roles),
            "role_assignment_rationale": [
                {
                    "role": assignment.role,
                    "provider_id": assignment.provider_id,
                    "model_id": assignment.model_id,
                    "capability_score": assignment.capability_score,
                    "reason": assignment.reason,
                    "capability_gaps": assignment.capability_gaps,
                }
                for assignment in assign_roles(
                    task, mode, self._profiles, trigger=trigger,
                )
            ],
            "why_single_or_not": (
                "score below threshold (8)" if mode == "single"
                else f"score {score} >= threshold for mode {mode!r}"
            ),
            "score_breakdown": breakdown,
        }

    def dry_run(
        self,
        task: FusionTaskProfile,
        trigger: FusionTrigger,
    ) -> FusionPlan:
        """Build a :class:`FusionPlan` + recommended commands, never dispatch.

        Alias of :meth:`plan` for CLI parity. The router never
        dispatches anything regardless of which entry point is
        used.
        """

        return self.plan(task, trigger)

    def create_verdict(
        self,
        plan: FusionPlan,
        *,
        status: FusionVerdictStatus,
        confidence: float,
        risks: list[str] | None = None,
        required_actions: list[str] | None = None,
        reason_codes: list[str] | None = None,
        trace_ids: list[str] | None = None,
        winning_plan_id: str | None = None,
    ) -> FusionVerdict:
        """Record a structured judgment on ``plan``.

        The router does not execute anything; the verdict is
        durable audit evidence that downstream consumers (CLI,
        review, readiness) can inspect.
        """

        return FusionVerdict(
            fusion_id=plan.fusion_id,
            status=status,
            winning_plan_id=winning_plan_id,
            confidence=confidence,
            risks=list(risks or []),
            required_actions=list(required_actions or []),
            reason_codes=list(reason_codes or []),
            trace_ids=list(trace_ids or []),
        )

    # ------------------------------------------------------------------
    # Convenience constructors
    # ------------------------------------------------------------------

    @staticmethod
    def mad_dog_trigger(
        *,
        reason: FusionTriggerReason = "explicit_user_request",
        severity: str = "critical",
    ) -> FusionTrigger:
        """Build the canonical ``mad-dog`` CLI trigger.

        The CLI ``mad-dog`` alias maps to this trigger shape so
        a future review artifact can answer "why did fusion
        escalate?" with a single ``reason_code``.
        """

        return FusionTrigger(
            source="user",
            reason=reason,
            severity=severity,  # type: ignore[arg-type]
            requested_mode="mad_dog",
        )

    @staticmethod
    def escalate_trigger(
        *,
        run_id: str,
        reason: FusionTriggerReason,
        severity: str = "high",
    ) -> FusionTrigger:
        """Build an escalation trigger from kernel / convergence evidence.

        Used by ``fusion-router escalate --run-id RUN_ID --reason
        repeated_failure --json``. The ``evidence`` payload carries
        the run_id so the audit trail is complete.
        """

        return FusionTrigger(
            source="kernel",
            reason=reason,
            severity=severity,  # type: ignore[arg-type]
            evidence={"run_id": run_id},
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _recommended_commands(
        self,
        task: FusionTaskProfile,
        trigger: FusionTrigger,
        mode: FusionMode,
    ) -> tuple[dict[str, Any], ...]:
        templates = _RECOMMENDED_TEMPLATES[mode]
        out: list[dict[str, Any]] = []
        for index, template in enumerate(templates):
            out.append(
                {
                    "sequence": index,
                    "kind": template["kind"],
                    "purpose": template["purpose"],
                    "role": template["role"],
                    "task_id": task.task_id,
                    "goal_id": task.goal_id,
                    "dry_run": True,
                    "execution_owner": "aci",
                    "trigger_reason": trigger.reason,
                },
            )
        return tuple(out)

    @staticmethod
    def _stop_conditions(mode: FusionMode) -> list[str]:
        base = [
            "policy_denied",
            "no_progress",
            "all_roles_assigned_or_degraded",
        ]
        if mode in {"attack", "mad_dog"}:
            base.append("judge_verdict_recorded")
        if mode == "mad_dog":
            base.append("budget_exceeded")
            base.append("summarizer_recorded")
        return base


__all__ = [
    "FusionRouter",
]