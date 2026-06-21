# LoopOS Plugin Manifest Specification

Alpha plugins are discovered and audited as metadata. Discovery and installation never import or
execute plugin code.

Required YAML fields: `id`, `type`, `name`, `version`. Supported types are `provider`, `skill`,
`policy`, `gateway`, `mcp`, `execution_backend`, `benchmark`, and `agent_role`.

Recommended fields: `description`, `compatibility.loopos`, `required_tools`, `permissions`,
`risk_level`, `maintainers`, and `tests`. IDs are stable lowercase identifiers. Versions use semantic
versioning. Permissions must be explicit and minimal.

`policy.bypass`, unrestricted terminal/network access, secret reads, and filesystem access outside
the workspace fail or escalate audit. Installation copies only `manifest.yaml` into the local
registry. Executable plugin loading is outside the Alpha contract.
