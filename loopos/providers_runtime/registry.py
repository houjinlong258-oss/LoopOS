"""Provider Runtime registry.

The :class:`ProviderRuntimeRegistry` holds the set of known provider
runtimes and is the data source for ``loopos providers runtime list``.
It refuses to register two runtimes with the same ``provider_id``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from loopos.providers_runtime.base import ProviderInfo, ProviderRuntime
from loopos.providers_runtime.mock import MockProviderRuntime


class ProviderRuntimeRow(BaseModel):
    """One row in ``loopos providers runtime list``."""

    model_config = ConfigDict(extra="forbid")

    provider_id: str
    display_name: str
    kind: str
    env_key: str
    base_url: str
    configured: bool
    live_calls: str  # "enabled" or "disabled"
    notes: str = ""


class ProviderRuntimeRegistry:
    """In-memory registry of provider runtimes."""

    def __init__(self, *, register_defaults: bool = True) -> None:
        self._runtimes: dict[str, ProviderRuntime] = {}
        if register_defaults:
            self._register_defaults()

    def _register_defaults(self) -> None:
        # The mock is always available, even without any keys.
        self.register(MockProviderRuntime())
        # The other defaults are best-effort; their import path is
        # self-contained, so failures here are real failures.
        try:
            from loopos.providers_runtime.openai import OpenAICompatibleProviderRuntime
            self.register(OpenAICompatibleProviderRuntime())
        except Exception:  # noqa: BLE001
            pass
        try:
            from loopos.providers_runtime.ollama import OllamaProviderRuntime
            self.register(OllamaProviderRuntime())
        except Exception:  # noqa: BLE001
            pass

    def register(self, runtime: ProviderRuntime) -> None:
        if runtime.provider_id in self._runtimes:
            return
        self._runtimes[runtime.provider_id] = runtime

    def get(self, provider_id: str) -> ProviderRuntime | None:
        return self._runtimes.get(provider_id.strip().lower())

    def list_runtimes(self) -> list[ProviderRuntimeRow]:
        rows: list[ProviderRuntimeRow] = []
        for provider_id, runtime in sorted(self._runtimes.items()):
            info: ProviderInfo = runtime.info()
            rows.append(
                ProviderRuntimeRow(
                    provider_id=info.provider_id,
                    display_name=info.display_name,
                    kind=info.kind,
                    env_key=info.env_key,
                    base_url=info.base_url,
                    configured=info.configured,
                    live_calls="enabled" if info.live_calls_default else "disabled",
                    notes=info.notes,
                )
            )
        return rows

    def inspect(self, provider_id: str) -> dict[str, Any] | None:
        runtime = self.get(provider_id)
        if runtime is None:
            return None
        info = runtime.info()
        return info.model_dump()


__all__ = ["ProviderRuntimeRegistry", "ProviderRuntimeRow"]
