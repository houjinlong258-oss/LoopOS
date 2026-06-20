# AI-ISA

AI-ISA is LoopOS's typed instruction set. Runtime logic should consume these objects instead of free-form LLM text.

## Operations

- `PLAN`
- `CALL_TOOL`
- `EXEC_TERMINAL`
- `OBSERVE`
- `EVALUATE`
- `UPDATE_STATE`
- `STORE_MEMORY`
- `EXTRACT_SKILL`
- `TERMINATE`

## Instruction Fields

- `id`
- `op`
- `created_at`
- `reason_code`
- `args`
- `safety`
- `expected_observation`
- `metadata`

## Safety Fields

- `risk_level`: `low`, `medium`, `high`, or `blocked`
- `requires_approval`
- `allowed_paths`
- `blocked_patterns`

## Expected Observation

- `success_criteria`
- `failure_criteria`
- `timeout_seconds`

## Parsing

Use:

```python
from loopos.core.isa import parse_instruction, instruction_to_json

instruction = parse_instruction(raw)
payload = instruction_to_json(instruction)
```

The MVP validates operation-specific requirements, such as `EXEC_TERMINAL` requiring `args.cmd` and `TERMINATE` requiring `args.reason`.
