import tempfile
import unittest
from pathlib import Path

from loopos.compute import ComputeModeStore, ComputeRouter
from loopos.model_kernel import ProviderRegistry
from loopos.registry import PluginRegistry, audit_manifest, load_manifest


class ComputeTests(unittest.TestCase):
    def test_private_data_is_local_in_every_mode(self) -> None:
        router = ComputeRouter()
        for mode in ("privacy-local", "hybrid", "cloud-power"):
            with self.subTest(mode=mode):
                decision = router.decide(mode, private_data=True, cloud_consent=True)  # type: ignore[arg-type]
                self.assertTrue(decision.local_only)
                self.assertFalse(decision.cloud_allowed)

    def test_cloud_power_requires_persisted_explicit_consent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ComputeModeStore(Path(tmp) / "mode.json")
            store.set("cloud-power")
            blocked = ComputeRouter().decide(store.load().mode)
            allowed = ComputeRouter().decide(store.load().mode, cloud_consent=True)
            self.assertTrue(blocked.requires_consent)
            self.assertFalse(blocked.cloud_allowed)
            self.assertTrue(allowed.cloud_allowed)


class RegistryTests(unittest.TestCase):
    def _manifest(self, root: Path, *, unsafe: bool = False) -> Path:
        path = root / ("unsafe.yaml" if unsafe else "safe.yaml")
        permissions = "[policy.bypass]" if unsafe else "[workspace.read]"
        path.write_text(
            f"""
id: pytest-repair
type: skill
name: Pytest Repair
version: 0.1.0
description: Repair failing tests.
required_tools: [file.read]
permissions: {permissions}
risk_level: medium
maintainers: [loopos]
tests: [tests/test_skill.py]
""",
            encoding="utf-8",
        )
        return path

    def test_registry_installs_metadata_without_plugin_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._manifest(root)
            (root / "plugin.py").write_text("raise RuntimeError('must not execute')", encoding="utf-8")
            registry = PluginRegistry(root / "registry")
            manifest, audit = registry.install(manifest_path)
            self.assertTrue(audit.safe)
            self.assertEqual(registry.search("pytest")[0].id, manifest.id)
            self.assertFalse((root / "registry" / "skill" / manifest.id / "plugin.py").exists())

    def test_audit_flags_policy_bypass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = load_manifest(self._manifest(Path(tmp), unsafe=True))
            audit = audit_manifest(manifest)
            self.assertFalse(audit.safe)
            self.assertEqual(audit.risk_level, "blocked")

    def test_canonical_provider_yaml_is_default_source(self) -> None:
        registry = ProviderRegistry()
        profile = registry.get("openai-codex")
        self.assertEqual(profile.default_models, ["openai-codex-default"])
        self.assertEqual(registry.route(["coding"]).id, "openai-codex")


if __name__ == "__main__":
    unittest.main()
