# Governance

LoopOS uses maintainer review for the Kernel and metadata-based contribution for the ecosystem.

## Ownership

- Core: AIL, Kernel, Policy OS, syscalls, execution, trace, memory governance, and release tooling.
- Ecosystem: provider, skill, policy, gateway, MCP, backend, benchmark, and agent-role plugins.
- Registry: manifest validation, permission audit, compatibility metadata, and revocation records.

Maintainers approve releases, security changes, core contracts, and registry policy. Significant
architecture or compatibility changes use the RFC process. High-risk code cannot be approved only
by its producer; verification evidence and independent review are required.

Decisions are recorded in issues, RFCs, or release notes. Automatic merge is not part of Alpha.
