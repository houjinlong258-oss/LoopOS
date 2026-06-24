# Mad Dog Fake-Convergence Attacker

Mad Dog is not a security blocker. Mad Dog is an adversarial evaluator that
attacks fake completion, missing evidence, weak design, brittle flow,
implementation gaps, goal mismatch, token waste, communication noise, release
gaps, and security risk.

Implemented package: `loopos.fusion_optimizer.mad_dog`.

## Finding Categories

- `fake_completion`
- `fake_convergence`
- `missing_test`
- `weak_design`
- `brittle_flow`
- `user_goal_mismatch`
- `implementation_gap`
- `documentation_gap`
- `regression_risk`
- `release_gap`
- `token_waste`
- `communication_noise`
- `security_risk`

## Delivery Blocking

A Mad Dog finding can block delivery only when it is evidence-backed.
Findings without evidence are advisory signals for repair and optimization.

`ConvergenceEngine` and `DeliveryEngine` consume fake-convergence evidence so
the loop cannot mark a simulated-only run as a clean real delivery.
