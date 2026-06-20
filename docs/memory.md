# Memory

LoopOS memory is structured and governed. It is not raw transcript text.

## Memory Types

- Events: append-only JSONL audit trail.
- State: one JSON file per run.
- Beliefs/preferences/facts/failures: governed `MemoryItem` records.
- Skills: reusable execution traces compressed from successful events.

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

## Governance

`MemoryGovernance` checks:

- confidence threshold
- source presence
- duplicate active memory
- conflict hints
- version metadata

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
