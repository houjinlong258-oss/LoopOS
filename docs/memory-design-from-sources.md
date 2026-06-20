# Memory Design from Sources

## Letta-Inspired Design

LoopOS separates compact working context from archival memory. Working context is compiled per run by `ContextCompiler`. Archival memory is stored as governed `MemoryItem` records.

## Zep-Inspired Design

LoopOS ranks memory by confidence, recency, and tag overlap. The MVP stores relationship hints as tags and metadata; a graph database is out of scope.

## projectmem-Inspired Design

LoopOS uses event-sourced JSONL logs and a `PreActionGate` before execution. The gate can block repeated failures, warn about known failed approaches, and suggest reusable skills.

## MVP Storage

- Event log: JSONL.
- State store: JSON files per run.
- Beliefs and skills: JSONL stores.

SQLite can be added later behind the same interfaces if indexing becomes necessary.

## Governance Rules

Memory writes are reviewed for:

- confidence range
- missing source
- duplicate active memory
- conflict hints
- version/status metadata

Low-confidence or duplicate writes are rejected or downgraded rather than silently stored.
