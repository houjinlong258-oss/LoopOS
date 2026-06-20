"""Traceable and resumable LoopOS Kernel engine."""

from __future__ import annotations

from typing import Any

from loopos.agents.intent_compiler import DeterministicIntentCompiler
from loopos.agents.skill_extractor import SkillExtractor
from loopos.ail.models import AILInstruction
from loopos.context import ContextCompiler
from loopos.convergence import ConvergenceEngine, EvaluationResult, ProgressDelta
from loopos.kernel.boot import KernelRuntime
from loopos.kernel.models import PendingApproval, RunRecord, RunSpec
from loopos.kernel.scheduler import LoopScheduler, SchedulerInput
from loopos.kernel.state_machine import KernelStateMachine
from loopos.kernel.transition import TransitionEngine
from loopos.memory.repository import MemoryRepository
from loopos.syscalls import SyscallCall, SyscallResult

_SYSCALLS = {
    "TERM.EXEC": "terminal.exec",
    "FILE.READ": "file.read",
    "FILE.WRITE": "file.write",
    "GIT.STATUS": "git.status",
    "GIT.DIFF": "git.diff",
}


class KernelLoopEngine:
    def __init__(
        self,
        runtime: KernelRuntime,
        *,
        intent_compiler: DeterministicIntentCompiler | None = None,
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
                {"op": instruction.op, "args": instruction.args, "instruction": instruction.model_dump(mode="json")},
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
                self._transition(run, "blocked", "HALTED", reason="instruction policy denied")
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
                    self._transition(run, "waiting_approval", "WAITING_APPROVAL")
                    self.runtime.run_manager.save(run)
                    return run
                if not result.success:
                    status = "blocked" if result.risk == "blocked" else "failed"
                    self._transition(run, status, "HALTED", reason=result.error or "syscall failed")  # type: ignore[arg-type]
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
            run.progress_score = min(1.0, cursor / len(plan))
            if instruction.op == "EVAL.APPLY":
                self._trace(
                    "evaluation",
                    run,
                    EvaluationResult(
                        goal_satisfied=bool(instruction.args.get("goal_satisfied", False)),
                        score=run.progress_score,
                        reason_codes=["evaluation.goal_checked"],
                    ).model_dump(mode="json"),
                    instruction_id=instruction.id,
                    step=instruction.step,
                )
            if instruction.op == "PROGRESS.MEASURE":
                previous = float(instruction.args.get("previous_score", 0.0))
                current = float(instruction.args.get("current_score", run.progress_score))
                self._trace(
                    "progress",
                    run,
                    ProgressDelta(
                        previous_score=previous,
                        current_score=current,
                        delta=current - previous,
                    ).model_dump(mode="json"),
                    instruction_id=instruction.id,
                    step=instruction.step,
                )
            if instruction.op == "LOOP.HALT":
                convergence = self.convergence.decide(
                    EvaluationResult(
                        goal_satisfied=True,
                        score=run.progress_score,
                        reason_codes=["evaluation.goal_satisfied"],
                    ),
                    ProgressDelta(
                        previous_score=max(0.0, run.progress_score - 0.1),
                        current_score=run.progress_score,
                        delta=0.1,
                    ),
                )
                self._trace(
                    "decision",
                    run,
                    convergence.model_dump(mode="json"),
                    instruction_id=instruction.id,
                    step=instruction.step,
                )
                decision = self.scheduler.decide(
                    SchedulerInput(
                        step=run.step,
                        max_steps=run.max_steps,
                        evaluation_success=True,
                    )
                )
                self.state_machine.apply_schedule(run, decision)
                self._trace_transition(run, decision.reason_code)
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
        status: Any,
        phase: Any,
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
        kind: Any,
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
