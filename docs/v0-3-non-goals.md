# LoopOS v0.3 — Non-Goals

> **Status (this document):** v0.3 non-goals are explicit and
> auditable. Anything listed here is *out of scope* for the
> v0.3-alpha → v0.3-RC hardening pass and is **not** a
> regression if it does not ship.

This document is the inverse of the v0.3 product surface. The
v0.3 product surface is what the runtime *is* (see
``docs/architecture-v0-3.md``); the v0.3 non-goals are what
the runtime *is not*. The non-goals matter because they make
the v0.3 release auditable: a reader can confirm that none
of the items below are present in the v0.3 tree, and that
the absence is a deliberate design choice, not an oversight.

The non-goals are organised by the five P0 / P1 hardening
buckets. The full v0.4 deferred-items list is in
``docs/architecture-v0-3.md`` Section D.

---

## A. Runtime surface — non-goals

The v0.3 runtime does not ship the following.

### A.1 No OpenGod → AIL authority bridge

OpenGod is a planning-only strategic decision system on
v0.3. Its decisions are surfaced through the Workbench and
the ``loopos opengod`` CLI; the kernel loop does not dispatch
on them. Wiring ``OpenGodDecision.kind`` to
``AILInstruction`` ops (``OPENGOD.HALT → LOOP.HALT``, etc.)
is a v0.4 item. See ``docs/v0-3-opengod-boundary.md`` for the
boundary decision and the v0.4 plan.

### A.2 No new LLM provider runtimes

The v0.3 provider runtime ships exactly three runtimes:
``MockProviderRuntime`` (default), ``OpenAICompatibleProviderRuntime``
(gated live), and ``OllamaProviderRuntime`` (gated live).
Adding new provider runtimes (Anthropic, Cohere, local
GGUF, etc.) is out of scope for v0.3.

### A.3 No MCP production wiring

The MCP router in ``loopos/mcp/`` is a compatibility facade
over the canonical syscall router. The kernel loop's
``_SYSCALLS`` table does not include ``TOOL.CALL`` on v0.3.
Wiring ``TOOL.CALL`` into the kernel loop, defining the
``TOOL.RESOLVE`` / ``TOOL.CALL`` / ``TOOL.RESULT`` AIL op
family, and adding the governance layer (per-tool approval
memory, per-session allow-lists, per-tool rate limits) is
the v0.4 Governed MCP Gateway. See
``docs/v0-3-mcp-boundary.md``.

### A.4 No skill governance

Skills are memory-backed on v0.3. The canonical
implementation lives in ``loopos.memory.skill_store`` and
``loopos.memory.skill_proposals``; the
``loopos/skills/__init__.py`` package is a re-export shim.
Full Skill Governance — skill lineage, scoring, dispatch
hooks, versioning — is a v0.4 item. See
``docs/v0-3-skills-boundary.md``.

### A.5 No Textual / Web UI

The v0.3 user-facing surface is the terminal-native
``loopos`` CLI plus the rich-Rich rendering layer
(``loopos.cli_ui``). No Textual TUI, no Web UI, no graphical
client. The v0.3 README documents this explicitly.

### A.6 No new policy types

The v0.3 policy packs cover the existing risk taxonomy
(L1-L5 + medium / high / blocked). Adding new policy types
(sandboxed shell, network policy, rate-limit policy) is
out of scope. The per-task instruction forbids it.

### A.7 No automatic code modification

v0.3 does not auto-merge patches, auto-modify its own
source, or run an unattended agent loop that writes to the
worktree. The ``run`` command requires explicit
``--workspace`` and ``--data-dir`` flags; the live provider
path requires ``--allow-live-provider + --budget-usd +
--confirm``.

---

## B. Quality / process — non-goals

### B.1 No CI workflow in the v0.3 release tarball

The v0.3 CI workflow is wired (see ``.github/workflows/ci.yml``)
but the v0.3 *release tarball* does not require CI to pass
before tagging. The CI workflow is a v0.3-RC requirement, not
a v0.3 release requirement.

### B.2 No mutation testing on the v0.3 critical path

The mutation testing pilot in P1-5 is a *baseline* report.
Running mutation testing on every commit is a v0.4 item.
The pilot's deliverables (the four per-module caches and
the report in ``docs/reports/v0-3-mutation-pilot.md``) are
the v0.3 record; CI does not gate on them.

### B.3 No SBOM or signed releases

The v0.3 release tarball does not carry a Software Bill of
Materials (SBOM) and is not signed. ``pip-audit`` /
``safety`` / ``cyclonedx`` are not on the v0.3-RC dependency
list. Sigstore / cosign signing is a v0.4 item.

### B.4 No multi-tenant isolation

The v0.3 runtime is single-tenant. The Workbench, the
agent bus, and the provider runtime share one process
state. Multi-tenant isolation (per-tenant data dirs,
per-tenant budget ledgers, per-tenant trace indexes) is
a v0.4 item.

### B.5 No streaming or async work

The v0.3 runtime is synchronous. The provider runtime's
``stream()`` method emits a single terminal chunk; it does
not open a Server-Sent Events stream. Async LLM transports
(``asyncio`` + ``httpx.AsyncClient``) are a v0.4 item.

### B.6 No internationalisation beyond UTF-8

The v0.3 CLI accepts UTF-8 input and emits UTF-8 output.
There is no localisation, no right-to-left support, no
locale-aware date / number formatting. The v0.3
``loopos run`` / ``loopos opengod`` CLIs do not have a
``--language`` flag.

---

## C. Hardening pass scope — non-goals

The v0.3-alpha → v0.3-RC hardening pass (P0 + P1) explicitly
forbids the following. Items the pass *would* normally do
in another release are deferred.

### C.1 No new features

The pass is a hardening pass, not a feature pass. The
constraint is explicit in the per-task instruction:

> Do not expand OpenGod features. Do not add new providers.
> Do not add MCP implementation. Do not add Textual / Web UI.

### C.2 No new tests outside the hardening scope

The pass adds regression tests for the v0.3 Typer
extraction, the deep-smoke stability fix, and the
mutation-pilot survivors. It does not add tests for v0.2
or v0.1 surfaces (the existing test suite covers them).

### C.3 No documentation rewrite

The pass adds the boundary decision docs
(``v0-3-opengod-boundary.md``, ``v0-3-skills-boundary.md``,
``v0-3-mcp-boundary.md``) and the architecture + non-goals
docs (``architecture-v0-3.md``, this file). It does not
rewrite the existing v0.3 readme, the AGENTS.md, or the
~80-markdown v0.3 doc set. A v0.4 pass will consolidate the
doc set.

### C.4 No runtime behaviour change

The pass moves code around (P0-1 BudgetLedger,
P0-2 urllib_transport, P1-4 typer_v0_3) and adds
documentation, but it does not change the user-facing
behaviour of any pre-existing v0.3 surface. The behaviour
matrix is asserted in
``docs/reports/v0-3-alpha-hardening-p0.md`` and
``docs/reports/v0-3-alpha-hardening-p1.md``.

### C.5 No mock-only behaviour presented as real runtime

The pass explicitly classifies every v0.3 surface as real,
dry-run, mock, or planning-only (see
``docs/architecture-v0-3.md`` Section C). No surface is
re-classified upward (mock → real, dry-run → live). The
loopback HTTP smoke in P0-2 is the only new real-runtime
path; everything else is documented as mock / dry-run /
planning-only.

### C.6 No v0.3.0 tag

The per-task instruction is explicit:

> Do not tag v0.3.0. Do not claim RC.

The pass ships to the ``v0.3-alpha-hardening`` branch on
top of the v0.3-alpha cleanup pass. The v0.3.0 tag is a
v0.3-RC decision, made after the P1 closeout report
records the final RC verdict.

---

## D. Why this list matters

The v0.3 non-goals are a *contract* with downstream users:
anything listed here is *intentionally absent*. If a
downstream user sees one of these items missing in the
v0.3 tree, the absence is a deliberate design choice, not
a regression. The v0.3 → v0.4 transition may add some of
these items; the v0.4 release notes will track the change.

The non-goals also bound the v0.3 release scope. A
contributor who wants to add one of these items must
either (a) propose a v0.4 RFC that supersedes the
non-goal, or (b) wait for the v0.4 release. The non-goals
are not a "we ran out of time" list; they are a
"v0.3 deliberately does not have this" list.

End of v0.3 non-goals.