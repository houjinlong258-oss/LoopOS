"""Stable (de)serialization helpers for ACI wire payloads.

These helpers exist separately from the Pydantic ``to_json`` /
``from_json`` methods so callers can pin a single wire-format
choice (e.g. ``exclude_none`` vs. ``exclude_unset``) without
sprinkling options across the codebase.

The helpers are deliberately tiny: they are convenience wrappers
around the Pydantic v2 ``model_dump_json`` / ``model_validate``
methods. They never reach into the network or perform I/O.
"""

from __future__ import annotations

import json
from typing import Any

from loopos.aci.models import AgentCommand, AgentCommandResult


def serialize_command_payload(command: AgentCommand) -> str:
    """Serialize an :class:`AgentCommand` to a stable JSON string.

    ``exclude_none=True`` keeps the wire payload small; ``None``
    fields are dropped. Callers that need the full payload should
    use ``command.model_dump_json(exclude_none=False)`` directly.
    """
    return command.model_dump_json(exclude_none=True)


def serialize_result_payload(result: AgentCommandResult) -> str:
    """Serialize an :class:`AgentCommandResult` to a stable JSON string."""
    return result.to_json()


def deserialize_command(raw: str | bytes | dict[str, Any]) -> AgentCommand:
    """Inverse of :func:`serialize_command_payload`."""
    from loopos.aci.models import parse_command

    # ``parse_command`` accepts ``str | dict``; decode ``bytes`` first.
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    return parse_command(raw)


def deserialize_result(raw: str | bytes | dict[str, Any]) -> AgentCommandResult:
    """Inverse of :func:`serialize_result_payload`."""
    return AgentCommandResult.from_json(raw)


def result_to_wire_dict(result: AgentCommandResult) -> dict[str, Any]:
    """Return a JSON-safe dict representation of the result.

    Used by the CLI and by tests that want to assert on the wire
    shape without round-tripping through a string.
    """
    return dict(json.loads(result.to_json()))


def command_to_wire_dict(command: AgentCommand) -> dict[str, Any]:
    """Return a JSON-safe dict representation of the command."""
    return dict(json.loads(command.model_dump_json(exclude_none=True)))
