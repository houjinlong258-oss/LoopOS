# skill-pytest-repair

A metadata-only sample skill plugin demonstrating how a community skill is
declared to the LoopOS registry.

## What this skill does

- **Type:** `skill`
- **Risk:** medium
- **Trigger tags:** `python`, `pytest`, `test_failure`

The skill describes a five-step pytest repair loop:

1. Run `pytest -q` to surface failures.
2. Read the failing test file.
3. Read the target source file.
4. Apply a minimal patch to the source.
5. Rerun `pytest -q` to verify the fix.

Successful traces of this shape can be compressed into a `SkillSpec` via
Memory Governance and reused on future pytest failures.

## Alpha contract

- Plugin manifests are metadata-only. LoopOS never imports or executes
  plugin code during discovery, audit, or install.
- The skill's `steps` are AIL instructions, not free-form prompts.
- Skill activation must still pass Policy OS for every step.

## Install

```bash
loopos registry install examples/plugins/skill-pytest-repair
loopos registry audit examples/plugins/skill-pytest-repair
```

## Audit

The auditor reviews `terminal:pytest` and `workspace:write` permissions.
Both are acceptable for a pytest repair skill but require explicit review;
`terminal.exec` without a scoped permission would be flagged.
