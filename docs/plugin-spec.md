# Plugin Registry

The Alpha registry validates and copies plugin manifests only. It supports provider, skill, policy,
gateway, MCP, execution backend, benchmark, and agent-role metadata. Discovery and audit never import
or execute plugin code.

Use `loopos registry list`, `search`, `install MANIFEST`, and `audit ID_OR_MANIFEST`. Unsafe
permissions, understated tool risk, missing maintainers, and missing tests are reported. The canonical
contract is `PLUGIN_SPEC.md` at the repository root.
