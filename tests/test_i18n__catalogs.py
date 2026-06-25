"""Smoke tests for ``loopos.i18n._catalogs`` (paired module file).

This file exists to satisfy the v0.4.0 anti-bloat rule that requires
each new ``loopos/`` module to have a paired ``tests/test_<module>.py``
covering it. The functional coverage of the catalog loader lives in
``tests/test_cli_i18n.py`` and ``tests/test_i18n_yaml.py``; this file
imports the helpers directly to keep the linter / anti-bloat gate
honest about which module owns which surface.
"""

from __future__ import annotations

from pathlib import Path

from loopos.i18n import _catalogs as catalogs
from loopos.i18n import (
    FALLBACK_LOCALE,
    SUPPORTED_LOCALES,
    _clear_catalog_cache,
    _config_path,
    _read_catalog_file,
    load_catalog,
    persist_locale,
    supported_locales,
)


def test_constants_match_module() -> None:
    assert catalogs.FALLBACK_LOCALE == FALLBACK_LOCALE == "en"
    assert catalogs.SUPPORTED_LOCALES is SUPPORTED_LOCALES
    # 3 legacy + 13 YAML draft = 16 total
    assert len(SUPPORTED_LOCALES) == 16


def test_clear_catalog_cache_is_callable() -> None:
    # Loading then clearing should leave the next load_catalog call to
    # re-read from disk; we just need to confirm the entry point is
    # wired.
    load_catalog("en")
    _clear_catalog_cache()
    assert load_catalog("en").get("commands") is not None


def test_read_catalog_file_prefers_yaml() -> None:
    # English is still a JSON file; a YAML locale (de) should round-trip
    # through the loader.
    data = _read_catalog_file("de")
    assert isinstance(data, dict)
    # YAML stubs use a mix of nested and flat dotted keys;
    # the loader must hand back exactly the parsed structure.
    assert data["_meta"]["locale"] == "de"
    assert "panel" in data


def test_persist_locale_and_config_path(
    tmp_path: Path, monkeypatch: object
) -> None:
    monkeypatch.setattr("loopos.i18n._config_path", lambda: tmp_path / "c.json")
    target = tmp_path / "c.json"
    result = persist_locale("zh")
    assert result == target
    assert target.exists()
    import json
    assert json.loads(target.read_text(encoding="utf-8"))["locale"] == "zh"


def test_config_path_returns_user_path() -> None:
    p = _config_path()
    assert p.name == "config.json"
    assert "loopos" in str(p)


def test_supported_locales_shape() -> None:
    rows = supported_locales()
    assert isinstance(rows, list)
    assert rows, "supported_locales() should not be empty"
    first = rows[0]
    for key in ("id", "name", "english_name", "draft"):
        assert key in first, f"missing {key!r} in {first!r}"
