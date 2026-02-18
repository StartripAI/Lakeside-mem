from __future__ import annotations

import pathlib
import sys
import unittest

SCRIPT_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from memory_runtime.contracts import EvidenceItem
from memory_runtime.executors import run_executor
from memory_runtime.planner import REQUIRED_SECTIONS, build_execution_plan, compile_task_spec, compute_coverage_report
from memory_runtime.retrieval import build_evidence_items, hybrid_rank_chunks


class MemoryRuntimeLayerTests(unittest.TestCase):
    def test_execution_plan_has_nine_sections(self) -> None:
        task = compile_task_spec(
            question="learn this project architecture and risks",
            project="demo",
            root_abs="/tmp/demo",
            profile="onboarding",
        )
        plan = build_execution_plan(task)
        self.assertEqual(len(plan.sections), 9)
        self.assertEqual(tuple(plan.sections), tuple(REQUIRED_SECTIONS))
        self.assertEqual(plan.min_evidence_per_section, 3)

    def test_coverage_report_computation(self) -> None:
        items = []
        for section in REQUIRED_SECTIONS:
            for idx in range(3):
                items.append(EvidenceItem(section=section, file_path=f"/tmp/{section}.py", symbol=f"s{idx}", role="ctx"))
        report = compute_coverage_report(items, min_evidence_per_section=3, pass_threshold_pct=95.0)
        self.assertTrue(report.pass_gate)
        self.assertEqual(report.coverage_pct, 100.0)
        self.assertEqual(list(report.missing_sections), [])

    def test_hybrid_rank_and_evidence_projection(self) -> None:
        chunks = [
            {
                "path": "App/main.py",
                "symbol_hint": "main bootstrap",
                "snippet": "entrypoint startup bootstrap",
                "category": "entrypoint",
                "score": 0.4,
                "semantic": 0.2,
            },
            {
                "path": "Backend/store.py",
                "symbol_hint": "save sqlite",
                "snippet": "persistence database storage sqlite",
                "category": "persistence",
                "score": 0.3,
                "semantic": 0.3,
            },
        ]
        ranked = hybrid_rank_chunks(chunks, question="entrypoint persistence architecture")
        self.assertEqual(len(ranked), 2)
        self.assertIn("hybrid_score", ranked[0])
        self.assertIn("score_breakdown", ranked[0])
        ev = build_evidence_items(ranked, root_abs="/tmp/demo")
        self.assertGreaterEqual(len(ev), 2)
        self.assertTrue(any(item.file_path.startswith("/tmp/demo/") for item in ev))

    def test_run_executor_none_is_non_mutating(self) -> None:
        result = run_executor(
            executor_mode="none",
            prompt="hello",
            cwd=str(pathlib.Path(".").resolve()),
            timeout_sec=10,
        )
        payload = result.to_dict()
        self.assertEqual(payload.get("executor_mode"), "none")
        self.assertFalse(bool(payload.get("attempted")))
        self.assertEqual(payload.get("status"), "skipped")


if __name__ == "__main__":
    unittest.main()

