"""LoopOS Agent OS Kernel contracts."""

from loopos.kernel.boot import KernelBoot, KernelBootError, KernelConfig, KernelRuntime
from loopos.kernel.checkpoint import CheckpointStore, KernelCheckpoint
from loopos.kernel.errors import (
    CheckpointError,
    InvariantViolationError,
    InvalidTransitionError,
    KernelError,
    SupervisorHaltError,
)
from loopos.kernel.evaluation_source import EvaluationSource
from loopos.kernel.invariants import KernelInvariantChecker, KernelInvariantViolation
from loopos.kernel.lifecycle import KernelLifecycle
from loopos.kernel.loop_engine import KernelLoopEngine
from loopos.kernel.models import PendingApproval, RunRecord, RunSpec
from loopos.kernel.progress_accumulator import (
    ProgressAccumulatorSnapshot,
    load_progress_accumulator,
    save_progress_accumulator,
    update_progress_accumulator,
)
from loopos.kernel.replay import ReplayEngine, ReplayResult
from loopos.kernel.run_manager import RunManager
from loopos.kernel.scheduler import LoopScheduler, ScheduleDecision, SchedulerInput
from loopos.kernel.signals import KernelSignal, KernelSignalEvent
from loopos.kernel.state_machine import KernelStateMachine
from loopos.kernel.supervisor import Supervisor, SupervisorConfig, SupervisorDecision
from loopos.kernel.trace import TraceEvent, TraceStore
from loopos.kernel.transition import TransitionEngine

__all__ = [
    "CheckpointError",
    "CheckpointStore",
    "EvaluationSource",
    "InvariantViolationError",
    "InvalidTransitionError",
    "KernelBoot",
    "KernelBootError",
    "KernelCheckpoint",
    "KernelConfig",
    "KernelError",
    "KernelInvariantChecker",
    "KernelInvariantViolation",
    "KernelLifecycle",
    "KernelLoopEngine",
    "KernelRuntime",
    "KernelSignal",
    "KernelSignalEvent",
    "KernelStateMachine",
    "LoopScheduler",
    "PendingApproval",
    "ProgressAccumulatorSnapshot",
    "ReplayEngine",
    "ReplayResult",
    "RunManager",
    "RunRecord",
    "RunSpec",
    "ScheduleDecision",
    "SchedulerInput",
    "Supervisor",
    "SupervisorConfig",
    "SupervisorDecision",
    "SupervisorHaltError",
    "TransitionEngine",
    "TraceEvent",
    "TraceStore",
    "load_progress_accumulator",
    "save_progress_accumulator",
    "update_progress_accumulator",
]
