"""CLI surface for ``loopos hookify``.

Subcommands:
    list     — list every rule in <data_dir>/hookify/ (or .loopos/hookify)
    enable   — flip ``enabled: false`` to ``enabled: true`` in a rule file
    disable  — flip ``enabled: true`` to ``enabled: false``
    test     — run a single rule against a synthetic event+input

Examples:
    loopos hookify list
    loopos hookify disable require-tests
    loopos hookify test require-tests \\
        --event on_iteration_end \\
        --data '{"iteration": {"transcript": "ran pytest"}}'
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from loopos.hookify import (
    HookifyEvent,
    HookifyRule,
    RuleEngine,
    load_rule_from_file,
    load_rules_from_dir,
)


def _hookify_dir(data_dir: str | None) -> Path:
    """Return the directory holding ``hookify.*.local.md`` files.

    Defaults to ``<cwd>/.loopos/hookify`` if no data_dir is given.
    """
    if data_dir:
        return Path(data_dir) / "hookify"
    return Path.cwd() / ".loopos" / "hookify"


def hookify_list_command(
    data_dir: str | None = None,
    json_output: bool = True,
) -> int:
    """List every rule in the hookify directory.

    Returns exit code 0. The JSON output is the list form; the
    human output is a table of name / event / action / enabled.
    """
    rules = load_rules_from_dir(_hookify_dir(data_dir))
    if json_output:
        sys.stdout.write(
            json.dumps(
                {
                    "status": "ok",
                    "count": len(rules),
                    "rules": [
                        {
                            "name": r.name,
                            "event": r.event.value,
                            "action": r.action.value,
                            "enabled": r.enabled,
                            "source_path": r.source_path,
                            "condition_count": len(r.conditions),
                        }
                        for r in rules
                    ],
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )
    else:
        sys.stdout.write(f"{len(rules)} hookify rule(s):\n")
        for r in rules:
            flag = "ON " if r.enabled else "off"
            sys.stdout.write(
                f"  [{flag}] {r.name}  event={r.event.value}  "
                f"action={r.action.value}  ({len(r.conditions)} conditions)\n"
                f"      {r.source_path}\n"
            )
    return 0


def hookify_enable_command(
    name: str,
    data_dir: str | None = None,
) -> int:
    """Flip ``enabled: false`` to ``enabled: true`` in a rule's file."""
    return _flip_enabled(name, data_dir, enabled=True)


def hookify_disable_command(
    name: str,
    data_dir: str | None = None,
) -> int:
    """Flip ``enabled: true`` to ``enabled: false`` in a rule's file."""
    return _flip_enabled(name, data_dir, enabled=False)


def _flip_enabled(
    name: str, data_dir: str | None, enabled: bool
) -> int:
    """Find the rule's source file and rewrite the ``enabled`` field.

    The rule is identified by ``name:`` in the YAML frontmatter, not
    by file path, so the user doesn't have to know the file name.
    """
    target_dir = _hookify_dir(data_dir)
    if not target_dir.exists():
        sys.stdout.write(
            json.dumps(
                {"status": "error", "error_code": "no_dir",
                 "message": f"hookify directory not found: {target_dir}"},
            )
            + "\n"
        )
        return 1
    matches: list[Path] = []
    for f in sorted(target_dir.glob("hookify.*.local.md")):
        rule = load_rule_from_file(f)
        if rule is not None and rule.name == name:
            matches.append(f)
    if not matches:
        sys.stdout.write(
            json.dumps(
                {"status": "error", "error_code": "rule_not_found",
                 "message": f"no rule named {name!r} in {target_dir}"},
            )
            + "\n"
        )
        return 1
    if len(matches) > 1:
        sys.stdout.write(
            json.dumps(
                {"status": "error", "error_code": "ambiguous",
                 "message": f"multiple rules named {name!r}: {[str(m) for m in matches]}"},
            )
            + "\n"
        )
        return 1
    path = matches[0]
    text = path.read_text(encoding="utf-8")
    new_text = _rewrite_enabled(text, enabled)
    if new_text == text:
        # already in the desired state
        sys.stdout.write(
            json.dumps(
                {"status": "ok", "name": name, "enabled": enabled, "changed": False,
                 "path": str(path)},
            )
            + "\n"
        )
        return 0
    path.write_text(new_text, encoding="utf-8")
    sys.stdout.write(
        json.dumps(
            {"status": "ok", "name": name, "enabled": enabled, "changed": True,
             "path": str(path)},
        )
        + "\n"
    )
    return 0


def _rewrite_enabled(text: str, enabled: bool) -> str:
    """Replace the ``enabled:`` line in a rule file's frontmatter."""
    target = "true" if enabled else "false"
    lines = text.splitlines()
    found = False
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("enabled:"):
            indent = line[: len(line) - len(stripped)]
            lines[i] = f"{indent}enabled: {target}"
            found = True
            break
    if not found:
        # Insert after the first ``---`` if not present.
        for i, line in enumerate(lines):
            if line.strip() == "---":
                lines.insert(i + 1, f"enabled: {target}")
                break
    return "\n".join(lines) + "\n"


def hookify_test_command(
    name: str,
    event: str = "all",
    data: str | None = None,
    data_dir: str | None = None,
) -> int:
    """Test a single rule against a synthetic event + input.

    ``data`` is a JSON string of the input dict. If not given, an
    empty dict is used.
    """
    try:
        parsed_data: dict[str, Any] = json.loads(data) if data else {}
    except json.JSONDecodeError as e:
        sys.stdout.write(
            json.dumps(
                {"status": "error", "error_code": "bad_data",
                 "message": f"invalid JSON: {e}"},
            )
            + "\n"
        )
        return 1

    target_dir = _hookify_dir(data_dir)
    matches: list[HookifyRule] = []
    for f in sorted(target_dir.glob("hookify.*.local.md")):
        rule = load_rule_from_file(f)
        if rule is not None and rule.name == name:
            matches.append(rule)
    if not matches:
        sys.stdout.write(
            json.dumps(
                {"status": "error", "error_code": "rule_not_found",
                 "message": f"no rule named {name!r} in {target_dir}"},
            )
            + "\n"
        )
        return 1

    rule = matches[0]
    evt = HookifyEvent.parse(event)
    engine = RuleEngine([rule])
    verdicts = engine.evaluate(evt, parsed_data)
    sys.stdout.write(
        json.dumps(
            {
                "status": "ok",
                "rule": name,
                "event": evt.value,
                "input": parsed_data,
                "matched": bool(verdicts),
                "would_block": any(v.should_block for v in verdicts),
                "would_warn": any(v.should_warn for v in verdicts),
                "message": verdicts[0].rule.message if verdicts else None,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    return 0
