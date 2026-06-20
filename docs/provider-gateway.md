# Provider Gateway

The Model Kernel MVP exposes `ProviderProfile`, YAML loading, capability discovery, alias resolution, local-only routing, and deterministic routing for reasoner, coder, vision, critic, verifier, aggregator, summarizer, safety-judge, and policy-explainer roles.

The first implementation is registry plus mock client only. Profiles describe OpenAI-compatible, Anthropic, Gemini, Bedrock, local, OAuth, and custom providers, but no provider receives credentials or network access in core tests. Provider selection cannot override Policy OS or syscall permissions.

Executable skeleton:

- `loopos providers list`
- `loopos providers route coding`
- `loopos providers assign vision_companion`
- `loopos models route --task coding --input image`
- `loopos models route --task coding --secret`

`MultiModelScheduler` can assign primary/coder/critic/verifier/summarizer/policy-explainer roles and select a `vision_companion` when the primary assignment lacks image capability. Secret tasks route through providers marked `local_only` or carrying the `local` capability.
