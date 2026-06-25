"""Tests for the v0.4.x i18n YAML schema + 13 new locales.

Validates:
- YAML catalog loading (without PyYAML dependency)
- Recursive parser handles arbitrary nesting
- All 16 supported locales are listed
- Locale aliases include zh-Hant and Traditional Chinese
- Native name and English name come from each catalog's _meta
- Missing keys fall through to English (existing behavior)
- Cross-locale JSON / YAML coexistence (zh/en/ru stay JSON; new
  ones are YAML)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loopos.i18n import (  # noqa: E402
    FALLBACK_LOCALE,
    SUPPORTED_LOCALES,
    _parse_simple_yaml,
    _read_catalog_file,
    load_catalog,
    set_locale,
    supported_locales,
    t,
)


# ---------------------------------------------------------------------------
# Catalog loading
# ---------------------------------------------------------------------------


class TestYAMLCatalogLoading:
    def test_yaml_files_exist(self) -> None:
        for loc in ("de", "es", "fr", "it", "pt", "ja", "ko", "tr", "uk",
                    "hu", "ga", "af", "zh-hant"):
            path = Path(__file__).resolve().parents[1] / "loopos" / "i18n" / f"{loc}.yaml"
            assert path.exists(), f"missing YAML catalog: {path}"

    def test_yaml_load_returns_dict(self) -> None:
        d = _read_catalog_file("de")
        assert isinstance(d, dict)
        assert d["_meta"]["locale"] == "de"
        assert d["_meta"]["english_name"] == "German"

    def test_yaml_nested_dict_loaded(self) -> None:
        d = _read_catalog_file("de")
        # The panel.run.title should be a real nested dict, not a
        # stringified one.
        assert isinstance(d["panel"]["run"], dict)
        assert d["panel"]["run"]["title"] == "Schleife ausführen"

    def test_yaml_quoted_strings_parsed(self) -> None:
        # The note field has spaces + punctuation; it must parse as
        # a single string, not as a list of fragments.
        d = _read_catalog_file("de")
        note = d["_meta"]["note"]
        assert "Best-effort" in note
        assert "draft=false" in note


class TestRecursiveParser:
    def test_two_levels(self) -> None:
        raw = (
            "outer:\n"
            "  inner: value\n"
        )
        d = _parse_simple_yaml(raw)
        assert d == {"outer": {"inner": "value"}}

    def test_three_levels(self) -> None:
        raw = (
            "a:\n"
            "  b:\n"
            "    c: deep\n"
        )
        d = _parse_simple_yaml(raw)
        assert d == {"a": {"b": {"c": "deep"}}}

    def test_mixed_siblings(self) -> None:
        raw = (
            "x: 1\n"
            "y:\n"
            "  z: 2\n"
            "w: 3\n"
        )
        d = _parse_simple_yaml(raw)
        assert d == {"x": 1, "y": {"z": 2}, "w": 3}

    def test_comments_skipped(self) -> None:
        raw = (
            "# top comment\n"
            "x: 1\n"
            "  # indented comment\n"
            "y: 2\n"
        )
        d = _parse_simple_yaml(raw)
        assert d == {"x": 1, "y": 2}


# ---------------------------------------------------------------------------
# Supported locales
# ---------------------------------------------------------------------------


class TestSupportedLocales:
    def test_count(self) -> None:
        # 16 total: zh, en, ru, zh-hant, de, es, fr, it, pt, ja, ko,
        # tr, uk, hu, ga, af
        assert len(SUPPORTED_LOCALES) == 16

    def test_fallback_locale_present(self) -> None:
        assert FALLBACK_LOCALE in SUPPORTED_LOCALES
        assert FALLBACK_LOCALE == "en"

    def test_zh_hant_present(self) -> None:
        # Traditional Chinese, distinct from zh (Simplified).
        assert "zh-hant" in SUPPORTED_LOCALES
        assert "zh" in SUPPORTED_LOCALES
        # Use a set to silence the comparison-overlap mypy error
        # (mypy knows the two literals are different types).
        assert {"zh-hant", "zh"} == {"zh-hant", "zh"}

    def test_supported_locales_have_meta(self) -> None:
        for loc in SUPPORTED_LOCALES:
            entry = load_catalog(loc)
            meta = entry.get("_meta", {}) if isinstance(entry, dict) else {}
            assert "locale" in meta, f"locale {loc} missing _meta.locale"
            assert "name" in meta, f"locale {loc} missing _meta.name"
            assert "english_name" in meta, f"locale {loc} missing _meta.english_name"


class TestSupportedLocalesIntrospection:
    def test_listed_in_native_name(self) -> None:
        entries = supported_locales()
        names = {e["id"]: e["name"] for e in entries}
        assert names["de"] == "Deutsch"
        assert names["ja"] == "日本語"
        assert names["zh-hant"] == "繁體中文"
        assert names["ga"] == "Gaeilge"

    def test_draft_flag_for_new_locales(self) -> None:
        entries = supported_locales()
        drafts = {e["id"]: e.get("draft", "") for e in entries}
        # The 13 new YAML locales are draft=true; legacy zh/en are
        # not draft; ru is documented as a best-effort draft (carries
        # the legacy draft=true marker from v0.4.0).
        for loc in ("de", "es", "fr", "it", "pt", "ja", "ko", "tr",
                    "uk", "hu", "ga", "af", "zh-hant"):
            assert drafts[loc] == "true", f"{loc} should be draft=true"
        for loc in ("zh", "en"):
            assert drafts[loc] != "true", f"{loc} should NOT be draft"


# ---------------------------------------------------------------------------
# Translation behaviour with YAML
# ---------------------------------------------------------------------------


class TestTranslationWithYAML:
    def test_de_translation(self) -> None:
        set_locale("de", source="test")
        assert t("app.name") == "LoopOS"
        assert t("panel.run.title") == "Schleife ausführen"
        assert t("severity.high") == "hoch"

    def test_ja_translation(self) -> None:
        set_locale("ja", source="test")
        assert t("app.tagline") == "プロジェクト訓練ランタイム"
        assert t("panel.run.title") == "ループ実行"

    def test_zh_hant_translation(self) -> None:
        set_locale("zh-hant", source="test")
        assert t("panel.run.title") == "執行迴圈"
        assert t("status.ready_to_deliver") == "可交付"

    def test_ga_translation(self) -> None:
        set_locale("ga", source="test")
        assert t("app.tagline") == "Am rith traenála tionscadail"
        assert t("status.ready_to_deliver") == "réidh_le_seachadadh"

    def test_missing_key_falls_back_to_english(self) -> None:
        set_locale("de", source="test")
        # panel.run.user_goal_label is not in the German YAML stub
        # so it falls through to English.
        assert t("panel.run.user_goal_label") == "User goal"

    def test_missing_key_falls_back_to_key(self) -> None:
        set_locale("en", source="test")
        # A key that doesn't exist anywhere should return verbatim.
        assert t("this.key.does.not.exist") == "this.key.does.not.exist"


# ---------------------------------------------------------------------------
# JSON + YAML coexistence
# ---------------------------------------------------------------------------


class TestJSONYAMLCoexistence:
    def test_legacy_json_still_works(self) -> None:
        for loc in ("zh", "en", "ru"):
            d = load_catalog(loc)
            assert isinstance(d, dict)
            assert d["_meta"]["locale"] == loc

    def test_zh_translation_unchanged(self) -> None:
        set_locale("zh", source="test")
        # Sanity: the legacy Chinese strings are still there.
        assert t("app.name") == "LoopOS"
        assert t("panel.run.title")  # some non-empty string

    def test_yaml_takes_precedence_when_both_exist(self) -> None:
        # If a locale has both .json and .yaml, YAML wins (per
        # the loader order in _read_catalog_file). We don't ship
        # such a conflict today but the loader is documented.
        # Just verify the loader's order via a quick assertion on
        # the function's source path.
        from loopos.i18n import _read_catalog_file as f
        import inspect
        src = inspect.getsource(f)
        assert "yaml" in src
        assert "json" in src
        # YAML is checked first in the source.
        yaml_pos = src.find("yaml_path")
        json_pos = src.find("json_path")
        assert yaml_pos < json_pos, "YAML must be checked before JSON"