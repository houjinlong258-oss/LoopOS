# Agent Freedom Runtime

LoopOS gives agents freedom inside governed boundaries. It does not constrain private reasoning or
force every task into a static workflow graph. It constrains authority: tools, data, side effects,
approvals, persistence, and release claims.

## Principle

```text
Do not constrain the agent's thinking. Constrain its authority.
Freedom of strategy, discipline of implementation.
```

LoopOS is not a workflow framework. A workflow prescribes the route; LoopOS lets an agent choose a
route while the runtime enforces capability, policy, evidence, and outcome boundaries.

## Freedom budget

| Level | Freedom | Required governance |
|---|---|---|
| F0 | Deterministic instruction sequence | schema and trace |
| F1 | Tool choice | tool capability and Policy OS |
| F2 | Plan choice | bounded plan and acceptance criteria |
| F3 | Strategy choice | progress, convergence, and review |
| F4 | Research choice | privacy, network, source, and cost boundaries |
| F5 | Autonomous project work | persistent tasks, worktree isolation, independent review |

The freedom level never overrides L0-L5 safety. More strategic freedom requires stronger evidence,
not broader ambient permissions.

## Capability boundary

A capability boundary declares which filesystem, terminal, Git, database, network, provider, and
memory operations are available. Policy OS can narrow it per instruction. The Syscall Router is the
only path from intent to an external adapter.

## Outcome contract

An outcome contract contains deliverables, acceptance criteria, constraints, non-goals, evidence,
and halt conditions. Completion claims without evidence remain pending.

## Smart delegation loop

The Kernel may delegate planning, coding, vision, criticism, or verification to different agents.
Delegation does not transfer approval authority. Trace connects each contribution to the final
evaluation, while Producer, Verifier, and Reviewer remain separable roles.

Letting go does not mean unsafe autonomy. Policy OS governs authority, Convergence governs progress,
Trace governs accountability, and Review governs delivery.
