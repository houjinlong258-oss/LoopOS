# Kernel Hardening

## Why this exists

Agent execution needs explicit lifecycle control, invariant checks, recovery points, and bounded
failure handling. Kernel hardening makes these controls inspectable instead of implicit.

## Core models

`KernelLifecycle` controls boot, run, stop, and failure phases. `KernelInvariantChecker` validates
cross-kernel guarantees. `KernelCheckpoint` stores replay-safe state. `Supervisor` applies restart
budgets and escalation rules. `KernelSignal` carries approval, cancel, timeout, and shutdown input.

## CLI usage

```bash
loopos kernel inspect --data-dir .loopos
loopos kernel invariants
loopos trace RUN_ID --show-ail --show-policy
loopos step replay RUN_ID 3
```

Example output:

```text
run status: waiting_approval
checkpoint: available
invariants: 15 passed, 0 failed
```

## Safety boundaries

Replay reconstructs recorded state and never invokes side-effecting adapters. High-risk actions
require both a policy decision and a checkpoint before execution.

## Current limitations

The supervisor is process-local and deterministic. Distributed scheduling and remote checkpoint
stores are outside the Founding Preview.
