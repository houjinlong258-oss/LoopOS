# Mock Model Call

A 60-second walkthrough that exercises the v0.3 governed Provider
Runtime with the mock provider, which never touches the network.

## Goal

Send a prompt through the governed Provider Runtime, get a
deterministic mock response, and confirm the budget / secret /
live-call guards are all in place.

## Command

```bash
python -m loopos.cli.app model-call --provider mock --prompt "Say LoopOS is ready." --json
```

The prompt can be a literal string (`--prompt "..."`) or a path
to a text file. To pass a longer prompt, write it to a file
first and pass the path:

```bash
echo "Summarise the Quickstart section in one sentence." > /tmp/prompt.txt
python -m loopos.cli.app model-call --provider mock --prompt /tmp/prompt.txt --json
```

## Expected output (abridged)

```json
{
  "status": "completed",
  "provider_id": "mock",
  "model_id": "mock-model",
  "content": "...",
  "reason_codes": [],
  "used_usd": 0.0
}
```

The exact `content` is whatever the mock provider is configured
to return for the test. What matters is:

- `status` is `"completed"` (or `"dry_run"` if you passed
  `--dry-run` explicitly).
- `provider_id` is `"mock"`.
- `used_usd` is `0.0` — the mock provider does not commit budget.
- `reason_codes` is empty.

## What happened internally

1. The CLI dispatched to
   `loopos.cli.commands.providers_runtime.model_call_command`.
2. The command validated the prompt path, read the prompt, and
   built a `ModelCallRequest`.
3. It instantiated a `ProviderRuntimeRegistry` and resolved the
   `mock` transport.
4. The mock transport returned a deterministic response, with
   secrets redacted before persist.
5. The shared `BudgetLedger` did **not** commit a charge (mock
   provider, dry-run path).

## Safety note

The mock provider is the default. With `--provider mock` you
cannot accidentally spend money, and `--dry-run` is the default
for `model-call`. If you want to call a real OpenAI-compatible
endpoint, see [`docs/cli-reference.md`](../cli-reference.md#loopos-model-call--provider-x--prompt-y)
for the explicit live-call flags.
