from __future__ import annotations

try:
    from rich.text import Text
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

def render_pipeline(current_stage: str) -> Text:
    if not _HAS_RICH:
        return Text(f"Pipeline: {current_stage}")
        
    stages = [
        "Goal Loaded",
        "Provider OK",
        "Policy OK",
        "Planning",
        "Execute",
        "Verify",
        "Complete"
    ]
    
    curr_idx = 3  # Default to Planning
    for idx, stage in enumerate(stages):
        if stage.lower().replace(" ", "") in current_stage.lower().replace(" ", "").replace("_", ""):
            curr_idx = idx
            break
            
    parts = []
    for idx, stage in enumerate(stages):
        if idx < curr_idx:
            parts.append(Text(f"✓ {stage}", style="green"))
        elif idx == curr_idx:
            parts.append(Text(f"→ {stage}", style="bold cyan"))
        else:
            parts.append(Text(f"○ {stage}", style="dim"))
            
    res = Text("  ")
    for i, part in enumerate(parts):
        if i > 0:
            res.append("   ")
        res.append(part)
    return res
