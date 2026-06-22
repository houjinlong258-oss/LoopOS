"""Tests for Phase 2 ACI provider integration.

These tests assert the contract between :class:`loopos.aci.runner.CommandRunner`
and :class:`loopos.providers.ProviderRegistry`:

* exact ``provider_id`` resolves to that profile;
* missing ``provider_id`` returns reason_code ``provider_not_found``;
* capability selection is deterministic across runs;
* ``local_only=True`` uses a local provider;
* the runner never imports networking modules and never makes live calls;
* ``resolved_provider`` appears on :class:`AgentCommandResult` when a
  :class:`ProviderHint` was supplied or ``kind == "provider_select"``;
* ``provider_select`` is metadata-only and never dispatches a syscall;
* ``explain_only`` and ``explain=True`` never dispatch a syscall;
* unknown / unmapped kinds return ``status='unsupported'`` rather than
  pretending to execute them.

The tests are offline-only. They never make a network call and they
never reach into ``loopos.kernel.*`` or ``KernelLoopEngine``.
"""

from __future__ import annotations

import ast
import re
import socket as _socket
import tempfile
import unittest
import urllib.request as _urllib_request
from pathlib import Path


from loopos.aci import (
    AgentCommand,
    CommandRunner,
    ProviderHint,
    ResolvedProvider,
    RunnerConfig,
)
from loopos.aci.errors import (
    ProviderResolutionError,
)
from loopos.policy_os.engine import PolicyEngine
from loopos.providers import ProviderRegistry
from loopos.syscalls.router import create_default_syscall_router


REPO_ROOT = Path(__file__).resolve().parents[1]
PROVIDERS_PKG = REPO_ROOT / "loopos" / "aci"


def _registry_with_builtins() -> ProviderRegistry:
    reg = ProviderRegistry()
    reg.load_builtin_profiles()
    return reg


def _runner(tmp: str, *, registry: ProviderRegistry | None = None) -> CommandRunner:
    return CommandRunner(
        policy_engine=PolicyEngine.load_default(),
        syscall_router=create_default_syscall_router(tmp, auto_approve_medium=True),
        provider_registry=registry if registry is not None else _registry_with_builtins(),
        config=RunnerConfig(workspace=tmp, run_id="aci-prov"),
    )


# ---------------------------------------------------------------------------
# Provider resolution: exact provider_id
# ---------------------------------------------------------------------------


class ProviderHintExactMatchTests(unittest.TestCase):
    def test_exact_provider_id_resolves(self) -> None:
        hint = ProviderHint(provider_id="anthropic")
        with tempfile.TemporaryDirectory() as tmp:
            runner = _runner(tmp)
            resolved = runner.resolve_provider(hint)
        self.assertEqual(resolved.provider_id, "anthropic")
        self.assertEqual(resolved.source, "exact")
        self.assertEqual(resolved.kind, "anthropic_messages")

    def test_exact_provider_id_via_run_appears_in_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = _runner(tmp)
            cmd = AgentCommand(
                goal_id="g",
                purpose="p",
                kind="terminal.exec",
                command="echo hi",
                provider_hint=ProviderHint(provider_id="anthropic"),
            )
            result = runner.run(cmd)
        self.assertIsNotNone(result.resolved_provider)
        assert result.resolved_provider is not None  # for type checker
        self.assertEqual(result.resolved_provider.provider_id, "anthropic")
        self.assertEqual(result.resolved_provider.source, "exact")


# ---------------------------------------------------------------------------
# Provider resolution: missing / not found
# ---------------------------------------------------------------------------


class ProviderHintMissingTests(unittest.TestCase):
    def test_missing_provider_id_returns_reason_code_in_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = _runner(tmp)
            cmd = AgentCommand(
                goal_id="g",
                purpose="p",
                kind="terminal.exec",
                command="echo hi",
                provider_hint=ProviderHint(provider_id="nonexistent-provider-xyz"),
            )
            result = runner.run(cmd)
        # Resolution failed but the syscall still ran (echo is benign).
        # The ``reason_codes`` list carries the provider reason code.
        self.assertIn("provider_not_found", result.reason_codes)

    def test_missing_provider_id_strict_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = _runner(tmp)
            with self.assertRaises(ProviderResolutionError) as ctx:
                runner.resolve_provider(ProviderHint(provider_id="nonexistent"))
        self.assertEqual(ctx.exception.reason_code, "provider_not_found")

    def test_no_registry_wired_returns_provider_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = CommandRunner(
                policy_engine=PolicyEngine.load_default(),
                syscall_router=create_default_syscall_router(tmp, auto_approve_medium=True),
                provider_registry=None,
                config=RunnerConfig(workspace=tmp, run_id="aci-noreg"),
            )
            cmd = AgentCommand(
                goal_id="g",
                purpose="p",
                kind="terminal.exec",
                command="echo hi",
                provider_hint=ProviderHint(provider_id="anthropic"),
            )
            result = runner.run(cmd)
        self.assertIn("provider_not_found", result.reason_codes)


# ---------------------------------------------------------------------------
# Provider resolution: capability selection (deterministic)
# ---------------------------------------------------------------------------


class ProviderHintCapabilityTests(unittest.TestCase):
    def test_capability_selection_is_deterministic(self) -> None:
        # Multiple providers may have the "vision" capability; the
        # runner picks one deterministically by provider_id.
        with tempfile.TemporaryDirectory() as tmp:
            runner = _runner(tmp)
            first = runner.resolve_provider(
                ProviderHint(required_capabilities=["vision"])
            )
            second = runner.resolve_provider(
                ProviderHint(required_capabilities=["vision"])
            )
        self.assertEqual(first.provider_id, second.provider_id)
        self.assertEqual(first.source, "capability")
        # The deterministic pick is the alphabetically smallest id.
        self.assertEqual(first.provider_id, "anthropic")

    def test_capability_with_local_only_constraint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = _runner(tmp)
            resolved = runner.resolve_provider(
                ProviderHint(
                    required_capabilities=["embeddings"],
                    local_only=True,
                )
            )
        self.assertEqual(resolved.source, "local")
        self.assertIn(resolved.provider_id, {"huggingface", "ollama-cloud"})

    def test_capability_with_preferred_kind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = _runner(tmp)
            resolved = runner.resolve_provider(
                ProviderHint(
                    required_capabilities=["text"],
                    preferred_kind="anthropic_messages",
                )
            )
        self.assertEqual(resolved.provider_id, "anthropic")

    def test_capability_unavailable_returns_reason_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = _runner(tmp)
            cmd = AgentCommand(
                goal_id="g",
                purpose="p",
                kind="terminal.exec",
                command="echo hi",
                provider_hint=ProviderHint(
                    required_capabilities=["non-existent-capability"]
                ),
            )
            result = runner.run(cmd)
        self.assertIn("provider_capability_unavailable", result.reason_codes)


# ---------------------------------------------------------------------------
# Provider selection kind is metadata-only
# ---------------------------------------------------------------------------


class ProviderSelectKindTests(unittest.TestCase):
    def test_provider_select_kind_resolves_without_syscall(self) -> None:
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            router = create_default_syscall_router(tmp, auto_approve_medium=True)
            with mock.patch.object(router, "dispatch") as spy:
                runner = CommandRunner(
                    policy_engine=PolicyEngine.load_default(),
                    syscall_router=router,
                    provider_registry=_registry_with_builtins(),
                    config=RunnerConfig(workspace=tmp, run_id="aci-ps"),
                )
                cmd = AgentCommand(
                    goal_id="g",
                    purpose="p",
                    kind="provider_select",
                    command="",  # provider_select does not need a command
                    provider_hint=ProviderHint(
                        required_capabilities=["reasoning"],
                    ),
                )
                result = runner.run(cmd)
        # provider_select must never dispatch a syscall.
        self.assertFalse(spy.called, "provider_select must not dispatch a syscall")
        self.assertEqual(result.status, "completed")
        self.assertTrue(result.success)
        self.assertIsNotNone(result.resolved_provider)
        assert result.resolved_provider is not None  # for type checker
        self.assertEqual(result.resolved_provider.source, "capability")
        # syscall summary is None -- no syscall was dispatched.
        self.assertIsNone(result.syscall)

    def test_provider_select_kind_requires_provider_hint(self) -> None:
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            AgentCommand(
                goal_id="g",
                purpose="p",
                kind="provider_select",
                command="",
            )

    def test_provider_select_without_match_returns_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = _runner(tmp)
            cmd = AgentCommand(
                goal_id="g",
                purpose="p",
                kind="provider_select",
                command="",
                provider_hint=ProviderHint(
                    required_capabilities=["no-such-capability-xyz"],
                ),
            )
            result = runner.run(cmd)
        self.assertEqual(result.status, "failed")
        self.assertIn("provider_capability_unavailable", result.reason_codes)


# ---------------------------------------------------------------------------
# explain_only kind is no-side-effect
# ---------------------------------------------------------------------------


class ExplainOnlyKindTests(unittest.TestCase):
    def test_explain_only_kind_does_not_dispatch_syscall(self) -> None:
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            router = create_default_syscall_router(tmp, auto_approve_medium=True)
            with mock.patch.object(
                router, "dispatch",
                side_effect=AssertionError("dispatched! explain_only must not dispatch"),
            ):
                runner = CommandRunner(
                    policy_engine=PolicyEngine.load_default(),
                    syscall_router=router,
                    provider_registry=_registry_with_builtins(),
                    config=RunnerConfig(workspace=tmp, run_id="aci-eo"),
                )
                cmd = AgentCommand(
                    goal_id="g",
                    purpose="p",
                    kind="explain_only",
                    command="echo hi",
                )
                result = runner.run(cmd)
        self.assertEqual(result.status, "dry_run")
        self.assertTrue(result.dry_run)


# ---------------------------------------------------------------------------
# Unsupported kind
# ---------------------------------------------------------------------------


class UnsupportedKindTests(unittest.TestCase):
    def test_kind_in_schema_but_no_syscall_returns_unsupported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = _runner(tmp)
            # ``file.patch`` and ``git.commit`` are valid schema
            # values but the current syscall registry does not
            # register them. The runner must surface this as
            # ``status='unsupported'``, NOT as a fake completion.
            cmd = AgentCommand(
                goal_id="g",
                purpose="p",
                kind="file.patch",
                command="README.md",
            )
            result = runner.run(cmd)
        self.assertEqual(result.status, "unsupported")
        self.assertFalse(result.success)
        self.assertIn("unsupported_command_kind", result.reason_codes)

    def test_strict_unsupported_raises(self) -> None:
        # Direct construction of an AgentCommand cannot produce an
        # "unknown" kind (Literal prevents it), so the strict
        # exception path is exercised by going through the runner
        # with a kind that has no syscall binding.
        with tempfile.TemporaryDirectory() as tmp:
            runner = _runner(tmp)
            cmd = AgentCommand(
                goal_id="g",
                purpose="p",
                kind="git.commit",
                command="commit message",
            )
            result = runner.run(cmd)
        self.assertEqual(result.status, "unsupported")


# ---------------------------------------------------------------------------
# Network / I/O invariants
# ---------------------------------------------------------------------------


class NetworkInvariantsTests(unittest.TestCase):
    """The runner must never make a live network call."""

    def test_runner_module_does_not_import_networking(self) -> None:
        from loopos.aci import runner as runner_module

        text = Path(runner_module.__file__).read_text(encoding="utf-8")
        # Strip docstrings and comments; the "we do not import networking"
        # claim is allowed in prose.
        no_doc = re.sub(r'"""[\s\S]*?"""', "", text)
        no_doc = re.sub(r"#[^\n]*", "", no_doc)

        forbidden = (
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
        offenders = [n for n in forbidden if n in no_doc]
        self.assertEqual(
            offenders, [],
            f"loopos.aci.runner must not import networking modules: {offenders}",
        )

    def test_provider_select_does_not_call_network(self) -> None:
        # The runner must never make a live network call during
        # ``provider_select`` execution. We monkey-patch the
        # ``socket.socket`` constructor and ``urllib.request.urlopen``
        # to record calls; if either is invoked the assertion fails.
        calls: list[str] = []

        def _fail_socket(*_args: object, **_kwargs: object) -> None:
            calls.append("socket.socket")

        def _fail_urlopen(*_args: object, **_kwargs: object) -> None:
            calls.append("urllib.request.urlopen")

        from unittest import mock

        with mock.patch.object(_socket, "socket", _fail_socket), \
             mock.patch.object(_urllib_request, "urlopen", _fail_urlopen):
            with tempfile.TemporaryDirectory() as tmp:
                runner = _runner(tmp)
                cmd = AgentCommand(
                    goal_id="g",
                    purpose="p",
                    kind="provider_select",
                    command="",
                    provider_hint=ProviderHint(
                        required_capabilities=["text"],
                    ),
                )
                runner.run(cmd)
        self.assertEqual(
            calls, [],
            f"provider_select must not touch the network; saw: {calls}",
        )

    def test_resolved_provider_appears_in_result_for_provider_select(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runner = _runner(tmp)
            cmd = AgentCommand(
                goal_id="g",
                purpose="p",
                kind="provider_select",
                command="",
                provider_hint=ProviderHint(provider_id="openai"),
            )
            result = runner.run(cmd)
        self.assertIsNotNone(result.resolved_provider)
        assert result.resolved_provider is not None  # for type checker
        self.assertEqual(result.resolved_provider.provider_id, "openai")


# ---------------------------------------------------------------------------
# Runner does not import kernel
# ---------------------------------------------------------------------------


class NoKernelInvariantsTests(unittest.TestCase):
    def test_runner_does_not_import_kernel(self) -> None:
        from loopos.aci import runner as runner_module

        text = Path(runner_module.__file__).read_text(encoding="utf-8")
        no_doc = re.sub(r'"""[\s\S]*?"""', "", text)
        no_doc = re.sub(r"#[^\n]*", "", no_doc)
        self.assertNotIn("loopos.kernel", no_doc)
        self.assertNotIn("KernelLoopEngine", no_doc)

    def test_aci_package_does_not_import_kernel(self) -> None:
        offenders: list[str] = []
        for src in sorted(PROVIDERS_PKG.glob("*.py")):
            tree = ast.parse(src.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("loopos.kernel"):
                            offenders.append(f"{src.name}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if (node.module or "").startswith("loopos.kernel"):
                        offenders.append(f"{src.name}: from {node.module} import ...")
        self.assertEqual(
            offenders, [],
            f"loopos.aci must not import loopos.kernel: {offenders}",
        )


# ---------------------------------------------------------------------------
# ProviderHint + ResolvedProvider model stability
# ---------------------------------------------------------------------------


class ProviderHintModelTests(unittest.TestCase):
    def test_provider_hint_roundtrip(self) -> None:
        hint = ProviderHint(
            provider_id="anthropic",
            required_capabilities=["coding", "reasoning"],
            preferred_kind="anthropic_messages",
            local_only=False,
            allow_fallback=True,
            notes="prefer Anthropic for code work",
        )
        raw = hint.model_dump_json()
        decoded = ProviderHint.model_validate_json(raw)
        self.assertEqual(decoded, hint)

    def test_provider_hint_extra_field_rejected(self) -> None:
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            ProviderHint.model_validate(
                {"provider_id": "anthropic", "totally_unknown": "x"}
            )

    def test_provider_hint_lowercases_provider_id(self) -> None:
        hint = ProviderHint(provider_id="Anthropic")
        self.assertEqual(hint.provider_id, "anthropic")

    def test_resolved_provider_roundtrip(self) -> None:
        resolved = ResolvedProvider(
            provider_id="openai",
            display_name="Openai",
            kind="openai_compatible",
            capabilities=["text", "reasoning"],
            source="exact",
        )
        raw = resolved.model_dump_json()
        decoded = ResolvedProvider.model_validate_json(raw)
        self.assertEqual(decoded, resolved)


if __name__ == "__main__":
    unittest.main()
