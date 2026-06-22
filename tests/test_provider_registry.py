"""Tests for the LoopOS Provider Runtime Registry.

These tests cover the metadata-only contract declared in
``loopos.providers``. They deliberately avoid any network calls,
filesystem scanning, or scheduler / client behavior — those concerns
live in ``loopos.model_kernel`` and are out of scope here.

The tests assert the registry's external API:

1. profile roundtrip via JSON
2. register / get / list / contains / __len__
3. duplicate provider_id rejected
4. unknown provider_id raises ProviderNotFoundError
5. capability / kind / feature lookups
6. custom-openai-compatible requires base_url
7. local-openai-compatible is flagged local_only
8. built-in profiles load from providers/defaults.yaml
9. no network calls (verified by import-only inspection)
10. no new third-party dependencies (PyYAML is the only runtime dep)
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

from loopos.providers import (
    DuplicateProviderError,
    ModelCapability,
    ModelProviderProfile,
    ProviderError,
    ProviderKind,
    ProviderNotFoundError,
    ProviderRegistry,
    ProviderValidationError,
)
from loopos.providers.errors import ProviderError as _ProviderError  # noqa: F401
from loopos.providers.models import ProviderCapabilityHints


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def registry() -> ProviderRegistry:
    """A fresh, empty registry for each test."""
    return ProviderRegistry()


def _make_profile(
    *,
    provider_id: str = "test-provider",
    name: str | None = None,
    kind: ProviderKind = "openai_compatible",
    capabilities: tuple[ModelCapability, ...] = ("text",),
    **overrides: object,
) -> ModelProviderProfile:
    """Construct a baseline profile for unit tests."""
    # If the caller supplied ``capability_hints`` in overrides, respect
    # it; otherwise build a default from ``capabilities``.
    hints = overrides.pop(
        "capability_hints",
        ProviderCapabilityHints(capabilities=capabilities),
    )
    return ModelProviderProfile(
        provider_id=provider_id,
        name=name or provider_id.title(),
        kind=kind,
        capability_hints=hints,
        **overrides,
    )


# ---------------------------------------------------------------------------
# 1. Profile roundtrip via JSON
# ---------------------------------------------------------------------------


class TestProfileRoundtrip:
    def test_profile_to_from_json_is_identity(self) -> None:
        original = _make_profile(
            provider_id="openai",
            name="OpenAI",
            capabilities=("text", "reasoning", "tools", "vision"),
            aliases=("open_ai",),
            default_models=("gpt-default",),
            notes="OpenAI Chat Completions",
        )
        raw = original.to_json()
        decoded = ModelProviderProfile.from_json(raw)
        assert decoded == original
        assert decoded.provider_id == "openai"
        assert decoded.capability_hints.capabilities == (
            "text", "reasoning", "tools", "vision",
        )
        assert "open_ai" in decoded.aliases

    def test_profile_to_from_json_accepts_bytes(self) -> None:
        original = _make_profile(provider_id="anthropic", name="Anthropic")
        encoded = original.to_json().encode("utf-8")
        decoded = ModelProviderProfile.from_json(encoded)
        assert decoded.provider_id == "anthropic"

    def test_profile_to_from_json_accepts_dict(self) -> None:
        original = _make_profile(provider_id="gemini", name="Gemini")
        payload = json.loads(original.to_json())
        decoded = ModelProviderProfile.from_json(payload)
        assert decoded == original

    def test_profile_provider_id_is_canonicalized(self) -> None:
        profile = _make_profile(provider_id="  OPENAI-CODEX  ", name="OpenAI Codex")
        assert profile.provider_id == "openai-codex"

    def test_extra_fields_are_forbidden(self) -> None:
        with pytest.raises(Exception):  # Pydantic ValidationError
            _make_profile(provider_id="x", name="X", unknown_field="nope")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# 2. Registry register / get / list / contains / __len__
# ---------------------------------------------------------------------------


class TestRegistryBasicApi:
    def test_empty_registry_has_no_profiles(self, registry: ProviderRegistry) -> None:
        assert len(registry) == 0
        assert registry.list() == ()
        assert registry.ids() == ()

    def test_register_then_get(self, registry: ProviderRegistry) -> None:
        profile = _make_profile(provider_id="openai", name="OpenAI")
        registry.register(profile)
        assert len(registry) == 1
        assert registry.get("openai") is profile

    def test_register_returns_via_alias(self, registry: ProviderRegistry) -> None:
        profile = _make_profile(
            provider_id="openai",
            name="OpenAI",
            aliases=("open_ai", "oai"),
        )
        registry.register(profile)
        assert registry.get("open_ai") is profile
        assert registry.get("oai") is profile

    def test_list_preserves_insertion_order(self, registry: ProviderRegistry) -> None:
        registry.register(_make_profile(provider_id="b", name="B"))
        registry.register(_make_profile(provider_id="a", name="A"))
        registry.register(_make_profile(provider_id="c", name="C"))
        assert registry.ids() == ("b", "a", "c")

    def test_contains_operator(self, registry: ProviderRegistry) -> None:
        registry.register(_make_profile(provider_id="openai", name="OpenAI"))
        assert "openai" in registry
        assert "open_ai" not in registry  # not registered as alias here
        assert "missing" not in registry

    def test_contains_via_alias(self, registry: ProviderRegistry) -> None:
        registry.register(
            _make_profile(provider_id="openai", name="OpenAI", aliases=("open_ai",))
        )
        assert "open_ai" in registry

    def test_try_get_returns_none_on_miss(self, registry: ProviderRegistry) -> None:
        assert registry.try_get("missing") is None
        registry.register(_make_profile(provider_id="openai", name="OpenAI"))
        assert registry.try_get("openai") is not None

    def test_aliases_snapshot_is_a_copy(self, registry: ProviderRegistry) -> None:
        registry.register(
            _make_profile(provider_id="openai", name="OpenAI", aliases=("open_ai",))
        )
        snapshot = registry.aliases()
        snapshot["mutated"] = "openai"
        assert "mutated" not in registry.aliases()

    def test_repr_mentions_profile_count(self, registry: ProviderRegistry) -> None:
        assert repr(registry) == "ProviderRegistry(profiles=0)"
        registry.register(_make_profile(provider_id="x", name="X"))
        assert repr(registry) == "ProviderRegistry(profiles=1)"

    def test_clear_resets_registry(self, registry: ProviderRegistry) -> None:
        registry.register(_make_profile(provider_id="x", name="X"))
        registry.clear()
        assert len(registry) == 0
        assert registry.list() == ()


# ---------------------------------------------------------------------------
# 3. Duplicate provider_id rejected
# ---------------------------------------------------------------------------


class TestDuplicateRegistrationRejected:
    def test_duplicate_provider_id_raises(self, registry: ProviderRegistry) -> None:
        registry.register(_make_profile(provider_id="openai", name="OpenAI"))
        with pytest.raises(DuplicateProviderError) as excinfo:
            registry.register(_make_profile(provider_id="openai", name="OpenAI v2"))
        assert excinfo.value.provider_id == "openai"
        assert isinstance(excinfo.value, ProviderError)
        assert isinstance(excinfo.value, ValueError)

    def test_duplicate_alias_raises(self, registry: ProviderRegistry) -> None:
        registry.register(
            _make_profile(provider_id="openai", name="OpenAI", aliases=("open_ai",))
        )
        with pytest.raises(DuplicateProviderError) as excinfo:
            registry.register(
                _make_profile(provider_id="openai-api", name="OpenAI API", aliases=("open_ai",))
            )
        assert excinfo.value.provider_id == "open_ai"


# ---------------------------------------------------------------------------
# 4. Unknown provider raises clear error
# ---------------------------------------------------------------------------


class TestUnknownProviderRaises:
    def test_get_unknown_raises_not_found(self, registry: ProviderRegistry) -> None:
        with pytest.raises(ProviderNotFoundError) as excinfo:
            registry.get("does-not-exist")
        assert "does-not-exist" in str(excinfo.value)
        assert isinstance(excinfo.value, ProviderError)
        assert isinstance(excinfo.value, KeyError)

    def test_get_unknown_lists_known_providers(self, registry: ProviderRegistry) -> None:
        registry.register(_make_profile(provider_id="a", name="A"))
        registry.register(_make_profile(provider_id="b", name="B"))
        with pytest.raises(ProviderNotFoundError) as excinfo:
            registry.get("missing")
        message = str(excinfo.value)
        # Sorted known ids appear in the message.
        assert "missing" in message


# ---------------------------------------------------------------------------
# 5. Capability / kind / feature lookups
# ---------------------------------------------------------------------------


class TestLookups:
    def test_find_by_capability_returns_matches_in_insertion_order(
        self, registry: ProviderRegistry,
    ) -> None:
        registry.register(_make_profile(provider_id="openai", capabilities=("vision",)))
        registry.register(_make_profile(provider_id="gemini", capabilities=("vision",)))
        registry.register(_make_profile(provider_id="deepseek", capabilities=("coding",)))
        matches = registry.find_by_capability("vision")
        assert [p.provider_id for p in matches] == ["openai", "gemini"]

    def test_find_by_capability_empty_token_raises(
        self, registry: ProviderRegistry,
    ) -> None:
        with pytest.raises(ProviderValidationError):
            registry.find_by_capability("")  # type: ignore[arg-type]

    def test_find_by_kind_returns_matches(self, registry: ProviderRegistry) -> None:
        registry.register(_make_profile(provider_id="anthropic", kind="anthropic_messages"))
        registry.register(_make_profile(provider_id="gemini", kind="gemini"))
        registry.register(_make_profile(provider_id="openai", kind="openai_compatible"))
        matches = registry.find_by_kind("anthropic_messages")
        assert [p.provider_id for p in matches] == ["anthropic"]

    def test_find_local_returns_only_local_profiles(
        self, registry: ProviderRegistry,
    ) -> None:
        registry.register(
            _make_profile(
                provider_id="hf",
                kind="local_openai_compatible",
                capability_hints=ProviderCapabilityHints(
                    capabilities=("text", "local"), local_only=True,
                ),
            )
        )
        registry.register(_make_profile(provider_id="openai"))
        matches = registry.find_local()
        assert [p.provider_id for p in matches] == ["hf"]

    def test_find_with_feature_filters_correctly(
        self, registry: ProviderRegistry,
    ) -> None:
        registry.register(
            _make_profile(provider_id="a", supports_vision=True),
        )
        registry.register(_make_profile(provider_id="b"))  # default no vision
        matches = registry.find_with_feature("vision")
        assert [p.provider_id for p in matches] == ["a"]

    def test_find_with_feature_unknown_raises(
        self, registry: ProviderRegistry,
    ) -> None:
        with pytest.raises(ProviderValidationError):
            registry.find_with_feature("quantum-entanglement")


# ---------------------------------------------------------------------------
# 6. Custom OpenAI-compatible provider validates with base URL requirement
# ---------------------------------------------------------------------------


class TestCustomProviderBaseUrl:
    def test_custom_kind_is_auto_set_to_base_url_required(self) -> None:
        profile = _make_profile(provider_id="custom", kind="custom_openai_compatible")
        assert profile.base_url_required is True

    def test_local_kind_is_auto_set_to_base_url_required(self) -> None:
        profile = _make_profile(provider_id="ollama-cloud", kind="local_openai_compatible")
        assert profile.base_url_required is True

    def test_openai_compatible_does_not_require_base_url(self) -> None:
        profile = _make_profile(provider_id="openai", kind="openai_compatible")
        assert profile.base_url_required is False


# ---------------------------------------------------------------------------
# 7. Local provider flags
# ---------------------------------------------------------------------------


class TestLocalProviderFlags:
    def test_local_provider_auto_marks_local_only(self) -> None:
        profile = _make_profile(
            provider_id="ollama",
            kind="local_openai_compatible",
        )
        assert profile.capability_hints.local_only is True

    def test_remote_provider_default_local_only_is_false(self) -> None:
        profile = _make_profile(provider_id="openai", kind="openai_compatible")
        assert profile.capability_hints.local_only is False


# ---------------------------------------------------------------------------
# 8. Built-in profiles load from providers/defaults.yaml
# ---------------------------------------------------------------------------


class TestBuiltinProfiles:
    def test_load_builtin_profiles_default_path(self, registry: ProviderRegistry) -> None:
        loaded = registry.load_builtin_profiles()
        assert loaded >= 20  # the shipped YAML has 27 entries
        assert len(registry) == loaded
        # A few representative providers must be present.
        for provider_id in ("openai", "anthropic", "gemini", "deepseek", "huggingface"):
            assert provider_id in registry

    def test_load_builtin_profiles_anthropic_is_anthropic_messages(
        self, registry: ProviderRegistry,
    ) -> None:
        registry.load_builtin_profiles()
        profile = registry.get("anthropic")
        assert profile.kind == "anthropic_messages"

    def test_load_builtin_profiles_bedrock_is_bedrock_kind(
        self, registry: ProviderRegistry,
    ) -> None:
        registry.load_builtin_profiles()
        profile = registry.get("bedrock")
        assert profile.kind == "bedrock"
        assert "aws_sdk" in profile.auth_modes

    def test_load_builtin_profiles_huggingface_is_local(
        self, registry: ProviderRegistry,
    ) -> None:
        registry.load_builtin_profiles()
        profile = registry.get("huggingface")
        assert profile.kind == "local_openai_compatible"
        assert profile.capability_hints.local_only is True
        assert "local" in profile.capability_hints.capabilities

    def test_load_builtin_profiles_local_only_auth_modes(
        self, registry: ProviderRegistry,
    ) -> None:
        registry.load_builtin_profiles()
        profile = registry.get("ollama-cloud")
        assert profile.kind == "local_openai_compatible"
        assert profile.auth_modes == ("none",)

    def test_load_builtin_profiles_openai_alias_resolves(
        self, registry: ProviderRegistry,
    ) -> None:
        registry.load_builtin_profiles()
        # The shipped YAML declares openai with alias "open_ai".
        openai_profile = registry.try_get("open_ai")
        assert openai_profile is not None
        assert openai_profile.provider_id == "openai"

    def test_load_builtin_profiles_vision_set(self, registry: ProviderRegistry) -> None:
        registry.load_builtin_profiles()
        vision_providers = registry.find_by_capability("vision")
        # Several providers should have vision in their defaults.
        assert len(vision_providers) >= 3

    def test_load_builtin_profiles_from_explicit_path(
        self, registry: ProviderRegistry, tmp_path: Path,
    ) -> None:
        yaml_path = tmp_path / "providers.yaml"
        yaml_path.write_text(
            "providers:\n"
            "  - id: my-test\n"
            "    aliases: [my_test]\n"
            "    capabilities: [text, coding]\n"
            "    cost_class: low\n"
            "    latency_class: low\n"
            "    reliability_score: 0.9\n",
            encoding="utf-8",
        )
        loaded = registry.load_builtin_profiles(yaml_path)
        assert loaded == 1
        profile = registry.get("my-test")
        assert profile.kind == "openai_compatible"
        assert profile.capability_hints.capabilities == ("text", "coding")
        assert profile.capability_hints.reliability_score == 0.9

    def test_load_builtin_profiles_missing_file_raises(
        self, registry: ProviderRegistry, tmp_path: Path,
    ) -> None:
        with pytest.raises(FileNotFoundError):
            registry.load_builtin_profiles(tmp_path / "does-not-exist.yaml")


# ---------------------------------------------------------------------------
# 9. No network calls
# ---------------------------------------------------------------------------


class TestNoNetworkCalls:
    """The Provider Runtime Registry must never perform network I/O.

    We assert this by importing the package and inspecting the source
    files of the loaded modules for tell-tale networking imports. The
    check is deliberately lightweight: any future addition of
    ``urllib``, ``requests``, ``httpx``, ``socket`` (other than via
    stdlib module-level imports that are not invoked) is a regression.
    """

    def test_no_networking_imports_in_providers_package(self) -> None:
        package_path = Path(__file__).resolve().parents[1] / "loopos" / "providers"
        forbidden_substrings = (
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
        )
        offenders: list[str] = []
        for source_file in sorted(package_path.glob("*.py")):
            text = source_file.read_text(encoding="utf-8")
            for needle in forbidden_substrings:
                if needle in text:
                    offenders.append(f"{source_file.name}: {needle}")
        assert not offenders, (
            "loopos.providers must not import networking modules; offenders: "
            + ", ".join(offenders)
        )

    def test_loading_builtins_does_not_invoke_networking(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Build a registry with built-ins and make sure no networking
        function is called during loading."""
        import socket as _socket
        import urllib.request as _urllib_request

        monkeypatch.setattr(_socket, "socket", None, raising=False)  # type: ignore[arg-type]
        called: list[str] = []

        def _fail(*_args: object, **_kwargs: object) -> None:
            called.append("urllib.request.urlopen")

        monkeypatch.setattr(_urllib_request, "urlopen", _fail, raising=False)
        registry = ProviderRegistry()
        registry.load_builtin_profiles()
        assert called == [], (
            "load_builtin_profiles must not call urllib.request.urlopen"
        )


# ---------------------------------------------------------------------------
# 10. No new third-party dependencies
# ---------------------------------------------------------------------------


class TestNoNewDependencies:
    """The loopos.providers package must add zero new dependencies.

    PyYAML is the only runtime dep, and it is already declared in
    pyproject.toml. We verify this by inspecting the AST of the package
    modules for any non-stdlib, non-pydantic, non-loopos imports.
    """

    def test_imports_are_stdlib_or_declared_deps(self) -> None:
        import ast

        package_path = Path(__file__).resolve().parents[1] / "loopos" / "providers"
        allowed_third_party = frozenset({"pydantic", "yaml"})
        offenders: list[str] = []

        stdlib_module_names = set(sys.stdlib_module_names)

        for source_file in sorted(package_path.glob("*.py")):
            tree = ast.parse(source_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        self._check_import(
                            top, stdlib_module_names, allowed_third_party,
                            offenders, source_file.name,
                        )
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    top = module.split(".")[0]
                    self._check_import(
                        top, stdlib_module_names, allowed_third_party,
                        offenders, source_file.name,
                    )

        assert not offenders, (
            "loopos.providers must not introduce new third-party deps; offenders: "
            + ", ".join(offenders)
        )

    @staticmethod
    def _check_import(
        top: str,
        stdlib: set[str],
        allowed: frozenset[str],
        offenders: list[str],
        source_name: str,
    ) -> None:
        # Relative imports are fine.
        if not top:
            return
        if top in stdlib:
            return
        if top in allowed:
            return
        if top.startswith("loopos"):
            return
        offenders.append(f"{source_name}: {top}")

    def test_providers_module_is_importable(self) -> None:
        # Smoke test: the package imports cleanly under all our public symbols.
        importlib.import_module("loopos.providers")


# ---------------------------------------------------------------------------
# 11. validate_profile() exposed publicly
# ---------------------------------------------------------------------------


class TestValidateProfile:
    def test_validate_passes_for_valid_profile(self, registry: ProviderRegistry) -> None:
        profile = _make_profile(provider_id="openai", name="OpenAI")
        registry.validate_profile(profile)  # no raise

    def test_validate_rejects_non_profile(self, registry: ProviderRegistry) -> None:
        with pytest.raises(ProviderValidationError):
            registry.validate_profile({"id": "openai"})  # type: ignore[arg-type]

    def test_validate_rejects_unknown_capability_at_construction(self) -> None:
        # The capability constraint is enforced by Pydantic at construction
        # time, so an invalid profile never reaches validate_profile().
        with pytest.raises(Exception):
            ProviderCapabilityHints(capabilities=("text", "unicorns"))  # type: ignore[arg-type]  # noqa: E501

    def test_validate_rejects_mismatched_auth_modes(self, registry: ProviderRegistry) -> None:
        # Build a profile with model_construct (skips validation) carrying
        # an auth_modes value the validator would reject, then confirm
        # validate_profile() surfaces it as ProviderValidationError.
        bad = ModelProviderProfile.model_construct(  # type: ignore[call-arg]
            provider_id="x",
            name="X",
            kind="openai_compatible",
            capability_hints=ProviderCapabilityHints(capabilities=("text",)),
            auth_modes=("api_key", "magic-wand"),  # type: ignore[arg-type]
        )
        with pytest.raises(ProviderValidationError):
            registry.validate_profile(bad)  # type: ignore[arg-type]  # noqa: E501


# ---------------------------------------------------------------------------
# 12. Capability-hint sub-model
# ---------------------------------------------------------------------------


class TestProviderCapabilityHints:
    def test_default_capability_is_text(self) -> None:
        hints = ProviderCapabilityHints()
        assert hints.capabilities == ("text",)
        assert hints.cost_class == "unknown"
        assert hints.latency_class == "unknown"
        assert hints.reliability_score == 0.5
        assert hints.local_only is False

    def test_capabilities_are_deduplicated(self) -> None:
        hints = ProviderCapabilityHints(capabilities=("text", "tools", "text"))
        assert hints.capabilities == ("text", "tools")

    def test_capabilities_normalised_to_lowercase(self) -> None:
        hints = ProviderCapabilityHints(capabilities=("VISION", "Coding"))
        assert hints.capabilities == ("vision", "coding")

    def test_unknown_capability_rejected(self) -> None:
        with pytest.raises(Exception):
            ProviderCapabilityHints(capabilities=("text", "unicorns"))  # type: ignore[arg-type]

    def test_reliability_score_clamped(self) -> None:
        with pytest.raises(Exception):
            ProviderCapabilityHints(reliability_score=2.0)
        with pytest.raises(Exception):
            ProviderCapabilityHints(reliability_score=-0.1)
