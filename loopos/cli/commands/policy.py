"""Policy OS CLI commands."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from loopos.cli.context import data_paths
from loopos.cli.renderers import render_policy_decision_text
from loopos.core.safety import CommandRiskAnalyzer
from loopos.policy_os.audit import PolicyAuditLog
from loopos.policy_os.engine import PolicyEngine


def policy_command(
    action: str = "list",
    policy_id: str | None = None,
    *,
    scope: str | None = None,
    input_json: str | None = None,
    data_dir: str | Path = ".loopos",
    verbose: bool = False,
    cmd: str | None = None,
    human_output: bool = False,
) -> int:
    engine = PolicyEngine.load_default()
    if action == "list":
        rows = [
            {
                "id": rule.id,
                "scope": rule.scope,
                "priority": rule.priority,
                "severity": rule.severity,
                "actions": [item.type for item in rule.actions],
            }
            for rule in engine.registry.list_rules(scope=scope)
        ]
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if action == "show":
        if not policy_id:
            print("policy show requires POLICY_ID.", file=sys.stderr)
            return 1
        try:
            try:
                payload = engine.registry.get_rule(policy_id).model_dump(mode="json")
            except KeyError:
                payload = engine.registry.get_pack(policy_id).model_dump(mode="json")
        except KeyError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if action == "check":
        if not scope:
            print("policy check requires --scope SCOPE.", file=sys.stderr)
            return 1
        try:
            subject = json.loads(input_json or "{}")
        except json.JSONDecodeError as exc:
            print(f"--input must be JSON: {exc}", file=sys.stderr)
            return 1
        if not isinstance(subject, dict):
            print("--input must be a JSON object.", file=sys.stderr)
            return 1
        decision = engine.evaluate(scope, subject=subject)
        if decision.audit_required:
            PolicyAuditLog(data_paths(data_dir)["policy_audit"]).append(scope, subject, decision)
        payload = decision.model_dump(mode="json")
        if human_output:
            try:
                from loopos.cli_ui import get_console
                from rich.panel import Panel
                con = get_console()
                if con is not None:
                    color = "green" if payload.get("allowed") else "red"
                    con.print(Panel(render_policy_decision_text(payload), title="[bold white]Policy Decision[/bold white]", border_style=color))
                else:
                    print(render_policy_decision_text(payload))
            except Exception:
                print(render_policy_decision_text(payload))
        else:
            print(decision.model_dump_json(indent=2))
        return 0 if decision.allowed else 2
    if action == "audit":
        rows = PolicyAuditLog(data_paths(data_dir)["policy_audit"]).list()
        if not rows:
            print("No policy audit entries.")
            return 0
        print(json.dumps(rows if verbose else rows[-20:], ensure_ascii=False, indent=2))
        return 0
    if action == "explain":
        if not cmd:
            print("policy explain requires --cmd CMD.", file=sys.stderr)
            return 1
        assessment = CommandRiskAnalyzer().analyze(cmd)
        decision = engine.evaluate(
            "terminal.execute",
            subject={
                "cmd": cmd,
                "risk_level": assessment.risk_level,
                "matched_patterns": assessment.matched_patterns,
            },
            tags=["terminal", "explain"],
            risk_level=assessment.risk_level,
        )
        payload = decision.model_dump(mode="json")
        if human_output:
            try:
                from loopos.cli_ui import get_console
                from rich.panel import Panel
                con = get_console()
                if con is not None:
                    color = "green" if payload.get("allowed") else "red"
                    con.print(Panel(render_policy_decision_text(payload, cmd=cmd), title="[bold white]Policy Decision[/bold white]", border_style=color))
                else:
                    print(render_policy_decision_text(payload, cmd=cmd))
            except Exception:
                print(render_policy_decision_text(payload, cmd=cmd))
        else:
            print(decision.model_dump_json(indent=2))
        return 0 if decision.allowed else 2
    print(f"Unknown policy action: {action}", file=sys.stderr)
    return 1
