"""Agent Bus — event → AgentCommand translation.

The translator maps the closed set of adapter event kinds onto the
closed set of ACI command kinds. Translation is a **pure function**:
the bus never decides *whether* to dispatch (that is the runner +
Policy OS's job), only *how* to render the request.

The mapping table mirrors the v0.3 spec:

* ``file_patch_proposed``  → ``AgentCommand(kind="file.patch")``
* ``syscall_requested``    → ``AgentCommand(kind="terminal.exec")``
* ``test_requested``       → ``AgentCommand(kind="terminal.exec", metadata.action="test.run")``
* ``model_call_requested`` → ``AgentCommand(kind="provider_select", metadata.action="provider.call")``
* all other kinds          → non-translatable (return [])

Notes
-----

* The v0.2 ACI kind list does not include ``test.run`` or
  ``provider.call``; we use the closest existing kinds and preserve
  the original intent in ``metadata.action`` so downstream consumers
  (including the Workbench UI) can render the correct label.
* The translator does not add ``dry_run`` flags; the bus decides
  whether to run the command in dry-run mode.
"""

from __future__ import annotations

from typing import Any, Callable

from loopos.adapters.events import AgentKernelEvent
from loopos.aci.models import AgentCommand, AgentCommandKind, ProviderHint


# Kind kinds that translate to one ACI command. Other kinds return [].
_TRANSLATABLE: dict[str, AgentCommandKind] = {
    "file_patch_proposed": "file.patch",
    "syscall_requested": "terminal.exec",
}


class AgentEventTranslator:
    """Stateless translator object.

    Tests can construct a custom translator by passing a different
    ``map_`` function. The default uses the table above.
    """

    def __init__(
        self,
        *,
        map_: Callable[[str], AgentCommandKind | None] | None = None,
    ) -> None:
        self._map = map_ or (lambda k: _TRANSLATABLE.get(k))

    def resolve_kind(self, event_kind: str) -> AgentCommandKind | None:
        """Return the ACI kind for a given adapter event kind, or None."""
        return self._map(event_kind)

    def translate(self, event: AgentKernelEvent) -> list[AgentCommand]:
        """Return a (possibly empty) list of ACI commands for an event."""
        kind = self.resolve_kind(event.kind)
        payload = event.payload or {}
        if event.kind == "file_patch_proposed":
            return [
                _build_command(
                    event,
                    kind="file.patch",
                    command=str(payload.get("path", "")),
                    args={
                        "diff": payload.get("diff", ""),
                        "purpose": payload.get("purpose", ""),
                    },
                )
            ]
        if event.kind == "syscall_requested":
            return [
                _build_command(
                    event,
                    kind="terminal.exec",
                    command=str(payload.get("command", "")),
                    args={
                        "cwd": payload.get("cwd", "."),
                        "purpose": payload.get("purpose", ""),
                    },
                )
            ]
        if event.kind == "test_requested":
            return [
                _build_command(
                    event,
                    kind="terminal.exec",
                    command=str(payload.get("command", "python -m pytest -q")),
                    args={
                        "cwd": payload.get("cwd", "."),
                        "purpose": str(payload.get("purpose", "test_requested")),
                    },
                    extra_metadata={"action": "test.run"},
                )
            ]
        if event.kind == "model_call_requested":
            provider_id = str(payload.get("provider_id", "mock"))
            return [
                _build_command(
                    event,
                    kind="provider_select",
                    command=str(payload.get("model_id", "mock")),
                    args={
                        "provider_id": provider_id,
                        "prompt": payload.get("prompt", ""),
                        "purpose": "model_call_requested",
                    },
                    provider_hint=ProviderHint(
                        provider_id=provider_id,
                        allow_fallback=True,
                        notes="model_call_requested",
                    ),
                    extra_metadata={"action": "provider.call"},
                )
            ]
        if kind is not None:
            # Generic translatable kind with no special payload handling.
            return [
                _build_command(
                    event,
                    kind=kind,
                    command=str(payload.get("command", "")),
                    args=dict(payload),
                )
            ]
        return []


def default_translator() -> AgentEventTranslator:
    """Return a fresh :class:`AgentEventTranslator` with the default table."""
    return AgentEventTranslator()


def translate_event(
    translator: AgentEventTranslator,
    event: AgentKernelEvent,
) -> list[AgentCommand]:
    """Free-function wrapper used by the bus."""
    return translator.translate(event)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_command(
    event: AgentKernelEvent,
    *,
    kind: AgentCommandKind,
    command: str,
    args: dict[str, Any],
    extra_metadata: dict[str, Any] | None = None,
    provider_hint: ProviderHint | None = None,
) -> AgentCommand:
    metadata: dict[str, Any] = {
        "source_event_id": event.event_id,
        "source_adapter_id": event.adapter_id,
        "source_event_kind": event.kind,
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    return AgentCommand(
        schema_version="0.2",
        goal_id=event.session_id,
        purpose=f"{event.kind} from {event.adapter_id}",
        kind=kind,
        command=command,
        args=args,
        session_id=event.session_id,
        mode="dry_run",  # the bus always routes through dry-run; runner may override
        dry_run=True,
        trace_required=True,
        metadata=metadata,
        provider_hint=provider_hint,
    )


__all__ = [
    "AgentEventTranslator",
    "default_translator",
    "translate_event",
    "_TRANSLATABLE",
]
