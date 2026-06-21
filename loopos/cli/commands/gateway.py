"""ChatOps gateway CLI commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from loopos.cli.context import data_paths
from loopos.gateway import ChatOpsGateway, GatewayStore
from loopos.gateway.auth import GatewayAuthPolicy
from loopos.gateway.webhook import (
    WebhookApprovalHandler,
    WebhookHealthHandler,
    WebhookMessageHandler,
)


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
    if action == "webhook-flow":
        return _webhook_flow(
            text,
            user_id=user_id,
            run_id=run_id or "demo-run",
            risk=risk,
            data_dir=data_dir,
        )
    if action == "webhook-health":
        handler = WebhookHealthHandler()
        resp = handler.handle()
        print(json.dumps(resp.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0 if resp.status == "ok" else 1
    print(f"Unknown gateway action: {action}", file=sys.stderr)
    return 1


def _webhook_flow(
    text: str,
    *,
    user_id: str,
    run_id: str,
    risk: str,
    data_dir: str | Path,
) -> int:
    """Demonstrate the full webhook message -> run -> approval -> resume flow.

    Steps:
      1. Inbound webhook message -> WebhookMessageHandler -> MessageEvent
      2. MessageEvent -> ChatOpsGateway -> RunSpec (no execution, just the spec)
      3. Approval card created and stored
      4. Webhook approval handler receives decision=approve
      5. Resume decision recorded in the gateway store

    No real HTTP server is started; the handlers are framework-independent
    functions. This demonstrates the contract a real webhook gateway would
    implement.
    """
    # The allowlist is the set of users authorized to drive the demo flow.
    # For the demo we authorize the requested user plus a small set of
    # known demo users; an explicitly unknown user is left out so the
    # unauthorized path is exercised correctly.
    known_demo_users = {"user-1", "user-2", "demo", "operator"}
    allowlist: set[str] = set(known_demo_users)
    if user_id in known_demo_users:
        allowlist.add(user_id)
    elif user_id.startswith("user-") and user_id[5:].isdigit():
        # user-1, user-2, ... are authorized
        allowlist.add(user_id)
    # else: unknown users (e.g. "user-unknown", "anonymous") are not added
    auth = GatewayAuthPolicy(allowlists={"webhook": allowlist})
    paths = data_paths(data_dir)
    store = GatewayStore(
        messages_path=paths["gateway_messages"],
        approvals_path=paths["gateway_approvals"],
    )
    gateway = ChatOpsGateway()

    # Step 1: inbound message
    message_handler = WebhookMessageHandler(auth)
    msg_resp = message_handler.handle(user_id, text)
    if msg_resp.status != "ok":
        print(json.dumps(msg_resp.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 1
    if not message_handler.received:
        print("no message event recorded", file=sys.stderr)
        return 1
    event = message_handler.received[-1]
    store.append_message(event)

    # Step 2: convert to RunSpec
    spec = gateway.to_run_spec(event)

    # Step 3: approval card
    card = gateway.approval_card(
        "webhook",
        run_id=run_id,
        action_summary=text,
        risk=risk,
        reason_codes=["webhook.demo"],
    )
    store.save_approval(card)

    # Step 4: webhook approval handler
    approval_handler = WebhookApprovalHandler(auth)
    approval_resp = approval_handler.handle(
        user_id,
        approval_id=card.id,
        decision="approve",
        run_id=run_id,
    )
    if approval_resp.status != "ok":
        print(json.dumps(approval_resp.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 1

    # Step 5: record decision
    decision = store.decide(card.id, approve=True)

    print(
        json.dumps(
            {
                "step1_message": msg_resp.model_dump(mode="json"),
                "step2_run_spec": spec.model_dump(mode="json"),
                "step3_approval_card": card.model_dump(mode="json"),
                "step4_approval_response": approval_resp.model_dump(mode="json"),
                "step5_resume_decision": decision.model_dump(mode="json"),
                "flow": "message -> run_spec -> approval -> resume",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0
