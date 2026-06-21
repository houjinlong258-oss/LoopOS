"""Kernel run, trace, and tool renderers."""

from __future__ import annotations

import json
from typing import Any, Iterable

from loopos.core.state import LoopState
from loopos.kernel import RunRecord, TraceEvent, TraceStore
from loopos.syscalls import SyscallSpec

try:  # Optional for local bootstrapping.
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    HAS_RICH = True
except Exception:  # pragma: no cover
    Console = None  # type: ignore[assignment,misc]
    Panel = None  # type: ignore[assignment,misc]
    Table = None  # type: ignore[assignment,misc]
    HAS_RICH = False


def render_state(state: LoopState, *, verbose: bool = False) -> str:
    payload: dict[str, Any] = {
        "run_id": state.run_id,
        "goal": state.goal,
        "status": state.status,
        "step_index": state.step_index,
        "progress_score": state.progress_score,
    }
    if state.last_observation:
        payload["last_observation"] = {
            "summary": state.last_observation.summary,
            "success": state.last_observation.success,
        }
        if verbose:
            payload["last_observation"]["stdout"] = state.last_observation.stdout
            payload["last_observation"]["stderr"] = state.last_observation.stderr
    if state.errors:
        payload["errors"] = state.errors
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_run(run: RunRecord, *, verbose: bool = False) -> str:
    payload: dict[str, Any] = {
        "run_id": run.run_id,
        "goal": run.goal,
        "status": run.status,
        "phase": run.phase,
        "step": run.step,
        "max_steps": run.max_steps,
        "workspace": run.workspace,
        "mode": run.mode,
        "progress_score": run.progress_score,
    }
    if run.pending_approval:
        payload["pending_approval"] = run.pending_approval.model_dump(mode="json")
    if run.errors:
        payload["errors"] = run.errors
    if verbose:
        payload["trace_event_ids"] = run.trace_event_ids
        payload["metadata"] = run.metadata
    return json.dumps(payload, ensure_ascii=False, indent=2)


def print_run(
    run: RunRecord,
    *,
    trace_store: TraceStore | None = None,
    verbose: bool = False,
    show_ail: bool = False,
    show_policy: bool = False,
    json_output: bool = False,
) -> None:
    events = trace_store.list(run.run_id) if trace_store else []
    if json_output:
        payload = json.loads(render_run(run, verbose=verbose))
        if show_ail:
            payload["ail"] = [event.payload for event in events if event.kind == "instruction"]
        if show_policy:
            payload["policy"] = [event.payload for event in events if event.kind == "policy"]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if not HAS_RICH:
        print(render_run(run, verbose=verbose))
        return
    console = Console()
    body = (
        f"Goal: {run.goal}\nStatus: {run.status}\nPhase: {run.phase}\n"
        f"Steps: {run.step}/{run.max_steps}\nWorkspace: {run.workspace}\nMode: {run.mode}"
    )
    console.print(Panel(body, title=f"LoopOS Kernel Run {run.run_id}"))
    for event in events:
        if event.kind == "instruction":
            console.print(f"[{event.step}/{run.max_steps}] {event.payload.get('op', 'UNKNOWN')}")
    if run.pending_approval:
        reasons = ", ".join(run.pending_approval.reason_codes)
        console.print(f"[yellow]Approval required[/yellow]: {reasons}")
    if show_ail:
        console.print_json(data=[e.payload for e in events if e.kind == "instruction"])
    if show_policy:
        console.print_json(data=[e.payload for e in events if e.kind == "policy"])


def print_history(run_id: str, events: list[TraceEvent]) -> None:
    if not HAS_RICH:
        print(json.dumps([e.model_dump(mode="json") for e in events], ensure_ascii=False, indent=2))
        return
    table = Table(title=f"History {run_id}")
    table.add_column("step")
    table.add_column("type")
    table.add_column("payload")
    for event in events:
        kind = event.type or event.kind or "run"
        table.add_row(str(event.step), kind, json.dumps(event.payload, ensure_ascii=False)[:120])
    Console().print(table)


def print_trace(run_id: str, events: list[TraceEvent], *, json_output: bool = False) -> None:
    payload = [event.model_dump(mode="json") for event in events]
    if json_output or not HAS_RICH:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    table = Table(title=f"Trace {run_id}")
    table.add_column("step")
    table.add_column("kind")
    table.add_column("summary")
    for event in events:
        summary = event.payload.get("op") or event.payload.get("summary") or event.type
        table.add_row(str(event.step), str(event.kind), str(summary)[:100])
    Console().print(table)


def print_tools(specs: Iterable[SyscallSpec], *, json_output: bool = False) -> None:
    rows = list(specs)
    payload = [spec.model_dump(mode="json") for spec in rows]
    if json_output or not HAS_RICH:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    table = Table(title="Kernel Syscalls")
    table.add_column("name")
    table.add_column("risk")
    table.add_column("policy scope")
    for spec in rows:
        table.add_row(spec.name, spec.risk, spec.policy_scope)
    Console().print(table)


def render_policy_decision_text(payload: dict[str, Any], *, cmd: str | None = None) -> str:
    """Render a policy decision for human review without changing JSON contracts."""

    allowed = bool(payload.get("allowed"))
    status = "ALLOWED" if allowed else "BLOCKED"
    action = str(payload.get("action", "unknown")).replace("_", " ").upper()
    safety = payload.get("safety_level") or payload.get("risk") or payload.get("severity")
    lines = [
        "LoopOS Policy Explain",
        "=" * 72,
    ]
    if cmd:
        lines.append(f"Command:         {cmd}")
    lines.extend(
        [
            f"Decision:        {status}",
            f"Action:          {action}",
            f"Safety level:    {safety or 'unknown'}",
            f"Risk:            {payload.get('risk', 'unknown')}",
            f"Approval:        {bool(payload.get('requires_approval'))}",
            f"Audit required:  {bool(payload.get('audit_required'))}",
        ]
    )
    reason_codes = payload.get("reason_codes") or []
    if reason_codes:
        lines.append("-" * 72)
        lines.append("Reason codes")
        for code in reason_codes:
            lines.append(f"  - {code}")
    active_rules = payload.get("active_rules") or []
    if active_rules:
        lines.append("-" * 72)
        lines.append("Matched policy rules")
        for rule in active_rules:
            lines.append(f"  - {rule}")
    constraints = payload.get("constraints") or {}
    if constraints:
        lines.append("-" * 72)
        lines.append("Constraints")
        for key, value in sorted(constraints.items()):
            lines.append(f"  - {key}: {value}")
    lines.append("=" * 72)
    return "\n".join(lines)


def render_db_payload_text(payload: object) -> str:
    """Render Data Guard payloads for human inspection."""

    if not isinstance(payload, dict):
        return json.dumps(payload, ensure_ascii=False, indent=2)
    operation = str(payload.get("operation") or payload.get("flow") or "data-guard")
    lines = [
        "LoopOS Data Guard",
        "=" * 72,
        f"Operation:       {operation}",
    ]
    detection = payload.get("risk_level")
    if detection:
        lines.extend(
            [
                f"Risk:            {payload.get('risk_level')}",
                f"Backup required: {payload.get('requires_backup')}",
                f"Destructive:     {payload.get('destructive')}",
            ]
        )
    inspection = payload.get("inspection") or payload.get("step1_inspection")
    if isinstance(inspection, dict):
        lines.extend(
            [
                "-" * 72,
                "Inspection",
                f"  Exists:         {inspection.get('exists')}",
                f"  SQLite:         {inspection.get('is_sqlite')}",
                f"  Tables:         {', '.join(inspection.get('tables') or []) or 'none'}",
            ]
        )
    manifest = payload.get("backup_manifest") or payload.get("step2_backup_manifest")
    if isinstance(manifest, dict):
        lines.extend(
            [
                "-" * 72,
                "Backup",
                f"  Backup id:      {manifest.get('backup_id')}",
                f"  Files:          {len(manifest.get('files') or [])}",
            ]
        )
    if "step3_checksum_verified" in payload:
        lines.append(f"Checksum:        {payload.get('step3_checksum_verified')}")
    if "shadow_path" in payload or "step4_shadow_path" in payload:
        lines.append(f"Shadow path:     {payload.get('shadow_path') or payload.get('step4_shadow_path')}")
    validation = payload.get("validation") or payload.get("step5_validation")
    if isinstance(validation, dict):
        lines.extend(
            [
                "-" * 72,
                "Validation",
                f"  Passed:         {validation.get('passed')}",
                f"  Backup id:      {validation.get('backup_id')}",
            ]
        )
    if "reports" in payload and isinstance(payload["reports"], list):
        lines.append(f"Reports:         {len(payload['reports'])}")
    lines.append("=" * 72)
    return "\n".join(lines)


def render_review_artifact_text(payload: dict[str, Any]) -> str:
    """Render a review artifact as a concise handoff summary."""

    lines = [
        "LoopOS Review Artifact",
        "=" * 72,
        f"Run:             {payload.get('run_id')}",
        f"Decision:        {str(payload.get('decision', 'unknown')).replace('_', ' ').upper()}",
        f"Tests:           {len(payload.get('tests_run') or [])}",
        f"Policy checks:   {len(payload.get('policy_checks') or [])}",
        f"Data checks:     {len(payload.get('data_guard_checks') or [])}",
        f"Trace events:    {len(payload.get('trace_event_ids') or [])}",
    ]
    maintainability = payload.get("maintainability_gate")
    if isinstance(maintainability, dict):
        lines.extend(
            [
                "-" * 72,
                "Maintainability gate",
                f"  Blocks merge:   {maintainability.get('blocks_merge')}",
                f"  Human review:   {maintainability.get('requires_human_review')}",
            ]
        )
        for code in maintainability.get("reason_codes") or []:
            lines.append(f"  - {code}")
    required_changes = payload.get("required_changes") or []
    if required_changes:
        lines.append("-" * 72)
        lines.append("Required changes")
        for item in required_changes:
            lines.append(f"  - {item}")
    lines.append("=" * 72)
    return "\n".join(lines)


def render_review_gate_text(payload: dict[str, Any]) -> str:
    """Render the risk-aware merge gate result for humans."""

    allowed = bool(payload.get("allowed_to_merge"))
    lines = [
        "LoopOS Merge Gate",
        "=" * 72,
        f"Status:          {'READY' if allowed else 'BLOCKED'}",
        f"Review artifact: {payload.get('review_artifact_id')}",
        f"Risk:            {payload.get('risk_level', 'unknown')}",
        f"Allowed:         {allowed}",
    ]
    blockers = payload.get("blockers") or []
    if blockers:
        lines.append("-" * 72)
        lines.append("Blockers")
        for blocker in blockers:
            lines.append(f"  - {blocker}")
    warnings = payload.get("warnings") or []
    if warnings:
        lines.append("-" * 72)
        lines.append("Warnings")
        for warning in warnings:
            lines.append(f"  - {warning}")
    lines.append("=" * 72)
    return "\n".join(lines)
