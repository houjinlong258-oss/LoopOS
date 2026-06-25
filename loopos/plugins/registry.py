"""Optional plugin registry."""

from __future__ import annotations

from loopos.plugins.plugin import Plugin


class PluginRegistry:
    def __init__(self, plugins: list[Plugin] | None = None) -> None:
        self._plugins = plugins or []

    def list(self) -> list[Plugin]:
        return list(self._plugins)

    def register(self, plugin: Plugin) -> Plugin:
        self._plugins.append(plugin)
        return plugin


__all__ = ["PluginRegistry"]
