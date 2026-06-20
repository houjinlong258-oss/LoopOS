"""LoopOS syscall layer."""

from loopos.syscalls.registry import SyscallRegistry
from loopos.syscalls.router import SyscallRouter, create_default_syscall_router
from loopos.syscalls.types import SyscallCall, SyscallResult, SyscallSpec

__all__ = [
    "SyscallCall",
    "SyscallRegistry",
    "SyscallResult",
    "SyscallRouter",
    "SyscallSpec",
    "create_default_syscall_router",
]
