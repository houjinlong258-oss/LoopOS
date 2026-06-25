from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator, cast

import pytest

from loopos.cli.commands.locale import locale_command
from loopos.i18n import (
    FALLBACK_LOCALE,
    SUPPORTED_LOCALES,
    init_locale,
    load_catalog,
    normalize_locale,
    resolve_locale,
    set_locale,
    supported_locales,
    t,
)


ENV_VARS = ("LOOPOS_LANG", "LOOPOS_LANG_PRE", "LANG", "LC_ALL", "LANGUAGE")


@pytest.fixture(autouse=True)
def reset_locale_state(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    set_locale("en", source="test")
    yield
    set_locale("en", source="test")


def catalog_text(locale: str, dotted_key: str) -> str:
    node: Any = load_catalog(locale)
    for part in dotted_key.split("."):
        assert isinstance(node, dict)
        node = node[part]
    assert isinstance(node, str)
    return node


class TestNormalizeLocale:
    def test_canonical_locales_passthrough(self) -> None:
        for loc in SUPPORTED_LOCALES:
            assert normalize_locale(loc) == loc

    def test_locale_with_region_collapses(self) -> None:
        assert normalize_locale("zh_CN") == "zh"
        assert normalize_locale("zh-Hans") == "zh"
        assert normalize_locale("en_US") == "en"
        assert normalize_locale("ru_RU") == "ru"

    def test_friendly_aliases(self) -> None:
        assert normalize_locale("Chinese") == "zh"
        assert normalize_locale("English") == "en"
        assert normalize_locale("Russian") == "ru"

    def test_unknown_returns_fallback(self) -> None:
        # v0.4.x: ja is now a real locale; the only unknown is "xx-YY"
        # and "" (empty).
        assert normalize_locale("ja") == "ja"  # real locale, kept
        assert normalize_locale("xx-YY") == "en"  # unknown -> fallback
        assert normalize_locale("") == "en"  # empty -> fallback


class TestTranslation:
    def test_lookup_uses_active_locale_catalog(self) -> None:
        set_locale("zh", source="test")
        assert t("panel.run.title") == catalog_text("zh", "panel.run.title")
        assert t("panel.run.title") != catalog_text("en", "panel.run.title")

    def test_english_fallback_when_active_key_is_missing(self) -> None:
        # v0.4.x: catalog cache lives in ``_catalogs``; we clear it
        # so the next ``load_catalog`` call rebuilds from disk.
        from loopos.i18n import _clear_catalog_cache
        from loopos.i18n._catalogs import _CATALOGS

        original = _CATALOGS.get("zh")
        _CATALOGS["zh"] = {"_meta": {"locale": "zh"}}
        try:
            set_locale("zh", source="test")
            assert t("panel.run.title") == catalog_text("en", "panel.run.title")
        finally:
            if original is None:
                _CATALOGS.pop("zh", None)
            else:
                _CATALOGS["zh"] = original
            _clear_catalog_cache()

    def test_key_verbatim_when_key_is_missing_everywhere(self) -> None:
        set_locale("zh", source="test")
        missing_key = "nonexistent.deeply.nested.key"
        assert t(missing_key) == missing_key

    def test_placeholder_substitution(self) -> None:
        out = t("messages.active_locale", locale="zh", source="test")
        assert "zh" in out
        assert "test" in out
        assert "{locale}" not in out
        assert "{source}" not in out

    def test_unknown_placeholder_leaves_template_readable(self) -> None:
        out = t("messages.active_locale", unknown_var="unused")
        assert "Active locale" in out
        assert "{locale}" in out

    def test_non_english_catalogs_have_severity_values(self) -> None:
        assert t("severity.high") == "high"
        for locale in ("zh", "ru"):
            set_locale(locale, source="test")
            assert t("severity.high")
            assert t("severity.high") != "severity.high"


class TestCatalog:
    def test_en_catalog_has_meta(self) -> None:
        en = load_catalog("en")
        assert en["_meta"]["locale"] == "en"
        assert en["_meta"]["english_name"] == "English"

    def test_supported_locales_lists_all(self) -> None:
        out = supported_locales()
        assert {item["id"] for item in out} == set(SUPPORTED_LOCALES)
        assert next(item for item in out if item["id"] == "ru")["draft"] == "true"
        assert next(item for item in out if item["id"] == "en")["draft"] == ""

    def test_unknown_locale_returns_empty_catalog(self) -> None:
        # v0.4.x: ja is now a real locale (YAML draft). Pick a
        # locale that does NOT exist on disk.
        assert load_catalog("xx-nonexistent") == {}


class TestResolveLocale:
    def test_flag_wins_over_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("loopos.i18n._read_persisted_locale", lambda: "en")
        monkeypatch.setenv("LOOPOS_LANG", "ru")
        locale, source = resolve_locale(flag="zh")
        assert locale == "zh"
        assert "flag" in source

    def test_env_wins_over_persisted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("loopos.i18n._read_persisted_locale", lambda: "en")
        monkeypatch.setenv("LOOPOS_LANG", "zh")
        locale, source = resolve_locale(flag=None)
        assert locale == "zh"
        assert "env" in source

    def test_persisted_wins_over_system(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("loopos.i18n._read_persisted_locale", lambda: "zh")
        monkeypatch.setattr("loopos.i18n._autodetect_locale", lambda: "ru")
        locale, source = resolve_locale(flag=None)
        assert locale == "zh"
        assert "persisted" in source

    def test_fallback_when_nothing_matches(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("loopos.i18n._read_persisted_locale", lambda: "")
        monkeypatch.setattr("loopos.i18n._autodetect_locale", lambda: "")
        locale, source = resolve_locale(flag=None)
        assert locale == FALLBACK_LOCALE
        assert source == "fallback"


class TestInitLocale:
    def test_init_sets_module_state(self) -> None:
        assert init_locale(flag="zh") == "zh"
        assert t("panel.run.title") == catalog_text("zh", "panel.run.title")

    def test_set_locale_unknown_coerces_to_english(self) -> None:
        set_locale("xx", source="test")
        assert t("panel.run.title") == catalog_text("en", "panel.run.title")


class TestPersistence:
    def test_persist_locale_writes_config(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake = tmp_path / "config.json"
        monkeypatch.setattr("loopos.i18n._config_path", lambda: fake)

        from loopos.i18n import persist_locale

        path = persist_locale("zh")
        assert path == fake
        assert json.loads(fake.read_text(encoding="utf-8"))["locale"] == "zh"

    def test_persist_locale_normalises_alias(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake = tmp_path / "config.json"
        monkeypatch.setattr("loopos.i18n._config_path", lambda: fake)

        from loopos.i18n import persist_locale

        persist_locale("Chinese")
        assert json.loads(fake.read_text(encoding="utf-8"))["locale"] == "zh"

    def test_persist_locale_preserves_existing_keys(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake = tmp_path / "config.json"
        fake.write_text(json.dumps({"locale": "en", "extra": "kept"}), encoding="utf-8")
        monkeypatch.setattr("loopos.i18n._config_path", lambda: fake)

        from loopos.i18n import persist_locale

        persist_locale("ru")
        data = json.loads(fake.read_text(encoding="utf-8"))
        assert data["locale"] == "ru"
        assert data["extra"] == "kept"


class TestLocaleCommand:
    def test_list_json_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert locale_command("list", json_output=True) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["active"] == "en"
        assert {item["id"] for item in payload["locales"]} == set(SUPPORTED_LOCALES)

    def test_list_text_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert locale_command("list") == 0
        stdout = capsys.readouterr().out
        for locale in SUPPORTED_LOCALES:
            assert locale in stdout

    def test_show_json_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        set_locale("zh", source="test")
        assert locale_command("show", json_output=True) == 0
        payload = cast(dict[str, object], json.loads(capsys.readouterr().out))
        assert payload["active"] == "zh"
        assert payload["source"] == "test"
        assert "config_path" in payload

    def test_set_persists_to_config(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        fake = tmp_path / "config.json"
        monkeypatch.setattr("loopos.i18n._config_path", lambda: fake)

        assert locale_command("set", "ru") == 0
        assert json.loads(fake.read_text(encoding="utf-8"))["locale"] == "ru"
        assert "ru" in capsys.readouterr().out

    def test_set_accepts_friendly_alias(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fake = tmp_path / "config.json"
        monkeypatch.setattr("loopos.i18n._config_path", lambda: fake)

        assert locale_command("set", "Chinese") == 0
        assert json.loads(fake.read_text(encoding="utf-8"))["locale"] == "zh"

    def test_set_invalid_locale_returns_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        fake = tmp_path / "config.json"
        monkeypatch.setattr("loopos.i18n._config_path", lambda: fake)

        assert locale_command("set", "klingon") == 2
        assert "klingon" in capsys.readouterr().err
        assert not fake.exists()

    def test_set_without_arg_returns_error(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert locale_command("set", None) == 2
        assert "requires" in capsys.readouterr().err.lower()

    def test_unknown_action_returns_error(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert locale_command("explode") == 2
        assert "unknown" in capsys.readouterr().err.lower()

    def test_set_then_show_round_trip(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        fake = tmp_path / "config.json"
        monkeypatch.setattr("loopos.i18n._config_path", lambda: fake)

        assert locale_command("set", "zh") == 0
        capsys.readouterr()
        assert locale_command("show", json_output=True) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["active"] == "zh"
