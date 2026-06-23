# LoopOS v0.3 Anti-Bloat Guard Notes

This file documents **v0.3-specific** anti-bloat rules. The base
`scripts/anti_bloat_check.py` is the live source of truth; this file
is human-readable documentation only.

## v0.3 allow-list additions

The following files / directories are explicitly allowed to exist
inside the v0.3 packages, in addition to the v0.2 allow-list:

* `loopos/product/__init__.py`
* `loopos/product/workbench.py`
* `loopos/product/views.py`
* `loopos/product/render.py`
* `loopos/product/commands.py`
* `loopos/product/session_view.py`
* `loopos/product/trace_view.py`
* `loopos/product/readiness_view.py`
* `loopos/product/fusion_view.py`
* `loopos/product/policy_view.py`
* `loopos/product/aci_view.py`
* `loopos/product/agent_view.py`
* `loopos/product/goal_view.py`
* `loopos/product/panel_layout.py`
* `loopos/product/text_render.py`

* `loopos/adapters/__init__.py`
* `loopos/adapters/base.py`
* `loopos/adapters/manifest.py`
* `loopos/adapters/events.py`
* `loopos/adapters/registry.py`
* `loopos/adapters/mock.py`
* `loopos/adapters/hermes.py`
* `loopos/adapters/scream_code.py`
* `loopos/adapters/cleanroom.py`
* `loopos/adapters/openhands.py`

* `loopos/agent_bus/__init__.py`
* `loopos/agent_bus/bus.py`
* `loopos/agent_bus/events.py`
* `loopos/agent_bus/translation.py`
* `loopos/agent_bus/command_bridge.py`
* `loopos/agent_bus/session.py`

* `loopos/providers_runtime/__init__.py`
* `loopos/providers_runtime/base.py`
* `loopos/providers_runtime/models.py`
* `loopos/providers_runtime/budget.py`
* `loopos/providers_runtime/usage.py`
* `loopos/providers_runtime/errors.py`
* `loopos/providers_runtime/mock.py`
* `loopos/providers_runtime/openai.py`
* `loopos/providers_runtime/ollama.py`
* `loopos/providers_runtime/registry.py`

* `loopos/opengod/__init__.py`
* `loopos/opengod/models.py`
* `loopos/opengod/decision.py`
* `loopos/opengod/evidence.py`
* `loopos/opengod/budget.py`
* `loopos/opengod/verdict.py`

## Forbidden by default

* No file inside `loopos/kernel/`, `loopos/model_kernel/`,
  `loopos/ail/`, or `loopos/ali/` may be created or modified for v0.3
  features except for explicit guard-wiring.
* No file in v0.3 packages may import a forbidden live token
  (`requests`, `httpx`, `urllib.request`, `urllib3`, `subprocess`,
  `popen`) **except** `loopos/providers_runtime/openai.py` and
  `loopos/providers_runtime/ollama.py`, which are the only
  HTTP-issuing layers and are gated by `live_provider_calls_allowed`.

End of v0.3 anti-bloat notes.
