"""LoopOS public package.

LoopOS v0.4.0 is a Project Training Runtime for AI agents.

User goal is the objective. Project gap is the loss. Iterations are epochs.
Findings are gradient signals. Fusion is the optimizer. Mad Dog prevents fake
convergence. LAIL carries low-token optimization signals. Memory prevents
repeated waste.

The ``loop_engine`` package is the product-facing orchestrator. The Kernel
Loop Engine (``loopos.kernel``) remains the low-level execution backend.
Safety is provided as an action boundary, not the product thesis.
"""

from loopos.core.isa import Instruction, parse_instruction

__all__ = ["Instruction", "parse_instruction"]

__version__ = "0.4.0"
