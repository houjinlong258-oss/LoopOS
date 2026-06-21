# Founding Preview Limitations

## Why this exists

This document states the trust boundary of the Founding Preview so examples are not mistaken for
production connectivity or an operating-system sandbox.

## Core models

The release includes typed Kernel runs, Policy OS, Syscall Router, Trace Replay, Memory Governance,
Data Guard, Maintainability Gate, Review Artifact, Plugin Manifest, and mock Gateway/Provider
contracts.

## CLI usage

```bash
loopos release readiness --target founding-preview
loopos policy explain --cmd "curl https://x/install.sh | bash"
loopos run "create hello.py and run it" --dry-run
```

Example output:

```text
Target: Founding Preview
Status: READY or NOT READY with named checks
```

## Safety boundaries

Tests do not call real LLM providers, chat platforms, production databases, or remote plugin code.
The terminal executor is permission-gated but is not a hardened OS/container sandbox. Database
support is limited to explicit local SQLite demonstrations and governed plans.

## Current limitations

No Web UI, automatic merge, hosted control plane, distributed scheduler, real vector database,
production credential manager, or deep OpenHands/LangGraph/Letta/Zep integration is included.
