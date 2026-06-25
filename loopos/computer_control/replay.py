"""Replay computer-control traces without re-executing actions."""

from __future__ import annotations

from loopos.computer_control.models import ComputerControlTrace, ComputerReplayResult


class ComputerReplay:
    """Read a trace and emit observations only."""

    def replay(self, trace: ComputerControlTrace | None) -> ComputerReplayResult:
        if trace is None:
            return ComputerReplayResult(trace_id="", status="not_found")
        return ComputerReplayResult(
            trace_id=trace.trace_id,
            actions_replayed=len(trace.actions_executed),
            actions_reexecuted=0,
            observations=trace.observations,
            status="replayed",
        )


__all__ = ["ComputerReplay"]
