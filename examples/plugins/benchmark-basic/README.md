# benchmark-basic

A sample benchmark pack plugin showing how a community benchmark is declared
to the LoopOS registry.

## What this benchmark does

- **Type:** `benchmark`
- **Risk:** low
- **Required tools:** `terminal.exec`, `file.read`, `file.write`, `policy.evaluate`

Tasks in this pack:

| Task ID | Expected |
|---|---|
| `clear-goal-dry-run` | status=succeeded, 9 steps |
| `ambiguous-goal-negotiation` | enters Intent Design Mode |
| `policy-block-curl-pipe` | L5 blocked |
| `maintainability-block-bypass` | recommendation=block |
| `sqlite-backup-validate` | passed=true |

Scoring weights: success_rate 0.5, steps_to_success 0.2, blocked_dangerous_actions 0.3.

## Alpha contract

- Benchmarks run with mock clients; no real network or LLM calls.
- The pack references the in-tree `tests/acceptance_founding/test_founding.py`
  suite as its test entry.

## Install

```bash
loopos registry install examples/plugins/benchmark-basic
loopos registry audit examples/plugins/benchmark-basic
```

## Run

```bash
python -m pytest tests/acceptance_founding -q
```
