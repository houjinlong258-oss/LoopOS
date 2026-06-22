# Provider Runtime Map — LoopOS v0.2

**Purpose:** map the Hermes Agent provider runtime design
(shapes, fields, hooks, registry API) onto the LoopOS v0.2
Provider Runtime Registry (`loopos.providers`) and document the
coexistence boundary with `loopos.model_kernel`.

**Companion docs:**

- `../license-and-provenance-audit.md` — license/provenance.
- `../hermes-agent-audit.md` — Hermes surface catalogue.
- `../claude-code-main-audit.md` — Claude Code surface catalogue.
- `../loopos-transplant-plan.md` — unified transplant plan.

**Status:** implemented in this branch (`v0.2/true-agent-os-kernel`).
**Date:** 2026-06-22.

---

## 1. Hermes `ProviderProfile` → LoopOS `ModelProviderProfile`

| Hermes field | Hermes type | LoopOS field | LoopOS type | notes |
|---|---|---|---|---|
| `name` | `str` | `provider_id` | `str` (kebab-case, canonicalised to lower-case) | LoopOS uses `provider_id` as the canonical key |
| (none) | n/a | `name` | `str` | human-readable display name (e.g. "OpenAI") |
| `aliases` | `tuple[str, ...]` | `aliases` | `tuple[str, ...]` | unchanged |
| `api_mode` | `str` | `kind` + `api_style` | `Literal[ProviderKind]` + `str` | split: `kind` is the transport family, `api_style` is the dialect |
| `display_name` | `str` | `name` | `str` | merged into the single display name |
| `description` | `str` | `notes` | `str` | free-form documentation |
| `signup_url` | `str` | (deferred) | n/a | reserved for v0.3+ |
| `env_vars` | `tuple[str, ...]` | (deferred) | n/a | LoopOS does not own env-var resolution in v0.2 |
| `base_url` | `str` | `default_base_url` | `str` | default; user can override when `supports_custom_base_url` is True |
| `models_url` | `str` | (deferred) | n/a | reserved for v0.3+ live catalog hook |
| `auth_type` | `Literal["api_key" \| "oauth_device_code" \| "oauth_external" \| "copilot" \| "aws_sdk"]` | `auth_modes` | `tuple[ProviderAuthMode, ...]` | tuple form (a provider may support multiple auth modes); re-tagged enum (drop `copilot`/`oauth_device_code` in v0.2) |
| `supports_health_check` | `bool` | (deferred) | n/a | the v0.2 registry does not perform health checks |
| `supports_vision` | `bool` | `supports_vision` | `bool` | unchanged |
| `supports_vision_tool_messages` | `bool` | (deferred) | n/a | transport-layer concern |
| `fallback_models` | `tuple[str, ...]` | `default_models` | `tuple[str, ...]` | renamed; semantically identical |
| `hostname` | `str` | (derived) | n/a | derived from `default_base_url` in v0.3+ |
| `default_headers` | `dict[str, str]` | (deferred) | n/a | transport-layer concern |
| `fixed_temperature` | `Any` | (deferred) | n/a | request-level hook |
| `default_max_tokens` | `int \| None` | (deferred) | n/a | request-level hook |
| `default_aux_model` | `str` | (deferred) | n/a | scheduling concern |
| (capability list, in YAML anchors) | `list[str]` | `capability_hints.capabilities` | `tuple[ModelCapability, ...]` | narrower set than `loopos.model_kernel.ProviderCapability` |
| (cost class, in YAML anchors) | `str` | `capability_hints.cost_class` | `CostClass` literal | unchanged |
| (latency class, in YAML anchors) | `str` | `capability_hints.latency_class` | `LatencyClass` literal | unchanged |
| (reliability score, in YAML anchors) | `float` | `capability_hints.reliability_score` | `float` (0.0–1.0) | unchanged |
| (local_only flag, in YAML anchors) | `bool` | `capability_hints.local_only` | `bool` | unchanged |
| `get_hostname()` | method | (deferred) | n/a | v0.3+ hook |
| `prepare_messages()` | method | (deferred) | n/a | v0.3+ transport hook |
| `build_extra_body()` | method | (deferred) | n/a | v0.3+ transport hook |
| `build_api_kwargs_extras()` | method | (deferred) | n/a | v0.3+ transport hook |
| `get_max_tokens()` | method | (deferred) | n/a | v0.3+ transport hook |
| `fetch_models()` | method | (deferred) | n/a | v0.3+ transport hook — out of v0.2 scope |

---

## 2. Hermes Registry API → LoopOS `ProviderRegistry`

| Hermes API | Hermes signature | LoopOS API | LoopOS signature | delta |
|---|---|---|---|---|
| `register_provider` | `register_provider(profile: ProviderProfile) -> None` | `register` | `register(profile: ModelProviderProfile) -> None` | strict: rejects duplicates with `DuplicateProviderError` |
| `get_provider_profile` | `get_provider_profile(name: str) -> ProviderProfile \| None` | `get` + `try_get` | `get(provider_id: str) -> ModelProviderProfile` (raises) and `try_get(provider_id) -> ModelProviderProfile \| None` | split into strict (raises) and lenient (None) variants |
| `list_providers` | `list_providers() -> list[ProviderProfile]` | `list` | `list() -> tuple[ModelProviderProfile, ...]` | tuple (immutable view); insertion-order preserved |
| (none) | n/a | `ids` | `ids() -> tuple[str, ...]` | explicit primary-key enumeration |
| (none) | n/a | `aliases` | `aliases() -> dict[str, str]` | snapshot copy of alias map |
| (none) | n/a | `contains` | `contains(provider_id: str) -> bool` and `__contains__` | bool query |
| (none) | n/a | `find_by_capability` | `find_by_capability(capability) -> tuple[ModelProviderProfile, ...]` | metadata-only; preserves insertion order |
| (none) | n/a | `find_by_kind` | `find_by_kind(kind) -> tuple[ModelProviderProfile, ...]` | transport-family lookup |
| (none) | n/a | `find_local` | `find_local() -> tuple[ModelProviderProfile, ...]` | local-only filter |
| (none) | n/a | `find_with_feature` | `find_with_feature(feature) -> tuple[ModelProviderProfile, ...]` | feature-flag filter |
| (none) | n/a | `validate_profile` | `validate_profile(profile) -> None` (raises `ProviderValidationError`) | public validation entry point |
| (none) | n/a | `clear` | `clear() -> None` | test-fixture helper |
| (none) | n/a | `load_builtin_profiles` | `load_builtin_profiles(source: str \| Path \| None) -> int` | explicit YAML load (no lazy discovery) |
| `route` (Hermes' `model_kernel` analogue) | `route(required: Sequence[str], *, local_only=False) -> ProviderProfile` | out of v0.2 scope | n/a | best-match routing is a `loopos.providers.selection` concern in v0.3+ |
| `_discover_providers` (lazy plugin scan) | internal | out of v0.2 scope | n/a | deferred to v0.3+; v0.2 has no filesystem discovery |
| (last-writer-wins on duplicate name) | implicit | strict: reject duplicate | `DuplicateProviderError` | LoopOS governance prefers explicit failure |

---

## 3. Built-in profiles (loaded from `providers/defaults.yaml`)

The shipped YAML declares 27 provider entries. Each is loaded
into a `ModelProviderProfile` via `ProviderRegistry.load_builtin_profiles()`.

| provider_id | aliases | kind | auth_modes | local_only | default capability set |
|---|---|---|---|---|---|
| `openai` | `open_ai` | `openai_compatible` | `api_key` | no | text, reasoning, tools, vision |
| `openai-codex` | `openai_codex` | `openai_compatible` | `api_key` | no | text, coding, reasoning, tools |
| `openrouter` | `open_router` | `openai_compatible` | `api_key` | no | text, reasoning, tools, vision |
| `anthropic` | (none) | `anthropic_messages` | `api_key` | no | text, reasoning, tools, vision |
| `gemini` | (none) | `gemini` | `api_key` | no | text, reasoning, tools, vision |
| `deepseek` | (none) | `openai_compatible` | `api_key` | no | text, coding, reasoning, tools |
| `kimi-coding` | `kimi_coding` | `openai_compatible` | `api_key` | no | text, coding, reasoning, tools |
| `minimax` | (none) | `openai_compatible` | `api_key` | no | text, reasoning, tools, vision |
| `xai` | (none) | `openai_compatible` | `api_key` | no | text, reasoning, tools, vision |
| `qwen-oauth` | `qwen_oauth` | `openai_compatible` | `api_key` | no | text, coding, reasoning, tools |
| `alibaba` | (none) | `openai_compatible` | `api_key` | no | text, reasoning, tools |
| `huggingface` | (none) | `local_openai_compatible` | `none` | yes | text, coding, reasoning, embeddings, local |
| `bedrock` | (none) | `bedrock` | `aws_sdk` | no | text, reasoning, tools |
| `azure-foundry` | `azure_foundry` | `azure_ai_foundry` | `api_key` | no | text, reasoning, tools, vision |
| `ollama-cloud` | `ollama_cloud` | `local_openai_compatible` | `none` | yes | text, coding, reasoning, embeddings, local |
| `custom` | (none) | `custom_openai_compatible` | `api_key` | no | text |
| `copilot` | (none) | `openai_compatible` | `api_key` | no | text, coding, reasoning, tools |
| `copilot-acp` | `copilot_acp` | `openai_compatible` | `api_key` | no | text, coding, reasoning, tools |
| `nous` | (none) | `openai_compatible` | `api_key` | no | text, reasoning, tools |
| `novita` | (none) | `openai_compatible` | `api_key` | no | text, reasoning, tools |
| `nvidia` | (none) | `openai_compatible` | `api_key` | no | text, reasoning, tools |
| `xiaomi` | (none) | `openai_compatible` | `api_key` | no | text |
| `zai` | (none) | `openai_compatible` | `api_key` | no | text, reasoning, tools |
| `stepfun` | (none) | `openai_compatible` | `api_key` | no | text, reasoning, tools |
| `kilocode` | (none) | `openai_compatible` | `api_key` | no | text, coding, reasoning, tools |
| `arcee` | (none) | `openai_compatible` | `api_key` | no | text, reasoning, tools |
| `gmi` | (none) | `openai_compatible` | `api_key` | no | text, reasoning, tools |

`alibaba-coding-plan` (Hermes-bundled) is **not present** in
`providers/defaults.yaml` and therefore not loaded by the
built-in loader. It can be added in a follow-up by appending a
new entry to the YAML.

---

## 4. Capability matrix (built-in profiles)

| capability | profiles |
|---|---|
| `text` | all 27 |
| `reasoning` | openai, openai-codex, openrouter, anthropic, gemini, deepseek, kimi-coding, minimax, xai, qwen-oauth, alibaba, bedrock, azure-foundry, copilot, copilot-acp, nous, novita, nvidia, zai, stepfun, kilocode, arcee, gmi |
| `coding` | openai-codex, deepseek, kimi-coding, qwen-oauth, huggingface, ollama-cloud, copilot, copilot-acp, kilocode |
| `tools` | most non-local providers |
| `vision` | openai, openrouter, anthropic, gemini, minimax, xai, azure-foundry |
| `audio` | none (no provider declares audio capability in the shipped YAML) |
| `embeddings` | huggingface, ollama-cloud |
| `local` | huggingface, ollama-cloud |

---

## 5. Auth matrix

| auth_mode | profiles |
|---|---|
| `api_key` | all except bedrock, huggingface, ollama-cloud |
| `aws_sdk` | bedrock |
| `oauth_external` | (none in the shipped YAML; reserved for v0.3+) |
| `none` | huggingface, ollama-cloud |

---

## 6. Coexistence with `loopos.model_kernel`

```
loopos.providers           (v0.2 — this module)
  ├─ ProviderRegistry      metadata-only, no I/O
  └─ ModelProviderProfile  declarative contract

loopos.model_kernel        (v0.1.0 baseline, unchanged in v0.2)
  ├─ ProviderRegistry      scheduler-aware, routes inference
  ├─ MultiModelScheduler   role-based dispatch
  ├─ MockModelClient       testing
  └─ OpenAICompatibleClient  real HTTP
```

The two modules do not import from each other. A future
integration may have `loopos.model_kernel` read from
`loopos.providers` to obtain canonical capability flags
instead of duplicating them.

---

## 7. Out-of-scope (deferred to v0.3+)

* `fetch_models()` live catalog probing
* `prepare_messages()` / `build_extra_body()` transport hooks
* Plugin auto-discovery (`HERMES_HOME/plugins/loopos/providers/<name>/`)
* Best-match routing (`ProviderRegistry.route()` analogue)
* `signup_url` / `env_vars` / `default_headers` transport metadata
* `default_aux_model` / `default_max_tokens` request-level defaults

All of these are documented as **future hook slots** in
`ModelProviderProfile` docstrings, but the v0.2 implementation
is metadata-only.
