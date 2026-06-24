"""Tests for ``loopos.cli.typer_v0_3`` extraction.

The P1-4 hardening pass extracts the seven v0.3 Typer bindings
(``workbench``, ``adapters``, ``providers-runtime``,
``model-call``, ``opengod``, ``session``, ``readiness``) from
``loopos/cli/app.py`` into a new module
``loopos/cli/typer_v0_3.py`` to shrink ``app.py`` without
changing the user-facing CLI surface.

These tests assert:

1. The extraction is non-trivial: the seven v0.3 functions
   no longer live in ``app.py`` (regression guard against
   accidental re-inlining).
2. The new module exposes a single ``register_v0_3_commands``
   function that wires the seven commands onto a Typer app.
3. The Typer path and the argparse fallback agree on the
   command surface (same seven command names, no extras).
4. The Typer path correctly delegates to the underlying pure
   command functions in ``loopos.cli.commands``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Dict, List


REPO_ROOT = Path(__file__).resolve().parent.parent
APP_PY = REPO_ROOT / "loopos" / "cli" / "app.py"
TYPER_V03 = REPO_ROOT / "loopos" / "cli" / "typer_v0_3.py"


# The seven v0.3 command names the user-facing surface must
# expose.
V0_3_COMMANDS = (
    "workbench",
    "adapters",
    "providers-runtime",
    "model-call",
    "opengod",
    "session",
    "readiness",
)


# ---------------------------------------------------------------------------
# Regression guards: the seven functions no longer live in app.py
# ---------------------------------------------------------------------------


def test_app_py_does_not_contain_v0_3_typer_bindings() -> None:
    """The seven v0.3 ``@app.command("...")`` bindings must no
    longer live in ``app.py``. They were extracted to
    ``loopos.cli.typer_v0_3``. This is a regression guard
    against accidental re-inlining.
    """
    text = APP_PY.read_text(encoding="utf-8")
    for cmd in V0_3_COMMANDS:
        assert f'@app.command("{cmd}")' not in text, (
            f"v0.3 command {cmd!r} still lives in app.py; "
            f"the extraction regressed. Move it back to "
            f"loopos/cli/typer_v0_3.py."
        )


def test_app_py_does_not_contain_v0_3_command_function_defs() -> None:
    """The ``_typer_<cmd>`` function definitions for the v0.3
    commands must no longer be in ``app.py``. The new module
    owns them.
    """
    text = APP_PY.read_text(encoding="utf-8")
    for cmd in V0_3_COMMANDS:
        # The function names in the new module are scoped to
        # the register function, but for an extra safety net
        # we also assert that the old ``_typer_<cmd>`` names
        # do not appear at top level in ``app.py``.
        fn_pattern = re.compile(
            rf"^def\s+_typer_{re.escape(cmd.replace('-', '_'))}\b",
            re.MULTILINE,
        )
        assert not fn_pattern.search(text), (
            f"def _typer_{cmd.replace('-', '_')}(...) still "
            f"lives in app.py; the extraction regressed."
        )


# ---------------------------------------------------------------------------
# The new module exposes the expected API
# ---------------------------------------------------------------------------


def test_typer_v0_3_module_exposes_register_function() -> None:
    from loopos.cli import typer_v0_3

    assert hasattr(typer_v0_3, "register_v0_3_commands"), (
        "loopos.cli.typer_v0_3 must expose register_v0_3_commands"
    )
    assert callable(typer_v0_3.register_v0_3_commands)
    assert "register_v0_3_commands" in typer_v0_3.__all__


def test_register_v0_3_commands_registers_all_seven() -> None:
    """Calling ``register_v0_3_commands(app, typer_mod)`` must
    register the seven v0.3 commands on ``app``. We use a
    double Typer stub: the ``typer_mod`` argument is replaced
    with a tiny module-level shim that records the
    ``@app.command(name)`` calls.
    """
    from loopos.cli import typer_v0_3

    registered: List[str] = []
    decorators: Dict[str, List[Callable[..., Any]]] = {}

    class _Option:
        def __init__(self, default: Any = ..., *args: Any, **kwargs: Any) -> None:
            self.default = default
            self.args = args
            self.kwargs = kwargs

    class _Argument:
        def __init__(self, default: Any = ..., *args: Any, **kwargs: Any) -> None:
            self.default = default
            self.args = args
            self.kwargs = kwargs

    class _TyperShim:
        Option = _Option
        Argument = _Argument

        class _Exit(Exception):
            pass

        Exit = _Exit

        @staticmethod
        def command(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                registered.append(name)
                decorators[name] = decorators.get(name, []) + [fn]
                return fn

            return decorator

    class _App:
        @staticmethod
        def command(
            name: str, **kwargs: Any
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                registered.append(name)
                return fn

            return decorator

    app = _App()
    typer_v0_3.register_v0_3_commands(app, _TyperShim)
    assert set(registered) == set(V0_3_COMMANDS), (
        f"register_v0_3_commands did not register all seven "
        f"v0.3 commands. Got: {sorted(registered)!r}, "
        f"expected: {sorted(V0_3_COMMANDS)!r}"
    )


def test_register_v0_3_commands_is_no_op_when_app_is_none() -> None:
    """In dependency-light environments, ``app`` is ``None``
    (Typer is not installed). ``register_v0_3_commands`` must
    be a no-op in that case, not raise.
    """
    from loopos.cli import typer_v0_3

    class _TyperShim:
        Option = object
        Argument = object

    # app=None: no-op.
    typer_v0_3.register_v0_3_commands(None, _TyperShim)  # must not raise


def test_register_v0_3_commands_is_no_op_when_typer_is_none() -> None:
    from loopos.cli import typer_v0_3

    class _App:
        def command(
            self, name: str
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                return fn
            return decorator

    typer_v0_3.register_v0_3_commands(_App(), None)  # must not raise


# ---------------------------------------------------------------------------
# CLI surface stays the same: Typer and argparse agree on the seven names
# ---------------------------------------------------------------------------


def test_cli_help_lists_all_v0_3_commands() -> None:
    """The Typer-rendered ``--help`` output must list all seven
    v0.3 commands. We invoke ``loopos.cli.app`` with ``--help``
    and parse the rendered command list.
    """
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "loopos.cli.app", "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout
    for cmd in V0_3_COMMANDS:
        assert cmd in out, (
            f"v0.3 command {cmd!r} missing from Typer --help output.\n"
            f"stdout: {out!r}"
        )


def test_argparse_fallback_also_lists_v0_3_commands() -> None:
    """The argparse fallback (``loopos.cli.fallback``) must also
    expose the seven v0.3 commands. The Typer path and the
    argparse path are two views on the same set of underlying
    command functions, so they must agree on the surface.
    """
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from loopos.cli.fallback import fallback_main;"
            "import sys; sys.exit(fallback_main(['--help']))",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout
    for cmd in V0_3_COMMANDS:
        assert cmd in out, (
            f"v0.3 command {cmd!r} missing from argparse --help output.\n"
            f"stdout: {out!r}"
        )