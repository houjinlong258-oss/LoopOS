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
_PERMISSION_EXPLANATIONS = {
    "benchmark:run": "Allows the plugin metadata to describe benchmark tasks.",
    "workspace:read": "Allows reading files inside the active workspace only.",
    "workspace:write": "Allows proposing or performing guarded writes inside the workspace.",
    "terminal:pytest": "Allows guarded pytest execution through terminal.exec policy checks.",
    "policy:enforce:terminal": "Allows a policy pack to constrain terminal execution.",
    "gateway:auth:token": "Requires token-based authentication for mock gateway traffic.",
    "gateway:allowlist": "Requires configured user or channel allowlists.",
    "env:OPENAI_API_KEY": "Declares a provider credential requirement; tests must not read it.",
    "network:outbound:https": "Declares outbound HTTPS capability, disabled until policy approval.",
}


def load_manifest(path: str | Path) -> PluginManifest:
    file = Path(path)
    payload = yaml.safe_load(file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("plugin manifest must be a YAML object")
    return PluginManifest.model_validate(payload)


def audit_manifest(manifest: PluginManifest) -> PluginAuditResult:
    findings: list[str] = []
    if not manifest.license:
        findings.append("missing_license")
    if not manifest.documentation:
        findings.append("missing_documentation")
    if manifest.entrypoint:
        findings.append("entrypoint_declared_metadata_only")
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
    permission_explanations = {
        permission: _PERMISSION_EXPLANATIONS.get(
            permission,
            "Custom permission; contributor must document purpose and policy gate.",
        )
        for permission in manifest.permissions
    }
    return PluginAuditResult(
        plugin_id=manifest.id,
        safe=not unsafe and not blocked,
        risk_level=risk,  # type: ignore[arg-type]
        findings=findings,
        permissions_reviewed=manifest.permissions,
        permission_explanations=permission_explanations,
        risk_explanation=_risk_explanation(manifest.risk_level, risk, findings),
        examples_validated=bool(manifest.metadata),
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


def _risk_explanation(declared: str, effective: str, findings: list[str]) -> str:
    if effective == "blocked":
        return "Blocked because the manifest requests a permission that can bypass policy."
    if effective == "high":
        return "High risk because the manifest requests sensitive permissions."
    if findings:
        return (
            f"Declared {declared}, raised to {effective} because audit findings require "
            "maintainer review."
        )
    return f"Declared and effective risk are both {declared}."
