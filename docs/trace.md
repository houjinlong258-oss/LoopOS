# Trace and Replay

Each kernel step emits versioned events for instructions, policy decisions, syscalls, observations, evaluations, transitions, memory, skills, and signals. Events are append-only JSONL and are indexed in SQLite when a repository is active.

Replay reads events through a compatibility parser, reconstructs the selected state, and reports differences from the durable run record. It never calls terminal, file-write, Git-write, MCP, or network adapters.
