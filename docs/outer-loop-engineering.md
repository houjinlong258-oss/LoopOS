# Outer Loop Engineering

The outer-loop MVP surrounds the Kernel with persistent triggers, tasks, worktree planning, and separated Producer, Verifier, and Reviewer roles.

Required invariants:

- triggers create tasks but never execute them directly
- code-changing tasks receive an isolated Git worktree and branch
- task state is persistent and idempotent
- Producer cannot approve its own high-risk output
- Verifier runs deterministic acceptance checks
- Reviewer evaluates the diff and residual risk independently
- cleanup only removes worktrees proven stale and owned by LoopOS

Executable skeleton:

- `loopos triggers fire daily-maintenance` creates a persisted task.
- `loopos tasks list` and `loopos tasks next --quick-win` inspect the queue.
- `loopos worktrees plan TASK_ID` records an isolated branch/path plan and detects lock conflicts.
- `loopos review start TASK_ID` creates an independent review record and rejects self-review for high-risk work.

The MVP records worktree intent instead of running `git worktree add`. Real materialization must be routed through Policy OS and syscalls.
