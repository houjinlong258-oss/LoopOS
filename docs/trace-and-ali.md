# Trace <-> ALI Bridge (Phase 5)

This document describes the Phase 5 trace bridge that persists
:class:`AgentLoopEventRecord` values into the existing
:class:`loopos.kernel.trace.TraceStore` so the ACI -> Kernel ->
ALI loop is replayable and auditable.

## Scope

Phase 5 wires ALI events into the kernel trace runtime. It does
**not** replace the trace runtime; it does **not** introduce a
new store, wire format, or event type. The bridge translates ALI
event records into the trace shape the runtime already accepts.

What this phase does **not** do:

- It does not rewrite `KernelLoopEngine`.
- It does not replace the existing trace runtime.
- It does not bypass Policy OS, the Syscall Router, or the
  existing trace / run_manager behavior.
- It does not introduce a new loop engine, transport, or
  runtime.
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
  |    -> PolicyEngine.evaluate(...)         (Policy OS, no bypass)
  |    -> SyscallRouter.dispatch(...)        (Syscall Router, no bypass)
  |    -> AgentCommandResult
  |
  |  consume_aci_result(session, result)
  |    -> session.attach_aci_result(...)
  |    -> apply_event(session, event, payload)  x N
  |    -> records: list[AgentLoopEventRecord]
  |
  |  _record_aci_outcome(result)
  |    -> run.metadata["aci_outcomes"].append({...})
  |
  |  _persist_ali_events(session, records=..., result=...)
  |    -> audit = build from AgentCommandResult + RunRecord
  |    -> persist_session_events(session, ..., audit=..., records=records)
  |       -> for each record: trace_store.append(kind="signal",
  |                                            type="ali.event",
  |                                            payload=...)
  |
  v
TraceStore (existing)
  events.jsonl, append-only, deterministic JSON per line
```

The bridge is the only place that touches
:class:`TraceStore` directly for ALI events; the kernel hook is
a thin pass-through.

## Event schema

Each ALI event becomes a :class:`loopos.kernel.trace.TraceEvent`
with:

| field | value |
|---|---|
| `kind` | `"signal"` (canonical kernel trace kind) |
| `type` | `"ali.event"` (discriminator for replay) |
| `run_id` | the kernel run id that owns the session |
| `step` | the kernel step at persist time |
| `payload` | ordered dict: seq, event, reason_code, next_state, created_at, aci_command_id, aci_goal_id, aci_status, aci_success, reason_codes, messages, trace_id, syscall_id, provider_id, provider_source, policy_decision, convergence_reason_code, kernel_run_id, kernel_step, kernel_status, kernel_phase |

The payload key order is stable (defined by
`_PAYLOAD_KEY_ORDER` in `loopos/trace/ali_bridge.py`). Extra keys
from a future ALI event are appended in alphabetical order so the
JSON serialisation stays deterministic.

The `payload` keeps the FSM-side fields (`seq`, `event`,
`reason_code`, `next_state`, `created_at`) and the audit-trail
fields (`aci_command_id`, `aci_goal_id`, `aci_status`,
`aci_success`, `reason_codes`, `messages`, `trace_id`,
`syscall_id`, `provider_id`, `provider_source`, `policy_decision`,
`convergence_reason_code`). The kernel-side fields (`kernel_run_id`,
`kernel_step`, `kernel_status`, `kernel_phase`) allow trace
consumers to correlate ALI events with the existing kernel
decision trace.

## Replay

```python
from loopos.trace.ali_bridge import replay_session_events

replayed = replay_session_events(trace_store, run_id=run_id)
# replayed is a list of dicts ordered by seq.
# Each dict has the canonical key order from _PAYLOAD_KEY_ORDER.
```

The replay reads the existing trace store, filters on
`type == "ali.event"`, and returns the records in `seq` order.
A replay consumer can rebuild an :class:`AgentLoopSession` from
scratch by re-applying the events through the FSM, or surface the
audit trail (command_id, trace_id, syscall_id, provider_id,
reason_codes, policy_decision, convergence_reason_code) without
re-running the policy engine.

## Dry-run behavior

A dry-run ACI result (`AgentCommand.dry_run=True`) produces:

| side | outcome |
|---|---|
| Filesystem | untouched (no side-effecting syscall ran) |
| Provider registry | metadata-only (no live API call) |
| Trace store | one `ali.event` (`progress_updated`) |
| Session state | `RUNNING` |

The single `ali.event` is **trace evidence**, not a side effect.
The runner's `status="dry_run"` propagates through the audit
payload so trace consumers can distinguish dry-run events from
real-execution events.

## Policy-denial trace proof

A policy denial (`rm -rf /` or any L5 trigger) produces:

| side | outcome |
|---|---|
| Filesystem | untouched (no syscall ran) |
| Trace store | one `ali.event` (`policy_denied` -> `HALTED_BLOCKED`) |
| Audit payload | `aci_status="blocked"`, `aci_success=False`, `reason_codes=["policy_denied", ...]`, `policy_decision.allowed=False` |
| Session state | `HALTED_BLOCKED` |

The kernel never invents a successful result; the trace event
records the policy verdict verbatim. A reviewer can replay the
event and read the audit fields to understand the denial.

## Repair / replan / unsupported trace proof

| ACI status | extra hint | ALI event(s) | session state |
|---|---|---|---|
| `failed` (repairable) | `evaluation.repairable=True` | `progress_updated`, `syscall_failed` | `REPAIRING` |
| `failed` (no_progress) | `progress.no_progress=True` | `progress_updated`, `convergence_replan` | `REPLANNING` |
| `failed` (non-repairable) | | `progress_updated`, `convergence_halt_failure` | `HALTED_FAILURE` |
| `unsupported` | | `convergence_halt_failure` | `HALTED_FAILURE` |

Unsupported kinds do not crash the bridge; they emit a single
`ali.event` whose audit payload carries `aci_status="unsupported"`
and `reason_codes=["unsupported_command_kind", ...]`.

## Metadata propagation

The audit payload is built from
:class:`AgentCommandResult` and the most recent
:class:`RunRecord`. Specifically:

| audit field | source |
|---|---|
| `aci_command_id` | `result.command_id` |
| `aci_goal_id` | `result.goal_id` |
| `aci_status` | `result.status` |
| `aci_success` | `result.success` |
| `reason_codes` | `result.reason_codes` |
| `messages` | `result.messages` |
| `trace_id` | `result.trace_id` |
| `syscall_id` | `result.metadata["syscall_id"]` |
| `provider_id` | `result.resolved_provider.provider_id` |
| `provider_source` | `result.resolved_provider.source` |
| `policy_decision` | `result.policy_decision_summary` (decision_id, allowed, action, safety_level, reason_codes) |
| `convergence_reason_code` | `result.convergence.reason_code` |
| `kernel_run_id` | `run.run_id` |
| `kernel_step` | `run.step` |
| `kernel_status` | `run.status` |
| `kernel_phase` | `run.phase` |

All fields survive a roundtrip through the trace store.

## Phase 4 backward compatibility

The Phase 4 contract `run.metadata["aci_outcomes"]` remains
intact. The Phase 5 bridge does not change the shape of the
outcome entries; it only adds a complementary trace stream on
top of it.

Verified by `KernelIntegrationRegressionTests.test_run_metadata_aci_outcomes_unchanged_after_bridge`.

## Safety invariants

- No push.
- No tag mutation.
- No dist mutation.
- No release-evidence mutation.
- `loopos/model_kernel/*` diff vs v0.1.0: empty.
- The trace runtime is **not replaced**; the bridge is a thin
  wrapper over the existing `TraceStore`.
- Policy OS, Syscall Router, and Trace remain the single source
  of truth.
- No live provider API call (monkey-patch test asserts this).
- No direct subprocess / shell bypass.
- Dry-run trace events are observation-only; they never produce
  filesystem / provider / syscall side effects.
- Unsupported ACI kinds emit failure trace evidence rather than
  crashing.
- `run.metadata["aci_outcomes"]` shape is unchanged.

## Tests

`tests/test_ali_trace_bridge.py` (16 tests) covers:

1. `to_event_stream` returns ordered deterministic events.
2. `to_event_stream` of an empty session is `[]`.
3. Completed ACI persists two `ali.event` records
   (`progress_updated`, `syscall_completed`).
4. Policy-denied ACI persists a single `ali.event`
   (`policy_denied` -> `HALTED_BLOCKED`).
5. Approval-required ACI persists a single `ali.event`
   (`approval_required` -> `WAITING_APPROVAL`).
6. Repairable failure persists an `ali.event`
   (`syscall_failed` -> `REPAIRING`).
7. No-progress failure persists an `ali.event`
   (`convergence_replan` -> `REPLANNING`).
8. Unsupported ACI persists a single `ali.event`
   (`convergence_halt_failure` -> `HALTED_FAILURE`).
9. `trace_id` / `syscall_id` / `provider_id` survive a
   roundtrip through the trace store.
10. Replay reconstructs the ordered event sequence.
11. Replay filters non-ALI events.
12. Trace payload serialisation is bytewise stable.
13. Replay preserves the canonical key order.
14. Dry-run ACI persists trace but produces no side effects.
15. The bridge does not call any live provider API.
16. The Phase 4 `run.metadata["aci_outcomes"]` contract is
    unchanged after the bridge is wired.

Existing tests continue to pass:

- `tests/test_kernel_aci_ali_integration.py` (Phase 4)
- `tests/test_kernel_convergence_integration.py`
- `tests/test_policy_os.py`
- `tests/test_aci_*.py`
- `tests/test_ali_*.py`

## File-level changes

| file | change | LOC |
|---|---|---|
| `loopos/trace/__init__.py` | new | +12 |
| `loopos/trace/ali_bridge.py` | new | +219 |
| `loopos/ali/session.py` | extended | +34 |
| `loopos/ali/__init__.py` | extended | +3 |
| `loopos/kernel/loop_engine.py` | extended | +91 / -3 |
| `tests/test_ali_trace_bridge.py` | new | +559 |

`loopos/kernel/models.py` and `loopos/kernel/__init__.py` are
unchanged.

## What this phase does not address

- The bridge does not bridge `AgentLoopSession` events into the
  broader `loopos.memory` subsystem; that is a separate task.
- The bridge does not introduce an ALI-level replay engine; the
  replay function returns the ordered stream and a future
  consumer can re-apply the events through the FSM.
- The bridge does not change the existing
  `TraceEvent.type` / `kind` mapping; ALI events use
  `kind="signal"` / `type="ali.event"`. A future phase may add
  a dedicated `kind="ali_event"` if the kernel trace runtime is
  extended.