"""Runtime configuration CLI command."""

from __future__ import annotations

import json
from pathlib import Path


def config_command(*, data_dir: str | Path = ".loopos") -> int:
    print(
        json.dumps(
            {
                "data_dir": str(Path(data_dir)),
                "runtime": "python",
                "kernel": "v2",
                "llm": "mock-only",
                "web_ui": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0
