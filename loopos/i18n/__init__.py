"""LoopOS internationalisation layer.

v0.4.0 closeout: full CLI localisation across zh / en / ru.

## Public surface

* :func:`t` — translate a dotted key like ``"panel.run.title"`` with
  optional ``{var}`` substitution. Falls back to English when the
  active locale is missing the key, then to the key itself when even
  English is missing (so a missing translation never crashes the CLI).
* :func:`set_locale` / :func:`get_locale` / :func:`active_source` —
  module-level locale state, mutated at startup by :func:`init_locale`.
* :func:`init_locale` — resolve the active locale from the priority
  list (CLI flag → ``LOOPOS_LANG`` env → ``~/.loopos/config.json`` →
  system ``LANG`` → ``LANGUAGE`` → Windows UI language → ``en``).
* :func:`resolve_locale` / :func:`normalize_locale` — pure helpers used
  by :func:`init_locale` and exposed for the ``locale`` subcommand.
* :func:`supported_locales` / :func:`load_catalog` — introspection and
  raw access.

## Translation tables

JSON files live alongside this module:

* :file:`en.json` — canonical (English).
* :file:`zh.json` — Simplified Chinese.
* :file:`ru.json` — Russian (best-effort draft; needs native review).

If a key is missing in the active locale we fall back to English; if
English also lacks the key we return the key verbatim. This makes
i18n strictly additive: shipping a new string in code without
registering it across all locales degrades to English, never to a
crash.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, cast

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FALLBACK_LOCALE = "en"
PACKAGE_DIR = Path(__file__).resolve().parent

# Friendly aliases users may type on the CLI (e.g. ``loopos locale set
# Chinese``). All map to one of the canonical locales below.
_LOCALE_ALIASES: dict[str, str] = {
    "zh": "zh", "zh-cn": "zh", "zh_cn": "zh", "zh-hans": "zh",
    "chinese": "zh", "中文": "zh", "汉语": "zh", "简体中文": "zh",
    "en": "en", "en-us": "en", "en_us": "en", "english": "en",
    "ru": "ru", "ru-ru": "ru", "ru_ru": "ru", "russian": "ru",
    "русский": "ru", "по-русски": "ru",
}

SUPPORTED_LOCALES: tuple[str, ...] = ("zh", "en", "ru")

# Cache of loaded catalogs (locale -> dict). Populated lazily.
_CATALOGS: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Catalog loading
# ---------------------------------------------------------------------------


def _read_catalog_file(locale: str) -> dict[str, Any]:
    path = PACKAGE_DIR / f"{locale}.json"
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            return cast(dict[str, Any], json.loads(handle.read()))
    except (OSError, json.JSONDecodeError):  # pragma: no cover - defensive
        return {}


def load_catalog(locale: str) -> dict[str, Any]:
    """Return the raw translation table for ``locale`` (cached)."""
    if locale not in _CATALOGS:
        _CATALOGS[locale] = _read_catalog_file(locale)
    return _CATALOGS[locale]


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


# ---------------------------------------------------------------------------
# Locale resolution
# ---------------------------------------------------------------------------


def normalize_locale(raw: str) -> str:
    """Normalise a free-form locale string to one of the supported
    locales. Returns the input unchanged if nothing matches so callers
    can decide what to do with unknown locales.
    """
    if not raw:
        return ""
    s = raw.strip().lower().replace("_", "-")
    # Direct hit.
    if s in SUPPORTED_LOCALES:
        return s
    # First segment of BCP-47 style: zh-Hans → zh.
    if "-" in s:
        head = s.split("-", 1)[0]
        if head in SUPPORTED_LOCALES:
            return head
    # Friendly alias.
    return _LOCALE_ALIASES.get(s, s)


def _config_path() -> Path:
    """``~/.loopos/config.json`` (created on demand by ``locale set``)."""
    return Path.home() / ".loopos" / "config.json"


def _read_persisted_locale() -> str:
    path = _config_path()
    if not path.exists():
        return ""
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.loads(handle.read())
    except (OSError, json.JSONDecodeError):
        return ""
    if isinstance(data, dict):
        value = data.get("locale", "")
        if isinstance(value, str):
            return value
    return ""


def _autodetect_locale() -> str:
    """Best-effort detection from the system / shell environment.

    Order on Linux / macOS:
        1. ``LANGUAGE`` (colon-separated, first match wins)
        2. ``LANG`` / ``LC_ALL``

    On Windows we additionally consult the user's UI language via
    ``kernel32.GetUserDefaultUILanguage``. Returns ``""`` when nothing
    matches.
    """
    candidates: list[str] = []
    lang = os.environ.get("LANG", "")
    lc_all = os.environ.get("LC_ALL", "")
    language = os.environ.get("LANGUAGE", "")
    if language:
        candidates.extend(language.split(":"))
    if lc_all:
        candidates.append(lc_all)
    if lang:
        candidates.append(lang)
    if sys.platform == "win32":
        try:
            import ctypes
            lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            # 0x0409 = en-US, 0x0804 = zh-CN, 0x0419 = ru-RU
            lcid_to_locale = {
                0x0409: "en", 0x0809: "en", 0x0c09: "en", 0x1009: "en",
                0x040C: "en", 0x080C: "en",
                0x0404: "zh", 0x0804: "zh", 0x0c04: "zh", 0x1004: "zh",
                0x0419: "ru", 0x0819: "ru",
            }
            mapped = lcid_to_locale.get(lcid)
            if mapped:
                candidates.append(mapped)
        except (OSError, AttributeError):
            pass
    for raw in candidates:
        norm = normalize_locale(raw)
        if norm in SUPPORTED_LOCALES:
            return norm
    return ""


def resolve_locale(*, flag: str | None = None) -> tuple[str, str]:
    """Walk the priority list and return ``(locale, source)``.

    Sources in priority order:
        1. ``--lang`` CLI flag (passed via ``flag=``).
        2. ``LOOPOS_LANG`` environment variable.
        3. ``~/.loopos/config.json`` (persisted by ``loopos locale set``).
        4. System auto-detect (LANG / LANGUAGE / Windows UI lang).
        5. :data:`FALLBACK_LOCALE` (``"en"``).
    """
    candidates: list[tuple[str, str]] = [
        ("--lang flag", flag or ""),
        ("LOOPOS_LANG env", os.environ.get("LOOPOS_LANG", "")),
        ("~/.loopos/config.json", _read_persisted_locale()),
        ("system locale", _autodetect_locale()),
    ]
    for source, raw in candidates:
        norm = normalize_locale(raw) if raw else ""
        if norm in SUPPORTED_LOCALES:
            return norm, source
    return FALLBACK_LOCALE, "fallback"


# ---------------------------------------------------------------------------
# Module-level active state
# ---------------------------------------------------------------------------

_ACTIVE_LOCALE: str = FALLBACK_LOCALE
_ACTIVE_SOURCE: str = "default"


def get_locale() -> str:
    return _ACTIVE_LOCALE


def active_source() -> str:
    return _ACTIVE_SOURCE


def set_locale(locale: str, *, source: str = "manual") -> None:
    """Override the active locale (used by the ``locale`` subcommand
    and tests). Unknown locales are coerced to English.
    """
    global _ACTIVE_LOCALE, _ACTIVE_SOURCE
    norm = normalize_locale(locale)
    _ACTIVE_LOCALE = norm if norm in SUPPORTED_LOCALES else FALLBACK_LOCALE
    _ACTIVE_SOURCE = source


def init_locale(*, flag: str | None = None) -> str:
    """Resolve + apply the locale for this process. Idempotent; safe
    to call from ``app.main`` at startup.
    """
    locale, source = resolve_locale(flag=flag)
    set_locale(locale, source=source)
    return locale


# ---------------------------------------------------------------------------
# Persistence (used by ``loopos locale set``)
# ---------------------------------------------------------------------------


def persist_locale(locale: str) -> Path:
    """Write ``locale`` to ``~/.loopos/config.json``. Returns the
    config path. Creates parent directories as needed.
    """
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, Any] = {}
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as handle:
                parsed = json.loads(handle.read())
                if isinstance(parsed, dict):
                    existing = parsed
        except (OSError, json.JSONDecodeError):
            existing = {}
    existing["locale"] = normalize_locale(locale) or FALLBACK_LOCALE
    with path.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(existing, ensure_ascii=False, indent=2))
        handle.write("\n")
    return path


# ---------------------------------------------------------------------------
# Translation lookup
# ---------------------------------------------------------------------------


def _lookup(catalog: dict[str, Any], dotted_key: str) -> Any:
    """Drill into a nested catalog by dotted key path."""
    node: Any = catalog
    for part in dotted_key.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node


def _format(template: str, kwargs: dict[str, Any]) -> str:
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        # Unknown placeholder — return the raw template so the user
        # can spot the typo.
        return template


def t(key: str, **kwargs: Any) -> str:
    """Translate a dotted key for the active locale.

    Resolution:
        1. Active locale catalog (``loopos.i18n.<locale>.json``).
        2. English catalog fallback.
        3. The key itself, formatted with ``kwargs``.

    ``**kwargs`` substitutes ``{name}`` placeholders in the translated
    string. Unknown placeholders are left as-is rather than raising
    so a half-translated string still prints something useful.
    """
    active = get_locale()
    for locale in (active, FALLBACK_LOCALE):
        catalog = load_catalog(locale)
        value = _lookup(catalog, key)
        if isinstance(value, str):
            return _format(value, kwargs)
    # Nothing matched — emit the key so it's obvious in the output.
    return _format(key, kwargs)


__all__ = [
    "FALLBACK_LOCALE",
    "SUPPORTED_LOCALES",
    "active_source",
    "get_locale",
    "init_locale",
    "load_catalog",
    "normalize_locale",
    "persist_locale",
    "resolve_locale",
    "set_locale",
    "supported_locales",
    "t",
]
