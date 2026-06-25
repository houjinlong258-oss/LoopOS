from __future__ import annotations

import json
import subprocess
import sys
from typing import cast

import pytest

from loopos.cli.app import _extract_lang_flag
from loopos.cli.commands.locale import locale_command
from loopos.cli.fallback import fallback_main


def test_locale_list_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert locale_command("list", json_output=True) == 0
    payload = json.loads(capsys.readouterr().out)
    # v0.4.x: 16 supported locales (3 legacy JSON + 13 new YAML drafts).
    ids = {item["id"] for item in payload["locales"]}
    assert {"zh", "en", "ru"} <= ids  # legacy subset still present
    assert "zh-hant" in ids  # Traditional Chinese
    assert "de" in ids  # German
    assert "ja" in ids  # Japanese
    assert len(ids) >= 16


def test_extract_lang_flag_cleans_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOOPOS_LANG_PRE", raising=False)
    cleaned, locale = _extract_lang_flag(["--lang", "en", "locale", "show"])
    assert cleaned == ["locale", "show"]
    assert locale == "en"


def test_locale_show_accepts_global_lang_flag() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "loopos.cli.app",
            "--lang=en",
            "locale",
            "show",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = cast(dict[str, object], json.loads(result.stdout))
    assert payload["active"] == "en"


def test_fallback_locale_show_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert fallback_main(["locale", "show", "--json"]) == 0
    payload = cast(dict[str, object], json.loads(capsys.readouterr().out))
    assert payload["active"] in {"zh", "en", "ru"}
