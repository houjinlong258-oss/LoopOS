# Memory Governance

LoopOS Alpha writes durable memory through proposals and governance decisions.

## Flow

```text
run events
-> MemoryProposalExtractor
-> MemoryProposal
-> MemoryGovernance
-> MemoryRepository
-> JSONL audit + SQLite index
```

## Proposal Status

- `pending`: created but not accepted.
- `accepted`: accepted and written as memory.
- `rejected`: rejected by user or governance.
- `merged`: accepted as a conflicting or merge candidate.

## Checks

- Confidence must meet the write threshold.
- Source must be present.
- Tags are normalized to lowercase unique values.
- Duplicate active memory is rejected.
- Same-tag conflicting memory is marked as conflicted for review.
- Decay score is recalculated from success/failure counters when present.

## Storage

JSONL remains the readable audit trail. SQLite is an index for retrieval, review, profile, and proposal queries.
