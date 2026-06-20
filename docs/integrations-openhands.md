# OpenHands Integration

LoopOS uses OpenHands as an optional runtime inspiration and future integration target.

## Current Adapter

`OpenHandsAdapter` exposes:

- `is_available()`
- `execute_command(cmd, cwd, timeout)`
- `read_file(path)`
- `write_file(path, content)`
- `apply_patch(patch)`

The adapter does not import private OpenHands runtime modules. If OpenHands is not installed or not callable, it falls back to LoopOS-native behavior or returns a structured unavailable observation.

## Rationale

OpenHands has useful runtime and sandbox concepts, but its full server/frontend stack is too large for the LoopOS MVP. LoopOS keeps its own AI-ISA, state, event, memory, and permission contracts.

## Future Work

- Detect an installed OpenHands SDK or stable CLI entry point.
- Translate LoopOS `EXEC_TERMINAL` and file operations into OpenHands runtime calls.
- Preserve LoopOS permission checks before delegation.
