# ChatOps Gateway

ChatOps adapters translate platform webhooks into typed `MessageEvent` and approval signals. The MVP boundary includes mock Telegram, email, Slack, Discord, and WhatsApp Cloud adapters only.

Adapters may create or continue Kernel Runs and render approval cards. They cannot execute tools, write memory, or approve blocked actions themselves. Platform user identity, run ownership, replay protection, and approval audit records are mandatory before enabling real APIs.

Executable skeleton:

- `loopos gateway simulate telegram "run tests"` creates a typed mock `MessageEvent`.
- `ChatOpsGateway.to_run_spec()` converts that message into a guarded `RunSpec`.
- `ChatOpsGateway.approval_card()` records mock approval cards for dangerous actions.
- `loopos gateway approval telegram "git reset --hard" --run-id RUN_ID --risk high` persists a mock approval card.
- `loopos gateway decide CARD_ID --approve` or `--deny` returns the structured resume decision for the Kernel.
