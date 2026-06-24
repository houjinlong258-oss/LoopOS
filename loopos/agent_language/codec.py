"""Compact LAIL codec."""

from __future__ import annotations

import shlex
from typing import Any

from loopos.agent_language.message import Actionability, AgentMessage
from loopos.agent_language.roles import AgentRole


CORE_PAYLOAD_ORDER = (
    "target",
    "gap",
    "category",
    "status",
    "finding_id",
    "test_status",
    "priority",
    "gain",
)


def message_to_compact(message: AgentMessage) -> str:
    """Encode an ``AgentMessage`` as a compact single-line LAIL signal."""

    parts = [
        message.signal_type,
        _kv("i", message.iteration_id),
        _kv("from", message.from_role.value),
        _kv("to", ",".join(role.value for role in message.recipients())),
        _kv("trace", message.trace_id),
        _kv("msg", message.message_id),
        _kv("conf", _compact_float(message.confidence)),
        _kv("auth", message.authority_delta),
    ]
    if message.quality_delta is not None:
        parts.append(_kv("qd", _compact_float(message.quality_delta)))
    if message.token_cost is not None:
        parts.append(_kv("tokens", message.token_cost))
    if message.communication_distance is not None:
        parts.append(_kv("dist", message.communication_distance))
    if message.actionability != Actionability.NONE:
        parts.append(_kv("action", message.actionability.value))
    if message.evidence:
        parts.append(_kv("evidence", ",".join(message.evidence)))

    payload_keys = [key for key in CORE_PAYLOAD_ORDER if key in message.payload]
    payload_keys.extend(sorted(k for k in message.payload if k not in payload_keys))
    for key in payload_keys:
        value = message.payload[key]
        if isinstance(value, (str, int, float, bool)):
            parts.append(_kv(key, value))
    return " ".join(parts)


def compact_to_message(line: str) -> AgentMessage:
    """Decode a compact LAIL line into an ``AgentMessage``."""

    tokens = shlex.split(line)
    if not tokens:
        raise ValueError("compact LAIL line is empty")
    signal_type = tokens[0]
    fields: dict[str, str] = {}
    payload: dict[str, Any] = {}
    for token in tokens[1:]:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        if key in {"i", "from", "to", "trace", "msg", "conf", "qd", "tokens", "dist", "action", "evidence", "auth"}:
            fields[key] = value
        else:
            payload[key] = _coerce(value)

    to_roles = [
        AgentRole(item)
        for item in fields.get("to", AgentRole.LOOP_CONTROLLER.value).split(",")
        if item
    ]
    to_role: AgentRole | list[AgentRole]
    to_role = to_roles[0] if len(to_roles) == 1 else to_roles
    return AgentMessage(
        message_id=fields.get("msg", "lail_decoded"),
        trace_id=fields.get("trace", "trace_decoded"),
        iteration_id=fields.get("i", "0"),
        from_role=AgentRole(fields.get("from", AgentRole.LOOP_CONTROLLER.value)),
        to_role=to_role,
        signal_type=signal_type,
        payload=payload,
        evidence=[item for item in fields.get("evidence", "").split(",") if item],
        confidence=float(fields.get("conf", "1")),
        quality_delta=float(fields["qd"]) if "qd" in fields else None,
        token_cost=int(fields["tokens"]) if "tokens" in fields else None,
        communication_distance=int(fields["dist"]) if "dist" in fields else None,
        actionability=Actionability(fields.get("action", Actionability.NONE.value)),
        requires_commitment=fields.get("action") == Actionability.COMMITMENT_REQUIRED.value,
        authority_delta="none",
    )


def json_to_compact(data: dict[str, Any]) -> str:
    """Encode either an AgentMessage JSON dict or a compact-signal dict."""

    if "message_id" in data and "signal_type" in data:
        return message_to_compact(AgentMessage.model_validate(data))
    signal_type = str(data.get("signal_type") or data.get("type") or "optimization.signal")
    msg = AgentMessage(
        trace_id=str(data.get("trace_id", "trace_json")),
        iteration_id=str(data.get("iteration") or data.get("iteration_id") or "0"),
        from_role=AgentRole(str(data.get("from") or data.get("from_role") or "loop_controller")),
        to_role=AgentRole(str(data.get("to") or data.get("to_role") or "optimizer")),
        signal_type=signal_type,
        payload={
            key: value
            for key, value in data.items()
            if key
            not in {
                "signal_type",
                "type",
                "trace_id",
                "iteration",
                "iteration_id",
                "from",
                "from_role",
                "to",
                "to_role",
                "evidence",
                "confidence",
                "requires_commitment",
                "authority_delta",
            }
        },
        evidence=list(data.get("evidence", [])),
        confidence=float(data.get("confidence", 1.0)),
        requires_commitment=bool(data.get("requires_commitment", False)),
        authority_delta="none",
    )
    return message_to_compact(msg)


def compact_to_json(line: str) -> dict[str, Any]:
    return compact_to_message(line).model_dump(mode="json")


def _kv(key: str, value: object) -> str:
    return f"{key}={shlex.quote(str(value))}"


def _compact_float(value: float) -> str:
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return text or "0"


def _coerce(value: str) -> Any:
    if value in {"true", "false"}:
        return value == "true"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


__all__ = [
    "compact_to_json",
    "compact_to_message",
    "json_to_compact",
    "message_to_compact",
]
