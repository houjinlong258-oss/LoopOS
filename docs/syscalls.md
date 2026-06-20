# Syscall Layer

All external LoopOS actions use `SyscallCall` and return `SyscallResult`. The router owns schema validation, Policy OS evaluation, approval checks, adapter invocation, normalized observations, and trace emission.

The MVP syscalls are `terminal.exec`, `file.read`, `file.write`, `git.status`, and `git.diff`. File paths are resolved inside the run workspace. Dry-run and replay never invoke side-effecting adapters.
