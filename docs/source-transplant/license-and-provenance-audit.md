# License & Provenance Audit — LoopOS v0.2 Source Transplant

**Purpose:** determine whether the two reference sources can be directly
reused, reused with attribution, or must be clean-room reimplemented
before any concept, interface, or behavior is transplanted into
LoopOS v0.2.

**Scope:** `claude-code-main` (Anthropic PBC) and
`hermes-agent-2026.6.19` (Nous Research). Only license/provenance
classification; concept-by-concept decisions live in the unified
transplant plan (`loopos-transplant-plan.md`).

**Audit date:** 2026-06-22
**Branch:** `v0.2/true-agent-os-kernel`

---

## 1. Summary

| source | classification | direct reuse | clean-room required | attribution required |
|---|---|---|---|---|
| `claude-code-main` (Anthropic PBC) | **proprietary_or_private_do_not_copy** | no | **yes** | yes (informational only) |
| `hermes-agent-2026.6.19` (Nous Research) | **restricted_reuse_with_attribution** | **yes** (MIT terms) | optional | **yes** (MIT) |

Neither source may be vendored or merged wholesale. Hermes may be
quoted and adapted per MIT; Claude Code Main may only inform design.

---

## 2. Per-source detail

### 2.1 claude-code-main

| field | value |
|---|---|
| root | `D:\LoopOS\移植参考的源码\claude-code-main\claude-code-main\` |
| LICENSE file | `LICENSE.md` (1 line, 150 bytes) |
| LICENSE text | `© Anthropic PBC. All rights reserved. Use is subject to Anthropic's Commercial Terms of Service (https://www.anthropic.com/legal/commercial-terms).` |
| metadata files | `package.json` (npm package, closed agent binary), `README.md`, `SECURITY.md`, `.github/ISSUE_TEMPLATE/*.yml`, `examples/mdm/managed-settings.json`, `examples/settings/*.json` |
| project origin | Anthropic PBC |
| license type | **Proprietary — commercial terms** (no OSS license) |
| distribution method | npm `@anthropic-ai/claude-code`; installer scripts `claude.ai/install.sh` and `claude.ai/install.ps1` |
| core agent source | **Not present in this tree.** The repository is a release/installation artifact: it ships plugins, settings examples, slash-command templates, CI workflows, and devcontainer configuration. The actual agent runtime is a closed-source npm package. |
| plugins shipped | `agent-sdk-dev`, `claude-opus-4-5-migration`, `code-review`, `commit-commands`, `explanatory-output-style`, `feature-dev`, `frontend-design`, `hookify`, `learning-output-style`, `plugin-dev`, `pr-review-toolkit`, `ralph-wiggum`, `security-guidance` (each is a README + `.claude-plugin/marketplace.json` manifest) |
| slash-command templates | `.claude/commands/commit-push-pr.md`, `dedupe.md`, `triage-issue.md` (each a structured prompt with `allowed-tools` and `description` frontmatter) |
| classification | `proprietary_or_private_do_not_copy` |
| direct code reuse allowed? | **NO.** Commercial terms + copyright reservation forbid redistribution of agent-derived code. |
| clean-room required? | **YES.** Only the published plugin READMEs, slash-command prompt templates, and `examples/settings/*.json` are usable as design references. Any code pattern observed in those files must be re-expressed in LoopOS-native style without copying. |
| attribution required? | Informational only ("inspired by Claude Code's permission model") in design docs; never a code-level attribution. |
| notes | `settings-strict.json`, `settings-bash-sandbox.json`, `settings-lax.json` describe a permission/sandbox schema (`permissions.deny/ask`, `sandbox.network.*`, `allowManagedPermissionRulesOnly`). These shape references are public and reusable as conceptual models. The `examples/mdm/managed-settings.json` file documents a managed-deployment policy schema. |

### 2.2 hermes-agent-2026.6.19

| field | value |
|---|---|
| root | `D:\LoopOS\移植参考的源码\hermes-agent-2026.6.19 (1)\hermes-agent-2026.6.19\` |
| LICENSE file | `LICENSE` (21 lines, MIT) |
| LICENSE text | `MIT License — Copyright (c) 2025 Nous Research` |
| metadata files | `pyproject.toml`, `MANIFEST.in`, `package.json`, `setup.py`, `README.md`, `README.ur-pk.md`, `README.zh-CN.md`, `AGENTS.md`, `SECURITY.md`, `CONTRIBUTING.md`, `flake.nix`, `flake.lock`, `Dockerfile`, `docker-compose.yml`, `pyproject.toml` |
| project origin | Nous Research |
| license type | **MIT License** |
| core agent source | **Present in this tree.** The full agent runtime (`run_agent.py`, `cli.py`, `model_tools.py`, `toolsets.py`, `hermes_state.py`, `hermes_cli/`, `agent/`, `tools/`, `plugins/`, `gateway/`, `cron/`, `skills/`, `optional-skills/`, `acp_adapter/`, `tui_gateway/`, `ui-tui/`, `apps/`, `scripts/`, `tests/`) is shipped under MIT. |
| provider plugin count | **28 bundled provider profiles** under `plugins/model-providers/<name>/` (alibaba, alibaba-coding-plan, anthropic, arcee, azure-foundry, bedrock, copilot, copilot-acp, custom, deepseek, gemini, gmi, huggingface, kilocode, kimi-coding, minimax, nous, novita, nvidia, ollama-cloud, openai-codex, opencode-zen, openrouter, qwen-oauth, stepfun, xai, xiaomi, zai) |
| terminal backends | 9 backends under `tools/environments/` (base, local, docker, ssh, modal, daytona, singularity, managed_modal, file_sync) |
| gateway platforms | ~20 messaging adapters under `gateway/platforms/` (telegram, discord, slack, whatsapp, homeassistant, signal, matrix, mattermost, email, sms, dingtalk, wecom, weixin, feishu, qqbot, bluebubbles, yuanbao, webhook, api_server) |
| classification | `restricted_reuse_with_attribution` |
| direct code reuse allowed? | **YES** under MIT terms, including modification and redistribution, **provided** the MIT copyright + permission notice is preserved in derivative works. |
| clean-room required? | **No, but recommended** for files intended to ship as LoopOS core. LoopOS governance rules forbid wholesale vendor merges, so even MIT-licensed code must be re-expressed through LoopOS's Pydantic v2 + Policy OS + Kernel architecture before adoption. |
| attribution required? | **YES.** Any code or design borrowed from Hermes must carry a header or docstring noting its MIT origin (Nous Research, hermes-agent-2026.6.19). This audit treats such borrowing as "inspired by" rather than "forked from". |
| notes | The bundled `providers/base.py` `ProviderProfile` dataclass is the cleanest reference for the LoopOS `ModelProviderProfile` contract; it is reused conceptually (fields, hooks, last-writer-wins semantics) but **not** copied verbatim. The bundled `plugins/model-providers/<name>/` directories are excellent shape references but their `__init__.py` files must NOT be copied because they reference hermes-internal hooks (`hermes_cli`, `agent/transports/`, etc.). |

---

## 3. Per-source reusable surface

### 3.1 claude-code-main — reusable surfaces

```text
1. examples/settings/settings-strict.json
   Permission model (deny/ask) and sandbox schema are public design.

2. examples/settings/settings-bash-sandbox.json
   Bash sandbox + network policy schema.

3. examples/settings/settings-lax.json
   Permissive end of the permission spectrum.

4. examples/mdm/managed-settings.json
   Managed-deployment policy schema (allowManagedPermissionRulesOnly,
   allowManagedHooksOnly, strictKnownMarketplaces).

5. .claude/commands/*.md (commit-push-pr, dedupe, triage-issue)
   Slash-command prompt template convention:
     ---
     allowed-tools: Bash(git ...:*), Bash(gh pr create:*)
     description: <one-line>
     ---
   Reusable as a LoopOS AIL/ACI prompt-injection template shape.

6. plugins/<name>/README.md
   Plugin authoring conventions (frontmatter, capability
   declarations, sandboxing expectations). Reusable as
   "LoopOS Skill Governance" shape reference.

7. .github/workflows/*.yml
   CI patterns (issue triage, dedupe, autoclose, label sweeps).
   Informational only — LoopOS has its own CI.
```

### 3.2 hermes-agent-2026.6.19 — reusable surfaces (under MIT)

```text
1. providers/base.py
   ProviderProfile dataclass — fields and hook shape. Concept
   reusable; verbatim copy forbidden (LoopOS governance requires
   Pydantic v2 typed contracts and explicit metadata separation).

2. providers/__init__.py
   register_provider() / get_provider_profile() / list_providers()
   API shape — last-writer-wins, alias resolution, lazy discovery.
   LoopOS re-implements this with explicit "no auto-discovery"
   boundary for v0.2.

3. hermes_cli/commands.py (CommandDef dataclass + COMMAND_REGISTRY)
   Central command-registry shape — name, description, category,
   aliases, args_hint, subcommands, cli_only, gateway_only. Reusable
   as LoopOS CLI surface design pattern.

4. plugins/model-providers/<name>/
   28 bundled profiles demonstrate the canonical "one directory
   per provider with __init__.py" plugin shape. LoopOS treats this
   as design intent but skips the plugin auto-discovery for v0.2.

5. tools/environments/<name>.py
   9 terminal backends (local, docker, ssh, modal, daytona,
   singularity, ...). LoopOS Execution Backend is the v0.3+ home
   for these; v0.2 defers.

6. hermes_cli/doctor.py
   "hermes doctor" pattern: schema-version check, /models probe,
   auth resolution check, dependency check. Reusable as LoopOS
   readiness/doctor CLI surface in v0.3+.

7. hermes_cli/skin_engine.py
   Data-driven skin/theme system. Reusable as LoopOS CLI theming
   in v0.3+ (defer for v0.2).

8. cron/jobs.py + cron/scheduler.py
   Job store + tick loop with file-lock + catchup window. Reusable
   as LoopOS Scheduler / Automation in v0.3+ (defer for v0.2).

9. skills/ + plugins/<other>/
   Frontmatter convention (name, description, version, author,
   license, platforms, metadata.hermes.tags). Reusable as LoopOS
   Skill Governance v0.3+ shape.

10. hermes-already-has-routines.md
    Documents non-core-but-shipped behaviors (kanban, curator,
    delegation). Informational reference only.
```

---

## 4. Per-source forbidden surface

### 4.1 claude-code-main — forbidden surface

```text
1. Any agent runtime source code (NOT PRESENT in tree, but if
   encountered elsewhere must not be copied).

2. Any UI screenshots, marketing text, or product copy.

3. Any Anthropic trademark, logo, or branding.

4. The npm package name "@anthropic-ai/claude-code" and any
   identifier that implies a Claude Code fork.
```

### 4.2 hermes-agent-2026.6.19 — forbidden surface

```text
1. Wholesale import of any module that depends on hermes-internal
   state (hermes_state.py, hermes_cli/, agent/, run_agent.py,
   model_tools.py, cli.py, gateway/run.py, hermes_logging.py,
   hermes_time.py, hermes_constants.py). These files reference
   $HERMES_HOME, profiles, and cross-module globals that LoopOS
   does not share.

2. The literal string "hermes" in any LoopOS public symbol,
   command name, config key, or env var.

3. Any branding, banner, spinner face, or theme string from
   hermes_cli/.

4. The MCP server catalog as a curated list — Hermes's
   optional-mcps is Hermes-specific; LoopOS does not vendor it.
```

---

## 5. Boundary statement

The LoopOS v0.2 Provider Runtime Registry is implemented as a
**clean-room** contract: it borrows the **shape** of Hermes's
`ProviderProfile` (identity, auth, endpoint, capability, hook
slots) and the **shape** of Hermes's registry API
(`register`, `get`, `list`, `find_by_capability`), but every
Python class is re-expressed through LoopOS's Pydantic v2 +
ConfigDict(extra="forbid") + Literal-enum style. No line of
Hermes code is copied.

The Claude Code Main contributes only **design intent**: the
permission/sandbox schema and the slash-command template
convention. None of its code is referenced, copied, or vendored.

This audit is binding for all subsequent LoopOS v0.2 work in the
`docs/source-transplant/` directory.
