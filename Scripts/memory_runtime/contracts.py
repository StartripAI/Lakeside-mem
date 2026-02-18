from __future__ import annotations

import dataclasses
from typing import Dict, List, Mapping, Sequence


@dataclasses.dataclass(frozen=True)
class TaskSpec:
    question: str
    project: str
    root_abs: str
    profile: str
    must_read_order: Sequence[str] = dataclasses.field(
        default_factory=lambda: ("docs_first", "code_second", "tests_risks_third")
    )

    def to_dict(self) -> Dict[str, object]:
        return {
            "question": self.question,
            "project": self.project,
            "root_abs": self.root_abs,
            "profile": self.profile,
            "must_read_order": list(self.must_read_order),
        }


@dataclasses.dataclass(frozen=True)
class ExecutionPlan:
    task: TaskSpec
    sections: Sequence[str]
    min_evidence_per_section: int
    coverage_target_pct: float
    efficiency_gain_target_pct: float

    def to_dict(self) -> Dict[str, object]:
        return {
            "task": self.task.to_dict(),
            "sections": list(self.sections),
            "min_evidence_per_section": int(self.min_evidence_per_section),
            "coverage_target_pct": float(self.coverage_target_pct),
            "efficiency_gain_target_pct": float(self.efficiency_gain_target_pct),
        }


@dataclasses.dataclass(frozen=True)
class EvidenceItem:
    section: str
    file_path: str
    symbol: str
    role: str
    score: float = 0.0

    def to_dict(self) -> Dict[str, object]:
        return {
            "section": self.section,
            "file_path": self.file_path,
            "symbol": self.symbol,
            "role": self.role,
            "score": float(self.score),
        }


@dataclasses.dataclass(frozen=True)
class CoverageReport:
    required_sections: Sequence[str]
    section_counts: Mapping[str, int]
    min_evidence_per_section: int
    covered_sections: Sequence[str]
    missing_sections: Sequence[str]
    coverage_pct: float
    pass_gate: bool

    def to_dict(self) -> Dict[str, object]:
        return {
            "required_sections": list(self.required_sections),
            "section_counts": {str(k): int(v) for k, v in self.section_counts.items()},
            "min_evidence_per_section": int(self.min_evidence_per_section),
            "covered_sections": list(self.covered_sections),
            "missing_sections": list(self.missing_sections),
            "coverage_pct": round(float(self.coverage_pct), 2),
            "pass": bool(self.pass_gate),
        }


@dataclasses.dataclass(frozen=True)
class ExecutionResult:
    executor_mode: str
    attempted: bool
    status: str
    return_code: int
    duration_ms: float
    command: Sequence[str]
    stdout: str
    stderr: str
    note: str = ""
    critic: Mapping[str, object] = dataclasses.field(default_factory=dict)

    def to_dict(self, *, max_chars: int = 2400) -> Dict[str, object]:
        return {
            "executor_mode": self.executor_mode,
            "attempted": bool(self.attempted),
            "status": self.status,
            "return_code": int(self.return_code),
            "duration_ms": round(float(self.duration_ms), 3),
            "command": list(self.command),
            "stdout": _trim(self.stdout, max_chars),
            "stderr": _trim(self.stderr, max_chars),
            "note": self.note,
            "critic": dict(self.critic),
        }


def _trim(text: str, max_chars: int) -> str:
    value = str(text or "")
    if len(value) <= max_chars:
        return value
    keep = max(40, max_chars // 2)
    return f"{value[:keep]}\n...<trimmed>...\n{value[-keep:]}"

