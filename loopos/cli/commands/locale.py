"""``loopos locale`` subcommand."""

from __future__ import annotations

import json
import sys

from loopos.i18n import (
    SUPPORTED_LOCALES,
    _config_path,
    active_source,
    get_locale,
    init_locale,
    normalize_locale,
    persist_locale,
    supported_locales,
    t,
)


def locale_command(
    action: str = "show",
    locale_id: str | None = None,
    *,
    json_output: bool = False,
) -> int:
    """Entry point for ``loopos locale``."""
    if action == "list":
        locales = supported_locales()
        if json_output:
            sys.stdout.write(
                json.dumps(
                    {"locales": locales, "active": get_locale()},
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n"
            )
            return 0
        try:
            from rich.console import Console
            from rich.table import Table

            console = Console()
            table = Table(
                box=None,
                padding=(0, 1),
                show_header=True,
                header_style="bold cyan",
            )
            table.add_column("id", style="cyan")
            table.add_column("name", style="white")
            table.add_column("english", style="dim")
            table.add_column("draft", style="yellow")
            for loc in locales:
                table.add_row(
                    loc["id"],
                    loc["name"],
                    loc["english_name"],
                    loc["draft"] or "-",
                )
            console.print(table)
            return 0
        except ImportError:
            pass
        for loc in locales:
            draft = f"  [{loc['draft']}]" if loc["draft"] else ""
            sys.stdout.write(
                f"  {loc['id']}  {loc['name']}  ({loc['english_name']}){draft}\n"
            )
        return 0

    if action == "show":
        locale = get_locale()
        source = active_source()
        payload = {
            "active": locale,
            "source": source,
            "config_path": str(_config_path()),
        }
        if json_output:
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            return 0
        sys.stdout.write(t("messages.active_locale", locale=locale, source=source) + "\n")
        sys.stdout.write(t("messages.config_path", path=str(_config_path())) + "\n")
        return 0

    if action == "set":
        if not locale_id:
            sys.stderr.write(
                t(
                    "errors.missing_required_arg",
                    command="locale",
                    action="set",
                    arg="LOCALE",
                )
                + "\n"
            )
            return 2
        norm = normalize_locale(locale_id)
        if norm not in SUPPORTED_LOCALES:
            sys.stderr.write(
                t(
                    "messages.invalid_locale",
                    locale=locale_id,
                    supported=", ".join(SUPPORTED_LOCALES),
                )
                + "\n"
            )
            return 2
        path = persist_locale(norm)
        init_locale()
        sys.stdout.write(t("messages.persisted_locale", locale=norm) + "\n")
        sys.stdout.write(t("messages.config_path", path=str(path)) + "\n")
        return 0

    if action == "help":
        sys.stdout.write(t("commands.locale.help") + "\n")
        sys.stdout.write("  loopos locale list\n")
        sys.stdout.write("  loopos locale show\n")
        sys.stdout.write("  loopos locale set <zh|en|ru>\n")
        return 0

    sys.stderr.write(t("errors.unknown_action", command="locale", action=action) + "\n")
    return 2


__all__ = ["locale_command"]

