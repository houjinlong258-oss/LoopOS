"""v0.4.0 ``loopos imagine ...`` command.

The ``imagine`` command is the user-facing entry point to the
``ImaginationSandbox``. It must **not** trigger any real side
effects and **must not** invoke hard policy blocks. The output is
a list of ``CreativeCandidate`` records with ``authority_delta="none"``
and no syscall / file-mutation / network fields.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from loopos.loop_engine import (
    ImaginationRequest,
    ImaginationSandbox,
    UserGoal,
)


def imagine_command(
    prompt: str,
    mode: str = "brainstorm",
    max_candidates: int = 3,
    json_output: bool = True,
) -> int:
    """Run the imagination sandbox and emit creative candidates."""
    if mode not in {"brainstorm", "wild", "alternatives", "architecture", "repair", "optimization"}:
        return _emit(
            {"status": "error", "message": f"unknown mode: {mode}"},
            json_output,
        )
    goal = UserGoal(raw_goal=prompt).normalized()
    request = ImaginationRequest(
        goal=goal,
        prompt=prompt,
        mode=mode,  # type: ignore[arg-type]
        max_candidates=max_candidates,
    )
    sandbox = ImaginationSandbox()
    result = sandbox.imagine(request)
    return _emit(result.model_dump(mode="json"), json_output)


def _emit(obj: Any, json_output: bool) -> int:
    if json_output:
        sys.stdout.write(json.dumps(obj, indent=2, default=str))
        sys.stdout.write("\n")
        return 0
    if isinstance(obj, dict):
        for k, v in obj.items():
            sys.stdout.write(f"{k}: {v}\n")
    else:
        sys.stdout.write(str(obj) + "\n")
    return 0


__all__ = ["imagine_command"]
