# v0.4 Full Completion Architecture

LoopOS v0.4 full completion keeps the product identity centered on the
Project Training Runtime:

```text
Goal -> Plan -> Build -> Test -> Review -> Repair -> Optimize -> Deliver
```

The full completion layer adds real project execution, token accounting,
project memory, low-distance LAIL routing, fake-convergence attack, and a
small local control plane. Safety remains the action boundary; it protects
side effects but is not the product's first screen.

## Runtime Surfaces

| Surface | Package | Default |
| --- | --- | --- |
| Project loop | `loopos.loop_engine` | simulated unless explicitly configured |
| Real executor | `loopos.executors` | sandboxed temp/local repo only |
| Computer control | `loopos.computer_control` | fake/dry-run/observe-only |
| Provider runtime | `loopos.providers_runtime` | mock; live opt-in |
| Token economy | `loopos.token_economy` | local ledger |
| Project memory | `loopos.project_memory` | in-memory compiler by default |
| Gateway/nodes | `loopos.gateway`, `loopos.nodes` | loopback/local-only |
| Tools/skills/plugins | `loopos.tools`, `loopos.skills`, `loopos.plugins` | optional contracts |

No full-completion component may claim real external effects unless the
effect was executed through the action boundary and recorded as evidence.
