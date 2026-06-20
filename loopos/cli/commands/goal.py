"""Goal negotiation CLI commands."""

from __future__ import annotations

import sys
from typing import Any

from loopos.goal import GoalNegotiator


def parse_goal_options(value: str | None) -> list[int]:
    if not value:
        return []
    try:
        options = [int(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as exc:
        raise ValueError("goal options must be comma-separated integers") from exc
    if not options or any(option < 1 or option > 5 for option in options):
        raise ValueError("goal options must be between 1 and 5")
    return list(dict.fromkeys(options))


def goal_command(
    action: str,
    raw_goal: str,
    *,
    option: str | None = None,
    json_output: bool = False,
) -> int:
    negotiator = GoalNegotiator()
    payload: Any
    if action == "analyze":
        payload = negotiator.analyze(raw_goal)
    elif action == "propose":
        payload = negotiator.propose(raw_goal)
    elif action == "finalize":
        try:
            payload = negotiator.finalize(raw_goal, option_ids=parse_goal_options(option))
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    else:
        print(f"Unknown goal action: {action}", file=sys.stderr)
        return 1
    if json_output or action != "propose":
        print(payload.model_dump_json(indent=2))
        return 0
    for item in payload.options:
        print(f"[{item.id}] {item.title}: {item.objective}")
    return 0
