"""YAML parser for i18n catalogs (no PyYAML dependency).

Supports the small flat-ish shape used by LoopOS catalogs:
- flat key: value pairs (strings, ints, floats, bools)
- arbitrarily-nested dicts via indent
- one level of list-of-scalars
- ``#`` comments at the start of a line

Anything more exotic (anchors, flow style, multi-doc) is not
supported. We use this parser instead of PyYAML to avoid the
~700KB dependency for the i18n module.
"""

from __future__ import annotations

from typing import Any


def parse_simple_yaml(raw: str) -> dict[str, Any]:
    """Parse the YAML subset used by i18n catalogs.

    Recursive parser: handles arbitrarily-deep nested dicts. Lists
    are rendered as ``- item`` blocks. Comments start with ``#``;
    quoted strings drop their quotes.
    """
    lines = raw.splitlines()
    return _parse_yaml_block(lines, 0, 0)[0]


def _parse_yaml_block(
    lines: list[str], start: int, base_indent: int,
) -> tuple[dict[str, Any], int]:
    """Parse a YAML block starting at ``start`` with ``base_indent``.

    Returns ``(parsed_dict, next_line_index)``. Recurses into
    nested blocks when a value's line is empty (the value is on
    subsequent lines at deeper indent).
    """
    out: dict[str, Any] = {}
    i = start
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        # If the line's indent is shallower than the block's
        # base, we've exited this block — let the caller handle it.
        indent = len(line) - len(line.lstrip())
        if indent < base_indent:
            return out, i
        if indent > base_indent:
            # Unexpected deep indent at start of a block: skip.
            i += 1
            continue
        if ":" not in stripped:
            i += 1
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()
        if value:
            out[key] = _coerce_scalar(value)
            i += 1
            continue
        # Empty value: recurse into the nested block.
        sub, i = _parse_yaml_block(lines, i + 1, base_indent + 2)
        out[key] = sub
    return out, i


def _parse_list_of_strings(lines: list[str]) -> list[str]:
    """Parse a YAML list of scalars: each line is ``- value``."""
    out: list[str] = []
    for raw in lines:
        body = raw.lstrip()
        if body.startswith("- "):
            out.append(_coerce_scalar(body[2:].strip()))  # type: ignore[arg-type]
        elif body == "-":
            out.append("")
    return out


def _coerce_scalar(value: Any) -> Any:
    """Coerce a YAML scalar string to bool / int / float / str."""
    if isinstance(value, str):
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            return value[1:-1]
        if value.lower() in {"true", "yes", "on"}:
            return True
        if value.lower() in {"false", "no", "off"}:
            return False
    if isinstance(value, str):
        try:
            return int(value)
        except (ValueError, TypeError):
            pass
        try:
            return float(value)
        except (ValueError, TypeError):
            pass
    return value


__all__ = ["parse_simple_yaml"]