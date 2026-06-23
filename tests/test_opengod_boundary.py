"""Tests for the v0.3 OpenGod boundary decision.

The hardening pass commits to Option B: OpenGod remains
planning-only on v0.3; the authority bridge is deferred to
v0.4. These tests assert the boundary is held:

1. ``loopos/opengod/__init__.py`` carries an explicit
   "planning-only, NOT wired into AIL execution authority"
   callout so the boundary is visible to anyone importing the
   package.
2. ``loopos/opengod/__init__.py`` does not export any AIL-
   adjacent symbols (``AILInstruction``, ``KernelLoopEngine``,
   etc.) — OpenGod stays a self-contained planning layer.
3. No code outside ``loopos/opengod/`` imports
   ``OpenGodDecision`` for execution purposes (the boundary is
   import-clean).
4. The v0.3 readiness check exposes
   ``check_opengod_planning_only_boundary`` and the check passes.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
OPENGOD_INIT = REPO_ROOT / "loopos" / "opengod" / "__init__.py"


# ---------------------------------------------------------------------------
# Module docstring + exports
# ---------------------------------------------------------------------------


def test_opengod_module_docstring_states_planning_only() -> None:
    """The module docstring must explicitly state that OpenGod is
    planning-only and is NOT wired into the AIL execution
    authority on v0.3.
    """
    text = OPENGOD_INIT.read_text(encoding="utf-8")
    # Pull the module docstring (between the first pair of triple
    # quotes after the future import).
    match = re.search(r'^"""(?P<body>.*?)"""', text, re.DOTALL | re.MULTILINE)
    assert match is not None, "loopos/opengod/__init__.py has no module docstring"
    body = match.group("body")
    assert "planning-only" in body, (
        "module docstring must declare OpenGod is planning-only"
    )
    assert "NOT" in body.upper() and (
        "WIRED" in body.upper() or "WIRE" in body.upper()
    ), "module docstring must declare OpenGod is NOT wired into AIL"
    assert "v0.3" in body, "module docstring must reference v0.3 explicitly"


def test_opengod_does_not_export_ail_symbols() -> None:
    """OpenGod must stay self-contained: no AIL-adjacent symbols
    (KernelLoopEngine, AILInstruction, etc.) in the public API
    surface (``__all__`` + actual import statements). The
    module docstring may *mention* these symbols by name when
    explaining the boundary; that is the whole point of the
    callout.
    """
    text = OPENGOD_INIT.read_text(encoding="utf-8")
    forbidden_substrings = [
        "KernelLoopEngine",
        "AILInstruction",
        "AILPreference",
        "AILContext",
        "AILCodec",
        "AILRuntime",
        "compile_next_ail",
    ]
    # Strip the module docstring before checking: the callout is
    # allowed to mention AIL symbols by name to explain the
    # boundary.
    stripped = re.sub(r'^""".*?"""', "", text, count=1, flags=re.DOTALL)
    for s in forbidden_substrings:
        assert s not in stripped, (
            f"loopos/opengod/__init__.py leaks AIL symbol {s!r}; "
            f"OpenGod must stay planning-only on v0.3"
        )


# ---------------------------------------------------------------------------
# Import-surface guard: nothing in the authority-side runtime
# paths imports OpenGodDecision / OpenGodVerdict for execution
# purposes.
#
# The boundary decision allows read-only display of OpenGod
# verdicts from the Workbench (``loopos/product/``) and the CLI
# (``loopos/cli/commands/opengod.py``). It forbids any
# execution-side authority from consulting OpenGod decisions.
# Authority-side paths: ``loopos/kernel/``, ``loopos/ail/``,
# ``loopos/agents/``, ``loopos/agent_bus/``.
# ---------------------------------------------------------------------------


_AUTHORITY_PATHS = ("loopos/kernel/", "loopos/ail/", "loopos/agents/", "loopos/agent_bus/")


def _is_authority_path(rel: Path) -> bool:
    parts = rel.parts
    return any("/".join(parts[:n]) in _AUTHORITY_PATHS for n in (2,))


# Patterns that look like an execution-side import of OpenGod.
_EXECUTION_IMPORT_PATTERNS = (
    re.compile(r"from\s+loopos\.opengod[^.\w].*OpenGodDecision"),
    re.compile(r"from\s+loopos\.opengod[^.\w].*OpenGodVerdict"),
    re.compile(r"from\s+loopos\.opengod[^.\w].*build_verdict"),
    re.compile(r"from\s+loopos\.opengod[^.\w].*decide"),
)


def test_no_authority_path_imports_opengod_execution_symbols() -> None:
    """Grep authority-side paths for imports of OpenGodDecision,
    OpenGodVerdict, decide, or build_verdict. The Workbench and
    CLI command paths are NOT authority paths; they are allowed to
    surface verdicts to the user.
    """
    offenders: list[tuple[str, int, str]] = []
    for path in REPO_ROOT.rglob("*.py"):
        if path == OPENGOD_INIT:
            continue
        rel = path.relative_to(REPO_ROOT)
        if not _is_authority_path(rel):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for pattern in _EXECUTION_IMPORT_PATTERNS:
                if pattern.search(line):
                    offenders.append((str(rel), lineno, line.strip()))
    assert not offenders, (
        "OpenGodDecision / OpenGodVerdict / decide / build_verdict "
        "must not be imported in authority-side runtime paths on v0.3:\n"
        + "\n".join(f"{p}:{ln}: {line}" for p, ln, line in offenders)
    )


# ---------------------------------------------------------------------------
# Readiness check integration
# ---------------------------------------------------------------------------


def test_readiness_check_exposes_boundary_check() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "v0_3_readiness_check.py"), "--json"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO_ROOT),
    )
    payload = json.loads(result.stdout)
    assert "opengod_planning_only_boundary" in payload["checks"], (
        "v0.3 readiness check must include opengod_planning_only_boundary"
    )
    check = payload["checks"]["opengod_planning_only_boundary"]
    assert check["status"] is True, check["detail"]
    assert payload["status"] == "pass"