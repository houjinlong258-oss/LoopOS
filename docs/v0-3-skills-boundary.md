# LoopOS v0.3 — Skills Module Boundary

> **Status:** v0.3 skills are memory-backed; full Skill
> Governance is deferred to v0.4.

The v0.3-alpha split-audit (`docs/reports/v0-3-alpha-split-audit.md`
Section F.4) flagged the seven-line `loopos/skills/__init__.py`
shim as an RC blocker:

> ``loopos/skills/`` is a 7-line re-export shim.
> ``loopos/skills/__init__.py`` re-exports from
> ``loopos.memory.skill_store`` and
> ``loopos.memory.skill_proposals``. AGENTS.md lists "Skill
> Learning" as a core capability and uses ``loopos/skills/`` as
> the namespace in the MVP layout. The actual implementation
> lives in ``loopos/memory/`` and is not clearly
> discoverable.

The P1-2 hardening task offered two paths:

* **Option A.** Move `loopos/memory/skill_store.py` and
  `loopos/memory/skill_proposals.py` into `loopos/skills/`, and
  re-export them from `loopos/memory/` for back-compat.
* **Option B.** Document skills as memory-backed on v0.3 and
  defer the full Skill Governance work to v0.4.

This pass ships **Option B**. The rest of this document
explains why and what it commits to.

---

## Why Option B

Option A is the right shape on the long-term AGENTS.md
blueprint: the blueprint says "loopos/skills/" should be the
home of skill code. But moving the implementation files would
generate churn:

* Every import site for `loopos.memory.skill_store` and
  `loopos.memory.skill_proposals` (inside `loopos/`, in tests,
  in the kernel loop, in the workbench) would have to be
  re-pointed or augmented with a back-compat re-export.
* The re-export shim would move to `loopos/memory/`, where it
  is harder to discover and easier to forget about.
* The change is purely cosmetic for the v0.3 alpha — the actual
  Skill Governance work (lineage, scoring, dispatch hooks) is
  not landing in v0.3 either way, so the cosmetic improvement
  is the only thing Option A delivers.

Option B keeps the runtime surface stable and is unambiguous
about *why* the namespace is a shim: the v0.3 implementation
lives in `loopos.memory.*` and the v0.4 work will move it to
`loopos/skills/`. The user-facing cost is one file
(`docs/v0-3-skills-boundary.md`, this document) and a stronger
docstring on the shim.

---

## What "memory-backed" means

`loopos/skills/` is a four-line re-export of two modules from
`loopos/memory/`:

* `loopos/memory/skill_store.py` — `Skill` (the persisted
  record), `SkillStore` (read/list), `extract_skill_from_events`
  (mine a Skill from a finished run's events).
* `loopos/memory/skill_proposals.py` — `SkillProposal` (the
  contract for proposing a new skill; lifecycle: pending ->
  accepted/rejected/merged).

The four-line `loopos/skills/__init__.py` re-exports
`Skill`, `SkillStore`, `extract_skill_from_events`, and
`SkillProposal`. The package exposes nothing else.

What the v0.3 surface does:

* read existing skills;
* extract a skill from a finished run;
* propose a new skill;
* accept / reject / merge a proposal.

What the v0.3 surface does **not** do:

* auto-merge proposals without a human or governance step;
* score proposals against an external model;
* persist skill lineage beyond `source_run_id`;
* expose a kernel-loop / AIL hook for skill dispatch;
* enforce a skill-versioning policy.

---

## What v0.4 has to do

The minimum viable v0.4 Skill Governance package is:

1. **Move** `loopos/memory/skill_store.py` and
   `loopos/memory/skill_proposals.py` into `loopos/skills/`.
   Keep the public API names unchanged.
2. **Re-export** the moved symbols from `loopos/memory/` for
   back-compat so the v0.3 import sites keep working.
3. **Define a Skill lineage contract** — a Skill carries
   `parent_skill_id` / `derived_from_skill_ids` plus
   supersession history.
4. **Define a Skill scoring contract** — a scoring function
   takes a `SkillProposal` + historical evidence and emits a
   confidence score with reasons. Off by default; on behind a
   feature flag.
5. **Add a Skill dispatch hook** — define how the kernel loop
   consults the skill store on a `GOAL` event. Off by default;
   the kernel is not allowed to dispatch a skill in v0.4
   without an explicit ``loopos skills enable`` switch.
6. **Add a Skill-versioning policy** — `status` (active /
   disabled / superseded) gains a `version` field; auto-merge
   rules require a version bump when source events change.
7. **Update this document** to record the v0.4 work as
   shipped.

That is on the order of one to two weeks of focused work
(estimate from the alpha audit's Section G.6). It is out of
scope for the v0.3-alpha → v0.3-RC hardening pass.

---

## Acceptance check

The hardening pass accepts this boundary decision when:

* `loopos/skills/__init__.py` carries the explicit
  "memory-backed, v0.3 shim; full governance deferred to v0.4"
  callout. (Asserted by a unit test.)
* `loopos/skills/__init__.py` re-exports exactly the same four
  symbols it did before the P1 pass; no public API surface
  change.
* `loopos/memory/skill_store.py` and
  `loopos/memory/skill_proposals.py` are unchanged; the
  canonical implementation still lives there on v0.3.
* `scripts/v0_3_readiness_check.py` exposes a new
  `check_skills_memory_backed_boundary` that asserts the
  callout, the four-symbol export surface, and the absence of
  v0.4 governance symbols (lineage, scoring, dispatch hook,
  versioning) in the `loopos/skills/` package.
* The `CHANGELOG.md` v0.3-alpha hardening P1 entry records
  the boundary decision and the v0.4 follow-up plan.

All five are delivered by this pass.

---

## Files touched by this decision

* `loopos/skills/__init__.py` — boundary callout added (size
  goes from 4 lines to ~30 lines, all of which is docstring).
* `docs/v0-3-skills-boundary.md` — this document.
* `scripts/v0_3_readiness_check.py` — new check.
* `tests/test_skills_boundary.py` — new tests for the callout,
  the export surface, the readiness check, and the
  governance-symbol guard.
* `CHANGELOG.md` — v0.3-alpha hardening P1 entry.

No other runtime files are touched. The canonical skill
implementation stays in `loopos/memory/`.

---

## Final status

Skills remain memory-backed on v0.3. Full Skill Governance is
on the v0.4 plan. The boundary is documented, asserted in
import-level tests, and surfaced in the v0.3 readiness check.

End of v0.3 Skills boundary decision.