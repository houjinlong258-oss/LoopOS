# LoopOS Readiness Proof Schema (Draft)

> Phase 0 ships the **schema and prose contract** only. The runtime
> producer that emits `readiness-proof.json` instances is a Phase 1
> deliverable. Do not implement the producer in Phase 0.

## Purpose

`readiness-proof.json` is a machine-readable artifact that proves a
LoopOS release is ready. It is **not** a single boolean — it is a set
of evidence-backed invariants.

## Required Fields

| Field | Type | Meaning | True when... |
|---|---|---|---|
| `schema_version` | string | Schema revision (`"0.2"` in Phase 0) | always |
| `phase` | string | Current pipeline phase | one of `phase-0`, `phase-1`, `phase-2`, `release-candidate`, `release` |
| `generated_at` | string (ISO 8601) | When the proof was produced | always |
| `fsm_coverage` | bool | All FSM states/transitions tested | every state appears in at least one test |
| `policy_gates_active` | bool | All Policy OS gates active | each gate has both unit + integration test |
| `budget_enforced` | bool | Budget limits enforced | over-budget raises, never silently truncates |
| `memory_governed` | bool | Memory writes go through governance | `STORE_MEMORY` always creates a proposal first |
| `replay_deterministic` | bool | Replay is deterministic | same input → same normalized hash |
| `go_core_untouched` | bool | v0.1.0 runtime baseline untouched | `git diff v0.1.0..HEAD -- loopos/` is empty |
| `aci_runtime_bound` | bool | ACI commands routed through kernel | AIL/AI-ISA instructions validated by Policy OS |
| `ali_fsm_bound` | bool | ALI sessions driven by FSM | state transitions logged + replayable |
| `anti_bloat_checked` | bool | Anti-bloat check passed | `scripts/anti_bloat_check.py` exits 0 |

## Optional Fields

- `evidence`: free-form object with paths to evidence artifacts
  (test reports, baseline file paths, hash lists). Structure is
  finalized in Phase 1.

## Phase 0 Behavior

In Phase 0:

- The schema is **defined** but not yet **produced** by the runtime.
- The 9 boolean fields are **placeholders** for Phase 1+ evidence.
- The example instance in
  `docs/schemas/readiness-proof.example.json` carries `false` for the
  runtime-bound fields and `true` for the static-check fields
  (`go_core_untouched`, `anti_bloat_checked`).

## Phase 1 Plan

- Add `loopos/aci/pre_landing/` (parked candidate) to emit
  `readiness-proof.json` after each CI run.
- Wire `scripts/anti_bloat_check.py` output into `evidence.anti_bloat_report`.
- Add `pytest tests/test_readiness_proof.py` to validate the example
  instance against this schema.

## Versioning

- Schema version follows semver. Adding a new optional field is a
  minor bump; renaming or removing a field is a major bump.
- All instances MUST validate against the schema version they declare.
