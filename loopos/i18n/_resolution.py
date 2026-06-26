"""Locale resolution for the i18n layer.

Kept separate from ``__init__.py`` so the public API module stays
under 300 lines per the v0.4.0 closeout anti-bloat rule.

The resolution priority is:

1. ``flag`` kwarg (CLI ``--lang=xx``)
2. ``LOOPOS_LANG`` env var
3. ``~/.loopos/config.json`` ``locale`` field
4. system ``LANG`` / ``LANGUAGE`` (POSIX)
5. Windows UI language (via ctypes)
6. ``en`` fallback

Each step normalizes the candidate string via
:func:`normalize_locale`, which maps aliases to canonical ids and
rejects anything outside :data:`SUPPORTED_LOCALES`.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Optional

from loopos.i18n._catalogs import (
    FALLBACK_LOCALE,
    SUPPORTED_LOCALES,
    _LOCALE_ALIASES,
)


def validate_locale(value: str) -> Optional[str]:
    """Strict check: returns the canonical id if known, else ``None``.

    This is the strict counterpart to :func:`normalize_locale`: the
    ``set`` CLI uses it to reject unknown user input, while
    :func:`normalize_locale` falls back to ``en`` for permissive
    auto-detection from system / env / persisted sources.
    """
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if candidate in SUPPORTED_LOCALES:
        return candidate
    # Lower-case fallback for case-insensitive matches.
    lower = candidate.lower()
    if lower in _LOCALE_ALIASES:
        return _LOCALE_ALIASES[lower]
    # Last resort: language prefix (e.g. "zh_CN" -> "zh", "en-US" -> "en").
    prefix = lower.split("-")[0].split("_")[0]
    if prefix in _LOCALE_ALIASES:
        return _LOCALE_ALIASES[prefix]
    return None


def normalize_locale(value: str) -> str:
    """Map any user input to a canonical locale id.

    Returns the input unchanged if it is already in
    :data:`SUPPORTED_LOCALES`; otherwise applies the alias table
    (e.g. ``"Chinese"`` -> ``"zh"``); otherwise returns the
    fallback (``"en"``). For strict validation (e.g. CLI ``set``)
    use :func:`validate_locale` instead.
    """
    return validate_locale(value) or FALLBACK_LOCALE


def _read_persisted_locale() -> Optional[str]:
    """Read the persisted locale from ``loopos.i18n._config_path()``.

    Returns the ``locale`` field if present, else ``None``.

    The path is resolved lazily through the public
    ``loopos.i18n`` namespace so the same helper that
    :func:`persist_locale` writes to is the helper this function
    reads from. Tests can therefore monkeypatch
    ``loopos.i18n._config_path`` and have both directions agree.
    """
    # Lazy import: keep this module independent of the public
    # ``__init__`` at import time, and pick up test-time
    # monkeypatches of ``loopos.i18n._config_path``.
    import loopos.i18n as _i18n
    config_path = _i18n._config_path()
    if not config_path.exists():
        return None
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            data = json.loads(handle.read())
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(data, dict):
        value = data.get("locale")
        if isinstance(value, str):
            return value
    return None


def _read_system_locale() -> Optional[str]:
    """Best-effort detection of the OS's preferred language."""
    # POSIX: LANG or LANGUAGE (en_US.UTF-8 / en_US:en).
    for var in ("LANG", "LANGUAGE"):
        value = os.environ.get(var)
        if value:
            return value
    # Windows: GetUserDefaultUILanguage returns a LANGID; map the
    # common ones to our canonical ids.
    if sys.platform == "win32":
        try:
            import ctypes  # type: ignore
            windll = ctypes.windll.kernel32  # type: ignore
            langid = windll.GetUserDefaultUILanguage()
            mapping = {
                0x0409: "en", 0x0809: "en",
                0x0407: "de", 0x0807: "de",
                0x040C: "fr", 0x080C: "fr",
                0x0410: "it", 0x0810: "it",
                0x0C0A: "es",  # Spanish (Spain, modern sort)
                0x040B: "fi",
                0x041D: "sv",
                0x0413: "nl",
                0x0419: "ru",
                0x0404: "zh-hant", 0x0C04: "zh-hant", 0x1404: "zh-hant",
                0x0804: "zh",
                0x0411: "ja",
                0x0412: "ko",
                0x041F: "tr",
            }
            mapped = mapping.get(int(langid))
            if mapped is not None:
                return mapped
        except Exception:  # pragma: no cover
            pass
    return None


def resolve_locale(
    flag: str | None = None,
) -> tuple[str, str]:
    """Pick the active locale by walking the priority chain.

    Returns ``(locale_id, source)`` where ``source`` is one of
    ``"flag"`` / ``"env"`` / ``"persisted"`` / ``"system"`` /
    ``"fallback"``. The ``flag`` kwarg corresponds to the CLI
    ``--lang=xx`` option.

    Implementation note: the persisted / system lookups are
    called through ``loopos.i18n.<name>`` at call time (not via
    direct module-level reference) so tests can monkeypatch
    ``loopos.i18n._read_persisted_locale`` /
    ``loopos.i18n._autodetect_locale`` to control resolution.
    """
    if flag:
        candidate = normalize_locale(flag)
        if candidate in SUPPORTED_LOCALES:
            return candidate, "flag"
    env_value = os.environ.get("LOOPOS_LANG")
    if env_value:
        candidate = normalize_locale(env_value)
        if candidate in SUPPORTED_LOCALES:
            return candidate, "env"
    # Lazy import: go through the public ``loopos.i18n`` namespace
    # so tests can monkeypatch ``loopos.i18n._read_persisted_locale``.
    import loopos.i18n as _i18n_public
    persisted = _i18n_public._read_persisted_locale()
    if persisted:
        candidate = normalize_locale(persisted)
        if candidate in SUPPORTED_LOCALES:
            return candidate, "persisted"
    system_value = _i18n_public._autodetect_locale()
    if system_value:
        candidate = normalize_locale(system_value)
        if candidate in SUPPORTED_LOCALES:
            return candidate, "system"
    return FALLBACK_LOCALE, "fallback"


def init_locale(*, flag: str | None = None) -> str:
    """Resolve and apply the active locale; return its id.

    This is the canonical entry point called at CLI startup. It is
    the only function that calls :func:`set_locale` at the module
    level (other callers use :func:`set_locale` directly for
    tests / manual override).
    """
    # Imported lazily here to avoid a circular import at module load
    # time: __init__ imports from this module, and we want to
    # mutate __init__'s globals.
    import loopos.i18n as _i18n
    locale, source = resolve_locale(flag=flag)
    _i18n.set_locale(locale, source=source)
    return locale


# Backward-compat alias for tests that monkeypatched the old name.
_autodetect_locale = _read_system_locale


__all__ = [
    "_autodetect_locale",
    "_read_persisted_locale",
    "init_locale",
    "normalize_locale",
    "resolve_locale",
    "validate_locale",
]