"""Tests for the hookify user-editable policy hooks."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loopos.hookify import (  # noqa: E402
    HookifyAction,
    HookifyCondition,
    HookifyEvent,
    HookifyOperator,
    HookifyRule,
    RuleEngine,
    load_rule_from_file,
    load_rules_from_dir,
)


# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------


class TestConditionMatching:
    def test_regex_match(self) -> None:
        c = HookifyCondition("path", HookifyOperator.REGEX_MATCH, r"\.env$")
        assert c.matches({"path": "/x/.env"}) is True
        assert c.matches({"path": "/x/.envx"}) is False
        assert c.matches({"path": "/x/file.txt"}) is False

    def test_contains(self) -> None:
        c = HookifyCondition("path", HookifyOperator.CONTAINS, "secret")
        assert c.matches({"path": "/x/secret.txt"}) is True
        assert c.matches({"path": "/x/public.txt"}) is False

    def test_equals(self) -> None:
        c = HookifyCondition("action", HookifyOperator.EQUALS, "rm -rf /")
        assert c.matches({"action": "rm -rf /"}) is True
        assert c.matches({"action": "rm -rf /tmp"}) is False

    def test_not_contains(self) -> None:
        c = HookifyCondition("transcript", HookifyOperator.NOT_CONTAINS, "pytest")
        assert c.matches({"transcript": "ran ruff"}) is True
        assert c.matches({"transcript": "ran pytest"}) is False

    def test_starts_with(self) -> None:
        c = HookifyCondition("path", HookifyOperator.STARTS_WITH, "/etc")
        assert c.matches({"path": "/etc/passwd"}) is True
        assert c.matches({"path": "/var/log"}) is False

    def test_ends_with(self) -> None:
        c = HookifyCondition("path", HookifyOperator.ENDS_WITH, ".key")
        assert c.matches({"path": "/x/priv.key"}) is True
        assert c.matches({"path": "/x/priv.pem"}) is False

    def test_bad_regex_does_not_raise(self) -> None:
        c = HookifyCondition("path", HookifyOperator.REGEX_MATCH, "[unclosed")
        # A bad regex silently returns False instead of crashing.
        assert c.matches({"path": "/x/.env"}) is False


# ---------------------------------------------------------------------------
# Rule
# ---------------------------------------------------------------------------


class TestRuleMatching:
    def test_disabled_rule_never_matches(self) -> None:
        r = HookifyRule(
            name="x", event=HookifyEvent.ALL, action=HookifyAction.BLOCK,
            message="x", enabled=False,
        )
        assert r.matches(HookifyEvent.PRE_ACTION, {}) is False

    def test_event_filter(self) -> None:
        r = HookifyRule(
            name="x", event=HookifyEvent.PRE_ACTION,
            action=HookifyAction.BLOCK, message="x",
        )
        assert r.matches(HookifyEvent.PRE_ACTION, {}) is True
        assert r.matches(HookifyEvent.POST_ACTION, {}) is False
        assert r.matches(HookifyEvent.ON_LOOP_START, {}) is False

    def test_all_event_matches_everything(self) -> None:
        r = HookifyRule(
            name="x", event=HookifyEvent.ALL,
            action=HookifyAction.BLOCK, message="x",
        )
        for ev in HookifyEvent:
            assert r.matches(ev, {}) is True

    def test_conditions_and_together(self) -> None:
        r = HookifyRule(
            name="x", event=HookifyEvent.ALL,
            action=HookifyAction.BLOCK, message="x",
            conditions=(
                HookifyCondition("a", HookifyOperator.CONTAINS, "1"),
                HookifyCondition("b", HookifyOperator.CONTAINS, "2"),
            ),
        )
        # Both conditions must match.
        assert r.matches(HookifyEvent.PRE_ACTION, {"a": "1", "b": "2"}) is True
        assert r.matches(HookifyEvent.PRE_ACTION, {"a": "1", "b": "x"}) is False
        assert r.matches(HookifyEvent.PRE_ACTION, {"a": "x", "b": "2"}) is False

    def test_empty_conditions_always_match(self) -> None:
        r = HookifyRule(
            name="x", event=HookifyEvent.ALL,
            action=HookifyAction.BLOCK, message="x",
            conditions=(),
        )
        assert r.matches(HookifyEvent.PRE_ACTION, {}) is True


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class TestRuleEngine:
    def test_no_rules_returns_empty(self) -> None:
        engine = RuleEngine()
        assert engine.evaluate(HookifyEvent.PRE_ACTION, {}) == []

    def test_evaluate_returns_matching_only(self) -> None:
        r1 = HookifyRule(
            name="a", event=HookifyEvent.ALL,
            action=HookifyAction.BLOCK, message="a",
            conditions=(HookifyCondition("x", HookifyOperator.CONTAINS, "1"),),
        )
        r2 = HookifyRule(
            name="b", event=HookifyEvent.ALL,
            action=HookifyAction.WARN, message="b",
            conditions=(HookifyCondition("x", HookifyOperator.CONTAINS, "2"),),
        )
        engine = RuleEngine([r1, r2])
        verdicts = engine.evaluate(HookifyEvent.PRE_ACTION, {"x": "1"})
        assert len(verdicts) == 1
        assert verdicts[0].rule.name == "a"

    def test_has_blocking(self) -> None:
        r = HookifyRule(
            name="x", event=HookifyEvent.ALL,
            action=HookifyAction.BLOCK, message="x",
        )
        engine = RuleEngine([r])
        assert engine.has_blocking(HookifyEvent.PRE_ACTION, {}) is True

    def test_has_blocking_with_warn_only(self) -> None:
        r = HookifyRule(
            name="x", event=HookifyEvent.ALL,
            action=HookifyAction.WARN, message="x",
        )
        engine = RuleEngine([r])
        assert engine.has_blocking(HookifyEvent.PRE_ACTION, {}) is False

    def test_warnings_returns_messages(self) -> None:
        r1 = HookifyRule(
            name="a", event=HookifyEvent.ALL,
            action=HookifyAction.WARN, message="warn-1",
        )
        r2 = HookifyRule(
            name="b", event=HookifyEvent.ALL,
            action=HookifyAction.BLOCK, message="block-1",
        )
        engine = RuleEngine([r1, r2])
        warnings = engine.warnings(HookifyEvent.PRE_ACTION, {})
        assert warnings == ["warn-1"]
        blocks = engine.blocking_messages(HookifyEvent.PRE_ACTION, {})
        assert blocks == ["block-1"]


# ---------------------------------------------------------------------------
# File loading
# ---------------------------------------------------------------------------


class TestLoadRuleFromFile:
    def test_basic_rule(self, tmp_path: Path) -> None:
        f = tmp_path / "hookify.block-rm.local.md"
        f.write_text(
            "---\n"
            "name: block-rm\n"
            "event: pre_action\n"
            "action: block\n"
            "enabled: true\n"
            "---\n"
            "\n"
            "Refusing rm operation.\n",
            encoding="utf-8",
        )
        rule = load_rule_from_file(f)
        assert rule is not None
        assert rule.name == "block-rm"
        assert rule.event == HookifyEvent.PRE_ACTION
        assert rule.action == HookifyAction.BLOCK
        assert rule.enabled is True
        assert rule.message == "Refusing rm operation."

    def test_rule_with_conditions(self, tmp_path: Path) -> None:
        f = tmp_path / "hookify.require-tests.local.md"
        f.write_text(
            "---\n"
            "name: require-tests\n"
            "event: on_iteration_end\n"
            "action: block\n"
            "enabled: true\n"
            "conditions:\n"
            "  - field: transcript\n"
            "    operator: not_contains\n"
            "    pattern: pytest\n"
            "---\n"
            "\n"
            "Tests not detected in transcript.\n",
            encoding="utf-8",
        )
        rule = load_rule_from_file(f)
        assert rule is not None
        assert len(rule.conditions) == 1
        assert rule.conditions[0].field == "transcript"
        assert rule.conditions[0].operator == HookifyOperator.NOT_CONTAINS
        assert rule.conditions[0].pattern == "pytest"

    def test_rule_with_multiple_conditions(self, tmp_path: Path) -> None:
        f = tmp_path / "hookify.api-key.local.md"
        f.write_text(
            "---\n"
            "name: api-key-in-ts\n"
            "event: pre_action\n"
            "action: warn\n"
            "conditions:\n"
            "  - field: file_path\n"
            "    operator: regex_match\n"
            "    pattern: \\.tsx?$\n"
            "  - field: new_text\n"
            "    operator: regex_match\n"
            "    pattern: (API_KEY|SECRET)\n"
            "---\n"
            "\n"
            "API key in TS file.\n",
            encoding="utf-8",
        )
        rule = load_rule_from_file(f)
        assert rule is not None
        assert len(rule.conditions) == 2
        assert rule.conditions[1].pattern == "(API_KEY|SECRET)"

    def test_disabled_rule_loaded_with_enabled_false(self, tmp_path: Path) -> None:
        f = tmp_path / "hookify.x.local.md"
        f.write_text(
            "---\n"
            "name: x\n"
            "event: all\n"
            "action: warn\n"
            "enabled: false\n"
            "---\n"
            "\n"
            "msg\n",
            encoding="utf-8",
        )
        rule = load_rule_from_file(f)
        assert rule is not None
        assert rule.enabled is False

    def test_file_without_frontmatter_returns_none(self, tmp_path: Path) -> None:
        f = tmp_path / "hookify.bad.local.md"
        f.write_text("no frontmatter here\n", encoding="utf-8")
        assert load_rule_from_file(f) is None

    def test_file_without_name_returns_none(self, tmp_path: Path) -> None:
        f = tmp_path / "hookify.bad.local.md"
        f.write_text(
            "---\nevent: all\naction: warn\n---\n\nmsg\n",
            encoding="utf-8",
        )
        assert load_rule_from_file(f) is None

    def test_quoted_strings_strip_quotes(self, tmp_path: Path) -> None:
        f = tmp_path / "hookify.x.local.md"
        f.write_text(
            '---\nname: "quoted-name"\nevent: all\naction: warn\n---\n\nmsg\n',
            encoding="utf-8",
        )
        rule = load_rule_from_file(f)
        assert rule is not None
        assert rule.name == "quoted-name"


class TestLoadRulesFromDir:
    def test_empty_dir_returns_empty(self, tmp_path: Path) -> None:
        rules = load_rules_from_dir(tmp_path)
        assert rules == []

    def test_loads_all_matching_files(self, tmp_path: Path) -> None:
        (tmp_path / "hookify.a.local.md").write_text(
            "---\nname: a\nevent: all\naction: warn\n---\n\na\n",
            encoding="utf-8",
        )
        (tmp_path / "hookify.b.local.md").write_text(
            "---\nname: b\nevent: all\naction: block\n---\n\nb\n",
            encoding="utf-8",
        )
        # Non-matching file should be ignored.
        (tmp_path / "README.md").write_text("# ignore me", encoding="utf-8")
        rules = load_rules_from_dir(tmp_path)
        assert len(rules) == 2
        names = {r.name for r in rules}
        assert names == {"a", "b"}

    def test_malformed_files_are_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "hookify.good.local.md").write_text(
            "---\nname: good\nevent: all\naction: warn\n---\n\ng\n",
            encoding="utf-8",
        )
        (tmp_path / "hookify.bad.local.md").write_text(
            "no frontmatter\n", encoding="utf-8",
        )
        rules = load_rules_from_dir(tmp_path)
        names = {r.name for r in rules}
        assert names == {"good"}


# ---------------------------------------------------------------------------
# End-to-end: rule file -> engine -> verdict
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_require_tests_rule_blocks_when_no_pytest(self, tmp_path: Path) -> None:
        f = tmp_path / "hookify.require-tests.local.md"
        f.write_text(
            "---\n"
            "name: require-tests\n"
            "event: on_iteration_end\n"
            "action: block\n"
            "conditions:\n"
            "  - field: transcript\n"
            "    operator: not_contains\n"
            "    pattern: pytest\n"
            "---\n"
            "\n"
            "Iteration must include a test run.\n",
            encoding="utf-8",
        )
        rule = load_rule_from_file(f)
        assert rule is not None
        engine = RuleEngine([rule])
        # No pytest in transcript -> rule fires, blocks.
        assert engine.has_blocking(
            HookifyEvent.ON_ITERATION_END, {"transcript": "ran ruff"},
        ) is True
        # pytest in transcript -> rule does not fire.
        assert engine.has_blocking(
            HookifyEvent.ON_ITERATION_END, {"transcript": "ran pytest"},
        ) is False

    def test_dangerous_rm_rule_blocks_rm(self, tmp_path: Path) -> None:
        f = tmp_path / "hookify.block-rm.local.md"
        f.write_text(
            "---\n"
            "name: block-rm\n"
            "event: pre_action\n"
            "action: block\n"
            "conditions:\n"
            "  - field: command\n"
            "    operator: regex_match\n"
            "    pattern: rm\\s+-rf\n"
            "---\n"
            "\n"
            "Dangerous rm command.\n",
            encoding="utf-8",
        )
        rule = load_rule_from_file(f)
        assert rule is not None
        engine = RuleEngine([rule])
        assert engine.has_blocking(
            HookifyEvent.PRE_ACTION, {"command": "rm -rf /tmp/x"},
        ) is True
        assert engine.has_blocking(
            HookifyEvent.PRE_ACTION, {"command": "ls /tmp/x"},
        ) is False

    def test_sensitive_files_rule_warns(self, tmp_path: Path) -> None:
        f = tmp_path / "hookify.sensitive-files.local.md"
        f.write_text(
            "---\n"
            "name: sensitive-files\n"
            "event: pre_action\n"
            "action: warn\n"
            "conditions:\n"
            "  - field: file_path\n"
            "    operator: contains\n"
            "    pattern: secret\n"
            "---\n"
            "\n"
            "Sensitive file detected.\n",
            encoding="utf-8",
        )
        rule = load_rule_from_file(f)
        assert rule is not None
        engine = RuleEngine([rule])
        # Fires on 'secret' substring
        warnings = engine.warnings(
            HookifyEvent.PRE_ACTION, {"file_path": "/x/secrets.yaml"},
        )
        assert warnings == ["Sensitive file detected."]
        # Does not block (only warn)
        assert engine.has_blocking(
            HookifyEvent.PRE_ACTION, {"file_path": "/x/secrets.yaml"},
        ) is False