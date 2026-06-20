# Memory

LoopOS memory is structured and governed. It is not raw transcript text.

## Memory Types

- Events: append-only JSONL audit trail.
- State: one JSON file per run.
- Beliefs/preferences/facts/failures: governed `MemoryItem` records.
- Skills: reusable execution traces compressed from successful events.
- Proposals: pending memory writes that must be accepted or rejected.
- User profile: key/value user model indexed for context rendering.

## Storage

Alpha uses JSONL + SQLite:

- JSONL and JSON remain the human-readable source of truth for audit and compatibility.
- SQLite stores query indexes for runs, events, memory items, skills, proposals, and user profile.
- `memory reindex` rebuilds SQLite from existing JSON/JSONL without changing original files.

## Memory Item Fields

- `id`
- `type`
- `content`
- `confidence`
- `source`
- `created_at`
- `updated_at`
- `version`
- `tags`
- `conflicts`
- `status`
- `layer`
- `scope`
- `metadata`
- `expires_at`
- `last_used_at`
- `usage_count`
- `success_count`
- `failure_count`
- `decay_score`

## Governance

`MemoryGovernance` checks:

- confidence threshold
- source presence
- duplicate active memory
- conflict hints
- version metadata
- scope/layer validity
- tag canonicalization
- conflict and merge hints
- decay scoring

## Retrieval

`MemoryRetriever` ranks by:

- confidence
- recency
- tag overlap

## Pre-Action Gate

`PreActionGate` checks before execution:

- repeated failed commands
- blocked command patterns
- memories that say an approach failed
- relevant skills that can replace a new action

## CLI

```bash
python -m loopos.cli.app memory list
python -m loopos.cli.app memory search pytest
python -m loopos.cli.app memory propose --from-run RUN_ID
python -m loopos.cli.app memory review
python -m loopos.cli.app memory accept PROPOSAL_ID
python -m loopos.cli.app memory reject PROPOSAL_ID
python -m loopos.cli.app memory reindex
python -m loopos.cli.app profile show
python -m loopos.cli.app profile set tone concise
```
