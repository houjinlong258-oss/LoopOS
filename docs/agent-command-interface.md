# Agent Command Interface

ACI is the Agent Command Interface: an agent-native command boundary where every command is bound to
a goal, policy decision, capability boundary, structured observation, trace, evaluation, progress,
and convergence feedback.

## CLI versus ACI

```text
CLI: command -> stdout/stderr -> exit code

ACI: goal -> command intent -> policy and capability checks -> approval
   -> syscall -> structured observation -> evaluation -> progress
   -> convergence -> trace and review artifact
```

ACI does not replace the terminal CLI. It defines the typed contract beneath terminal, gateway, MCP,
and future daemon entry points.

## Command draft

```yaml
aci_command:
  id: cmd_01
  goal_id: goal_123
  kind: terminal.exec
  intent: run_tests
  command: "pytest -q -m 'not slow'"
  cwd: "."
  purpose: "verify non-slow tests after kernel changes"
  expected_observation: test_result
  risk_hint: low
  requires:
    filesystem_read: true
    filesystem_write: false
    network: false
    database: false
  constraints:
    timeout_seconds: 120
    no_destructive_actions: true
  approval:
    required: false
  trace:
    required: true
```

## Result draft

```yaml
aci_result:
  command_id: cmd_01
  status: completed
  success: true
  exit_code: 0
  observation_type: test_result
  policy_decision: {action: allow, safety_level: L1}
  evaluation: {goal_satisfied: true, confidence: 0.92}
  progress: {previous_score: 0.72, current_score: 0.88}
  convergence: {action: continue}
  trace_id: trace_abc
```

## Agent tool contract

An agent tool is not a function call. It is a governed capability. Every tool declares its input and
output schema, side effects, default and dynamic risk, approval conditions, trace requirement,
rollback availability, and observation type.

```yaml
tool:
  name: terminal.exec
  capability: terminal_execution
  side_effects: {filesystem_write: possible, network: false}
  risk: {default: medium, dynamic_policy: true}
  approval: {required_when: ["safety_level >= L4"]}
  trace: {required: true}
  rollback: {available: false}
  observation: {type: command_result}
```

Current AIL, `SyscallCall`, `PolicyDecision`, and `TraceEvent` models are the v0.1 implementation
substrate. The draft does not claim a separate ACI network protocol exists yet.
