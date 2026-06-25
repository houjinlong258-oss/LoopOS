"""Computer Control Runtime session runner."""

from __future__ import annotations

from datetime import datetime, timezone

from loopos.computer_control.approval import build_approval
from loopos.computer_control.backends import (
    BrowserComputerBackend,
    ComputerBackend,
    FakeComputerBackend,
    LocalOptionalComputerBackend,
)
from loopos.computer_control.models import (
    ComputerActionPlan,
    ComputerActionRequest,
    ComputerControlCheckpoint,
    ComputerControlMode,
    ComputerControlPermissionSet,
    ComputerControlSession,
    ComputerControlTrace,
    ComputerTask,
)
from loopos.computer_control.policy_adapter import ComputerControlPolicy
from loopos.computer_control.risk import classify_action
from loopos.lail import encode_signal


class ComputerController:
    """Plan, observe, and optionally execute a bounded computer task."""

    def __init__(
        self,
        backend: ComputerBackend | None = None,
        *,
        policy: ComputerControlPolicy | None = None,
    ) -> None:
        self.backend = backend or FakeComputerBackend()
        self.policy = policy or ComputerControlPolicy()
        self.checkpoints: list[ComputerControlCheckpoint] = []
        self.lail_signals: list[dict[str, object]] = []

    def run_task(
        self,
        task: ComputerTask,
        *,
        mode: ComputerControlMode = "dry_run",
        permissions: ComputerControlPermissionSet | None = None,
    ) -> ComputerControlTrace:
        perms = permissions or ComputerControlPermissionSet()
        session = ComputerControlSession(
            run_id=task.run_id,
            mode=mode,
            backend=self.backend.backend_id,
            permissions=perms,
        )
        trace = ComputerControlTrace(
            session_id=session.session_id,
            run_id=task.run_id,
            mode=mode,
            backend=session.backend,
        )
        observation = self.backend.observe(session)
        trace.observations.append(observation)
        self.checkpoints.append(
            ComputerControlCheckpoint(
                session_id=session.session_id,
                run_id=task.run_id,
                iteration_id=task.iteration_id,
                observation_id=observation.observation_id,
            )
        )
        self.lail_signals.append(
            encode_signal(
                kind="computer_observed",
                run_id=task.run_id,
                iteration_index=int(task.iteration_id) if task.iteration_id.isdigit() else 0,
                trace_id=trace.trace_id,
                payload={"observation_id": observation.observation_id, "backend": session.backend},
            ).model_dump(mode="json")
        )
        action = ComputerActionRequest(
            session_id=session.session_id,
            run_id=task.run_id,
            iteration_id=task.iteration_id,
            trace_id=trace.trace_id,
            action_type="verify",
            target_description=task.description,
            expected_result=task.expected_result,
            risk_level=classify_action(task.description),
            requires_approval=False,
        )
        plan = ComputerActionPlan(
            task_id=task.task_id,
            actions=[action],
            rationale="minimal observable verification plan",
        )
        trace.actions_planned.extend(plan.actions)
        decision = self.policy.evaluate(action, mode=mode, permissions=perms)
        if mode in {"observe_only", "dry_run"}:
            result = self.backend.execute(session, action).model_copy(update={"status": "dry_run"})
            trace.actions_executed.append(result)
        elif decision.allowed:
            result = self.backend.execute(session, action)
            trace.actions_executed.append(result)
        else:
            trace.actions_blocked.append(action)
            if decision.requires_approval:
                trace.approvals.append(build_approval(action, decision.risk_level))
        for result in trace.actions_executed:
            self.checkpoints.append(
                ComputerControlCheckpoint(
                    session_id=session.session_id,
                    run_id=task.run_id,
                    iteration_id=task.iteration_id,
                    action_id=result.action_id,
                    observation_id=(
                        result.observed_after.observation_id if result.observed_after else None
                    ),
                    status=result.status,
                )
            )
            self.lail_signals.append(
                encode_signal(
                    kind="computer_action_executed",
                    run_id=task.run_id,
                    iteration_index=int(task.iteration_id) if task.iteration_id.isdigit() else 0,
                    trace_id=trace.trace_id,
                    payload={"action_id": result.action_id, "status": result.status},
                ).model_dump(mode="json")
            )
        trace.completed_at = datetime.now(timezone.utc).isoformat()
        return trace


def backend_from_id(backend_id: str) -> ComputerBackend:
    if backend_id == "browser":
        return BrowserComputerBackend()
    if backend_id in {"local", "local_optional"}:
        return LocalOptionalComputerBackend()
    return FakeComputerBackend()


__all__ = ["ComputerController", "backend_from_id"]
