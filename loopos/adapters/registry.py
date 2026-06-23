"""Adapter Registry.

The :class:`AdapterRegistry` holds the set of known adapters and
provides the data backing ``loopos adapters list`` / ``inspect``. It
refuses to register an adapter whose manifest claims direct shell or
direct file-write authority (the manifest validator already enforces
this for external adapters; the registry double-checks at registration
time so a hand-built manifest cannot smuggle authority in).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from loopos.adapters.base import AgentKernelAdapter
from loopos.adapters.manifest import AgentKernelManifest
from loopos.adapters.mock import MockAdapter


class AdapterSummary(BaseModel):
    """Flat summary row used by ``loopos adapters list``."""

    model_config = ConfigDict(extra="forbid")

    adapter_id: str
    display_name: str
    kind: str
    status: str
    authority_live_tools: bool
    requires_aci: bool
    requires_policy: bool
    notes: str = ""


class AdapterRegistry:
    """In-memory registry of known agent kernel adapters."""

    def __init__(self, *, register_defaults: bool = True) -> None:
        self._adapters: dict[str, AgentKernelAdapter] = {}
        self._manifests: dict[str, AgentKernelManifest] = {}
        if register_defaults:
            self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(MockAdapter())
        # Spec-only / proof adapters are registered lazily to avoid
        # importing optional modules unless requested.
        for loader in (self._load_hermes, self._load_scream_code, self._load_cleanroom):
            try:
                loader()
            except Exception:  # noqa: BLE001 - optional adapters are best-effort
                continue

    def _load_hermes(self) -> None:
        from loopos.adapters.hermes import HermesAdapter

        self.register(HermesAdapter())

    def _load_scream_code(self) -> None:
        from loopos.adapters.scream_code import ScreamCodeAdapter

        self.register(ScreamCodeAdapter())

    def _load_cleanroom(self) -> None:
        from loopos.adapters.cleanroom import CleanroomAdapter

        self.register(CleanroomAdapter())

    def register(self, adapter: AgentKernelAdapter) -> None:
        manifest = adapter.manifest()
        # Defence in depth: never register an adapter that claims
        # direct authority, regardless of kind.
        if manifest.authority.direct_shell or manifest.authority.direct_file_write:
            raise ValueError(f"adapter {manifest.adapter_id!r} claims direct authority; refused")
        self._adapters[manifest.adapter_id] = adapter
        self._manifests[manifest.adapter_id] = manifest

    def get(self, adapter_id: str) -> AgentKernelManifest | None:
        return self._manifests.get(adapter_id.strip().lower())

    def get_adapter(self, adapter_id: str) -> AgentKernelAdapter | None:
        return self._adapters.get(adapter_id.strip().lower())

    def list_adapters(self) -> list[AdapterSummary]:
        summaries: list[AdapterSummary] = []
        for manifest in sorted(self._manifests.values(), key=lambda m: m.adapter_id):
            live_tools = (
                manifest.capabilities.shell_request
                or manifest.capabilities.file_patch
                or manifest.capabilities.model_call_request
            )
            summaries.append(
                AdapterSummary(
                    adapter_id=manifest.adapter_id,
                    display_name=manifest.name,
                    kind=manifest.kind,
                    status=manifest.status,
                    authority_live_tools=live_tools,
                    requires_aci=manifest.authority.requires_aci,
                    requires_policy=manifest.authority.requires_policy,
                    notes=manifest.notes,
                )
            )
        return summaries

    def inspect(self, adapter_id: str) -> dict[str, Any] | None:
        manifest = self.get(adapter_id)
        if manifest is None:
            return None
        return manifest.model_dump()


__all__ = ["AdapterRegistry", "AdapterSummary"]
