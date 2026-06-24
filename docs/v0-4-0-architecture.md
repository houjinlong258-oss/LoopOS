# v0.4.0 Architecture

LoopOS v0.4.0 is a Project Training Runtime for AI agents.

```text
User Goal
  -> ProjectObjective
  -> SuccessCriteria
  -> LoopEngine
  -> Plan
  -> Build
  -> Test
  -> Review
  -> ProjectLoss / GoalGap
  -> Repair / Optimize
  -> ProjectCheckpoint
  -> Repeat or Deliver
```

## Product Layer

`loopos.loop_engine` is the product-facing orchestrator. It does not replace
`loopos.kernel`. The Kernel Loop Engine remains the low-level execution
backend.

## Signal Layer

`loopos.agent_language` carries LAIL messages and routes them with
communication-distance metrics.

## Memory Layer

`loopos.project_memory` stores compressed project-training signals and
compiles role-specific `ContextPacket` records.

## Quality Layer

`loopos.quality` measures `QualityScore`, `ProjectLoss`, fake convergence,
convergence status, and delivery readiness.

## Optimizer Layer

`loopos.fusion_optimizer` ranks next-iteration candidates. It is an optimizer,
not an allow/block verdict router.

## Boundary Layer

Policy OS, Syscall Router, approval, Data Guard, Memory Governance, and Trace
remain intact. They protect real side effects. They are not the first screen.
