"""Permission-gated terminal executor."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from loopos.core.isa import Instruction
from loopos.core.state import Observation
from loopos.execution.permissions import PermissionPolicy


class TerminalExecutor:
    """Execute terminal commands only after policy approval."""

    def __init__(
        self,
        *,
        policy: PermissionPolicy | None = None,
        default_cwd: str | Path = ".",
        auto_approve: bool = False,
    ) -> None:
        self.policy = policy or PermissionPolicy(allowlist_paths=[Path(default_cwd).resolve()])
        self.default_cwd = Path(default_cwd).resolve()
        self.auto_approve = auto_approve

    def execute(
        self,
        cmd: str | Instruction,
        cwd: str | Path | None = None,
        timeout_seconds: int | None = None,
    ) -> Observation:
        if isinstance(cmd, Instruction):
            instruction = cmd
            command = str(instruction.args.get("cmd", ""))
            cwd = instruction.args.get("cwd", cwd)
            expected_timeout = (
                instruction.expected_observation.timeout_seconds
                if instruction.expected_observation
                else None
            )
            timeout_seconds = timeout_seconds or expected_timeout
        else:
            command = cmd

        cwd_path = Path(cwd or self.default_cwd).resolve()
        decision = self.policy.evaluate(
            command,
            cwd=cwd_path,
            timeout_seconds=timeout_seconds,
            auto_approve=self.auto_approve,
        )
        if not decision.allowed:
            return Observation(
                success=False,
                summary="command blocked by permission policy",
                stderr="\n".join(decision.reasons),
                return_code=None,
                duration_ms=0,
                timed_out=False,
                command=command,
                cwd=str(cwd_path),
                error="blocked",
                data={"permission": decision.model_dump()},
            )

        started = time.perf_counter()
        try:
            # shell=True is deliberate for the MVP so Windows built-ins such as
            # `echo` work. The command string has already passed policy checks.
            completed = subprocess.run(
                command,
                cwd=str(cwd_path),
                shell=True,
                capture_output=True,
                text=True,
                timeout=decision.timeout_seconds,
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            return Observation(
                success=completed.returncode == 0,
                summary=(
                    "command completed"
                    if completed.returncode == 0
                    else f"command failed with exit code {completed.returncode}"
                ),
                stdout=completed.stdout,
                stderr=completed.stderr,
                return_code=completed.returncode,
                duration_ms=duration_ms,
                timed_out=False,
                command=command,
                cwd=str(cwd_path),
                data={"permission": decision.model_dump()},
            )
        except subprocess.TimeoutExpired as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            return Observation(
                success=False,
                summary="command timed out",
                stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
                stderr=(exc.stderr or "") if isinstance(exc.stderr, str) else "",
                return_code=None,
                duration_ms=duration_ms,
                timed_out=True,
                command=command,
                cwd=str(cwd_path),
                error="timeout",
                data={"permission": decision.model_dump()},
            )
