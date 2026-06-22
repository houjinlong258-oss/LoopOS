# Kernel <-> ACI <-> ALI Integration (Phase 4)

This document describes the Phase 4 minimal integration that closes
the runtime loop between `KernelLoopEngine`, the Agent Command
Interface (ACI), and the Agent Loop Interface (ALI).

## Scope

Phase 4 wires the already-stable ACI runner and ALI FSM to the
kernel without rewriting either layer. The integration is **opt-in**:
existing `KernelLoopEngine.run()` / `KernelLoopEngine.resume()`
paths continue to work unchanged; callers that want to drive an
`AgentLoopSession` from a real `AgentCommandResult` use the new
`KernelLoopEngine.submit_agent_command(...)` method.

What this phase does **not** do:

- It does not rewrite `KernelLoopEngine`.
- It does not replace the convergence / scheduler / progress
  accumulator / evaluation source pipeline.
- It does not bypass Policy OS, the Syscall Router, or the Trace
  store.
- It does not introduce a new loop engine, transport, or runtime.
- It does not call live provider APIs.

## End-to-end flow

```text
caller
  |
  |  AgentCommand
  v
KernelLoopEngine.submit_agent_command(command, session)
  |
  |  CommandRunner.run(command)
  |    -> PolicyEngine.evaluate(...)        (Policy OS, no bypass)
  |    -> SyscallRouter.dispatch(...)       (Syscall Router, no bypass)
  |    -> AgentCommandResult
  |
  |  consume_aci_result(session, result)
  |    -> session.attach_aci_result(...)
  |    -> apply_event(session, event, payload)  x N
  |
  |  _record_aci_outcome(result)
  |    -> run.metadata["aci_outcomes"].append({...})
  |    -> runtime.run_manager.save(run)
  |
  v
ALI session (RUNNING / REPAIRING / REPLANNING /
            WAITING_APPROVAL / HALTED_*)
```

## Public surface

```python
from loopos.kernel import KernelLoopEngine
from loopos.aci import AgentCommand
from loopos.ali import create_session, apply_event

engine = KernelLoopEngine(runtime)
runner = engine._default_aci_runner()        # uses runtime.policy_engine
                                              # and runtime.syscall_router
session = create_session("goal-p4-1")
apply_event(session, "goal_submitted")
apply_event(session, "command_submitted")

cmd = AgentCommand(goal_id="goal-p4-1",
                   purpose="phase 4 integration",
                   kind="terminal.exec",
                   command="echo hello")

result = engine.submit_agent_command(cmd, session)
# result.status in {"completed", "blocked", "failed",
#                   "approval_required", "dry_run", "unsupported"}
# session.state in {"RUNNING", "REPAIRING", "REPLANNING",
#                   "WAITING_APPROVAL", "HALTED_BLOCKED",
#                   "HALTED_FAILURE"}
```

The runner can also be supplied by the caller when the kernel's
default router does not match the test scenario (e.g. the kernel
router does not auto-approve medium-risk commands, while a test
runner can):

```python
result = engine.submit_agent_command(
    cmd, session,
    aci_runner=custom_runner,
    fsm=custom_fsm,                       # optional FSM override
)
```

## State transition matrix

| ACI result                 | extra hints                  | ALI session state     |
|----------------------------|------------------------------|-----------------------|
| `completed` (dry_run=False)|                              | `RUNNING`             |
| `completed` (dry_run=True) |                              | `RUNNING`             |
| `dry_run`                  |                              | `RUNNING`             |
| `blocked` (policy denial)  |                              | `HALTED_BLOCKED`      |
| `blocked` (validation)     |                              | `HALTED_BLOCKED`      |
| `approval_required`        |                              | `WAITING_APPROVAL`    |
| `failed` (repairable=True) | `evaluation.repairable=True` | `REPAIRING`           |
| `failed` (no_progress=True)| `progress.no_progress=True`  | `REPLANNING`          |
| `failed` (non-repairable)  |                              | `HALTED_FAILURE`      |
| `unsupported`              |                              | `HALTED_FAILURE`      |

The mapping is the same data-only table Phase 3 pinned in
`loopos.ali.aci_consumption._desired_event_sequence`. Phase 4 does
not introduce a new mapping; it composes the existing one.

## Policy-denial behavior

A policy denial produces an `AgentCommandResult` with
`status="blocked"` and a `policy_denied` (or `terminal_rm_rf_denied`,
`network_access_denied`, `remote_script_pipe_denied`,
`git_tag_denied`, `release_evidence_mutation_denied`) reason code.
`consume_aci_result` classifies this as a policy denial via
`loopos.ali.aci_consumption._is_policy_denial` and emits
`policy_denied` rather than `convergence_halt_blocked`. The
session terminates at `HALTED_BLOCKED`; the kernel run record
carries the structured reason code under
`run.metadata["aci_outcomes"][-1]["reason_codes"]`.

L5 denials (`safety_level="L5"`) flow through the same path; the
runner never invents a successful result, and the kernel never
overrides the verdict.

## Repair / replan behavior

A failed `AgentCommandResult` whose `evaluation.repairable=True`
drives the session to `REPAIRING`. The existing kernel repair
scheduling semantics (see `loopos.kernel.scheduler.LoopScheduler`)
remain intact; this phase does not introduce a parallel repair
path. The session's `REPAIRING` state is the ALI-side mirror of the
kernel's repair decision.

A failed `AgentCommandResult` whose `progress.no_progress=True`
drives the session to `REPLANNING`. The existing kernel replan
scheduling semantics remain intact.

A failed `AgentCommandResult` that is neither repairable nor
no-progress drives the session to `HALTED_FAILURE` via
`convergence_halt_failure`.

## Trace / syscall / provider metadata propagation

After `submit_agent_command` returns, the most recent `RunRecord`
in the runtime's run manager has its `metadata["aci_outcomes"]`
list appended with a compact verdict:

```python
{
    "command_id": str,
    "goal_id": str,
    "status": str,                  # AgentCommandResult.status
    "success": bool,                # AgentCommandResult.success
    "reason_codes": list[str],
    "trace_id": str | None,         # AgentCommandResult.trace_id
    "syscall_id": str | None,       # AgentCommandResult.metadata["syscall_id"]
    "provider_id": str | None,      # AgentCommandResult.resolved_provider.provider_id
    "blocked_reason": str | None,
    "requires_approval": bool,
    "dry_run": bool,
}
```

The session additionally carries the same metadata on
`session.aci_refs[-1].metadata` (set by `consume_aci_result`'s
audit-reference attachment), so the integration does not lose the
audit trail even if the kernel run record is later reloaded.

The kernel never re-runs the policy engine to read these values;
the existing decision path can read them directly from
`run.metadata["aci_outcomes"]`.

## Safety invariants

Phase 4 satisfies the kernel-loop safety rules:

- `runtime.policy_engine` is the single source of truth for policy
  decisions. The integration passes it through to
  `CommandRunner(policy_engine=...)`.
- `runtime.syscall_router` is the only side-effecting path. The
  runner's `_dispatch` calls `runtime.syscall_router.dispatch(...)`.
- `runtime.trace_store` continues to receive every transition. The
  integration does not write to the trace directly; `_record_aci_outcome`
  uses `run_manager.save(...)` to persist the audit metadata, and the
  existing `_transition` / `_trace` helpers keep emitting events.
- `EvaluationSource`, `ProgressAccumulator`, and `ConvergenceEngine`
  are unchanged.
- The runner never spawns a subprocess directly.
- The runner never calls a live provider API (it only reads the
  metadata-only `loopos.providers.ProviderRegistry`).
- A `dry_run=True` AgentCommand produces a result with
  `dry_run=True` and never touches the filesystem (verified by the
  Phase 4 test suite).
- An `unsupported` kind is handled gracefully: `consume_aci_result`
  emits `convergence_halt_failure` rather than crashing.

## Tests

`tests/test_kernel_aci_ali_integration.py` (15 tests) covers:

1. Successful ACI result leaves ALI session RUNNING.
2. `progress_updated` + `syscall_completed` events are emitted on
   the session.
3. Policy-denied result moves ALI to HALTED_BLOCKED.
4. L5 (`terminal_rm_rf_denied`) denial still ends in HALTED_BLOCKED.
5. Approval-required result moves ALI to WAITING_APPROVAL.
6. Repairable failure moves ALI to REPAIRING.
7. No-progress failure moves ALI to REPLANNING.
8. Non-repairable failure moves ALI to HALTED_FAILURE.
9. Unsupported ACI kind moves ALI to HALTED_FAILURE without crashing.
10. Trace / syscall / provider metadata propagates to
    `run.metadata["aci_outcomes"]`.
11. ACI audit reference is attached on the session.
12. Dry-run ACI result does not produce side effects.
13. Integration does not call any live provider API (monkey-patches
    `socket.socket` and `urllib.request.urlopen`).
14. Default runner uses the kernel's policy engine + syscall router.
15. Existing `KernelLoopEngine.run()` path is unchanged.

Existing tests must continue to pass:

- `tests/test_kernel_convergence_integration.py`
- `tests/test_policy_os.py`
- `tests/test_aci_*.py`
- `tests/test_ali_*.py`
- `tests/test_provider_registry.py`
- `tests/test_provider_model_kernel_consistency.py`
- `tests/test_v0_2_agent_os_kernel_integration.py`

## What this phase does not address

- The integration does not yet bridge `AgentLoopSession` events into
  `loopos.trace`; that is a separate persistence task (proposed in a
  later phase). Today, events live on `session.events` and the audit
  references live on `session.aci_refs`.
- `KernelLoopEngine` does not own an `AgentLoopSession`; the caller
  creates one and passes it in. A future phase may add a
  per-run-session registry so the engine can auto-recover the
  session on `resume()`.
- The kernel convergence handoff is still driven by the existing
  AIL-instruction pipeline. Replacing the convergence path with an
  ALI-driven path is out of scope.

## File-level changes

| file | change | LOC delta |
|---|---|---|
| `loopos/kernel/loop_engine.py` | extended | +192 / -1 |
| `tests/test_kernel_aci_ali_integration.py` | new | +458 |

`loopos/kernel/models.py` and `loopos/kernel/__init__.py` are
unchanged.