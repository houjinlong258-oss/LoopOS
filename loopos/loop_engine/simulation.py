"""Default simulated adapters for v0.4.0.

The simulation layer is explicit: simulated build and test records use
``status="simulated"`` and ``source="loopos_v0_4_simulated_adapter"``.
These aliases make the adapter boundary visible without duplicating the
existing deterministic default implementations.
"""

from __future__ import annotations

from loopos.loop_engine.builder import LoopBuilder as SimulatedBuilder
from loopos.loop_engine.checkpoint import InMemoryCheckpointStore
from loopos.loop_engine.models import SIMULATED_ADAPTER_SOURCE
from loopos.loop_engine.optimizer import LoopOptimizer as SimulatedOptimizer
from loopos.loop_engine.planner import LoopPlanner as SimulatedPlanner
from loopos.loop_engine.repair import RepairEngine as SimulatedRepairPlanner
from loopos.loop_engine.reviewer import LoopReviewer as SimulatedReviewer
from loopos.loop_engine.tester import LoopTester as SimulatedTester
from loopos.quality.convergence import ConvergenceEngine as SimpleConvergenceEvaluator
from loopos.quality.delivery import DeliveryEngine as SimulatedDeliveryEvaluator


__all__ = [
    "InMemoryCheckpointStore",
    "SIMULATED_ADAPTER_SOURCE",
    "SimpleConvergenceEvaluator",
    "SimulatedBuilder",
    "SimulatedDeliveryEvaluator",
    "SimulatedOptimizer",
    "SimulatedPlanner",
    "SimulatedRepairPlanner",
    "SimulatedReviewer",
    "SimulatedTester",
]
