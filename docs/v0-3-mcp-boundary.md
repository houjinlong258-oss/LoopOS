# LoopOS v0.3 — MCP Boundary

> **Status:** v0.3 MCP is a compatibility facade over the
> canonical syscall router. Production wiring is deferred to
> v0.4 (Governed MCP Gateway).

The v0.3-alpha split-audit (`docs/reports/v0-3-alpha-split-audit.md`
Section F.6) flagged a possible dead-code concern:

> ``loopos/mcp/router.py``, ``loopos/mcp/types.py``, and
> ``loopos/mcp/__init__.py`` exist. But
> ``loopos/kernel/loop_engine.py::_SYSCALLS`` (the syscall
> routing table) maps ``TERM.EXEC``, ``FILE.READ``,
> ``FILE.WRITE``, ``GIT.STATUS``, ``GIT.DIFF`` -- it does
> **not** include ``TOOL.CALL``. If the kernel never dispatches
> to the MCP router, then ``loopos/mcp/`` is dead code or only
> exercised by tests.

The P1-3 hardening task asked for an audit. The audit
result: **the MCP router is reachable from ``create_default_router()``
but is not wired into the kernel loop on v0.3.** The audit
recommends documenting the boundary explicitly and deferring
production wiring to v0.4 (Governed MCP Gateway).

The P1-3 hardening task offered two paths:

* **Option A.** Wire ``TOOL.CALL`` into ``KernelLoopEngine._SYSCALLS``
  now, with a minimal safe wire path. Add a kernel-loop test
  that exercises the route.
* **Option B.** Document MCP as present but not
  production-wired on v0.3. Defer production wiring to v0.4.

This pass ships **Option B**. The rest of this document
records the audit and the v0.4 plan.

---

## Audit results

### What is present

* `loopos/mcp/types.py` (71 lines): Pydantic v2 contracts for
  `ToolSpec`, `ToolCall`, `ToolResult`, `RegisteredTool`, and
  the `ToolRegistry` in-memory store. A `ToolRiskLevel`
  literal pins the risk taxonomy at `{"low", "medium",
  "high", "blocked"}`.
* `loopos/mcp/router.py` (136 lines): `ToolRouter` class
  with `register`, `list_tools`, `resolve`, `call`. The
  `call` method goes through Policy OS first
  (`policy_engine.evaluate("tool.call", ...)`) and only then
  invokes the registered handler. The
  `create_default_router()` factory wires the router to the
  v0.2 canonical `create_default_syscall_router()`, mapping
  each syscall spec to a tool spec + handler.
* `loopos/mcp/__init__.py`: public API surface
  (`ToolCall`, `ToolRegistry`, `ToolResult`, `ToolSpec`,
  `create_default_router`).

### What is not wired

* `KernelLoopEngine._SYSCALLS` (loopos/kernel/loop_engine.py
  line 46) maps:
  * `TERM.EXEC → terminal.exec`
  * `FILE.READ → file.read`
  * `FILE.WRITE → file.write`
  * `GIT.STATUS → git.status`
  * `GIT.DIFF → git.diff`
  * **No `TOOL.CALL` entry.**
* A repo-wide grep for `create_default_router`, `ToolRouter`,
  and `loopos.mcp` returns only the package itself and
  `tests/test_mcp_router.py`. The kernel loop, the workbench,
  and the CLI do not import the router.

### What is reachable

* `tests/test_mcp_router.py` exercises the router
  end-to-end (Policy OS gate + handler dispatch + result
  shape).
* The workbench and any code that explicitly imports
  `loopos.mcp.create_default_router` can wire it manually.
  Nothing in `loopos/` does so today.

### Risk classification

The MCP router is **mock-only** in production on v0.3. It
exists; the contracts are typed; the Policy OS gate is
present; but the kernel loop does not dispatch to it. The
"real runtime" path on v0.3 is the v0.2 canonical syscall
router; the MCP router is a layered facade that the runtime
does not use.

This is **not** hidden dead code. The package is import-clean,
the contracts are used by tests, and the Policy OS gate is
enforced. The boundary is just not crossed by the kernel loop.

---

## Why Option B

Option A would add a `TOOL.CALL` entry to
`KernelLoopEngine._SYSCALLS` plus a kernel-loop test that
exercises the route. The minimal wire path *is* available
(the router is functional; the only missing piece is the
syscall-table entry). But the v0.4 hardening plan needs more
than a syscall-table entry:

* a typed AIL op family (`TOOL.RESOLVE` / `TOOL.CALL` /
  `TOOL.RESULT`);
* a governance layer (per-tool approval memory, per-session
  allow-lists, per-tool rate limits);
* a redaction contract on tool call args / results;
* an audit-trail contract that lands every tool call in the
  governed trace store.

Shipping only the syscall-table entry on v0.3 would land
half a feature and document a wire path that production code
should not yet trust. It would also lock in the AIL op
family shape before v0.4 audits it.

Option B keeps v0.3 stable. The router remains reachable
(from tests, from the workbench if someone wires it
manually) and the contracts remain typed. The kernel loop
does not dispatch to it. The v0.4 work is the right place
to land the wire path together with the governance layer.

---

## What v0.4 has to do

The minimum viable v0.4 Governed MCP Gateway is:

1. **Wire `TOOL.CALL`** into `KernelLoopEngine._SYSCALLS`.
2. **Define a typed AIL op family**:
   * `TOOL.RESOLVE` -- look up a tool by name, returns the
     `ToolSpec` and Policy OS decision.
   * `TOOL.CALL` -- dispatch a `ToolCall` through the router,
     returns the `ToolResult`.
   * `TOOL.RESULT` -- observe a tool result, run
     redaction + audit.
3. **Add a governance layer**:
   * per-tool approval memory (cached per session);
   * per-session allow-lists (a session may pre-approve
     `low` and `medium` tools);
   * per-tool rate limit (token bucket per tool per session).
4. **Define a redaction contract**: tool call args and
   results are passed through `redact_secrets` before they
   reach the trace store.
5. **Add an audit trail**: every tool call lands in the
   governed trace store with `kind=tool.call` and the
   redacted payload.
6. **Update this document** to record the gateway as
   shipped.

That is on the order of one to two days of focused work
(estimate from the alpha audit's Section G.7). It is out of
scope for the v0.3-alpha → v0.3-RC hardening pass.

---

## Acceptance check

The hardening pass accepts this audit and boundary decision
when:

* `loopos/mcp/__init__.py` carries the explicit
  "present but not production-wired" callout. (Asserted by a
  unit test.)
* `KernelLoopEngine._SYSCALLS` does not include `TOOL.CALL`
  on v0.3. (Asserted by a unit test.)
* The MCP router's public API is unchanged. (Asserted by
  import + roundtrip test.)
* The v0.3 readiness check exposes a new
  `check_mcp_present_not_wired_boundary` that asserts the
  callout, the missing `TOOL.CALL` entry, and the package
  remains import-clean.
* The `CHANGELOG.md` v0.3-alpha hardening P1 entry records
  the audit and the v0.4 follow-up plan.

All five are delivered by this pass.

---

## Files touched by this decision

* `loopos/mcp/__init__.py` — boundary callout added; the
  `__all__` list is expanded to include the typed exports
  (`ToolRouter`, `ToolHandler`, `ToolRiskLevel`,
  `RegisteredTool`) so the public surface matches the
  module's actual exports.
* `docs/v0-3-mcp-boundary.md` — this document.
* `scripts/v0_3_readiness_check.py` — new check.
* `tests/test_mcp_boundary.py` — new tests.
* `CHANGELOG.md` — v0.3-alpha hardening P1 entry.

No other runtime files are touched.

---

## Final status

MCP remains a compatibility facade on v0.3. The kernel loop
does not dispatch to it. The v0.4 work (Governed MCP Gateway)
will land the production wire path together with the
governance layer. The boundary is documented, asserted in
import-level tests, and surfaced in the v0.3 readiness
check.

End of v0.3 MCP boundary audit.