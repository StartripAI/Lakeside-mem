from __future__ import annotations

import re
from typing import Dict, Mapping

RISK_PATTERNS = (
    re.compile(r"\brm\s+-rf\b", flags=re.IGNORECASE),
    re.compile(r"curl\s+.+\|\s*sh", flags=re.IGNORECASE),
    re.compile(r"\bchmod\s+777\b", flags=re.IGNORECASE),
    re.compile(r"\bDROP\s+TABLE\b", flags=re.IGNORECASE),
)


def evaluate_execution_result(
    execution_result: Mapping[str, object],
    *,
    coverage_gate: Mapping[str, object] | None = None,
    coverage_report: Mapping[str, object] | None = None,
) -> Dict[str, object]:
    status = str(execution_result.get("status", "")).strip().lower()
    stdout = str(execution_result.get("stdout", ""))
    stderr = str(execution_result.get("stderr", ""))
    cmd = " ".join(str(v) for v in execution_result.get("command", []) if str(v).strip())
    merged = "\n".join([stdout, stderr, cmd]).strip()

    stuck = _looks_stuck(status=status, output=merged)
    risk_hits = [pat.pattern for pat in RISK_PATTERNS if pat.search(merged)]
    risk_level = "high" if risk_hits else "low"
    warnings = []
    if stuck:
        warnings.append("possible_stuck_loop_detected")
    if risk_hits:
        warnings.append("risky_command_pattern_detected")

    coverage_missing = []
    if coverage_gate and not bool(coverage_gate.get("pass", True)):
        raw = coverage_gate.get("missing_categories", [])
        if isinstance(raw, list):
            coverage_missing.extend(str(v) for v in raw if str(v).strip())
    if coverage_report and not bool(coverage_report.get("pass", True)):
        raw = coverage_report.get("missing_sections", [])
        if isinstance(raw, list):
            coverage_missing.extend(str(v) for v in raw if str(v).strip())
    coverage_missing = _ordered_unique(coverage_missing)

    recommendation = "continue"
    if risk_hits:
        recommendation = "require_human_review"
    elif stuck:
        recommendation = "retry_with_narrower_scope"
    elif coverage_missing:
        recommendation = "fill_missing_coverage"

    return {
        "stuck_detected": bool(stuck),
        "risk_level": risk_level,
        "risk_hits": risk_hits,
        "warnings": warnings,
        "coverage_missing": coverage_missing,
        "recommendation": recommendation,
    }


def _looks_stuck(*, status: str, output: str) -> bool:
    txt = str(output or "")
    if status in {"timeout"}:
        return True
    lines = [line.strip() for line in txt.splitlines() if line.strip()]
    if len(lines) < 4:
        return False
    recent = lines[-8:]
    unique = set(recent)
    return len(unique) <= max(1, len(recent) // 3)


def _ordered_unique(values):
    out = []
    seen = set()
    for value in values:
        txt = str(value or "").strip()
        if not txt or txt in seen:
            continue
        seen.add(txt)
        out.append(txt)
    return out

