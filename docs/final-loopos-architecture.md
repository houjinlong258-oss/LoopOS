# Final LoopOS Architecture

LoopOS is a terminal-native Agent OS Kernel. Codex is the engineering agent that implements and verifies LoopOS; Codex is not the LoopOS runtime itself.

```text
Natural-language goal
-> Goal Negotiation / GoalSpec
-> Context Compiler
-> AIL plan
-> Policy OS
-> deterministic Scheduler and Convergence Engine
-> Syscall Router / adapters
-> Observation / Evaluation / ProgressDelta / LoopDecision
-> governed Memory and Skill proposals
-> Trace / Replay / Renderer
```

The inner loop is implemented in the Python Kernel MVP. The outer loop, provider gateway, multi-model scheduler, and ChatOps adapters remain separate follow-up layers so they cannot bypass Kernel policy, approval, trace, or memory governance.

## Engineering Order

1. Keep AIL, Policy OS, Kernel, syscalls, trace, memory, and convergence deterministic.
2. Add persistent task and worktree orchestration around the stable inner loop.
3. Add provider profiles and mock capability routing without real credentials.
4. Add mock ChatOps adapters that translate messages and approvals into Kernel events.
5. Enable real providers or platforms only behind explicit configuration and integration tests.
