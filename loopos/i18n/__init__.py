"""LoopOS internationalisation layer.

v0.4.0 closeout: full CLI localisation across zh / en / ru.
v0.4.x: added 13 more locales via YAML stub catalogs
(af, de, es, fr, ga, hu, it, ja, ko, pt, tr, uk, zh-hant) — all
flagged ``draft=true`` pending native-speaker review.

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

Catalogs live alongside this module in either JSON or YAML format.
The loader prefers YAML (because YAML is easier to maintain by
hand) and falls back to JSON for the existing zh / en / ru
catalogs.

* :file:`en.json` — canonical (English, JSON for backward compat).
* :file:`zh.json` — Simplified Chinese (JSON).
* :file:`ru.json` — Russian best-effort draft (JSON, ``draft=true``).
* :file:`af.yaml` / :file:`de.yaml` / :file:`es.yaml` /
  :file:`fr.yaml` / :file:`ga.yaml` / :file:`hu.yaml` /
  :file:`it.yaml` / :file:`ja.yaml` / :file:`ko.yaml` /
  :file:`pt.yaml` / :file:`tr.yaml` / :file:`uk.yaml` /
  :file:`zh-hant.yaml` — 13 best-effort draft YAML stubs.

If a key is missing in the active locale we fall back to English; if
English also lacks the key we return the key verbatim. This makes
i18n strictly additive: shipping a new string in code without
registering it across all locales degrades to English, never to a
crash.

## Module layout

This module is kept small (<300 LOC) per the v0.4.0 closeout
anti-bloat rule. The YAML parser and the catalog loader are split
into focused submodules:

* :mod:`loopos.i18n._yaml` — hand-rolled YAML parser (no PyYAML dep).
* :mod:`loopos.i18n._catalogs` — catalog loading + alias table.
* :mod:`loopos.i18n._resolution` — locale resolution + init.
"""
from __future__ import annotations

from typing import Any

from loopos.i18n._catalogs import (
    FALLBACK_LOCALE,
    PACKAGE_DIR,
    SUPPORTED_LOCALES,
    _clear_catalog_cache,
    _config_path,
    _read_catalog_file,
    load_catalog,
    persist_locale,
    supported_locales,
)
from loopos.i18n._resolution import (
    _autodetect_locale,
    _read_persisted_locale,
    init_locale,
    normalize_locale,
    resolve_locale,
    validate_locale,
)
from loopos.i18n._yaml import parse_simple_yaml

# Re-export the simple_yaml parser under its private name for
# backward compat with anything that imported it from __init__.
_parse_simple_yaml = parse_simple_yaml


__all__ = [
    "FALLBACK_LOCALE",
    "PACKAGE_DIR",
    "SUPPORTED_LOCALES",
    "_autodetect_locale",
    "_clear_catalog_cache",
    "_config_path",
    "_read_catalog_file",
    "_read_persisted_locale",
    "active_source",
    "get_locale",
    "init_locale",
    "load_catalog",
    "normalize_locale",
    "parse_simple_yaml",
    "persist_locale",
    "resolve_locale",
    "set_locale",
    "supported_locales",
    "t",
    "validate_locale",
]


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------


_ACTIVE_LOCALE: str = FALLBACK_LOCALE
_ACTIVE_SOURCE: str = "default"


def get_locale() -> str:  # noqa: F811 -- re-exported above; here for type
    """Return the active locale id (``"en"`` / ``"zh"`` / etc.)."""
    return _ACTIVE_LOCALE


def active_source() -> str:  # noqa: F811
    """Return the source of the active locale (for diagnostics).

    Possible values: ``"default"`` | ``"manual"`` | ``"env"`` |
    ``"flag"`` | ``"persisted"`` | ``"system"`` | ``"fallback"``.
    """
    return _ACTIVE_SOURCE


def set_locale(locale: str, *, source: str = "manual") -> None:  # noqa: F811
    """Set the active locale (idempotent). ``source`` is recorded for
    diagnostics and the ``active_source()`` getter.
    """
    global _ACTIVE_LOCALE, _ACTIVE_SOURCE
    normalized = normalize_locale(locale)
    if normalized in SUPPORTED_LOCALES:
        _ACTIVE_LOCALE = normalized
    else:
        _ACTIVE_LOCALE = FALLBACK_LOCALE
    _ACTIVE_SOURCE = source


def t(key: str, **kwargs: Any) -> str:
    """Translate ``key`` (a dotted path like ``"panel.run.title"``).

    Resolution order: active locale → English fallback → key
    verbatim. Missing keys never raise; they degrade gracefully.
    Optional ``kwargs`` are substituted into the translated string
    via :func:`str.format`.
    """
    raw = _lookup(_ACTIVE_LOCALE, key)
    if raw is None:
        raw = _lookup(FALLBACK_LOCALE, key)
    if raw is None:
        return key
    if not kwargs:
        return raw
    try:
        return raw.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return raw


def _lookup(locale: str, key: str) -> str | None:
    """Walk the dotted key path through the catalog tree.

    Returns ``None`` if any segment is missing, so the caller can
    fall through to the next locale.
    """
    catalog = load_catalog(locale)
    node: Any = catalog
    for segment in key.split("."):
        if not isinstance(node, dict):
            return None
        if segment not in node:
            return None
        node = node[segment]
    if not isinstance(node, str):
        return None
    return node
