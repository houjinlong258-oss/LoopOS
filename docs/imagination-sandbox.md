# Imagination Sandbox

> LoopOS does not constrain imagination.
> LoopOS constrains what imagination is allowed to become.

The `ImaginationSandbox` is the v0.4.0 surface where models can
brainstorm, speculate, attack, propose wild architectures, and
disagree with themselves — **without** triggering a hard policy
block. It is the *thought* layer.

For the boundary that turns a thought into an action, see
[Creativity Boundary](creativity-boundary.md).

## 1. Purpose

Earlier versions of LoopOS were correct to enforce policy on
**side effects** — file writes, shell commands, network calls,
provider calls, release operations. But the same governance
inadvertently bled into the *thinking* layer. Plan candidates got
blocked because they looked risky. Brainstorm outputs got reviewed
as if they were commands. Mad Dog findings were treated as
verdicts.

The v0.4.0 `ImaginationSandbox` fixes this. In the sandbox:

- Brainstorming is allowed to be wrong, redundant, or weird.
- Multiple contradictory plans can coexist.
- Architecture speculation is allowed to violate current constraints.
- Risk is **labeled**, not **enforced**.
- Findings feed the next plan candidate, not the policy engine.

## 2. What is in the sandbox

The sandbox is implemented in `loopos.loop_engine.imagination` and
exposes three Pydantic models:

```python
class ImaginationRequest:
    goal: UserGoal
    prompt: str
    mode: Literal["brainstorm", "wild", "alternatives",
                  "architecture", "repair", "optimization"]
    max_candidates: int

class CreativeCandidate:
    id: str
    title: str
    summary: str
    rationale: str
    assumptions: list[str]
    expected_benefits: list[str]
    risks: list[str]
    possible_actions: list[str]
    wildness_level: int
    requires_commitment: bool
    authority_delta: Literal["none"] = "none"  # hard invariant

class ImaginationResult:
    candidates: list[CreativeCandidate]
    notes: list[str]
    trace_id: str | None
```

## 3. Hard invariants

These invariants are enforced at the type level and at the runtime
boundary. They are **non-negotiable** in v0.4.0.

1. `CreativeCandidate.authority_delta` is *always* `"none"`. There is
   no other value.
2. `ImaginationResult` carries no `SyscallRequest`, no file path
   mutation, no network endpoint, and no release operation.
3. `ImaginationSandbox.imagine()` does **not** call into
   `PolicyEngine` for hard blocks. Policy can attach an advisory
   risk label; it cannot refuse to return a result.
4. `ImaginationSandbox` does **not** create a `CommitmentProposal`.
   The only way to bridge from imagination to action is through the
   `CommitmentBoundary`, and that is a separate call.

## 4. Modes

| Mode | Purpose |
|------|---------|
| `brainstorm` | Free-form candidate generation for a goal |
| `wild` | Out-of-the-box ideas, allowed to be expensive / risky / weird |
| `alternatives` | Generate 2+ competing candidates for the same plan |
| `architecture` | Long-horizon structural proposals |
| `repair` | Generate ideas to fix a specific finding |
| `optimization` | Generate ideas to improve a non-failing dimension |

The mode is advisory — it does not constrain the candidate content.

## 5. Usage in the loop

The loop itself does not require imagination. The sandbox is for
*external* callers (CLI: `loopos imagine ...`, future agents, etc.)
and for future planner extensions that want to consult a brainstorm
set before emitting a `PlanCandidate`.

In v0.4.0 the surface is intentionally simple:

```python
from loopos.loop_engine.imagination import (
    ImaginationSandbox, ImaginationRequest,
)

sandbox = ImaginationSandbox()
result = sandbox.imagine(
    ImaginationRequest(
        goal=user_goal,
        prompt="Three ways to implement Fusion Optimizer",
        mode="brainstorm",
        max_candidates=3,
    )
)
# result.candidates[*].authority_delta == "none"
# result has no syscall field, no file mutation, no policy block.
```

## 6. Why the hard invariants matter

The hard invariants are what make the rest of the loop engineering
runtime work. Without them:

- A model trained to be helpful would still feel policed during
  brainstorming, and the output would be narrower than it needed to be.
- A "risky" idea (e.g. "rewrite the planner from scratch") would be
  silently dropped before the planner even saw it.
- The optimizer layer would have to fight the policy layer on every
  call.

With the invariants in place, the boundary is explicit and
**deliberate**: imagination is free, and authority is governed. The
governance kicks in only at the commitment step, where it belongs.

## 7. Related reading

- [Creativity Boundary](creativity-boundary.md) — idea → action gating
- [Loop Engineering Runtime](loop-engineering-runtime.md)
- [Core Loop](core-loop.md)
- [Fusion Optimizer](fusion-optimizer.md)
