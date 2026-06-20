"""State-machine loop engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from loopos.core.isa import Instruction, validate_instruction_for_mvp
from loopos.core.context import ContextCompiler
from loopos.core.policy import DeterministicDemoPolicy
from loopos.core.state import Evaluation, LoopState, Observation
from loopos.llm.providers import LLMProvider
from loopos.memory.event_log import EventLog
from loopos.memory.extractor import MemoryProposalExtractor
from loopos.memory.pre_action_gate import PreActionGate
from loopos.memory.repository import MemoryRepository
from loopos.memory.state_store import StateStore


class PolicyProtocol(Protocol):
    def next_instruction(self, state: LoopState) -> Instruction:
        """Return the next instruction for the current state."""


class ExecutorProtocol(Protocol):
    def execute(self, instruction: Instruction) -> Observation:
        """Execute an instruction and return an observation."""


class EvaluatorProtocol(Protocol):
    def evaluate(
        self,
        state: LoopState,
        instruction: Instruction,
        observation: Observation,
    ) -> Evaluation:
        """Evaluate an observation and decide the next state transition."""


class MockInstructionExecutor:
    """Mock executor used until real tool execution is requested."""

    def execute(self, instruction: Instruction) -> Observation:
        if instruction.op == "EXEC_TERMINAL":
            cmd = str(instruction.args.get("cmd", ""))
            return Observation(
                success=True,
                summary=f"mock executed: {cmd}",
                stdout="hello\n" if "echo hello" in cmd.lower() else "",
                command=cmd,
                cwd=str(instruction.args.get("cwd", ".")),
                return_code=0,
            )
        if instruction.op == "TERMINATE":
            return Observation(
                success=True,
                summary=str(instruction.args.get("reason", "terminated")),
            )
        return Observation(success=True, summary=f"mock handled {instruction.op}")


class SimpleEvaluator:
    """Small deterministic evaluator for MVP tests."""

    def evaluate(
        self,
        state: LoopState,
        instruction: Instruction,
        observation: Observation,
    ) -> Evaluation:
        if observation.error == "blocked" or observation.data.get("gate_action") == "block":
            return Evaluation(status="blocked", summary=observation.summary)
        if instruction.op == "TERMINATE":
            return Evaluation(
                status="succeeded" if observation.success else "failed",
                score_delta=1.0,
                summary=observation.summary,
            )
        if not observation.success:
            return Evaluation(status="failed", summary=observation.summary)
        return Evaluation(status="continue", score_delta=0.5, summary=observation.summary)


class LoopEngine:
    """Bounded, deterministic state machine for LoopOS runs."""

    def __init__(
        self,
        *,
        policy: PolicyProtocol | None = None,
        executor: ExecutorProtocol | None = None,
        evaluator: EvaluatorProtocol | None = None,
        event_log: EventLog | None = None,
        state_store: StateStore | None = None,
        pre_action_gate: PreActionGate | None = None,
        memory_repository: MemoryRepository | None = None,
        context_compiler: ContextCompiler | None = None,
        proposal_extractor: MemoryProposalExtractor | None = None,
        propose_memory: bool = False,
    ) -> None:
        self.policy = policy or DeterministicDemoPolicy()
        self.executor = executor or MockInstructionExecutor()
        self.evaluator = evaluator or SimpleEvaluator()
        self.event_log = event_log
        self.state_store = state_store
        self.pre_action_gate = pre_action_gate
        self.memory_repository = memory_repository
        self.context_compiler = context_compiler or ContextCompiler()
        self.proposal_extractor = proposal_extractor
        self.propose_memory = propose_memory

    @classmethod
    def with_local_stores(
        cls,
        base_dir: str | Path = ".loopos",
        *,
        memory_repository: MemoryRepository | None = None,
        propose_memory: bool = False,
        llm_provider: LLMProvider | None = None,
    ) -> "LoopEngine":
        repo = memory_repository or MemoryRepository(base_dir)
        base = Path(base_dir)
        memories = repo.retrieve(limit=20)
        skills = repo.skills.list()
        return cls(
            event_log=repo.events if memory_repository is not None else EventLog(base / "events.jsonl"),
            state_store=repo.states if memory_repository is not None else StateStore(base / "runs"),
            pre_action_gate=PreActionGate(events=repo.events.list(), memories=memories, skills=skills),
            memory_repository=repo,
            proposal_extractor=MemoryProposalExtractor(llm_provider) if propose_memory else None,
            propose_memory=propose_memory,
        )

    def run(self, goal: str, *, max_steps: int = 5, timeout_seconds: int | None = None) -> LoopState:
        if max_steps <= 0:
            raise ValueError("max_steps must be positive")

        state = LoopState(goal=goal, status="running")
        self.context_compiler.compile(
            state,
            memories=self.memory_repository.retrieve(limit=30) if self.memory_repository else [],
            skills=self.memory_repository.skills.list() if self.memory_repository else [],
        )
        self._append("run_started", state, {"goal": goal, "timeout_seconds": timeout_seconds})
        self._save(state)

        for _ in range(max_steps):
            instruction = self.policy.next_instruction(state)
            self._append("instruction_planned", state, instruction.model_dump(mode="json"))

            issues = validate_instruction_for_mvp(instruction)
            if issues:
                observation = Observation(
                    success=False,
                    summary="instruction validation failed",
                    error="; ".join(issues),
                )
            else:
                gate_decision = (
                    self.pre_action_gate.before(instruction) if self.pre_action_gate else None
                )
                if gate_decision and gate_decision.action == "block":
                    observation = Observation(
                        success=False,
                        summary="pre-action gate blocked instruction",
                        error="blocked",
                        data={
                            "gate_action": gate_decision.action,
                            "reasons": gate_decision.reasons,
                        },
                    )
                else:
                    observation = self.executor.execute(instruction)
                    if gate_decision and gate_decision.action != "allow":
                        observation.data["gate_action"] = gate_decision.action
                        observation.data["gate_reasons"] = gate_decision.reasons

            evaluation = self.evaluator.evaluate(state, instruction, observation)
            state.apply(instruction, observation, evaluation)
            self._append("observation", state, observation.model_dump(mode="json"))
            self._append("evaluation", state, evaluation.model_dump(mode="json"))
            self._save(state)
            self._maybe_propose_memory(state.run_id)

            if state.is_terminal:
                self._append("run_finished", state, {"status": state.status})
                return state

        state.status = "failed"
        state.errors.append("max_steps exceeded")
        self._append("run_finished", state, {"status": state.status, "reason": "max_steps exceeded"})
        self._save(state)
        return state

    def _append(self, event_type: str, state: LoopState, payload: dict[str, Any]) -> None:
        if self.event_log is not None:
            event = self.event_log.append(event_type, state.run_id, state.step_index, payload)
            if self.memory_repository is not None:
                self.memory_repository.index.upsert_event(event)

    def _save(self, state: LoopState) -> None:
        if self.memory_repository is not None:
            self.memory_repository.save_state(state)
        elif self.state_store is not None:
            self.state_store.save(state)

    def _maybe_propose_memory(self, run_id: str) -> None:
        if not self.propose_memory or self.memory_repository is None or self.proposal_extractor is None:
            return
        events = self.memory_repository.events.list(run_id)
        proposals, errors = self.proposal_extractor.extract(
            run_id=run_id,
            events=events,
            user_profile=self.memory_repository.get_profile(),
        )
        for proposal in proposals:
            self.memory_repository.propose(proposal)
        for error in errors:
            self.memory_repository.events.append(
                "memory_proposal_error",
                run_id,
                len(events),
                {"error": error},
            )
