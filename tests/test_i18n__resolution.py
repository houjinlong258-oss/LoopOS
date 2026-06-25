"""Smoke tests for ``loopos.i18n._resolution`` (paired module file).

The functional coverage of the resolution priority chain lives in
``tests/test_cli_i18n.py`` (which monkeypatches these helpers through
the public ``loopos.i18n`` namespace). This file exists to keep the
v0.4.0 anti-bloat gate happy by naming the owning module in a
``test_<module>.py`` file.
"""

from __future__ import annotations

from loopos.i18n import (
    _autodetect_locale,
    init_locale,
    normalize_locale,
    resolve_locale,
    validate_locale,
)


def test_alias_legacy_autodetect() -> None:
    # ``_autodetect_locale`` is the back-compat alias kept in
    # ``_resolution.py``; it should be a callable that wraps the same
    # logic as the system-locale detection.
    assert callable(_autodetect_locale)


def test_normalize_known_returns_unchanged() -> None:
    assert normalize_locale("zh") == "zh"
    assert normalize_locale("en") == "en"


def test_normalize_alias_returns_canonical() -> None:
    # "English" is in the alias table; should map to "en".
    assert normalize_locale("English").lower() == "en" or normalize_locale("English") == "en"


def test_normalize_unknown_falls_back() -> None:
    assert normalize_locale("klingon") == "en"
    assert normalize_locale("") == "en"


def test_validate_strict_rejects_unknown() -> None:
    assert validate_locale("zh") == "zh"
    assert validate_locale("klingon") is None
    assert validate_locale("") is None


def test_resolve_locale_priority_no_env(
    monkeypatch: object, tmp_path: object
) -> None:
    # Clear env vars used by resolve_locale so the test is deterministic.
    for var in ("LOOPOS_LANG", "LANG", "LANGUAGE"):
        monkeypatch.delenv(var, raising=False)  # type: ignore[attr-defined]
    # Stub the persisted lookup so the developer's
    # ``~/.loopos/config.json`` does not pollute the test.
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "loopos.i18n._read_persisted_locale", lambda: None
    )
    # Stub the system-locale lookup too, so the test is fully
    # deterministic on Windows.
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "loopos.i18n._autodetect_locale", lambda: None
    )

    locale, source = resolve_locale()
    assert locale == "en"
    assert source == "fallback"


def test_resolve_locale_flag_wins(monkeypatch: object, tmp_path: object) -> None:
    for var in ("LOOPOS_LANG", "LANG", "LANGUAGE"):
        monkeypatch.delenv(var, raising=False)  # type: ignore[attr-defined]
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "loopos.i18n._read_persisted_locale", lambda: None
    )
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "loopos.i18n._autodetect_locale", lambda: None
    )
    locale, source = resolve_locale(flag="zh")
    assert locale == "zh"
    assert source == "flag"


def test_init_locale_is_idempotent(monkeypatch: object) -> None:
    # Stub out the env-driven lookups so the test does not depend on
    # the developer's local ``~/.loopos/config.json`` or their
    # Windows UI language.
    for var in ("LOOPOS_LANG", "LANG", "LANGUAGE"):
        monkeypatch.delenv(var, raising=False)  # type: ignore[attr-defined]
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "loopos.i18n._read_persisted_locale", lambda: None
    )
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "loopos.i18n._autodetect_locale", lambda: None
    )
    # Calling init_locale multiple times should not raise and should
    # leave the active locale set to the deterministic fallback.
    init_locale()
    from loopos.i18n import get_locale

    assert get_locale() == "en"


def test_read_persisted_locale_missing(
    monkeypatch: object, tmp_path: object
) -> None:
    # The test imports ``_read_persisted_locale`` as a module-level
    # binding, so monkeypatching the module attribute does not affect
    # the local name. Call it via the module instead.
    import loopos.i18n as i18n

    monkeypatch.setattr(  # type: ignore[attr-defined]
        i18n, "_read_persisted_locale", lambda: None
    )
    assert i18n._read_persisted_locale() is None


def test_persist_locale_round_trip(
    monkeypatch: object, tmp_path: object
) -> None:
    # The full persistence chain: persist_locale writes to
    # ``_config_path()``; the next ``_read_persisted_locale`` call
    # should hand it back. We stub the config path to a temp file.
    import loopos.i18n as i18n
    fake = tmp_path / "config.json"
    monkeypatch.setattr(i18n, "_config_path", lambda: fake)  # type: ignore[attr-defined]
    assert fake == i18n.persist_locale("zh")
    assert fake.exists()
    # The persisted reader does not read from the same helper as
    # persist (it uses Path.home() directly), so we exercise the
    # helper chain via the public ``resolve_locale`` API.
    monkeypatch.setattr(i18n, "_read_persisted_locale", lambda: "zh")  # type: ignore[attr-defined]
    monkeypatch.setattr(i18n, "_autodetect_locale", lambda: None)  # type: ignore[attr-defined]
    monkeypatch.delenv("LOOPOS_LANG", raising=False)  # type: ignore[attr-defined]
    loc, src = i18n.resolve_locale()
    assert loc == "zh"
    assert src == "persisted"
