"""Tests for v0.4.0 CLI commands."""

from __future__ import annotations

import io
import json
import sys
from collections.abc import Callable
from typing import Any, cast

from loopos.cli.commands.imagine import imagine_command
from loopos.cli.commands.lail import lail_command
from loopos.cli.commands.loop import (
    loop_deliver_command,
    loop_optimize_command,
    loop_review_command,
    loop_run_command,
    loop_status_command,
)


def _capture_json(callable_: Callable[[], int]) -> dict[str, Any]:
    """Run ``callable_``, capture its stdout, parse JSON."""
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        rc = callable_()
    finally:
        sys.stdout = old
    out = buf.getvalue()
    if not out.strip():
        return {"_rc": rc, "_empty": True}
    return cast(dict[str, Any], json.loads(out))


class TestLoopCli:
    def test_loop_run_outputs_iteration(self) -> None:
        data = _capture_json(lambda: loop_run_command(
            "Build a hello CLI with tests and docs",
            max_iterations=1, dry_run=True, json_output=True,
        ))
        assert "iterations" in data
        assert len(data["iterations"]) == 1
        assert data["iterations"][0]["plan"]["title"]

    def test_loop_run_json_is_valid_json(self) -> None:
        data = _capture_json(lambda: loop_run_command(
            "Build a thing", max_iterations=1, json_output=True,
        ))
        # Must be valid JSON (no Rich control codes, no extra prose).
        assert isinstance(data, dict)
        assert "run_id" in data  # v0.4.0 closeout: cross-process
        assert "iterations" in data

    def test_loop_status_after_run(self) -> None:
        loop_run_command("Build X", max_iterations=1, json_output=True)
        data = _capture_json(lambda: loop_status_command(json_output=True))
        assert "iterations" in data
        assert data["iterations"]

    def test_loop_review_mad_dog(self) -> None:
        loop_run_command("Build X", max_iterations=1, json_output=True)
        data = _capture_json(lambda: loop_review_command(mad_dog=True, json_output=True))
        assert "findings" in data
        assert "mad_dog_findings" in data
        assert isinstance(data["mad_dog_findings"], list)

    def test_loop_optimize_outputs_fusion(self) -> None:
        loop_run_command("Build X", max_iterations=1, json_output=True)
        data = _capture_json(lambda: loop_optimize_command(json_output=True))
        assert "recommended_next_plan" in data
        assert "review_findings" in data
        assert "confidence" in data

    def test_loop_deliver_outputs_delivery_candidate(self) -> None:
        loop_run_command("Build X with tests and docs", max_iterations=2, json_output=True)
        data = _capture_json(lambda: loop_deliver_command(json_output=True))
        assert "summary" in data
        assert "evidence" in data
        assert "quality_score" in data


class TestImagineCli:
    def test_imagine_has_no_side_effects(self) -> None:
        # Imagine must never write a file, never make a syscall.
        from loopos.cli.commands.imagine import imagine_command as cmd
        public = {m for m in dir(cmd) if not m.startswith("_")}
        for forbidden in ("write", "syscall", "execute", "dispatch", "shell"):
            assert forbidden not in public, f"imagine_command exposes {forbidden}"

    def test_imagine_emits_candidates_with_authority_none(self) -> None:
        data = _capture_json(lambda: imagine_command(
            "Design three better ways to implement Fusion Optimizer",
            mode="brainstorm", max_candidates=3, json_output=True,
        ))
        assert "candidates" in data
        assert len(data["candidates"]) == 3
        for c in data["candidates"]:
            assert c["authority_delta"] == "none"
            # No syscall / file / network fields.
            for forbidden in ("syscall", "file_mutation", "network_call", "release_operation"):
                assert forbidden not in c

    def test_imagine_rejects_unknown_mode(self) -> None:
        # The CLI gracefully returns an error dict for unknown mode.
        data = _capture_json(lambda: imagine_command(
            "x", mode="nonsense", max_candidates=1, json_output=True,
        ))
        assert data.get("status") == "error"


class TestLailCli:
    def test_lail_encode_decode_json(self) -> None:
        """lail encode / decode round-trips a JSON payload.

        v0.4.0 closeout: ``lail encode`` returns a full
        ``LailSignal`` (no ``compact`` field). ``decode`` is a
        pass-through that re-emits the signal as JSON.
        """
        payload = {
            "type": "review.finding",
            "iteration": 1,
            "from": "reviewer",
            "to": "optimizer",
            "target": "loop_engine.repair",
            "gap": "missing evidence",
        }
        encoded = _capture_json(
            lambda: lail_command("encode", json.dumps(payload), json_output=True)
        )
        # v0.4.0 LAIL: the encode result is a LailSignal dict.
        assert "kind" in encoded
        assert "payload" in encoded
        assert encoded["payload"]["target"] == "loop_engine.repair"
        # Decode round-trips by re-emitting the encoded dict.
        decoded = _capture_json(
            lambda: lail_command("decode", json.dumps(encoded), json_output=True)
        )
        assert decoded["payload"]["target"] == "loop_engine.repair"
        assert decoded["payload"]["from"] == "reviewer"
