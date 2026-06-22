# Agent Loop Interface (ALI) — LoopOS v0.2

> **ALI 是 LoopOS Run 的状态机消费者。** 它把 ACI 的每次
> :class:`AgentCommandResult` 翻译为 FSM 事件序列，让一个 LoopOS
> Run 在 ``CREATED → READY → RUNNING → (REPAIRING / REPLANNING /
> WAITING_APPROVAL / ASKING_USER) → HALTED_*`` 之间收敛。

> **Design note (v0.1):** ALI defines how an agent submits a
> governed command (via ACI) and how commands participate in a
> governed Kernel loop. The boundary rules below remain in force for
> every phase; the Phase 3 consumer makes them enforceable in typed
> Python without modifying the kernel loop engine.

---

## 1. Definition

ALI = Agent Loop Interface. The bounded, replayable finite-state
machine that drives an agent run inside LoopOS. ALI owns:

* a session ID,
* a goal ID,
* the current FSM state,
* the bounded event log (replayable),
* the audit references to ACI results that drove each transition.

ALI does not import ``loopos.kernel.*`` or touch ``KernelLoopEngine``
directly. The Phase 4 integration goes the other way:
``KernelLoopEngine.submit_agent_command(...)`` calls
:func:`loopos.ali.session.consume_aci_result` to drive an
:class:`AgentLoopSession` from a real :class:`AgentCommandResult`.
The one-way dependency is preserved (kernel -> ALI -> ACI), and the
existing ``run`` / ``resume`` / convergence paths are untouched.
See ``docs/kernel-aci-ali-integration.md`` for the integration
contract.

The Phase 3 consumer in
:func:`loopos.ali.session.consume_aci_result` remains the only ALI
entry point that depends on ``loopos.aci`` (one-way: ALI depends on
ACI, not the reverse).

### Loop actions

ALI exposes the semantic outcomes already represented by the
convergence and scheduler contracts:

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

### Boundary rules (carry-over from v0.1)

1. A plan hint cannot override a real failed observation.
2. A syscall failure cannot bypass evaluation or the Scheduler.
3. Approval and policy denial remain first-class loop outcomes.
4. Repeated failure, repeated action, and no-progress counts persist
   per run.

These rules are enforced by the Phase 3 transition table: a blocked
or failed result always emits the ``policy_denied`` /
``convergence_halt_*`` / ``syscall_failed`` event; a completed result
cannot bypass the next-step ``progress_updated`` audit record.

---

## 2. States and events

The FSM is defined entirely by data: a transition table lives in
``loopos/ali/fsm.py``. New states and events are added by appending
rows, not by rewriting an ``if/else`` maze.

### States

```text
CREATED          initial state after create_session()
READY            after goal_submitted
RUNNING          after command_submitted; the default "in-flight" state
WAITING_APPROVAL after approval_required; resumes on policy_allowed
REPAIRING        after syscall_failed (a repairable failure)
REPLANNING       after convergence_replan or repeated repair failure
ASKING_USER      after convergence_ask
HALTED_SUCCESS   terminal; reached via convergence_halt_success
HALTED_FAILURE   terminal; reached via convergence_halt_failure
HALTED_BLOCKED   terminal; reached via policy_denied or convergence_halt_blocked
```

### Events emitted by :func:`consume_aci_result`

```text
progress_updated            emitted on every successful consume (RUNNING only)
syscall_completed           emitted on a completed syscall
syscall_failed              emitted on a repairable failure (-> REPAIRING)
policy_denied               emitted on a policy-blocked result (-> HALTED_BLOCKED)
approval_required           emitted on approval-needed (-> WAITING_APPROVAL)
convergence_replan          emitted on a no-progress failure (-> REPLANNING)
convergence_halt_blocked    emitted on a structural block (-> HALTED_BLOCKED)
convergence_halt_failure    emitted on a non-repairable failure or
                            unsupported kind (-> HALTED_FAILURE)
```

The full taxonomy is in ``AgentLoopEvent`` (see
``loopos/ali/models.py``). Events that the consumer does NOT emit
(``goal_submitted``, ``command_submitted``, ``observation_recorded``,
``evaluation_applied``, ``convergence_continue``, etc.) are emitted by
the kernel loop engine in Phase 4+.

---

## 3. ACI -> ALI mapping

The mapping is implemented as a small data table inside
:func:`consume_aci_result` and consumed through the FSM transition
table. No ACI status triggers an ``if/else`` branch in the consumer.

| ACI ``status`` | extra hints | emitted ALI event sequence | FSM transition(s) |
|---|---|---|---|
| ``completed`` | ``dry_run=False`` | ``progress_updated``, ``syscall_completed`` | RUNNING -> RUNNING -> RUNNING |
| ``completed`` | ``dry_run=True`` | ``progress_updated`` | RUNNING -> RUNNING |
| ``dry_run`` | any | ``progress_updated`` | RUNNING -> RUNNING |
| ``blocked`` | policy denial (``policy_denied`` / ``terminal_rm_rf_denied`` / ...) | ``policy_denied`` | RUNNING -> HALTED_BLOCKED |
| ``blocked`` | structural / validation block | ``convergence_halt_blocked`` | RUNNING -> HALTED_BLOCKED |
| ``approval_required`` | any | ``approval_required`` | RUNNING -> WAITING_APPROVAL |
| ``failed`` | ``EvaluationSummary.repairable=True`` | ``progress_updated``, ``syscall_failed`` | RUNNING -> RUNNING -> REPAIRING |
| ``failed`` | ``ProgressSummary.no_progress=True`` | ``progress_updated``, ``convergence_replan`` | RUNNING -> RUNNING -> REPLANNING |
| ``failed`` | non-repairable | ``progress_updated``, ``convergence_halt_failure`` | RUNNING -> RUNNING -> HALTED_FAILURE |
| ``unsupported`` | any | ``convergence_halt_failure`` | RUNNING -> HALTED_FAILURE |

The ``progress_updated`` event is only valid from ``RUNNING`` in the
transition table. When the consumer is invoked from ``REPAIRING`` or
``REPLANNING`` (a typical re-consume after a previous failure), the
``progress_updated`` prefix is filtered out by
:func:`_filter_for_state` so the FSM never sees an invalid transition.

---

## 4. State transition examples

### 4.1 Successful run

```text
CREATED
   | goal_submitted
   v
READY
   | command_submitted
   v
RUNNING  -- consume completed result (dry_run=False)
   | progress_updated
   | syscall_completed
   v
RUNNING
   ... (next command) ...
```

### 4.2 Policy-blocked command

```text
RUNNING  -- consume blocked result (policy_denied reason)
   | policy_denied
   v
HALTED_BLOCKED   (terminal)
```

### 4.3 Repairable failure with subsequent success

```text
RUNNING  -- consume failed result (repairable=True)
   | progress_updated
   | syscall_failed
   v
REPAIRING  -- (agent submits a new command)
   | command_submitted
   v
RUNNING  -- consume completed result
   | progress_updated
   | syscall_completed
   v
RUNNING
```

### 4.4 Repeated failure that escalates to replan

```text
RUNNING  -- consume failed result (repairable=True)
   | progress_updated
   | syscall_failed
   v
REPAIRING  -- consume failed result (repairable=True) from REPAIRING
   | syscall_failed         (progress_updated is invalid in REPAIRING,
                             filtered out by _filter_for_state)
   v
REPLANNING
   | command_submitted
   v
RUNNING
```

### 4.5 Unsupported kind

```text
RUNNING  -- consume unsupported result
   | convergence_halt_failure
   v
HALTED_FAILURE   (terminal, reason_code=unsupported_command_kind)
```

---

## 5. Reason code propagation

The :class:`AgentCommandResult.reason_codes` list is preserved end to
end:

* Stored on the audit reference (via
  :meth:`AgentLoopSession.attach_aci_result`) under
  ``metadata.reason_codes``.
* Carried in every event payload the consumer emits (key
  ``reason_codes``).
* Forwarded by the FSM transition table to the
  :class:`AgentLoopEventRecord.reason_code` field on the audit log
  (the FSM's row reason_code, not the ACI reason code).

This separation is deliberate: the **ALI row reason code** identifies
the *transition* (e.g. ``ali.syscall_failed_repairable``), while the
**ACI reason codes** identify the *why* (e.g. ``provider_not_found``,
``terminal_rm_rf_denied``). Review artifacts and readiness proofs
read both.

---

## 6. Trace / syscall / provider metadata propagation

Each event payload carries a structured view of the audit trail:

```python
{
    "command_id": "cmd-1",
    "goal_id": "goal-1",
    "aci_status": "completed",
    "aci_success": True,
    "reason_codes": [...],
    "messages": [...],
    "trace_id": "trace-xyz",          # AgentCommandResult.trace_id
    "syscall_id": "syscall-42",       # from metadata.syscall_id
    "provider_id": "anthropic",        # ResolvedProvider.provider_id
    "provider_source": "exact",       # ResolvedProvider.source
    "policy_decision": {              # PolicyDecisionSummary
        "decision_id": "...",
        "allowed": True,
        "action": "allow",
        "safety_level": "L0",
        "reason_codes": [...]
    },
    "convergence_reason_code": "..."  # when meaningful
}
```

Downstream consumers (Review artifact, Readiness proof) read this
payload directly without re-resolving anything from the
:class:`AgentCommandResult`.

---

## 7. Audit reference attachment

:func:`consume_aci_result` always calls
:meth:`AgentLoopSession.attach_aci_result` before applying any
event. The audit reference lives at ``session.aci_refs`` and carries
the bare metadata needed to look the result up later:

```python
session.latest_aci_ref()  # -> _ACIResultRef(command_id, status, success,
                            #    goal_id, blocked_reason, requires_approval,
                            #    metadata={reason_codes, trace_id, provider_id})
```

The attachment happens before the FSM event sequence runs so that a
partial-failure consumer (e.g. the FSM rejects a mid-sequence
transition in a future phase) still leaves the audit trail intact.

---

## 8. Lifecycle and termination

* :func:`consume_aci_result` rejects terminal sessions with
  :class:`SessionClosedError`. There is no path to "rewind" a halted
  session.
* The consumer does not introduce side effects beyond mutating the
  session. It does not touch the filesystem, the network, or
  subprocesses.
* The session's ``max_events`` cap is enforced by
  :class:`AgentLoopSession`'s model validator. The consumer does not
  raise when the cap is reached; instead, the underlying FSM raises
  ``ValueError`` from the session constructor when a new event would
  push past the cap.

---

## 9. v0.2 vs deferred

### Implemented in Phase 3

* :func:`loopos.ali.session.consume_aci_result` -- one-shot consumer
  that maps :class:`AgentCommandResult` to FSM events.
* State-aware filtering via :func:`_filter_for_state`.
* :class:`AgentCommandResult` audit reference attached before the
  event sequence runs.
* 25 unit tests in :mod:`tests.test_ali_aci_consumption`.

### Deferred

* Real evaluation / progress (the placeholders
  :attr:`EvaluationSummary.repairable` and
  :attr:`ProgressSummary.no_progress` are read but the kernel that
  populates them lands later).
* Multi-result batch consumption. The consumer handles one result at
  a time. The caller (loop engine or test harness) loops.
* Persisting :class:`AgentLoopSession` to ``loopos/trace`` -- the
  session model is already JSON-serializable, but the integration
  with the trace subsystem is a separate task.

### Implemented in Phase 4

* Kernel-side integration via
  :meth:`KernelLoopEngine.submit_agent_command` -- a thin opt-in
  entry point that runs an :class:`AgentCommand` through the
  existing :class:`CommandRunner`, drives the ALI session via
  :func:`consume_aci_result`, and mirrors the audit metadata
  (``trace_id``, ``syscall_id``, ``provider_id``, reason codes) to
  ``run.metadata['aci_outcomes']``.
* The integration uses the kernel runtime's policy engine and
  syscall router, so Policy OS, Syscall Router, and Trace remain
  the single source of truth. Existing ``KernelLoopEngine.run()`` /
  ``resume()`` paths are untouched.
* 15 tests in :mod:`tests.test_kernel_aci_ali_integration` cover the
  full ACI -> ALI mapping plus regression of the existing kernel
  convergence flow. See ``docs/kernel-aci-ali-integration.md`` for
  the full contract.

---

## 10. Examples

### Boot a session and consume a completed result

```python
from loopos.ali import create_session, apply_event, consume_aci_result
from loopos.aci import AgentCommandResult

session = create_session("goal-1")
apply_event(session, "goal_submitted")      # CREATED -> READY
apply_event(session, "command_submitted")    # READY   -> RUNNING

result = AgentCommandResult(
    command_id="cmd-1",
    goal_id="goal-1",
    status="completed",
    success=True,
    policy_decision=...,
)
records = consume_aci_result(session, result)
assert session.state == "RUNNING"
assert [r.event for r in records] == [
    "progress_updated", "syscall_completed",
]
```

### Consume a repairable failure and recover

```python
from loopos.ali import create_session, apply_event, consume_aci_result
from loopos.aci.models import AgentCommandResult, EvaluationSummary

session = create_session("goal-2")
apply_event(session, "goal_submitted")
apply_event(session, "command_submitted")

# First, a repairable failure.
failed = AgentCommandResult(
    command_id="cmd-2",
    goal_id="goal-2",
    status="failed",
    success=False,
    policy_decision=...,
    evaluation=EvaluationSummary(repairable=True),
)
consume_aci_result(session, failed)
assert session.state == "REPAIRING"

# Agent submits a new command.
apply_event(session, "command_submitted")
assert session.state == "RUNNING"

# Second attempt succeeds.
success = AgentCommandResult(
    command_id="cmd-3",
    goal_id="goal-2",
    status="completed",
    success=True,
    policy_decision=...,
)
consume_aci_result(session, success)
assert session.state == "RUNNING"
```

### Inspect the audit trail

```python
for record in session.events:
    print(record.seq, record.event, record.reason_code,
          record.payload.get("reason_codes"))
```

Output (for the recovery scenario above):

```text
0 goal_submitted          ali.goal_submitted          []
1 command_submitted        ali.command_submitted        []
2 progress_updated         ali.progress_updated         []
3 syscall_failed           ali.syscall_failed_repairable  []
4 command_submitted        ali.repair_command_submitted []
5 progress_updated         ali.progress_updated         []
6 syscall_completed         ali.syscall_completed         []
```

---

## 11. Relationship to KernelLoopEngine and ACI

```text
AgentCommand (loopos/aci)
   |
   v
AgentCommandResult (loopos/aci)
   |
   v
consume_aci_result (loopos/ali) <-- this phase
   |
   v
AgentLoopSession events (loopos/ali)
   |
   v
(v0.1) KernelLoopEngine reads session.events to drive the run loop.
```

ALI is the bridge between ACI's per-command outcomes and the kernel
loop engine's run-level state. The consumer in this phase makes the
bridge explicit, typed, and testable without the kernel needing to be
modified.
