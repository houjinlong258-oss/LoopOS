# Real Executor Runtime

`loopos.executors` provides a sandboxed execution path for real project
training work. It can:

- apply unified diffs inside a sandboxed repo;
- run explicit argv commands with timeout;
- capture exit code, stdout, stderr, and duration;
- store raw and compacted artifacts separately;
- turn failed test logs into `ReviewFinding` records;
- expose changed files and diff summaries.

The default `LoopEngine` path remains simulated. Real execution is enabled only
when the caller passes `real_executor=True` in code or:

```bash
python -m loopos.cli.app loop run "Fix failing tests" \
  --real-executor --no-dry-run --sandbox --repo-path <temp-repo> --json
```

The real executor never requires network access. Timeout state suppresses
follow-up commands so a runaway command cannot continue the sequence.
