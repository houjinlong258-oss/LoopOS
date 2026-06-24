# Creativity Boundary

> Thought is free. Authority is governed.

The Creativity Boundary is the *commitment* layer between the
`ImaginationSandbox` and any real side effect. It answers one
question: **is this idea about to become an action that needs
policy / approval / syscall routing?**

For the upstream surface, see
[Imagination Sandbox](imagination-sandbox.md). For the downstream
surface, see [Action Boundary](action-boundary.md).

## 1. Why a separate layer

There are three classes of "things" LoopOS deals with:

| Class | Examples | Where it lives |
|-------|----------|----------------|
| **Ideas** | brainstorm, plan candidate, review finding, mad dog finding, risk label, doc suggestion | `ImaginationSandbox` (no policy block) |
| **Commitments** | `CommitmentProposal` to patch, run a command, hit a network endpoint, mutate a DB, release | `CommitmentBoundary` (gated) |
| **Actions** | the actual file write / shell / network call / release | `ActionBoundary` (Policy OS + Syscall Router) |

The Creativity Boundary is the gate from "ideas" to "commitments".
The Action Boundary is the gate from "commitments" to "actions".

## 2. `CommitmentProposal`

```python
class CommitmentProposal:
    id: str
    source_candidate_id: str | None
    proposed_action: str
    action_type: Literal[
        "plan", "patch", "test", "command",
        "syscall", "release", "doc",
    ]
    expected_side_effects: list[str]
    required_permissions: list[str]
    requires_policy: bool
    requires_approval: bool
    rationale: str
```

A `CommitmentProposal` is *typed* and *auditable*. It does not
dispatch anything by itself. It is the thing the
`CommitmentBoundary.commit()` call validates.

## 3. The `commit()` decision

`CommitmentBoundary.commit(proposal)` returns a structured decision
in v0.4.0:

```python
class CommitmentDecision:
    allowed: bool
    requires_approval: bool
    reason_codes: list[str]
    risk_label: str
    constraints: list[str]
    audit_id: str
```

The decision is deterministic for a given `(proposal, policy_state)`
pair. The same proposal with the same policy state will always
produce the same decision.

## 4. What triggers hard policy checks

Only `CommitmentProposal.action_type` values that map to real
side effects trigger the policy check. The mapping in v0.4.0:

| `action_type` | Side effect | Hard policy? |
|---------------|-------------|--------------|
| `plan` | none | no |
| `doc` | none (advisory) | no |
| `patch` | file write | yes |
| `test` | subprocess + file write | yes |
| `command` | shell execution | yes |
| `syscall` | any router-mediated call | yes |
| `release` | release operation | yes |

Ideas whose `action_type` is `plan` or `doc` cannot be hard-blocked
by Policy OS in v0.4.0. They can be **labeled** with a risk level,
but they cannot be denied.

## 5. The "policy gates actions, not ideas" invariant

This invariant is enforced at the type level: an
`ImaginationSandbox` cannot return a `CommitmentProposal`. The only
way to produce one is to call the `CommitmentBoundary` explicitly
from a loop iteration or from a CLI command. This makes the policy
check **invisible** to brainstorm / planning / review code paths.

## 6. CLI surface

```bash
# Brainstorm with no side effects
loopos imagine "Three ways to redesign the planner" --json

# Promote a candidate to a commitment (gated)
# (planned for v0.4.x; in v0.4.0 the surface is library-level)
```

In v0.4.0, the v0.4.0 loop engine itself produces
`CommitmentProposal` instances when an iteration needs to run a
real (non-simulated) test or build. The `CommitmentBoundary` is the
gate.

## 7. Related reading

- [Imagination Sandbox](imagination-sandbox.md) — the idea layer
- [Action Boundary](action-boundary.md) — the action layer
- [Policy OS](policy-os.md) — the existing policy surface
- [Loop Engineering Runtime](loop-engineering-runtime.md)
