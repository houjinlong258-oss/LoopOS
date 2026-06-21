# provider-openai-compatible

A metadata-only sample provider plugin showing how a community OpenAI-compatible
adapter is declared to the LoopOS registry.

## What this plugin is

- **Type:** `provider`
- **Risk:** medium
- **Required tools:** `provider.chat`
- **Required permissions:** `OPENAI_API_KEY` env var and outbound HTTPS network

The plugin manifest declares capabilities (`text`, `code`, `reasoning`, `json_schema`),
default models, cost/latency class, and reliability score. LoopOS uses this metadata
for capability routing — it never imports plugin code during discovery or install.

## Alpha contract

- Real network transport is **disabled by default**.
- Tests never make real API calls.
- Enabling real transport requires explicit Policy OS approval and a guarded
  provider syscall that records to trace.
- The packaged `loopos.model_kernel.openai_compatible` module is the in-tree
  reference implementation this plugin advertises.

## Install

```bash
loopos registry install examples/plugins/provider-openai-compatible
```

After install, the manifest is copied into the local registry under
`.loopos/registry/`. LoopOS will then surface this provider in
`loopos registry list` and `loopos models list`.

## Audit

```bash
loopos registry audit examples/plugins/provider-openai-compatible
```

The auditor flags `network:outbound:https` as a permission that requires
explicit review, which is the correct outcome for a cloud provider.
