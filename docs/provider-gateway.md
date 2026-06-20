# Provider Gateway

The Model Kernel MVP exposes `ProviderProfile`, capability discovery, alias resolution, and deterministic routing for reasoner, coder, vision, critic, verifier, aggregator, summarizer, and policy-explainer roles.

The first implementation is registry plus mock client only. Profiles describe OpenAI-compatible, Anthropic, Gemini, Bedrock, local, OAuth, and custom providers, but no provider receives credentials or network access in core tests. Provider selection cannot override Policy OS or syscall permissions.

Executable skeleton:

- `loopos providers list`
- `loopos providers route coding`
- `loopos providers assign vision_companion`

`MultiModelScheduler` can assign primary/coder/critic/verifier/summarizer/policy-explainer roles and select a `vision_companion` when the primary assignment lacks image capability.
