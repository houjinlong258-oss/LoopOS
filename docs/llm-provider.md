# LLM Provider

LoopOS Alpha uses LLMs only for memory proposal extraction. It does not let LLM output directly drive terminal execution.

## Providers

- `mock`: deterministic local provider used by tests and default CLI flows.
- `openai-compatible`: minimal `/v1/chat/completions` client.

## Environment

```bash
set LOOPOS_LLM_BASE_URL=https://api.openai.com
set LOOPOS_LLM_API_KEY=...
set LOOPOS_LLM_MODEL=gpt-4.1-mini
set LOOPOS_LLM_TIMEOUT_SECONDS=30
```

If `LOOPOS_LLM_API_KEY` is missing, the provider returns a readable error and makes no network request.

## CLI

```bash
python -m loopos.cli.app run "demo" --propose-memory --llm-provider mock
python -m loopos.cli.app run "demo" --propose-memory --llm-provider openai-compatible
```

Generated proposals must still be accepted before they become active memory.
