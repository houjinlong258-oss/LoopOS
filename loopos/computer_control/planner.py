"""Computer action planner."""

from __future__ import annotations

from loopos.computer_control.models import ComputerActionPlan, ComputerActionRequest, ComputerTask
from loopos.computer_control.risk import classify_action


class ComputerActionPlanner:
    """Create the smallest action plan for an observable task."""

    def plan(self, task: ComputerTask, *, session_id: str, trace_id: str) -> ComputerActionPlan:
        action = ComputerActionRequest(
            session_id=session_id,
            run_id=task.run_id,
            iteration_id=task.iteration_id,
            trace_id=trace_id,
            action_type="verify",
            target_description=task.description,
            expected_result=task.expected_result,
            risk_level=classify_action(task.description),
        )
        return ComputerActionPlan(task_id=task.task_id, actions=[action])


__all__ = ["ComputerActionPlanner"]
