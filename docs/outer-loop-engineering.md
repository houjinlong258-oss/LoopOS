# Outer Loop Engineering

The outer-loop MVP surrounds the Kernel with persistent triggers, tasks, worktree planning, and separated Producer, Verifier, and Reviewer roles.

Required invariants:

- triggers create tasks but never execute them directly
- code-changing tasks receive an isolated Git worktree and branch
- task state is persistent and idempotent
- task todos and delivery artifacts are persistent
- Producer cannot approve its own high-risk output
- Verifier runs deterministic acceptance checks
- Reviewer evaluates the diff and residual risk independently
- code-changing tasks cannot enter review until a worktree has been planned
- cleanup only removes worktrees proven stale and owned by LoopOS

Executable skeleton:

- `loopos triggers fire daily-maintenance` creates a persisted task.
- `loopos tasks list` and `loopos tasks next --quick-win` inspect the queue.
- `loopos tasks todo TASK_ID --text "Run checks"` appends a persistent todo.
- `loopos tasks report TASK_ID --content "..."`
- `loopos tasks patch TASK_ID --content "..."`
- `loopos tasks pr TASK_ID --content "..."`
- `loopos worktrees plan TASK_ID` records an isolated branch/path plan and detects lock conflicts.
- `loopos worktrees stale WORKTREE_ID` and `loopos worktrees cleanup WORKTREE_ID` manage lifecycle state.
- `loopos review start TASK_ID` creates an independent review record and rejects self-review for high-risk work.

The MVP records worktree intent instead of running `git worktree add`. Real materialization must be routed through Policy OS and syscalls.
