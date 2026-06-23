"""Tests for ``loopos.agent_bus``."""

from __future__ import annotations

from typing import Any

from loopos.adapters.events import AgentKernelEvent
from loopos.agent_bus import (
    AgentBus,
    default_translator,
    translate_event,
)
from loopos.aci.models import AgentCommand, AgentCommandResult


class _FakeRunner:
    """Minimal in-test runner compatible with the v0.2 CommandRunner.run signature.

    Records ``(command, kwargs)`` so tests can assert on the call
    signature (e.g. ``explain=`` keyword, not ``dry_run=``).
    """

    def __init__(self) -> None:
        self.calls: list[tuple[Any, Any]] = []

    def run(self, command: Any, *, explain: bool = False) -> AgentCommandResult:
        self.calls.append((command, {"explain": explain}))
        from loopos.policy_os.models import PolicyDecision
        return AgentCommandResult(
            schema_version="0.2",
            command_id=command.id,
            goal_id=command.goal_id,
            status="dry_run" if explain else "completed",
            policy_decision=PolicyDecision(allowed=not explain, action="allow"),
        )


def _event(kind: str, **payload: Any) -> AgentKernelEvent:
    return AgentKernelEvent(
        session_id="s1",
        adapter_id="mock",
        kind=kind,
        payload=payload,
    )


def test_file_patch_proposed_translates_to_file_patch() -> None:
    event = _event("file_patch_proposed", path="x", diff="y", purpose="p")
    cmds = translate_event(default_translator(), event)
    assert len(cmds) == 1
    assert cmds[0].kind == "file.patch"
    assert cmds[0].command == "x"
    assert cmds[0].args["diff"] == "y"


def test_syscall_requested_translates_to_terminal_exec() -> None:
    event = _event("syscall_requested", command="ls -la", purpose="list")
    cmds = translate_event(default_translator(), event)
    assert len(cmds) == 1
    assert cmds[0].kind == "terminal.exec"
    assert cmds[0].command == "ls -la"


def test_test_requested_maps_to_terminal_exec_with_action_metadata() -> None:
    event = _event("test_requested", command="python -m pytest -q")
    cmds = translate_event(default_translator(), event)
    assert len(cmds) == 1
    assert cmds[0].kind == "terminal.exec"
    assert cmds[0].metadata.get("action") == "test.run"


def test_model_call_requested_maps_to_provider_select() -> None:
    event = _event("model_call_requested", provider_id="openai", model_id="gpt-4.1", prompt="hi")
    cmds = translate_event(default_translator(), event)
    assert len(cmds) == 1
    assert cmds[0].kind == "provider_select"
    assert cmds[0].metadata.get("action") == "provider.call"
    # provider_hint must be present per v0.2 ACI rule
    assert cmds[0].provider_hint is not None
    assert cmds[0].provider_hint.provider_id == "openai"


def test_non_translatable_event_returns_empty() -> None:
    for kind in ("thought", "plan_created", "observation", "result", "done", "error", "goal_started"):
        cmds = translate_event(default_translator(), _event(kind))
        assert cmds == [], f"{kind!r} should not translate"


def test_agent_bus_publish_emits_receipt() -> None:
    bus = AgentBus()
    receipt = bus.publish(_event("file_patch_proposed", path="x", diff="y", purpose="p"))
    assert receipt.accepted is True
    assert len(receipt.commands) == 1
    assert receipt.commands[0].kind == "file.patch"
    assert receipt.adapter_id == "mock"


def test_agent_bus_publish_non_translatable_emits_zero_command_receipt() -> None:
    bus = AgentBus()
    receipt = bus.publish(_event("thought", text="thinking"))
    assert receipt.accepted is True
    assert receipt.commands == []
    assert "non_translatable_event" in receipt.reason_codes


def test_agent_bus_attach_session() -> None:
    bus = AgentBus()
    session = bus.attach_session(
        adapter_session_id="a1", adapter_id="mock", ali_session_id="ali_1"
    )
    assert session.adapter_id == "mock"
    assert bus.get_session("a1") is session


def test_agent_bus_translate_pure() -> None:
    bus = AgentBus()
    event = _event("file_patch_proposed", path="x", diff="y", purpose="p")
    a = bus.translate(event)
    b = bus.translate(event)
    assert len(a) == len(b) == 1
    assert a[0].kind == b[0].kind == "file.patch"


def test_agent_bus_event_log_records_published() -> None:
    bus = AgentBus()
    bus.publish(_event("thought", text="x"))
    bus.publish(_event("file_patch_proposed", path="x"))
    log = bus.event_log()
    assert len(log) == 2
    assert log[0].kind == "thought"
    assert log[1].kind == "file_patch_proposed"



def test_agent_bus_dispatch_uses_explain_kwarg() -> None:
    """Regression: ``AgentBus.dispatch`` must call the v0.2 runner with
    the documented ``explain=`` keyword (not ``dry_run=``)."""
    fr = _FakeRunner()
    bus = AgentBus(runner=fr)  # type: ignore[arg-type]
    cmd = AgentCommand(
        goal_id="g1",
        purpose="t",
        kind="noop",
        command="noop",
        dry_run=True,
    )
    bus.dispatch(cmd)
    assert fr.calls, "dispatch did not call the runner"
    _, kwargs = fr.calls[0]
    assert "explain" in kwargs
    assert "dry_run" not in kwargs


def test_agent_bus_dispatch_passes_dry_run_flag() -> None:
    """When the bus is in dry-run mode, dispatch must pass explain=True."""
    fr = _FakeRunner()
    bus = AgentBus(runner=fr, dry_run=True)  # type: ignore[arg-type]
    cmd = AgentCommand(goal_id="g1", purpose="t", kind="noop", command="noop")
    bus.dispatch(cmd)
    _, kwargs = fr.calls[0]
    assert kwargs["explain"] is True


def test_agent_bus_publish_routes_through_dispatch() -> None:
    """``publish`` must actually dispatch the translated command, not
    just store it on the receipt."""
    fr = _FakeRunner()
    bus = AgentBus(runner=fr)  # type: ignore[arg-type]
    receipt = bus.publish(
        _event("file_patch_proposed", path="x", diff="y", purpose="p")
    )
    assert len(fr.calls) == 1
    assert receipt.commands[0].kind == "file.patch"


def test_agent_bus_publish_blocked_on_runner_failure() -> None:
    """A runner ``status="blocked"`` causes the receipt to be marked
    not-accepted and the policy decision to flip to ``block``."""
    class BlockingRunner:
        def run(self, command: Any, *, explain: bool = False) -> AgentCommandResult:
            from loopos.policy_os.models import PolicyDecision
            return AgentCommandResult(
                command_id=command.id,
                goal_id=command.goal_id,
                status="blocked",
                policy_decision=PolicyDecision(allowed=False, action="deny"),
            )

    bus = AgentBus(runner=BlockingRunner())  # type: ignore[arg-type]
    receipt = bus.publish(
        _event("file_patch_proposed", path="x", diff="y", purpose="p")
    )
    assert receipt.accepted is False
    assert receipt.policy_decision == "block"
