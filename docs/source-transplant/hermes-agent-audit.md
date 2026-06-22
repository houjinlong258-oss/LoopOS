# Hermes Agent Audit — LoopOS v0.2 Source Transplant

**Purpose:** catalogue Hermes Agent's product / runtime / provider
/ interface design surfaces and classify each one's transplant
disposition for LoopOS v0.2.

**Source:** `D:\LoopOS\移植参考的源码\hermes-agent-2026.6.19 (1)\hermes-agent-2026.6.19\` (MIT, © 2025 Nous Research).

**License:** see `license-and-provenance-audit.md` — Hermes is
classified `restricted_reuse_with_attribution`. Concepts,
interfaces, and shapes are reusable; verbatim code is not.

**Reference docs:** the project's own `AGENTS.md` (loaded by
the runtime during this audit) was the primary architectural
source. Additional references include `providers/base.py`,
`providers/__init__.py`, `providers/README.md`,
`hermes_cli/commands.py`, `hermes_cli/providers.py`, and
`hermes_cli/` directory listings.

**Audit date:** 2026-06-22

---

## 1. CLI / TUI Map

Hermes exposes a single CLI binary `hermes` with **~115 slash
commands** (`hermes_cli/commands.py`) split across five
categories (Session, Configuration, Tools & Skills, Info, Exit).
Subcommands such as `hermes chat`, `hermes model`, `hermes
setup`, `hermes doctor`, `hermes cron`, `hermes kanban`,
`hermes gateway`, `hermes acp` are wired through the same
`COMMAND_REGISTRY` and re-rendered for CLI help, gateway
dispatch, Telegram BotCommands, Slack subcommand mapping, and
autocomplete. The TUI (`ui-tui/` + `tui_gateway/`) is a
separate Ink (React) front-end talking to the Python runtime
over newline-delimited JSON-RPC.

| surface | source files | behavior | LoopOS target | decision | notes |
|---|---|---|---|---|---|
| `hermes` (root) | `cli.py`, `hermes_cli/main.py` | entry into classic CLI / TUI / dashboard | `loopos.cli` (existing) | adopt_concept | central registry pattern |
| `hermes chat` | `cli.py::HermesCLI._cmd_chat` | single-shot LLM call | `loopos.cli chat` (deferred) | defer_to_v0_3_plus | requires runtime LLM integration |
| `hermes model [--provider] [--refresh]` | `model_switch.py`, `runtime_provider.py` | switch active model + persist | `loopos.cli model` (deferred) | defer_to_v0_3_plus | needs provider runtime calls |
| `hermes models` | `model_catalog.py` | enumerate known/fetched models | `loopos.cli models` (deferred) | defer_to_v0_3_plus | needs network |
| `hermes tools` | `tools_config.py` (curses UI) | enable/disable toolsets | `loopos.cli tools` (deferred) | wrap_as_adapter (later) | reusable as LoopOS CapabilityBoundary config UI |
| `hermes config` | `config.py` | show / set config.yaml keys | `loopos.cli config` | wrap_as_adapter | fits LoopOS existing CLI surface |
| `hermes setup` | `setup.py`, `setup_whatsapp_cloud.py`, etc. | interactive onboarding wizard | `loopos.cli setup` (deferred) | defer_to_v0_3_plus | interactive UX is significant work |
| `hermes gateway` | `gateway.py`, `gateway_enroll.py` | start messaging gateway | `loopos.cli gateway` | reject_for_v0_2 | LoopOS does not own a gateway runtime in v0.2 |
| `hermes cron <verb>` | `cron.py` | schedule, list, run, pause cron jobs | `loopos.cli cron` | defer_to_v0_3_plus | design reusable, impl deferred |
| `hermes doctor` | `doctor.py` | health check: provider reachability, schema version, env, deps | `loopos.cli doctor` | wrap_as_adapter | re-target LoopOS Readiness Runtime |
| `hermes status` | `status.py` | show current session/model/token state | `loopos.cli status` | wrap_as_adapter | small, valuable for v0.2 |
| `hermes update` | `migrate.py` | in-place config / DB migration | `loopos.cli update` | reject_for_v0_2 | LoopOS has separate release discipline |
| `hermes acp` | `acp_adapter/` | serve ACP (Agent Client Protocol) for editors | `loopos.cli acp` | reject_for_v0_2 | ACP not in LoopOS v0.2 scope |
| `hermes sessions` | `session_listing.py` | list/resume past sessions | `loopos.cli sessions` | defer_to_v0_3_plus | needs persistent session store |
| `hermes dashboard` | `web_server.py`, `tui_gateway` | web-hosted TUI + chat sidebar | not in LoopOS scope | reject_for_v0_2 | no web UI in v0.2 |
| `hermes web` | `web_server.py` | run web server only | not in LoopOS scope | reject_for_v0_2 | no web UI in v0.2 |
| `hermes logs` | `logs.py` | tail agent.log / errors.log / gateway.log | `loopos.cli logs` | defer_to_v0_3_plus | depends on Trace+Log subsystem |
| `hermes profile` / `hermes profiles` | `profiles.py` | multi-instance profile management | `loopos.cli profile` | defer_to_v0_3_plus | LoopOS profile model is different |
| `hermes kanban <verb>` | `kanban.py`, `kanban_db.py`, `kanban_dispatcher` | multi-agent work queue | out of LoopOS scope | reject_for_v0_2 | not an OS kernel concern |
| `hermes memory` / `hermes memory setup` | `memory_providers.py`, `memory_setup.py` | configure memory backend | `loopos.cli memory` | defer_to_v0_3_plus | fits Memory Governance v0.3+ |
| `hermes skills <verb>` | `skills_hub.py`, `skills_config.py` | list/install/pin/archive skills | `loopos.cli skills` | defer_to_v0_3_plus | fits Skill Governance v0.3+ |
| `hermes curator <verb>` | `curator.py` | skill-maintenance background process | out of LoopOS scope | reject_for_v0_2 | not kernel-level |
| `hermes backup / rollback / snapshot` | `backup.py`, `checkpoints.py` | filesystem checkpoints | `loopos.cli backup` | defer_to_v0_3_plus | depends on Trace |
| `hermes skin` | `skin_engine.py` | switch CLI theme | out of LoopOS scope | reject_for_v0_2 | LoopOS v0.2 has no theming |
| `hermes reasoning / fast / voice / busy / indicator / footer` | `cli.py`, `display.py` | runtime display toggles | out of LoopOS scope | reject_for_v0_2 | v0.2 has no TUI |
| `hermes claw` / `hermes weixin` / `hermes feishu` / `hermes slack` / `hermes telegram` / `hermes discord` | `claw.py`, `gateway_enroll.py` etc. | platform-specific setup wizards | out of LoopOS scope | reject_for_v0_2 | LoopOS is kernel, not product |
| Slash commands (central registry `COMMAND_REGISTRY`) | `hermes_cli/commands.py` | single source of truth for ~115 `/cmd` definitions, aliases, args_hint, subcommands, platform gating | LoopOS CLI architecture (defer impl) | adopt_concept | reuse the CommandDef dataclass shape |
| TUI (Ink React front-end + JSON-RPC) | `ui-tui/`, `tui_gateway/` | out-of-process TUI | defer TUI to v0.3+ | defer_to_v0_3_plus | not a v0.2 kernel concern |
| Dashboard (web server) | `web_server.py`, `apps/` | web-hosted TUI | reject | reject_for_v0_2 | no web UI |

**LoopOS v0.2 disposition:** the **command-registry shape**
(`CommandDef` dataclass with name, description, category,
aliases, args_hint, subcommands, cli_only, gateway_only,
gateway_config_gate) is the most valuable transplant; the
**specific command list** is almost entirely deferred because
LoopOS v0.2 is a kernel, not a product.

---

## 2. Provider Runtime Map

Hermes maintains a ProviderProfile contract per provider, plus a
registry that supports lazy plugin discovery
(`plugins/model-providers/<name>/`), alias resolution,
last-writer-wins override, and live model-listing probing. The
loop already exists in `providers/__init__.py` and `providers/base.py`.

| provider/concept | source files | auth | model discovery | streaming | tool use | LoopOS target | decision |
|---|---|---|---|---|---|---|---|
| OpenAI (`openai`) | `plugins/model-providers/openai-codex/`, `hermes_cli/providers.py` | api_key + bearer | live `/v1/models` | yes | yes | `loopos.providers` built-in `openai` profile | adopt_concept (metadata only) |
| OpenAI Codex (`openai-codex`) | `plugins/model-providers/openai-codex/` | oauth_external | n/a | yes | yes | `loopos.providers` built-in `openai-codex` profile | adopt_concept |
| Anthropic (`anthropic`) | `plugins/model-providers/anthropic/` | api_key | live `/v1/models` | yes | yes | `loopos.providers` built-in `anthropic` profile | adopt_concept |
| Google Gemini (`gemini`) | `plugins/model-providers/gemini/` | api_key | live `/v1beta/models` | yes | yes | `loopos.providers` built-in `gemini` profile | adopt_concept |
| OpenRouter (`openrouter`) | `plugins/model-providers/openrouter/` | api_key | live public catalog | yes | yes | `loopos.providers` built-in `openrouter` profile | adopt_concept |
| AWS Bedrock (`bedrock`) | `plugins/model-providers/bedrock/` | aws_sdk (SigV4) | custom (boto3) | yes | yes | `loopos.providers` built-in `bedrock` profile | adopt_concept |
| DeepSeek (`deepseek`) | `plugins/model-providers/deepseek/` | api_key | live `/models` | yes | yes | `loopos.providers` built-in `deepseek` profile | adopt_concept |
| Qwen OAuth (`qwen-oauth`) | `plugins/model-providers/qwen-oauth/` | oauth_external | portal-managed | yes | yes | `loopos.providers` built-in `qwen-oauth` profile | adopt_concept |
| Alibaba / Qwen (`alibaba`, `alibaba-coding-plan`) | `plugins/model-providers/alibaba*/` | api_key | live `/models` | yes | yes | `loopos.providers` built-in `qwen` profile (alias) | adopt_concept |
| Moonshot Kimi (`kimi-coding`) | `plugins/model-providers/kimi-coding/` | api_key | live `/models` | yes | yes | `loopos.providers` built-in `moonshot` profile | adopt_concept |
| xAI (`xai`) | `plugins/model-providers/xai/` | api_key | live `/models` | yes | yes | `loopos.providers` built-in `xai` profile | adopt_concept |
| MiniMax (`minimax`) | `plugins/model-providers/minimax/` | api_key | live `/models` | yes | yes | `loopos.providers` built-in `minimax` profile | adopt_concept |
| Hugging Face (`huggingface`) | `plugins/model-providers/huggingface/` | api_key | live `/models` | yes | partial | `loopos.providers` built-in `huggingface` profile | adopt_concept |
| Nous Research (`nous`) | `plugins/model-providers/nous/` | oauth_device_code | portal-managed | yes | yes | `loopos.providers` built-in `nous` profile | adopt_concept |
| Novita (`novita`) | `plugins/model-providers/novita/` | api_key | live `/models` | yes | yes | `loopos.providers` built-in `novita` profile | adopt_concept |
| NVIDIA NIM (`nvidia`) | `plugins/model-providers/nvidia/` | api_key | live `/models` | yes | yes | `loopos.providers` built-in `nvidia` profile | adopt_concept |
| Xiaomi MiMo (`xiaomi`) | `plugins/model-providers/xiaomi/` | api_key | live `/models` | yes | partial | `loopos.providers` built-in `xiaomi` profile | adopt_concept |
| Z.ai / GLM (`zai`) | `plugins/model-providers/zai/` | api_key | live `/models` | yes | yes | `loopos.providers` built-in `zai` profile | adopt_concept |
| StepFun (`stepfun`) | `plugins/model-providers/stepfun/` | api_key | live `/models` | yes | yes | `loopos.providers` built-in `stepfun` profile | adopt_concept |
| Kilocode (`kilocode`) | `plugins/model-providers/kilocode/` | api_key | live `/models` | yes | yes | `loopos.providers` built-in `kilocode` profile | adopt_concept |
| Arcee (`arcee`) | `plugins/model-providers/arcee/` | api_key | live `/models` | yes | yes | `loopos.providers` built-in `arcee` profile | adopt_concept |
| GMI (`gmi`) | `plugins/model-providers/gmi/` | api_key | live `/models` | yes | yes | `loopos.providers` built-in `gmi` profile | adopt_concept |
| Ollama Cloud (`ollama-cloud`) | `plugins/model-providers/ollama-cloud/` | api_key | live `/models` | yes | yes | `loopos.providers` built-in `ollama-cloud` profile | adopt_concept |
| Azure Foundry (`azure-foundry`) | `plugins/model-providers/azure-foundry/` | api_key | live `/models` | yes | yes | `loopos.providers` built-in `azure-foundry` profile | adopt_concept |
| Copilot (`copilot`, `copilot-acp`) | `plugins/model-providers/copilot*/` | oauth_external | n/a | yes | yes | `loopos.providers` built-in `copilot` profile | adopt_concept |
| OpenCode Zen (`opencode-zen`) | `plugins/model-providers/opencode-zen/` | api_key | live `/models` | yes | yes | `loopos.providers` built-in `opencode-zen` profile | adopt_concept |
| Custom (`custom`) | `plugins/model-providers/custom/` | api_key + custom base URL | user-driven | depends | depends | `loopos.providers` built-in `custom_openai_compatible` + `local_openai_compatible` profiles | adopt_concept |
| ProviderProfile dataclass (`name`, `api_mode`, `aliases`, `auth_type`, `base_url`, `models_url`, `supports_vision`, `fallback_models`, `default_headers`, `fixed_temperature`, `default_max_tokens`, `default_aux_model`, `hostname`) | `providers/base.py` | n/a | n/a | n/a | n/a | `loopos.providers.models.ModelProviderProfile` | clean_room reimplement (Pydantic v2 + ConfigDict(extra="forbid")) |
| ProviderProfile hooks (`get_hostname`, `prepare_messages`, `build_extra_body`, `build_api_kwargs_extras`, `get_max_tokens`, `fetch_models`) | `providers/base.py` | n/a | n/a | n/a | n/a | `loopos.providers.models.ModelProviderProfile` hook methods | adopt_concept (metadata-only — no network calls in v0.2) |
| Provider registry API (`register_provider`, `get_provider_profile`, `list_providers`) | `providers/__init__.py` | n/a | n/a | n/a | n/a | `loopos.providers.registry.ProviderRegistry` (`register`, `get`, `list`, `find_by_capability`, `validate_profile`, `load_builtin_profiles`) | clean_room reimplement |
| Lazy plugin discovery (`plugins/model-providers/<name>/` + `HERMES_HOME/plugins/...`) | `providers/__init__.py::_discover_providers` | n/a | n/a | n/a | n/a | LoopOS v0.2: NO auto-discovery; built-ins loaded from YAML only. Discovery deferred to v0.3+. | reject_for_v0_2 (defer discovery) |
| `fetch_models` live probe (Bearer-auth `GET {base_url}/models`) | `providers/base.py::ProviderProfile.fetch_models` | n/a | n/a | n/a | n/a | LoopOS v0.2: stub-only; documented as a future hook. No network. | reject_for_v0_2 (defer live fetch) |
| Hermes overlay system (`HERMES_OVERLAYS` dict) | `hermes_cli/providers.py` | n/a | n/a | n/a | n/a | not relevant — Hermes transport-specific quirks | reject_for_v0_2 |
| models.dev catalog integration | external | n/a | n/a | n/a | n/a | not relevant | reject_for_v0_2 |

**LoopOS v0.2 disposition:** **adopt** the ProviderProfile **shape** and the **registry API**; **reject** auto-discovery and live probing for now. The 28 built-in provider profiles become metadata-only `ModelProviderProfile` entries loaded from the existing `providers/defaults.yaml` (which already lists 27 of them — only `alibaba-coding-plan` is missing from LoopOS's YAML).

---

## 3. Agent Capability Map

Hermes bundles a wide product surface (memory providers, skill
curation, cron, gateway, kanban, curator, etc.). Most of this
is **product surface**, not **kernel surface**, and most of it
does not belong in LoopOS v0.2.

| capability | source files | value for LoopOS | LoopOS target | decision |
|---|---|---|---|---|
| Skills (bundled + optional, frontmatter, platforms gating) | `skills/`, `optional-skills/`, `hermes_cli/skills_hub.py`, `agent/skill_commands.py` | high — Skill Governance shape | `loopos.skills` (existing) | adopt_concept (defer impl) |
| Memory (ABC + plugin providers: honcho, mem0, supermemory, byterover, hindsight, holographic, openviking, retaindb) | `agent/memory_provider.py`, `agent/memory_manager.py`, `plugins/memory/` | high — Memory Governance shape | `loopos.memory` (existing) | adopt_concept (defer impl) |
| Curator (skill auto-archive by usage telemetry) | `agent/curator.py`, `agent/curator_backup.py`, `hermes_cli/curator.py`, `tools/skill_usage.py` | medium — provides the "policy can act on telemetry" idea | not in v0.2 | defer_to_v0_3_plus |
| Background processes (terminal `background=True, notify_on_complete=True`) | `tools/`, `gateway/` | medium — long-running task supervision | `loopos.execution` (existing) | defer_to_v0_3_plus |
| Delegation (subagent tool `delegate_task`, sync + batch) | `tools/delegate_tool.py`, `agent/delegation.py` | high — but LoopOS uses Kernel + ALI, not subagents | `loopos.ali.delegation` (defer) | defer_to_v0_3_plus |
| Cron scheduler (`cron/jobs.py`, `cron/scheduler.py`) | `cron/` | high — bounded scheduler with catchup window | `loopos.execution.scheduler` (defer) | defer_to_v0_3_plus |
| Kanban (multi-agent work queue, SQLite-backed) | `hermes_cli/kanban.py`, `hermes_cli/kanban_db.py` | low — product surface | not in LoopOS | reject_for_v0_2 |
| Gateway (messaging platforms, ~20 adapters) | `gateway/run.py`, `gateway/platforms/` | low for v0.2 — not a kernel concern | not in v0.2 | reject_for_v0_2 |
| ACP adapter (editor integration) | `acp_adapter/` | low for v0.2 | not in v0.2 | reject_for_v0_2 |
| Tools (auto-discovery via `tools/registry.py`) | `tools/`, `model_tools.py`, `toolsets.py` | high — but LoopOS uses Syscall Router instead | `loopos.syscalls` (existing) | adopt_concept (already done) |
| Toolsets (`toolsets.py` `_HERMES_CORE_TOOLS`, per-platform base) | `toolsets.py` | medium — declarative toolset bundles | `loopos.syscalls` bundles | defer_to_v0_3_plus |
| MCP catalog (curated MCP servers) | `hermes_cli/mcp_catalog.py`, `optional-mcps/` | low for v0.2 | not in v0.2 | reject_for_v0_2 |
| Web search provider (separate from terminal) | `tools/web_search.py` (multiple providers) | low | not in v0.2 | reject_for_v0_2 |
| Browser provider (Playwright-backed) | `tools/browser_*` | low | not in v0.2 | reject_for_v0_2 |
| Image provider (DALL-E, Imagen, etc.) | `agent/image_gen_provider.py`, `plugins/image_gen/` | low | not in v0.2 | reject_for_v0_2 |
| TTS / STT providers | `agent/tts*.py`, `agent/stt*.py` | low | not in v0.2 | reject_for_v0_2 |
| Plugin discovery (general plugins, `~/.hermes/plugins/`, pip entry points) | `hermes_cli/plugins.py` | medium — `register(register_tool, register_cli_command, hooks)` shape | `loopos.plugins` (defer) | defer_to_v0_3_plus |
| Profile system (multi-instance `HERMES_HOME`) | `hermes_cli/profiles.py`, `hermes_constants.py` | low — LoopOS uses different multi-tenancy | not in v0.2 | reject_for_v0_2 |
| Skin engine (data-driven CLI theming) | `hermes_cli/skin_engine.py` | low — LoopOS has no TUI in v0.2 | not in v0.2 | reject_for_v0_2 |
| Context compression | `agent/compression*.py`, `hermes_cli/partial_compress.py` | high — important for long-running loops | `loopos.context` (defer) | defer_to_v0_3_plus |
| Auxiliary LLM (per-task side-LLM for curator/vision/embedding/title/session_search) | `agent/auxiliary_client.py` | medium — provider multiplexing idea | `loopos.providers` selection policy | defer_to_v0_3_plus |
| Session store (SQLite + FTS5) | `hermes_state.py` | medium — durable session shape | `loopos.ali.session` (existing) | adopt_concept (already partially done) |
| Tracing / logging (`hermes_logging.py`) | `hermes_logging.py`, `logs.py` | high — profile-aware logs | `loopos.trace` (existing) | adopt_concept (already partially done) |
| Doctor (`hermes doctor`) | `doctor.py` | high — readiness/health check UX | `loopos.cli doctor` | wrap_as_adapter |
| Setup wizard (`hermes setup`) | `setup.py`, plugin-specific setup flows | medium — interactive onboarding UX | not in v0.2 | defer_to_v0_3_plus |
| Slash command autocomplete + help rendering | `hermes_cli/completion.py`, `commands.py` | high — single-registry multi-consumer pattern | `loopos.cli` (existing) | adopt_concept |

**LoopOS v0.2 disposition:** **adopt** the plugin / skill / memory / provider / tool / tracing **shapes**; **defer** all product-surface implementations to v0.3+. The most important near-term LoopOS v0.2 wins are the **provider registry** (this prompt's Phase S5) and the **slash-command central registry pattern** (CLI surface).

---

## 4. Backend Map

Hermes abstracts the terminal backend as a pluggable
`Environment` so the same agent loop can run locally, in Docker,
over SSH, on Modal, on Daytona, on Singularity, etc.

| backend | source files | behavior | LoopOS target | decision |
|---|---|---|---|---|
| Local (`local`) | `tools/environments/local.py` | direct local PTY | `loopos.execution.local` | defer_to_v0_3_plus |
| Docker (`docker`) | `tools/environments/docker.py` | per-session container | `loopos.execution.docker` | defer_to_v0_3_plus |
| SSH (`ssh`) | `tools/environments/ssh.py` | remote shell over SSH | `loopos.execution.ssh` | defer_to_v0_3_plus |
| Modal (`modal`) | `tools/environments/modal.py` | managed serverless container | `loopos.execution.modal` | defer_to_v0_3_plus |
| Managed Modal (`managed_modal.py`) | same family | managed deployment variant | `loopos.execution.managed_modal` | defer_to_v0_3_plus |
| Daytona (`daytona.py`) | `tools/environments/daytona.py` | Daytona dev environment | `loopos.execution.daytona` | defer_to_v0_3_plus |
| Singularity (`singularity.py`) | `tools/environments/singularity.py` | HPC container runtime | `loopos.execution.singularity` | defer_to_v0_3_plus |
| File sync (`file_sync.py`) | `tools/environments/file_sync.py` | local<->remote sync helper | `loopos.execution.file_sync` | defer_to_v0_3_plus |
| Base (`base.py`) | `tools/environments/base.py` | ABC + shared interface | `loopos.execution.base` | defer_to_v0_3_plus |

**LoopOS v0.2 disposition:** **defer all** Execution Backend abstraction. LoopOS already has `loopos/execution/` and `loopos/syscalls/` which own this concern; v0.3+ will adopt the Hermes "Environment" ABC shape when adding non-local backends.

---

## 5. Key Hermes invariants worth transplanting

These are the **principles** (not the code) that LoopOS v0.2
should absorb.

1. **Provider profile is declarative.** Auth, endpoints,
   quirks, fallback list, and hooks are declared once on a
   `ProviderProfile`; transport reads from it instead of
   receiving 20+ boolean flags. LoopOS `ModelProviderProfile`
   should be the single source of truth for provider metadata.

2. **Registry is lazy + last-writer-wins.** Discovery happens
   on first access; user-installed profiles override bundled
   ones. LoopOS v0.2 defers auto-discovery but keeps the
   last-writer-wins semantic (`register()` replaces prior
   entry with same `provider_id`).

3. **Capability-driven lookup.** Consumers ask
   `find_by_capability("vision")` rather than hardcoding
   provider names. LoopOS `ModelProviderProfile.capabilities`
   enables this.

4. **No live calls in the contract.** The `ProviderProfile`
   declares what the provider can do; the transport (which
   LoopOS defers) executes calls. LoopOS v0.2 ships only the
   metadata contract.

5. **One registry, many consumers.** `COMMAND_REGISTRY` is
   the single source of truth that drives CLI help, gateway
   dispatch, Telegram BotCommands, Slack subcommand mapping,
   and autocomplete. LoopOS should adopt this for its CLI
   surface.

6. **Profile-aware paths.** `_apply_profile_override()` sets
   `HERMES_HOME` before any module imports, so profile isolation
   is free. LoopOS does not need this in v0.2 but should
   remember the pattern for v0.3+.

7. **Cache invariance.** Hermes treats prompt-cache preservation
   as sacred. LoopOS should respect this when it eventually
   integrates an LLM runtime — system prompt byte-stability is
   a v0.3+ constraint on Context Governance.
