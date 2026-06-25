"""Optional runtime plugin contracts."""

from __future__ import annotations

from loopos.plugins.hooks import PluginHook
from loopos.plugins.plugin import Plugin
from loopos.plugins.registry import PluginRegistry

__all__ = ["Plugin", "PluginHook", "PluginRegistry"]
