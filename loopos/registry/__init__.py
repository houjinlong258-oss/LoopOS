"""Metadata-only plugin registry."""

from loopos.registry.models import PluginAuditResult, PluginManifest, PluginType
from loopos.registry.store import PluginRegistry, audit_manifest, load_manifest

__all__ = [
    "PluginAuditResult",
    "PluginManifest",
    "PluginRegistry",
    "PluginType",
    "audit_manifest",
    "load_manifest",
]
