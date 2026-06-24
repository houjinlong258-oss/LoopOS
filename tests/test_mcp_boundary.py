"""Tests for the v0.3 MCP boundary (Option B).

The v0.3-alpha split-audit flagged a possible dead-code concern:
the MCP router exists but the kernel loop does not dispatch to
it. The P1-3 audit confirms the boundary: the router is
reachable from tests + manual wiring, but the kernel loop's
``_SYSCALLS`` table does not include ``TOOL.CALL``. Production
wiring is deferred to v0.4 (Governed MCP Gateway).

These tests pin the boundary down:

1. The MCP module docstring declares "present but not
   production-wired on v0.3".
2. ``KernelLoopEngine._SYSCALLS`` does not include
   ``TOOL.CALL`` (asserted via reflection rather than textual
   grep, so a future refactor of the syscall table does not
   silently flip the wiring).
3. The MCP router's public API is stable: ``create_default_router``
   still returns a working router, the contracts remain typed.
4. The v0.3 readiness check exposes the new boundary check.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MCP_INIT = REPO_ROOT / "loopos" / "mcp" / "__init__.py"


# ---------------------------------------------------------------------------
# Docstring + boundary
# ---------------------------------------------------------------------------


def test_mcp_module_docstring_states_present_not_wired() -> None:
    import re

    text = MCP_INIT.read_text(encoding="utf-8")
    match = re.search(r'^"""(?P<body>.*?)"""', text, re.DOTALL | re.MULTILINE)
    assert match is not None, "loopos/mcp/__init__.py has no module docstring"
    body = match.group("body")
    assert "not production-wired" in body, (
        "module docstring must declare MCP is not production-wired on v0.3"
    )
    assert "v0.4" in body, (
        "module docstring must reference the v0.4 follow-up plan"
    )
    assert "TOOL.CALL" in body, (
        "module docstring must mention the missing TOOL.CALL syscall entry"
    )


# ---------------------------------------------------------------------------
# Kernel-loop syscall table guard
# ---------------------------------------------------------------------------


def test_kernel_loop_engine_does_not_dispatch_tool_call() -> None:
    """``KernelLoopEngine._SYSCALLS`` must not include
    ``TOOL.CALL`` on v0.3. This is a reflection check, not a
    textual grep, so a future refactor of the syscall table
    cannot silently flip the wiring.
    """
    import loopos.kernel.loop_engine as loop_engine

    syscalls = getattr(loop_engine, "_SYSCALLS", None)
    assert syscalls is not None, (
        "loopos.kernel.loop_engine._SYSCALLS missing; cannot audit MCP wiring"
    )
    assert isinstance(syscalls, dict), (
        f"loopos.kernel.loop_engine._SYSCALLS must be a dict, got {type(syscalls)!r}"
    )
    assert "TOOL.CALL" not in syscalls, (
        f"TOOL.CALL must not be in _SYSCALLS on v0.3; "
        f"production MCP wiring is deferred to v0.4. Current _SYSCALLS: "
        f"{sorted(syscalls.keys())!r}"
    )
    # The five v0.3 syscalls must still be present (regression
    # guard: the P1 pass must not have removed them).
    for required in (
        "TERM.EXEC",
        "FILE.READ",
        "FILE.WRITE",
        "GIT.STATUS",
        "GIT.DIFF",
    ):
        assert required in syscalls, (
            f"v0.3 syscall {required!r} missing from _SYSCALLS"
        )


# ---------------------------------------------------------------------------
# Public API stability: the router must still be reachable and functional
# ---------------------------------------------------------------------------


def test_mcp_router_still_constructs_and_dispatches() -> None:
    """The compat facade must still work: a caller that wires
    ``create_default_router()`` manually must get a router
    that goes through the Policy OS gate and dispatches
    correctly.
    """
    from loopos.mcp import (
        ToolCall,
        ToolResult,
        create_default_router,
    )

    router = create_default_router(workspace=str(REPO_ROOT), auto_approve=False)
    # The router should expose the v0.2 syscalls as tools
    # (TERM.EXEC, FILE.READ, etc.).
    tool_names = sorted(t.name for t in router.list_tools())
    assert "file.read" in tool_names
    assert "file.write" in tool_names
    assert "terminal.exec" in tool_names

    # A high-risk tool call without auto-approve must be
    # blocked at the policy gate, not at the handler.
    high_call = ToolCall(
        name="file.write",
        args={"path": "/tmp/should-not-be-written", "content": "x"},
        metadata={},
    )
    result = router.call(high_call)
    assert isinstance(result, ToolResult)
    assert result.success is False
    # The router must NOT have written the file when the policy
    # gate refused the call.
    assert not Path("/tmp/should-not-be-written").exists()


def test_mcp_public_api_exports_match_v0_3() -> None:
    """The MCP public API must remain stable on v0.3: callers
    who import from ``loopos.mcp`` get the same set of names
    they got before the P1 pass.
    """
    import loopos.mcp as mcp

    expected = {
        "RegisteredTool",
        "ToolCall",
        "ToolHandler",
        "ToolRegistry",
        "ToolResult",
        "ToolRiskLevel",
        "ToolRouter",
        "ToolSpec",
        "create_default_router",
    }
    assert set(mcp.__all__) == expected, (
        f"loopos.mcp public API changed: {set(mcp.__all__) ^ expected!r}"
    )
    # And the symbols are importable.
    for name in expected:
        assert hasattr(mcp, name), f"loopos.mcp missing {name}"


# ---------------------------------------------------------------------------
# Readiness check integration
# ---------------------------------------------------------------------------


def test_readiness_check_exposes_mcp_boundary_check() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "v0_3_readiness_check.py"), "--json"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO_ROOT),
    )
    payload = json.loads(result.stdout)
    assert "mcp_present_not_wired_boundary" in payload["checks"], (
        "v0.3 readiness check must include mcp_present_not_wired_boundary"
    )
    check = payload["checks"]["mcp_present_not_wired_boundary"]
    assert check["status"] is True, check["detail"]
    assert payload["status"] == "pass"