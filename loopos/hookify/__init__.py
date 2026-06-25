"""Hookify — user-editable policy hooks for LoopOS.

Inspired by claude-code/hookify (a 1,200-line plugin with a similar
"markdown rule files in .local.md" pattern). LoopOS's hookify is the
v0.4.x minimal-surface port:

* Users drop ``.loopos/hookify.<name>.local.md`` files into their
  project root. Each file is a YAML frontmatter + markdown body
  that defines a rule.
* The rule is loaded on every action and matched against the
  hook's input data (a dict of strings).
* The rule's ``action`` is either ``warn`` (just show a message)
  or ``block`` (refuse the action).
* The ``loopos hookify`` CLI lists, enables, disables, and tests rules.

Hookify is the user-facing policy layer. The ``ActionBoundary``
(de712158) is the developer-facing structural layer. They compose:
Hookify rules run BEFORE the boundary falls through to the
deterministic allow-list, so a user rule can block something the
boundary would otherwise allow (e.g. block a specific repo path
the boundary doesn't know about).

Events covered in v0.4.x (matching the most important LoopOS
phases; later events come with follow-ups):

* ``pre_action``      — before any action runs (file_write, shell, etc.)
* ``post_action``     — after a successful action (audit-rail hook)
* ``on_iteration_end`` — at the end of every loop iteration
* ``on_loop_start``   — at the start of a loop run
* ``all``             — fires on every event

Operators:

* ``regex_match``   — pattern must match (most common)
* ``contains``      — string must contain pattern
* ``equals``        — exact string match
* ``not_contains``  — string must NOT contain pattern
* ``starts_with``   — string starts with pattern
* ``ends_with``     — string ends with pattern
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable


__all__ = [
    "HookifyEvent",
    "HookifyAction",
    "HookifyOperator",
    "HookifyCondition",
    "HookifyRule",
    "HookifyVerdict",
    "load_rule_from_file",
    "load_rules_from_dir",
    "RuleEngine",
]


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------


class HookifyEvent(str, Enum):
    """The set of events hookify rules can attach to."""

    PRE_ACTION = "pre_action"
    POST_ACTION = "post_action"
    ON_ITERATION_END = "on_iteration_end"
    ON_LOOP_START = "on_loop_start"
    ALL = "all"

    @classmethod
    def parse(cls, value: str) -> "HookifyEvent":
        try:
            return cls(value)
        except ValueError:
            return cls.ALL


class HookifyAction(str, Enum):
    WARN = "warn"
    BLOCK = "block"


class HookifyOperator(str, Enum):
    REGEX_MATCH = "regex_match"
    CONTAINS = "contains"
    EQUALS = "equals"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"

    @classmethod
    def parse(cls, value: str) -> "HookifyOperator":
        try:
            return cls(value)
        except ValueError:
            return cls.REGEX_MATCH


@dataclass(frozen=True)
class HookifyCondition:
    """A single ``field <operator> pattern`` clause."""

    field: str
    operator: HookifyOperator
    pattern: str

    def matches(self, input_data: dict[str, Any]) -> bool:
        """Return True if this condition matches the input data."""
        value = str(input_data.get(self.field, ""))
        return self._evaluate(value)

    def _evaluate(self, value: str) -> bool:
        if self.operator is HookifyOperator.REGEX_MATCH:
            return _safe_regex_search(self.pattern, value)
        if self.operator is HookifyOperator.CONTAINS:
            return self.pattern in value
        if self.operator is HookifyOperator.EQUALS:
            return value == self.pattern
        if self.operator is HookifyOperator.NOT_CONTAINS:
            return self.pattern not in value
        if self.operator is HookifyOperator.STARTS_WITH:
            return value.startswith(self.pattern)
        if self.operator is HookifyOperator.ENDS_WITH:
            return value.endswith(self.pattern)
        return False  # pragma: no cover


@dataclass(frozen=True)
class HookifyRule:
    """A single user rule.

    ``name`` and ``event`` are required. ``enabled=False`` skips the
    rule without deleting the file. ``conditions`` AND together
    (all must match). An empty ``conditions`` list always matches.
    """

    name: str
    event: HookifyEvent
    action: HookifyAction
    message: str
    source_path: str | None = None
    enabled: bool = True
    conditions: tuple[HookifyCondition, ...] = ()

    def matches(self, event: HookifyEvent, input_data: dict[str, Any]) -> bool:
        """Return True if this rule fires for ``event`` + ``input_data``."""
        if not self.enabled:
            return False
        if self.event is not HookifyEvent.ALL and self.event is not event:
            return False
        if not self.conditions:
            return True
        return all(c.matches(input_data) for c in self.conditions)


@dataclass(frozen=True)
class HookifyVerdict:
    """The result of evaluating a single rule."""

    rule: HookifyRule
    matched: bool

    @property
    def should_block(self) -> bool:
        return self.matched and self.rule.action is HookifyAction.BLOCK

    @property
    def should_warn(self) -> bool:
        return self.matched and self.rule.action is HookifyAction.WARN


# ---------------------------------------------------------------------------
# Rule engine
# ---------------------------------------------------------------------------


@lru_cache(maxsize=128)
def _safe_regex_search(pattern: str, value: str) -> bool:
    """Cache compiled regexes; never raise on a bad pattern.

    A bad pattern silently returns ``False`` (the rule does not
    match) rather than crashing the loop. Users can diagnose
    patterns via ``loopos hookify test``.
    """
    try:
        return re.search(pattern, value) is not None
    except re.error:
        return False


class RuleEngine:
    """Evaluate a collection of rules against a single event."""

    def __init__(self, rules: Iterable[HookifyRule] = ()) -> None:
        self._rules: list[HookifyRule] = list(rules)

    def add(self, rule: HookifyRule) -> None:
        self._rules.append(rule)

    def extend(self, rules: Iterable[HookifyRule]) -> None:
        self._rules.extend(rules)

    def evaluate(
        self, event: HookifyEvent, input_data: dict[str, Any]
    ) -> list[HookifyVerdict]:
        """Return one ``HookifyVerdict`` per matching rule."""
        return [
            HookifyVerdict(rule=r, matched=True)
            for r in self._rules
            if r.matches(event, input_data)
        ]

    def has_blocking(self, event: HookifyEvent, input_data: dict[str, Any]) -> bool:
        return any(v.should_block for v in self.evaluate(event, input_data))

    def warnings(
        self, event: HookifyEvent, input_data: dict[str, Any]
    ) -> list[str]:
        return [v.rule.message for v in self.evaluate(event, input_data) if v.should_warn]

    def blocking_messages(
        self, event: HookifyEvent, input_data: dict[str, Any]
    ) -> list[str]:
        return [v.rule.message for v in self.evaluate(event, input_data) if v.should_block]


# ---------------------------------------------------------------------------
# File loading: .local.md with YAML frontmatter
# ---------------------------------------------------------------------------


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse a markdown file with YAML frontmatter.

    Returns (frontmatter_dict, body_text). The frontmatter is the
    YAML block between the first pair of ``---`` lines. We use a
    minimal hand-rolled parser instead of pulling in PyYAML because
    hookify's frontmatter is small, flat, and uses only string /
    list / bool types — PyYAML would be 700KB of dependency for
    a 50-line parser.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    # Find the closing ``---`` (must be at column 0, no leading spaces).
    end = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end == -1:
        return {}, text
    raw = "\n".join(lines[1:end])
    body = "\n".join(lines[end + 1:]).strip()
    parsed = _parse_simple_yaml(raw)
    return parsed, body


def _parse_simple_yaml(raw: str) -> dict[str, Any]:
    """Parse a small flat YAML subset.

    Supports:
        key: value
        key: "quoted value"
        key:
          - item1
          - item2
        key:
          - field: foo
            operator: contains
            pattern: bar

    No nested lists of lists, no anchors, no flow style. This is
    enough for hookify's frontmatter, which is a small list of
    condition dicts.
    """
    out: dict[str, Any] = {}
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        # Top-level key (no leading whitespace).
        if not line.startswith((" ", "\t")) and ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            if not value:
                # Sub-block follows. Walk the indented block.
                sub: list[Any] | dict[str, Any] = []
                j = i + 1
                sub_lines: list[str] = []
                while j < len(lines) and (
                    lines[j].startswith((" ", "\t")) or not lines[j].strip()
                ):
                    if lines[j].strip():
                        sub_lines.append(lines[j])
                    j += 1
                if sub_lines:
                    # Detect: list of scalars vs list of dicts vs dict.
                    first = sub_lines[0].lstrip()
                    if first.startswith("- "):
                        sub = _parse_list_of_dicts(sub_lines)
                    elif all(":" in s for s in sub_lines if s.strip()):
                        sub = {}
                        for sl in sub_lines:
                            sl_stripped = sl.strip()
                            if ":" in sl_stripped:
                                k, _, v = sl_stripped.partition(":")
                                sub[k.strip()] = _coerce_scalar(v.strip())  # type: ignore[index]
                    else:
                        sub = [
                            _coerce_scalar(s.lstrip()[2:].strip())
                            for s in sub_lines
                            if s.strip()
                        ]
                out[key] = sub
                i = j
                continue
            out[key] = _coerce_scalar(value)
        i += 1
    return out


def _parse_list_of_dicts(lines: list[str]) -> list[dict[str, Any]]:
    """Parse a YAML list-of-dicts.

    Each item starts with ``- `` (or ``-\n`` followed by indented
    continuation lines). Keys are collected until the next ``-`` or
    end of input. Continuation lines must be indented further than
    the ``-`` column.
    """
    items: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    current_indent: int | None = None
    for raw in lines:
        if not raw.strip():
            continue
        # Find the leading indent.
        stripped_leading = raw.lstrip()
        indent = len(raw) - len(stripped_leading)
        body = stripped_leading
        if body.startswith("- "):
            # Start a new item.
            if current:
                items.append(current)
                current = {}
            # The remainder after ``- `` may be ``key: value`` inline.
            remainder = body[2:].strip()
            current_indent = indent
            if ":" in remainder and not remainder.startswith('"'):
                k, _, v = remainder.partition(":")
                current[k.strip()] = _coerce_scalar(v.strip())
            elif remainder:
                # Treat as an inline value (rare for hookify).
                pass
        else:
            # Continuation line: must be indented past the ``-``.
            if current_indent is None or indent <= current_indent:
                # Malformed; skip.
                continue
            if ":" in body:
                k, _, v = body.partition(":")
                current[k.strip()] = _coerce_scalar(v.strip())
    if current:
        items.append(current)
    return items


def _coerce_scalar(value: str) -> Any:
    """Coerce a YAML scalar string to int / float / bool / str."""
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    if value.lower() in {"true", "yes", "on"}:
        return True
    if value.lower() in {"false", "no", "off"}:
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def load_rule_from_file(path: str | Path) -> HookifyRule | None:
    """Load a single rule from a ``.local.md`` file.

    Returns ``None`` if the file is malformed (logged but not raised,
    so a single bad rule doesn't break the whole engine).
    """
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return None
    frontmatter, body = _parse_frontmatter(text)
    if not frontmatter:
        return None
    if not frontmatter.get("name"):
        return None
    raw_conditions = frontmatter.get("conditions") or []
    if not isinstance(raw_conditions, list):
        return None
    conditions: list[HookifyCondition] = []
    for c in raw_conditions:
        if not isinstance(c, dict):
            return None
        try:
            conditions.append(
                HookifyCondition(
                    field=str(c.get("field", "")),
                    operator=HookifyOperator.parse(str(c.get("operator", "regex_match"))),
                    pattern=str(c.get("pattern", "")),
                )
            )
        except (ValueError, TypeError):
            return None
    return HookifyRule(
        name=str(frontmatter["name"]),
        event=HookifyEvent.parse(str(frontmatter.get("event", "all"))),
        action=HookifyAction(str(frontmatter.get("action", "warn"))),
        message=body or str(frontmatter.get("name", "")),
        source_path=str(p),
        enabled=bool(frontmatter.get("enabled", True)),
        conditions=tuple(conditions),
    )


def load_rules_from_dir(
    directory: str | Path | None = None,
) -> list[HookifyRule]:
    """Load every ``hookify.*.local.md`` from a directory.

    Defaults to ``<cwd>/.loopos`` if no directory is given. The
    directory is created if it does not exist; an empty list is
    returned in that case.
    """
    if directory is None:
        directory = Path.cwd() / ".loopos"
    p = Path(directory)
    p.mkdir(parents=True, exist_ok=True)
    out: list[HookifyRule] = []
    for f in sorted(p.glob("hookify.*.local.md")):
        rule = load_rule_from_file(f)
        if rule is not None:
            out.append(rule)
    return out