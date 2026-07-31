from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# Public by default; overridable for tests / offline use without private data.
# Set OUPAP_PROCESSED_DIR to a directory containing `chunks/` and `candidates/`.
# Set OUPAP_KB_DB to point the index sqlite elsewhere (e.g. a temp path).
PROCESSED_DIR = Path(
    os.environ.get("OUPAP_PROCESSED_DIR", str(ROOT / "data" / "processed"))
)
CHUNKS_DIR = PROCESSED_DIR / "chunks"
DB_PATH = Path(os.environ.get("OUPAP_KB_DB", str(ROOT / "data" / "kb.sqlite")))
OPERATIONAL_RULES_PATH = ROOT / "config" / "operational_rules.json"
AREA_SURVEY_KNOWLEDGE_PATH = ROOT / "config" / "area_survey_knowledge.json"


def iter_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(CHUNKS_DIR.glob("*.ndjson")):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    records.append(json.loads(line))
    if OPERATIONAL_RULES_PATH.exists():
        payload = json.loads(
            OPERATIONAL_RULES_PATH.read_text(encoding="utf-8")
        )
        for index, rule in enumerate(payload["rules"], start=1):
            records.append(
                {
                    "chunk_id": rule["rule_id"],
                    "document_id": payload["document_id"],
                    "knowledge_base": payload["knowledge_base"],
                    "source_file": OPERATIONAL_RULES_PATH.name,
                    "pdf_page": None,
                    "source_locator": f"规则 {rule['rule_id']}",
                    "source_type": "internal_rule",
                    "text": (
                        f"{rule['category']}｜{rule['severity']}｜"
                        f"{rule['requirement']}｜校验器：{rule['validator']}"
                    ),
                    "extraction_method": "structured",
                    "confidence": 1.0,
                    "document_status": payload["document_status"],
                }
            )
    if AREA_SURVEY_KNOWLEDGE_PATH.exists():
        payload = json.loads(
            AREA_SURVEY_KNOWLEDGE_PATH.read_text(encoding="utf-8")
        )
        for entry in payload["entries"]:
            records.append(
                {
                    "chunk_id": entry["item_id"],
                    "document_id": payload["document_id"],
                    "knowledge_base": payload["knowledge_base"],
                    "source_file": AREA_SURVEY_KNOWLEDGE_PATH.name,
                    "pdf_page": None,
                    "source_locator": entry["source_locator"],
                    "source_type": entry["source_type"],
                    "text": (
                        f"{entry['category']}｜{entry['review_status']}｜"
                        f"{entry['text']}"
                    ),
                    "extraction_method": "structured",
                    "confidence": 1.0 if entry["review_status"] == "已复核" else 0.7,
                    "document_status": payload["document_status"],
                }
            )
    return records


def build_index(db_path: Path = DB_PATH) -> dict[str, Any]:
    records = iter_records()
    if not records:
        raise RuntimeError("未找到检索块，请先运行 src/build_kb.py。")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            DROP TABLE IF EXISTS chunks;
            DROP TABLE IF EXISTS chunk_fts;
            CREATE TABLE chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                knowledge_base TEXT NOT NULL,
                source_file TEXT NOT NULL,
                pdf_page INTEGER,
                source_locator TEXT NOT NULL,
                source_type TEXT NOT NULL,
                text TEXT NOT NULL,
                extraction_method TEXT NOT NULL,
                confidence REAL NOT NULL,
                document_status TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE chunk_fts USING fts5(
                chunk_id UNINDEXED,
                text,
                tokenize='unicode61'
            );
            """
        )
        for record in records:
            values = (
                record["chunk_id"],
                record["document_id"],
                record["knowledge_base"],
                record["source_file"],
                record.get("pdf_page"),
                record.get("source_locator")
                or f"PDF 第 {record['pdf_page']} 页",
                record.get("source_type", "pdf"),
                record["text"],
                record["extraction_method"],
                record["confidence"],
                record["document_status"],
            )
            connection.execute(
                "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                values,
            )
            connection.execute(
                "INSERT INTO chunk_fts(chunk_id, text) VALUES (?, ?)",
                (record["chunk_id"], record["text"]),
            )
        connection.commit()
    return {
        "database": str(db_path),
        "chunk_count": len(records),
        "documents": sorted({record["document_id"] for record in records}),
    }


def ngrams(text: str, size: int = 2) -> set[str]:
    compact = re.sub(r"[\W_]+", "", text, flags=re.UNICODE)
    if len(compact) < size:
        return {compact} if compact else set()
    return {compact[index : index + size] for index in range(len(compact) - size + 1)}


def excerpt(text: str, query: str, limit: int = 360) -> str:
    terms = [term for term in re.split(r"\s+", query) if term]
    positions = [text.find(term) for term in terms if text.find(term) >= 0]
    center = min(positions) if positions else 0
    start = max(0, center - 80)
    end = min(len(text), start + limit)
    result = text[start:end].strip()
    if start:
        result = "…" + result
    if end < len(text):
        result += "…"
    return result


class KnowledgeBase:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        if not db_path.exists():
            build_index(db_path)

    def search(
        self, query: str, limit: int = 5, knowledge_base: str | None = None
    ) -> list[dict[str, Any]]:
        where = ""
        parameters: list[Any] = []
        if knowledge_base:
            where = " WHERE knowledge_base = ?"
            parameters.append(knowledge_base)
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT * FROM chunks" + where, parameters
            ).fetchall()

        query_grams = ngrams(query)
        query_terms = [term for term in re.split(r"\s+", query) if term]
        ranked: list[tuple[float, sqlite3.Row]] = []
        for row in rows:
            text = row["text"]
            text_grams = ngrams(text)
            overlap = len(query_grams & text_grams) / max(1, len(query_grams))
            term_hits = sum(1 for term in query_terms if term in text)
            exact_bonus = 2.0 if query in text else 0.0
            confidence_weight = 0.7 + 0.3 * float(row["confidence"])
            score = (overlap * 5 + term_hits + exact_bonus) * confidence_weight
            if score > 0:
                ranked.append((score, row))
        ranked.sort(
            key=lambda item: (
                -item[0],
                item[1]["pdf_page"]
                if item[1]["pdf_page"] is not None
                else 0,
            )
        )

        results: list[dict[str, Any]] = []
        for score, row in ranked[:limit]:
            results.append(
                {
                    "chunk_id": row["chunk_id"],
                    "score": round(score, 4),
                    "document_id": row["document_id"],
                    "knowledge_base": row["knowledge_base"],
                    "source_file": row["source_file"],
                    "pdf_page": row["pdf_page"],
                    "source_locator": row["source_locator"],
                    "source_type": row["source_type"],
                    "quotation": excerpt(row["text"], query),
                    "extraction_method": row["extraction_method"],
                    "confidence": row["confidence"],
                    "document_status": row["document_status"],
                }
            )
        return results


def main() -> int:
    parser = argparse.ArgumentParser(description="片区策划知识库索引与检索")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("build")
    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument("--kb", choices=["A", "B", "C"])
    search_parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    if args.command == "build":
        print(json.dumps(build_index(), ensure_ascii=False, indent=2))
        return 0

    kb = KnowledgeBase()
    print(
        json.dumps(
            kb.search(args.query, args.limit, args.kb),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
