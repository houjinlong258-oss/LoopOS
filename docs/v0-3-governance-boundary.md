# LoopOS v0.3 Governance Boundary

> **Status:** Enforced as of v0.3.
> **Audience:** Anyone proposing to add or change code in the
> `loopos/product/`, `loopos/adapters/`, `loopos/agent_bus/`,
> `loopos/providers_runtime/`, or `loopos/opengod/` packages.

This document is the **authoritative boundary** for v0.3 module
growth. It exists so that the Product Layer, Adapter Layer, Agent Bus,
Provider Runtime, and OpenGod layer can grow without re-licensing the
v0.2 kernel or weakening the existing v0.2 readiness proof.

---

## 1. v0.3 Hard Rules

These rules are **non-negotiable** and any PR that violates them is a
hard-fail in `scripts/v0_3_readiness_check.py`:

1. **Agent may think freely. Agent may not exceed authority.**
   The v0.2 Policy OS continues to be the only authority boundary.
2. **Model calls may be real. Real calls must be governed.**
   `loopos/providers_runtime/` can do HTTP, but every live call must
   require `live_provider_calls_allowed=True` AND a budget.
3. **Product Layer cannot bypass the kernel.**
   `loopos/product/` is allowed to **render** and **dispatch**; it
   must never instantiate a `KernelLoopEngine` itself or call into
   the syscall router directly. The path is:
   `product -> adapter registry / agent bus -> ACI -> kernel`.
4. **Adapters cannot bypass ACI.**
   An external `AgentKernelAdapter` may only emit
   `AgentKernelEvent` objects. The Agent Bus translates those events
   into `AgentCommand` objects that flow through `loopos.aci`.
5. **OpenGod does not execute.**
   `loopos/opengod/` produces strategic decisions; it never calls
   `kernel_loop_engine.submit_agent_command` and never opens a file
   or a network connection. Anything that wants side effects must
   route through `loopos.fusion_router` (planning) and `loopos.aci`
   (execution), in that order.
6. **No silent live provider calls.**
   If `live_provider_calls_allowed=False` (the default), every
   provider runtime must return a `ModelCallResponse` with
   `status="blocked"` and `reason_codes=["live_provider_disabled"]`.
7. **Secrets never leave the runtime boundary.**
   `loopos.providers_runtime.usage.redact_secrets` is the only
   redaction primitive. It is applied to every response payload, every
   log line, and every error message that originates from a provider.

---

## 2. Module Allow-List

The following **allow-list** describes which v0.3 modules may import
which v0.2 modules. Imports not in this list are a hard-fail.

| From / To                | `loopos.kernel` | `loopos.aci` | `loopos.ali` | `loopos.policy_os` | `loopos.providers` (meta) | `loopos.providers_runtime` | `loopos.fusion_router` | `loopos.trace` |
| ------------------------ | --------------- | ------------ | ------------ | ------------------ | -------------------------- | -------------------------- | ---------------------- | ------------- |
| `loopos.product`         | ❌              | ✅ dispatch  | ✅ render    | ❌                 | ✅ meta only               | ❌                         | ✅ render verdict      | ✅ render trace |
| `loopos.adapters`        | ❌              | ❌           | ❌           | ❌                 | ❌                         | ❌                         | ❌                     | ❌            |
| `loopos.agent_bus`       | ❌              | ✅ translate | ✅ attach   | ❌                 | ❌                         | ❌                         | ❌                     | ✅ persist    |
| `loopos.providers_runtime` | ❌           | ❌           | ❌           | ❌                 | ✅ meta only               | (self)                    | ❌                     | ✅ emit event |
| `loopos.opengod`         | ❌              | ❌           | ❌           | ❌                 | ❌                         | ❌                         | ✅ read plans         | ✅ read       |

**Notes**

* The **adapters** package has **zero** import access to ACI, ALI,
  Policy OS, the kernel, or any provider runtime. That is by design:
  an adapter is a contract, not a side effect.
* The **agent_bus** package may import ACI/ALI/Trace because its job
  is to translate `AgentKernelEvent` into governed `AgentCommand`s
  and to attach the adapter session to an ALI session.
* The **product** package may import ACI/ALI/Trace for read-only
  inspection (rendering the workbench), and may import the fusion
  router for the Fusion view, but it must not call
  `kernel.submit_agent_command`.
* The **opengod** package is read-only across the runtime: it can
  inspect trace events and fusion plans, but it cannot produce
  commands of its own.

---

## 3. Anti-Bloat Notes for v0.3

The v0.2 anti-bloat check (`scripts/anti_bloat_check.py`) continues to
run unmodified against v0.3. The v0.3-specific additions to its
allow-list are:

* `loopos.product` is allowed to grow up to the documented module
  split (`workbench.py`, `views.py`, `render.py`, `commands.py`,
  `*_view.py`).
* `loopos.adapters` is allowed one file per first-class adapter
  (mock, hermes, scream-code, cleanroom). Adding a new adapter is
  allowed only via the registry.
* `loopos.providers_runtime` is allowed one file per first-class
  provider runtime (base, mock, openai, ollama, registry, plus shared
  models/budget/usage/errors).
* `loopos.agent_bus` is allowed the documented split (bus, events,
  translation, command_bridge, session).
* `loopos.opengod` is allowed the documented split (models, decision,
  evidence, budget, verdict).

Any new file in a v0.3 package is **out-of-scope** until it is added
to the allow-list in this document **and** to
`scripts/anti_bloat_check.py`.

---

## 4. v0.3 Readiness Proof Surface

`scripts/v0_3_readiness_check.py` is the canonical entry point for
v0.3 readiness. It MUST verify:

1. `loopos.product` is importable and `Workbench` is constructable.
2. `loopos.adapters` registry is populated with at least mock + hermes.
3. `loopos.agent_bus` is importable and translates at least one
   `AgentKernelEvent` to an `AgentCommand`.
4. `loopos.providers_runtime` is importable; live calls are blocked
   by default; budget is enforced; secrets are redacted.
5. `loopos.opengod` is importable and produces a `OpenGodDecision`
   that does not contain an `AgentCommand`.
6. Workbench CLI renders the eight required panels.
7. `loopos adapters list` returns JSON matching the documented schema.
8. `loopos providers runtime list` returns JSON matching the
   documented schema.
9. `loopos model call --dry-run` returns a `dry_run` response.
10. `scripts/v0_2_readiness_check.py` still passes (no regression).

---

## 5. Reading Order

* `docs/architecture.md` — overall v0.2 architecture.
* `docs/cli-ui.md` — v0.2 CLI conventions reused in v0.3.
* `docs/fusion-router.md` — v0.2 fusion router, upgraded in v0.3.
* `docs/readiness-proof-schema.md` — readiness proof shape.

End of v0.3 governance boundary.
