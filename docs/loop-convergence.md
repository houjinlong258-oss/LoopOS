# Loop Convergence Kernel

Convergence uses structured `EvaluationResult`, `ProgressDelta`, `LoopDecision`, and `HaltCondition` models. The deterministic engine can continue, repair, replan, ask the user, wait for approval, or halt with success, failure, or blocked status.

Every evaluation, progress measurement, decision, and halt condition is written to the trace. Model text cannot directly set process status; the Scheduler and TransitionEngine enforce the lifecycle and max-step bound.
