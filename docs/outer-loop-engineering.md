# Outer Loop Engineering

The future outer loop surrounds the Kernel with persistent triggers, tasks, worktree isolation, and separated Producer, Verifier, and Reviewer roles.

Required invariants:

- triggers create tasks but never execute them directly
- code-changing tasks receive an isolated Git worktree and branch
- task state is persistent and idempotent
- Producer cannot approve its own high-risk output
- Verifier runs deterministic acceptance checks
- Reviewer evaluates the diff and residual risk independently
- cleanup only removes worktrees proven stale and owned by LoopOS

This layer is not part of the current executable MVP and must use Kernel Runs for all work.
