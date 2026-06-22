# LoopOS Mad Dog Mode

Mad Dog Mode is the friendly CLI alias for the Fusion Router's
explicit user-force escalation. It is **not** a separate
execution engine; it is a thin wrapper over
`loopos fusion-router plan ...` with a fixed trigger shape:

```text
mode            = "mad_dog"
trigger.source  = "user"
trigger.reason  = "explicit_user_request"
trigger.severity = "critical"   (overridable via --severity)
```

## When to Use Mad Dog Mode

Use Mad Dog Mode when normal single-model execution is not
enough and you want the maximum governed escalation available:

* nasty bugs that survive multiple fixes;
* large refactors with cross-file impact;
* release blockers;
* security-sensitive debugging;
* repeated failures that the same model keeps repeating;
* the user has shown repeated dissatisfaction.

## When NOT to Use Mad Dog Mode

Do not use Mad Dog Mode for:

* small changes (a single file, a single function, a quick
  review);
* tasks where a single capable model is enough;
* tasks where the cost budget cannot justify the role fanout;
* tasks where the model is already confident.

The default remains single-model execution. Mad Dog Mode is the
escalation, not the baseline.

## Slogan

```text
Mad Dog Mode increases intelligence density, not authority level.
```

## CLI

```bash
# Force the full role set under explicit user authority.
loopos mad-dog task.json --json
loopos mad-dog task.json --severity high --json

# Explain the activation rationale.
loopos mad-dog explain task.json --json

# Escalate an existing run based on failure evidence.
loopos mad-dog escalate --run-id RUN_ID --reason release_blocker --json

# Inspect a persisted mad-dog plan / verdict.
loopos mad-dog status FUSION_ID --json

# List all persisted mad-dog plans / verdicts.
loopos mad-dog list --json

# Route a persisted mad-dog plan through the kernel integration
# (planning-only when no kernel engine is supplied).
loopos mad-dog route --fusion-id FUSION_ID --json
```

`mad-dog` maps directly to:

```text
mode = "mad_dog"
trigger.source = "user"
trigger.reason = "explicit_user_request"
trigger.severity = "critical" (default)
```

The override via `--severity` lets a user request the full
`mad_dog` role set without forcing `critical` severity (e.g.
for a soft escalation that still benefits from the full team).

## Role Set Under Mad Dog Mode

```text
planner
architect
bug_hunter
coder
test_breaker
security_guard
simplifier
reviewer
judge
summarizer
```

The router degrades gracefully when the registry cannot honour
a role: the best available profile is reused and the gap is
recorded in `FusionRoleAssignment.capability_gaps`. When no
providers are registered at all, each role receives an empty
assignment with `capability_gaps=["no_providers_available"]`.

## Authority Boundary

Mad Dog Mode must still obey:

* **Policy OS** -- every recommended command carries the same
  policy envelope as a normal command.
* **Budget limit** -- the `FusionPlan.budget_limit` field records
  `max_roles` and `max_rounds`; the runtime can refuse to start
  a run that exceeds the budget.
* **Provider availability** -- role assignments degrade gracefully
  to reuse the best available profile.
* **No destructive actions without approval** -- the router
  recommends commands; only ACI / Kernel may execute governed
  commands.
* **No live provider calls in v0.2** -- `FusionPlan.live_provider_calls_allowed=False`
  by default. Live fanout is deferred to v0.3+.

## Hard Limits

* Mad Dog Mode never edits files, runs shell, or calls a live
  provider API directly. It is a planning layer.
* Mad Dog Mode does not bypass Policy OS, the Syscall Router, or
  the existing trace runtime.
* Mad Dog Mode does not increase authority level. The user, the
  kernel, and the policy layer remain the authority.

## Tests

`tests/test_fusion_router_cli.py` covers:

* `mad-dog` forces `mode = "mad_dog"` regardless of score.
* `mad-dog --severity low` still selects `mad_dog`.
* `mad-dog explain` returns the activation rationale under the
  mad-dog trigger shape.
* `mad-dog escalate` builds a plan with `source = "kernel"`.
* `mad-dog status` reads from the local JSON persistence layer
  (Phase 7).
* `mad-dog list` enumerates persisted plan / verdict ids.
* `mad-dog route` returns a structured `planning_only` result when
  no kernel engine is supplied (Phase 7).

`tests/test_fusion_router_persistence.py` and
`tests/test_fusion_router_kernel_wiring.py` cover the Phase 7
persistence + runner adapter (shared between `fusion-router` and
`mad-dog`).

## File Layout

The Mad Dog Mode alias lives in:

* `loopos/cli/commands/mad_dog.py` -- the Typer command.
* `loopos/fusion_router/cli.py` -- the CLI helpers (shared with
  `fusion-router`).
* `loopos/fusion_router/router.py` -- the `FusionRouter.mad_dog_trigger`
  factory.

The actual planning is performed by `loopos.fusion_router`; Mad
Dog Mode is a thin wrapper that pins the trigger shape.