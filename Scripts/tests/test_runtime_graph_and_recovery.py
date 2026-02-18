from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from codex_mem import (
    extract_graph_lite_edges,
    fetch_graph_lite_neighbor_scores,
    open_db,
    run_coverage_recovery_loop,
    upsert_graph_lite_edges,
)


class GraphLiteAndRecoveryTests(unittest.TestCase):
    def test_graph_lite_edges_are_persisted_and_scored(self) -> None:
        chunks = [
            {
                "path": "App/main.py",
                "symbol_hint": "bootstrap main",
                "categories": ["entrypoint"],
            },
            {
                "path": "App/store.py",
                "symbol_hint": "save sqlite",
                "categories": ["persistence"],
            },
            {
                "path": "Backend/ai.py",
                "symbol_hint": "generate stream",
                "categories": ["ai_generation"],
            },
        ]
        edges = extract_graph_lite_edges(chunks)
        self.assertTrue(edges)

        with tempfile.TemporaryDirectory(prefix="cm_graph_") as tmp:
            root = pathlib.Path(tmp)
            conn = open_db(root, ".codex_mem")
            written = upsert_graph_lite_edges(conn, project="demo", edges=edges)
            conn.commit()
            self.assertGreater(written, 0)
            scores = fetch_graph_lite_neighbor_scores(
                conn,
                project="demo",
                paths=["App/main.py", "App/store.py", "Backend/ai.py"],
            )
            self.assertIn("App/main.py", scores)
            self.assertIn("App/store.py", scores)
            self.assertIn("Backend/ai.py", scores)

    def test_coverage_recovery_loop_adds_pass_and_records_run(self) -> None:
        initial_payload = {
            "chunks": [
                {
                    "path": "App/main.py",
                    "symbol_hint": "main bootstrap",
                    "snippet": "entrypoint startup bootstrap",
                    "category": "entrypoint",
                }
            ]
        }
        initial_gate = {
            "profile": "onboarding",
            "required_categories": ["entrypoint", "persistence", "ai_generation"],
            "present_categories": ["entrypoint"],
            "missing_categories": ["persistence", "ai_generation"],
            "pass": False,
            "second_pass_runs": [],
        }
        probe_payload = {
            "chunks": [
                {
                    "path": "Backend/store.py",
                    "symbol_hint": "save sqlite",
                    "snippet": "persistence database sqlite save generation flow stream",
                    "category": "persistence",
                    "categories": ["persistence", "ai_generation"],
                }
            ]
        }
        with mock.patch("codex_mem.run_repo_query", return_value=probe_payload):
            payload, gate, recovery_runs = run_coverage_recovery_loop(
                root=pathlib.Path("."),
                question="learn this project architecture and persistence",
                profile_name="onboarding",
                repo_payload=initial_payload,
                coverage_gate=initial_gate,
                code_top_k=8,
                code_module_limit=8,
                snippet_chars=240,
                repo_index_dir=".codex_knowledge",
                max_passes=2,
            )
        self.assertTrue(bool(gate.get("pass")))
        self.assertTrue(isinstance(payload.get("chunks"), list))
        self.assertGreaterEqual(len(recovery_runs), 1)
        self.assertEqual(recovery_runs[0].get("pass_index"), 1)


if __name__ == "__main__":
    unittest.main()

