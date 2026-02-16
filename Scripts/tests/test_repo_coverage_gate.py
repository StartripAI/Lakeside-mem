from __future__ import annotations

import pathlib
import sys
import unittest

SCRIPT_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from codex_mem import _extract_repo_chunks, ensure_repo_coverage, infer_repo_categories


class RepoCoverageGateTests(unittest.TestCase):
    def test_infer_repo_categories_uses_snippet_and_symbol_hints(self) -> None:
        categories = infer_repo_categories(
            "Scripts/repo_knowledge.py",
            symbol_hint="build_parser, parse_args",
            snippet=(
                "entrypoint startup bootstrap main flow; "
                "persistence database sqlite migration save; "
                "ai generation streaming prism organize"
            ),
        )
        self.assertIn("entrypoint", categories)
        self.assertIn("persistence", categories)
        self.assertIn("ai_generation", categories)

    def test_onboarding_coverage_gate_uses_multi_categories(self) -> None:
        payload = {
            "chunks": [
                {
                    "path": "Scripts/repo_knowledge.py",
                    "start_line": 336,
                    "end_line": 381,
                    "symbol_hint": "build_parser, parse_args",
                    "snippet": (
                        "entrypoint startup bootstrap; "
                        "persistence database storage sqlite; "
                        "ai generation streaming pipeline"
                    ),
                }
            ]
        }

        normalized_chunks = _extract_repo_chunks(payload)
        self.assertEqual(len(normalized_chunks), 1)
        self.assertIn("categories", normalized_chunks[0])
        self.assertIn("entrypoint", normalized_chunks[0]["categories"])
        self.assertIn("persistence", normalized_chunks[0]["categories"])
        self.assertIn("ai_generation", normalized_chunks[0]["categories"])

        _, gate = ensure_repo_coverage(
            root=pathlib.Path("."),
            question="learn this project: architecture, entrypoint, persistence, ai generation",
            profile_name="onboarding",
            repo_payload=payload,
            code_top_k=8,
            code_module_limit=8,
            snippet_chars=240,
            repo_index_dir=".codex_knowledge",
        )

        self.assertTrue(bool(gate.get("pass")))
        self.assertEqual(gate.get("missing_categories"), [])
        present = gate.get("present_categories", [])
        self.assertIn("entrypoint", present)
        self.assertIn("persistence", present)
        self.assertIn("ai_generation", present)

    def test_markdown_snippet_keywords_do_not_force_category(self) -> None:
        categories = infer_repo_categories(
            "Documentation/ARCHITECTURE.md",
            snippet="entrypoint persistence ai generation backend",
        )
        self.assertEqual(categories, ["code"])


if __name__ == "__main__":
    unittest.main()
