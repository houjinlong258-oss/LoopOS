"""Mascot rendering and usage strategy."""

MASCOT_LARGE = r"""   /\_/\
  ( o.o )   LoopOS v0.3
   /∞\      governed agent runtime
  /___\ ))= Think freely. Act governed."""

MASCOT_COMPACT = "( o.o )∞"

PROMPT_SYMBOL = "loopos ∞>"

def get_mascot(compact: bool = False) -> str:
    return MASCOT_COMPACT if compact else MASCOT_LARGE
