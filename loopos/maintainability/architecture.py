"""Architecture boundary rules for the Maintainability Kernel.

Detects when a patch crosses module boundaries in ways that suggest the
author did not understand the existing architecture. The boundary graph is
loaded from a YAML config (``loopos/maintainability/architecture.yaml`` if
present) and otherwise defaults to the in-repo top-level packages.

This is a heuristic v0.5: it flags changes that touch more than one
``loopos.<package>`` module without a declared bridge, and changes that
import from a package outside the public API surface.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from loopos.maintainability.models import CodeChangeSummary, MaintainabilityFinding

_IMPORT_PATTERN = re.compile(
    r"^\s*from\s+loopos\.([a-z_][a-z0-9_]*)(?:\.[a-z_][a-z0-9_]*)*\s+import\s+(.+)",
    re.MULTILINE,
)
_PUBLIC_API_PATTERN = re.compile(r"^\s*(__all__|def [a-z_]\w+|class [A-Z]\w*)", re.MULTILINE)


class ArchitectureBoundaryRules:
    """Module-boundary and public-API-change checks."""

    def __init__(self, config: "ArchitectureConfig | None" = None) -> None:
        self.config = config or ArchitectureConfig.default()

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ArchitectureBoundaryRules":
        return cls(ArchitectureConfig.from_yaml(path))

    def check_boundary_crossings(
        self,
        summary: CodeChangeSummary,
        files: dict[str, str],
    ) -> list[MaintainabilityFinding]:
        findings: list[MaintainabilityFinding] = []
        touched_packages: set[str] = set()
        for path in summary.changed_files:
            pkg = _package_of(path)
            if pkg:
                touched_packages.add(pkg)
        if len(touched_packages) > self.config.max_packages_per_patch:
            findings.append(
                MaintainabilityFinding(
                    category="module_boundary",
                    severity="warning",
                    message=(
                        f"Patch touches {len(touched_packages)} packages "
                        f"({', '.join(sorted(touched_packages))}); max allowed is "
                        f"{self.config.max_packages_per_patch}."
                    ),
                    suggested_fix="Split the change so each patch targets one package.",
                    evidence=sorted(touched_packages),
                )
            )
        for path, content in files.items():
            findings.extend(self._check_cross_imports(path, content))
            findings.extend(self._check_public_api_changes(path, content, summary))
        return findings

    def _check_cross_imports(self, path: str, content: str) -> list[MaintainabilityFinding]:
        findings: list[MaintainabilityFinding] = []
        source_pkg = _package_of(path)
        if not source_pkg:
            return findings
        for match in _IMPORT_PATTERN.finditer(content):
            target_pkg = match.group(1)
            if target_pkg == source_pkg:
                continue
            # A declared bridge explicitly permits the import.
            if target_pkg in self.config.bridges.get(source_pkg, set()):
                continue
            # Importing a non-public package from outside its boundary is
            # always a finding — the caller is reaching past the public API.
            # Importing a public package without a declared bridge is also
            # a finding: the caller should route through the boundary or
            # the bridge graph should be updated.
            findings.append(
                MaintainabilityFinding(
                    category="module_boundary",
                    severity="warning",
                    file=path,
                    message=(
                        f"Cross-package import loopos.{target_pkg} from "
                        f"loopos.{source_pkg} is not a declared bridge."
                    ),
                    suggested_fix=(
                        f"Add '{target_pkg}' to architecture.bridges['{source_pkg}'] "
                        "or route the call through the public API."
                    ),
                    evidence=[match.group(0).strip()],
                )
            )
        return findings

    def _check_public_api_changes(
        self,
        path: str,
        content: str,
        summary: CodeChangeSummary,
    ) -> list[MaintainabilityFinding]:
        findings: list[MaintainabilityFinding] = []
        if path not in summary.new_public_apis and path not in summary.deleted_public_apis:
            return findings
        if not _PUBLIC_API_PATTERN.search(content):
            findings.append(
                MaintainabilityFinding(
                    category="module_boundary",
                    severity="warning",
                    file=path,
                    message=(
                        "Public API surface changed but no __all__, public def, or public "
                        "class declaration found in the added lines."
                    ),
                    suggested_fix="Update __all__ or document the new public symbol.",
                )
            )
        return findings


class ArchitectureConfig:
    """Boundary graph for architecture checks."""

    def __init__(
        self,
        *,
        public_packages: set[str],
        bridges: dict[str, set[str]],
        max_packages_per_patch: int,
    ) -> None:
        self.public_packages = public_packages
        self.bridges = bridges
        self.max_packages_per_patch = max_packages_per_patch

    @classmethod
    def default(cls) -> "ArchitectureConfig":
        return cls(
            public_packages={
                "ail",
                "kernel",
                "policy_os",
                "syscalls",
                "memory",
                "goal",
                "convergence",
                "cli",
                "model_kernel",
                "gateway",
                "data_guard",
                "maintainability",
                "review",
                "fusion",
                "prompt_distill",
            },
            bridges={
                "cli": {"kernel", "policy_os", "memory", "goal", "convergence", "review"},
                "kernel": {"policy_os", "syscalls", "memory"},
                "syscalls": {"execution", "data_guard", "gateway", "model_kernel"},
                "review": {"maintainability", "kernel"},
                "fusion": {"model_kernel", "policy_os"},
            },
            max_packages_per_patch=3,
        )

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ArchitectureConfig":
        payload: dict[str, Any] = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        public = {str(pkg) for pkg in payload.get("public_packages", [])}
        bridges_raw = payload.get("bridges", {}) or {}
        bridges: dict[str, set[str]] = {}
        for source, targets in bridges_raw.items():
            bridges[str(source)] = {str(t) for t in targets or []}
        max_per_patch = int(payload.get("max_packages_per_patch", 3))
        if not public:
            return cls.default()
        return cls(
            public_packages=public,
            bridges=bridges,
            max_packages_per_patch=max_per_patch,
        )


def _package_of(path: str) -> str | None:
    match = re.match(r"^(?:loopos|tests)/([a-z_][a-z0-9_]*)/", path)
    return match.group(1) if match else None
