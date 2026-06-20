# Agent Internal Language

AIL is the canonical structured protocol between LoopOS kernel components. Kernel operations use dotted names such as `GOAL.SET`, `CTX.COMPILE`, `TERM.EXEC`, `FILE.WRITE`, `EVAL.SCORE`, and `LOOP.HALT`.

An instruction identifies its run and step, includes structured reason and safety evidence, declares expected observations, and links the Policy OS decision used for execution. Legacy AI-ISA names remain supported at the codec boundary and are normalized before scheduling.

AIL contains no hidden chain-of-thought. Reasons are concise codes, evidence references, and confidence values suitable for audit and replay.
