"""ChatOps gateway CLI commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from loopos.cli.context import data_paths
from loopos.gateway import ChatOpsGateway, GatewayStore


def gateway_command(
    action: str = "simulate",
    channel: str = "telegram",
    text: str = "hello",
    *,
    user_id: str = "user",
    data_dir: str | Path = ".loopos",
    run_id: str | None = None,
    risk: str = "medium",
    reason_code: str | None = None,
    approve: bool = False,
    deny: bool = False,
) -> int:
    gateway = ChatOpsGateway()
    paths = data_paths(data_dir)
    store = GatewayStore(
        messages_path=paths["gateway_messages"],
        approvals_path=paths["gateway_approvals"],
    )
    if action == "simulate":
        try:
            event = gateway.receive(channel, user_id, text)  # type: ignore[arg-type]
            spec = gateway.to_run_spec(event)
            store.append_message(event)
        except (KeyError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(
            json.dumps(
                {
                    "event": event.model_dump(mode="json"),
                    "run_spec": spec.model_dump(mode="json"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if action == "approval":
        if not run_id:
            print("gateway approval requires --run-id RUN_ID.", file=sys.stderr)
            return 1
        try:
            card = gateway.approval_card(
                channel,  # type: ignore[arg-type]
                run_id=run_id,
                action_summary=text,
                risk=risk,
                reason_codes=[
                    item.strip() for item in (reason_code or "").split(",") if item.strip()
                ],
            )
            store.save_approval(card)
        except (KeyError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(card.model_dump_json(indent=2))
        return 0
    if action == "decide":
        if approve == deny:
            print("gateway decide requires exactly one of --approve or --deny.", file=sys.stderr)
            return 1
        try:
            decision = store.decide(channel, approve=approve)
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(decision.model_dump_json(indent=2))
        return 0
    if action == "approvals":
        cards = store.list_approvals()
        print(
            json.dumps(
                [card.model_dump(mode="json") for card in cards],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    print(f"Unknown gateway action: {action}", file=sys.stderr)
    return 1
