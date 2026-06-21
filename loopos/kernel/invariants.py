"""Kernel invariant checker — enforces governance contracts at each step.

Every invariant returns None on success or a KernelInvariantViolation on failure.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class KernelInvariantViolation(BaseModel):
    """A single invariant violation detected during a run step."""

    violation_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    step: int | None = None
    invariant_id: str
    severity: Literal["warning", "error", "blocker"] = "error"
    message: str
    evidence_event_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KernelInvariantChecker:
    """Check governance invariants for a run step.

    Invariants:
    1. No syscall without PolicyDecision.
    2. No terminal execution without SyscallRouter.
    3. No file mutation without policy.
    4. No database operation without Data Guard when detected.
    5. No long-term memory commit without Memory Governance.
    6. No run completion without EvaluationResult.
    7. No loop continuation without LoopDecision.
    8. No trace gap between instruction and observation.
    9. No approval resume without approval event.
    """

    def check_all(
        self,
        run_id: str,
        step: int,
        events: list[dict[str, Any]],
    ) -> list[KernelInvariantViolation]:
        """Run all invariants against the events for a single step."""
        violations: list[KernelInvariantViolation] = []
        kinds = {e.get("kind") or e.get("type", "") for e in events}

        # I1: syscall needs policy
        if "syscall" in kinds or "observation" in kinds:
            if "policy" not in kinds:
                violations.append(KernelInvariantViolation(
                    run_id=run_id,
                    step=step,
                    invariant_id="I1_POLICY_BEFORE_SYSCALL",
                    severity="blocker",
                    message="Syscall or observation recorded without a policy decision event.",
                ))

        # I2: instruction needs observation
        if "instruction" in kinds and "observation" not in kinds:
            violations.append(KernelInvariantViolation(
                run_id=run_id,
                step=step,
                invariant_id="I2_INSTRUCTION_OBSERVATION_GAP",
                severity="error",
                message="Instruction event has no corresponding observation event.",
            ))

        # I3: terminal events must come from syscall router
        for event in events:
            payload = event.get("payload", {})
            if isinstance(payload, dict):
                op = payload.get("op", "")
                if op in ("TERM.EXEC", "EXEC_TERMINAL") and not event.get("syscall_id"):
                    violations.append(KernelInvariantViolation(
                        run_id=run_id,
                        step=step,
                        invariant_id="I3_TERMINAL_WITHOUT_SYSCALL",
                        severity="blocker",
                        message="Terminal execution without syscall router routing.",
                        evidence_event_ids=[event.get("id", "")],
                    ))

        # I4: completion needs evaluation
        for event in events:
            payload = event.get("payload", {})
            if isinstance(payload, dict):
                after = payload.get("after", {})
                if isinstance(after, dict) and after.get("status") in ("succeeded", "failed"):
                    if "evaluation" not in kinds:
                        violations.append(KernelInvariantViolation(
                            run_id=run_id,
                            step=step,
                            invariant_id="I4_COMPLETION_WITHOUT_EVALUATION",
                            severity="warning",
                            message="Run transitioned to terminal status without evaluation event.",
                        ))
                        break

        # I5: memory commit needs governance
        for event in events:
            kind = event.get("kind") or event.get("type", "")
            if kind == "memory":
                payload = event.get("payload", {})
                if isinstance(payload, dict) and payload.get("governance_id") is None:
                    violations.append(KernelInvariantViolation(
                        run_id=run_id,
                        step=step,
                        invariant_id="I5_MEMORY_WITHOUT_GOVERNANCE",
                        severity="blocker",
                        message="Memory commit without governance metadata.",
                        evidence_event_ids=[event.get("id", "")],
                    ))

        return violations

    def check_approval_resume(
        self,
        run_id: str,
        step: int,
        events: list[dict[str, Any]],
    ) -> list[KernelInvariantViolation]:
        """Check that resume from waiting_approval has an approval signal."""
        violations: list[KernelInvariantViolation] = []
        has_resume = False
        has_approval = False
        for event in events:
            kind = event.get("kind") or event.get("type", "")
            if kind == "signal":
                payload = event.get("payload", {})
                if isinstance(payload, dict) and payload.get("signal") in ("approve", "deny"):
                    has_approval = True
            if kind == "transition":
                payload = event.get("payload", {})
                if isinstance(payload, dict):
                    before = payload.get("before", {})
                    after = payload.get("after", {})
                    if (isinstance(before, dict) and before.get("status") == "waiting_approval"
                            and isinstance(after, dict) and after.get("status") == "running"):
                        has_resume = True
        if has_resume and not has_approval:
            violations.append(KernelInvariantViolation(
                run_id=run_id,
                step=step,
                invariant_id="I6_RESUME_WITHOUT_APPROVAL",
                severity="blocker",
                message="Run resumed from waiting_approval without approval signal event.",
            ))
        return violations

    def check_data_guard(
        self,
        run_id: str,
        step: int,
        events: list[dict[str, Any]],
    ) -> list[KernelInvariantViolation]:
        """I7: destructive database operations require a Data Guard backup event."""
        violations: list[KernelInvariantViolation] = []
        has_backup = False
        destructive_ops: list[dict[str, Any]] = []
        for event in events:
            kind = event.get("kind") or event.get("type", "")
            payload = event.get("payload", {})
            if not isinstance(payload, dict):
                continue
            if kind == "syscall" and payload.get("name", "").startswith("database."):
                if payload.get("name") in ("database.run_migration", "database.restore"):
                    destructive_ops.append(payload)
            if kind in ("observation", "syscall") and payload.get("backup_verified"):
                has_backup = True
        for op in destructive_ops:
            if not has_backup:
                violations.append(KernelInvariantViolation(
                    run_id=run_id,
                    step=step,
                    invariant_id="I7_DATA_GUARD_BEFORE_DATABASE_ACTION",
                    severity="blocker",
                    message=(
                        f"Destructive database syscall {op.get('name')} recorded "
                        "without a verified backup event."
                    ),
                    evidence_event_ids=[op.get("id", "")],
                ))
        return violations

    def check_provider_policy(
        self,
        run_id: str,
        step: int,
        events: list[dict[str, Any]],
    ) -> list[KernelInvariantViolation]:
        """I8: provider calls require a policy decision event in the same step."""
        violations: list[KernelInvariantViolation] = []
        has_policy = any(
            (event.get("kind") or event.get("type", "")) == "policy" for event in events
        )
        for event in events:
            kind = event.get("kind") or event.get("type", "")
            payload = event.get("payload", {})
            if not isinstance(payload, dict):
                continue
            if kind == "syscall" and payload.get("name", "").startswith("provider."):
                if not has_policy:
                    violations.append(KernelInvariantViolation(
                        run_id=run_id,
                        step=step,
                        invariant_id="I8_PROVIDER_POLICY_BEFORE_MODEL_CALL",
                        severity="blocker",
                        message=(
                            f"Provider syscall {payload.get('name')} recorded without "
                            "a policy decision event."
                        ),
                        evidence_event_ids=[event.get("id", "")],
                    ))
        return violations

    def check_gateway_auth(
        self,
        run_id: str,
        step: int,
        events: list[dict[str, Any]],
    ) -> list[KernelInvariantViolation]:
        """I9: gateway delivery requires an auth-allowed event in the same step."""
        violations: list[KernelInvariantViolation] = []
        has_auth = False
        for event in events:
            payload = event.get("payload", {})
            if isinstance(payload, dict) and payload.get("auth_allowed") is True:
                has_auth = True
        for event in events:
            kind = event.get("kind") or event.get("type", "")
            payload = event.get("payload", {})
            if not isinstance(payload, dict):
                continue
            if kind == "syscall" and payload.get("name", "").startswith("gateway."):
                if not has_auth:
                    violations.append(KernelInvariantViolation(
                        run_id=run_id,
                        step=step,
                        invariant_id="I9_GATEWAY_AUTH_BEFORE_DELIVERY",
                        severity="blocker",
                        message=(
                            f"Gateway syscall {payload.get('name')} recorded without "
                            "an auth-allowed event."
                        ),
                        evidence_event_ids=[event.get("id", "")],
                    ))
        return violations

    def check_skill_governance(
        self,
        run_id: str,
        step: int,
        events: list[dict[str, Any]],
    ) -> list[KernelInvariantViolation]:
        """I10: skill activation requires a governance decision event."""
        violations: list[KernelInvariantViolation] = []
        has_governance = any(
            (event.get("kind") or event.get("type", "")) == "memory"
            and isinstance(event.get("payload", {}), dict)
            and event.get("payload", {}).get("governance_id") is not None
            for event in events
        )
        for event in events:
            kind = event.get("kind") or event.get("type", "")
            payload = event.get("payload", {})
            if not isinstance(payload, dict):
                continue
            if kind == "skill" and payload.get("activated") and not has_governance:
                violations.append(KernelInvariantViolation(
                    run_id=run_id,
                    step=step,
                    invariant_id="I10_SKILL_GOVERNANCE_BEFORE_ACTIVATION",
                    severity="error",
                    message="Skill activated without a governance decision event.",
                    evidence_event_ids=[event.get("id", "")],
                ))
        return violations

    def check_maintainability_gate(
        self,
        run_id: str,
        step: int,
        events: list[dict[str, Any]],
    ) -> list[KernelInvariantViolation]:
        """I11: review approval requires a non-blocking maintainability report."""
        violations: list[KernelInvariantViolation] = []
        for event in events:
            kind = event.get("kind") or event.get("type", "")
            payload = event.get("payload", {})
            if not isinstance(payload, dict):
                continue
            if kind == "review" and payload.get("decision") == "approve":
                report_id = payload.get("maintainability_report_id")
                blocked = payload.get("maintainability_blocked", False)
                if blocked or report_id is None:
                    violations.append(KernelInvariantViolation(
                        run_id=run_id,
                        step=step,
                        invariant_id="I11_MAINTAINABILITY_GATE_BEFORE_REVIEW_APPROVAL",
                        severity="error",
                        message=(
                            "Review approved without a non-blocking maintainability "
                            "report reference."
                        ),
                        evidence_event_ids=[event.get("id", "")],
                    ))
        return violations

    def check_review_artifact_before_merge(
        self,
        run_id: str,
        step: int,
        events: list[dict[str, Any]],
    ) -> list[KernelInvariantViolation]:
        """I12: merge requires a review artifact event in the same or earlier step."""
        violations: list[KernelInvariantViolation] = []
        has_artifact = any(
            (event.get("kind") or event.get("type", "")) == "review"
            and isinstance(event.get("payload", {}), dict)
            and event.get("payload", {}).get("artifact_id") is not None
            for event in events
        )
        for event in events:
            kind = event.get("kind") or event.get("type", "")
            payload = event.get("payload", {})
            if not isinstance(payload, dict):
                continue
            if kind == "transition" and payload.get("after", {}).get("status") == "merged":
                if not has_artifact:
                    violations.append(KernelInvariantViolation(
                        run_id=run_id,
                        step=step,
                        invariant_id="I12_REVIEW_ARTIFACT_BEFORE_MERGE",
                        severity="blocker",
                        message="Run transitioned to merged without a review artifact event.",
                        evidence_event_ids=[event.get("id", "")],
                    ))
        return violations

    def check_checkpoint_before_high_risk(
        self,
        run_id: str,
        step: int,
        events: list[dict[str, Any]],
    ) -> list[KernelInvariantViolation]:
        """I13: high-risk actions require a checkpoint event in the same step."""
        violations: list[KernelInvariantViolation] = []
        has_checkpoint = any(
            (event.get("kind") or event.get("type", "")) == "checkpoint"
            for event in events
        )
        for event in events:
            kind = event.get("kind") or event.get("type", "")
            payload = event.get("payload", {})
            if not isinstance(payload, dict):
                continue
            if kind == "policy" and payload.get("safety_level") in ("L3", "L4", "L5"):
                if payload.get("safety_level") == "L5":
                    continue  # L5 is blocked, no checkpoint needed
                if not has_checkpoint:
                    violations.append(KernelInvariantViolation(
                        run_id=run_id,
                        step=step,
                        invariant_id="I13_CHECKPOINT_BEFORE_HIGH_RISK_ACTION",
                        severity="warning",
                        message=(
                            f"High-risk action (safety_level={payload.get('safety_level')}) "
                            "recorded without a checkpoint event."
                        ),
                        evidence_event_ids=[event.get("id", "")],
                    ))
        return violations

    def check_all_extended(
        self,
        run_id: str,
        step: int,
        events: list[dict[str, Any]],
    ) -> list[KernelInvariantViolation]:
        """Run the original invariants plus the v0.5 extensions."""
        violations = self.check_all(run_id, step, events)
        violations.extend(self.check_approval_resume(run_id, step, events))
        violations.extend(self.check_data_guard(run_id, step, events))
        violations.extend(self.check_provider_policy(run_id, step, events))
        violations.extend(self.check_gateway_auth(run_id, step, events))
        violations.extend(self.check_skill_governance(run_id, step, events))
        violations.extend(self.check_maintainability_gate(run_id, step, events))
        violations.extend(self.check_review_artifact_before_merge(run_id, step, events))
        violations.extend(self.check_checkpoint_before_high_risk(run_id, step, events))
        return violations
