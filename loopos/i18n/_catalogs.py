"""Catalog loading + locale registry for the i18n layer.

Kept separate from ``__init__.py`` so the public API module stays
under 300 lines per the v0.4.0 closeout anti-bloat rule.

The loader prefers YAML (because YAML is easier to maintain by
hand) and falls back to JSON for the legacy zh / en / ru catalogs.
Missing catalogs return an empty dict; the lookup layer falls
through to English.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from loopos.i18n._yaml import parse_simple_yaml


FALLBACK_LOCALE = "en"
PACKAGE_DIR = Path(__file__).resolve().parent

# Friendly aliases users may type on the CLI (e.g. ``loopos locale set
# Chinese``). All map to one of the canonical locales below.
_LOCALE_ALIASES: dict[str, str] = {
    # zh + variants
    "zh": "zh", "zh-cn": "zh", "zh_cn": "zh", "zh-hans": "zh",
    "chinese": "zh", "中文": "zh", "汉语": "zh", "简体中文": "zh",
    # zh-Hant (Traditional Chinese)
    "zh-hant": "zh-hant", "zh_hant": "zh-hant", "zh-tw": "zh-hant",
    "zh_tw": "zh-hant", "zh-hk": "zh-hant", "zh_hk": "zh-hant",
    "繁體中文": "zh-hant", "繁體": "zh-hant",
    # en
    "en": "en", "en-us": "en", "en_us": "en", "english": "en",
    # ru
    "ru": "ru", "ru-ru": "ru", "ru_ru": "ru", "russian": "ru",
    "русский": "ru", "по-русски": "ru",
    # de
    "de": "de", "de-de": "de", "de_de": "de", "german": "de",
    "deutsch": "de",
    # es
    "es": "es", "es-es": "es", "es_es": "es", "spanish": "es",
    "español": "es", "castellano": "es",
    # fr
    "fr": "fr", "fr-fr": "fr", "fr_fr": "fr", "french": "fr",
    "français": "fr", "francais": "fr",
    # it
    "it": "it", "it-it": "it", "it_it": "it", "italian": "it",
    "italiano": "it",
    # pt
    "pt": "pt", "pt-br": "pt", "pt_br": "pt", "pt-pt": "pt",
    "portuguese": "pt", "português": "pt", "portugues": "pt",
    # ja
    "ja": "ja", "ja-jp": "ja", "ja_jp": "ja", "japanese": "ja",
    "日本語": "ja",
    # ko
    "ko": "ko", "ko-kr": "ko", "ko_kr": "ko", "korean": "ko",
    "한국어": "ko",
    # tr
    "tr": "tr", "tr-tr": "tr", "tr_tr": "tr", "turkish": "tr",
    "türkçe": "tr", "turkce": "tr",
    # uk
    "uk": "uk", "uk-ua": "uk", "uk_ua": "uk", "ukrainian": "uk",
    "українська": "uk", "ukrainska": "uk",
    # hu
    "hu": "hu", "hu-hu": "hu", "hu_hu": "hu", "hungarian": "hu",
    "magyar": "hu",
    # ga
    "ga": "ga", "ga-ie": "ga", "ga_ie": "ga", "irish": "ga",
    "gaeilge": "ga",
    # af
    "af": "af", "af-za": "af", "af_za": "af", "afrikaans": "af",
}

# v0.4.x: 16 locales total. The 13 new ones are draft YAML stubs
# pending native-speaker review. English is the canonical fallback.
SUPPORTED_LOCALES: tuple[str, ...] = (
    "zh", "en", "ru", "zh-hant",
    "de", "es", "fr", "it", "pt",
    "ja", "ko", "tr", "uk", "hu", "ga", "af",
)

# Cache of loaded catalogs (locale -> dict). Populated lazily.
_CATALOGS: dict[str, dict[str, Any]] = {}


def _read_catalog_file(locale: str) -> dict[str, Any]:
    """Load the catalog for ``locale`` from disk.

    Prefers YAML (newer, hand-editable) and falls back to JSON
    (legacy, used by zh / en / ru). The set of keys in any catalog
    is a subset of the English catalog; missing keys fall through
    to English at lookup time.
    """
    # Try YAML first.
    yaml_path = PACKAGE_DIR / f"{locale}.yaml"
    if yaml_path.exists():
        try:
            text = yaml_path.read_text(encoding="utf-8")
            return parse_simple_yaml(text)
        except Exception:  # pragma: no cover - defensive
            return {}
    # Fall back to JSON (legacy catalogs).
    json_path = PACKAGE_DIR / f"{locale}.json"
    if json_path.exists():
        try:
            with json_path.open("r", encoding="utf-8") as handle:
                return cast(dict[str, Any], json.loads(handle.read()))
        except (OSError, json.JSONDecodeError):  # pragma: no cover - defensive
            return {}
    return {}


def load_catalog(locale: str) -> dict[str, Any]:
    """Return the raw translation table for ``locale`` (cached)."""
    if locale not in _CATALOGS:
        _CATALOGS[locale] = _read_catalog_file(locale)
    return _CATALOGS[locale]


def _config_path() -> Path:
    """Return the per-user config file path: ``~/.loopos/config.json``.

    Public to the rest of the i18n / CLI surface but kept private
    to outside callers (single underscore).
    """
    return Path.home() / ".loopos" / "config.json"


def persist_locale(locale: str) -> Path | None:
    """Write the active locale to ``~/.loopos/config.json``.

    The file is created if it does not exist; the rest of its
    contents are preserved. A failed write is silently swallowed
    (the locale will simply revert to env or system on the next
    startup) so a permission error never blocks the CLI.

    The input is normalized via :func:`normalize_locale` first
    (e.g. ``"Chinese"`` -> ``"zh"``) so the persisted value is
    always a canonical id, not a friendly alias.

    Returns the config path on success, ``None`` on failure.

    Implementation note: the config path is resolved through the
    public ``loopos.i18n`` namespace at call time, so tests can
    monkeypatch ``loopos.i18n._config_path`` to redirect to a
    tmp dir.
    """
    import loopos.i18n as _i18n_public
    path = _i18n_public._config_path()
    normalized = _i18n_public.normalize_locale(locale)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        existing: dict[str, Any] = {}
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as handle:
                    data = json.loads(handle.read())
                if isinstance(data, dict):
                    existing = data
            except (OSError, json.JSONDecodeError):
                existing = {}
        existing["locale"] = normalized
        with path.open("w", encoding="utf-8") as handle:
            json.dump(existing, handle, indent=2, ensure_ascii=False)
    except OSError:
        # Permission errors etc. are non-fatal; the active locale
        # still works for this session.
        return None
    return path


def supported_locales() -> list[dict[str, str]]:
    """Return ``[{id, name, english_name, draft}, ...]`` for ``loopos
    locale list`` and similar introspection."""
    out: list[dict[str, str]] = []
    for loc in SUPPORTED_LOCALES:
        catalog = load_catalog(loc)
        meta = catalog.get("_meta", {}) if isinstance(catalog, dict) else {}
        out.append({
            "id": loc,
            "name": str(meta.get("name", loc)),
            "english_name": str(meta.get("english_name", loc)),
            "draft": "true" if meta.get("draft") else "",
        })
    return out


__all__ = [
    "FALLBACK_LOCALE",
    "PACKAGE_DIR",
    "SUPPORTED_LOCALES",
    "load_catalog",
    "supported_locales",
]


# Allow internal callers (and tests) to clear the cache when they
# mutate on-disk catalogs at runtime.
def _clear_catalog_cache() -> None:
    """Clear the catalog cache (test helper)."""
    _CATALOGS.clear()