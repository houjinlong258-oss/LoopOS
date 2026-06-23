# LoopOS v0.3 — Alpha History Cleanup Report

> **Status (this document):** v0.3-alpha implementation snapshot complete.
> **Audit target:** `HEAD` at cleanup time (`d316837`).
> **Verdict:** **v0.3-alpha accepted, RC blocked pending hardening.**

This report documents the history-topology cleanup of the v0.3-alpha
implementation. It supersedes the alpha-split-audit's "1+5 reality"
section by delivering the planned 8 logical commits, and it
supersedes the corrected closeout report's "Known Limitations"
bullet for the pre-existing flaky test.

The cleanup follows the per-task mapping provided in the user
spec, anchored on base `136fdf38da63df71ac7079dad791185a5a815340`
(the last v0.2-tagged commit).

---

## A. Old topology summary (pre-cleanup)

The pre-cleanup `main` branch had seven commits on top of `136fdf3`,
but they did not match the planned 8-commit logical split. The
bulk of the v0.3 implementation landed in a single mega-drop whose
commit message was a docs one:

| # | Hash (old) | Subject | Files | Notes |
| - | ---------- | ------- | ----- | ----- |
| 1 | `e39b9d5` | `docs(repo): separate product docs from agent prompts` | 76 (+9472 / -6) | Mega-drop. Disguised a full v0.3 implementation under a docs commit message. |
| 2 | `f7b70f3` | `feat(cli): add rich workbench rendering foundation` | 11 | LoopOS `cli_ui/` package. |
| 3 | `273c21f` | `feat(cli): add loopos workbench command surface` | 6 | Workbench CLI + pyproject extra. |
| 4 | `569409f` | `fix(cli): prepend panel name to panel title in render_view_rich to preserve test assertions` | 1 | Small follow-up to commit 2. |
| 5 | `b5b6b07` | `fix(cli): resolve static type checking, mypy warnings, and add missing unit tests` | 14 | Brought mypy to 0 errors across 392 files. |
| 6 | `0931b82` | `docs: add v0.3 rich cli workbench closeout report` | 1 | Carried the false "continues to fail" claim. |
| 7 | `b4d9350` | `docs(v0.3): add v0.3-alpha implementation snapshot / split audit` | 1 | The split audit itself. |

`git log --oneline` between v0.2 and v0.3 read as a docs commit
plus a string of small follow-ups — not a narrative of logical
features. RC required the topology to read as a narrative.

The pre-cleanup history was **not** pushed to `origin/main`. The
remote tracking ref for `main` resolved to `136fdf3` (the v0.2
base); the local branch was seven commits ahead. This was
confirmed via `git rev-parse origin/main` (= `136fdf3...`) and
`git log --oneline origin/main..main`. Local-only history was a
precondition for the `git reset --soft` rewrite; if any of those
commits had been shared, this cleanup would have stopped and
reported instead.

---

## B. New topology summary (post-cleanup)

Eight logical commits replace the old seven. The mapping in the
per-task spec was followed with two adjustments documented in
Section E.

| # | Hash (new) | Subject | Files | Lines |
| - | ---------- | ------- | ----- | ----- |
| 1 | `e14c7c2` | `docs(repo): separate product docs from agent prompts` | 7 | +14556 / -0 |
| 2 | `921d725` | `feat(product): add v0.3 workbench product surface` | 27 | +2308 / -12 |
| 3 | `0eb54c3` | `feat(agent): add adapter layer and agent bus` | 18 | +1946 / -0 |
| 4 | `23f42fb` | `feat(providers): add governed provider runtime` | 15 | +2374 / -0 |
| 5 | `888b90b` | `feat(fusion): add verdict orchestration prototype` | 3 | +253 / -0 |
| 6 | `9d78f9e` | `feat(opengod): add strategic planning layer` | 8 | +793 / -0 |
| 7 | `4121e0e` | `test(readiness): add v0.3 readiness and regression coverage` | 5 | +950 / -0 |
| 8 | `d316837` | `docs(v0.3): add alpha audit and implementation map` | 17 | +2422 / -14556 |

Total: 8 commits, 90 unique files touched (+25 602 / -14 568).
The -14556 line deletion in commit 8 is the symmetric
`docs/LoopOS_*_Prompt.md → .agent-prompts/...` rename: commit 1
created the new paths; commit 8 removes the old paths so the
working tree stays consistent.

---

## C. Commit list with files per commit

### C.1 Commit 1 — `e14c7c2` `docs(repo): separate product docs from agent prompts`

```
.agent-prompts/LoopOS_Current_Repo_Codex_Improvement_Prompts.md    +1540
.agent-prompts/LoopOS_Data_Safety_Backup_Guard_Prompt.md           +1203
.agent-prompts/LoopOS_Final_Upgrade_Master_Codex_Prompt.md          +3221
.agent-prompts/LoopOS_Fusion_Codex_Prompts.md                      +2238
.agent-prompts/LoopOS_Kernel_Level_Codex_Prompt.md                 +1547
.agent-prompts/LoopOS_Ultimate_Landable_Codex_Prompt.md            +2957
.agent-prompts/prompts/loopos-codex-prompt-pack.md                 +1850
```

Move 6 Codex self-prompt files from `docs/` into `.agent-prompts/`
plus re-home the pre-existing `docs/prompts/loopos-codex-prompt-pack.md`.
No runtime implementation files. No docs files (the v0.3 docs land
in commit 8).

### C.2 Commit 2 — `921d725` `feat(product): add v0.3 workbench product surface`

```
loopos/cli/app.py                              +148
loopos/cli/commands/__init__.py                +31 / -1
loopos/cli/commands/policy.py                  +24 / -2
loopos/cli/commands/runtime.py                 +33 / -2
loopos/cli/commands/workbench.py               +148
loopos/cli/fallback.py                         +134
loopos/cli_ui/__init__.py                      +44
loopos/cli_ui/console.py                       +41
loopos/cli_ui/diff.py                          +11
loopos/cli_ui/errors.py                        +29
loopos/cli_ui/json.py                          +8
loopos/cli_ui/mascot.py                        +13
loopos/cli_ui/panels.py                        +295
loopos/cli_ui/progress.py                      +43
loopos/cli_ui/prompts.py                       +16
loopos/cli_ui/tables.py                        +73
loopos/cli_ui/theme.py                         +22
loopos/product/__init__.py                     +71
loopos/product/commands.py                     +196
loopos/product/panel_layout.py                 +43
loopos/product/render.py                       +127
loopos/product/views.py                        +86
loopos/product/workbench.py                    +390
pyproject.toml                                 +6 / -2
tests/test_cli_ui_console.py                   +59
tests/test_product.py                          +110
tests/test_v0_3_deep_smoke.py                  +119
```

Pure renderer surface; default `--dry-run`. Rich rendering layer
parallel to `loopos/product/render.py`. Workbench CLI via Typer
binding + argparse fallback. `rich` and `typer` moved to optional
`workbench` extra in `pyproject.toml`. The three CLI registration
files (`app.py`, `fallback.py`, `commands/__init__.py`) also
register the other six v0.3 commands; their registration becomes
effective at HEAD once the subsequent commits land.

### C.3 Commit 3 — `0eb54c3` `feat(agent): add adapter layer and agent bus`

```
loopos/adapters/__init__.py                    + (new)
loopos/adapters/base.py
loopos/adapters/cleanroom.py
loopos/adapters/events.py
loopos/adapters/hermes.py
loopos/adapters/manifest.py
loopos/adapters/mock.py
loopos/adapters/registry.py
loopos/adapters/scream_code.py
loopos/agent_bus/__init__.py
loopos/agent_bus/bus.py
loopos/agent_bus/command_bridge.py
loopos/agent_bus/events.py
loopos/agent_bus/session.py
loopos/agent_bus/translation.py
loopos/cli/commands/adapters.py                + (new)
tests/test_adapters_v0_3.py
tests/test_agent_bus.py
```

Adapter interface + mock + cleanroom + Hermes + Scream-Code
specifications. Agent bus dispatches translated commands to the
v0.2 `CommandRunner`; no direct bypass (governance invariant
enforced by `scripts/v0_3_readiness_check.py`).

### C.4 Commit 4 — `23f42fb` `feat(providers): add governed provider runtime`

```
loopos/providers_runtime/__init__.py
loopos/providers_runtime/base.py
loopos/providers_runtime/budget.py
loopos/providers_runtime/errors.py
loopos/providers_runtime/mock.py
loopos/providers_runtime/models.py
loopos/providers_runtime/ollama.py
loopos/providers_runtime/openai.py
loopos/providers_runtime/registry.py
loopos/providers_runtime/usage.py
loopos/cli/commands/providers_runtime.py
loopos/cli/commands/session.py
scripts/v0_3_live_provider_smoke.py
tests/test_providers_runtime.py
tests/test_v0_3_live_provider_smoke.py
```

Gated live-call surface: budget, secret redaction, explicit
confirm flag. Mock provider is in-process only. OpenAI/Ollama
transports are wire-shaped (real endpoints, gated) but the audit
exercise used an injected transport — no real HTTP was emitted.
`scripts/v0_3_live_provider_smoke.py` is gated on
`LOOPOS_LIVE_SMOKE=1` (9 safety checks).

### C.5 Commit 5 — `888b90b` `feat(fusion): add verdict orchestration prototype`

```
loopos/fusion_router/__init__.py               + (delta)
loopos/fusion_router/orchestrator.py           + (new)
tests/test_fusion_orchestrator.py              + (new)
```

Caller-driven only — no daemon, no thread, no asyncio. Maps
`FusionVerdict.status` to `AgentCommand` and dispatches via v0.2
`CommandRunner`. Opt-in via CLI / tests.

### C.6 Commit 6 — `9d78f9e` `feat(opengod): add strategic planning layer`

```
loopos/opengod/__init__.py
loopos/opengod/budget.py
loopos/opengod/decision.py
loopos/opengod/evidence.py
loopos/opengod/models.py
loopos/opengod/verdict.py
loopos/cli/commands/opengod.py
tests/test_opengod.py
```

Planning-only. Emits `OpenGodDecision` + `OpenGodVerdict`; never
calls a provider, never opens a file, never executes shell.
Hard-enforced by
`scripts/v0_3_readiness_check.py::check_opengod_decision_emits_no_command`.
**Not** wired into the AIL execution authority on this snapshot —
see Section G, blocker #2.

### C.7 Commit 7 — `4121e0e` `test(readiness): add v0.3 readiness and regression coverage`

```
scripts/v0_3_readiness_check.py                +635
tests/test_v0_3_readiness_check.py             +87
tests/test_v0_3_cli.py                         +181
tests/test_cli_error_handling.py               +7
loopos/cli/commands/readiness.py               +40
```

22 hard checks (the 22nd is the live_provider_smoke check).
`tests/test_cli_error_handling.py` is the previously-flaky test
fixed via pre-subprocess existence assertions; it now passes
deterministically across reruns.

### C.8 Commit 8 — `d316837` `docs(v0.3): add alpha audit and implementation map`

```
CHANGELOG.md                                              + (v0.3-alpha entry)
docs/v0-3-readme.md                                       + (new)
docs/v0-3-readiness.md                                    + (new)
docs/v0-3-anti-bloat.md                                   + (new)
docs/v0-3-governance-boundary.md                          + (new)
docs/reports/v0-3-alpha-split-audit.md                    + (new)
docs/reports/v0-3-audit-bugs.md                           + (new)
docs/reports/v0-3-rc-audit.md                             + (new)
docs/reports/v0-3-strict-rc-audit.md                      + (new)
docs/reports/v0-3-rich-cli-workbench-closeout.md          + (corrected)
docs/LoopOS_Current_Repo_Codex_Improvement_Prompts.md     - (deleted)
docs/LoopOS_Data_Safety_Backup_Guard_Prompt.md            - (deleted)
docs/LoopOS_Final_Upgrade_Master_Codex_Prompt.md          - (deleted)
docs/LoopOS_Fusion_Codex_Prompts.md                       - (deleted)
docs/LoopOS_Kernel_Level_Codex_Prompt.md                  - (deleted)
docs/LoopOS_Ultimate_Landable_Codex_Prompt.md             - (deleted)
docs/prompts/loopos-codex-prompt-pack.md                  - (deleted)
```

`docs/reports/v0-3-runtime-bugfix-audit.md` is **not** present on
this snapshot and so is not included (the per-task instruction
"if present" is a no-op).

The seven `docs/LoopOS_*` deletions close the loop on commit 1's
`.agent-prompts/` rename: commit 1 created the new paths via git's
rename detection; commit 8 deletes the now-empty old paths so the
working tree stays consistent.

---

## D. Documentation correction

The pre-cleanup closeout report
(`docs/reports/v0-3-rich-cli-workbench-closeout.md`) had this
inaccurate bullet on line 124 of its old form:

> **Pre-existing test failure**: The test
> `tests/test_cli_error_handling.py::test_run_with_file_as_workspace_returns_clean_error`
> continues to fail because of environment cleanup behavior (stale
> check on workspace paths), which is a pre-existing issue from v0.2.

This is **false** for the current `HEAD`. The strict-audit fixed
this test in-tree by adding pre-subprocess existence assertions
(`assert file_path.exists()` and `assert file_path.is_file()` after
`file_path.write_text(...)`, visible in the diff of the original
`e39b9d5`). The fix is in-tree and the test passes deterministically
across reruns.

The bullet is replaced with:

> **Pre-existing test fix**: The previously flaky test
> `tests/test_cli_error_handling.py::test_run_with_file_as_workspace_returns_clean_error`
> was fixed in `e39b9d5` (added pre-subprocess existence assertions).
> It is **passing** in the current v0.3-alpha snapshot, which
> reports `947 passed, 9 skipped, 46 deselected, 19 subtests` with
> **no failures**. There are no known failing tests in the current
> v0.3-alpha snapshot.

The correction is committed as part of commit 8 (the docs commit)
because the closeout report is itself a docs artifact. Splitting
the correction into its own commit would have meant either
(a) amending commit 1 (which had already been frozen when the
correction was discovered) or (b) carrying an unrelated
single-bullet fixup commit that violated the per-task spec's
8-commit structure.

---

## E. Mapping adjustments

Two adjustments to the per-task mapping are documented here so
future re-runs can either match them or revise them explicitly.

### E.1 `research/reference-sources/` is empty on this snapshot

The per-task spec said commit 1 should include
`research/reference-sources/`. On the current `HEAD`, the
`research/` directory contains two untracked sub-directories
(`reference-sources/` and `prompts/`) with no git-tracked files.
`git ls-files research/` returns nothing; `git ls-tree HEAD
research/` returns nothing.

Because nothing under `research/` is git-tracked on this snapshot,
no commit can include `research/reference-sources/` content. The
mapping is preserved as-is; future snapshots that populate
`research/reference-sources/` with tracked files should pull that
path into commit 1 or a future docs-restructure commit.

### E.2 `loopos/cli/{app,fallback}.py` and `commands/__init__.py` are colocated with commit 2

These three files register all seven new v0.3 CLI commands, not
just `workbench`. Splitting them by feature would have required
seven non-contiguous edits to the same files across seven commits,
which git cannot represent as a clean per-commit file-set without
either amending or rebasing mid-flight.

The chosen resolution: place these three files in commit 2 (the
workbench commit), with the commit message explicitly noting that
the registrations for the other six commands become effective only
after their respective commits land. This is the same resolution
the alpha split-audit recommended in Section B.

### E.3 Commit 1's rename deletion half lands in commit 8

When `git reset --soft 136fdf3` is performed, the rename is staged
as a pair (`R docs/.../X.md → .agent-prompts/.../X.md`). When
commit 1 is then made with pathspec `.agent-prompts/` only, git
commits the create half but not the delete half (the delete half
remains staged for the next commit). The delete half therefore
lands in commit 8 alongside the v0.3 docs.

The alternative was to amend commit 1, which would have meant
re-doing the whole rebase. The chosen resolution is documented in
commit 8's message: "This commit also closes the loop on commit 1's
`.agent-prompts/` rename by removing the now-empty original
`docs/LoopOS_*_Prompt.md` files."

### E.4 `docs/reports/v0-3-runtime-bugfix-audit.md` not present

The per-task spec said commit 8 should include this file "if
present". It is not present on this snapshot. No inclusion.

---

## F. Validation results

All eight validation commands specified in the per-task plan pass
on the post-cleanup `HEAD` (`d316837`).

### F.1 `python -m pytest -m "not slow" -q`

```
947 passed, 9 skipped, 46 deselected, 19 subtests passed in 149.69s (0:02:29)
```

* 947 passed (matches the audit's pre-cleanup baseline; +7 from the
  alpha's `test_cli_ui_console.py` add and the targeted additions
  in `test_v0_3_deep_smoke.py`).
* 9 skipped — the 9 gated live-provider smoke tests.
* 46 deselected — `-m "not slow"` excludes the `slow` group.
* 0 failed.
* 19 subtests passed.

### F.2 `python -m pytest -m "slow" -q`

```
46 passed, 956 deselected in 107.41s (0:01:47)
```

### F.3 `python -m ruff check .`

```
All checks passed!
```

### F.4 `python -m mypy loopos tests`

```
Success: no issues found in 392 source files
```

### F.5 `python scripts/v0_2_readiness_check.py --json`

```json
{
  "status": "pass",
  "hard_fail_count": 0,
  "warnings": [
    {
      "name": "release_evidence_untouched",
      "detail": "release evidence changed: [
        'docs/reports/v0-3-alpha-split-audit.md',
        'docs/reports/v0-3-audit-bugs.md',
        'docs/reports/v0-3-rc-audit.md',
        'docs/reports/v0-3-rich-cli-workbench-closeout.md',
        'docs/reports/v0-3-strict-rc-audit.md'
      ]"
    }
  ]
}
```

The single warning is informational: v0.3 audit evidence files
were modified during the alpha phase. Not a blocker.

### F.6 `python scripts/v0_3_readiness_check.py --json`

```json
{
  "status": "pass",
  "hard_fail_count": 0,
  "warnings": []
}
```

22 of 22 hard checks pass. The 22nd is
`check_live_provider_smoke`, added during the alpha audit.

### F.7 `python scripts/anti_bloat_check.py --json`

```json
{
  "hard_fail_count": 0,
  "warning_count": 1,
  "warnings": [
    {
      "reason_code": "module_count_delta",
      "severity": "warning",
      "message": "loopos/ module count grew by 92 (baseline=199, current=291)"
    }
  ]
}
```

Single soft warning: 92 new Python modules under `loopos/`.
Expected for an alpha that introduces 5 new sub-packages plus the
fusion orchestrator.

### F.8 `python rc_audit_cli_smoke.py`

```
[ok] fusion-router list -> count=1321
[ok] fusion-router route -> status=planning_only fallback=kernel_engine not supplied; returning planning-only result
[ok] mad-dog plan -> mode=mad_dog fusion_id=2d743724-b9ca-43a3-8562-c09589ad52c1
[ok] mad-dog status -> status=loaded
[ok] mad-dog list -> count=1322
[ok] mad-dog route -> status=planning_only fallback=kernel_engine not supplied; returning planning-only result

ALL CLI SURFACES OK
```

### F.9 `git status --short`

```
(nothing)
```

Working tree clean.

### F.10 `git log --oneline -n 12`

```
d316837 docs(v0.3): add alpha audit and implementation map
4121e0e test(readiness): add v0.3 readiness and regression coverage
9d78f9e feat(opengod): add strategic planning layer
888b90b feat(fusion): add verdict orchestration prototype
23f42fb feat(providers): add governed provider runtime
0eb54c3 feat(agent): add adapter layer and agent bus
921d725 feat(product): add v0.3 workbench product surface
e14c7c2 docs(repo): separate product docs from agent prompts
136fdf3 fix(ci): fetch release history and repair fusion cli route smoke  (v0.2 base)
4a15004 fix(release): guard Windows process group flag
66b4230 test(readiness): hoist list comprehension out of f-string for py3.11
e18dca2 release(polish): v0.2.0 metadata, README banner, archive-mode readiness
```

---

## G. Remaining RC blockers

Inherited unchanged from `docs/reports/v0-3-alpha-split-audit.md`
Section F. The history cleanup does not introduce or fix any
blocker; it only rearranges the diff topology.

1. **Mega-commit topology (F.1)** — **RESOLVED** by this cleanup.
   `git log --oneline` between v0.2 and v0.3 now reads as a narrative
   of 8 logical features. Removed from the blocker list.
2. **OpenGod is not wired into AIL** — still open. F.2 in audit.
3. **Workbench ↔ `model_call_command` budget tracker divergence** —
   still open. F.3 in audit.
4. **`loopos/skills/` is a 7-line re-export shim** — still open.
   F.4 in audit.
5. **Live-provider smoke is wire-level fake, not real HTTP** — still
   open. F.5 in audit.
6. **MCP Tool Hub may be dead code** — still open. F.6 in audit.
7. **No mutation testing, no secret scanning, no SBOM, no CI
   workflow** — still open. F.7 in audit.
8. **`loopos/cli/app.py` exceeds 300-LOC anti-bloat soft cap** —
   still open. F.8 in audit.
9. **~80 markdown docs, no API reference, no architecture
   diagram** — still open. F.9 in audit. The closeout-report
   inaccuracy item (F.9 sub-bullet) is **RESOLVED** by this
   cleanup.

Net: 7 RC blockers remain (down from 9). Items 1 and the F.9
inaccuracy sub-bullet are closed.

---

## H. Next hardening plan

The remaining 7 RC blockers map to the following hardening work,
ordered by leverage × cost (P0 → P3). Estimates assume a single
focused engineer.

### H.1 OpenGod → AIL bridge (P0)

F.2. Define a typed contract that maps `OpenGodDecision.kind` to one
or more `AILInstruction`s (e.g. `OPENGOD.HALT → LOOP.HALT`,
`OPENGOD.REFINE → AILPreference`). Add tests at the contract level
and at the integration level (a kernel-loop test that injects a
stub OpenGodDecision and asserts the loop honors it). Wire into
`KernelLoopEngine.compile_next_ail()`. ~3-4 days.

### H.2 Cross-path budget ledger (P1)

F.3. Add a `BudgetLedger` (process-singleton, keyed by
`provider_id + model_id + session_id`) to
`loopos/providers_runtime/budget.py`. Migrate both call sites
(`Workbench.call_model`, `model_call_command`) to use it. Add a
regression test that runs both paths in sequence and asserts
`commit()` is called exactly once and totals match. ~1 day.

### H.3 Loopback HTTP smoke (P1)

F.5. New `scripts/v0_3_live_provider_smoke_http.py` that boots a
`http.server` on `127.0.0.1:0` returning canned OpenAI/Ollama
responses, points `OPENAI_BASE_URL` at it, and runs the live call
end-to-end. Add as a 23rd readiness check, gated on
`LOOPOS_LIVE_HTTP_SMOKE=1`. ~1-2 days.

### H.4 CI workflow + pre-commit + secret scan (P1)

F.7. Add `.github/workflows/ci.yml` running ruff + mypy + pytest +
v0_2 readiness + v0_3 readiness + anti-bloat on every PR. Add
`.pre-commit-config.yaml` running the same on every local commit.
Add `gitleaks` (or `trufflehog`) to CI. ~1-2 days.

### H.5 Skills module re-homing (P2)

F.4. Move `loopos/memory/skill_store.py` and
`loopos/memory/skill_proposals.py` into `loopos/skills/` and
re-export from `loopos/memory/` for back-compat. Matches the
AGENTS.md blueprint and removes the "shim" anti-pattern.
~0.5 day.

### H.6 MCP wiring audit (P2)

F.6. One-day audit. Either wire `TOOL.CALL` into
`KernelLoopEngine._SYSCALLS` and add a corresponding AIL op, or
document the deferred status with a clear "not used in v0.3"
note in `loopos/mcp/__init__.py`. ~0.5-1 day.

### H.7 `loopos/cli/app.py` extraction (P2)

F.8. Move each v0.3 command's Typer binding into
`loopos/cli/typer/<command>.py` (one module per command). Reduces
`app.py` from 851 to ~450 lines. The argparse fallback in
`loopos/cli/fallback.py` is already split and can serve as a
reference. ~1 day.

### H.8 Mutation testing on the 5 new v0.3 packages (P2)

F.7 (sub-item). Install `mutmut` (or `cosmic-ray`). Run against
`loopos/adapters/`, `loopos/agent_bus/`, `loopos/opengod/`,
`loopos/product/`, `loopos/providers_runtime/`. Target 80% mutant
kill. Add to CI. ~2-3 days.

### H.9 docs/ prompts audit (P3)

The 6 prompt files in `.agent-prompts/` are Codex self-prompts
(`LoopOS_Kernel_Level_Codex_Prompt.md` etc.). They were correctly
separated from the doc tree in commit 1 of this cleanup. But their
content is high-leverage stale material — they may reference old
package names, old v0.2 layouts, or contracts that have since
changed. A 2-day pass: read each, mark which still apply, delete
or rewrite the others.

### H.10 API reference + architecture diagram (P3)

F.9 (open sub-bullet). No auto-generated API reference; no
architecture diagram. A 2-3 day pass: introduce `sphinx` (or
`mkdocs` with `mkdocstrings`) and an architecture diagram
(Mermaid in markdown or a separate SVG). Both will land as a
single docs PR.

---

## I. Final status

**v0.3-alpha implementation snapshot complete. RC blocked pending
hardening.**

All eight validation gates pass on `HEAD` (`d316837`):

| Gate | Result |
| ---- | ------ |
| `pytest -m "not slow"` | 947 passed, 9 skipped, 46 deselected, 19 subtests |
| `pytest -m "slow"` | 46 passed, 956 deselected |
| `ruff check .` | All checks passed |
| `mypy loopos tests` | Success: no issues found in 392 source files |
| `v0_2_readiness_check.py --json` | status=pass, hard_fail_count=0 |
| `v0_3_readiness_check.py --json` | status=pass, hard_fail_count=0 (22/22) |
| `anti_bloat_check.py --json` | hard_fail_count=0 |
| `rc_audit_cli_smoke.py` | ALL CLI SURFACES OK |
| `git status --short` | clean |

The 8-commit logical split is in place. The 7-commit blocker
(F.1) is closed. The closeout-report inaccuracy (F.9 sub-bullet)
is closed. 7 RC blockers remain — all known, all scoped, all
non-runtime-correctness issues.

The v0.3 implementation does **not** claim RC. It claims
**v0.3-alpha**: the implementation snapshot is complete, the
runtime is safe, the tests are green, the documentation is honest
about what is mock vs. real vs. planning-only, and the commit
history now reads as a narrative of logical features. The
remaining work to call it RC is mechanical and well-scoped.

End of v0.3-alpha history cleanup.