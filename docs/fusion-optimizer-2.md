# Fusion Optimizer 2.0

Fusion Optimizer 2.0 ranks next-iteration plans by quality gain and token cost.

The result now includes:

- `expected_quality_gain`;
- `token_cost_estimate`;
- `utility_score`.

Mad Dog findings, review findings, prior repair plans, and token economy
signals all shape the next plan. Fusion remains a pure optimizer: it does not
write files, call providers, or execute tools.
