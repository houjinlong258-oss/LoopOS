# Prompt and Policy Distillation

## Why this exists

Distillation converts project guidance into reviewable behavior, renderer, and policy drafts. It
avoids copying large prompt blobs into runtime business logic.

## Core models

`PromptSource` records provenance. `PromptSegment` is a classified rule fragment. `BehaviorPack`,
`RendererPack`, and `PolicyPackDraft` are typed outputs. `DistillationAudit` records conflicts,
safety escalation, and source-copy checks.

## CLI usage

```bash
loopos distill inspect AGENTS.md --json
loopos distill run AGENTS.md --json
loopos distill audit AGENTS.md
```

Example output:

```text
segments: 24
policy rules: 9
conflicts: 1
status: requires_review
```

## Safety boundaries

Generated policy is a draft and is never activated automatically. Safety and permission rules
outrank style or optimization guidance, and conflicting rules require review.

## Current limitations

Classification is deterministic and keyword-based. It does not infer organization-wide intent or
replace policy-pack review and tests.
