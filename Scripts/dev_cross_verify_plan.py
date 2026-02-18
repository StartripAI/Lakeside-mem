#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import time
from typing import Dict, Tuple


def run_agent(agent: str, prompt: str, cwd: pathlib.Path, timeout_sec: int) -> Dict[str, object]:
    if agent == "codex":
        cmd = [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "--json",
            "--cd",
            str(cwd),
            prompt,
        ]
    else:
        cmd = ["claude", "-p", "--output-format", "json", prompt]
    started = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=str(cwd), timeout=timeout_sec)
    except subprocess.TimeoutExpired as exc:
        return {
            "agent": agent,
            "return_code": 124,
            "duration_ms": round((time.time() - started) * 1000.0, 3),
            "stdout": str(exc.stdout or ""),
            "stderr": str(exc.stderr or ""),
            "ok": False,
        }
    except FileNotFoundError:
        return {
            "agent": agent,
            "return_code": 127,
            "duration_ms": round((time.time() - started) * 1000.0, 3),
            "stdout": "",
            "stderr": f"{agent} CLI not found",
            "ok": False,
        }
    return {
        "agent": agent,
        "return_code": int(proc.returncode),
        "duration_ms": round((time.time() - started) * 1000.0, 3),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "ok": proc.returncode == 0,
    }


def similarity(a: str, b: str) -> float:
    ta = set(tokens(a))
    tb = set(tokens(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def tokens(text: str):
    return re.findall(r"[A-Za-z_][A-Za-z0-9_]{1,}|[0-9]+|[\u4e00-\u9fff]+", str(text or "").lower())


def main() -> int:
    parser = argparse.ArgumentParser(description="Internal Codex+Claude plan cross-validation loop.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--max-rounds", type=int, default=100)
    parser.add_argument("--converge-threshold", type=float, default=0.7)
    parser.add_argument("--timeout-sec", type=int, default=120)
    parser.add_argument("--out", default="Documentation/benchmarks/dev_cross_verify_latest.json")
    args = parser.parse_args()

    root = pathlib.Path(args.root).resolve()
    max_rounds = max(1, min(100, int(args.max_rounds)))
    threshold = max(0.1, min(1.0, float(args.converge_threshold)))
    prompt = str(args.prompt)
    reports = []
    converged = False
    score = 0.0

    for idx in range(1, max_rounds + 1):
        codex = run_agent("codex", prompt, root, max(30, int(args.timeout_sec)))
        claude = run_agent("claude", prompt, root, max(30, int(args.timeout_sec)))
        codex_text = str(codex.get("stdout", ""))
        claude_text = str(claude.get("stdout", ""))
        score = similarity(codex_text, claude_text)
        reports.append(
            {
                "round": idx,
                "codex": _trim_result(codex),
                "claude": _trim_result(claude),
                "similarity": round(score, 4),
            }
        )
        if bool(codex.get("ok")) and bool(claude.get("ok")) and score >= threshold:
            converged = True
            break
        prompt = (
            f"{args.prompt}\n\n"
            f"Round {idx} disagreement score={round(score, 4)}. "
            "Refine the result to improve factual alignment and deterministic structure."
        )

    out_path = (root / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ok": converged,
        "max_rounds": max_rounds,
        "rounds_used": len(reports),
        "threshold": threshold,
        "final_similarity": round(score, 4),
        "reports": reports,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": converged, "out": str(out_path), "rounds_used": len(reports)}, ensure_ascii=False))
    return 0 if converged else 1


def _trim_result(item: Dict[str, object]) -> Dict[str, object]:
    return {
        "agent": item.get("agent"),
        "return_code": item.get("return_code"),
        "duration_ms": item.get("duration_ms"),
        "stdout_tail": _tail(str(item.get("stdout", "")), 1200),
        "stderr_tail": _tail(str(item.get("stderr", "")), 1200),
    }


def _tail(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


if __name__ == "__main__":
    raise SystemExit(main())
