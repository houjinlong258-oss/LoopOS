# Computer Control Safety Boundary

Computer Control is not silent remote control and not an OS-permission bypass.

Rules:

- default mode is dry-run or observe-only;
- local control requires explicit `--allow-computer-control`;
- high and critical actions require approval;
- critical actions are blocked by default unless explicitly overridden by a
  higher-level audited permission set;
- screenshots and clipboard content are redacted by default;
- raw screenshots are not persisted unless explicitly allowed;
- replay never re-executes actions;
- optional local/CUA/Codex adapters are unavailable by default and do not grant
  permissions themselves.

The runtime emits checkpoints and LAIL signals so every action is visible in
the loop trace.
