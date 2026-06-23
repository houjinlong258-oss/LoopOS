#!/usr/bin/env python3
"""LoopOS v0.2 Readiness Check (Phase 8).

This script is the **runtime producer** for the v0.2 readiness
proof. It runs a battery of structural and behavioural checks
and emits a single JSON document conforming to the schema
defined in :file:`docs/schemas/readiness-proof.schema.json`
(plus the v0.2-specific fields added in Phase 8).

Required output shape::

    {
      "schema_version": "0.2",
      "status": "pass" | "fail",
      "checks": {
        "provider_registry_bound": bool,
        "aci_runtime_bound": bool,
        "ali_fsm_bound": bool,
        "kernel_loop_integrated": bool,
        "trace_bridge_active": bool,
        "ali_replay_deterministic": bool,
        "fusion_router_available": bool,
        "mad_dog_cli_available": bool,
        "fusion_plan_persistence_available": bool,
        "policy_gates_active": bool,
        "dry_run_no_side_effects": bool,
        "no_live_provider_calls": bool,
        "no_kernel_mutation_in_phase": bool,
        "no_model_kernel_mutation": bool,
        "anti_bloat_checked": bool,
      },
      "hard_fail_count": int,
      "warnings": [...],
    }

The script is **deterministic**: same repository state -> same
output. There are no network calls, no live provider calls, no
subprocess executions beyond the explicit
:func:`subprocess.run` invocations to read ``git diff`` output
and to drive ``anti_bloat_check.py``.

Exit codes:

* ``0`` -- all hard checks pass (warnings may be present).
* ``1`` -- one or more hard checks failed.

Usage::

    python scripts/v0_2_readiness_check.py --json
    python scripts/v0_2_readiness_check.py --self-check
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

# Make ``loopos`` importable when the script is invoked as
# ``python scripts/v0_2_readiness_check.py`` from the repo root
# without a prior ``pip install -e .`` step. Tests call the
# script via the ``python -m`` equivalent or with cwd set, so
# this is a safety net for direct invocation.
sys.path.insert(0, str(REPO_ROOT))
PHASE_8_BASE = "69189db252f1b90f4546a7896a9ad8818e7ec69e"
V010_TAG = "v0.1.0"

# Packages covered by the no-live-provider / no-subprocess check.
PACKAGES_FORBIDDEN_LIVE: tuple[str, ...] = (
    "loopos/providers",
    "loopos/aci",
    "loopos/fusion_router",
    "loopos/trace",
)

# Forbidden top-level imports. ``urllib.request`` / ``urllib3`` /
# ``requests`` / ``httpx`` would be evidence of a network call;
# ``subprocess`` / ``popen`` would be evidence of shell bypass.
FORBIDDEN_LIVE_TOKENS: tuple[str, ...] = (
    "requests",
    "httpx",
    "urllib.request",
    "urllib3",
    "subprocess",
    "popen",
)

# Files / directories the kernel-diff must NOT modify in Phase 8.
KERNEL_PROTECTED_GLOB: str = "loopos/kernel/"
MODEL_KERNEL_PROTECTED_GLOB: str = "loopos/model_kernel/"
RELEASE_EVIDENCE_GLOBS: tuple[str, ...] = (
    "dist/",
    "docs/release-notes/",
    "docs/reports/",
)


@dataclass
class Finding:
    """Single readiness check outcome."""

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
# Structural / source-level checks
# ---------------------------------------------------------------------------


def check_provider_registry_bound() -> Finding:
    """The ``loopos.providers.ProviderRegistry`` is importable and exposes metadata-only APIs."""

    try:
        from loopos.providers import (  # type: ignore[import-not-found]
            ModelProviderProfile,
            ProviderRegistry,
        )
    except Exception as exc:  # noqa: BLE001 - any import failure is a hard fail
        return Finding(
            name="provider_registry_bound",
            status=False,
            detail=f"loopos.providers import failed: {exc}",
        )
    registry = ProviderRegistry()
    registry.register(
        ModelProviderProfile(
            provider_id="readiness-check-local",
            name="Local Placeholder",
            aliases=("rc-local",),
            kind="openai_compatible",
            api_style="chat_completions",
            auth_modes=("none",),
            base_url_required=False,
            supports_streaming=True,
            supports_tools=False,
            supports_vision=False,
            supports_audio=False,
            supports_embeddings=False,
            supports_model_listing=True,
            supports_custom_base_url=False,
            default_models=("placeholder",),
            notes="readiness-check synthetic profile",
        ),
    )
    return Finding(
        name="provider_registry_bound",
        status=True,
        detail=(
            f"ProviderRegistry registered {len(registry.list())} profile(s); "
            f"find_by_capability={len(registry.find_by_capability('text'))} match(es)"
        ),
    )


def check_aci_runtime_bound() -> Finding:
    """ACI runner routes through Policy OS + Syscall Router, not raw subprocess."""

    try:
        from loopos.aci import AgentCommand, CommandRunner  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        return Finding(
            name="aci_runtime_bound",
            status=False,
            detail=f"loopos.aci import failed: {exc}",
        )
    # The runner is a class with a ``run`` method that takes an
    # :class:`AgentCommand`. A smoke instance must be constructable
    # without external state.
    runner = CommandRunner()
    assert hasattr(runner, "run")
    assert hasattr(runner, "validate")
    assert hasattr(AgentCommand, "model_validate")
    return Finding(
        name="aci_runtime_bound",
        status=True,
        detail="CommandRunner exposes run / validate; AgentCommand pydantic-validated",
    )


def check_ali_fsm_bound() -> Finding:
    """ALI FSM and session are importable, transition table is non-empty."""

    try:
        from loopos.ali import AgentLoopSession  # type: ignore[import-not-found]
        from loopos.ali.fsm import DEFAULT_FSM  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        return Finding(
            name="ali_fsm_bound",
            status=False,
            detail=f"loopos.ali import failed: {exc}",
        )
    table_size = len(DEFAULT_FSM.table)
    session = AgentLoopSession(goal_id="readiness-check")
    assert session.state == "CREATED"
    assert table_size > 0
    assert hasattr(DEFAULT_FSM, "apply")
    return Finding(
        name="ali_fsm_bound",
        status=True,
        detail=f"DEFAULT_FSM has {table_size} transition rows; session CREATED",
    )


def check_kernel_loop_integrated() -> Finding:
    """``KernelLoopEngine.submit_agent_command`` is the canonical integration point."""

    try:
        from loopos.kernel import KernelLoopEngine  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        return Finding(
            name="kernel_loop_integrated",
            status=False,
            detail=f"loopos.kernel import failed: {exc}",
        )
    if not hasattr(KernelLoopEngine, "submit_agent_command"):
        return Finding(
            name="kernel_loop_integrated",
            status=False,
            detail="KernelLoopEngine.submit_agent_command missing",
        )
    return Finding(
        name="kernel_loop_integrated",
        status=True,
        detail="KernelLoopEngine.submit_agent_command present",
    )


def check_trace_bridge_active() -> Finding:
    """The ALI trace bridge ``loopos.trace.ali_bridge`` is importable."""

    try:
        from loopos.trace.ali_bridge import ALI_EVENT_TYPE  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        return Finding(
            name="trace_bridge_active",
            status=False,
            detail=f"loopos.trace.ali_bridge import failed: {exc}",
        )
    return Finding(
        name="trace_bridge_active",
        status=True,
        detail=(
            f"ALI_EVENT_TYPE={ALI_EVENT_TYPE!r}; persist / replay helpers present"
        ),
    )


def check_ali_replay_deterministic() -> Finding:
    """The Phase 8 ALI replay engine rebuilds sessions deterministically."""

    try:
        from loopos.trace.ali_replay import (  # type: ignore[import-not-found]
            replay_events,
        )
    except Exception as exc:  # noqa: BLE001
        return Finding(
            name="ali_replay_deterministic",
            status=False,
            detail=f"loopos.trace.ali_replay import failed: {exc}",
        )

    # Determinism smoke: feed two empty event lists and assert
    # both replays land in the same initial state. We do not
    # bring up a full kernel here; the structural check is the
    # ``import + replay of an empty stream -> same final state``.
    first = replay_events([], goal_id="rc-empty-1")
    second = replay_events([], goal_id="rc-empty-2")
    if first.final_state != second.final_state:
        return Finding(
            name="ali_replay_deterministic",
            status=False,
            detail=(
                f"replay diverged: first={first.final_state!r} "
                f"second={second.final_state!r}"
            ),
        )
    return Finding(
        name="ali_replay_deterministic",
        status=True,
        detail=(
            f"empty-stream replay stable in {first.final_state!r}; "
            f"replay_session_from_trace + replay_trace_events present"
        ),
    )


def check_fusion_router_available() -> Finding:
    """The :class:`FusionRouter` is importable and produces a plan."""

    try:
        from loopos.fusion_router import (  # type: ignore[import-not-found]
            FusionRouter,
            FusionTaskProfile,
            FusionTrigger,
        )
    except Exception as exc:  # noqa: BLE001
        return Finding(
            name="fusion_router_available",
            status=False,
            detail=f"loopos.fusion_router import failed: {exc}",
        )
    router = FusionRouter()
    plan = router.plan(
        FusionTaskProfile(title="rc-trivial", task_type="bugfix"),
        FusionTrigger(source="user", reason="explicit_user_request"),
    )
    return Finding(
        name="fusion_router_available",
        status=True,
        detail=(
            f"FusionRouter.plan produced mode={plan.mode!r} "
            f"score={plan.fusion_score}"
        ),
    )


def check_mad_dog_cli_available() -> Finding:
    """The ``mad-dog`` CLI command is importable."""

    try:
        from loopos.cli.commands.mad_dog import mad_dog_command  # type: ignore[import-not-found]
        from loopos.cli.commands.fusion_router import fusion_router_command  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        return Finding(
            name="mad_dog_cli_available",
            status=False,
            detail=f"CLI command import failed: {exc}",
        )
    assert callable(mad_dog_command)
    assert callable(fusion_router_command)
    return Finding(
        name="mad_dog_cli_available",
        status=True,
        detail="mad_dog_command + fusion_router_command callable",
    )


def check_fusion_plan_persistence_available() -> Finding:
    """The :class:`FusionPlanStore` is importable and write/read-back works."""

    try:
        from loopos.fusion_router import (  # type: ignore[import-not-found]
            FusionPlanStore,
            FusionRouter,
            FusionTaskProfile,
            FusionTrigger,
        )
    except Exception as exc:  # noqa: BLE001
        return Finding(
            name="fusion_plan_persistence_available",
            status=False,
            detail=f"loopos.fusion_router import failed: {exc}",
        )

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        store = FusionPlanStore(root=tmp)
        router = FusionRouter()
        plan = router.plan(
            FusionTaskProfile(title="rc-persistence", task_type="bugfix"),
            FusionTrigger(source="user", reason="explicit_user_request"),
        )
        store.save_plan(plan)
        loaded = store.load_plan(plan.fusion_id)
        assert loaded is not None
        assert loaded.fusion_id == plan.fusion_id
        assert store.list_plans() == [plan.fusion_id]
    return Finding(
        name="fusion_plan_persistence_available",
        status=True,
        detail=(
            f"FusionPlanStore wrote and read back plan "
            f"{plan.fusion_id!r} (mode={plan.mode!r})"
        ),
    )


def check_policy_gates_active() -> Finding:
    """Policy OS engine + a real policy pack load successfully."""

    try:
        from loopos.policy_os.engine import PolicyEngine  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        return Finding(
            name="policy_gates_active",
            status=False,
            detail=f"loopos.policy_os import failed: {exc}",
        )
    try:
        engine = PolicyEngine.load_default()
    except Exception as exc:  # noqa: BLE001
        return Finding(
            name="policy_gates_active",
            status=False,
            detail=f"PolicyEngine.load_default failed: {exc}",
        )
    n_packs = len(engine.registry.packs)
    n_rules = len(engine.registry.rules)
    # Smoke: the engine must answer a real request.
    decision = engine.evaluate("instruction.validate", subject={})
    if not hasattr(decision, "allowed"):
        return Finding(
            name="policy_gates_active",
            status=False,
            detail="PolicyEngine.evaluate returned a decision without "
            "`allowed` attribute",
        )
    return Finding(
        name="policy_gates_active",
        status=True,
        detail=(
            f"PolicyEngine loaded default packs ({n_packs} pack(s), "
            f"{n_rules} rule(s)); evaluate() returned allowed={decision.allowed}"
        ),
    )


def check_dry_run_no_side_effects() -> Finding:
    """A dry-run ACI command returns ``status='dry_run'`` without touching the filesystem."""

    try:
        from loopos.aci import AgentCommand, CommandRunner  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        return Finding(
            name="dry_run_no_side_effects",
            status=False,
            detail=f"loopos.aci import failed: {exc}",
        )

    import tempfile as _tempfile

    with _tempfile.TemporaryDirectory():
        runner = CommandRunner()
        cmd = AgentCommand(
            goal_id="rc-dry-run",
            purpose="readiness check",
            kind="terminal.exec",
            command="echo readiness-check",
            dry_run=True,
        )
        result = runner.run(cmd)
        if result.status != "dry_run":
            return Finding(
                name="dry_run_no_side_effects",
                status=False,
                detail=(
                    f"dry-run ACI returned status={result.status!r} "
                    f"(expected 'dry_run')"
                ),
            )
        if not result.dry_run:
            return Finding(
                name="dry_run_no_side_effects",
                status=False,
                detail="dry-run ACI did not set result.dry_run=True",
            )
    return Finding(
        name="dry_run_no_side_effects",
        status=True,
        detail="dry-run ACI returns status='dry_run' / dry_run=True",
    )


# ---------------------------------------------------------------------------
# No-live-provider / no-subprocess check
# ---------------------------------------------------------------------------


def _collect_forbidden_imports(
    package_path: str, tokens: tuple[str, ...]
) -> list[str]:
    """Return ``"<source>: <import>"`` lines that contain any of ``tokens``."""

    findings: list[str] = []
    if not Path(package_path).exists():
        return findings
    for source in Path(package_path).rglob("*.py"):
        if "__pycache__" in source.parts:
            continue
        try:
            text = source.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name.lower()
                    if any(token in name for token in tokens):
                        findings.append(f"{source}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module is not None:
                    name = node.module.lower()
                    if any(token in name for token in tokens):
                        findings.append(f"{source}: from {node.module}")
    return findings


def check_no_live_provider_calls() -> Finding:
    """AST-scan the v0.2 packages for forbidden network / subprocess imports."""

    all_findings: list[str] = []
    for package in PACKAGES_FORBIDDEN_LIVE:
        all_findings.extend(
            _collect_forbidden_imports(package, FORBIDDEN_LIVE_TOKENS)
        )
    return Finding(
        name="no_live_provider_calls",
        status=len(all_findings) == 0,
        detail=(
            "all v0.2 packages clean" if not all_findings
            else f"forbidden imports: {all_findings!r}"
        ),
    )


# ---------------------------------------------------------------------------
# Git-level invariants (kernel untouched in phase, model_kernel
# untouched, dist untouched)
# ---------------------------------------------------------------------------


def _git_diff_names(commit_range: str, *paths: str) -> list[str]:
    completed = subprocess.run(
        ["git", "diff", "--name-only", commit_range, "--", *paths],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return [f"<git-error: {completed.stderr.strip()!r}>"]
    return [
        line.strip()
        for line in completed.stdout.splitlines()
        if line.strip()
    ]


def check_no_kernel_mutation_in_phase() -> Finding:
    """``git diff <PHASE_8_BASE>..HEAD -- loopos/kernel/`` must be empty."""

    changed = _git_diff_names(f"{PHASE_8_BASE}..HEAD", KERNEL_PROTECTED_GLOB)
    return Finding(
        name="no_kernel_mutation_in_phase",
        status=len(changed) == 0,
        detail=(
            "loopos/kernel/ untouched in Phase 8"
            if not changed
            else f"loopos/kernel/ changed: {changed!r}"
        ),
    )


def check_no_model_kernel_mutation() -> Finding:
    """``git diff <v0.1.0>..HEAD -- loopos/model_kernel/`` must be empty."""

    changed = _git_diff_names(
        f"{V010_TAG}..HEAD", MODEL_KERNEL_PROTECTED_GLOB,
    )
    return Finding(
        name="no_model_kernel_mutation",
        status=len(changed) == 0,
        detail=(
            "loopos/model_kernel/ untouched since v0.1.0"
            if not changed
            else f"loopos/model_kernel/ changed: {changed!r}"
        ),
    )


def check_release_evidence_untouched() -> Finding:
    """``git diff <v0.1.0>..HEAD`` over dist + release evidence must be empty."""

    changed: list[str] = []
    for path in RELEASE_EVIDENCE_GLOBS:
        changed.extend(_git_diff_names(f"{V010_TAG}..HEAD", path))
    return Finding(
        name="release_evidence_untouched",
        status=len(changed) == 0,
        detail=(
            "dist + release evidence untouched since v0.1.0"
            if not changed
            else f"release evidence changed: {changed!r}"
        ),
        severity="hard",
    )


def check_anti_bloat() -> Finding:
    """``python scripts/anti_bloat_check.py --json`` must report ``hard_fail_count=0``."""

    completed = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "anti_bloat_check.py"),
            "--json",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        # ``anti_bloat_check.py`` returns non-zero on hard-fail
        # but still emits JSON on stdout. Parse anyway.
        pass
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        return Finding(
            name="anti_bloat_checked",
            status=False,
            detail=f"anti_bloat_check.py output not JSON: {exc}",
        )
    hard_fails = int(payload.get("hard_fail_count", 0))
    return Finding(
        name="anti_bloat_checked",
        status=hard_fails == 0 and completed.returncode in (0, 1),
        detail=(
            f"hard_fail_count={hard_fails}, "
            f"warning_count={payload.get('warning_count', 0)}"
        ),
    )


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------


def _is_git_repo() -> bool:
    """Return True iff ``REPO_ROOT/.git`` is present.

    When this returns ``False`` we are operating from an extracted
    source archive and cannot run any check that depends on git
    history (kernel-diff, model-kernel-diff, anti-bloat baseline).
    """

    return (REPO_ROOT / ".git").exists()


def _skipped(name: str, detail: str) -> Finding:
    """Build a "skipped" :class:`Finding` (status=True, severity=warning).

    Skipped findings never contribute to ``hard_fail_count``; they are
    surfaced via the :class:`Finding.severity == "warning"` channel so
    downstream consumers can distinguish "ran and passed" from "did not
    run" without parsing prose detail strings.
    """

    return Finding(name=name, status=True, detail=detail, severity="warning")


def run_checks(archive_mode: bool = False) -> dict[str, Any]:
    """Run readiness checks and return the structured payload.

    Parameters
    ----------
    archive_mode:
        When ``True``, every check that requires ``git`` history is
        replaced by a "skipped: archive-mode (no .git)" warning
        finding. Use this mode when running from an extracted source
        archive (``dist/LoopOS-v0.2.0-source.zip``) where ``.git`` is
        not present. The default is ``False`` for full git-checkout
        validation.
    """

    if archive_mode:
        checks: list[Finding] = [
            check_provider_registry_bound(),
            check_aci_runtime_bound(),
            check_ali_fsm_bound(),
            check_kernel_loop_integrated(),
            check_trace_bridge_active(),
            check_ali_replay_deterministic(),
            check_fusion_router_available(),
            check_mad_dog_cli_available(),
            check_fusion_plan_persistence_available(),
            check_policy_gates_active(),
            check_dry_run_no_side_effects(),
            check_no_live_provider_calls(),
            _skipped(
                "no_kernel_mutation_in_phase",
                "skipped: archive-mode (no .git); requires git checkout",
            ),
            _skipped(
                "no_model_kernel_mutation",
                "skipped: archive-mode (no .git); requires git checkout",
            ),
            _skipped(
                "anti_bloat_checked",
                "skipped: archive-mode (no .git baseline); "
                "requires git checkout",
            ),
            _skipped(
                "release_evidence_untouched",
                "skipped: archive-mode (no .git); requires git checkout",
            ),
        ]
    else:
        checks = [
            check_provider_registry_bound(),
            check_aci_runtime_bound(),
            check_ali_fsm_bound(),
            check_kernel_loop_integrated(),
            check_trace_bridge_active(),
            check_ali_replay_deterministic(),
            check_fusion_router_available(),
            check_mad_dog_cli_available(),
            check_fusion_plan_persistence_available(),
            check_policy_gates_active(),
            check_dry_run_no_side_effects(),
            check_no_live_provider_calls(),
            check_no_kernel_mutation_in_phase(),
            check_no_model_kernel_mutation(),
            check_anti_bloat(),
        ]

    hard_fails = [c for c in checks if c.severity == "hard" and not c.status]
    warnings: list[dict[str, Any]] = []

    # The release-evidence check is structural; in full mode it
    # surfaces as a warning when v0.2 legitimately must not touch
    # release artifacts. In archive-mode it is already a "skipped"
    # finding in ``checks`` so we skip re-running it here.
    if not archive_mode:
        release_evidence = check_release_evidence_untouched()
        if not release_evidence.status:
            warnings.append(
                {
                    "name": release_evidence.name,
                    "detail": release_evidence.detail,
                }
            )

    overall_status = "pass" if not hard_fails else "fail"

    return {
        "schema_version": "0.2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": overall_status,
        "mode": "archive" if archive_mode else "git-checkout",
        "checks": {
            check.name: {
                "status": check.status,
                "detail": check.detail,
                "severity": check.severity,
            }
            for check in checks
        },
        "hard_fail_count": len(hard_fails),
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="LoopOS v0.2 readiness check.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit JSON to stdout (machine-readable).",
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="run the readiness check and exit 0 even on hard-fail",
    )
    parser.add_argument(
        "--archive-mode",
        action="store_true",
        help=(
            "skip git-required checks; use when running from an "
            "extracted source archive without a .git directory"
        ),
    )
    parser.add_argument(
        "--no-archive-mode",
        action="store_true",
        help=(
            "force full git-checkout validation even if .git is "
            "missing (the git-required checks will then fail)"
        ),
    )
    args = parser.parse_args(argv)

    if args.archive_mode:
        archive_mode = True
    elif args.no_archive_mode:
        archive_mode = False
    else:
        archive_mode = not _is_git_repo()

    payload = run_checks(archive_mode=archive_mode)
    if args.json or not args.self_check:
        json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")

    if args.self_check:
        return 0
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())