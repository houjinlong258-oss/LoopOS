# Safety Model

LoopOS treats terminal execution as privileged behavior. The runtime must analyze a command before it is executed.

## Risk Levels

- `low`: read-only or locally bounded commands such as listing files, reading workspace files, running deterministic tests, and git status.
- `medium`: commands that may write project files, install dependencies, or make local state changes.
- `high`: destructive or broad operations that could lose work or alter the machine, such as recursive deletion, hard git resets, privileged Docker, or network upload.
- `blocked`: commands that should never run in the MVP, such as disk formatting, `curl | bash`, private key reads, broad process kills, or global git config changes.

## Approval Rules

- `blocked`: never execute.
- `high`: requires explicit approval and is rejected in non-interactive mode.
- `medium`: may execute only when policy permits the path and command shape.
- `low`: can execute when path and timeout checks pass.

The `--yes` CLI flag only applies to low and medium risk behavior. It cannot bypass high or blocked decisions.

## Terminal Policy Checks

`PermissionPolicy` checks:

1. Command risk from `CommandRiskAnalyzer`.
2. Allowlisted working directories.
3. Denylisted patterns.
4. Approval-required patterns.
5. Timeout caps.
6. Network restrictions.

## Known MVP Limits

- Command parsing is conservative string analysis, not a full shell parser.
- Windows shell built-ins are supported by running through the system shell after policy checks.
- Future hardening should add per-platform command tokenization, seccomp/container isolation, and stronger filesystem sandboxing.
