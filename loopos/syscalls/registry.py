"""In-memory syscall registry."""

from loopos.syscalls.types import RegisteredSyscall, SyscallHandler, SyscallSpec


class SyscallRegistry:
    def __init__(self) -> None:
        self._items: dict[str, RegisteredSyscall] = {}

    def register(self, spec: SyscallSpec, handler: SyscallHandler) -> None:
        if spec.name in self._items:
            raise ValueError(f"syscall already registered: {spec.name}")
        self._items[spec.name] = RegisteredSyscall(spec=spec, handler=handler)

    def resolve(self, name: str) -> RegisteredSyscall:
        try:
            return self._items[name]
        except KeyError as exc:
            raise KeyError(f"unknown syscall: {name}") from exc

    def list(self) -> list[SyscallSpec]:
        return [item.spec for item in self._items.values()]

