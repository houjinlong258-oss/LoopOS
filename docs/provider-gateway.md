# Provider Gateway

The future Model Kernel exposes `ProviderProfile`, capability discovery, alias resolution, and deterministic routing for reasoner, coder, vision, critic, verifier, aggregator, summarizer, and policy-explainer roles.

The first implementation must be registry plus mock client only. Profiles may describe OpenAI-compatible, Anthropic, Gemini, Bedrock, local, OAuth, and custom providers, but no provider receives credentials or network access in core tests. Provider selection cannot override Policy OS or syscall permissions.
