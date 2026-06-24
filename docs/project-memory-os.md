# Project Memory OS

Memory is not chat history. Memory is compressed project training signal.

Project Memory OS exists to reduce repeated context, repeated failures, and
token waste during the Project Training Loop.

Implemented package: `loopos.project_memory`.

## Layers

- `WorkingMemory`
- `ObjectiveMemory`
- `DecisionMemory`
- `FailureMemory`
- `TestMemory`
- `CodeMapMemory`
- `ProcedureMemory`
- `AgentMemory`
- `DeliveryMemory`

## Failure Memory

Failure Memory is P0. It records:

- failed attempt
- failure reason
- related files
- related tests
- why not to repeat it
- what to do next time

The MemoryCompiler uses `FailureMemory` to warn repairer and optimizer roles
before they repeat a known bad path.
