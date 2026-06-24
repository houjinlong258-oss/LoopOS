# Workbench Tour

A longer walkthrough that explores each of the eight v0.3
panels and shows how to read them.

## Goal

Get familiar with the eight required v0.3 panels so you know
which one to look at when something does not behave as expected.

## Command

```bash
python -m loopos.cli.app workbench --dry-run --json | python -m json.tool
```

Pipe through `python -m json.tool` to make the structure easy to
read.

## The eight panels

| Panel           | What it tells you                                                            |
| --------------- | ---------------------------------------------------------------------------- |
| `goal`          | The goal the Workbench is reasoning about (title, intent, acceptance, risk).|
| `agent`         | Which Agent Kernel Adapter is wired in and what its authority claims are.    |
| `policy`        | The active policy pack and the most recent policy decision for this goal.    |
| `aci`           | The Agent Command Interface commands the Workbench would dispatch.           |
| `ali`           | The Agent Loop Interface transitions the work would drive.                   |
| `trace-replay`  | The trace / replay handles the workbench would record; replay rebuilds state.|
| `fusion`        | Whether the Fusion Router would escalate and to which mode (`single`/`mad_dog` etc.).|
| `readiness`     | The current v0.3 readiness check results (mirrors `loopos readiness check`). |

## Expected output (abridged)

```json
{
  "goal": { "title": "...", "intent": "...", "risk": "low" },
  "agent": { "adapter_id": "mock", "authority_claims": ["read"] },
  "policy": { "pack": "safe-default", "decision": "allow", "reason_codes": [] },
  "aci": { "commands": [] },
  "ali": { "transitions": [] },
  "trace-replay": { "replayable": true },
  "fusion": { "mode": "single" },
  "readiness": { "status": "pass", "hard_fail_count": 0 }
}
```

The exact shape is governed by the Workbench schema in
`loopos/product/`; the panel keys above are the v0.3 contract.

## What happened internally

The Workbench is built on three layers:

1. `Workbench.build_context()` collects inputs (goal, adapter,
   policy, trace, etc.) into a `WorkbenchContext`.
2. `build_panels_from_context()` projects the context into the
   eight required panels.
3. `render_json` (or `render_plain`) emits the human or machine
   form.

In `--dry-run` mode, no real provider call, no real shell exec,
no real file write happens. The Workbench is a *projector*; the
real action would flow through the governed Kernel / ACI /
Syscall Router if you flipped the dry-run flag.

## Safety note

The Workbench is the only user-facing v0.3 surface. It is
deliberately a *viewer* and a *projector* — it never owns
authority. Authority lives in the Policy OS, the Syscall Router,
and the Fusion Router / OpenGod. The Workbench is where you go
to *see* what would happen, not to *make* it happen.

See [`docs/architecture-v0-3.md`](../architecture-v0-3.md) for
the full module map.
