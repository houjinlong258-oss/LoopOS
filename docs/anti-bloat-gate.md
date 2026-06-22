# Anti-Bloat Gate

AI code bloat is the tendency to answer constraints and revision requests by accumulating helpers,
wrappers, branches, fallbacks, and configuration instead of deleting, merging, inlining, or fixing
the existing logic.

```text
Prefer subtraction over accumulation.
No helper unless justified.
```

## Warning rules for v0.1

The Anti-Bloat Gate is advisory in v0.1 and feeds Maintainability review. It does not silently block
every pull request.

1. Every new helper requires a boundary or reuse justification.
2. A single-use helper is presumed invalid unless it isolates policy, I/O, serialization,
   validation, persistence, or an external interface.
3. New abstraction count should be at most one unless approved.
4. Prefer editing existing code over adding files.
5. Prefer reducing lines and branches over adding them.
6. If lines added exceed twice lines deleted, explain why.
7. Reject functions whose only purpose is calling another function.
8. Add a class only when it owns state, lifecycle, or a boundary.
9. Do not add a config option to avoid fixing logic.
10. Do not add a fallback that hides errors.
11. If asked not to add helpers, do not add a helper to enforce that request.

## Report draft

```yaml
anti_bloat_report:
  added_functions: 7
  single_use_helpers: 5
  wrapper_functions: 3
  new_abstractions: 4
  new_config_flags: 1
  new_fallback_paths: 2
  lines_added: 214
  lines_deleted: 2
  concept_count_delta: 6
  verdict: request_simplification
  reasons: [excessive_single_use_helpers, low_deletion_ratio, wrapper_only_functions]
```

The report is a proposed v0.2 extension. Current enforcement remains the existing Maintainability
Analyzer, risk-aware MergeGate, and human review.
