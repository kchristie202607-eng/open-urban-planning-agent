"""
Public, data-safe area-survey system tests for OUPAP.

Covers:
  * all shipped public configs parse as valid JSON,
  * the synthetic public knowledge config + operational rules are indexable.

The previous version referenced the private instance's ``project_state`` and an
internal ``.agents/skills`` audit script; those assertions have been removed so
the suite runs with only public artifacts.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kb_index import iter_records


class AreaSurveySystemTests(unittest.TestCase):
    def test_public_configs_parse(self):
        for relative in [
            "config/area_survey_agents.json",
            "config/area_survey_workflow.json",
            "config/geospatial_capabilities.json",
            "config/area_survey_knowledge.json",
            "config/operational_rules.json",
        ]:
            with self.subTest(relative):
                json.loads((ROOT / relative).read_text(encoding="utf-8"))

    def test_knowledge_is_indexable(self):
        records = iter_records()
        ids = {record["chunk_id"] for record in records}
        # synthetic public knowledge entries
        for expected in ("AS-SURV-001", "AS-SURV-002", "AS-SURV-003"):
            self.assertIn(expected, ids)
        # operational rules (KB C)
        self.assertIn("C-VIS-002", ids)


if __name__ == "__main__":
    unittest.Main()
