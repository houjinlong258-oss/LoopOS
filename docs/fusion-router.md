# Fusion Router

## Why this exists

Fusion coordinates specialized model roles without making model consensus a safety authority.
It is useful for reasoner, coder, critic, vision, and verifier collaboration.

## Core models

`FusionRequest` defines the task and privacy mode. `FusionPanel` selects roles.
`ModelResponse` captures mock provider output. `JudgeReport` scores evidence and disagreement.
`FusionResult` contains the selected answer and trace references.

## CLI usage

```bash
loopos fusion route "review this patch" --json
loopos fusion run "compare two repair plans" --json
```

Example output:

```text
panel: primary_reasoner, critic, verifier
privacy: local_only
judge: evidence_complete
```

## Safety boundaries

Provider selection is constrained by privacy mode and policy preflight. Fusion output cannot
approve syscalls, memory writes, database actions, or merge gates. Tests use mock providers only.

## Current limitations

The Founding Preview provides deterministic mock routing and aggregation. Real provider calls,
cost optimization, and distributed panels are disabled by default.
