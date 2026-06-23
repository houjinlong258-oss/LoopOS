from typing import Any
try:
    from rich.syntax import Syntax
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

def render_diff(diff_text: str) -> Any:
    if not _HAS_RICH:
        return diff_text
    return Syntax(diff_text, "diff", theme="monokai", word_wrap=True)
