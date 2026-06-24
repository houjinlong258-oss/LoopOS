# Fusion / Mad Dog Planning

A walkthrough that exercises the planning-only Fusion Router and
its `mad-dog` alias, and shows the planning-vs-execution boundary
in action.

## Goal

Demonstrate that the Fusion Router and `mad-dog` are
**planning-only** by default — they emit a plan / verdict, never
execute anything, never spend budget, never bypass Policy OS.

## Command

```bash
# A normal fusion plan
python -m loopos.cli.app fusion-router plan task.json --json

# The same plan, but with the user-force mad-dog overrides
python -m loopos.cli.app mad-dog plan task.json --severity critical --json
```

`task.json` is a small JSON file with a goal description. See
`tests/fixtures/` for an example.

## Expected output (abridged)

```json
{
  "fusion_id": "...",
  "mode": "single",
  "decision": { "kind": "single_agent" },
  "verdict": "allow",
  "reason_codes": [],
  "evidence": [...],
  "aci_recommendations": [...]
}
```

For the `mad-dog` invocation the same shape is returned but with
`mode: "mad_dog"`, `severity: "critical"`, and the trigger
overrides applied.

## What happened internally

1. The CLI dispatched to
   `loopos.cli.commands.fusion_router.fusion_router_command` (or
   `mad_dog_command` for the alias).
2. The router gathered the goal and the evidence, scored the
   trigger, and assigned roles from the metadata-only
   `loopos.providers` registry.
3. The router emitted a `FusionPlan` and persisted it via the
   local `FusionPlanStore` so `fusion-router status` and
   `mad-dog status` can read it back later.
4. The plan is *not* executed. It is a *recommendation* — the
   caller decides whether to route the plan through the
   governed Kernel / ACI / Syscall Router, which is the only
   path that can execute it.

## Safety note

Both `fusion-router` and `mad-dog` are **planning-only** in v0.3.
They cannot:

- Spend budget on their own.
- Bypass Policy OS.
- Bypass the Syscall Router.
- Execute anything directly.

The `mad-dog` alias is the user-force mode; it raises the
default severity to `critical` and tags the trigger as
`explicit_user_request`. It is still planning-only.

In v0.4 (deferred) the planning boundary may move and the
Fusion Runner may route the recommended ACI commands through the
Kernel automatically. Until then, the only path to *execute* a
Fusion plan is to wire it into a `KernelLoopEngine` and route the
ACI commands through `submit_agent_command`.

See [`docs/v0-3-non-goals.md`](../v0-3-non-goals.md) for the
items v0.3 deliberately does not do.
