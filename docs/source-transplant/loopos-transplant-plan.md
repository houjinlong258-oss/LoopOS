# LoopOS Source Transplant Plan

**Purpose:** unify the Claude Code Main and Hermes Agent
audits into a single LoopOS v0.2 plan that decides what to
adopt, what to wrap, what to clean-room, what to reject, and
what to defer.

**Companion docs:**

- `license-and-provenance-audit.md` — license / provenance
  classification (binding).
- `hermes-agent-audit.md` — Hermes surface catalogue.
- `claude-code-main-audit.md` — Claude Code surface catalogue.
- `provider-runtime-map.md` (written next) — concrete
  Provider Runtime Registry map for v0.2.

---

## Summary

LoopOS v0.2 is a **governance kernel**, not a coding agent
and not a product surface. The two reference sources are
**design references**, not code forks.

- **Hermes Agent (MIT)** contributes the **provider runtime
  registry shape** (declarative `ProviderProfile`, lazy
  discovery, last-writer-wins, capability-driven lookup) and
  the **slash-command central registry shape** (CommandDef
  with name, description, category, aliases, args_hint,
  subcommands, platform gating).

- **Claude Code Main (proprietary)** contributes **only
  design intent**: the declarative permission JSON schema,
  the `allowed-tools` slash-command frontmatter, the
  phase-gated-with-confirmation workflow pattern, and the
  managed-overlay pattern. No code is borrowed.

- **LoopOS keeps its own architecture** — Pydantic v2 typed
  contracts, Kernel + ALI FSM + ACI commands + Policy OS +
  Syscall Router + Trace + Memory + Skill governance. The
  Provider Runtime Registry is added as a new substrate that
  the rest of LoopOS may use later.

The v0.2 implementation ships **only the Provider Runtime
Registry** (Phase S5 in this prompt). All other surfaces
(ACI runtime, ALI FSM extensions, skill marketplace, memory
provider plug-ins, gateway, ACP, TUI) are already partially
implemented or explicitly deferred.

---

## Source Classifications

(See `license-and-provenance-audit.md` for full details.)

| source | license | classification | direct reuse | clean-room | attribution |
|---|---|---|---|---|---|
| claude-code-main | Anthropic commercial terms (proprietary) | `proprietary_or_private_do_not_copy` | no | yes | informational only |
| hermes-agent-2026.6.19 | MIT (© 2025 Nous Research) | `restricted_reuse_with_attribution` | yes (MIT terms) | recommended | yes (preserve MIT notice) |

---

## Unified Mapping

| source | source concept | LoopOS concept | v0.2 decision | v0.3+ decision |
|---|---|---|---|---|
| claude-code-main | agent loop (turn-taking, tool repair) | `loopos.ali.fsm.AgentLoopFSM` | adopt_concept (already in tree) | extend with repair states |
| claude-code-main | tool invocation JSON contract | `loopos.aci.AgentCommand` | adopt_concept (already in tree) | extend with new `AgentCommandKind` entries |
| claude-code-main | bash sandbox + permission model | `loopos.syscalls.terminal` + `loopos.policy_os` | adopt_concept | add sandbox network policy |
| claude-code-main | file editing | `loopos.syscalls.file` + `loopos.data_guard` | adopt_concept | add diff-review UX |
| claude-code-main | permission JSON (`permissions.deny/ask/allowManagedPermissionRulesOnly`) | `loopos.policy_os.policy_yaml` | adopt_concept | publish a managed-policy schema |
| claude-code-main | managed-settings overlay | `loopos.policy_os.governance.managed_overlay` | defer_to_v0_3_plus | implement when MDM is in scope |
| claude-code-main | slash-command template (`allowed-tools:` frontmatter) | `loopos.ali.commands.slash_template` | adopt_concept (deferred) | implement as a `CommandTemplate` pydantic model |
| claude-code-main | `!command` inline context | `loopos.context.command_context` | defer_to_v0_3_plus | implement when AIL prompt assembly is in scope |
| claude-code-main | hooks (`PreToolUse`, `PostToolUse`, `Stop`, ...) | `loopos.trace.hooks` | defer_to_v0_3_plus | implement hook points on Trace events |
| claude-code-main | 7-phase feature-dev workflow | `loopos.ali.phased_workflow` | defer_to_v0_3_plus | implement when multi-phase workflows ship |
| claude-code-main | sub-agents (scoped personas) | `loopos.ali.delegation` | defer_to_v0_3_plus | implement when delegation ships |
| claude-code-main | plugin directory layout | `loopos.plugins.directory_layout` | defer_to_v0_3_plus | implement when plugin loader ships |
| claude-code-main | data collection / telemetry | out of LoopOS scope | reject_for_v0_2 | LoopOS never collects telemetry |
| hermes-agent | provider registry + `ProviderProfile` dataclass | `loopos.providers.registry` + `loopos.providers.models.ModelProviderProfile` | **adopt_concept (this prompt — Phase S5)** | extend with discovery + live fetch |
| hermes-agent | 28 bundled provider plugins | `loopos.providers` built-in profiles (loaded from `providers/defaults.yaml`) | **adopt_concept (this prompt — Phase S5)** | keep YAML as data source |
| hermes-agent | `register_provider` / `get_provider_profile` / `list_providers` API | `ProviderRegistry.register/get/list/find_by_capability/validate_profile/load_builtin_profiles` | **adopt_concept (this prompt — Phase S5)** | keep API shape; add discovery in v0.3+ |
| hermes-agent | lazy plugin discovery (bundled → user → legacy) | out of v0.2 scope | reject_for_v0_2 | add in v0.3+ with explicit `plugins_dirs` config |
| hermes-agent | `ProviderProfile.fetch_models` live probe | out of v0.2 scope | reject_for_v0_2 | add in v0.3+ as a documented hook (not auto-called) |
| hermes-agent | `ProviderProfile` hooks (`prepare_messages`, `build_extra_body`, ...) | `ModelProviderProfile` hook methods (metadata-only stubs) | **adopt_concept (this prompt — Phase S5)** | implement hooks in v0.3+ when transport lands |
| hermes-agent | `HERMES_OVERLAYS` (transport-specific quirks) | not relevant | reject_for_v0_2 | LoopOS does not own transport quirks |
| hermes-agent | `hermes_cli/commands.py` central command registry | `loopos.cli` existing registry | adopt_concept (deferred) | extend LoopOS `cli/` with `CommandDef` shape |
| hermes-agent | `hermes doctor` | `loopos.cli doctor` | defer_to_v0_3_plus | wrap as adapter to `loopos.readiness` |
| hermes-agent | `hermes model`, `hermes setup`, `hermes cron`, `hermes skills`, `hermes memory` | `loopos.cli` subcommands | defer_to_v0_3_plus | implement when underlying capability ships |
| hermes-agent | `hermes gateway`, `hermes acp`, `hermes web` | out of LoopOS scope | reject_for_v0_2 | LoopOS is kernel, not product |
| hermes-agent | `hermes_cli/skin_engine.py` theming | out of LoopOS scope | reject_for_v0_2 | LoopOS v0.2 has no TUI |
| hermes-agent | `hermes_constants.py` profile system | out of LoopOS scope | reject_for_v0_2 | LoopOS multi-tenancy is different |
| hermes-agent | terminal backends (`tools/environments/`) | `loopos.execution` | defer_to_v0_3_plus | add `Environment` ABC in v0.3+ |
| hermes-agent | cron scheduler (`cron/`) | `loopos.execution.scheduler` | defer_to_v0_3_plus | implement when scheduler ships |
| hermes-agent | memory provider plugins (ABC) | `loopos.memory` | defer_to_v0_3_plus | implement when Memory Governance v0.3+ ships |
| hermes-agent | skill frontmatter conventions | `loopos.skills` | defer_to_v0_3_plus | adopt `name/description/version/license/platforms` subset |
| hermes-agent | delegation (`tools/delegate_tool.py`) | `loopos.ali.delegation` | defer_to_v0_3_plus | implement when sub-sessions ship |
| hermes-agent | tracing / logging (`hermes_logging.py`, `logs.py`) | `loopos.trace` | adopt_concept (already partially in tree) | extend with profile-aware logs |
| hermes-agent | context compression | `loopos.context` | defer_to_v0_3_plus | implement when Context Governance v0.3+ ships |
| hermes-agent | auxiliary LLM multiplexing | `loopos.providers.selection` | defer_to_v0_3_plus | implement when selection policy ships |
| hermes-agent | `SKILL.md` frontmatter standards | `loopos.skills.frontmatter` | defer_to_v0_3_plus | adopt subset of frontmatter |

---

## Provider Runtime Recommendation

**Status:** implemented in this prompt's Phase S5.

**Decision: clean-room reimplement with Hermes as design reference.**

The Provider Runtime Registry is the one substrate where Hermes's
shape is so close to what LoopOS needs that a from-scratch
reimplementation would just rediscover the same shape. LoopOS
therefore:

1. **Adopts the field set** of Hermes `ProviderProfile`
   (identity, auth, endpoint, capabilities, hook slots, model
   metadata) but re-expresses each field through LoopOS's
   Pydantic v2 + `ConfigDict(extra="forbid")` + `Literal`
   enum style.

2. **Adopts the registry API shape** (`register`, `get`,
   `list`) but adds three LoopOS-specific operations
   (`find_by_capability`, `validate_profile`,
   `load_builtin_profiles`) that fit the existing
   `loopos/providers/defaults.yaml` schema.

3. **Rejects lazy plugin discovery and live model probing**
   for v0.2. The registry is **metadata-only**: no network
   calls, no filesystem scanning beyond loading one YAML
   file, no client construction. This is the safest possible
   first substrate.

4. **Loads built-in profiles from the existing
   `providers/defaults.yaml`** (which already lists 27 of
   Hermes's 28 providers). The registry treats YAML as the
   canonical data source.

5. **Keeps MIT attribution** in the registry docstrings.

For v0.3+ the registry grows:

- plugin discovery (`HERMES_HOME/plugins/loopos/providers/<name>/`)
- live `fetch_models()` probe behind a feature flag
- `ModelProviderProfile` subclass hooks (currently stubs)
- per-provider `prepare_messages` / `build_extra_body` implementations

---

## CLI Surface Recommendation

**Status:** deferred.

LoopOS already has a `loopos/cli/` module. The Hermes
`COMMAND_REGISTRY` shape (`CommandDef` dataclass with name,
description, category, aliases, args_hint, subcommands,
cli_only, gateway_only, gateway_config_gate) is a useful
reference for v0.3+ when the CLI grows beyond its current
surface.

For v0.2, no CLI changes are made.

---

## ACI Recommendation

**Status:** already implemented in v0.2 (Phase 2 — out of scope of this prompt).

LoopOS `loopos/aci/models.py` already provides the `AgentCommand`
and `AgentCommandResult` Pydantic v2 contracts. The Hermes /
Claude Code audit confirms the design direction (typed
command contract, structured observation, convergence hint)
without identifying any new ACI surface to add.

The Provider Runtime Registry does **not** live inside
`loopos/aci/` — it is a substrate that ACI may consume in
v0.3+ when LLM runtime integration lands.

---

## ALI Recommendation

**Status:** already implemented in v0.2 (Phase 3 — out of scope of this prompt).

LoopOS `loopos/ali/models.py` and `loopos/ali/fsm.py` provide
the FSM (AgentLoopFSM), session, and event-record contracts.
The Hermes / Claude Code audit confirms the design direction
(repair / replan / wait-approval / halt states; transition
table as data) without identifying any new ALI surface to
add in this prompt.

---

## Skills / Memory Recommendation

**Status:** deferred to v0.3+.

Hermes skill frontmatter (`name`, `description`, `version`,
`author`, `license`, `platforms`, `metadata.hermes.*`) and
memory provider ABC are useful references but the LoopOS
`loopos/skills/` and `loopos/memory/` modules are not in
this prompt's scope. No changes are made.

---

## Gateway / ACP Recommendation

**Status:** rejected for v0.2 and v0.3+.

LoopOS is a kernel. It does not own a messaging gateway or
an ACP adapter. These are product-surface concerns that
belong to consumer products, not the OS itself.

---

## Rejected Items

```text
- claude-code-main: actual agent runtime source (NOT IN TREE).
- claude-code-main: data collection / telemetry.
- claude-code-main: GitHub Actions issue-triage workflows.
- claude-code-main: devcontainer configuration.
- claude-code-main: marketing copy, branding, trademarks.
- hermes-agent: hermes-internal state modules (hermes_state.py,
  hermes_logging.py, hermes_time.py, hermes_constants.py).
- hermes-agent: gateway platform adapters (~20 platforms).
- hermes-agent: kanban dispatcher.
- hermes-agent: skill curator.
- hermes-agent: TUI (ui-tui/, tui_gateway/) — no TUI in v0.2.
- hermes-agent: skin engine — no theming in v0.2.
- hermes-agent: HERMES_OVERLAYS transport-specific quirks.
- hermes-agent: models.dev catalog integration.
- hermes-agent: webhook/api_server platforms.
- hermes-agent: profile system (HERMES_HOME multi-instance).
- hermes-agent: image-gen / TTS / STT providers.
```

## Deferred Items

```text
- ACI runtime extension (model-provider-aware).
- ALI FSM extension (provider-aware turn selection).
- LoopOS `loopos.cli` extension with `CommandDef` registry.
- LoopOS `loopos.cli doctor` (readiness/UX).
- LoopOS `loopos.cli status` / `logs`.
- LoopOS `loopos.cli tools` (capability config UX).
- LoopOS `loopos.cli model` / `models` / `model` switch.
- LoopOS `loopos.cli cron` / `setup` / `sessions`.
- LoopOS `loopos.plugins` directory layout.
- LoopOS `loopos.context` cache-invariant + compression.
- LoopOS `loopos.execution` Environment ABC.
- LoopOS `loopos.execution.scheduler` cron.
- LoopOS `loopos.skills` frontmatter + skill loader.
- LoopOS `loopos.memory` provider ABC.
- LoopOS `loopos.ali.delegation` subagent tool.
- LoopOS `loopos.readiness` doctor / readiness surface.
- LoopOS Provider plugin auto-discovery (v0.3+).
- LoopOS Provider live `fetch_models` probe (v0.3+).
```

---

## Stage Plan

### Stage 1 — Provider Runtime Registry (this prompt — Phase S5)

**Deliverables:**

- `loopos/providers/__init__.py`
- `loopos/providers/models.py`
- `loopos/providers/registry.py`
- `tests/test_provider_registry.py`
- `docs/source-transplant/provider-runtime-map.md`
- README.md minimal update
- CHANGELOG.md minimal unreleased entry

**Capability surface:**

- `ProviderKind` enum (Literal): `openai_compatible`, `anthropic_messages`, `gemini`, `bedrock`, `custom_openai_compatible`, `local_openai_compatible`
- `ProviderAuthMode` enum (Literal): `api_key`, `oauth_external`, `aws_sdk`, `none`
- `ModelCapability` enum (Literal): `text`, `reasoning`, `coding`, `tools`, `vision`, `audio`, `embeddings`, `local`
- `ModelProviderProfile` (Pydantic v2): full metadata contract
- `ProviderRegistry`: `register`, `get`, `list`, `find_by_capability`, `validate_profile`, `load_builtin_profiles`
- Built-in profiles loaded from `providers/defaults.yaml`

**Constraints:**

- No new dependencies.
- No network calls.
- No filesystem scanning beyond the YAML.
- All hooks stubbed or absent (no `prepare_messages`,
  `build_extra_body`, `fetch_models` implementations).
- Deterministic ordering for `list()` and `find_by_capability`.

### Stage 2 — ACI / Coding Agent Bridge (next branch — out of scope here)

When the v0.2.1 branch lands, `loopos/aci/` can be extended
to expose a `provider_hint` field on `AgentCommand` and let
the runner resolve it via `ProviderRegistry.find_by_capability`.

### Stage 3 — ALI / Session FSM (next-next branch — out of scope here)

When ALI v0.3+ lands, the session can carry a
`provider_selection` hint and the FSM can emit a
`provider_unavailable` event when the registry returns no
match.

---

## Implementation Boundaries (binding for Stage 1)

1. **Do not import hermes-agent source code.** Only read it.
2. **Do not modify `loopos/kernel/*` or `KernelLoopEngine`.**
3. **Do not modify `loopos/aci/*`, `loopos/ali/*`, `loopos/freedom/*`, `loopos/policy_os/*`.**
   The Provider Runtime Registry is a new substrate, not a
   refactor of existing modules.
4. **Do not add new third-party dependencies.**
5. **Do not call any network APIs.** Metadata-only.
6. **Do not vendor Claude Code Main code.**
7. **Do not modify `dist/`, `docs/release-notes/`,
   `docs/reports/`, or the `v0.1.0` tag.**
8. **Do not push.**
