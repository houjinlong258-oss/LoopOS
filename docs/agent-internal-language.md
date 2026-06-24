# LoopOS Agent Internal Language

LAIL is the internal structured, token-efficient signal language used by
LoopOS agents during the Project Training Loop.

LAIL is not an execution protocol. It carries goal, gap, finding, repair,
loss, checkpoint, convergence, memory, and delivery signals between roles.
It does not run tools, shells, network calls, database writes, releases, or
syscalls.

## Roles

The v0.4.0 role set is implemented in `loopos.agent_language.roles`:

- `loop_controller`
- `planner`
- `builder`
- `tester`
- `reviewer`
- `repairer`
- `optimizer`
- `mad_dog`
- `delivery_evaluator`
- `memory_compiler`

## Signals

The supported signal vocabulary is implemented in
`loopos.agent_language.signals`:

- `goal.received`
- `objective.compiled`
- `plan.proposed`
- `build.completed`
- `test.passed`
- `test.failed`
- `review.finding`
- `repair.proposed`
- `optimization.signal`
- `loss.measured`
- `checkpoint.saved`
- `convergence.checked`
- `fake_convergence.detected`
- `delivery.candidate`
- `memory.context_compiled`
- `communication.routed`

## Message Boundary

`AgentMessage` is a strict Pydantic model. It requires trace and iteration
identity, source and recipient roles, a signal type, payload, evidence,
confidence, token and communication metrics, and an `authority_delta`.

Hard rules:

- LAIL messages cannot contain executable syscall fields.
- LAIL messages cannot trigger shell, network, database, file mutation, or release work.
- `authority_delta` remains `none` before commitment.
- Commitment happens through the Commitment Boundary, not through LAIL.

## Compact Codec

LAIL supports full JSON for trace/debug and a compact single-line form for
agent-to-agent communication:

```text
review.finding i=4 from=reviewer to=repairer,optimizer target=loop_engine.repair gap=failed_test auth=none
```

The codec is implemented in `loopos.agent_language.codec`.
