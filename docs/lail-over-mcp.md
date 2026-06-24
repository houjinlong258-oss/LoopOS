# LAIL, MCP, A2A, ACI, and Syscall

LAIL is the internal signal language. MCP, A2A, ACI, and Syscall are
different boundaries.

| Surface | Responsibility |
|---------|----------------|
| LAIL | Internal optimization signals between LoopOS roles. No actions. |
| MCP | External tools, resources, and context access. |
| A2A | External agent interoperability. |
| ACI | Converts a proposal into an executable command request. |
| Syscall | Executes real side effects behind Policy OS and trace. |

One sentence:

LAIL decides how agents exchange optimization signals. ACI decides how an
idea becomes a command request. Syscall decides how a command becomes a real
side effect. MCP and A2A decide how outside tools and agents connect.

`loopos.agent_language.mcp_bridge.LailMcpBridge` is an adapter. It serializes
LAIL messages into tool payloads but does not call tools and is not a core
dependency of LAIL routing.
