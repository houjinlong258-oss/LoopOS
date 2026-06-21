"""Core LoopOS runtime models and engine.

Note: ``LoopEngine`` is exported here for backward compatibility only and is
deprecated in favor of ``loopos.kernel.loop_engine.KernelLoopEngine``. It will be
removed from this package in v0.2.
"""

# ``LoopEngine`` is re-exported only to preserve backward compatibility. New code
# should import and use ``loopos.kernel.loop_engine.KernelLoopEngine`` instead.
# Will be removed in v0.2.
from loopos.core.isa import Instruction
from loopos.core.loop_engine import LoopEngine  # noqa: F401  # deprecated, see note above
from loopos.core.state import LoopState, Observation

__all__ = ["Instruction", "LoopEngine", "LoopState", "Observation"]
