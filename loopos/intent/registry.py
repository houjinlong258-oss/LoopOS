"""Command registry for the Apollo router (md §4.3).

The :class:`CommandRegistry` holds the deterministic set of
:class:`CommandIntent` manifests the router can resolve against. It is a
thin, immutable-by-default lookup layer so the resolver stays pure and
testable.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from loopos.intent.builtin_manifests import BUILTIN_COMMANDS
from loopos.intent.schema import CommandIntent, TaskType


class CommandRegistry:
    """An ordered, de-duplicated collection of command manifests."""

    def __init__(self, commands: Iterable[CommandIntent] | None = None) -> None:
        self._commands: list[CommandIntent] = []
        self._by_id: dict[str, CommandIntent] = {}
        for command in commands if commands is not None else BUILTIN_COMMANDS:
            self.register(command)

    def register(self, command: CommandIntent) -> None:
        if command.command_id in self._by_id:
            raise ValueError(f"duplicate command_id: {command.command_id}")
        self._commands.append(command)
        self._by_id[command.command_id] = command

    def get(self, command_id: str) -> CommandIntent | None:
        return self._by_id.get(command_id)

    def list(self) -> tuple[CommandIntent, ...]:
        return tuple(self._commands)

    def for_task_type(self, task_type: TaskType) -> tuple[CommandIntent, ...]:
        return tuple(c for c in self._commands if task_type in c.task_types)

    def __iter__(self) -> Iterator[CommandIntent]:
        return iter(self._commands)

    def __len__(self) -> int:
        return len(self._commands)


def default_registry() -> CommandRegistry:
    """Return a registry pre-loaded with the built-in manifests."""

    return CommandRegistry()


__all__ = ["CommandRegistry", "default_registry"]
