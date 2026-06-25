# Computer Control Runtime

`loopos.computer_control` is a consented, visible, auditable, replayable local
computer-control runtime for project training.

It supports four modes:

| Mode | Behavior |
| --- | --- |
| `observe_only` | observe state only |
| `dry_run` | plan and record actions without real OS effects |
| `sandbox_control` | execute only through sandbox/fake/registered sandbox backends |
| `local_control` | requires explicit `--allow-computer-control` |

CI and tests use `FakeComputerBackend`. The fake backend records click/type/
verify-style actions, returns deterministic redacted observations, and performs
no OS side effects.

Replay reads `ComputerControlTrace` and never re-executes actions.
