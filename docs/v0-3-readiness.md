# LoopOS v0.3 — Release Candidate Audit

This document is the **final audit** of LoopOS v0.3 against the
v0.3 master prompt. It is intended for the v0.3 release reviewer.

## 1. Static checks

```text
$ python -m ruff check .
All checks passed!

$ python -m mypy loopos tests   # see "remaining technical debt" below
```

## 2. v0.3 readiness

```text
$ python scripts/v0_3_readiness_check.py --json
{
  "schema_version": "0.3",
  "status": "pass",
  "hard_fail_count": 0,
  ...
 21 checks total, all passing
}
```

## 3. v0.2 regression

```text
$ python scripts/v0_2_readiness_check.py --json
{
  "schema_version": "0.2",
  "status": "pass",
  "hard_fail_count": 0
}
```

## 4. Anti-bloat

```text
$ python scripts/anti_bloat_check.py --json
{
  "hard_fail_count": 0
}
```

## 5. Test suite

```text
$ python -m pytest -m "not slow"
932 passed, 46 deselected, 19 subtests passed in ~90s
```

## 6. v0.3 modules added in this RC

* `loopos/product/` — 7 modules (workbench, views, render, commands,
  panel_layout, plus `__init__`).
* `loopos/agent_bus/` — 5 modules (bus, events, translation,
  command_bridge, session, plus `__init__`).
* `loopos/providers_runtime/` — 4 new modules (base, mock, openai,
  ollama, registry) on top of the existing budget / errors / models /
  usage.
* `loopos/opengod/` — 5 modules (models, decision, evidence, budget,
  verdict, plus `__init__`).
* `loopos/fusion_router/orchestrator.py` — FusionVerdict
  orchestration.
* `loopos/cli/commands/{workbench,adapters,providers_runtime,
  opengod,session,readiness}.py` — 6 new CLI commands.
* `scripts/v0_3_readiness_check.py` — 21-check readiness proof.
* `tests/test_{providers_runtime,agent_bus,opengod,product,
  v0_3_cli,adapters_v0_3,fusion_orchestrator,
  v0_3_readiness_check,v0_3_deep_smoke}.py` — 9 new test files,
  90 new tests.

## 7. v0.3 documentation

* `docs/v0-3-governance-boundary.md` — module allow-list and
  hard rules.
* `docs/v0-3-anti-bloat.md` — file allow-list for v0.3.
* `docs/v0-3-readme.md` — feature → implementation → verification
  map (this release's master index).
* `docs/v0-3-readiness.md` — readiness proof surface (referenced
  from the governance boundary doc).

## 8. CI checklist

| Step | Command | Expected |
| ---- | ------- | -------- |
| ruff | `python -m ruff check .` | "All checks passed!" |
| pytest (not slow) | `python -m pytest -m "not slow"` | 932 passed |
| v0.2 readiness | `python scripts/v0_2_readiness_check.py --json` | status=pass |
| v0.3 readiness | `python scripts/v0_3_readiness_check.py --json` | status=pass |
| anti-bloat | `python scripts/anti_bloat_check.py --json` | hard_fail_count=0 |
| adapters list | `loopos adapters list --json` | list with mock+hermes |
| providers runtime list | `loopos providers runtime list --json` | list with mock+openai+ollama |
| workbench dry-run | `loopos workbench --dry-run --json` | panels.* keys present |
| model call dry-run | `loopos model call PROMPT --dry-run --json` | status=completed |
| live provider blocked | `loopos model call PROMPT --allow-live-provider --json` | status=blocked, required_flags non-empty |
| opengod decide | `loopos opengod g1 --fusion-mode mad_dog --json` | decision.kind=mad_dog |

All steps green. LoopOS v0.3 is ready for RC review.

## 9. Remaining technical debt

The following are tracked but **not blocking** v0.3:

1. `mypy` is not run in CI yet for the v0.3 packages; ruff and the
   932-test suite are the static + dynamic gates. mypy conformance
   is on the v0.3.1 follow-up list.
2. The Agent Bus does not yet persist events to the loopos trace
   store; it logs to its own in-memory log. Persistence is on the
   v0.3.1 list.
3. The OpenGod planner is rule-based. A learned or model-based
   planner is **explicitly out of scope** for v0.3 per the prompt.
4. There is no v0.3-specific TUI; the v0.3 product surface is the
   Workbench CLI (panels + JSON). TUI work is in the v0.4
   roadmap.

End of v0.3 RC audit.

---

## Final release note (v0.3.0 release metadata aligned on main)

The release-metadata commit on `main` bumps:

- `VERSION` from `0.2.0` to `0.3.0`
- `pyproject.toml` `version` from `0.2.0` to `0.3.0`
- `README.md` top banner from v0.2.0 to v0.3.0, plus a new
  "v0.3 Highlights" section near the top
- `CHANGELOG.md` v0.3 heading to `## 0.3.0 (Universal Agent Runtime) - 2026-06-24`
- `docs/v0-3-readiness.md` and `docs/reports/v0-3-rc-decision.md` updated with this
  final release note

No runtime code (`loopos/`, `tests/`) is changed. The v0.1.0 / v0.2.0
tags and `scripts/baselines/v0_1_0_loopos.txt` are not touched. The
v0.3.0 tag is the user's separate decision after the eight validation
gates pass on this `main` HEAD.
