"""Agent Bus — observable event/command router.

The :class:`AgentBus` is the central object that the Workbench / the
Product Layer talks to. It exposes three operations:

* :meth:`publish` — accept a raw ``AgentKernelEvent`` and route it
  through the translator + bridge, returning a structured receipt.
* :meth:`translate` — pure function: event -> list[AgentCommand].
* :meth:`dispatch` — pure function: command -> AgentCommandResult.
* :meth:`attach_session` — bind an adapter session to an ALI session.

The default :class:`AgentBus` uses a :class:`default_translator` and a
:func:`loopos.aci.runner.CommandRunner` for the bridge, so a fresh
bus works in tests without any setup.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from loopos.adapters.events import AgentKernelEvent
from loopos.aci.models import AgentCommand, AgentCommandResult
from loopos.aci.runner import CommandRunner
from loopos.agent_bus.session import AgentBusSession
from loopos.agent_bus.translation import (
    default_translator,
    translate_event,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AgentBusReceipt(BaseModel):
    """Structured receipt returned by :meth:`AgentBus.publish`."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "0.3"
    event_id: str
    session_id: str
    adapter_id: str
    accepted: bool
    commands: list[AgentCommand] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    policy_decision: str = "allow"  # "allow" | "allow_with_constraints" | "block" | "approval_required"
    trace_id: str = Field(default_factory=lambda: f"trace_{uuid4().hex[:10]}")
    created_at: datetime = Field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class AgentBus:
    """The Agent Bus. Default translator + default ACI runner."""

    def __init__(
        self,
        *,
        runner: CommandRunner | None = None,
        translator: Any | None = None,
        dry_run: bool = True,
    ) -> None:
        self._runner = runner or CommandRunner()
        self._translator = translator or default_translator()
        self._dry_run = dry_run
        self._sessions: dict[str, AgentBusSession] = {}
        self._event_log: list[AgentKernelEvent] = []

    # -- session management -------------------------------------------------

    def attach_session(
        self,
        adapter_session_id: str,
        adapter_id: str,
        ali_session_id: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> AgentBusSession:
        session = AgentBusSession(
            adapter_session_id=adapter_session_id,
            adapter_id=adapter_id,
            ali_session_id=ali_session_id,
            metadata=dict(metadata or {}),
        )
        self._sessions[adapter_session_id] = session
        return session

    def get_session(self, adapter_session_id: str) -> AgentBusSession | None:
        return self._sessions.get(adapter_session_id)

    # -- core operations ----------------------------------------------------

    def translate(self, event: AgentKernelEvent) -> list[AgentCommand]:
        return translate_event(self._translator, event)

    def dispatch(self, command: AgentCommand) -> AgentCommandResult:
        # ``CommandRunner.run`` is keyed on ``explain`` (v0.2). When
        # the bus is configured in dry-run mode we pass ``explain=True``
        # so the runner short-circuits; otherwise we actually run.
        return self._runner.run(command, explain=self._dry_run)

    def publish(self, event: AgentKernelEvent) -> AgentBusReceipt:
        """Translate + dispatch + return a structured receipt.

        The bus records the event in its log, translates the event
        into one or more ``AgentCommand`` objects, and then dispatches
        them through the v0.2 :class:`CommandRunner`. The receipt
        contains the translated commands and the runner's
        :class:`AgentCommandResult` for the **last** command, so
        callers can route on the outcome.
        """
        self._event_log.append(event)
        commands = self.translate(event)
        if not commands:
            return AgentBusReceipt(
                event_id=event.event_id,
                session_id=event.session_id,
                adapter_id=event.adapter_id,
                accepted=True,
                commands=[],
                reason_codes=["non_translatable_event"],
                policy_decision="allow",
            )
        # Dispatch each command. Real ACL lives in Policy OS + the
        # runner; the bus just observes the outcome and surfaces it
        # on the receipt.
        results: list[AgentCommand] = []
        last_result = None
        decision = "allow"
        reasons: list[str] = []
        for cmd in commands:
            results.append(cmd)
            try:
                last_result = self.dispatch(cmd)
            except Exception as exc:  # noqa: BLE001 - never let dispatch crash publish
                decision = "block"
                reasons.append(f"dispatch_error:{type(exc).__name__}")
                last_result = None
                continue
            if str(getattr(last_result, "status", "")) in ("blocked", "failed"):
                decision = "block"
                reasons.append(
                    f"runner_status:{getattr(last_result, 'status', 'unknown')}"
                )
        return AgentBusReceipt(
            event_id=event.event_id,
            session_id=event.session_id,
            adapter_id=event.adapter_id,
            accepted=decision != "block",
            commands=results,
            reason_codes=reasons,
            policy_decision=decision,
        )

    # -- inspection ---------------------------------------------------------

    def event_log(self) -> list[AgentKernelEvent]:
        return list(self._event_log)

    def list_sessions(self) -> list[AgentBusSession]:
        return list(self._sessions.values())


__all__ = ["AgentBus", "AgentBusReceipt"]
