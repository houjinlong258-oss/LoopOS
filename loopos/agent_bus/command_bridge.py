"""Agent Bus — command bridge into the ACI runner.

The :class:`AgentCommandBridge` is a thin adapter that lets the bus
call the existing v0.2 :class:`loopos.aci.runner.CommandRunner`
without importing it in the bus's hot path. The bridge exists to:

* keep the bus loop readable,
* allow tests to swap the bridge for a fake,
* centralise dry-run / mode handling.
"""

from __future__ import annotations

from typing import Protocol

from loopos.aci.models import AgentCommand, AgentCommandResult
from loopos.aci.runner import CommandRunner


class _RunnerLike(Protocol):
    def run(self, command: AgentCommand, *, explain: bool = False) -> AgentCommandResult: ...


class AgentCommandBridge:
    """Default command bridge wrapping the v0.2 :class:`CommandRunner`."""

    def __init__(self, *, runner: _RunnerLike | None = None) -> None:
        self._runner = runner or CommandRunner()

    def dispatch(self, command: AgentCommand, *, explain: bool = True) -> AgentCommandResult:
        # ``CommandRunner.run(explain=True)`` short-circuits; ``explain=False``
        # runs the full pipeline. The bridge takes a flag named
        # ``explain`` to match the v0.2 runner signature; callers that
        # think in terms of dry-run should pass ``explain=True``.
        return self._runner.run(command, explain=explain)

    def runner(self) -> _RunnerLike:
        return self._runner


__all__ = ["AgentCommandBridge"]
