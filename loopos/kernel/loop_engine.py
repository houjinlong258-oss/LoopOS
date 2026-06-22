"""Traceable and resumable LoopOS Kernel engine.

Phase 4 (v0.2): a thin ``submit_agent_command`` integration point
closes the runtime loop by wiring :class:`loopos.aci.CommandRunner`
to :func:`loopos.ali.session.consume_aci_result`. Existing
``run`` / ``resume`` / convergence-handoff paths are untouched.
The integration is opt-in: callers can keep using the existing
AIL-instruction loop or call :meth:`KernelLoopEngine.submit_agent_command`
to drive an ALI session from a real :class:`AgentCommandResult`.
"""

from __future__ import annotations

from typing import Any, Protocol

from loopos.aci.models import AgentCommand, AgentCommandResult
from loopos.aci.runner import CommandRunner
from loopos.agents.intent_compiler import DeterministicIntentCompiler
from loopos.agents.skill_extractor import SkillExtractor
from loopos.ail.models import AILInstruction
from loopos.ali.fsm import AgentLoopFSM
from loopos.ali.models import AgentLoopSession
from loopos.ali.session import consume_aci_result
from loopos.context import ContextCompiler
from loopos.convergence import ConvergenceEngine, EvaluationResult, LoopDecision, ProgressDelta
from loopos.kernel.boot import KernelRuntime
from loopos.kernel.evaluation_source import EvaluationSource
from loopos.kernel.models import KernelPhase, KernelRunStatus, PendingApproval, RunRecord, RunSpec
from loopos.kernel.progress_accumulator import update_progress_accumulator
from loopos.kernel.scheduler import LoopScheduler, ScheduleDecision, SchedulerInput
from loopos.kernel.state_machine import KernelStateMachine
from loopos.kernel.trace import TraceKind
from loopos.kernel.transition import TransitionEngine
from loopos.memory.repository import MemoryRepository
from loopos.syscalls import SyscallCall, SyscallResult

# Convergence actions that always resolve to a halt regardless of the scheduler.
_CONVERGENCE_HALT_ACTIONS = frozenset({"halt_success", "halt_failure", "halt_blocked"})
# Convergence action sets whose intent is preserved as a scheduler input signal.
_CONVERGENCE_REPAIR_ACTIONS = frozenset({"repair"})
_CONVERGENCE_REPLAN_ACTIONS = frozenset({"replan"})
_CONVERGENCE_ASK_ACTIONS = frozenset({"ask_user"})
_CONVERGENCE_WAIT_ACTIONS = frozenset({"wait_approval"})
_CONVERGENCE_CONTINUE_ACTIONS = frozenset({"continue"})

_SYSCALLS = {
    "TERM.EXEC": "terminal.exec",
    "FILE.READ": "file.read",
    "FILE.WRITE": "file.write",
    "GIT.STATUS": "git.status",
    "GIT.DIFF": "git.diff",
}


class IntentCompiler(Protocol):
    def compile(self, run: RunRecord) -> list[AILInstruction]: ...


class KernelLoopEngine:
    def __init__(
        self,
        runtime: KernelRuntime,
        *,
        intent_compiler: IntentCompiler | None = None,
        scheduler: LoopScheduler | None = None,
        memory_repository: MemoryRepository | None = None,
    ) -> None:
        self.runtime = runtime
        self.intent_compiler = intent_compiler or DeterministicIntentCompiler()
        self.scheduler = scheduler or LoopScheduler()
        self.state_machine = KernelStateMachine()
        self.transitions = TransitionEngine()
        self.memory_repository = memory_repository
        self.context_compiler = ContextCompiler(policy_engine=runtime.policy_engine)
        self.convergence = ConvergenceEngine()
        self.evaluation_source = EvaluationSource()
        if memory_repository is not None:
            self.runtime.trace_store.indexer = memory_repository.index.upsert_trace_event

    def run(self, spec: RunSpec) -> RunRecord:
        run = self.runtime.run_manager.create(spec)
        self._transition(run, "running", "COMPILING")
        self._trace("run", run, {"event": "run_started", "state": run.model_dump(mode="json")})
        self._trace("goal", run, {"goal_spec": spec.metadata.get("goal_spec", {})})
        plan = self.intent_compiler.compile(run)
        run.metadata["plan"] = [item.model_dump(mode="json") for item in plan]
        run.metadata["cursor"] = 0
        self.runtime.run_manager.save(run)
        return self._execute(run)

    def resume(self, run_id: str, *, approve: bool = False, deny: bool = False) -> RunRecord:
        run = self.runtime.run_manager.load(run_id)
        if run.status != "waiting_approval":
            raise ValueError(f"run is not waiting for approval: {run.status}")
        if approve == deny:
            raise ValueError("resume requires exactly one of approve or deny")
        self._trace(
            "signal",
            run,
            {"signal": "approve" if approve else "deny"},
            instruction_id=run.current_instruction_id,
        )
        if deny:
            self._transition(run, "blocked", "HALTED", reason="approval denied")
            self.runtime.run_manager.save(run)
            return run
        run.pending_approval = None
        self._transition(run, "running", "EXECUTING")
        self.runtime.run_manager.save(run)
        return self._execute(run, approve_pending=True)

    def _execute(self, run: RunRecord, *, approve_pending: bool = False) -> RunRecord:
        plan = [AILInstruction.model_validate(item) for item in run.metadata.get("plan", [])]
        cursor = int(run.metadata.get("cursor", 0))
        while cursor < len(plan):
            if run.step >= run.max_steps:
                decision = self.scheduler.decide(
                    SchedulerInput(step=run.step, max_steps=run.max_steps)
                )
                self.state_machine.apply_schedule(run, decision)
                self._trace_transition(run, decision.reason_code)
                self.runtime.run_manager.save(run)
                return run

            instruction = plan[cursor]
            run.current_instruction_id = instruction.id
            self._trace(
                "instruction",
                run,
                {
                    "op": instruction.op,
                    "args": instruction.args,
                    "instruction": instruction.model_dump(mode="json"),
                },
                instruction_id=instruction.id,
                step=instruction.step,
            )
            policy = self.runtime.policy_engine.evaluate(
                "instruction.validate",
                subject=instruction.model_dump(mode="json"),
                tags=["instruction", instruction.normalized_op.lower()],
                risk_level=instruction.safety.risk_level,
            )
            instruction.policy.decision_id = policy.decision_id
            instruction.policy.matched_rules = policy.matched_rules
            self._trace(
                "policy",
                run,
                policy.model_dump(mode="json"),
                instruction_id=instruction.id,
                policy_decision_id=policy.decision_id,
                step=instruction.step,
            )
            if not policy.allowed and not policy.requires_approval:
                run.step = instruction.step
                evaluation = self.evaluation_source.evaluate(
                    run=run,
                    instruction=instruction,
                    policy_decision=policy,
                    hints=instruction.args,
                )
                _, decision, _ = self._run_convergence_scheduler_handoff(
                    run,
                    instruction=instruction,
                    evaluation=evaluation,
                    current_score=run.progress_score,
                    source="instruction_policy",
                )
                self._apply_scheduler_decision(run, decision)
                self.runtime.run_manager.save(run)
                return run

            result: SyscallResult | None = None
            if instruction.op in _SYSCALLS:
                result = self.runtime.syscall_router.dispatch(
                    SyscallCall(
                        run_id=run.run_id,
                        instruction_id=instruction.id,
                        name=_SYSCALLS[instruction.op],
                        input=instruction.args,
                        workspace=run.workspace,
                        mode=run.mode,
                        approval_granted=approve_pending,
                    ),
                    step=instruction.step,
                )
                approve_pending = False
                self._trace(
                    "observation",
                    run,
                    {
                        "success": result.success,
                        "summary": result.error or "syscall completed",
                        "result": result.model_dump(mode="json"),
                    },
                    instruction_id=instruction.id,
                    syscall_id=result.syscall_id,
                    policy_decision_id=result.policy_decision.decision_id,
                    step=instruction.step,
                )
                if result.requires_approval and not result.success:
                    run.pending_approval = PendingApproval(
                        instruction_id=instruction.id,
                        syscall_id=result.syscall_id,
                        reason_codes=result.policy_decision.reason_codes,
                        risk="high" if result.risk == "high" else "medium",
                    )
                    run.metadata["cursor"] = cursor
                    run.step = instruction.step
                    evaluation = self.evaluation_source.evaluate(
                        run=run,
                        instruction=instruction,
                        syscall_result=result,
                        hints=instruction.args,
                    )
                    _, decision, _ = self._run_convergence_scheduler_handoff(
                        run,
                        instruction=instruction,
                        evaluation=evaluation,
                        current_score=run.progress_score,
                        source="approval_required",
                        approval_required=True,
                    )
                    self._apply_scheduler_decision(run, decision)
                    self.runtime.run_manager.save(run)
                    return run
            elif instruction.op == "CTX.COMPILE":
                context = self._compile_context(run)
                self._trace(
                    "observation",
                    run,
                    {"success": True, "summary": "context compiled", "context": context},
                    instruction_id=instruction.id,
                    step=instruction.step,
                )
            else:
                self._trace(
                    "observation",
                    run,
                    {"success": True, "summary": f"kernel handled {instruction.op}"},
                    instruction_id=instruction.id,
                    step=instruction.step,
                )

            run.step = instruction.step
            cursor += 1
            run.metadata["cursor"] = cursor
            planned_score = min(1.0, cursor / len(plan))
            if result is None:
                run.progress_score = max(run.progress_score, planned_score)
            elif result.success:
                evidence_score = result.output.get("progress_score")
                run.progress_score = (
                    max(0.0, min(1.0, float(evidence_score)))
                    if isinstance(evidence_score, int | float) and not isinstance(evidence_score, bool)
                    else max(run.progress_score, planned_score)
                )

            if result is not None:
                evaluation = self.evaluation_source.evaluate(
                    run=run,
                    instruction=instruction,
                    syscall_result=result,
                    hints=instruction.args,
                )
                _, decision, _ = self._run_convergence_scheduler_handoff(
                    run,
                    instruction=instruction,
                    evaluation=evaluation,
                    current_score=run.progress_score,
                    source="syscall_result",
                    failure_fingerprint=result.error,
                )
                terminal = self._apply_scheduler_decision(run, decision)
                if terminal:
                    self.runtime.run_manager.save(run)
                    return run
                self._resume_after_nonterminal_decision(run, decision)
                self.runtime.run_manager.save(run)
                continue

            if instruction.op == "EVAL.APPLY":
                if instruction.args.get("acceptance_passed") is True:
                    run.metadata["acceptance_passed"] = True
                evaluation = self.evaluation_source.evaluate(
                    run=run,
                    instruction=instruction,
                    hints=instruction.args,
                )
                _, decision, _ = self._run_convergence_scheduler_handoff(
                    run,
                    instruction=instruction,
                    evaluation=evaluation,
                    current_score=run.progress_score,
                    source="evaluation_apply",
                )
                terminal = self._apply_scheduler_decision(run, decision)
                if terminal:
                    self.runtime.run_manager.save(run)
                    return run
                self._resume_after_nonterminal_decision(run, decision)

            if instruction.op == "PROGRESS.MEASURE":
                current_hint = instruction.args.get("current_score", run.progress_score)
                if isinstance(current_hint, int | float) and not isinstance(current_hint, bool):
                    run.progress_score = max(0.0, min(1.0, float(current_hint)))
                latest = run.metadata.get("latest_evaluation")
                evaluation = (
                    EvaluationResult.model_validate(latest)
                    if isinstance(latest, dict)
                    else self.evaluation_source.evaluate(
                        run=run,
                        instruction=instruction,
                        hints=instruction.args,
                    )
                )
                _, decision, _ = self._run_convergence_scheduler_handoff(
                    run,
                    instruction=instruction,
                    evaluation=evaluation,
                    current_score=run.progress_score,
                    source="progress_measure",
                )
                terminal = self._apply_scheduler_decision(run, decision)
                if terminal:
                    self.runtime.run_manager.save(run)
                    return run
                self._resume_after_nonterminal_decision(run, decision)

            if instruction.op == "LOOP.HALT":
                latest_payload = run.metadata.get("latest_evaluation")
                latest = (
                    EvaluationResult.model_validate(latest_payload)
                    if isinstance(latest_payload, dict)
                    else None
                )
                if latest is not None and (latest.failed or latest.blocked):
                    evaluation = latest.model_copy(update={"repairable": False})
                else:
                    accepted = run.metadata.get("acceptance_passed") is True
                    evaluation = self.evaluation_source.evaluate(
                        run=run,
                        instruction=instruction,
                        hints={
                            "goal_satisfied": accepted,
                            "failed": not accepted,
                            "score": run.progress_score,
                        },
                    )
                    if not accepted:
                        evaluation = evaluation.model_copy(
                            update={
                                "failure_type": "acceptance_not_met",
                                "reason_codes": ["acceptance.not_met"],
                            }
                        )
                convergence, decision, _ = self._run_convergence_scheduler_handoff(
                    run,
                    instruction=instruction,
                    evaluation=evaluation,
                    current_score=run.progress_score,
                    source="loop_halt",
                )
                self._apply_scheduler_decision(run, decision)
                self._trace(
                    "halt",
                    run,
                    convergence.halt.model_dump(mode="json"),
                    instruction_id=instruction.id,
                    step=instruction.step,
                )
                self.runtime.run_manager.save(run)
                self._propose_skill(run)
                return run
            self.runtime.run_manager.save(run)
        return run

    # ----- Phase 4: ACI / ALI integration (optional path) -----------------

    def submit_agent_command(
        self,
        command: AgentCommand,
        session: AgentLoopSession,
        *,
        aci_runner: CommandRunner | None = None,
        fsm: AgentLoopFSM | None = None,
    ) -> AgentCommandResult:
        """Submit an :class:`AgentCommand` through the ACI runner and drive the ALI session.

        Phase 4 minimal integration. The existing
        :meth:`run` / :meth:`resume` / convergence-handoff paths are
        untouched; this method is an optional entry point for
        callers that want to drive an :class:`AgentLoopSession`
        from a real :class:`AgentCommandResult`.

        Sequence:

        1. Run ``command`` through :class:`CommandRunner`, using the
           kernel runtime's policy engine so Policy OS stays the
           single source of truth (no bypass).
        2. Call :func:`consume_aci_result` to attach the result as
           an audit reference on the session and drive the FSM
           through the state-aware sequence (RUNNING / REPAIRING /
           REPLANNING / WAITING_APPROVAL / HALTED_*).
        3. Mirror the audit metadata (``trace_id``, ``syscall_id``,
           ``provider_id``, ``status``, ``success``, ``reason_codes``)
           onto the kernel ``run`` metadata so the existing kernel
           decision path can read the ACI verdict without
           re-running the policy engine.

        The runner never spawns a subprocess directly: it routes
        through ``runtime.syscall_router`` (when supplied via the
        runner config) or returns a structured policy-only verdict.
        ``dry_run`` ACI results do not produce side effects.

        Parameters
        ----------
        command:
            The :class:`AgentCommand` to submit. ``goal_id`` is used
            to attach the audit reference to ``session``.
        session:
            The :class:`AgentLoopSession` to drive. The caller is
            responsible for advancing the session through
            ``goal_submitted`` / ``command_submitted`` before invoking
            this method, matching the pre-condition that
            :func:`consume_aci_result` documents.
        aci_runner:
            Optional pre-built :class:`CommandRunner`. When ``None``,
            the kernel builds a default runner that uses
            ``runtime.policy_engine`` (and ``runtime.syscall_router``
            so dispatched commands route through the existing
            Syscall Router).
        fsm:
            Optional :class:`AgentLoopFSM` override. Defaults to the
            package-level :data:`DEFAULT_FSM`.

        Returns
        -------
        :class:`AgentCommandResult`
            The structured result that the runner produced. The same
            object is also attached to the session via the audit
            reference (consume_aci_result handles the attachment).

        Raises
        ------
        :class:`loopos.ali.errors.SessionClosedError`
            If the session is in a terminal state.
        :class:`loopos.ali.errors.InvalidTransitionError`
            If no event in the desired sequence is valid from the
            session's current state.
        """

        runner = aci_runner or self._default_aci_runner()
        result = runner.run(command)
        consume_aci_result(session, result, fsm=fsm)
        # Mirror the audit metadata onto the latest run record so the
        # existing kernel decision path can read the ACI verdict
        # without re-running the policy engine. This is the minimum
        # needed to expose trace_id / syscall_id / provider_id to the
        # kernel without replacing any existing convergence behavior.
        self._record_aci_outcome(result)
        return result

    def _default_aci_runner(self) -> CommandRunner:
        """Build a :class:`CommandRunner` pre-wired with the kernel runtime.

        Uses ``runtime.policy_engine`` so Policy OS stays the single
        source of truth, and ``runtime.syscall_router`` so dispatched
        commands route through the existing Syscall Router (no
        subprocess bypass).
        """

        return CommandRunner(
            policy_engine=self.runtime.policy_engine,
            syscall_router=self.runtime.syscall_router,
        )

    def _record_aci_outcome(self, result: AgentCommandResult) -> None:
        """Append a compact ACI verdict to the most recent run's metadata.

        The kernel keeps a single ``aci_outcomes`` list under
        ``run.metadata`` so the existing convergence / decision path
        can read trace_id / syscall_id / provider_id / status /
        reason_codes without changing the convergence contract.
        """

        latest = self._latest_run_record()
        if latest is None:
            return
        outcomes = latest.metadata.setdefault("aci_outcomes", [])
        outcomes.append(
            {
                "command_id": result.command_id,
                "goal_id": result.goal_id,
                "status": result.status,
                "success": result.success,
                "reason_codes": list(result.reason_codes),
                "trace_id": result.trace_id,
                "syscall_id": result.metadata.get("syscall_id"),
                "provider_id": (
                    result.resolved_provider.provider_id
                    if result.resolved_provider is not None
                    else None
                ),
                "blocked_reason": result.blocked_reason,
                "requires_approval": result.requires_approval,
                "dry_run": result.dry_run,
            }
        )
        # Persist so a subsequent load() can read the appended outcome.
        # The kernel never overwrites existing metadata keys, so this
        # is additive only.
        try:
            self.runtime.run_manager.save(latest)
        except (AttributeError, OSError, ValueError):
            # Best-effort persistence: if the manager does not support
            # save (e.g. in dry-run boot paths) the in-memory outcome
            # is still observable via ``latest.metadata`` until the
            # caller re-loads.
            pass

    def _latest_run_record(self) -> RunRecord | None:
        """Return the most recently loaded run record, if any.

        ``KernelLoopEngine`` does not own a ``current_run`` pointer;
        the integration uses the trace store as the source of truth
        and reads back the latest run for which a ``run`` event was
        emitted. Returns ``None`` when no run has been started yet
        (e.g. when :meth:`submit_agent_command` is exercised in
        isolation, before :meth:`run`).
        """

        run_events = [
            event for event in self.runtime.trace_store.list()
            if event.kind == "run"
        ]
        if not run_events:
            return None
        run_id = run_events[-1].run_id
        try:
            return self.runtime.run_manager.load(run_id)
        except (KeyError, FileNotFoundError, ValueError):
            return None

    def _run_convergence_scheduler_handoff(
        self,
        run: RunRecord,
        *,
        instruction: AILInstruction,
        evaluation: EvaluationResult,
        current_score: float,
        source: str,
        approval_required: bool = False,
        failure_fingerprint: str | None = None,
    ) -> tuple[LoopDecision, ScheduleDecision, ProgressDelta]:
        _, progress = update_progress_accumulator(
            run=run,
            evaluation=evaluation,
            instruction=instruction,
            current_score=current_score,
            failure_fingerprint=failure_fingerprint,
        )
        run.metadata["latest_evaluation"] = evaluation.model_dump(mode="json")
        run.metadata["latest_progress"] = progress.model_dump(mode="json")
        self._trace(
            "evaluation",
            run,
            evaluation.model_dump(mode="json"),
            instruction_id=instruction.id,
            step=instruction.step,
        )
        self._trace(
            "progress",
            run,
            progress.model_dump(mode="json"),
            instruction_id=instruction.id,
            step=instruction.step,
        )
        convergence = self.convergence.decide(
            evaluation,
            progress,
            approval_required=approval_required,
        )
        self._trace(
            "decision",
            run,
            convergence.model_dump(mode="json"),
            instruction_id=instruction.id,
            step=instruction.step,
        )
        scheduler_input = self._scheduler_input_from_convergence(run, convergence)
        decision = self.scheduler.decide(scheduler_input)
        self._trace(
            "decision",
            run,
            {
                "source": "convergence_to_scheduler",
                "runtime_source": source,
                "convergence_action": convergence.action,
                "convergence_reason_code": convergence.reason_code,
                "scheduler_input": scheduler_input.model_dump(mode="json"),
                "scheduler_decision": decision.model_dump(mode="json"),
                "evaluation": evaluation.model_dump(mode="json"),
                "progress": progress.model_dump(mode="json"),
            },
            instruction_id=instruction.id,
            step=instruction.step,
        )
        return convergence, decision, progress

    def _apply_scheduler_decision(
        self,
        run: RunRecord,
        decision: ScheduleDecision,
    ) -> bool:
        self.state_machine.apply_schedule(run, decision)
        self._trace_transition(run, decision.reason_code)
        return decision.action.startswith("halt_") or decision.action == "wait_approval"

    def _resume_after_nonterminal_decision(
        self,
        run: RunRecord,
        decision: ScheduleDecision,
    ) -> None:
        if decision.action in {"repair", "replan"}:
            self._transition(
                run,
                "running",
                "EXECUTING",
                reason=f"{decision.reason_code}.resume",
            )

    def _scheduler_input_from_convergence(
        self,
        run: RunRecord,
        convergence: LoopDecision,
    ) -> SchedulerInput:
        """Translate a convergence ``LoopDecision`` into a ``SchedulerInput``.

        The scheduler remains the final authority (it preserves the fixed
        precedence chain), but the convergence engine's judgment now flows into
        the scheduler as structured input signals instead of being dropped:

        - halt_success / halt_failure / halt_blocked -> evaluation_success/
          evaluation_failed signal so the scheduler's halt path fires
        - repair -> repairable=True (scheduler may still overrule via precedence)
        - replan -> no_progress=True (scheduler may still overrule via precedence)
        - ask_user -> approval_required=True (maps to wait_approval precedence)
        - wait_approval -> approval_required=True (kept as wait_approval)
        - continue -> baseline continue signal
        """

        action = convergence.action
        step = run.step
        max_steps = run.max_steps

        if action in _CONVERGENCE_HALT_ACTIONS:
            if action == "halt_success":
                return SchedulerInput(
                    step=step,
                    max_steps=max_steps,
                    evaluation_success=True,
                )
            if action == "halt_failure":
                return SchedulerInput(
                    step=step,
                    max_steps=max_steps,
                    evaluation_failed=True,
                )
            # halt_blocked: surface as a policy-blocked halt so the scheduler's
            # halt_blocked precedence path is exercised.
            return SchedulerInput(
                step=step,
                max_steps=max_steps,
                policy_allowed=False,
            )

        if action in _CONVERGENCE_REPAIR_ACTIONS:
            return SchedulerInput(
                step=step,
                max_steps=max_steps,
                evaluation_failed=True,
                repairable=True,
            )

        if action in _CONVERGENCE_REPLAN_ACTIONS:
            return SchedulerInput(
                step=step,
                max_steps=max_steps,
                no_progress=True,
            )

        if action in _CONVERGENCE_ASK_ACTIONS or action in _CONVERGENCE_WAIT_ACTIONS:
            return SchedulerInput(
                step=step,
                max_steps=max_steps,
                approval_required=True,
            )

        # continue (and any future unknown action) keeps the baseline continue
        # behavior so the scheduler's default continue path applies.
        return SchedulerInput(step=step, max_steps=max_steps)

    def _compile_context(self, run: RunRecord) -> dict[str, Any]:
        if self.memory_repository is None:
            return {"goal_summary": run.goal, "memories": [], "skills": []}
        from loopos.core.state import LoopState

        context = self.context_compiler.compile(
            LoopState(
                run_id=run.run_id,
                goal=run.goal,
                status="running",
                step_index=run.step,
                progress_score=run.progress_score,
            ),
            memories=self.memory_repository.retrieve(limit=30),
            skills=self.memory_repository.skills.list(),
            available_tools=[spec.name for spec in self.runtime.syscall_router.registry.list()],
        )
        return context.model_dump(mode="json")

    def _propose_skill(self, run: RunRecord) -> None:
        if self.memory_repository is None:
            return
        events = self.runtime.trace_store.list(run.run_id)
        try:
            proposal = SkillExtractor().extract(
                run,
                events,
                name=f"run-{run.run_id[:8]}",
                description=f"Structured actions for: {run.goal}",
                trigger_tags=["kernel", "successful-run"],
            )
        except ValueError:
            return
        self.memory_repository.propose_skill(proposal)
        self._trace("skill", run, proposal.model_dump(mode="json"), step=run.step)

    def _transition(
        self,
        run: RunRecord,
        status: KernelRunStatus,
        phase: KernelPhase,
        *,
        reason: str | None = None,
    ) -> None:
        before = run.model_dump(mode="json")
        self.transitions.apply(run, status, phase, reason=reason)
        self.runtime.trace_store.append(
            "transition",
            run.run_id,
            run.step,
            {"before": before, "after": run.model_dump(mode="json"), "reason": reason},
            instruction_id=run.current_instruction_id,
        )

    def _trace_transition(self, run: RunRecord, reason: str) -> None:
        self._trace(
            "transition",
            run,
            {"after": run.model_dump(mode="json"), "reason": reason},
            instruction_id=run.current_instruction_id,
        )

    def _trace(
        self,
        kind: TraceKind,
        run: RunRecord,
        payload: dict[str, Any],
        *,
        instruction_id: str | None = None,
        syscall_id: str | None = None,
        policy_decision_id: str | None = None,
        step: int | None = None,
    ) -> None:
        event = self.runtime.trace_store.append(
            kind,
            run.run_id,
            run.step if step is None else step,
            payload,
            instruction_id=instruction_id,
            syscall_id=syscall_id,
            policy_decision_id=policy_decision_id,
        )
        run.trace_event_ids.append(event.id)
