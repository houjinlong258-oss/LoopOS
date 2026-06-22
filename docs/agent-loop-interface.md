# Agent Loop Interface

ALI is the Agent Loop Interface. ACI defines how an agent submits a governed command; ALI defines
how commands participate in a governed Kernel loop.

## Loop actions

ALI exposes the semantic outcomes already represented by the convergence and scheduler contracts:

```text
continue
repair
replan
ask_user
wait_approval
halt_success
halt_failure
halt_blocked
```

An ALI step consumes the current goal and state, one validated instruction, policy and capability
decisions, a structured observation, the latest evaluation, and accumulated progress. It emits a
convergence decision and a Scheduler-owned transition.

## Boundary rules

1. A plan hint cannot override a real failed observation.
2. A syscall failure cannot bypass evaluation or the Scheduler.
3. Approval and policy denial remain first-class loop outcomes.
4. Repeated failure, repeated action, and no-progress counts persist per run.
5. Every ACI-to-ALI handoff is traceable.
6. Replay consumes Trace only and never executes the syscall again.

## Relationship to the runtime

`KernelLoopEngine` is the v0.1 ALI implementation. `EvaluationSource` converts runtime evidence,
`ProgressAccumulatorSnapshot` preserves cross-step signals, `ConvergenceEngine` proposes the loop
action, and `LoopScheduler` remains the final arbiter.

Future language implementations must preserve these JSON-compatible contracts rather than inventing
parallel semantics.
