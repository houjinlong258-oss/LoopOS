"""Fusion Verdict Orchestration (caller-driven).

The :class:`FusionVerdictOrchestrator` consumes a
:class:`loopos.fusion_router.FusionVerdict` and produces a
:candidate_orchestration` describing the **next** ALI state and the
:class:`~loopos.aci.models.AgentCommand` to submit (if any).

The orchestrator is **caller-driven**: it does not run as a daemon,
does not call providers, does not push or release. The caller (the
workbench / the user) is responsible for actually submitting the
produced command through the ACI runner.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from loopos.aci.models import AgentCommand, AgentCommandResult
from loopos.aci.runner import CommandRunner
from loopos.fusion_router import FusionVerdict


class OrchestrationResult(BaseModel):
    """Structured result of a verdict orchestration step."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "0.3"
    verdict_id: str = ""
    status: str = "no_action"  # "no_action" | "submitted" | "blocked" | "halted"
    next_ali_state: str = ""
    command: AgentCommand | None = None
    command_result: AgentCommandResult | None = None
    reason_codes: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class FusionVerdictOrchestrator:
    """Caller-driven orchestrator for fusion verdicts."""

    def __init__(self, *, runner: CommandRunner | None = None) -> None:
        self._runner = runner or CommandRunner()

    def orchestrate(
        self,
        verdict: FusionVerdict,
        *,
        goal_id: str = "goal_demo",
        session_id: str = "ali_demo",
        dry_run: bool = True,
    ) -> OrchestrationResult:
        """Translate a :class:`FusionVerdict` into a next step."""
        verdict_id = str(getattr(verdict, "verdict_id", getattr(verdict, "fusion_id", "")))
        status = str(getattr(verdict, "status", ""))
        if status == "needs_repair":
            return self._submit(
                verdict,
                kind="noop",
                purpose="repair.plan",
                next_ali_state="REPAIRING",
                goal_id=goal_id,
                session_id=session_id,
                dry_run=dry_run,
                reason="verdict_needs_repair",
            )
        if status == "needs_replan":
            return self._submit(
                verdict,
                kind="noop",
                purpose="goal.replan",
                next_ali_state="REPLANNING",
                goal_id=goal_id,
                session_id=session_id,
                dry_run=dry_run,
                reason="verdict_needs_replan",
            )
        if status == "rejected":
            return OrchestrationResult(
                verdict_id=verdict_id,
                status="halted",
                next_ali_state="HALTED_FAILURE",
                reason_codes=["verdict_rejected"],
            )
        if status == "ask_user":
            return OrchestrationResult(
                verdict_id=verdict_id,
                status="no_action",
                next_ali_state="WAITING_APPROVAL",
                reason_codes=["verdict_ask_user"],
            )
        return OrchestrationResult(
            verdict_id=verdict_id,
            status="no_action",
            next_ali_state="",
            reason_codes=["verdict_no_action"],
        )

    # -------------------------------------------------------------------

    def _submit(
        self,
        verdict: FusionVerdict,
        *,
        kind: str,
        purpose: str,
        next_ali_state: str,
        goal_id: str,
        session_id: str,
        dry_run: bool,
        reason: str,
    ) -> OrchestrationResult:
        command = AgentCommand(
            schema_version="0.2",
            goal_id=goal_id,
            purpose=purpose,
            kind=kind,  # type: ignore[arg-type]
            command=purpose,
            session_id=session_id,
            mode="dry_run" if dry_run else "guarded",
            dry_run=dry_run,
            trace_required=True,
            metadata={
                "source": "fusion_verdict_orchestrator",
                "verdict_id": str(getattr(verdict, "verdict_id", getattr(verdict, "fusion_id", ""))),
                "reason": reason,
            },
        )
        # ``CommandRunner.run(explain=True)`` short-circuits without
        # actually executing; ``explain=False`` lets the runner go
        # through the full pipeline. Pass the same flag as the caller's
        # intent: dry_run=True → explain=True; dry_run=False → explain=False.
        result = self._runner.run(command, explain=dry_run)
        return OrchestrationResult(
            verdict_id=str(getattr(verdict, "verdict_id", getattr(verdict, "fusion_id", ""))),
            status="submitted",
            next_ali_state=next_ali_state,
            command=command,
            command_result=result,
            reason_codes=[reason],
        )


__all__ = ["FusionVerdictOrchestrator", "OrchestrationResult"]
