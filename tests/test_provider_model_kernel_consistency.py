"""Tests that guard consistency between loopos.providers (v0.2 metadata
substrate) and loopos.model_kernel (v0.1.0 scheduler/client layer).

These tests assert the boundary contract between the two modules:

1. ``providers/defaults.yaml`` is the single metadata source for
   built-in provider IDs. Both ``loopos.providers.load_builtin_profiles()``
   and ``loopos.model_kernel.ProviderRegistry()`` read it.

2. ``loopos.providers`` is metadata-only: no network imports, no
   HTTP client construction, no live model fetching, no vendor SDK
   references. ``loopos.model_kernel`` is the consumer / client /
   scheduler layer; it is not a duplicated source of truth.

3. Provider IDs are stable and deterministic across runs.

4. Intentionally deferred providers (``alibaba-coding-plan`` is
   bundled by Hermes Agent but absent from ``providers/defaults.yaml``)
   are documented as deferred in
   ``docs/source-transplant/provider-runtime-map.md`` rather than
   silently dropped.

These tests are the v0.2 guard: they will fail loudly if a future
change introduces drift between the two registries, adds a network
capability to the metadata substrate, or drops a deferred provider
without documentation.
"""

from __future__ import annotations

import ast
import importlib
import socket as _socket
import urllib.request as _urllib_request
from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]  # PyYAML ships no type stubs

from loopos.model_kernel import ProviderRegistry as V1Registry
from loopos.providers import ProviderRegistry as V2Registry

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
PROVIDERS_PKG = REPO_ROOT / "loopos" / "providers"
MODEL_KERNEL_PKG = REPO_ROOT / "loopos" / "model_kernel"
DEFAULTS_YAML = REPO_ROOT / "providers" / "defaults.yaml"
PROVIDER_RUNTIME_MAP = REPO_ROOT / "docs" / "source-transplant" / "provider-runtime-map.md"

# Provider IDs that are intentionally deferred for v0.2. Each entry MUST
# appear in ``provider-runtime-map.md`` with surrounding context that
# names it as deferred (so the gap is documented, not silent).
INTENTIONALLY_DEFERRED_IDS: tuple[str, ...] = ("alibaba-coding-plan",)


def _yaml_provider_ids() -> set[str]:
    """Return the set of ``id`` values directly from ``providers/defaults.yaml``.

    This bypasses both registries so the raw YAML is the only source of
    truth in this assertion.
    """
    with DEFAULTS_YAML.open("r", encoding="utf-8") as fh:
        payload = yaml.safe_load(fh)
    rows = payload.get("providers") if isinstance(payload, dict) else None
    assert isinstance(rows, list), f"{DEFAULTS_YAML}: 'providers' must be a list"
    return {row["id"] for row in rows if isinstance(row, dict) and row.get("id")}


# ---------------------------------------------------------------------------
# Test 2 — defaults.yaml is the single metadata source
# ---------------------------------------------------------------------------


class TestDefaultsYamlIsSingleSource:
    def test_defaults_yaml_exists(self) -> None:
        assert DEFAULTS_YAML.is_file(), (
            f"expected the single metadata source at {DEFAULTS_YAML}"
        )

    def test_v2_default_yaml_path_matches(self) -> None:
        from loopos.providers.registry import _default_yaml_path

        assert _default_yaml_path().resolve() == DEFAULTS_YAML.resolve()

    def test_v1_default_providers_root_matches(self) -> None:
        # model_kernel.ProviderRegistry uses Path(__file__).resolve().parents[2]
        # to find the providers/ directory. parents[2] from
        # loopos/model_kernel/registry.py resolves to the repo root.
        model_kernel_registry_py = (MODEL_KERNEL_PKG / "registry.py").resolve()
        expected_root = model_kernel_registry_py.parents[2] / "providers"
        assert expected_root.resolve() == (REPO_ROOT / "providers").resolve()


# ---------------------------------------------------------------------------
# Test 1 — both registries agree on built-in provider IDs
# ---------------------------------------------------------------------------


class TestBothRegistriesAgreeOnIds:
    def test_v2_loaded_ids_equal_v1_yaml_loaded_ids(self) -> None:
        v2 = V2Registry()
        loaded = v2.load_builtin_profiles()
        assert loaded >= 20, f"v2 loaded only {loaded} profiles; expected >= 20"
        v2_ids = set(v2.ids())

        v1 = V1Registry()  # auto-loads from defaults.yaml
        v1_ids = {p.id for p in v1.list()}

        only_in_v2 = v2_ids - v1_ids
        only_in_v1 = v1_ids - v2_ids
        assert not only_in_v2, (
            f"loopos.providers has IDs loopos.model_kernel doesn't: {sorted(only_in_v2)}"
        )
        assert not only_in_v1, (
            f"loopos.model_kernel has IDs loopos.providers doesn't: {sorted(only_in_v1)}"
        )

    def test_yaml_id_set_equals_v2_loaded_ids(self) -> None:
        # Direct YAML read: the canonical source of truth.
        yaml_ids = _yaml_provider_ids()
        v2 = V2Registry()
        v2.load_builtin_profiles()
        v2_ids = set(v2.ids())
        assert yaml_ids == v2_ids, (
            f"YAML IDs {sorted(yaml_ids - v2_ids)} not loaded by v2; "
            f"v2 IDs {sorted(v2_ids - yaml_ids)} not in YAML"
        )

    def test_v2_ids_equal_v1_hardcoded_fallback_ids(self) -> None:
        # The model_kernel._PROVIDER_IDS hardcoded list is the fallback
        # contract when YAML is missing. It must stay in sync with the
        # YAML-or-deferred set so future contributors cannot add to one
        # without updating the other.
        from loopos.model_kernel.registry import _PROVIDER_IDS

        v2 = V2Registry()
        v2.load_builtin_profiles()
        v2_ids = set(v2.ids())
        hardcoded_ids = set(_PROVIDER_IDS)
        # Documented deferrals are absent from v2 but live in v1.
        hardcoded_minus_v2 = hardcoded_ids - v2_ids - set(INTENTIONALLY_DEFERRED_IDS)
        v2_minus_hardcoded = v2_ids - hardcoded_ids
        assert not hardcoded_minus_v2, (
            "model_kernel._PROVIDER_IDS has IDs that defaults.yaml + v0.2 "
            f"don't recognize: {sorted(hardcoded_minus_v2)}"
        )
        assert not v2_minus_hardcoded, (
            "defaults.yaml has IDs that model_kernel._PROVIDER_IDS doesn't: "
            f"{sorted(v2_minus_hardcoded)}"
        )


# ---------------------------------------------------------------------------
# Test 3 — loopos.providers is metadata-only
# ---------------------------------------------------------------------------


_FORBIDDEN_NETWORK_IMPORTS: tuple[str, ...] = (
    "import urllib",
    "from urllib",
    "import requests",
    "from requests",
    "import httpx",
    "from httpx",
    "import aiohttp",
    "from aiohttp",
    "import socket",
    "from socket",
    "import http.client",
    "from http.client",
)

_FORBIDDEN_VENDOR_SDK_IMPORTS: tuple[str, ...] = (
    "import openai",
    "from openai",
    "import anthropic",
    "from anthropic",
    "import google",
    "from google",
    "import boto3",
    "from boto3",
    "import cohere",
    "from cohere",
)

# These symbols belong to loopos.model_kernel's client / scheduler layer.
# The metadata substrate must not reference them.
_FORBIDDEN_MODEL_KERNEL_SYMBOLS: tuple[str, ...] = (
    "OpenAICompatibleClient",
    "MockModelClient",
    "MultiModelScheduler",
    "ModelAssignment",
    "VisionSummary",
    "load_provider_profiles",
)


class TestProvidersIsMetadataOnly:
    def test_no_network_module_imports(self) -> None:
        offenders: list[str] = []
        for src in sorted(PROVIDERS_PKG.glob("*.py")):
            text = src.read_text(encoding="utf-8")
            for needle in _FORBIDDEN_NETWORK_IMPORTS:
                if needle in text:
                    offenders.append(f"{src.name}: {needle}")
        assert not offenders, (
            "loopos.providers must not import networking modules: "
            + ", ".join(offenders)
        )

    def test_no_vendor_sdk_imports(self) -> None:
        offenders: list[str] = []
        for src in sorted(PROVIDERS_PKG.glob("*.py")):
            text = src.read_text(encoding="utf-8")
            for needle in _FORBIDDEN_VENDOR_SDK_IMPORTS:
                if needle in text:
                    offenders.append(f"{src.name}: {needle}")
        assert not offenders, (
            "loopos.providers must not import vendor SDKs: "
            + ", ".join(offenders)
        )

    def test_no_model_kernel_client_or_scheduler_symbols_in_code(self) -> None:
        # The metadata substrate must not reference model_kernel client
        # / scheduler symbols in actual code. Docstrings that *name*
        # those symbols for documentation purposes are allowed; only
        # AST Name / Attribute references count as dependencies.
        offenders: list[str] = []
        for src in sorted(PROVIDERS_PKG.glob("*.py")):
            tree = ast.parse(src.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    if node.id in _FORBIDDEN_MODEL_KERNEL_SYMBOLS:
                        offenders.append(
                            f"{src.name}:{node.lineno}: Name({node.id})"
                        )
                elif isinstance(node, ast.Attribute):
                    if node.attr in _FORBIDDEN_MODEL_KERNEL_SYMBOLS:
                        offenders.append(
                            f"{src.name}:{node.lineno}: Attribute(.{node.attr})"
                        )
        assert not offenders, (
            "loopos.providers must not reference model_kernel client/scheduler "
            "symbols in code: " + ", ".join(offenders)
        )

    def test_load_builtin_profiles_does_no_network_io(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Build a registry with built-ins and make sure no networking
        # function is called during loading.
        socket_calls: list[str] = []
        urlopen_calls: list[str] = []

        def _fail_socket(*_args: object, **_kwargs: object) -> None:
            socket_calls.append("socket.socket")

        def _fail_urlopen(*_args: object, **_kwargs: object) -> None:
            urlopen_calls.append("urllib.request.urlopen")

        monkeypatch.setattr(_socket, "socket", _fail_socket, raising=False)
        monkeypatch.setattr(_urllib_request, "urlopen", _fail_urlopen, raising=False)

        v2 = V2Registry()
        v2.load_builtin_profiles()
        assert socket_calls == [], "load_builtin_profiles must not touch socket.socket"
        assert urlopen_calls == [], "load_builtin_profiles must not call urllib.urlopen"


# ---------------------------------------------------------------------------
# Test 4 — loopos.model_kernel is treated as a downstream consumer
# ---------------------------------------------------------------------------


class TestModelKernelIsConsumer:
    def test_providers_package_does_not_import_model_kernel(self) -> None:
        offenders: list[str] = []
        for src in sorted(PROVIDERS_PKG.glob("*.py")):
            tree = ast.parse(src.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("loopos.model_kernel"):
                            offenders.append(f"{src.name}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if (node.module or "").startswith("loopos.model_kernel"):
                        offenders.append(
                            f"{src.name}: from {node.module} import ..."
                        )
        assert not offenders, (
            "loopos.providers must not import from loopos.model_kernel "
            "(one-way dependency: providers -> substrate, model_kernel -> "
            "downstream consumer): " + ", ".join(offenders)
        )

    def test_runtime_map_documents_v1_as_consumer(self) -> None:
        # provider-runtime-map.md §6 explicitly characterizes
        # loopos.model_kernel as the scheduler-aware client layer.
        text = PROVIDER_RUNTIME_MAP.read_text(encoding="utf-8")
        lower = text.lower()
        assert "scheduler" in lower, (
            "provider-runtime-map.md must mention 'scheduler' to describe "
            "model_kernel's role"
        )
        assert "consumer" in lower or "client" in lower, (
            "provider-runtime-map.md must call model_kernel a consumer / "
            "client layer"
        )


# ---------------------------------------------------------------------------
# Test 5 — provider IDs are stable and deterministic
# ---------------------------------------------------------------------------


class TestProviderIdsAreStable:
    def test_load_builtin_profiles_is_deterministic(self) -> None:
        first = V2Registry()
        first.load_builtin_profiles()
        first_ids = first.ids()

        second = V2Registry()
        second.load_builtin_profiles()
        second_ids = second.ids()

        assert first_ids == second_ids, (
            "load_builtin_profiles() must produce the same IDs in the same order"
        )

    def test_repeated_load_on_fresh_registry_is_stable(self) -> None:
        # Stability contract: each fresh-registry load yields the same
        # count. (Idempotency on a non-fresh registry is intentionally
        # out of scope for this guard; the registry rejects duplicate
        # IDs strictly.)
        counts = []
        ids_sequences: list[tuple[str, ...]] = []
        for _ in range(3):
            v2 = V2Registry()
            counts.append(v2.load_builtin_profiles())
            ids_sequences.append(v2.ids())
        assert counts[0] == counts[1] == counts[2] >= 20, (
            f"fresh-registry load_builtin_profiles counts diverge: {counts}"
        )
        assert ids_sequences[0] == ids_sequences[1] == ids_sequences[2], (
            "fresh-registry load_builtin_profiles ids diverge across runs"
        )

    def test_v1_hardcoded_id_list_is_immutable_during_runtime(self) -> None:
        # The hardcoded _PROVIDER_IDS tuple is the fallback contract;
        # mutating it during a run would break the YAML-vs-fallback
        # invariant silently.
        import loopos.model_kernel.registry as mk_registry

        snapshot = tuple(mk_registry._PROVIDER_IDS)
        # Reloading the module must not change the constant.
        importlib.reload(mk_registry)
        assert tuple(mk_registry._PROVIDER_IDS) == snapshot, (
            "model_kernel._PROVIDER_IDS changed across module reload; "
            "treat the list as immutable."
        )

    def test_id_order_matches_yaml_order(self) -> None:
        # The loopos.providers registry returns ids in insertion order,
        # which mirrors the YAML's `providers:` list order. Catches
        # accidental reordering (e.g. someone sorts alphabetically
        # without realizing downstream consumers depend on insertion
        # order).
        with DEFAULTS_YAML.open("r", encoding="utf-8") as fh:
            payload = yaml.safe_load(fh)
        yaml_ids_in_order: list[str] = [
            row["id"] for row in payload["providers"]
            if isinstance(row, dict) and row.get("id")
        ]
        v2 = V2Registry()
        v2.load_builtin_profiles()
        assert list(v2.ids()) == yaml_ids_in_order


# ---------------------------------------------------------------------------
# Test 6 — intentionally deferred providers are documented
# ---------------------------------------------------------------------------


class TestDeferredProvidersAreDocumented:
    def test_alibaba_coding_plan_not_in_v2_registry(self) -> None:
        v2 = V2Registry()
        v2.load_builtin_profiles()
        assert "alibaba-coding-plan" not in v2.ids()
        assert "alibaba-coding-plan" not in v2.aliases().values()

    def test_alibaba_coding_plan_not_in_yaml(self) -> None:
        assert "alibaba-coding-plan" not in _yaml_provider_ids()

    def test_alibaba_coding_plan_not_in_v1_hardcoded_fallback(self) -> None:
        from loopos.model_kernel.registry import _PROVIDER_IDS

        assert "alibaba-coding-plan" not in _PROVIDER_IDS

    @pytest.mark.parametrize("deferred_id", INTENTIONALLY_DEFERRED_IDS)
    def test_deferred_provider_is_documented_in_runtime_map(
        self, deferred_id: str,
    ) -> None:
        text = PROVIDER_RUNTIME_MAP.read_text(encoding="utf-8")
        assert deferred_id in text, (
            f"deferred provider_id {deferred_id!r} not mentioned in "
            f"provider-runtime-map.md"
        )
        idx = text.find(deferred_id)
        window = text[max(0, idx - 250): idx + 400].lower()
        deferred_markers = (
            "deferred",
            "not present",
            "follow-up",
            "missing",
            "absent",
            "not loaded",
        )
        assert any(marker in window for marker in deferred_markers), (
            f"deferred provider_id {deferred_id!r} appears in "
            f"provider-runtime-map.md but the surrounding text does not "
            f"explain it as deferred. Window: {window!r}"
        )
