# Go Core Roadmap

LoopOS 0.1.0 remains Python-only. The Founding Release will not be delayed by a language rewrite.
The migration contract is JSON-compatible ACI, AIL, Policy, Syscall, Trace, and convergence data.

## Target split

```text
Go runs the agent runtime.
Python teaches the agent.
Rust contains the blast radius.
```

### Go Core

Kernel loop, Scheduler, Policy OS, Syscall Router, Trace runtime, Data Guard, Release Readiness,
Plugin Registry, Gateway, CLI, and daemon. Go is suitable for a single cross-platform binary,
bounded concurrency, predictable startup, process supervision, and release tooling.

### Python Intelligence Layer

LLM providers, prompt distillation, Fusion judge, local intelligence, skill extraction, evaluation
heuristics, and benchmarks. Python remains the fastest integration environment for model and data
ecosystems.

### Rust Sandbox

Terminal isolation, seccomp/jail integration, filesystem containment, secret scanning, and hardened
parsers. Rust is reserved for components where memory safety and a narrow blast radius justify the
additional build complexity.

## Migration phases

- **v0.2:** optional `core-go/` scaffold with version, trace-tree, policy-explain, and release-verify
  commands. It does not replace Python.
- **v0.3:** migrate Trace and Policy readers while preserving JSON schemas.
- **v0.4:** migrate terminal, file, Git, and local SQLite syscall routing.
- **v0.5:** make the Go Kernel, Scheduler, convergence bridge, and transitions the default runtime;
  retain Python for intelligence features.

## Compatibility rules

1. JSON schemas are the cross-language contract.
2. Persisted v0.1 run, trace, policy, memory, and release records remain readable.
3. Python and Go implementations must pass the same golden fixtures.
4. Side-effecting adapters remain behind policy and capability checks.
5. No rewrite begins before the Founding Release is verified and tagged.
