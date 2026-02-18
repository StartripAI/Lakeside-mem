from __future__ import annotations

from typing import Dict, Mapping, Sequence

from .contracts import CoverageReport, EvidenceItem, ExecutionPlan, TaskSpec

REQUIRED_SECTIONS: Sequence[str] = (
    "north_star",
    "architecture",
    "module_map",
    "entrypoint",
    "main_flow",
    "persistence",
    "ai_generation",
    "tests",
    "risks",
)


def compile_task_spec(*, question: str, project: str, root_abs: str, profile: str) -> TaskSpec:
    return TaskSpec(
        question=str(question or "").strip(),
        project=str(project or "").strip() or "default",
        root_abs=str(root_abs or "").strip(),
        profile=str(profile or "").strip() or "daily_qa",
    )


def build_execution_plan(
    task: TaskSpec,
    *,
    min_evidence_per_section: int = 3,
    coverage_target_pct: float = 95.0,
    efficiency_gain_target_pct: float = 30.0,
) -> ExecutionPlan:
    return ExecutionPlan(
        task=task,
        sections=REQUIRED_SECTIONS,
        min_evidence_per_section=max(1, int(min_evidence_per_section)),
        coverage_target_pct=max(0.0, float(coverage_target_pct)),
        efficiency_gain_target_pct=max(0.0, float(efficiency_gain_target_pct)),
    )


def compute_coverage_report(
    evidence_items: Sequence[EvidenceItem],
    *,
    required_sections: Sequence[str] = REQUIRED_SECTIONS,
    min_evidence_per_section: int = 3,
    pass_threshold_pct: float = 95.0,
) -> CoverageReport:
    min_per_section = max(1, int(min_evidence_per_section))
    required = [str(sec) for sec in required_sections if str(sec).strip()]
    counts: Dict[str, int] = {sec: 0 for sec in required}
    for item in evidence_items:
        sec = str(item.section or "").strip()
        if sec in counts:
            counts[sec] += 1
    covered = [sec for sec in required if counts.get(sec, 0) >= min_per_section]
    missing = [sec for sec in required if sec not in covered]
    coverage_pct = 100.0 if not required else (len(covered) / len(required)) * 100.0
    all_sections_pass = len(missing) == 0
    gate_pass = all_sections_pass and coverage_pct >= float(pass_threshold_pct)
    return CoverageReport(
        required_sections=tuple(required),
        section_counts=counts,
        min_evidence_per_section=min_per_section,
        covered_sections=tuple(covered),
        missing_sections=tuple(missing),
        coverage_pct=coverage_pct,
        pass_gate=gate_pass,
    )


def coverage_report_from_dicts(
    evidence_items: Sequence[Mapping[str, object]],
    *,
    required_sections: Sequence[str] = REQUIRED_SECTIONS,
    min_evidence_per_section: int = 3,
    pass_threshold_pct: float = 95.0,
) -> CoverageReport:
    normalized = [
        EvidenceItem(
            section=str(item.get("section", "")),
            file_path=str(item.get("file_path", "")),
            symbol=str(item.get("symbol", "")),
            role=str(item.get("role", "")),
            score=float(item.get("score", 0.0) or 0.0),
        )
        for item in evidence_items
        if isinstance(item, Mapping)
    ]
    return compute_coverage_report(
        normalized,
        required_sections=required_sections,
        min_evidence_per_section=min_evidence_per_section,
        pass_threshold_pct=pass_threshold_pct,
    )

