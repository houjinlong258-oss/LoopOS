# LoopOS v0.3 — OpenGod Boundary Decision

> **Status:** planning-only on v0.3; authority bridge deferred to v0.4.
> **Verdict (P0-4):** Option B from the hardening task.

This document records the v0.3-alpha → v0.3-RC hardening decision
for the OpenGod boundary. The hardening task offered two paths:

* **Option A.** Implement a minimal ``OpenGodDecision → AIL``
  bridge with tests. This would add new AIL instruction ops
  (e.g. ``OPENGOD.HALT → LOOP.HALT``), wire
  ``OpenGodDecision`` into ``KernelLoopEngine.compile_next_ail()``,
  and add a kernel-loop test that injects a stub
  ``OpenGodDecision`` and asserts the loop honors it.
* **Option B.** Document OpenGod as planning-only on v0.3 and
  defer the authority bridge to v0.4.

This pass ships **Option B**. The rest of this document explains
why and what it commits to.

---

## Why Option B

The hardening task is explicit:

> Do not expand OpenGod features.

Option A is a feature expansion. Adding new AIL instruction ops
grows the AIL surface area; wiring ``OpenGodDecision`` into the
kernel loop changes the kernel's contract; adding a kernel-loop
test for the bridge couples OpenGod to the kernel's authority
guarantees. Each of those is a meaningful change to LoopOS's
"shape" — exactly the kind of change the hardening pass is
forbidden from making.

Option B keeps v0.3's surface stable. The only changes are
documentation (this file plus an explicit "planning-only" callout
in ``loopos/opengod/__init__.py``) and one additional readiness
check that asserts the boundary is actually honored at the
import level. No new AIL ops. No kernel-loop coupling. No
runtime-behavior change.

Option B is also the safer default for v0.3-RC: shipping a kernel
authority bridge that has not been audited under load would be
worse than shipping no bridge at all. The Workbench already
surfaces ``OpenGodVerdict`` to the user (see
``loopos/product/workbench.py::_fusion_summary``), so the
information is available; the kernel just does not act on it.

---

## What "planning-only" means

OpenGod's v0.3 contract is unchanged from the alpha release:

* OpenGod reads evidence from the runtime (goal, trace, fusion
  plan, adapter state, readiness proof).
* OpenGod emits ``OpenGodDecision`` and ``OpenGodVerdict``.
* OpenGod never calls a provider, never opens a file, never
  executes shell.
* The Workbench shows OpenGod verdicts in the fusion panel.
* The CLI exposes ``loopos opengod ...`` for manual inspection.

What changes with this hardening pass:

* ``loopos/opengod/__init__.py`` adds an explicit "NOT wired into
  AIL execution authority on v0.3" callout so the boundary is
  visible to anyone importing the package.
* ``scripts/v0_3_readiness_check.py`` adds a new check
  ``check_opengod_planning_only_boundary`` that fails RC if
  either the boundary callout is missing or
  ``loopos.kernel.loop_engine`` (or any equivalent runtime
  engine) starts importing OpenGodDecision.
* This document exists.

What does **not** change:

* No new AIL instruction ops.
* No ``OpenGodDecision`` consumption in
  ``KernelLoopEngine.compile_next_ail()``.
* No background scheduler for OpenGod.
* No widening of the OpenGod API surface.
* No new OpenGod tests beyond the boundary check.

---

## What v0.4 has to do

The bridge is a v0.4 item. The minimum viable contract is:

1. Map ``OpenGodDecision.kind`` → one or more ``AILInstruction``
   ops. The natural mapping is:
   * ``OpenGodDecisionKind.HALT`` → ``LOOP.HALT``
   * ``OpenGodDecisionKind.REFINE`` → ``AILPreference``
     (so the next AIL compile weights the decision)
   * ``OpenGodDecisionKind.SCALE`` → ``TERM.EXEC`` with a bounded
     scope (still needs the kernel's policy check)
   * ``OpenGodDecisionKind.ACCEPT`` → no-op (the kernel's own
     decision stands)
2. Wire the bridge into ``KernelLoopEngine.compile_next_ail()``
   behind a feature flag (``LOOPOS_OPENGOD_AUTHORITY=1``); off by
   default.
3. Add a kernel-loop test that injects a stub
   ``OpenGodDecision`` and asserts the loop honors it.
4. Add a second test that asserts the loop does *not* honor the
   decision when the flag is off (so v0.3's contract still
   holds for the v0.3 path).
5. Audit the kernel's policy-check coverage for the new
   ``OPENGOD.*`` op family.
6. Update this document to record the bridge as shipped.

That is on the order of three to four days of focused work
(estimate from ``docs/reports/v0-3-alpha-split-audit.md``
Section G.2). It is out of scope for this hardening pass.

---

## Acceptance check

The hardening pass accepts this boundary decision when:

* ``loopos/opengod/__init__.py`` contains the explicit
  "planning-only, NOT wired into AIL execution authority"
  callout. (Asserted by a unit test.)
* ``scripts/v0_3_readiness_check.py`` exposes
  ``check_opengod_planning_only_boundary`` and the check passes.
* No code outside ``loopos/opengod/`` imports
  ``OpenGodDecision`` for execution purposes. The readiness
  check greps for this.
* The ``CHANGELOG.md`` v0.3-RC entry records the boundary
  decision and the v0.4 follow-up plan.

All four are delivered by this pass.

---

## Files touched by this decision

* ``loopos/opengod/__init__.py`` — boundary callout added.
* ``docs/v0-3-opengod-boundary.md`` — this document.
* ``scripts/v0_3_readiness_check.py`` — new check.
* ``tests/test_opengod_boundary.py`` — new tests for the
  callout, the readiness check, and the import-surface guard.
* ``CHANGELOG.md`` — v0.3-RC entry.

No other runtime files are touched.

---

## Final status

OpenGod remains planning-only on v0.3. The authority bridge is
on the v0.4 plan. The boundary is documented, asserted in
import-level tests, and surfaced in the v0.3 readiness check.

End of v0.3 OpenGod boundary decision.