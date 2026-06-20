# ChatOps Gateway

ChatOps adapters translate platform webhooks into typed `MessageEvent` and approval signals. The MVP boundary includes mock Telegram, email, Slack, Discord, and WhatsApp Cloud adapters only.

Adapters may create or continue Kernel Runs and render approval cards. They cannot execute tools, write memory, or approve blocked actions themselves. Platform user identity, run ownership, replay protection, and approval audit records are mandatory before enabling real APIs.
