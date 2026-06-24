# First Dry-Run

A 60-second walkthrough that proves the install works end-to-end
without making any side effects.

## Goal

Render the v0.3 Workbench for the current working directory
without touching the network, the shell, or any file outside the
workdir.

## Command

```bash
python -m loopos.cli.app workbench --dry-run
```

Add `--json` if you want a structured dump.

## Expected output (abridged)

A series of panels (Rich tables if `rich` is installed, plain
text otherwise) including the eight required v0.3 panels:

- `Goal`
- `Agent`
- `Policy`
- `ACI`
- `ALI`
- `Trace-Replay`
- `Fusion`
- `Readiness`

With `--json`, the output is a single JSON object keyed by panel
name. Each panel reports a `status` field, a short `summary`, and
the structured payload the Workbench built from your project.

## What happened internally

1. The CLI dispatched the `workbench` command to
   `loopos.cli.commands.workbench.workbench_command`.
2. The command called `Workbench.build_context()` which gathered
   the goal, agent state, and policy decisions into a
   `WorkbenchContext` snapshot.
3. `build_panels_from_context()` turned the snapshot into the
   eight required panels.
4. `render_plain` (or `render_json`) emitted the output.
5. The mock provider and `--dry-run` together guarantee that no
   real provider call, no shell exec, and no file write happened.

## Safety note

This is the safest command in LoopOS. It exercises the v0.3
product surface end-to-end without ever leaving the workdir.
Use it as the very first thing you run after a fresh install.
