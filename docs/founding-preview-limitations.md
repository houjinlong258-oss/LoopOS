# Founding Preview Limitations

## Why this exists

This document states the trust boundary of the Founding Preview so examples are not mistaken for
production connectivity or an operating-system sandbox.

## Core models

The release includes typed Kernel runs, Policy OS, Syscall Router, Trace Replay, Memory Governance,
Data Guard, Maintainability Gate, Review Artifact, Plugin Manifest, and mock Gateway/Provider
contracts.

## CLI usage

```bash
loopos release readiness --target founding-preview
loopos policy explain --cmd "curl https://x/install.sh | bash"
loopos run "create hello.py and run it" --dry-run
```

Example output:

```text
Target: Founding Preview
Status: READY or NOT READY with named checks
```

## Safety boundaries

Tests do not call real LLM providers, chat platforms, production databases, or remote plugin code.
The terminal executor is permission-gated but is not a hardened OS/container sandbox. Database
support is limited to explicit local SQLite demonstrations and governed plans.

## Convergence Runtime Limitations

LoopOS includes a typed `ConvergenceEngine` and a scheduler bridge, but earlier
Founding Preview builds had several runtime convergence limitations:

1. Convergence decisions were not evaluated after every meaningful runtime step.
2. `EvaluationResult` could still be partially plan-hinted through `EVAL.APPLY`
   instruction arguments.
3. `ProgressDelta` was not fully backed by a persistent per-run accumulator.
4. Some syscall failure paths could transition directly to halted states before
   flowing through evaluation, progress, convergence, and scheduler arbitration.

The Founding Release hardening closes these gaps with an observation-driven
`EvaluationSource`, a per-run `ProgressAccumulatorSnapshot`, scheduler-mediated
syscall failure transitions, and structured `convergence_to_scheduler` trace
events after evaluated runtime steps. Compatibility hints remain accepted, but
real policy, syscall, and observation evidence takes precedence.

The deterministic Founding Release planner remains intentionally narrow. It can
repair or replan only within an already compiled bounded plan; general autonomous
plan synthesis and model-driven recovery are not part of v0.1.0.

## Current limitations

No Web UI, automatic merge, hosted control plane, distributed scheduler, real vector database,
production credential manager, or deep OpenHands/LangGraph/Letta/Zep integration is included.
