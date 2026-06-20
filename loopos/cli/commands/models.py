"""Provider and multi-model CLI commands."""

from __future__ import annotations

import json
import sys

from loopos.model_kernel import MultiModelScheduler, ProviderRegistry


def providers_command(
    action: str = "list",
    value: str | None = None,
    *,
    json_output: bool = False,
) -> int:
    registry = ProviderRegistry()
    if action == "list":
        rows = [profile.model_dump(mode="json") for profile in registry.list()]
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if action == "route":
        capabilities = [item.strip() for item in (value or "text").split(",") if item.strip()]
        try:
            profile = registry.route(capabilities)
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(profile.model_dump_json(indent=2))
        return 0
    if action == "assign":
        role = value or "primary_reasoner"
        try:
            assignment = MultiModelScheduler(registry).assign(role)  # type: ignore[arg-type]
        except (KeyError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if json_output:
            print(assignment.model_dump_json(indent=2))
        else:
            print(f"{assignment.role}: {assignment.provider_id} ({assignment.reason_code})")
        return 0
    print(f"Unknown providers action: {action}", file=sys.stderr)
    return 1


def models_command(
    action: str = "route",
    *,
    task: str = "general",
    input_kind: str | None = None,
    secret: bool = False,
) -> int:
    if action != "route":
        print(f"Unknown models action: {action}", file=sys.stderr)
        return 1
    try:
        assignments = MultiModelScheduler().route_task(
            task=task,
            input_kind=input_kind,
            secret=secret,
        )
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        json.dumps(
            [item.model_dump(mode="json") for item in assignments],
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0
