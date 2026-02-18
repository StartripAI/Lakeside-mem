from __future__ import annotations

import pathlib
import shutil
import subprocess
import time
import os
from typing import Mapping, Sequence

from .contracts import ExecutionResult


def run_executor(
    *,
    executor_mode: str,
    prompt: str,
    cwd: str,
    timeout_sec: int = 90,
    extra_env: Mapping[str, str] | None = None,
) -> ExecutionResult:
    mode = str(executor_mode or "none").strip().lower()
    if mode == "none":
        return ExecutionResult(
            executor_mode="none",
            attempted=False,
            status="skipped",
            return_code=0,
            duration_ms=0.0,
            command=[],
            stdout="",
            stderr="",
            note="executor disabled",
        )

    if mode not in {"codex", "claude"}:
        return ExecutionResult(
            executor_mode=mode,
            attempted=False,
            status="invalid_executor",
            return_code=2,
            duration_ms=0.0,
            command=[],
            stdout="",
            stderr=f"unsupported executor mode: {mode}",
            note="use one of: none, codex, claude",
        )

    command = _build_command(mode=mode, prompt=prompt, cwd=cwd)
    binary = command[0]
    if not shutil.which(binary):
        return ExecutionResult(
            executor_mode=mode,
            attempted=False,
            status="unavailable",
            return_code=127,
            duration_ms=0.0,
            command=command,
            stdout="",
            stderr=f"{binary} not found in PATH",
            note="install the executor CLI or use --executor none",
        )

    env = dict(os.environ)
    if extra_env:
        for key, value in extra_env.items():
            env[str(key)] = str(value)
    started = time.time()
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=str(pathlib.Path(cwd).resolve()),
            timeout=max(10, int(timeout_sec)),
            check=False,
            env=env,
        )
        status = "succeeded" if proc.returncode == 0 else "failed"
        return ExecutionResult(
            executor_mode=mode,
            attempted=True,
            status=status,
            return_code=int(proc.returncode),
            duration_ms=(time.time() - started) * 1000.0,
            command=command,
            stdout=proc.stdout,
            stderr=proc.stderr,
            note="",
        )
    except subprocess.TimeoutExpired as exc:
        return ExecutionResult(
            executor_mode=mode,
            attempted=True,
            status="timeout",
            return_code=124,
            duration_ms=(time.time() - started) * 1000.0,
            command=command,
            stdout=str(exc.stdout or ""),
            stderr=str(exc.stderr or ""),
            note=f"timed out after {timeout_sec}s",
        )


def available_executors() -> Sequence[str]:
    out = []
    if shutil.which("codex"):
        out.append("codex")
    if shutil.which("claude"):
        out.append("claude")
    return tuple(out)


def _build_command(*, mode: str, prompt: str, cwd: str) -> list[str]:
    if mode == "codex":
        return [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "--json",
            "--cd",
            str(pathlib.Path(cwd).resolve()),
            str(prompt),
        ]
    return [
        "claude",
        "-p",
        "--output-format",
        "json",
        str(prompt),
    ]
