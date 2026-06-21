# Goal Negotiation

`AmbiguityReport` records a deterministic score, low/medium/high level, missing fields, risk factors,
confirmation/negotiation requirements, and reason codes.

- Low: finalize directly.
- Medium: show missing information and require explicit confirmation.
- High: do not execute; generate three to five structured proposals for selection or merging.

Proposals include scope, non-goals, deliverables, acceptance criteria, risk, estimated steps, and a
recommendation. Final `GoalSpec` records its origin and compatibility defaults for older stored runs.
Database goals receive read-only audit, backup/shadow/validation, and manual checklist alternatives.
