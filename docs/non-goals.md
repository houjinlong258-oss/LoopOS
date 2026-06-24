# Non-Goals

> LoopOS is the runtime for self-improving AI engineering loops.
> It is not — and is not trying to be — any of the things below.

This document is the v0.4.0 negative space. It is short on
purpose: if a project proposal starts to look like one of these,
it is probably the wrong project.

## 1. LoopOS is not

- **A chatbot.** LoopOS is a state-driven runtime. Natural
  language exists at the input and output boundaries; internal
  handoffs are typed.
- **A plain agent runner.** A plain agent runner dispatches
  LLM calls. LoopOS runs a *loop*, and the loop is the product.
- **A security audit tool.** LoopOS includes a security
  boundary; that boundary is not the product.
- **A pure policy engine.** Policy OS is preserved and intact in
  v0.4.0, but it is one of several support layers, not the
  product.
- **A pure syscall router.** Same as above.
- **An approval inbox.** The `MadDogReviewer` and the
  `LoopReviewer` are not approval UIs. They produce typed
  findings.
- **A multi-model answer aggregator.** Fusion in v0.4.0 is an
  optimizer, not a chat router. See
  [Fusion Optimizer](fusion-optimizer.md).
- **A planner that never closes the loop.** A plan is the
  *first* thing the loop produces, not the *only* thing.
- **A replacement for the Kernel.** The Kernel Loop Engine
  remains the low-level execution backend.
- **A "human in the loop" UI.** The CLI is the surface; the
  state is the artifact.
- **A continuous deployment system.** Delivery is a *loop
  decision*, not a release pipeline.
- **A benchmarking platform.** Quality scores are loop-internal;
  they are not cross-project comparable.

## 2. LoopOS is

- **A loop engineering runtime.** A typed, deterministic,
  test-covered engine that drives Goal → Plan → Build → Test →
  Review → Repair → Optimize → Deliver.
- **A multi-layer system with clear boundaries.** Product layer
  (loop_engine / quality / fusion_optimizer / boundary) on top
  of an execution backend (kernel / ail / execution) on top of
  a boundary layer (policy_os / syscalls / memory / trace).
- **A governed runtime for AI engineering work.** Governed,
  yes. But governed *inside* a loop, not in place of it.
- **A pluggable, offline-first MVP.** The default executors are
  simulated; real executors can be plugged in. The default
  scorers are deterministic; pluggable scoring is supported.
  The default tests are offline; the readiness scripts are
  offline; nothing in v0.4.0 makes a network call as part of a
  unit test.

## 3. Why this list exists

The non-goals are explicit because v0.4.0 is a *repositioning*.
It is easy to read a multi-candidate optimizer, an evidence-gated
Mad Dog, a quality score, and a delivery decision and conclude
that LoopOS is becoming a "do everything" platform. It is not.
The product thesis is the loop, and the loop has a clear
narrow surface:

> User gives a goal. LoopOS drives the loop until the work is
> ready to deliver. Safety is the boundary; quality is the
> measure; delivery is the convergence target.

Everything in the v0.4.0 release is in service of that thesis.

## 4. Related reading

- [Loop Engineering Runtime](loop-engineering-runtime.md) — the thesis
- [Core Loop](core-loop.md) — the loop
- [Action Boundary](action-boundary.md) — what safety is
- [v0.4 Architecture](v0-4-architecture.md) — what the layers are
