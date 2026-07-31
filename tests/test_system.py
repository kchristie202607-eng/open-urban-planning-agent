"""
Public, data-safe system tests for OUPAP.

These tests run entirely on SYNTHETIC fixtures under ``tests/fixtures/processed``
(no private planning data required). They cover:
  * the knowledge-base index/build on synthetic chunks + public configs,
  * the workflow engine math/finance/validation on ``examples/demo_project.json``,
  * the visual-quality aspect-ratio contract.

The previously instance-coupled assertions (which referenced private
``data/processed`` and ``project_state``) have been removed; see
``tests/fixtures`` and ``scripts/generate_synthetic_kb.py``.
"""
from __future__ import annotations

import json
import math
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kb_index import (
    CHUNKS_DIR,
    DB_PATH,
    PROCESSED_DIR,
    KnowledgeBase,
    build_index,
)
from run_workflow import calculate_finance, calculate_metrics, run, validate
from visual_quality import (
    fit_web_mercator_bounds,
    make_visual_workplan,
    map_aspect_ratio_check,
    validate_visual_workplan,
)


class KnowledgeBaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build_index()

    def test_index_contains_expected_documents(self):
        with sqlite3.connect(str(DB_PATH)) as connection:
            documents = {
                row[0]
                for row in connection.execute(
                    "SELECT DISTINCT document_id FROM chunks"
                )
            }
        # handbook (KB A), guizhou_plan (KB B), production_rules (KB C),
        # plus the synthetic public knowledge config.
        for expected in (
            "handbook",
            "guizhou_plan",
            "production_rules_20260730",
            "area_survey_knowledge_public",
        ):
            self.assertIn(expected, documents)

    def test_search_returns_traceable_evidence(self):
        results = KnowledgeBase().search(
            "城市更新片区策划", limit=3, knowledge_base="A"
        )
        self.assertTrue(results)
        self.assertTrue(all(item["pdf_page"] >= 1 for item in results))
        self.assertTrue(all(item["source_file"].endswith(".pdf") for item in results))

    def test_operational_rules_are_searchable(self):
        results = KnowledgeBase().search(
            "卫片 GIS 等比例 拉伸", limit=50, knowledge_base="C"
        )
        self.assertTrue(results)
        self.assertTrue(any(item["chunk_id"] == "C-VIS-002" for item in results))
        self.assertTrue(
            any(item["source_type"] == "internal_rule" for item in results)
        )

    def test_processed_records_have_required_fields(self):
        chunk_required = {
            "chunk_id",
            "document_id",
            "knowledge_base",
            "source_file",
            "pdf_page",
            "text",
            "extraction_method",
            "confidence",
            "document_status",
        }
        candidate_required = {
            "item_id",
            "document_id",
            "knowledge_base",
            "rule_category",
            "mandatory_level",
            "evidence",
            "confidence",
            "review_status",
        }
        for path in sorted(CHUNKS_DIR.glob("*.ndjson")):
            for line in path.read_text(encoding="utf-8").splitlines():
                record = json.loads( line )
                self.assertTrue(chunk_required <= record.keys())
                self.assertGreaterEqual(record["pdf_page"], 1)
                self.assertTrue(0 <= record["confidence"] <= 1)
        for path in sorted((PROCESSED_DIR / "candidates").glob("*.ndjson")):
            for line in path.read_text(encoding="utf-8").splitlines():
                record = json.loads( line )
                self.assertTrue(candidate_required <= record.keys())
                self.assertTrue(0 <= record["confidence"] <= 1)
                self.assertGreaterEqual(record["evidence"]["pdf_page"], 1)

    def test_manifest_counts_reconcile(self):
        manifest = json.loads(
            (PROCESSED_DIR / "manifest.json").read_text(encoding="utf-8")
        )
        for document in manifest["documents"]:
            document_id = document["document_id"]
            chunk_lines = (
                CHUNKS_DIR / f"{document_id}.ndjson"
            ).read_text(encoding="utf-8").splitlines()
            candidate_lines = (
                PROCESSED_DIR
                / "candidates"
                / f"{document_id}.ndjson"
            ).read_text(encoding="utf-8").splitlines()
            self.assertEqual(document["chunk_count"], len(chunk_lines))
            self.assertEqual(document["candidate_count"], len(candidate_lines))


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.project_path = ROOT / "examples" / "demo_project.json"
        self.project = json.loads(self.project_path.read_text(encoding="utf-8"))

    def test_demo_input_valid(self):
        self.assertEqual(validate(self.project), [])

    def test_metrics_reconcile(self):
        metrics = calculate_metrics(self.project)
        self.assertAlmostEqual(
            metrics["total_gfa_m2"],
            metrics["site_area_m2"] * metrics["target_far"],
            places=2,
        )
        self.assertTrue(
            math.isclose(
                sum(metrics["program_gfa_m2"].values()),
                metrics["total_gfa_m2"],
                rel_tol=0.001,
            )
        )

    def test_finance_reconciles(self):
        metrics = calculate_metrics(self.project)
        finance = calculate_finance(self.project, metrics)
        components = (
            finance["new_construction_cost_yuan"]
            + finance["renovation_cost_yuan"]
            + finance["public_space_cost_yuan"]
            + finance["other_cost_yuan"]
            + finance["contingency_yuan"]
        )
        self.assertAlmostEqual(components, finance["total_investment_yuan"], places=2)

    def test_visual_plan_prohibits_nonuniform_scaling(self):
        plan = make_visual_workplan(self.project)
        review = validate_visual_workplan(plan)
        self.assertTrue(review["passed"])
        self.assertTrue(plan["rendering_policy"]["preserve_aspect_ratio"])
        self.assertFalse(plan["rendering_policy"]["allow_nonuniform_scaling"])
        self.assertTrue(
            all(
                item.get("required_data") and item.get("drawing_requirements")
                for item in plan["figures"]
                if item["evidence_class"] == "placeholder_brief"
            )
        )

    def test_web_mercator_viewport_matches_canvas(self):
        fitted = fit_web_mercator_bounds(
            [106.914475486, 27.708718974, 106.923458776, 27.720038408],
            1800,
            1180,
        )
        result = map_aspect_ratio_check(fitted, 1800, 1180)
        self.assertTrue(result["passed"])
        self.assertLessEqual(result["relative_error"], 1e-6)

    def test_invalid_visual_stretch_is_rejected(self):
        bad = json.loads(json.dumps(self.project))
        bad["visual_requirements"] = {
            "preserve_aspect_ratio": False,
            "allow_nonuniform_scaling": True,
        }
        errors = validate(bad)
        self.assertTrue(any("非等比例" in item for item in errors))

    def test_end_to_end_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "demo"
            result = run(self.project_path, output)
            expected = {
                "scenario.json",
                "evidence.json",
                "massing.geojson",
                "visual_workplan.json",
                "project_list.csv",
                "quality_report.json",
                "report.md",
            }
            self.assertEqual(set(result["artifacts"]), expected)
            quality = json.loads(
                (output / "quality_report.json").read_text(encoding="utf-8")
            )
            self.assertEqual(quality["status"], "带条件通过")


if __name__ == "__main__":
    unittest.Main()
