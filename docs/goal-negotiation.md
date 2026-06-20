# Goal Negotiation Kernel

`GoalNegotiator` analyzes user input before a Run is created. Concrete goals finalize directly as `GoalSpec`; vague project-wide goals return five bounded options: architecture audit, MVP delivery, Kernel upgrade, CLI priority, or custom/merged scope.

An ambiguous goal cannot enter `KernelLoopEngine` without selected option IDs. A finalized GoalSpec records the objective, success criteria, constraints, and selected options and is emitted as a trace event. A one-time selection is not persisted as a global preference.

CLI entry points are `loopos goal analyze`, `loopos goal propose`, `loopos goal finalize --option`, and `loopos run --goal-option`.
