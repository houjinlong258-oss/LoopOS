"""Metadata-only local plugin registry."""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from loopos.registry.models import PluginAuditResult, PluginManifest, PluginType

_UNSAFE_PERMISSIONS = {
    "network.unrestricted",
    "filesystem.outside_workspace",
    "terminal.unrestricted",
    "secrets.read",
    "policy.bypass",
}
_HIGH_RISK_TOOLS = {"terminal.exec", "database.run_migration", "database.restore"}


def load_manifest(path: str | Path) -> PluginManifest:
    file = Path(path)
    payload = yaml.safe_load(file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("plugin manifest must be a YAML object")
    return PluginManifest.model_validate(payload)


def audit_manifest(manifest: PluginManifest) -> PluginAuditResult:
    findings: list[str] = []
    unsafe = sorted(set(manifest.permissions).intersection(_UNSAFE_PERMISSIONS))
    if unsafe:
        findings.extend(f"unsafe_permission:{item}" for item in unsafe)
    risky_tools = sorted(set(manifest.required_tools).intersection(_HIGH_RISK_TOOLS))
    if risky_tools and manifest.risk_level == "low":
        findings.append("risk_level_understates_required_tools")
    if not manifest.maintainers:
        findings.append("missing_maintainer")
    if not manifest.tests:
        findings.append("missing_tests")
    blocked = any(item.startswith("unsafe_permission:policy.bypass") for item in findings)
    risk = "blocked" if blocked else "high" if unsafe else "medium" if findings else manifest.risk_level
    return PluginAuditResult(
        plugin_id=manifest.id,
        safe=not unsafe and not blocked,
        risk_level=risk,  # type: ignore[arg-type]
        findings=findings,
        permissions_reviewed=manifest.permissions,
    )


class PluginRegistry:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def install(self, manifest_path: str | Path) -> tuple[PluginManifest, PluginAuditResult]:
        manifest = load_manifest(manifest_path)
        audit = audit_manifest(manifest)
        if not audit.safe or audit.risk_level == "blocked":
            raise ValueError("plugin audit failed: " + ", ".join(audit.findings))
        destination = self.root / manifest.type / manifest.id
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(manifest_path, destination / "manifest.yaml")
        return manifest, audit

    def list(self, *, plugin_type: PluginType | None = None) -> Sequence[PluginManifest]:
        manifests = [load_manifest(path) for path in sorted(self.root.glob("*/*/manifest.yaml"))]
        if plugin_type:
            manifests = [manifest for manifest in manifests if manifest.type == plugin_type]
        return manifests

    def search(self, query: str, *, plugin_type: PluginType | None = None) -> Sequence[PluginManifest]:
        lowered = query.lower()
        return [
            manifest
            for manifest in self.list(plugin_type=plugin_type)
            if lowered in f"{manifest.id} {manifest.name} {manifest.description}".lower()
        ]

    def audit(self, plugin_id: str) -> PluginAuditResult:
        for manifest in self.list():
            if manifest.id == plugin_id:
                return audit_manifest(manifest)
        raise KeyError(f"plugin not found: {plugin_id}")
