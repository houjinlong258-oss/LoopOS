# Claude Code Main Audit — LoopOS v0.2 Source Transplant

**Purpose:** catalogue Claude Code Main's coding-agent
execution design surfaces and classify each for LoopOS v0.2.

**Source:** `D:\LoopOS\移植参考的源码\claude-code-main\claude-code-main\` (Anthropic PBC, commercial terms, core agent closed-source).

**License:** see `license-and-provenance-audit.md` —
Claude Code Main is classified
`proprietary_or_private_do_not_copy`. Only the published
plugins, slash-command templates, settings examples, and CI
workflows are usable as design references. No code may be
copied.

**Note on source shape:** the Claude Code repository ships
only **the surrounding shell** (plugins, slash-command
templates, settings examples, CI workflows, devcontainer,
issue templates, MDM examples). The actual agent runtime is a
closed-source npm package (`@anthropic-ai/claude-code`). Most
audit items therefore describe **observable behavior** (from
README, plugin READMEs, settings examples) rather than **code
patterns** (which are not present).

**Audit date:** 2026-06-22

---

## 1. Components

| component | source files | behavior | LoopOS target | decision | notes |
|---|---|---|---|---|---|
| Agent loop (turn-taking, tool calls, repair) | NOT IN TREE (closed npm) | synchronous turn loop with tool-call repair | `loopos.ali.fsm.AgentLoopFSM` (existing) | adopt_concept | LoopOS ALI FSM is the LoopOS-native equivalent; no direct code reference |
| Tool invocation (`Bash`, `Read`, `Edit`, `Write`, `Glob`, `Grep`, `WebSearch`, `WebFetch`, ...) | NOT IN TREE | structured tool calls with JSON args | `loopos.aci.AgentCommand` (existing) | adopt_concept | LoopOS ACI is the LoopOS-native equivalent |
| Shell / Bash execution | NOT IN TREE (closed), `settings-bash-sandbox.json` for policy | sandboxed bash with permission policy | `loopos.syscalls.terminal` (existing) | adopt_concept | settings JSON gives the schema |
| File editing (`Edit`/`Write` tool) | NOT IN TREE (closed) | structured file edits with diff review | `loopos.syscalls.file` (existing) | adopt_concept | LoopOS already has file syscalls + Data Guard |
| Permission / approval model (`permissions.deny`, `permissions.ask`, `allowManagedPermissionRulesOnly`) | `examples/settings/settings-strict.json`, `settings-bash-sandbox.json`, `settings-lax.json`, `examples/mdm/managed-settings.json` | declarative permission policy with three modes (strict/lax/bash-sandbox) | `loopos.policy_os.PolicyDecision` (existing) | adopt_concept | LoopOS Policy OS already covers this; the Claude Code settings JSON is a useful schema reference |
| Managed policy rules + managed hooks | `examples/mdm/managed-settings.json` | MDM-deployed settings cannot be overridden by users (`allowManagedPermissionRulesOnly`, `allowManagedHooksOnly`, `strictKnownMarketplaces`) | `loopos.policy_os.governance.managed_overlay` (defer) | defer_to_v0_3_plus | useful pattern; LoopOS v0.2 does not have managed deployments yet |
| Permission sandbox (network allowlist, Unix sockets, local binding, httpProxy, socksProxy) | `examples/settings/settings-bash-sandbox.json::sandbox.network` | declarative network sandbox with allowlist + socket controls | `loopos.policy_os.sandbox.network` (defer) | defer_to_v0_3_plus | shape reusable; impl deferred |
| Slash-command template convention (`---\nallowed-tools: Bash(...:*)\ndescription: ...\n---\n\n<context>\n\n<task>`) | `.claude/commands/commit-push-pr.md`, `dedupe.md`, `triage-issue.md` | structured prompt-injection template with allowed-tool scoping and `!<command>` inline context fetching | `loopos.ali.commands.slash_template` (defer) | adopt_concept | the template shape (frontmatter + context + task) is reusable as a LoopOS AIL/ACI prompt-injection template |
| `allowed-tools:` frontmatter field | `.claude/commands/commit-push-pr.md` | per-command allowlist of `Bash(...)` patterns | `loopos.policy_os.command.capability_filter` (defer) | adopt_concept | fits LoopOS `CommandCapability` model |
| `!git status` inline-command context fetching | `.claude/commands/commit-push-pr.md` | inject command output into the prompt at submit time | `loopos.context.command_context` (defer) | adopt_concept | useful for LoopOS AIL prompt assembly |
| Plugin discovery via `.claude-plugin/marketplace.json` | `plugins/<name>/.claude-plugin/marketplace.json` (per plugin), `plugins/README.md` | one-marketplace-per-plugin with `name`, `owner`, `plugins[].name/source/description` | `loopos.plugins.marketplace` (defer) | defer_to_v0_3_plus | LoopOS does not need plugin marketplaces in v0.2 |
| Plugin frontmatter conventions (`name`, `description`, `version`, optional `author`, `keywords`, `license`) | `plugins/README.md` | shared shape across all Claude Code plugins | `loopos.plugins.frontmatter` (defer) | adopt_concept | LoopOS can adopt a slimmer subset (name, description, version, license, platforms) |
| Plugin subdirectories (`commands/`, `agents/`, `skills/`, `hooks/`, `settings.json`) | `plugins/README.md` | one plugin = one directory; each contains its own slash commands, agents, skills, hooks, settings overrides | `loopos.plugins.directory_layout` (defer) | adopt_concept | LoopOS v0.2 does not adopt plugins but the shape is worth remembering |
| Per-plugin `settings.json` (extends the user's `~/.claude/settings.json`) | `plugins/README.md`, `plugins/feature-dev/README.md` | declarative per-plugin settings overrides | `loopos.plugins.settings_overlay` (defer) | defer_to_v0_3_plus | needs plugin infrastructure first |
| Per-plugin agents (sub-agent definitions) | `plugins/README.md` (mentions), `plugins/feature-dev/README.md` describes `code-explorer` agents | sub-agent personas with specific tool permissions | `loopos.ali.delegation` (defer) | defer_to_v0_3_plus | LoopOS uses Kernel + ALI FSM, not subagents |
| Per-plugin hooks (PreToolUse, PostToolUse, UserPromptSubmit, Stop, etc.) | `plugins/hookify/README.md`, `plugins/README.md` | hook points that can validate/modify tool calls or prompts | `loopos.trace.hooks` (defer) | adopt_concept | LoopOS Trace layer can adopt this hook vocabulary in v0.3+ |
| 7-phase feature-dev workflow (Discovery → Codebase Exploration → Clarifying Questions → Architecture Design → Implementation → Quality Review → Summary) | `plugins/feature-dev/README.md` | guided multi-phase workflow with phase-gated user confirmation | `loopos.ali.phased_workflow` (defer) | adopt_concept | LoopOS already has a similar phased-governance idea (Phase 0-S6) |
| Issue triage slash command (multi-mode: bug / feature / model-behavior / documentation) | `.claude/commands/triage-issue.md`, `.github/ISSUE_TEMPLATE/*.yml` | triage-by-template convention | not in LoopOS scope | reject_for_v0_2 | LoopOS is not an issue tracker |
| Commit/push/PR slash command (`commit-push-pr.md`) | `.claude/commands/commit-push-pr.md` | one-message commit + push + PR open | not in LoopOS scope | reject_for_v0_2 | LoopOS does not own git workflow |
| Dedupe slash command (auto-mark duplicate issues) | `.claude/commands/dedupe.md`, `.github/workflows/claude-dedupe-issues.yml` | duplicate detection by issue similarity | not in LoopOS scope | reject_for_v0_2 | LoopOS is not an issue tracker |
| Slash-command auto-detection (user types `/`, command list appears) | NOT IN TREE | UI affordance | out of LoopOS scope (no TUI in v0.2) | reject_for_v0_2 | UX concern |
| Issue lifecycle automation (auto-close after stale, sweep duplicates) | `.github/workflows/sweep.yml`, `auto-close-duplicates.yml`, `lock-closed-issues.yml` | GitHub Actions patterns | not in LoopOS scope | reject_for_v0_2 | LoopOS has its own CI |
| Managed-settings delivery via MDM (`/Library/Managed Preferences/...`, `/etc/managed/...`, registry paths) | `examples/mdm/managed-settings.json`, `examples/mdm/README.md` | OS-managed config delivery, prevents user override | `loopos.policy_os.managed_overlay` (defer) | defer_to_v0_3_plus | shape reusable; impl deferred |
| Devcontainer setup | `.devcontainer/devcontainer.json` | reproducible dev env via VS Code dev container | not in LoopOS scope | reject_for_v0_2 | LoopOS has its own dev setup |
| Prompt Caching (per-conversation prefix cache) | NOT IN TREE (mentioned in behavior) | preserve prefix cache across turns | `loopos.context.cache_invariant` (defer) | defer_to_v0_3_plus | important for v0.3+ LLM runtime, not for v0.2 |
| Task completion detection | NOT IN TREE (closed) | heuristic + structured signal for "done" | `loopos.ali.fsm.convergence` (existing) | adopt_concept | LoopOS `ConvergenceSnapshot` is the LoopOS-native equivalent |
| Tool approval UX (interactive approve/deny) | NOT IN TREE (closed) | human-in-the-loop approval flow | `loopos.aci.AgentCommand.approval_granted` (existing) | adopt_concept | LoopOS ACI already carries an `approval_granted` flag |
| Repair/retry behavior | NOT IN TREE (closed) | automatic retry of failed tool calls with modified args | `loopos.ali.fsm` REPAIRING state (existing) | adopt_concept | LoopOS ALI already has REPAIRING |
| `claude` (root entrypoint) | NOT IN TREE (npm package) | one-binary CLI entry | `loopos.cli` (existing) | adopt_concept | LoopOS already has a CLI surface |
| `/bug` slash command (report bug from inside the agent) | README mentions | user-driven bug submission | not in LoopOS scope | reject_for_v0_2 | UX/product surface |
| Data collection + retention policy (telemetry, conversation data) | README "Data collection" section, `docs/data-usage`, Commercial Terms | opt-in/opt-out telemetry, retention windows | not in LoopOS scope | reject_for_v0_2 | LoopOS does not collect telemetry |

---

## 2. Claude Code-specific design ideas worth transplanting

### 2.1 Permission model (settings-strict.json)

Three-tier permission policy:

```json
{
  "permissions": {
    "disableBypassPermissionsMode": "disable",
    "ask":  ["Bash"],
    "deny": ["WebSearch", "WebFetch"]
  },
  "allowManagedPermissionRulesOnly": true
}
```

LoopOS already has a `PolicyDecision` model with `allowed: bool`. The Claude Code shape adds a useful **mode selector** (disable / ask / deny / allow) which can inform a future LoopOS `policy_mode` field. **No code reference required** — this is a published schema, not copyrightable as code.

### 2.2 Sandbox network policy

```json
{
  "sandbox": {
    "enabled": true,
    "network": {
      "allowUnixSockets": [],
      "allowLocalBinding": false,
      "allowedDomains": [],
      "httpProxyPort": null,
      "socksProxyPort": null
    }
  }
}
```

LoopOS `loopos/syscalls/` could adopt a similar network sandbox contract in v0.3+. The shape (`allowlist + per-binding controls + proxy allowlist`) is reusable.

### 2.3 Slash-command prompt-injection template

```markdown
---
allowed-tools: Bash(git checkout --branch:*), Bash(git add:*), Bash(git status:*), Bash(git push:*), Bash(git commit:*), Bash(gh pr create:*)
description: Commit, push, and open a PR
---

## Context

- Current git status: !`git status`
- Current git diff (staged and unstaged changes): !`git diff HEAD`
- Current branch: !`git branch --show-current`

## Your task

Based on the above changes:
1. Create a new branch if on main
2. Create a single commit with an appropriate message
3. Push the branch to origin
4. Create a pull request using `gh pr create`
```

Three reusable ideas:

1. **`---` frontmatter with `allowed-tools` and `description`** — declarative per-command capability filter. LoopOS can adopt this as a `CommandTemplate` shape.
2. **`!command` inline command invocation** — embed command output in the prompt. LoopOS can adopt this in `loopos.context.command_context` (deferred).
3. **`## Context` + `## Your task` sections** — explicit prompt structure. LoopOS AIL/ACI prompt templates can adopt this convention.

### 2.4 7-phase feature-dev workflow

The `feature-dev` plugin defines a multi-phase workflow with phase-gated user confirmation (Discovery → Codebase Exploration → Clarifying Questions → Architecture Design → Implementation → Quality Review → Summary). This is conceptually close to LoopOS's Phase 0–S6 governance: each phase has a defined deliverable and a go/no-go checkpoint.

LoopOS v0.2 does not adopt the `feature-dev` plugin directly but should remember the **phase-gated-with-confirmation** pattern for v0.3+ AIL workflows.

### 2.5 Plugin directory layout

```
plugins/<plugin-name>/
├── .claude-plugin/
│   └── marketplace.json    # marketplace manifest
├── commands/               # slash-command .md files
├── agents/                 # sub-agent persona files
├── skills/                 # skill scripts / refs
├── hooks/                  # PreToolUse / PostToolUse hooks
└── settings.json           # per-plugin settings overrides
```

LoopOS v0.2 does not adopt the plugin system, but the **directory layout** is a useful reference for v0.3+ `loopos.plugins`.

---

## 3. Key Claude Code invariants worth transplanting

1. **Permission policy is declarative JSON** with three modes
   (strict / lax / bash-sandbox). LoopOS Policy OS already
   encodes this as a typed model; the JSON shape is a useful
   public-schema reference.

2. **Slash-command templates use `allowed-tools` frontmatter**
   to scope per-command capabilities. This is a clean pattern
   that maps onto LoopOS's `CommandCapability` model.

3. **Sandbox + managed overlay are orthogonal.** A user can
   have a strict sandbox AND a managed policy layer on top.
   LoopOS `PolicyDecision` already supports this layering via
   `constraints`; the JSON shape is the schema.

4. **No new permissions without an audit.** Claude Code's
   `disableBypassPermissionsMode` is a guarded override that
   must be explicitly set. LoopOS Policy OS already requires
   this for `allow_unsafe`.

5. **Sub-agents are personas with scoped tools**, not full
   agents. LoopOS ALI FSM treats a delegated run as the same
   FSM in a new session with narrowed `CommandCapability` —
   the same principle.
