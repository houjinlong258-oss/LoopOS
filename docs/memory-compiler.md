# Memory Compiler

The MemoryCompiler builds the smallest useful role-specific context packet.
Every agent should not reread every trace, document, and failure.

Implemented package: `loopos.project_memory.compiler`.

## Inputs

- target role
- goal summary
- current gap
- token budget
- compressed objective, decision, failure, test, and delivery memory

## Output

`ContextPacket` contains:

- target role
- goal summary
- current gap
- relevant decisions
- relevant failures
- relevant tests
- relevant files
- avoid repeating
- expected output
- token budget
- estimated tokens
- token budget ledger

The compiler gives repairers failure history, gives optimizers known bad
paths, and avoids broadcasting irrelevant context to every role.
