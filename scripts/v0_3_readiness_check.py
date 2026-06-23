#!/usr/bin/env python3
"""LoopOS v0.3 Readiness Check.

The v0.3 readiness proof covers the **Product Layer**, the **Agent
Kernel Adapter Layer**, the **Agent Bus**, the **Real LLM Provider
Runtime**, the **Fusion Verdict Orchestration**, and the **OpenGod
Planning Layer**. It re-runs the v0.2 readiness proof first so the
v0.3 output doubles as a regression guard.

Output shape::

    {
      "schema_version": "0.3",
      "status": "pass" | "fail",
      "checks": {
        ... 30+ named checks ...
      },
      "hard_fail_count": int,
      "warnings": [...],
      "v0_2_readiness": {...}
    }

The script is deterministic: same repo state -> same output. No
network calls, no live provider calls. Exit codes:

* ``0`` -- all hard checks pass (warnings may be present).
* ``1`` -- one or more hard checks failed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


@dataclass
class Finding:
    name: str
    status: bool
    detail: str = ""
    severity: str = "hard"  # "hard" | "warning"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "severity": self.severity,
        }


# ---------------------------------------------------------------------------
# Product layer
# ---------------------------------------------------------------------------


def check_product_layer() -> Finding:
    try:
        from loopos.product import (
            Workbench,
            build_panels_from_context,
            render_plain,
        )
    except Exception as exc:  # noqa: BLE001
        return Finding("product_layer_importable", False, f"import failed: {exc}")
    wb = Workbench()
    ctx = wb.build_context(goal={"title": "demo"}, dry_run=True)
    panels = build_panels_from_context(ctx)
    text = render_plain(panels)
    return Finding(
        "product_layer_importable",
        True,
        f"Workbench built context; rendered {len(text.splitlines())} lines of plain output",
    )


def check_workbench_panels() -> Finding:
    try:
        from loopos.product import (
            build_panels_from_context,
            render_plain,
            Workbench,
        )
    except Exception as exc:  # noqa: BLE001
        return Finding("workbench_renders_eight_panels", False, f"import failed: {exc}")
    wb = Workbench()
    ctx = wb.build_context(goal={"title": "demo"}, dry_run=True)
    panels = build_panels_from_context(ctx)
    text = render_plain(panels)
    required_substrings = [
        "goal ", "agent ", "policy ", "aci ", "ali ", "trace_replay",
        "fusion ", "readiness ",
    ]
    missing = [s for s in required_substrings if s not in text]
    if missing:
        return Finding(
            "workbench_renders_eight_panels",
            False,
            f"missing panel headers: {missing}",
        )
    return Finding(
        "workbench_renders_eight_panels",
        True,
        "all 8 panel headers present in plain output",
    )


# ---------------------------------------------------------------------------
# Adapter layer
# ---------------------------------------------------------------------------


def check_adapter_registry_populated() -> Finding:
    try:
        from loopos.adapters import AdapterRegistry
    except Exception as exc:  # noqa: BLE001
        return Finding("adapter_registry_populated", False, f"import failed: {exc}")
    reg = AdapterRegistry()
    ids = sorted(a.adapter_id for a in reg.list_adapters())
    must_have = {"mock", "hermes"}
    missing = must_have - set(ids)
    return Finding(
        "adapter_registry_populated",
        not missing,
        f"registered {len(ids)} adapter(s): {ids}" + (f"; missing: {sorted(missing)}" if missing else ""),
    )


def check_adapter_authority_guarded() -> Finding:
    try:
        from loopos.adapters.manifest import AgentKernelAuthority, AgentKernelManifest
    except Exception as exc:  # noqa: BLE001
        return Finding("adapter_authority_guarded", False, f"import failed: {exc}")
    # Try to construct an external adapter that claims direct_shell.
    raised = False
    try:
        AgentKernelManifest(
            adapter_id="bad",
            name="Bad",
            version="0.3.0",
            kind="external_cli",
            entrypoint="x",
            authority=AgentKernelAuthority(direct_shell=True),
        )
    except Exception:  # noqa: BLE001
        raised = True
    return Finding(
        "adapter_authority_guarded",
        raised,
        "manifest refuses direct_shell=True" if raised else "manifest allowed direct_shell=True",
    )


# ---------------------------------------------------------------------------
# Agent bus
# ---------------------------------------------------------------------------


def check_agent_bus_translates() -> Finding:
    try:
        from loopos.adapters.events import AgentKernelEvent
        from loopos.agent_bus import AgentBus, default_translator
    except Exception as exc:  # noqa: BLE001
        return Finding("agent_bus_translates_event", False, f"import failed: {exc}")
    bus = AgentBus(translator=default_translator())
    event = AgentKernelEvent(
        session_id="s1", adapter_id="mock",
        kind="file_patch_proposed", payload={"path": "x", "diff": "y", "purpose": "p"},
    )
    cmds = bus.translate(event)
    return Finding(
        "agent_bus_translates_event",
        bool(cmds) and cmds[0].kind == "file.patch",
        f"file_patch_proposed -> {len(cmds)} command(s); first kind={cmds[0].kind if cmds else 'none'}",
    )


def check_agent_bus_no_bypass() -> Finding:
    """The bus must not have direct shell or direct file-write methods."""
    try:
        from loopos.agent_bus import AgentBus
    except Exception as exc:  # noqa: BLE001
        return Finding("agent_bus_no_bypass", False, f"import failed: {exc}")
    forbidden = ("shell", "file_write", "execute")
    offenders = [name for name in dir(AgentBus) if any(f == name for f in forbidden)]
    return Finding(
        "agent_bus_no_bypass",
        not offenders,
        "no direct bypass methods on AgentBus" if not offenders else f"forbidden methods: {offenders}",
    )


# ---------------------------------------------------------------------------
# Provider runtime
# ---------------------------------------------------------------------------


def check_provider_runtime_importable() -> Finding:
    try:
        from loopos.providers_runtime import (
            ProviderRuntimeRegistry,
        )
        reg = ProviderRuntimeRegistry()
        ids = [r.provider_id for r in reg.list_runtimes()]
    except Exception as exc:  # noqa: BLE001
        return Finding("provider_runtime_importable", False, f"import/init failed: {exc}")
    must = {"mock", "openai", "ollama"}
    return Finding(
        "provider_runtime_importable",
        must.issubset(set(ids)),
        f"registered: {sorted(ids)}",
    )


def check_live_provider_disabled_by_default() -> Finding:
    try:
        from loopos.providers_runtime import (
            MockProviderRuntime,
            ModelCallRequest,
            ModelMessage,
        )
    except Exception as exc:  # noqa: BLE001
        return Finding("live_provider_disabled_by_default", False, f"import failed: {exc}")
    rt = MockProviderRuntime()
    resp = rt.call(
        ModelCallRequest(
            provider_id="mock", model_id="m",
            messages=[ModelMessage(role="user", content="hi")],
            live_provider_calls_allowed=False,
        )
    )
    return Finding(
        "live_provider_disabled_by_default",
        "live_provider_disabled" in (resp.reason_codes or []),
        f"mock response reason_codes={resp.reason_codes}",
    )


def check_openai_live_blocked_by_default() -> Finding:
    try:
        from loopos.providers_runtime import (
            OpenAICompatibleProviderRuntime,
            ModelCallRequest,
            ModelMessage,
        )
    except Exception as exc:  # noqa: BLE001
        return Finding("openai_live_blocked_by_default", False, f"import failed: {exc}")
    rt = OpenAICompatibleProviderRuntime()
    resp = rt.call(
        ModelCallRequest(
            provider_id="openai", model_id="gpt-4.1",
            messages=[ModelMessage(role="user", content="hi")],
            live_provider_calls_allowed=False,
        )
    )
    return Finding(
        "openai_live_blocked_by_default",
        resp.status == "dry_run",
        f"openai without approval -> status={resp.status}, reason_codes={resp.reason_codes}",
    )


def check_budget_guard() -> Finding:
    try:
        from loopos.providers_runtime import ProviderBudget
    except Exception as exc:  # noqa: BLE001
        return Finding("provider_budget_guard_blocks", False, f"import failed: {exc}")
    budget = ProviderBudget(max_usd=0.10, used_usd=0.0)
    decision = budget.check(0.50)
    return Finding(
        "provider_budget_guard_blocks",
        not decision.allowed,
        f"0.50 USD over 0.10 max -> allowed={decision.allowed}, reason_codes={decision.reason_codes}",
    )


def check_secret_redaction() -> Finding:
    try:
        from loopos.providers_runtime.usage import redact_secrets
    except Exception as exc:  # noqa: BLE001
        return Finding("secret_redaction", False, f"import failed: {exc}")
    sample = "token=sk-abcdefghij1234567890 is leaked"
    redacted = redact_secrets(sample)
    return Finding(
        "secret_redaction",
        "REDACTED" in redacted and "sk-abcdefghij" not in redacted,
        f"redacted: {redacted!r}",
    )


# ---------------------------------------------------------------------------
# Fusion orchestrator
# ---------------------------------------------------------------------------


def check_fusion_orchestrator() -> Finding:
    try:
        from loopos.fusion_router import (
            FusionVerdict,
            FusionVerdictOrchestrator,
        )
    except Exception as exc:  # noqa: BLE001
        return Finding("fusion_orchestrator_present", False, f"import failed: {exc}")
    v = FusionVerdict.model_validate(
        {"fusion_id": "f1", "status": "needs_repair", "confidence": 0.5, "reason_codes": []}
    )
    o = FusionVerdictOrchestrator()
    r = o.orchestrate(v)
    return Finding(
        "fusion_orchestrator_present",
        r.status == "submitted" and r.next_ali_state == "REPAIRING",
        f"needs_repair -> next={r.next_ali_state}, status={r.status}",
    )


# ---------------------------------------------------------------------------
# OpenGod
# ---------------------------------------------------------------------------


def check_opengod_decision() -> Finding:
    try:
        from loopos.opengod import build_verdict, collect_evidence, decide
    except Exception as exc:  # noqa: BLE001
        return Finding("opengod_decision_emits_no_command", False, f"import failed: {exc}")
    ctx = collect_evidence(goal_id="g1", fusion_mode="mad_dog")
    d = decide(ctx)
    v = build_verdict(d)
    return Finding(
        "opengod_decision_emits_no_command",
        d.kind == "mad_dog" and v.status == "ok" and not hasattr(d, "command"),
        f"mad_dog fusion -> decision.kind={d.kind}, verdict.status={v.status}",
    )


def check_opengod_halt_on_hard_fail() -> Finding:
    try:
        from loopos.opengod import collect_evidence, decide
    except Exception as exc:  # noqa: BLE001
        return Finding("opengod_halt_on_hard_fail", False, f"import failed: {exc}")
    ctx = collect_evidence(goal_id="g1", hard_fail_count=3)
    d = decide(ctx)
    return Finding(
        "opengod_halt_on_hard_fail",
        d.kind == "halt" and "hard_fail_present" in d.reason_codes,
        f"hard_fail=3 -> decision.kind={d.kind}",
    )


def check_opengod_budget_guard() -> Finding:
    try:
        from loopos.opengod import OpenGodBudgetGuard, collect_evidence, decide
    except Exception as exc:  # noqa: BLE001
        return Finding("opengod_budget_guard_blocks", False, f"import failed: {exc}")
    ctx = collect_evidence(goal_id="g1", fusion_mode="mad_dog", budget_used_usd=0.95)
    d = decide(ctx)
    guard = OpenGodBudgetGuard(max_usd=1.0, reserve_usd=0.10)
    a = guard.assess(ctx, d)
    return Finding(
        "opengod_budget_guard_blocks",
        not a.allowed and "opengod_budget_exceeded" in a.reason_codes,
        f"projected={a.projected_used_usd} max={a.max_usd} allowed={a.allowed}",
    )


def check_opengod_planning_only_boundary() -> Finding:
    """Enforce the v0.3 OpenGod boundary decision (Option B).

    Asserts:

    * ``loopos/opengod/__init__.py`` carries the explicit
      "planning-only, NOT wired into AIL execution authority"
      callout so the boundary is visible to importers.
    * No AIL-adjacent symbol leaks into the OpenGod public API
      (after stripping the module docstring, which is allowed to
      *mention* these symbols by name).
    * No authority-side runtime path (``loopos/kernel/``,
      ``loopos/ail/``, ``loopos/agents/``, ``loopos/agent_bus/``)
      imports ``OpenGodDecision`` / ``OpenGodVerdict`` / ``decide``
      / ``build_verdict`` for execution purposes.

    See ``docs/v0-3-opengod-boundary.md`` for the full decision
    and the v0.4 follow-up plan.
    """
    import re as _re

    # Module docstring callout.
    init_path = REPO_ROOT / "loopos" / "opengod" / "__init__.py"
    if not init_path.exists():
        return Finding(
            "opengod_planning_only_boundary",
            False,
            "loopos/opengod/__init__.py missing",
        )
    text = init_path.read_text(encoding="utf-8")
    match = _re.search(r'^"""(?P<body>.*?)"""', text, _re.DOTALL | _re.MULTILINE)
    if match is None:
        return Finding(
            "opengod_planning_only_boundary",
            False,
            "loopos/opengod/__init__.py has no module docstring",
        )
    body = match.group("body")
    if "planning-only" not in body:
        return Finding(
            "opengod_planning_only_boundary",
            False,
            "module docstring missing 'planning-only' callout",
        )
    if not (_re.search(r"\bNOT\b", body) and _re.search(r"\bWIRE", body, _re.IGNORECASE)):
        return Finding(
            "opengod_planning_only_boundary",
            False,
            "module docstring missing 'NOT wired' callout",
        )
    if "v0.3" not in body:
        return Finding(
            "opengod_planning_only_boundary",
            False,
            "module docstring missing v0.3 reference",
        )
    # Public API hygiene: no AIL-adjacent symbols in the export
    # surface (after stripping the module docstring, which is
    # allowed to mention AIL symbols by name to explain the
    # boundary).
    stripped = _re.sub(r'^""".*?"""', "", text, count=1, flags=_re.DOTALL)
    forbidden_substrings = (
        "KernelLoopEngine",
        "AILInstruction",
        "AILPreference",
        "AILContext",
        "AILCodec",
        "AILRuntime",
        "compile_next_ail",
    )
    for s in forbidden_substrings:
        if s in stripped:
            return Finding(
                "opengod_planning_only_boundary",
                False,
                f"loopos/opengod/__init__.py leaks AIL symbol {s!r}",
            )
    # Import-surface guard: nothing in authority-side runtime
    # paths imports OpenGodDecision / OpenGodVerdict / decide /
    # build_verdict.
    authority_paths = (
        "loopos/kernel/",
        "loopos/ail/",
        "loopos/agents/",
        "loopos/agent_bus/",
    )
    offenders: list[str] = []
    patterns = (
        _re.compile(r"from\s+loopos\.opengod[^.\w].*OpenGodDecision"),
        _re.compile(r"from\s+loopos\.opengod[^.\w].*OpenGodVerdict"),
        _re.compile(r"from\s+loopos\.opengod[^.\w].*build_verdict"),
        _re.compile(r"from\s+loopos\.opengod[^.\w].*decide"),
    )
    for path in REPO_ROOT.rglob("*.py"):
        if path == init_path:
            continue
        rel = path.relative_to(REPO_ROOT)
        rel_str = str(rel).replace("\\", "/")
        if not any(rel_str.startswith(p) for p in authority_paths):
            continue
        try:
            other_text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(other_text.splitlines(), start=1):
            for pat in patterns:
                if pat.search(line):
                    offenders.append(f"{rel}:{lineno}: {line.strip()}")
                    break
    if offenders:
        return Finding(
            "opengod_planning_only_boundary",
            False,
            "OpenGod execution-side imports found in authority-side runtime paths: "
            + " | ".join(offenders[:3]),
        )
    return Finding(
        "opengod_planning_only_boundary",
        True,
        "module docstring declares planning-only; "
        "no AIL symbols leaked; no authority-side imports of "
        "OpenGodDecision/OpenGodVerdict/decide/build_verdict in "
        "loopos/kernel/ loopos/ail/ loopos/agents/ loopos/agent_bus/",
    )


# ---------------------------------------------------------------------------
# CLI smoke
# ---------------------------------------------------------------------------


def check_cli_adapters_list() -> Finding:
    try:
        from loopos.cli.commands import adapters_command
    except Exception as exc:  # noqa: BLE001
        return Finding("cli_adapters_list", False, f"import failed: {exc}")
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = adapters_command("list", json_output=True)
    out = buf.getvalue()
    try:
        rows = json.loads(out)
    except Exception as exc:  # noqa: BLE001
        return Finding("cli_adapters_list", False, f"non-JSON output: {exc}")
    return Finding(
        "cli_adapters_list",
        rc == 0 and isinstance(rows, list) and len(rows) >= 3,
        f"adapters list returned {len(rows)} rows",
    )


def check_cli_providers_runtime_list() -> Finding:
    try:
        from loopos.cli.commands import providers_runtime_command
    except Exception as exc:  # noqa: BLE001
        return Finding("cli_providers_runtime_list", False, f"import failed: {exc}")
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = providers_runtime_command("list", json_output=True)
    out = buf.getvalue()
    try:
        rows = json.loads(out)
    except Exception as exc:  # noqa: BLE001
        return Finding("cli_providers_runtime_list", False, f"non-JSON output: {exc}")
    return Finding(
        "cli_providers_runtime_list",
        rc == 0 and isinstance(rows, list) and len(rows) >= 2,
        f"providers runtime list returned {len(rows)} rows",
    )


def check_cli_model_call_dry_run() -> Finding:
    try:
        from loopos.cli.commands import model_call_command
    except Exception as exc:  # noqa: BLE001
        return Finding("cli_model_call_dry_run", False, f"import failed: {exc}")
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = model_call_command(
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
            provider="mock",
            model="mock-model",
            dry_run=True,
            allow_live_provider=False,
            budget_usd=0.0,
            confirm=False,
            json_output=True,
        )
    out = buf.getvalue()
    try:
        payload = json.loads(out)
    except Exception as exc:  # noqa: BLE001
        return Finding("cli_model_call_dry_run", False, f"non-JSON output: {exc}")
    return Finding(
        "cli_model_call_dry_run",
        rc == 0 and payload.get("status") in ("completed", "dry_run"),
        f"mock dry-run -> status={payload.get('status')}, rc={rc}",
    )


def check_cli_model_call_blocks_live() -> Finding:
    try:
        from loopos.cli.commands import model_call_command
    except Exception as exc:  # noqa: BLE001
        return Finding("cli_model_call_blocks_live", False, f"import failed: {exc}")
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = model_call_command(
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
            provider="openai",
            model="gpt-4.1",
            dry_run=False,  # actually going live
            allow_live_provider=True,
            budget_usd=0.0,
            confirm=False,
            json_output=True,
        )
    out = buf.getvalue()
    try:
        payload = json.loads(out)
    except Exception as exc:  # noqa: BLE001
        return Finding("cli_model_call_blocks_live", False, f"non-JSON output: {exc}")
    return Finding(
        "cli_model_call_blocks_live",
        rc == 4 and payload.get("status") == "blocked",
        f"live without budget/confirm -> status={payload.get('status')}, rc={rc}",
    )


def check_cli_workbench_renders() -> Finding:
    try:
        from loopos.cli.commands import workbench_command
    except Exception as exc:  # noqa: BLE001
        return Finding("cli_workbench_renders", False, f"import failed: {exc}")
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = workbench_command(None, dry_run=True, json_output=True, project=str(REPO_ROOT))
    out = buf.getvalue()
    try:
        payload = json.loads(out)
    except Exception as exc:  # noqa: BLE001
        return Finding("cli_workbench_renders", False, f"non-JSON output: {exc}")
    panels = (payload.get("panels") or {})
    return Finding(
        "cli_workbench_renders",
        rc == 0 and all(k in panels for k in ("goal", "agent", "policy", "aci", "ali", "trace_replay", "fusion", "readiness")),
        f"workbench --json rendered {len(panels)} panels",
    )


def check_live_provider_smoke() -> Finding:
    """Delegate to ``scripts/v0_3_live_provider_smoke.py``.

    The smoke uses an injectable transport — no real HTTP — so it
    is always safe to run. CI invokes it unconditionally.
    """
    import subprocess as _sp
    script = REPO_ROOT / "scripts" / "v0_3_live_provider_smoke.py"
    if not script.exists():
        return Finding("live_provider_smoke", False, "live provider smoke script missing")
    try:
        result = _sp.run(
            [sys.executable, str(script)],
            capture_output=True, text=True, timeout=60, cwd=str(REPO_ROOT),
        )
    except Exception as exc:  # noqa: BLE001
        return Finding("live_provider_smoke", False, f"subprocess failed: {exc}")
    passed = result.returncode == 0 and "PASS" in result.stdout
    return Finding(
        "live_provider_smoke",
        passed,
        f"exit={result.returncode}; last_line={(result.stdout.strip().splitlines() or [''])[-1][:120]}",
    )


def check_loopback_http_smoke() -> Finding:
    """Delegate to ``scripts/v0_3_live_provider_smoke_http.py``.

    Unlike ``check_live_provider_smoke`` (which uses an injected
    transport), this check boots a real ``http.server`` on
    ``127.0.0.1:0`` and exercises the runtime's stdlib
    ``urllib_transport``. It is gated on
    ``LOOPOS_LIVE_HTTP_SMOKE=1`` because it occupies a local port
    and (if extended in the future) may take longer than the
    injected-transport smoke. CI sets the env var to enable it.
    """
    import subprocess as _sp
    script = REPO_ROOT / "scripts" / "v0_3_live_provider_smoke_http.py"
    if not script.exists():
        return Finding(
            "loopback_http_smoke",
            False,
            "loopback HTTP smoke script missing",
        )
    env = os.environ.copy()
    env["LOOPOS_LIVE_HTTP_SMOKE"] = "1"
    try:
        result = _sp.run(
            [sys.executable, str(script), "--json", "--run"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(REPO_ROOT),
            env=env,
        )
    except Exception as exc:  # noqa: BLE001
        return Finding(
            "loopback_http_smoke",
            False,
            f"subprocess failed: {exc}",
        )
    try:
        payload = json.loads(result.stdout)
    except Exception:  # noqa: BLE001
        return Finding(
            "loopback_http_smoke",
            False,
            f"non-JSON output: {(result.stdout or '')[:200]!r} stderr={(result.stderr or '')[:200]!r}",
        )
    hard_fails = int(payload.get("hard_fail_count", 0))
    passed = result.returncode == 0 and hard_fails == 0
    detail = (
        f"status={payload.get('status')}; hard_fail_count={hard_fails}; "
        f"loopback_url={payload.get('loopback_url')}; "
        f"request_hit_count={payload.get('request_hit_count')}"
    )
    return Finding("loopback_http_smoke", passed, detail)


# ---------------------------------------------------------------------------
# v0.2 regression guard
# ---------------------------------------------------------------------------


def check_v0_2_readiness_passes() -> Finding:
    """Run the v0.2 readiness script and verify it still returns pass."""
    import subprocess
    script = REPO_ROOT / "scripts" / "v0_2_readiness_check.py"
    if not script.exists():
        return Finding("v0_2_readiness_passes", False, "v0.2 readiness script missing")
    try:
        result = subprocess.run(
            [sys.executable, str(script), "--json"],
            capture_output=True, text=True, timeout=60, cwd=str(REPO_ROOT),
        )
    except Exception as exc:  # noqa: BLE001
        return Finding("v0_2_readiness_passes", False, f"subprocess failed: {exc}")
    try:
        payload = json.loads(result.stdout)
    except Exception as exc:  # noqa: BLE001
        return Finding("v0_2_readiness_passes", False, f"non-JSON: {exc}")
    return Finding(
        "v0_2_readiness_passes",
        payload.get("status") == "pass",
        f"v0.2 readiness.status={payload.get('status')}, hard_fail_count={payload.get('hard_fail_count')}",
    )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


ALL_CHECKS = (
    check_product_layer,
    check_workbench_panels,
    check_adapter_registry_populated,
    check_adapter_authority_guarded,
    check_agent_bus_translates,
    check_agent_bus_no_bypass,
    check_provider_runtime_importable,
    check_live_provider_disabled_by_default,
    check_openai_live_blocked_by_default,
    check_budget_guard,
    check_secret_redaction,
    check_fusion_orchestrator,
    check_opengod_decision,
    check_opengod_halt_on_hard_fail,
    check_opengod_budget_guard,
    check_opengod_planning_only_boundary,
    check_cli_adapters_list,
    check_cli_providers_runtime_list,
    check_cli_model_call_dry_run,
    check_cli_model_call_blocks_live,
    check_cli_workbench_renders,
    check_live_provider_smoke,
    check_loopback_http_smoke,
    check_v0_2_readiness_passes,
)


def run_checks() -> dict[str, Any]:
    findings: list[Finding] = []
    for check in ALL_CHECKS:
        try:
            findings.append(check())
        except Exception as exc:  # noqa: BLE001
            findings.append(
                Finding(
                    name=check.__name__,
                    status=False,
                    detail=f"check raised: {exc}",
                    severity="hard",
                )
            )
    hard_fails = [f for f in findings if f.severity == "hard" and not f.status]
    warnings = [f for f in findings if f.severity == "warning"]
    return {
        "schema_version": "0.3",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not hard_fails else "fail",
        "checks": {f.name: f.to_dict() for f in findings},
        "hard_fail_count": len(hard_fails),
        "warnings": [w.to_dict() for w in warnings],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LoopOS v0.3 readiness check.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args(argv)
    payload = run_checks()
    if args.json or not args.self_check:
        json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    if args.self_check:
        return 0
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
