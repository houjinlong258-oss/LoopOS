# Maintainability Kernel

## Why this exists

LoopOS treats maintainability as a delivery constraint. A patch that runs once but bypasses
policy, duplicates architecture, hides global state, or lacks meaningful tests is not complete.

## Core models

`CodeChangeSummary` describes a diff. `MaintainabilityFinding` records evidence and severity.
`MaintainabilityReport` aggregates scores. `MaintainabilityGateDecision` produces an explicit
allow, review, or block outcome that can be attached to a Review Artifact.

## CLI usage

```bash
loopos code summary --diff changes.diff
loopos code maintainability --diff changes.diff --json
loopos code gate --diff changes.diff
```

Example output:

```text
recommendation: require_review
score: 78
findings: missing_test_change, cross_package_internal_import
```

## Safety boundaries

The analyzer reads diff text only. It does not execute changed code. Policy, syscall, Data Guard,
and memory-governance bypass patterns are blockers rather than style warnings.

## Current limitations

The analyzer is deterministic and heuristic. It does not replace language-specific static
analysis, a verifier test run, or an independent reviewer.
