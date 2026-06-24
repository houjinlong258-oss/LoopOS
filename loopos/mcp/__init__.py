"""LoopOS v0.3 MCP — present but not production-wired.

.. important::

    **MCP on v0.3 is a compatibility facade over the canonical
    syscall router.** The v0.3 implementation lives in
    :mod:`loopos.mcp.router` and :mod:`loopos.mcp.types`. It
    exposes a :class:`ToolRouter` that translates ``ToolCall``
    objects into :class:`~loopos.syscalls.SyscallCall` objects
    and dispatches them through the v0.2
    :func:`create_default_syscall_router` (so the same Policy OS
    checks apply).

    **The MCP router is not wired into the kernel loop on v0.3.**
    The ``KernelLoopEngine._SYSCALLS`` table maps
    ``TERM.EXEC``, ``FILE.READ``, ``FILE.WRITE``, ``GIT.STATUS``,
    ``GIT.DIFF`` -- it does **not** include ``TOOL.CALL``. The
    v0.3 kernel loop never dispatches to the MCP router. The
    router is reachable from the workbench and from test code
    via ``create_default_router()``, but production runs do not
    exercise it.

    **Full production wiring is deferred to v0.4 (Governed MCP
    Gateway).** v0.4 will:

    1. Add a ``TOOL.CALL`` entry to ``KernelLoopEngine._SYSCALLS``
       so the kernel loop can dispatch to the MCP router.
    2. Define a typed AIL op family (``TOOL.RESOLVE`` /
       ``TOOL.CALL`` / ``TOOL.RESULT``) with Policy OS hooks.
    3. Add a governance layer: per-tool approval memory,
       per-session allow-lists, and a per-tool rate limit.
    4. Add an audit trail: every tool call lands in the
       governed trace store with redaction.

    See :doc:`v0-3-mcp-boundary` for the full decision record
    and the v0.4 plan.
"""

from __future__ import annotations

from loopos.mcp.router import ToolRouter, create_default_router
from loopos.mcp.types import (
    RegisteredTool,
    ToolCall,
    ToolHandler,
    ToolRegistry,
    ToolResult,
    ToolRiskLevel,
    ToolSpec,
)

__all__ = [
    "RegisteredTool",
    "ToolCall",
    "ToolHandler",
    "ToolRegistry",
    "ToolResult",
    "ToolRiskLevel",
    "ToolRouter",
    "ToolSpec",
    "create_default_router",
]