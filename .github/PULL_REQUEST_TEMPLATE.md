<!--
LoopOS v0.2 PR Template
This template applies to PRs targeting the v0.2 branch only.
v0.1.0 release evidence is FROZEN; see docs/v0.1.0-FREEZE.md.
-->

## Summary

<!-- One-paragraph description of the change. -->

## v0.2 Boundary Gates (HARD-FAIL)

- [ ] **v0.1.0 release evidence untouched.** No changes to the v0.1.0
      tag, dist artifact, release notes, or CI report. Evidence file
      `docs/v0.1.0-FREEZE.md` and `scripts/baselines/v0_1_0_loopos.txt`
      are append-only after first commit.
- [ ] **v0.1.0 runtime baseline untouched.** No file in
      `scripts/baselines/v0_1_0_loopos.txt` was modified or deleted.
      Reason code: `v0_1_runtime_modified`.
- [ ] **No new dependencies without explicit allowlist.** If a new
      dependency is required, add it to `ALLOWED_DEPS` in
      `scripts/anti_bloat_check.py` AND open a tracking issue.
      Reason code: `unauthorized_dependency`.
- [ ] **No v0.1.0 evidence mutation.** All files listed in
      `EVIDENCE_FILES` in `scripts/anti_bloat_check.py` are intact.
      Reason code: `v0_1_0_evidence_mutated`.

## v0.2 Boundary Gates (WARNINGS — review carefully)

- [ ] **No files over 300 LOC** in new modules (or justified in the
      PR description with a split plan).
- [ ] **Tests paired with new runtime code.** New `loopos/`
      modules ship with a corresponding `tests/test_<module>.py`.
- [ ] **No new wrappers / single-use helpers / new abstractions**
      unless the PR description justifies each.

## Pre-Submit Checklist

- [ ] `python scripts/anti_bloat_check.py` exits 0 (warnings allowed).
- [ ] `python tests/test_anti_bloat_check.py` passes.
- [ ] `git status` shows only files in the v0.2 allowlist:
      - `docs/v0.1.0-FREEZE.md` (append-only)
      - `docs/schemas/readiness-proof.schema.json`
      - `docs/schemas/readiness-proof.example.json`
      - `docs/readiness-proof-schema.md`
      - `scripts/anti_bloat_check.py`
      - `scripts/baselines/v0_1_0_loopos.txt` (append-only)
      - `README.md` (banner section only)
      - `.github/PULL_REQUEST_TEMPLATE.md`
      - `tests/test_anti_bloat_check.py`
- [ ] `git diff v0.1.0..HEAD -- loopos/` is empty.
- [ ] `git log` shows no tag or dist changes.

## Out of Scope (requires separate PR + design review)

- Modifications to `KernelLoopEngine` or any v0.1.0 runtime file
- Full Go Core rewrite (out of scope for v0.2 entirely)
- Web UI, cloud service, distributed scheduler, autonomous daemon

## Related Issues

<!-- Link tracking issues, e.g. "unauthorized-dependency approval: #NNN" -->
