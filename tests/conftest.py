"""
Pytest bootstrap for OUPAP public tests.

Points the knowledge-base loader at the SYNTHETIC, public fixtures so the suite
runs without any private planning data. These env vars are honoured by
``src/kb_index.py`` and ``src/run_workflow.py``.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

os.environ.setdefault(
    "OUPAP_PROCESSED_DIR",
    str(ROOT / "tests" / "fixtures" / "processed"),
)
os.environ.setdefault(
    "OUPAP_KB_DB",
    str(ROOT / "tests" / "fixtures" / "kb.sqlite"),
)
