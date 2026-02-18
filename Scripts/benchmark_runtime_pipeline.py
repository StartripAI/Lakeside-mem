#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import time
from typing import Dict, List


def run_stage(name: str, cmd: List[str]) -> Dict[str, object]:
    started = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return {
        "name": name,
        "command": cmd,
        "return_code": int(proc.returncode),
        "duration_ms": round((time.time() - started) * 1000.0, 3),
        "stdout_tail": _tail(proc.stdout, 1200),
        "stderr_tail": _tail(proc.stderr, 1200),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Standardized benchmark pipeline with checkpoint resume.")
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--out",
        default="Documentation/benchmarks/runtime_pipeline_latest.json",
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--checkpoint",
        default="Documentation/benchmarks/runtime_pipeline_checkpoint.json",
        help="Checkpoint JSON path.",
    )
    parser.add_argument(
        "--compare",
        default="",
        help="Optional previous runtime_pipeline report for delta comparison.",
    )
    args = parser.parse_args()

    root = pathlib.Path(args.root).resolve()
    out_path = (root / args.out).resolve()
    ckpt_path = (root / args.checkpoint).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ckpt_path.parent.mkdir(parents=True, exist_ok=True)

    done = {}
    if ckpt_path.exists():
        try:
            done = json.loads(ckpt_path.read_text(encoding="utf-8"))
        except Exception:
            done = {}
    stages = [
        (
            "prompt_compaction",
            [
                "python3",
                str(root / "Scripts" / "benchmark_prompt_compaction.py"),
                "--root",
                str(root),
                "--runs",
                "3",
                "--out",
                str(root / "Documentation" / "benchmarks" / "prompt_compaction_latest.json"),
            ],
        ),
        (
            "scenario_savings",
            [
                "python3",
                str(root / "Scripts" / "benchmark_scenario_savings.py"),
                "--root",
                str(root),
                "--out",
                str(root / "Documentation" / "benchmarks" / "scenario_savings_latest.json"),
            ],
        ),
        (
            "marketing_claim",
            [
                "python3",
                str(root / "Scripts" / "benchmark_marketing_claim.py"),
                "--root",
                str(root),
                "--out",
                str(root / "Documentation" / "benchmarks" / "marketing_claims_latest.json"),
            ],
        ),
        (
            "pmf_dashboard",
            [
                "python3",
                str(root / "Scripts" / "build_pmf_dashboard.py"),
                "--root",
                str(root),
                "--out",
                str(root / "Documentation" / "benchmarks" / "PMF_DASHBOARD.md"),
            ],
        ),
    ]

    stage_reports: List[Dict[str, object]] = []
    for name, cmd in stages:
        if name != "pmf_dashboard" and bool(done.get(name)):
            stage_reports.append(
                {
                    "name": name,
                    "skipped": True,
                    "reason": "checkpoint_complete",
                }
            )
            continue
        stage_cmd = list(cmd)
        if name == "pmf_dashboard":
            # Ensure dashboard reads current-stage runtime data, not stale prior runs.
            _write_report(
                out_path,
                {
                    "ok": True,
                    "root": str(root),
                    "checkpoint": str(ckpt_path),
                    "stages": stage_reports,
                },
            )
            stage_cmd.extend(["--runtime-report", str(out_path)])
        report = run_stage(name, stage_cmd)
        stage_reports.append(report)
        if int(report.get("return_code", 1)) != 0:
            _write_report(
                out_path,
                {
                    "ok": False,
                    "root": str(root),
                    "stages": stage_reports,
                },
            )
            return 1
        done[name] = True
        ckpt_path.write_text(json.dumps(done, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    comparator = {}
    if args.compare:
        baseline_path = pathlib.Path(args.compare).expanduser().resolve()
        if baseline_path.exists():
            try:
                baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
                comparator = _compare_reports(baseline, {"stages": stage_reports})
            except Exception as exc:
                comparator = {"error": str(exc)}

    report = {
        "ok": True,
        "root": str(root),
        "checkpoint": str(ckpt_path),
        "stages": stage_reports,
        "comparator": comparator,
    }
    _write_report(out_path, report)
    # Refresh dashboard with final report so stage counts reflect the complete pipeline state.
    refresh = run_stage(
        "pmf_dashboard_refresh",
        [
            "python3",
            str(root / "Scripts" / "build_pmf_dashboard.py"),
            "--root",
            str(root),
            "--out",
            str(root / "Documentation" / "benchmarks" / "PMF_DASHBOARD.md"),
            "--runtime-report",
            str(out_path),
        ],
    )
    if int(refresh.get("return_code", 1)) != 0:
        report["ok"] = False
        report["pmf_dashboard_refresh"] = refresh
        _write_report(out_path, report)
        return 1
    return 0


def _compare_reports(old: Dict[str, object], new: Dict[str, object]) -> Dict[str, object]:
    def stage_map(payload: Dict[str, object]) -> Dict[str, Dict[str, object]]:
        rows = payload.get("stages", [])
        out: Dict[str, Dict[str, object]] = {}
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict) and row.get("name"):
                    out[str(row.get("name"))] = row
        return out

    old_map = stage_map(old)
    new_map = stage_map(new)
    deltas = {}
    for name, new_row in new_map.items():
        old_row = old_map.get(name, {})
        new_d = float(new_row.get("duration_ms", 0.0) or 0.0)
        old_d = float(old_row.get("duration_ms", 0.0) or 0.0)
        if old_d > 0:
            delta_pct = ((new_d - old_d) / old_d) * 100.0
        else:
            delta_pct = 0.0
        deltas[name] = {
            "duration_ms_old": round(old_d, 3),
            "duration_ms_new": round(new_d, 3),
            "duration_delta_pct": round(delta_pct, 3),
        }
    return {"duration_deltas": deltas}


def _write_report(path: pathlib.Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _tail(text: str, max_chars: int) -> str:
    value = str(text or "")
    if len(value) <= max_chars:
        return value
    return value[-max_chars:]


if __name__ == "__main__":
    raise SystemExit(main())
