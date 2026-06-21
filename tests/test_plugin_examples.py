"""Tests for the bundled plugin examples under examples/plugins/."""

from __future__ import annotations

from pathlib import Path

import pytest

from loopos.registry.store import PluginRegistry, audit_manifest, load_manifest

_EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "plugins"

_EXPECTED = (
    "provider-openai-compatible",
    "skill-pytest-repair",
    "policy-strict-terminal",
    "gateway-webhook",
    "benchmark-basic",
)


def test_expected_plugin_examples_exist() -> None:
    missing = [name for name in _EXPECTED if not (_EXAMPLES / name / "manifest.yaml").exists()]
    assert not missing, f"missing plugin example manifests: {missing}"


@pytest.mark.parametrize("plugin_id", list(_EXPECTED))
def test_each_plugin_manifest_loads_and_audits(plugin_id: str) -> None:
    manifest = load_manifest(_EXAMPLES / plugin_id / "manifest.yaml")
    assert manifest.id == plugin_id
    audit = audit_manifest(manifest)
    assert audit.plugin_id == plugin_id
    # No example uses an unsafe permission; audits must not be blocked.
    assert audit.risk_level != "blocked", f"{plugin_id} blocked: {audit.findings}"
    assert manifest.maintainers, f"{plugin_id} must declare a maintainer"
    assert manifest.tests, f"{plugin_id} must reference at least one test path"
    assert manifest.compatibility.get("loopos"), f"{plugin_id} must declare loopos compatibility"


def test_install_all_examples_into_temp_registry(tmp_path: Path) -> None:
    registry = PluginRegistry(tmp_path / "registry")
    for plugin_id in _EXPECTED:
        manifest, audit = registry.install(_EXAMPLES / plugin_id / "manifest.yaml")
        assert manifest.id == plugin_id
        assert audit.safe
    installed = {manifest.id for manifest in registry.list()}
    assert installed == set(_EXPECTED)
