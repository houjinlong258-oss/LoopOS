"""Deterministic Kernel boot sequence."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from loopos.kernel.run_manager import RunManager
from loopos.kernel.trace import TraceStore
from loopos.policy_os.engine import PolicyEngine
from loopos.syscalls import SyscallRouter, create_default_syscall_router


class KernelConfig(BaseModel):
    workspace: str = "."
    data_dir: str = ".loopos"
    policy_dir: str | None = None
    auto_approve_medium: bool = False


class KernelBootError(RuntimeError):
    pass


@dataclass(frozen=True)
class KernelRuntime:
    config: KernelConfig
    policy_engine: PolicyEngine
    syscall_router: SyscallRouter
    trace_store: TraceStore
    run_manager: RunManager


class KernelBoot:
    """Load config, policies, syscalls, stores, workspace, and run manager."""

    def start(self, config: KernelConfig) -> KernelRuntime:
        workspace = Path(config.workspace).resolve()
        if not workspace.exists() or not workspace.is_dir():
            raise KernelBootError(f"workspace does not exist: {workspace}")
        if not os.access(workspace, os.R_OK | os.W_OK):
            raise KernelBootError(f"workspace is not writable: {workspace}")

        try:
            engine = (
                PolicyEngine.load_default(config.policy_dir)
                if config.policy_dir is not None
                else PolicyEngine.load_default()
            )
        except (OSError, ValueError) as exc:
            raise KernelBootError(f"policy pack load failed: {exc}") from exc
        if config.policy_dir is not None and not engine.registry.packs:
            raise KernelBootError(f"missing policy pack: {config.policy_dir}")

        try:
            data_dir = Path(config.data_dir)
            trace = TraceStore(data_dir / "events.jsonl")
            manager = RunManager(data_dir / "runs")
            syscalls = create_default_syscall_router(
                workspace,
                policy_engine=engine,
                trace_store=trace,
                auto_approve_medium=config.auto_approve_medium,
            )
        except (OSError, ValueError) as exc:
            raise KernelBootError(f"kernel store or syscall initialization failed: {exc}") from exc

        return KernelRuntime(config, engine, syscalls, trace, manager)

