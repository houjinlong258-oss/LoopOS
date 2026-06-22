"""Agent Command Interface (ACI).

ACI is the agent-native command boundary introduced in LoopOS v0.2.
Every command is bound to a goal, a policy decision, a capability
boundary, a structured observation, a trace, an evaluation, progress,
and a convergence feedback signal.

This package is intentionally small:

* :mod:`loopos.aci.models` - typed :class:`AgentCommand` and
  :class:`AgentCommandResult` schemas with stable JSON contracts.
* :mod:`loopos.aci.errors` - typed errors raised by the ACI layer.
* :mod:`loopos.aci.runner` - :class:`CommandRunner` that routes an
  :class:`AgentCommand` through the existing Policy OS / Syscall path
  without bypassing it.

ACI does **not** import ``loopos.kernel.*`` and does **not** touch
``KernelLoopEngine`` in Phase 1. The integration with the Kernel loop
engine is deferred to a later phase.
"""

from loopos.aci.errors import (
    ACIError,
    CommandBlockedError,
    CommandValidationError,
    PolicyDeniedError,
)
from loopos.aci.models import (
    AgentCommand,
    AgentCommandKind,
    AgentCommandMode,
    AgentCommandResult,
    AgentCommandStatus,
    ObservationSummary,
    ProgressSnapshot,
)
from loopos.aci.models import (
    AgentCommand,
    AgentCommandKind,
    AgentCommandMode,
    AgentCommandResult,
    AgentCommandStatus,
    ConvergenceSnapshot,
    EvaluationHint,
    ObservationKind,
    ObservationSummary,
    ProgressSnapshot,
    parse_command,
    serialize_command,
)
from loopos.aci.runner import (
    KIND_TO_POLICY_SCOPE,
    KIND_TO_SYSCALL,
    CommandRunner,
    RunnerConfig,
    build_default_runner,
)

__all__ = [
    "ACIError",
    "AgentCommand",
    "AgentCommandKind",
    "AgentCommandMode",
    "AgentCommandResult",
    "AgentCommandStatus",
    "CommandBlockedError",
    "CommandRunner",
    "CommandValidationError",
    "ConvergenceSnapshot",
    "EvaluationHint",
    "KIND_TO_POLICY_SCOPE",
    "KIND_TO_SYSCALL",
    "ObservationKind",
    "ObservationSummary",
    "PolicyDeniedError",
    "ProgressSnapshot",
    "RunnerConfig",
    "build_default_runner",
    "parse_command",
    "serialize_command",
]
