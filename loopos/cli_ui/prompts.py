from __future__ import annotations
import sys

try:
    from rich.prompt import Prompt
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

def ask_choice(prompt_text: str, choices: list[str], default: str) -> str:
    if not _HAS_RICH:
        sys.stdout.write(f"{prompt_text} ({'/'.join(choices)}) [{default}]: ")
        sys.stdout.flush()
        line = sys.stdin.readline().strip()
        return line if line else default
    return Prompt.ask(prompt_text, choices=choices, default=default)
