# gateway-webhook

A sample gateway plugin showing how a community webhook adapter is declared
to the LoopOS registry.

## What this gateway does

- **Type:** `gateway`
- **Risk:** medium
- **Platform:** `webhook`
- **Required permissions:** `gateway:auth:token`, `gateway:allowlist`

Routes exposed by the in-tree reference implementation:

| Route | Purpose |
|---|---|
| `POST /message` | Inbound message → MessageEvent → Kernel run |
| `POST /approval` | Inbound approval → KernelSignal → resume/halt |
| `GET /health` | Liveness probe |

## Alpha contract

- The webhook handler is a framework-independent function; no production
  web server is required to use it.
- Auth is bearer-token with an explicit allowlist. Unauthorized requests
  are rejected.
- Approvals cannot bypass Policy OS; they only resume a run that was
  already waiting for approval.
- Every gateway event is logged to the trace store.

## Install

```bash
loopos registry install examples/plugins/gateway-webhook
loopos registry audit examples/plugins/gateway-webhook
```

## Simulate

```bash
loopos gateway simulate webhook "hello world" --user-id user-1
loopos gateway simulate webhook approval --run-id <run-id> --approve
```
