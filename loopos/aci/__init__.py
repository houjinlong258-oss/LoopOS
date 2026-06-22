"""Agent Command Interface (ACI).

ACI is the agent-native command boundary introduced in LoopOS v0.2.
Every command is bound to a goal, a policy decision, a capability
boundary, a structured observation, a trace, an evaluation, progress,
and a convergence feedback signal.

Phase 2 surface:

* :mod:`loopos.aci.models` — typed :class:`AgentCommand` and
  :class:`AgentCommandResult` schemas with stable JSON contracts.
  Includes :class:`ProviderHint`, :class:`ResolvedProvider`,
  :class:`RiskHint`, and the four ``Summary`` models that downstream
  consumers (ALI FSM, Review Artifact, Readiness Proof) consume.
* :mod:`loopos.aci.errors` — typed errors raised by the ACI layer.
  Adds :class:`ProviderResolutionError` and
  :class:`UnsupportedCommandKindError` for the strict-mode escape
  hatches behind :meth:`CommandRunner.resolve_provider`.
* :mod:`loopos.aci.runner` — :class:`CommandRunner` that routes an
  :class:`AgentCommand` through the existing Policy OS / Syscall
  path, with provider-hint resolution (metadata-only) via
  :class:`loopos.providers.ProviderRegistry`.
* :mod:`loopos.aci.serialization` — stable (de)serialization
  helpers for the wire format.

ACI does **not** import ``loopos.kernel.*`` and does **not** touch
``KernelLoopEngine`` in Phase 2. The integration with the Kernel
loop engine is deferred to a later phase.
"""

from loopos.aci.errors import (
    ACIError,
    CommandBlockedError,
    CommandValidationError,
    PolicyDeniedError,
    ProviderResolutionError,
    UnsupportedCommandKindError,
)
from loopos.aci.models import (
    AgentCommand,
    AgentCommandKind,
    AgentCommandMode,
    AgentCommandResult,
    AgentCommandStatus,
    CommandCapability,
    ConvergenceHint,
    ConvergenceSummary,
    EvaluationSummary,
    ObservationKind,
    ObservationSummary,
    PolicyDecisionSummary,
    ProgressSummary,
    ProviderHint,
    ProviderResolutionSource,
    ResolvedProvider,
    RiskHint,
    RiskHintLevel,
    SyscallSummary,
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
from loopos.aci.serialization import (
    command_to_wire_dict,
    deserialize_command,
    deserialize_result,
    result_to_wire_dict,
    serialize_command_payload,
    serialize_result_payload,
)

__all__ = [
    # Core contracts
    "AgentCommand",
    "AgentCommandResult",
    "AgentCommandKind",
    "AgentCommandMode",
    "AgentCommandStatus",
    # Provider binding
    "ProviderHint",
    "ResolvedProvider",
    "ProviderResolutionSource",
    # Risk + sub-models
    "RiskHint",
    "RiskHintLevel",
    "CommandCapability",
    # Summaries (consumed by ALI / Review / Readiness)
    "PolicyDecisionSummary",
    "SyscallSummary",
    "ObservationSummary",
    "ObservationKind",
    "EvaluationSummary",
    "ProgressSummary",
    "ConvergenceSummary",
    "ConvergenceHint",
    # Runner
    "CommandRunner",
    "RunnerConfig",
    "KIND_TO_POLICY_SCOPE",
    "KIND_TO_SYSCALL",
    "build_default_runner",
    # Errors
    "ACIError",
    "CommandBlockedError",
    "CommandValidationError",
    "PolicyDeniedError",
    "ProviderResolutionError",
    "UnsupportedCommandKindError",
    # Serialization
    "parse_command",
    "serialize_command",
    "serialize_command_payload",
    "serialize_result_payload",
    "deserialize_command",
    "deserialize_result",
    "command_to_wire_dict",
    "result_to_wire_dict",
]
