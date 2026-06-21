# Safety Model

Policy OS classifies actions from L0 through L5:

- L0: observation and read-only metadata.
- L1: bounded local tests, temporary work, and safe local processing.
- L2: project writes and medium-risk changes requiring a visible plan and confirmation.
- L3: destructive Git, restore, production-like, or broad changes requiring explicit approval,
  trace, and rollback evidence.
- L4: user-only actions such as payment, irreversible external submission, or raw private export.
- L5: blocked behavior such as remote script pipes, destructive system commands, secret
  exfiltration, policy bypass, and real database execution in Alpha.

Deny overrides allow; approval overrides silent execution. `--dry-run` and replay never invoke
side-effecting adapters. Paths stay inside the workspace. Database operations require Data Guard;
only local samples can produce a verified Alpha backup manifest.

String command analysis remains conservative and is not an OS sandbox. Future production releases
need isolated execution backends and platform-specific command parsing.
