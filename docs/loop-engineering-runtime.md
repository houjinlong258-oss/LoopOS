# Loop Engineering Runtime

> Other agents execute tasks. **LoopOS trains projects toward completion.**

LoopOS v0.4.0 is repositioned as a **Project Training Runtime** for AI
agents. The product thesis is the **training loop**: define an
objective, run a forward pass (plan → build → test → review), measure
a loss, produce an evaluation signal, take an optimizer step,
checkpoint, repeat until convergence.

This document is the canonical product thesis. The canonical
end-to-end reference is
[`docs/project-training-loop.md`](project-training-loop.md); this
document focuses on the **what changed** story and how LoopOS
relates to the existing runtime surfaces.

## 1. What changed

Earlier versions of LoopOS were correctly described as a "kernel for
running agents" — strong on governance, weak on the *engineering
loop*. v0.4.0 changes the centre of gravity:

| Earlier framing (v0.2 / v0.3) | v0.4.0 framing |
|-------------------------------|----------------|
| Agent runtime with policy, syscall, memory, and trace | **Project training runtime** for AI agents |
| Policy OS as the headline | **Project training loop** as the headline; Policy OS is the action boundary |
| Fusion as a verdict / escalation router | Fusion as the **optimizer** that proposes the next iteration |
| Mad Dog as a security blocker | Mad Dog as the **adversarial evaluator** that prevents fake convergence |
| Goal as input | Goal as the **project objective** / training objective |
| Quality score is a number | Quality score is the **loss**; gradients are **evaluation signals** |
| Loop halts when AIL scheduler says so | Loop halts when the project **converges** |
| Delivery is "the loop finished" | Delivery requires **ConvergenceReport** + no fake convergence |

The Kernel, AIL, Policy OS, Syscall Router, Memory OS, and Trace are
**preserved and intact**. They are now positioned as the **execution
backend** and **action boundary** of the project training runtime,
not its product identity.

## 2. The thesis

```text
User gives an objective.
LoopOS runs a forward pass: plan → build → test → review.
LoopOS measures the loss (gap between current state and objective).
LoopOS produces evaluation signals (which findings push the loss up).
The Fusion Optimizer proposes the next best iteration.
Mad Dog attacks the result to prevent fake convergence.
LoopOS checkpoints and repeats.
The loop runs until the project converges.
```

The product thesis is the **project training loop** itself. The
safety boundary exists to make the loop safe to run, not to make
the loop safe to *not run*.

In one sentence:

> **LoopOS is the runtime for self-improving AI engineering loops.**

## 3. The five design principles

1. **User goal is the north star.** Every iteration produces evidence
   of progress against explicit success criteria. There is no
   "completed" without evidence.
2. **The loop is the engine.** Plan → Build → Test → Review → Repair →
   Optimize → Repeat. Each phase produces typed data that feeds the
   next. No phase is optional; no phase pretends to be the others.
3. **Thought is free; authority is governed.** Imagination, planning,
   brainstorming, and review are not policed — they live in a
   `ImaginationSandbox` and `CommitmentBoundary` only requires
   gating when an idea becomes an action with side effects.
4. **Safety is the boundary, not the engine.** Policy OS and the
   Syscall Router remain the single source of truth for real
   side effects. They run *because* the loop runs, not instead of it.
5. **Delivery is convergence, not termination.** The loop stops when
   success criteria are satisfied, quality thresholds are met, and
   remaining risks are acknowledged — not when a budget runs out.

## 4. What the loop is not

- Not a single LLM call dressed up as orchestration.
- Not a multi-model chat where the loudest answer wins.
- Not a planner that emits a plan and then forgets about execution.
- Not a CI runner that owns deployment.
- Not a safety review tool. (Mad Dog *does* safety; it also does nine
  other categories.)

## 5. The relationship to the rest of LoopOS

```text
v0.4.0 product surface
  ├── loop_engine/   ← LoopEngine (Goal → ... → Deliver)
  ├── quality/       ← QualityScorer, ConvergenceEngine, DeliveryEngine
  ├── fusion_optimizer/  ← FusionOptimizer, MadDogReviewer
  └── boundary/      ← thin compatibility layer over policy_os / syscalls

v0.2 / v0.3 execution backend (preserved)
  ├── kernel/        ← KernelLoopEngine (AIL-driven)
  ├── ail/           ← Agent Internal Language
  ├── policy_os/     ← Policy OS (boundary)
  ├── syscalls/      ← Syscall Router (boundary)
  ├── memory/        ← Memory OS
  ├── trace/         ← Trace + ALI replay
  ├── fusion_router/ ← legacy verdict / escalation router
  └── ...            ← execution, integrations, etc.
```

The loop engine in v0.4.0 is the **product-facing orchestrator**. The
Kernel Loop Engine (`loopos.kernel`) remains the **low-level execution
backend**. They are different layers, and they coexist on purpose.

## 6. Why the v0.4.0 timing is right

The Kernel and its governance surfaces are stable, tested, and
well-documented. The remaining work was always going to be on the
*loop*: making sure failed tests feed repair, repair feeds plans,
plans feed builds, builds feed quality scores, quality scores feed
convergence, and convergence produces a real delivery candidate.
v0.4.0 is that work.

## 7. Related reading

- [Core Loop](core-loop.md) — phase-by-phase walkthrough
- [v0.4 Architecture](v0-4-architecture.md) — module layering
- [Imagination Sandbox](imagination-sandbox.md) — creativity without policy blocks
- [Creativity Boundary](creativity-boundary.md) — idea → action gating
- [Action Boundary](action-boundary.md) — where safety lives
- [Non-Goals](non-goals.md) — what LoopOS deliberately is not
