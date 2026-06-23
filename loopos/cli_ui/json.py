import json
import sys
from typing import Any

def emit_json(payload: Any) -> None:
    """Print pure JSON to stdout, guaranteeing no Rich codes leak in."""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    sys.stdout.flush()
