# Governed Agent Loop

## Definition

A governed agent loop repeatedly acts, observes, evaluates, and converges under explicit policy,
capability, trace, and outcome contracts. It keeps the useful persistence of a shell auto-loop
without giving an agent unlimited authority.

## Why shell loops work

A simple `while true` loop is effective because it preserves momentum, feeds the previous result
back into the next attempt, and stops when a visible condition is met. It is also fragile: text is
treated as state, stop conditions are easy to spoof, retries are unbounded, and tools have no
common permission, trace, rollback, or quality contract.

## LoopOS upgrade

| Shell auto-loop | LoopOS runtime |
|---|---|
| `PROMPT.md` | `GoalSpec` and outcome contract |
| `while true` | bounded `KernelLoopEngine` |
| `grep` stop hook | typed `ConvergenceEngine` evidence |
| `output.txt` | `Observation` and `TraceEvent` |
| fixed `sleep` | Scheduler and bounded backoff |
| ambient shell authority | Policy OS and capability boundary |
| completion only | Maintainability and Anti-Bloat review |
| no release proof | Release Readiness and artifact verification |

The Scheduler remains the final transition authority. A failed syscall cannot jump directly to a
success or halt state; it must become evaluation and progress evidence before convergence decides
what signal the Scheduler receives.

## Runtime contract

```text
GoalSpec -> Context -> Policy -> AIL instruction -> Syscall
         -> Observation -> Evaluation -> Progress -> Convergence
         -> Scheduler -> Trace -> continue, repair, replan, ask, approve, or halt
```

This is not an invitation to run forever. Every loop is bounded, every external action is governed,
and replay never repeats side effects.

> They built a loop. We built the OS for the loop.
