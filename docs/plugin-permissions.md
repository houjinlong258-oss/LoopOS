# Plugin Permissions

## Why this exists

Permissions make plugin intent reviewable before any future runtime binding is considered.

## Core models

`permissions` describes requested capabilities, `required_tools` names syscall contracts, and
`risk_level` states the author estimate. Registry audit recalculates risk and reports unsafe or
understated declarations. Audit output includes:

- `permission_explanations`: human-readable meaning of each requested permission.
- `risk_explanation`: why effective risk equals or exceeds declared risk.
- `examples_validated`: whether the manifest includes metadata examples for reviewers.

## CLI usage

```bash
loopos registry audit examples/plugins/policy-strict-terminal/manifest.yaml
```

Example output:

```text
permissions_reviewed: policy:enforce:terminal
permission_explanations:
  policy:enforce:terminal: Allows a policy pack to constrain terminal execution.
risk_explanation: Declared and effective risk are both medium.
risk_level: medium
safe: true
```

## Safety boundaries

Manifest permissions are declarations, not grants. Policy OS and Syscall Router remain mandatory.
Unrestricted network, outside-workspace filesystem, unrestricted terminal, secret reads, and
policy bypass are unsafe capabilities.

## Current limitations

The Alpha registry does not enforce operating-system capabilities because it does not load plugin
code. Future runtime plugins require signatures, sandboxing, and explicit administrator approval.
