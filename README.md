# LoopOS

> **LoopOS is a Project Training Runtime for AI agents.**
> It continuously plans, experiments, evaluates, repairs, optimizes, and
> repeats until the project converges toward the user's goal.

![LoopOS — the project training runtime](docs/assets/brand/loopos-hero.png)

> Other agents execute tasks.
> **LoopOS trains projects toward completion.**

```text
Give LoopOS an objective.
It plans. It builds. It tests. It evaluates.
It finds gaps. It repairs. It optimizes.
And it repeats — until the project converges.
```

LoopOS applies the **training loop of AI models** to project execution.
Each iteration is a forward pass. Failed tests, review findings, and
reviewer feedback become gradient signals. The Fusion Optimizer
proposes the next best iteration. Mad Dog is the adversarial
evaluator that prevents fake convergence. The loop checkpoints,
evaluates, and re-trains the project — not the LLM.

| ML training | LoopOS project training |
|-------------|--------------------------|
| training objective | **project objective** (`UserGoal`) |
| loss | **project loss / gap** (`ProjectLoss`, `GoalGap`) |
| forward pass + eval | plan → build → test → review |
| gradient signal | **evaluation signal** (`EvaluationSignal`) |
| optimizer | **Fusion Optimizer** (next best iteration) |
| adversarial eval | **Mad Dog** (anti–fake-convergence) |
| epoch | **iteration** (`TrainingIteration`) |
| checkpoint | **project checkpoint** (`ProjectCheckpoint`) |
| convergence | **delivery** (`ConvergenceReport`) |

The loop stops when the project converges — not when an LLM says "done".
See [`docs/project-training-loop.md`](docs/project-training-loop.md) for
the full analogy and [`docs/core-loop.md`](docs/core-loop.md) for the
phases.

## Why Project Training

Most AI coding agents optimize for *one* completion. Real engineering —
and real product work — is iterative: plan, build, test, review, repair,
optimize, and repeat until the work actually satisfies the goal.

LoopOS is the **runtime** for that loop. It treats the project like a
model that needs training: each iteration produces a measurable loss, a
gradient signal, a checkpoint, and a recommendation for the next
iteration. The loop runs until the project converges or until the
iteration budget is exhausted.

> User goal is the north star.
> Loop is the engine.
> Loss is the signal.
> Optimizer is the steering wheel.
> Adversary is the safeguard against fake convergence.
> Safety is the action boundary.

## Quickstart

```bash
python -m pip install -e ".[dev]"

# Drive a goal through the loop
python -m loopos.cli.app loop run "Build a provider runtime and harden it until tests pass" \
    --max-iterations 3 --json

# Drive a real sandboxed temp/local repo executor
python -m loopos.cli.app loop run "Fix failing tests" \
    --real-executor --no-dry-run --sandbox --repo-path ./some-temp-repo --json

# Inspect the current state
python -m loopos.cli.app loop status --json

# Replay and inspect evidence without re-running side effects
python -m loopos.cli.app loop replay --latest --json
python -m loopos.cli.app loop diff --latest --json
python -m loopos.cli.app loop artifacts --latest --json

# Free-form creative brainstorm (no side effects, no policy blocks)
python -m loopos.cli.app imagine "Design three better ways to implement Fusion Optimizer" --json

# Fusion optimizer → recommends next iteration plan
python -m loopos.cli.app loop optimize --json

# Mad Dog quality attack
python -m loopos.cli.app loop review --mad-dog --json

# Computer Control defaults to fake/dry-run unless explicitly allowed
python -m loopos.cli.app computer run "Observe fake desktop and verify target" --dry-run --json
python -m loopos.cli.app computer replay --latest --json

# Token and tool-surface economy
python -m loopos.cli.app token report --latest --json
python -m loopos.cli.app tools search "run tests" --json

# Final delivery candidate
python -m loopos.cli.app loop deliver --json
```

The v0.4.0 build is **simulated** at the build/test/review layer by
default — there is no real LLM wired into the planner/builder/tester
yet. The data flow is real: failed tests become findings, findings
become repair plans, repair plans drive the next plan candidate. Real
executor backends can be plugged in by implementing the
`LoopPlanner` / `LoopBuilder` / `LoopTester` protocols.

## What changed in v0.4.0

| Area | v0.2 / v0.3 | v0.4.0 |
|------|-------------|--------|
| Identity | Kernel for running agents | **Loop engineering runtime** |
| Main loop | AIL scheduler → syscall | `LoopEngine` drives Goal → Plan → Build → Test → Review → Repair → Optimize → Deliver |
| Quality | Implicit (policy decisions) | Explicit `QualityScore` per iteration, drives convergence |
| Fusion | `fusion_router` (verdict / escalation) | `fusion_optimizer` — multi-candidate optimizer feeding the next plan |
| Mad Dog | Security blocker | **Extreme quality attacker** — 10 categories, evidence-required for delivery blocking |
| Creativity | Implicit in `intent` | Explicit `ImaginationSandbox` + `CommitmentBoundary` (policy gates actions, not ideas) |
| Safety | Product centerpiece | **Boundary layer** — still real, but demoted to supporting role |
| Delivery | Loop halts | `DeliveryCandidate` with evidence, known limitations, open risks |

## Architecture overview

```text
                     ┌───────────────────────────────┐
                     │            User Goal          │
                     └───────────────┬───────────────┘
                                     │
                  ┌──────────────────▼──────────────────┐
                  │             Goal Engine             │
                  └──────────────────┬──────────────────┘
                                     │
                  ┌──────────────────▼──────────────────┐
                  │       Success Criteria              │
                  └──────────────────┬──────────────────┘
                                     │
   ┌───────────────  LoopEngine (product)  ───────────────┐
   │                                                       │
   │   Plan → Build → Test → Review → Repair → Optimize    │
   │                          │                            │
   │                          └─► QualityScore             │
   │                          └─► ConvergenceStatus        │
   │                          └─► next iteration / Deliver │
   └─────────────────────┬─────────────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │   Fusion Optimizer  │   (multi-candidate next-plan)
              │   + Mad Dog Review  │   (10 quality categories)
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │   Quality Engine    │   (score + convergence + delivery)
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │ Commitment Boundary │   (idea → action gating)
              └──────────┬──────────┘
                         │
   ┌──────────  Action Boundary / Safety Layer  ──────────┐
   │   Policy OS · Syscall Router · Approval · Trace       │
   │   (only triggers on real side effects)                 │
   └───────────────────────────────────────────────────────┘
```

Read [`docs/loop-engineering-runtime.md`](docs/loop-engineering-runtime.md) for the
full thesis, [`docs/core-loop.md`](docs/core-loop.md) for the loop walkthrough,
and [`docs/v0-4-architecture.md`](docs/v0-4-architecture.md) for layering details.

## CLI surface (v0.4.0)

```bash
# Loop-first workflow
loopos loop run         "<goal>"  --max-iterations N --json
loopos loop status      --json
loopos loop review      [--mad-dog] --json
loopos loop repair      --json
loopos loop optimize    --json
loopos loop deliver     --json

# Creative space
loopos imagine          "<prompt>" --json

# Fusion optimizer
loopos fusion optimize  --json
loopos mad-dog attack   <target>  --json
```

All v0.2 / v0.3 commands still work (kernel, policy, syscall, fusion-router,
goal, memory, worktree, …). v0.4.0 is a layer on top, not a replacement.

## Safety Boundary

LoopOS still ships an action boundary for real side effects: file writes,
shell commands, network calls, provider calls, release operations. That
boundary is **real, intact, and policy-driven** — it just no longer occupies
the first screen.

> Safety is not the product thesis. Loop engineering is the product thesis.

Read [`docs/action-boundary.md`](docs/action-boundary.md) for the
re-positioning and [`docs/safety.md`](docs/safety.md) for the underlying
enforcement.

## What LoopOS is **not**

LoopOS is **not**:

- a chat bot
- a plain agent runner
- a security audit tool
- a pure policy engine
- a pure syscall router
- an approval inbox
- a multi-model answer aggregator
- a planner that never closes the loop

It is a **goal-driven loop engineering runtime**. See
[`docs/non-goals.md`](docs/non-goals.md).

## Development

```bash
python -m pytest
python -m ruff check .
python -m mypy loopos tests

# Readiness proofs
python scripts/v0_2_readiness_check.py --json
python scripts/v0_3_readiness_check.py --json
python scripts/v0_4_readiness_check.py --json
python scripts/anti_bloat_check.py --json
```

The test suite is deterministic and offline. See
[`CONTRIBUTING.md`](CONTRIBUTING.md) and [`SECURITY.md`](SECURITY.md)
before contributing.

## Documentation

### v0.4.0 — Loop Engineering

- [Loop Engineering Runtime](docs/loop-engineering-runtime.md)
- [Core Loop](docs/core-loop.md)
- [v0.4 Architecture](docs/v0-4-architecture.md)
- [Imagination Sandbox](docs/imagination-sandbox.md)
- [Creativity Boundary](docs/creativity-boundary.md)
- [Fusion Optimizer](docs/fusion-optimizer.md)
- [Mad Dog Quality Attacker](docs/mad-dog-quality-attacker.md)
- [Quality Engine](docs/quality-engine.md)
- [Convergence and Delivery](docs/convergence-and-delivery.md)
- [Action Boundary](docs/action-boundary.md)
- [Non-Goals](docs/non-goals.md)

### Foundational

- [Architecture](docs/architecture.md)
- [Quickstart](docs/quickstart.md)
- [Safety](docs/safety.md)
- [Policy OS](docs/policy-os.md)
- [Syscalls](docs/syscalls.md)
- [Memory Governance](docs/memory-governance.md)
- [Fusion Router (legacy)](docs/fusion-router.md) — preserved for compatibility
- [Agent Freedom Runtime](docs/agent-freedom-runtime.md)
- [CLI](docs/cli-ui.md)

## License

Licensed under the Apache License, Version 2.0. See [`LICENSE`](LICENSE).