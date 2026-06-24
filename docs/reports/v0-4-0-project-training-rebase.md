# LoopOS v0.4.0 Project Training Rebase Report

Date: 2026-06-24

## 1. Product Rebase

LoopOS is now positioned as a Project Training Runtime. The first screen is
Goal -> Plan -> Build -> Test -> Review -> Repair -> Optimize -> Repeat ->
Deliver. Safety remains real, but it is an action boundary instead of the
product center.

## 2. Training Analogy

Project objective maps to training objective. Project loss and goal gap map to
loss. Plan/build/test/review maps to forward pass plus evaluation. Findings
map to gradient signals. Fusion Optimizer maps to optimizer. Iterations map to
epochs. ProjectCheckpoint maps to checkpoint. Delivery maps to convergence.

## 3. LoopEngine Data Flow

`LoopEngine` normalizes a goal, generates success criteria, creates a plan,
builds, tests, reviews, repairs, optimizes, scores quality, computes loss,
saves a checkpoint, and either repeats or delivers. Failed tests become
ReviewFinding records. Findings become RepairPlan records. Repair plans affect
the next PlanCandidate.

## 4. Simulation Honesty

The default v0.4.0 builder and tester are simulated. `BuildResult` and
`TestResult` expose `status="simulated"` and
`source="loopos_v0_4_simulated_adapter"`. Future real adapters implement the
interfaces in `loopos.loop_engine.interfaces`.

## 5. LAIL

`loopos.agent_language` implements AgentMessage, roles, signals, compact codec,
SignalRouter, CommunicationDistanceOptimizer, trace, translator, and MCP
adapter. LAIL cannot embed syscall, shell, network, database, file mutation,
or release fields.

## 6. Communication Distance

`review.finding` and `test.failed` route directly to `repairer` and
`optimizer`. `fake_convergence.detected` routes directly to `loop_controller`
and `delivery_evaluator`. Metrics record distance, recipients, token estimate,
broadcast count, and redundant context avoided.

## 7. Project Memory

`loopos.project_memory` implements Working, Objective, Decision, Failure,
Test, CodeMap, Procedure, Agent, and Delivery memory. FailureMemory records the
attempt, reason, related files/tests, avoid-repeating rule, and next action.

## 8. Memory Compiler

`MemoryCompiler` emits role-specific `ContextPacket` records with relevant
decisions, failures, tests, files, avoid-repeating rules, expected output, and
token ledger. Repairer and optimizer roles receive failure context without
broadcasting full history.

## 9. Loss / Gap

`ProjectLoss` records unsatisfied required criteria, blocking findings, no
improvement, fake convergence, and `GoalGap`. `ConvergenceEngine` uses these
signals to continue, deliver, or exhaust the iteration budget.

## 10. Fusion Optimizer

`FusionOptimizer` recommends the next best plan from candidates and findings.
The old `fusion_router` remains intact for v0.3 compatibility.

## 11. Mad Dog

Mad Dog is now a fake-convergence attacker. It covers fake completion, fake
convergence, missing tests, weak design, brittle flow, goal mismatch,
implementation gaps, documentation gaps, regression risk, release gaps, token
waste, communication noise, and security risk.

## 12. Safety Boundary

Policy OS, Syscall Router, approval, Memory Governance, Data Guard, and Trace
remain at the real action boundary. No new safety gate was added to planning,
imagination, review, LAIL routing, or optimization.

## 13. Readiness And Tests

The readiness script now checks Project Training Runtime positioning, LoopEngine
data flow, LAIL, Project Memory, MemoryCompiler, Communication Distance,
simulation labels, Fusion Optimizer, Mad Dog, CLI loop commands, and the final
report.

Validation run on 2026-06-24:

| Check | Result |
|-------|--------|
| `python -m pytest -m "not slow" -q` | pass |
| `python -m pytest -m "slow" -q` | pass |
| `python -m ruff check .` | pass |
| `python -m mypy loopos tests` | pass, 481 source files |
| `python scripts/v0_2_readiness_check.py --json` | pass, hard_fail_count=0 |
| `python scripts/v0_3_readiness_check.py --json` | pass, hard_fail_count=0 |
| `python scripts/v0_4_readiness_check.py --json` | pass, 43/43 checks |
| `python scripts/anti_bloat_check.py --json` | hard_fail_count=0, warning_count=5 |
| `python rc_audit_cli_smoke.py` | pass, all CLI surfaces OK |

Anti-bloat warnings are non-blocking and reflect known repository size / paired
test naming heuristics: module-count growth, large existing CLI/deep-smoke
files, and three CLI command files whose tests live in shared v0.4 CLI tests
instead of same-named paired files.

## 14. Current Limits

The default build/test/review adapters are still simulated. Cross-process loop
state persistence is minimal. Real provider-backed planners/builders/testers
remain v0.5 work. The working tree is not clean because the v0.4 rebase files
are present as local modifications/untracked files and have not been committed.

## 15. v0.5 Recommendations

- Add real executor adapters behind the v0.4 interfaces.
- Persist ProjectCheckpoint records to disk.
- Feed Project Memory from real traces.
- Add resumable loop runs.
- Add token-aware context compilation to real provider calls.
