"""AIL validation and inspection CLI commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import ValidationError

from loopos.ail.codec import instruction_to_ail
from loopos.ail.models import AILInstruction
from loopos.core.isa import Instruction


def ail_command(
    action: str = "validate",
    file: str | None = None,
    *,
    verbose: bool = False,
) -> int:
    if action not in {"validate", "inspect"}:
        print(f"Unknown ail action: {action}", file=sys.stderr)
        return 1
    if not file:
        print(f"ail {action} requires FILE.", file=sys.stderr)
        return 1
    try:
        payload = json.loads(Path(file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not read AIL input: {exc}", file=sys.stderr)
        return 1
    try:
        instruction = AILInstruction.model_validate(payload)
    except ValidationError:
        try:
            instruction = instruction_to_ail(Instruction.model_validate(payload))
        except ValidationError as exc:
            print(f"Invalid AIL instruction: {exc}", file=sys.stderr)
            return 1
    if action == "validate":
        print(f"valid AIL instruction: {instruction.id}")
        if verbose:
            print(instruction.model_dump_json(indent=2))
        return 0
    print(instruction.model_dump_json(indent=2))
    return 0
