"""Tests for the v0.3 skills module boundary (Option B).

The v0.3-alpha split-audit flagged the seven-line
``loopos/skills/__init__.py`` re-export shim as a discoverability
RC blocker. The P1-2 hardening pass ships Option B: the shim
stays a shim, but it carries a strong docstring that says so,
the v0.4 follow-up plan is documented in
``docs/v0-3-skills-boundary.md``, and the v0.3 readiness check
asserts the callout, the export surface, and the absence of
v0.4 governance symbols.

These tests pin those properties down.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_INIT = REPO_ROOT / "loopos" / "skills" / "__init__.py"


# ---------------------------------------------------------------------------
# Docstring + exports
# ---------------------------------------------------------------------------


def test_skills_module_docstring_states_memory_backed() -> None:
    text = SKILLS_INIT.read_text(encoding="utf-8")
    match = re.search(r'^"""(?P<body>.*?)"""', text, re.DOTALL | re.MULTILINE)
    assert match is not None, "loopos/skills/__init__.py has no module docstring"
    body = match.group("body")
    # The callout must say the canonical implementation lives in
    # ``loopos.memory`` and that full governance is deferred to
    # v0.4.
    assert "memory-backed" in body, (
        "module docstring must declare skills are memory-backed"
    )
    assert "loopos.memory" in body, (
        "module docstring must point at the canonical implementation in loopos.memory"
    )
    assert "v0.4" in body, (
        "module docstring must reference the v0.4 follow-up plan"
    )


def test_skills_does_not_expose_governance_symbols() -> None:
    """On v0.3 the public skills surface is read / extract /
    propose / accept-reject-merge. None of the v0.4 governance
    symbols (lineage, scoring, dispatch hook, versioning) may
    leak into the public API.
    """
    text = SKILLS_INIT.read_text(encoding="utf-8")
    forbidden_substrings = [
        "SkillLineage",
        "SkillScoring",
        "SkillDispatcher",
        "SkillDispatchHook",
        "SkillVersion",
        "skill_lineage",
        "skill_scoring",
        "skill_dispatcher",
        "skill_dispatch_hook",
        "skill_version",
    ]
    for s in forbidden_substrings:
        assert s not in text, (
            f"loopos/skills/__init__.py leaks v0.4 governance "
            f"symbol {s!r}; skills must stay memory-backed on v0.3"
        )


def test_skills_exports_match_v0_3_surface() -> None:
    """The four v0.3 exports must remain stable: Skill,
    SkillStore, SkillProposal, extract_skill_from_events.
    """
    from loopos import skills

    assert set(skills.__all__) == {
        "Skill",
        "SkillProposal",
        "SkillStore",
        "extract_skill_from_events",
    }
    # And the four symbols are importable from the canonical
    # home, too.
    from loopos.memory.skill_proposals import SkillProposal as _SP
    from loopos.memory.skill_store import Skill as _S
    from loopos.memory.skill_store import SkillStore as _SS
    from loopos.memory.skill_store import (
        extract_skill_from_events as _extract,
    )

    assert skills.Skill is _S
    assert skills.SkillStore is _SS
    assert skills.SkillProposal is _SP
    assert skills.extract_skill_from_events is _extract


def test_skills_shim_does_not_contain_implementation() -> None:
    """The shim must not silently grow a real implementation. A
    v0.3 skills package that contains class definitions, IO, or
    network code is a regression. The shim is allowed to
    re-export symbols and document the boundary; nothing else.
    """
    text = SKILLS_INIT.read_text(encoding="utf-8")
    # Strip the module docstring + the import statements + the
    # __all__ list. The remaining code should be empty (or close
    # to it).
    stripped = re.sub(r'^""".*?"""', "", text, count=1, flags=re.DOTALL)
    stripped = re.sub(r"^from\s+__future__\s+import.*$", "", stripped, flags=re.MULTILINE)
    stripped = re.sub(r"^from\s+loopos\.memory.*$", "", stripped, flags=re.MULTILINE)
    stripped = re.sub(r"^__all__\s*=.*$", "", stripped, flags=re.MULTILINE)
    # Allow blank lines and comments.
    non_blank = [
        line
        for line in stripped.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert not non_blank, (
        "loopos/skills/__init__.py contains implementation code; "
        f"the shim must stay a shim. Found: {non_blank!r}"
    )


# ---------------------------------------------------------------------------
# Readiness check integration
# ---------------------------------------------------------------------------


def test_readiness_check_exposes_skills_boundary_check() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "v0_3_readiness_check.py"), "--json"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO_ROOT),
    )
    payload = json.loads(result.stdout)
    assert "skills_memory_backed_boundary" in payload["checks"], (
        "v0.3 readiness check must include skills_memory_backed_boundary"
    )
    check = payload["checks"]["skills_memory_backed_boundary"]
    assert check["status"] is True, check["detail"]
    assert payload["status"] == "pass"