# LAIL Full Protocol

LoopOS uses two compatible LAIL surfaces:

- `loopos.lail`: compact training-log signals written to run artifacts.
- `loopos.agent_language`: role-addressed internal optimization messages.

The role-addressed protocol routes signals directly to the roles that need
them. Examples:

| Signal | Recipients |
| --- | --- |
| `test.failed` | repairer, optimizer |
| `review.finding` | repairer, optimizer |
| `fake_convergence.detected` | loop controller, delivery evaluator |
| `computer.observed` | visual tester, UI reviewer |
| `token.budget_recorded` | loop controller, optimizer |

`AgentMessage` refuses executable payload fields such as `syscall`, `cmd`,
`shell`, `file_mutation`, and `network_call`. LAIL can propose and route
signals; it cannot execute side effects.
