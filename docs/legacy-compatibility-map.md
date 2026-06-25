# Legacy Compatibility Map

LoopOS v0.4 full completion keeps the older runtime surfaces importable while the
product-facing screen moves to `loopos.loop_engine`.

| Legacy Surface | Status | Replacement / Owner |
| --- | --- | --- |
| `loopos.core.LoopEngine` | Pending deprecation shim | `loopos.kernel.KernelLoopEngine` for low-level execution, `loopos.loop_engine.LoopEngine` for project training |
| v0.1/v0.2 memory CLI | Preserved | `loopos memory list/search/propose/reindex/review/accept/reject` |
| v0.3 provider runtime | Preserved | `loopos providers-runtime`, `loopos model-call`, `loopos provider smoke --provider mock` |
| v0.4 simulated loop | Preserved | default `loopos loop run --dry-run` |
| v0.4 full real executor | Added | `loopos loop run --real-executor --sandbox --repo-path <repo>` |

The compatibility rule is simple: old commands remain available, new full
completion capabilities are additive, and no legacy path can bypass Policy OS,
Action Boundary, Syscall Router, Memory Governance, or Trace.
