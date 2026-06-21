# Review Artifact

## Why this exists

Agent-produced changes need one reviewable record that joins intent, diff, tests, policy, data
safety, maintainability, verifier evidence, and reviewer approval.

## Core models

`ReviewArtifact` is the immutable review summary. `ReviewArtifactBuilder` assembles evidence.
`MergeGateDecision` explains eligibility. `MergeGate` rejects missing verification, self-approval,
policy blockers, unsafe data operations, or maintainability blockers.

## CLI usage

```bash
loopos review artifact TASK_ID --diff changes.diff
loopos review gate TASK_ID
loopos review verify TASK_ID --actor verifier --note "tests passed"
loopos review approve TASK_ID --actor reviewer --note "approved"
```

Example output:

```text
eligible: false
blockers: verifier_evidence_missing, independent_review_missing
```

## Safety boundaries

The producer cannot approve its own high-risk work. LoopOS does not automatically merge changes;
Git operations continue through policy-governed syscalls.

## Current limitations

Review artifacts are local records. Hosted forge comments, pull requests, and merge APIs are not
connected in the Founding Preview.
