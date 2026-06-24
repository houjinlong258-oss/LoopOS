"""v0.4.0 closeout: ``loopos lail ...`` commands.

The LAIL CLI is the user-facing surface for the agent-internal
language. In the v0.4.0 closeout it is a thin wrapper around
``loopos.lail``.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from loopos.lail import encode_signal


_LAIL_KINDS = {
    "iteration_started",
    "plan_emitted",
    "build_completed",
    "test_completed",
    "review_completed",
    "repair_planned",
    "optimization_planned",
    "evaluation_signal",
    "convergence_decided",
    "delivery_emitted",
    "checkpoint_saved",
    "memory_packet_compiled",
}


def lail_encode_command(
    kind: str,
    run_id: str,
    iteration_index: int = 0,
    trace_id: str | None = None,
    payload: str | None = None,
    json_output: bool = True,
) -> int:
    """Build a ``LailSignal`` and emit it as JSON.

    The ``payload`` argument is a JSON string. If omitted, the
    payload is empty.
    """
    if kind not in _LAIL_KINDS:
        print(f"unknown kind: {kind}", file=sys.stderr)
        return 2
    payload_dict: dict[str, Any] = {}
    if payload:
        try:
            payload_dict = json.loads(payload)
        except json.JSONDecodeError as exc:
            print(f"invalid payload JSON: {exc}", file=sys.stderr)
            return 2
    sig = encode_signal(
        kind=kind,  # type: ignore[arg-type]
        run_id=run_id,
        iteration_index=iteration_index,
        trace_id=trace_id,
        payload=payload_dict,
    )
    if json_output:
        sys.stdout.write(json.dumps(sig.model_dump(mode="json"), indent=2))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(str(sig.short()) + "\n")
    return 0


def lail_command(
    action: str = "encode",
    value: str | None = None,
    *,
    json_output: bool = True,
) -> int:
    """v0.1-compat ``lail_command(action, value, json_output)`` shim.

    The v0.4.0 closeout exposes ``lail_encode_command`` as the
    primary surface (and ``loopos lail encode --kind ...`` as the
    CLI). This shim preserves the v0.1 ``lail_command("encode", payload)``
    / ``lail_command("decode", compact)`` interface so the older
    test surface keeps working. ``decode`` is informational: it
    re-emits the signal as JSON for round-trip verification.
    """
    if action == "encode":
        # value is the JSON payload; the kind defaults to a
        # representative LAIL kind for v0.1 compatibility.
        return lail_encode_command(
            kind="evaluation_signal",
            run_id="run_lail_cli",
            iteration_index=0,
            trace_id=None,
            payload=value,
            json_output=json_output,
        )
    if action == "decode":
        # ``value`` is the previously-emitted JSON. Re-emit it.
        try:
            obj = json.loads(value) if isinstance(value, str) else value
        except json.JSONDecodeError as exc:
            print(f"invalid compact JSON: {exc}", file=sys.stderr)
            return 2
        if json_output:
            sys.stdout.write(json.dumps(obj, indent=2))
            sys.stdout.write("\n")
        else:
            sys.stdout.write(str(obj) + "\n")
        return 0
    print(f"unknown action: {action}", file=sys.stderr)
    return 2


__all__ = ["lail_command", "lail_encode_command"]

