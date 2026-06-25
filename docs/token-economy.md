# Token Economy

`loopos.token_economy` records per-iteration token budgets:

- input tokens;
- output tokens;
- compiled context tokens;
- saved tokens;
- budget and over-budget status.

The ledger feeds optimization: large context packets without recorded savings
raise token-waste findings. `loopos.output_compaction` keeps exit code and
failure lines while trimming long stdout/stderr logs.

The goal is not perfect tokenizer accounting. The goal is measurable pressure
against repeated context dumping and oversized tool schemas.
