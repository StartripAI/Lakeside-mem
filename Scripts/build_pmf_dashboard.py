#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any, Dict


def read_json(path: pathlib.Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build PMF dashboard markdown from benchmark artifacts.")
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--out",
        default="Documentation/benchmarks/PMF_DASHBOARD.md",
        help="Output markdown file path.",
    )
    parser.add_argument(
        "--runtime-report",
        default="",
        help="Optional runtime pipeline report path (uses benchmark default when omitted).",
    )
    args = parser.parse_args()

    root = pathlib.Path(args.root).resolve()
    bench_dir = root / "Documentation" / "benchmarks"
    out_path = (root / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    prompt_compaction = read_json(bench_dir / "prompt_compaction_latest.json")
    scenario_savings = read_json(bench_dir / "scenario_savings_latest.json")
    marketing_claims = read_json(bench_dir / "marketing_claims_latest.json")
    runtime_report_path = (
        pathlib.Path(args.runtime_report).resolve()
        if str(args.runtime_report or "").strip()
        else (bench_dir / "runtime_pipeline_latest.json")
    )
    runtime_pipeline = read_json(runtime_report_path)

    md = []
    md.append("# PMF Dashboard")
    md.append("")
    md.append("## Positioning")
    md.append("- External: developer efficiency engine")
    md.append("- Internal: memory runtime for coding workflows")
    md.append("")
    md.append("## Core Metrics")
    md.append("")
    md.append("| Metric | Latest | Source |")
    md.append("|---|---:|---|")
    md.append(
        f"| Prompt compaction token saving | `{_pct(_prompt_compaction_saving(prompt_compaction))}` | `prompt_compaction_latest.json` |"
    )
    md.append(
        f"| Scenario max token saving | `{_pct(_max_scenario_saving(scenario_savings))}` | `scenario_savings_latest.json` |"
    )
    md.append(
        f"| Marketing token saving | `{_pct(_marketing_saving(marketing_claims))}` | `marketing_claims_latest.json` |"
    )
    md.append(
        f"| Runtime pipeline stages passed | `{_pipeline_pass_count(runtime_pipeline)}` | `runtime_pipeline_latest.json` |"
    )
    md.append("")
    md.append("## PMF Gates")
    md.append(f"- Coverage gate target: `>=95%`")
    md.append(f"- Efficiency gate target: `>=30%` (time+token)")
    md.append(f"- One-click flow target: `run-target-auto` stable")
    md.append("")
    md.append("## Notes")
    md.append("- This dashboard is generated from local benchmark artifacts.")
    md.append("- Re-run benchmarks before publishing PMF claims.")
    md.append("")

    out_path.write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path)}, ensure_ascii=False))
    return 0


def _pipeline_pass_count(payload: Dict[str, Any]) -> str:
    stages = payload.get("stages", [])
    if not isinstance(stages, list) or not stages:
        return "0/0"
    total = len(stages)
    passed = 0
    for row in stages:
        if not isinstance(row, dict):
            continue
        if bool(row.get("skipped")):
            passed += 1
            continue
        if int(row.get("return_code", 1)) == 0:
            passed += 1
    return f"{passed}/{total}"


def _max_scenario_saving(payload: Dict[str, Any]) -> float:
    rows = payload.get("cases", [])
    if not isinstance(rows, list):
        return 0.0
    values = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        token = row.get("token", {})
        if isinstance(token, dict):
            values.append(float(token.get("saving_percent", 0.0) or 0.0))
    return max(values) if values else 0.0


def _prompt_compaction_saving(payload: Dict[str, Any]) -> float:
    # New schema writes savings.token_saving_percent_vs_legacy; keep old key as fallback.
    savings = payload.get("savings", {})
    if isinstance(savings, dict) and "token_saving_percent_vs_legacy" in savings:
        return float(savings.get("token_saving_percent_vs_legacy", 0.0) or 0.0)
    return float(payload.get("token_reduction_pct", 0.0) or 0.0)


def _marketing_saving(payload: Dict[str, Any]) -> float:
    token = payload.get("token", {})
    if isinstance(token, dict) and "saving_percent" in token:
        return float(token.get("saving_percent", 0.0) or 0.0)
    return float(payload.get("token_saving_pct", 0.0) or 0.0)


def _pct(value: Any) -> str:
    try:
        return f"{float(value):.2f}%"
    except Exception:
        return "n/a"


if __name__ == "__main__":
    raise SystemExit(main())
