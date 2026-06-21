# Plugin Development

## Why this exists

LoopOS plugins are metadata-first extension contracts. The registry validates and copies manifests
without importing or executing plugin code.

## Core models

`PluginManifest` declares type, compatibility, license, documentation, tools, permissions, risk,
maintainers, and tests. `PluginAuditResult` explains permission and risk findings. `PluginRegistry`
provides local search, audit, install, and list operations.

## CLI usage

```bash
loopos registry audit examples/plugins/skill-pytest-repair/manifest.yaml
loopos registry install examples/plugins/skill-pytest-repair/manifest.yaml
loopos registry list
```

Example output:

```text
plugin_id: skill-pytest-repair
safe: true
risk_level: medium
permission_explanations:
  workspace:read: Allows reading files inside the active workspace only.
risk_explanation: Declared and effective risk are both medium.
```

## Contributor checklist

- Add `license` and `documentation` to every manifest.
- Keep plugin examples metadata-only; installation copies the manifest and does not import code.
- Explain every custom permission in docs or metadata.
- Provide deterministic tests or example validation evidence.
- Do not request `policy.bypass`, unrestricted filesystem, unrestricted terminal, unrestricted
  network, or secret-read permissions.

## Safety boundaries

Installation copies validated metadata only. A manifest cannot grant itself tools, bypass policy,
or execute code. `policy.bypass`, unrestricted secrets, filesystem, terminal, and network access
are rejected or escalated.

## Current limitations

There is no remote marketplace, signature verification, dependency installation, or runtime code
loader in the Founding Preview. Start from `examples/plugins/` and follow `PLUGIN_SPEC.md`.
