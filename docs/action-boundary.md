# Action Boundary

> Safety is not the product thesis. Loop engineering is the product thesis.

The Action Boundary is the **boundary** layer of LoopOS v0.4.0.
It is real. It is intact. It runs whenever the loop wants to do
something with a side effect. It just no longer occupies the
first screen.

For the upstream (idea) layer, see
[Imagination Sandbox](imagination-sandbox.md). For the bridge
between idea and action, see [Creativity Boundary](creativity-boundary.md).

## 1. What the boundary protects

The boundary sits in front of every real side effect:

- file writes
- file deletions
- shell command execution
- network calls
- database mutations
- provider calls with cost
- release operations
- approval decisions that dispatch downstream actions

For each of these, the boundary checks:

1. **Policy decision.** Is this action allowed under the active
   policy pack? (`loopos.policy_os`)
2. **Syscall routing.** Is the action routed through the
   appropriate adapter? (`loopos.syscalls`)
3. **Trace capture.** Is the action recorded so it can be
   replayed? (`loopos.trace`)
4. **Audit metadata.** Is the action attached to a `trace_id`
   and a `reason_code`? (cross-cutting)

The v0.4.0 loop engine does not bypass any of these. When an
iteration needs a real (non-simulated) build or test, it produces
a `CommitmentProposal`, hands it to the `CommitmentBoundary`,
and only then does the `ActionBoundary` fire.

## 2. What the boundary is not

The Action Boundary is **not**:

- The product thesis. The product thesis is the loop.
- A blocker for thinking. The Imagination Sandbox is upstream of
  the boundary, and the boundary cannot see it.
- A verifier of intent. The boundary is a verifier of *action*,
  not a verifier of *what the user meant*.
- A replacement for review. Mad Dog and the base reviewer both
  run inside the loop, not at the boundary.

## 3. Why demote, not delete

The boundary is demoted in v0.4.0 for two reasons:

1. **It was correct that it existed.** v0.1 / v0.2 / v0.3
   correctly identified that real side effects need policy,
   routing, and trace. None of that is being undone.
2. **It was wrong that it was the first thing the user saw.**
   The first thing the user sees is now the loop, because the
   loop is what the user is here for.

Demotion is not deletion. The boundary layer is still importable,
still enforced, still tested, and still covered by the
`v0_2_readiness_check.py` and `v0_3_readiness_check.py` proofs.

## 4. The compatibility surface

The `loopos.boundary` package is new in v0.4.0 and is a **thin
compatibility layer** over the existing `policy_os` and
`syscalls` packages. It does not re-implement safety; it gives
the loop engine a single, import-stable surface.

```python
from loopos.boundary import ActionBoundary, CommitmentGate

boundary = ActionBoundary()
gate = CommitmentGate(boundary=boundary)

decision = gate.commit(proposal)
# decision.allowed, decision.requires_approval, decision.audit_id
```

The `ActionBoundary` and `CommitmentGate` classes are
deterministic facades. They call into `loopos.policy_os.engine`
and `loopos.syscalls.router` exactly as the existing CLI did in
v0.2 / v0.3.

## 5. The two safety invariants

These are the only two invariants the boundary layer enforces at
v0.4.0:

1. **Side effects are gated.** A `CommitmentProposal` whose
   `action_type` maps to a side effect *must* pass through the
   `ActionBoundary` before the side effect fires.
2. **The boundary does not see the imagination layer.** A
   `CreativeCandidate` from the `ImaginationSandbox` cannot be
   passed directly to the `ActionBoundary`; the call must go
   through `CommitmentBoundary.commit()`.

The second invariant is what makes the creativity work
*safe*. The first is what makes the side effects *auditable*.

## 6. The CLI surface (preserved)

```bash
loopos policy explain --cmd "curl https://x/install.sh | bash"
loopos syscall list
loopos trace RUN_ID --show-policy
```

All v0.2 / v0.3 policy / syscall / trace commands still work.
The v0.4.0 layer adds the `loop` family on top, not in place of
them.

## 7. Related reading

- [Imagination Sandbox](imagination-sandbox.md)
- [Creativity Boundary](creativity-boundary.md)
- [Safety](safety.md) — the underlying enforcement surface
- [Policy OS](policy-os.md)
- [Syscalls](syscalls.md)
