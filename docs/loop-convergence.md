# Loop Convergence

Every Kernel iteration records an observation, `EvaluationResult`, `ProgressDelta`, and
`LoopDecision`. Evidence includes acceptance-criterion state, failure type, regression, score delta,
no-progress count, repeated failure count, repeated action count, and trace references.

The deterministic outcomes are `continue`, `repair`, `replan`, `ask_user`, `wait_approval`,
`halt_success`, `halt_failure`, and `halt_blocked`. Regression prefers repair when possible; repeated
actions or no progress trigger replan; repeated unrecoverable failures halt. Database tasks cannot
converge successfully without verified backup, shadow validation, rollback evidence, and no sensitive
trace leakage.
