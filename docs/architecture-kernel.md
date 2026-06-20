# LoopOS Kernel Architecture

LoopOS Kernel is a deterministic, policy-governed runtime for terminal-native agent runs. A user goal becomes a managed process; every external action becomes a syscall; every transition and decision becomes a trace event.

## Runtime Pipeline

```text
Goal
-> Intent Compiler / RunSpec
-> Context Compiler
-> deterministic Planner
-> AIL validation and normalization
-> Policy OS
-> Kernel Scheduler
-> Syscall Router
-> Observation
-> Evaluation
-> Transition Engine
-> governed Memory and Skill proposals
-> Scheduler continue, repair, replan, wait, or halt
-> Renderer
```

## Process Model

`RunRecord` is the durable process record. It owns status, phase, step, workspace, execution mode, bounds, pending approval, timestamps, and references to trace events. `RunManager` is the only kernel service that creates and persists run records.

## Scheduler

The scheduler is a pure decision function. Policy denial halts as blocked; approval requirements wait; success halts; repairable failures repair; no-progress evaluations replan; max steps fail; all other cases continue.

## Syscalls

External effects are restricted to registered syscalls. The MVP registry contains terminal execution, workspace file read/write, and Git status/diff. Routing always validates input, evaluates policy, records the decision, executes one adapter, normalizes the result, and appends trace events.

## Trace and Replay

Trace events are append-only and carry run, step, instruction, policy, and syscall references. Replay reconstructs state and explains a step from stored events. Replay never executes a syscall.

## Compatibility

Legacy AI-ISA, LoopEngine, MCP Router, EventLog, StateStore, JSONL, and SQLite entry points remain readable. Compatibility adapters normalize legacy operation names and records before they enter the Kernel.
