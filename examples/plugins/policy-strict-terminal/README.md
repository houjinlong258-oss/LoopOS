# policy-strict-terminal

A sample policy pack plugin that hardens terminal execution beyond the
default L0-L5 baseline.

## What this policy does

- **Type:** `policy`
- **Risk:** low
- **Scope:** `terminal.execute`

Rules declared:

| Rule | Severity | Safety | Reason code |
|---|---|---|---|
| `terminal.block.curl_pipe_shell` | critical | L5 | `remote_code_execution_pipe` |
| `terminal.block.rm_rf_root` | critical | L5 | `dangerous_recursive_delete_root` |
| `terminal.require_approval.git_reset` | high | L3 | `destructive_git_operation` |
| `terminal.require_approval.sudo` | high | L3 | `privilege_escalation` |

The default in-tree `policies/safety/terminal.yaml` already covers these
patterns; this sample plugin shows how a community contributor can package
a stricter variant.

## Alpha contract

- Plugin manifests are metadata-only.
- Policy pack activation is opt-in and never overrides core safety rules.
- A distilled policy pack cannot grant new permissions.

## Install

```bash
loopos registry install examples/plugins/policy-strict-terminal
loopos registry audit examples/plugins/policy-strict-terminal
```
