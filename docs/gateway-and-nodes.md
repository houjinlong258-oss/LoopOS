# Gateway And Nodes

The v0.4 full control plane is intentionally small.

`loopos.gateway` remains loopback/local-first for CLI flows. `gateway status`
and `gateway doctor` report local exposure and approval-flow health.

`loopos.nodes` declares node capabilities such as:

- `shell.exec`;
- `file.patch`;
- `test.run`;
- `computer.observe`;
- `ui.verify`;
- `provider.call`;
- `memory.retrieve`.

Non-local nodes require pairing. Capabilities declare what a node can do; they
do not bypass the action boundary.
