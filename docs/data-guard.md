# Data Guard

Data Guard detects database goals, migration commands, destructive SQL, sensitive entities, and
production-like targets. High-risk work requires a backup plan, verified backup, shadow plan,
validation, rollback plan, and human approval.

The Alpha vault copies only explicit workspace-local files, writes SHA-256 manifests, marks artifacts
read-only where supported, and verifies checksums. It never connects to a database. The nine
`database.*` syscalls expose inspection, local sample backup, verification, mock shadow/validation,
redaction, and disabled migration/restore boundaries.

Raw PII, credentials, and unredacted samples are prohibited from Context, Trace, and Memory.
