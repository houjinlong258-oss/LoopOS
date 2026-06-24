# Communication Distance Optimizer

The Communication Distance Optimizer routes each signal directly to the roles
that need it.

Implemented package: `loopos.agent_language.router`.

## Metrics

- `communication_distance`
- `broadcast_count`
- `recipient_count`
- `token_cost_estimate`
- `redundant_context_avoided`

## Default Routing

| Signal | Recipients |
|--------|------------|
| `review.finding` | `repairer`, `optimizer` |
| `test.failed` | `repairer`, `optimizer` |
| `fake_convergence.detected` | `loop_controller`, `delivery_evaluator` |
| `memory.context_compiled` | the role named in `target_role` |

This prevents supervisor-style re-narration and avoids broad context
broadcasts.
