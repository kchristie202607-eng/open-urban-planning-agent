#!/usr/bin/env python3
"""
Generate synthetic, public knowledge-base fixtures for OUPAP.

These fixtures let the test suite (and `kb_index.build_index`) run WITHOUT any
private planning data. They contain NO real policy text, client data, GIS data,
or project specifics — only benign, obviously-synthetic placeholders.

Output:
  tests/fixtures/processed/chunks/{handbook,guizhou_plan,production_rules_20260730}.ndjson
  tests/fixtures/processed/candidates/{handbook,guizhou_plan,production_rules_20260730}.ndjson
  tests/fixtures/processed/manifest.json
  config/area_survey_knowledge.json   (synthetic, generic — replaces the private instance KB)
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "processed"
CHUNKS = FIX / "chunks"
CANDIDATES = FIX / "candidates"
CONFIG_DIR = ROOT / "config"

CHUNKS.mkdir(parents=True, exist_ok=True)
CANDIDATES.mkdir(parents=True, exist_ok=True)

# --- synthetic chunk records (knowledge base A: handbook, B: guizhou plan) ---
HANDBOOK_CHUNKS = [
    {
        "chunk_id": f"HB-{i:03d}",
        "document_id": "handbook",
        "knowledge_base": "A",
        "source_file": "urban_renewal_handbook.pdf",
        "pdf_page": 10 + i,
        "text": f"城市更新工作手册（合成样例 {i}）：片区调查应先体检后更新，明确底线管控与公共利益。",
        "extraction_method": "synthetic",
        "confidence": 0.95,
        "document_status": "已复核",
    }
    for i in range(3)
]

GUIZHOU_CHUNKS = [
    {
        "chunk_id": f"GZ-{i:03d}",
        "document_id": "guizhou_plan",
        "knowledge_base": "B",
        "source_file": "guizhou_renewal_plan.pdf",
        "pdf_page": 20 + i,
        "text": f"贵州省城市更新规划（合成样例 {i}）：以片区为单元统筹推进老旧小区与完整社区建设。",
        "extraction_method": "synthetic",
        "confidence": 0.9,
        "document_status": "已复核",
    }
    for i in range(3)
]

PROD_CHUNKS = [
    {
        "chunk_id": f"PR-{i:03d}",
        "document_id": "production_rules_20260730",
        "knowledge_base": "C",
        "source_file": "production_rules.pdf",
        "pdf_page": 1 + i,
        "text": f"生产规范（合成样例 {i}）：成果图件必须区分已有正式图纸、GIS生成图与预留图框。",
        "extraction_method": "synthetic",
        "confidence": 0.98,
        "document_status": "已复核",
    }
    for i in range(3)
]

# --- synthetic candidate records (structured rule/indicator candidates) ---
HANDBOOK_CANDIDATES = [
    {
        "item_id": f"HB-C-{i:03d}",
        "document_id": "handbook",
        "knowledge_base": "A",
        "rule_category": "survey_method",
        "mandatory_level": "recommended",
        "evidence": {"pdf_page": 11 + i, "text": "合成候选指标：片区调查覆盖率。"},
        "confidence": 0.8,
        "review_status": "已复核",
    }
    for i in range(2)
]

GUIZHOU_CANDIDATES = [
    {
        "item_id": f"GZ-C-{i:03d}",
        "document_id": "guizhou_plan",
        "knowledge_base": "B",
        "rule_category": "indicator",
        "mandatory_level": "optional",
        "evidence": {"pdf_page": 21 + i, "text": "合成候选指标：完整社区达标率。"},
        "confidence": 0.75,
        "review_status": "待复核",
    }
    for i in range(2)
]

PROD_CANDIDATES = [
    {
        "item_id": f"PR-C-{i:03d}",
        "document_id": "production_rules_20260730",
        "knowledge_base": "C",
        "rule_category": "quality_gate",
        "mandatory_level": "mandatory",
        "evidence": {"pdf_page": 2 + i, "text": "合成候选校验：等比例投影视口。"},
        "confidence": 0.9,
        "review_status": "已复核",
    }
    for i in range(2)
]


def _write(ndjson_path: Path, records: list[dict]) -> None:
    with ndjson_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


_write(CHUNKS / "handbook.ndjson", HANDBOOK_CHUNKS)
_write(CHUNKS / "guizhou_plan.ndjson", GUIZHOU_CHUNKS)
_write(CHUNKS / "production_rules_20260730.ndjson", PROD_CHUNKS)
_write(CANDIDATES / "handbook.ndjson", HANDBOOK_CANDIDATES)
_write(CANDIDATES / "guizhou_plan.ndjson", GUIZHOU_CANDIDATES)
_write(CANDIDATES / "production_rules_20260730.ndjson", PROD_CANDIDATES)

manifest = {
    "generated_by": "scripts/generate_synthetic_kb.py (synthetic, public)",
    "documents": [
        {
            "document_id": "handbook",
            "chunk_count": len(HANDBOOK_CHUNKS),
            "candidate_count": len(HANDBOOK_CANDIDATES),
        },
        {
            "document_id": "guizhou_plan",
            "chunk_count": len(GUIZHOU_CHUNKS),
            "candidate_count": len(GUIZHOU_CANDIDATES),
        },
        {
            "document_id": "production_rules_20260730",
            "chunk_count": len(PROD_CHUNKS),
            "candidate_count": len(PROD_CANDIDATES),
        },
    ],
}
(FIX / "manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
)

# --- synthetic, generic public knowledge config (replaces private instance KB) ---
knowledge = {
    "document_id": "area_survey_knowledge_public",
    "knowledge_base": "C",
    "title": "片区调查通用知识（合成公开版）",
    "document_status": "synthetic",
    "entries": [
        {
            "item_id": "AS-SURV-001",
            "category": "survey_scope",
            "review_status": "已复核",
            "source_locator": "通用调查范围",
            "source_type": "public_method",
            "text": "片区调查范围应覆盖现状、问题、资源与意愿四个维度，并与上位规划衔接。",
        },
        {
            "item_id": "AS-SURV-002",
            "category": "evidence_rule",
            "review_status": "已复核",
            "source_locator": "证据留痕",
            "source_type": "public_method",
            "text": "每条规范性结论须附来源文件、页码与原文，区分已复核约束与模型推算值。",
        },
        {
            "item_id": "AS-SURV-003",
            "category": "visual_rule",
            "review_status": "已复核",
            "source_locator": "制图规则",
            "source_type": "public_method",
            "text": "卫片与GIS图层须使用同一投影变换，禁止非等比例拉伸，视口与画布宽高比相对误差不超过1e-6。",
        },
    ],
}
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
(CONFIG_DIR / "area_survey_knowledge.json").write_text(
    json.dumps(knowledge, ensure_ascii=False, indent=2), encoding="utf-8"
)

print("synthetic KB fixtures written:")
print(f"  chunks: {len(HANDBOOK_CHUNKS) + len(GUIZHOU_CHUNKS) + len(PROD_CHUNKS)} lines")
print(f"  candidates: {len(HANDBOOK_CANDIDATES) + len(GUIZHOU_CANDIDATES) + len(PROD_CANDIDATES)} lines")
print(f"  config/area_survey_knowledge.json: {len(knowledge['entries'])} entries")
