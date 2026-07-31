from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCAL_DEPS = ROOT / ".deps"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))

from pypdf import PdfReader

CONFIG_PATH = ROOT / "config" / "sources.json"
OUTPUT_ROOT = ROOT / "data" / "processed"

RULE_TERMS = (
    "应当",
    "应",
    "必须",
    "不得",
    "严禁",
    "禁止",
    "不应",
    "宜",
    "可",
    "鼓励",
    "力争",
    "确保",
)
INDICATOR_TERMS = (
    "容积率",
    "建筑密度",
    "绿地率",
    "停车",
    "配建",
    "面积",
    "比例",
    "半径",
    "距离",
    "高度",
    "层数",
    "人口",
    "投资",
    "资金",
    "收益",
    "成本",
    "覆盖率",
    "完成率",
)
NUMBER_RE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:%|％|平方米|万平方米|平方公里|公顷|米|公里|个|处|项|户|人|年|万元|亿元|栋|层)"
)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？；])|\n+")


def json_dump_line(handle: Any, record: dict[str, Any]) -> None:
    handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_sources() -> list[dict[str, Any]]:
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)["sources"]


def iter_text_pages(path: Path) -> Iterable[tuple[int, str, float]]:
    reader = PdfReader(str(path))
    for index, page in enumerate(reader.pages, start=1):
        text = normalize_text(page.extract_text() or "")
        confidence = 1.0 if text else 0.0
        yield index, text, confidence


def iter_ocr_pages(path: Path) -> Iterable[tuple[int, str, float]]:
    import numpy as np
    import pypdfium2 as pdfium
    from rapidocr import RapidOCR

    engine = RapidOCR()
    pdf = pdfium.PdfDocument(str(path))
    for index in range(len(pdf)):
        page = pdf[index]
        bitmap = page.render(scale=2.0, rotation=0)
        image = bitmap.to_pil()
        result = engine(np.asarray(image))
        texts = list(result.txts or [])
        scores = [float(score) for score in (result.scores or [])]
        text = normalize_text("\n".join(texts))
        confidence = round(sum(scores) / len(scores), 4) if scores else 0.0
        yield index + 1, text, confidence
        image.close()
        bitmap.close()
        page.close()
    pdf.close()


def chunks(text: str, target_chars: int = 900) -> Iterable[str]:
    paragraphs = [part.strip() for part in re.split(r"\n+", text) if part.strip()]
    current: list[str] = []
    size = 0
    for paragraph in paragraphs:
        if current and size + len(paragraph) > target_chars:
            yield "\n".join(current)
            current = []
            size = 0
        if len(paragraph) > target_chars:
            for start in range(0, len(paragraph), target_chars):
                piece = paragraph[start : start + target_chars]
                if piece:
                    yield piece
            continue
        current.append(paragraph)
        size += len(paragraph)
    if current:
        yield "\n".join(current)


def classify(text: str) -> str:
    mappings = (
        ("历史文化保护", ("历史文化", "文物", "历史建筑", "保护传承")),
        ("资金与财务", ("资金", "融资", "投资", "收益", "成本", "专项债")),
        ("公共服务", ("公共服务", "公共设施", "社区服务", "停车", "公园")),
        ("开发强度", ("容积率", "建筑密度", "绿地率", "高度", "开发强度")),
        ("空间划定", ("片区划定", "更新片区", "更新单元", "边界", "空间结构")),
        ("更新方式", ("微改造", "拆除新建", "综合整治", "修缮", "改造方式")),
        ("产业与运营", ("产业", "业态", "运营", "招商")),
        ("项目实施", ("项目库", "实施方案", "项目建设", "时序")),
        ("编制程序", ("编制", "审批", "成果形式", "报批", "程序")),
    )
    for category, terms in mappings:
        if any(term in text for term in terms):
            return category
    return "其他"


def mandatory_level(text: str) -> str:
    if any(term in text for term in ("必须", "不得", "严禁", "禁止", "应当")):
        return "强制"
    if any(term in text for term in ("宜", "鼓励", "力争", "可")):
        return "引导"
    return "待判断"


def candidate_sentences(text: str) -> Iterable[str]:
    for sentence in SENTENCE_SPLIT_RE.split(text):
        sentence = sentence.strip()
        if len(sentence) < 8:
            continue
        has_rule = any(term in sentence for term in RULE_TERMS)
        has_indicator = any(term in sentence for term in INDICATOR_TERMS)
        has_number = bool(NUMBER_RE.search(sentence))
        if has_rule or (has_indicator and has_number):
            yield sentence[:1200]


def process_document(source: dict[str, Any]) -> dict[str, Any]:
    document_id = source["document_id"]
    path = Path(source["path"])
    if not path.exists():
        raise FileNotFoundError(f"源文件不存在：{path}")

    pages_dir = OUTPUT_ROOT / "pages"
    chunks_dir = OUTPUT_ROOT / "chunks"
    candidates_dir = OUTPUT_ROOT / "candidates"
    for directory in (pages_dir, chunks_dir, candidates_dir):
        directory.mkdir(parents=True, exist_ok=True)

    page_path = pages_dir / f"{document_id}.ndjson"
    chunk_path = chunks_dir / f"{document_id}.ndjson"
    candidate_path = candidates_dir / f"{document_id}.ndjson"
    method = source["extraction_method"]
    iterator = iter_ocr_pages(path) if method == "ocr" else iter_text_pages(path)

    page_count = 0
    text_chars = 0
    chunk_count = 0
    candidate_count = 0
    confidence_total = 0.0

    with (
        page_path.open("w", encoding="utf-8", newline="\n") as page_file,
        chunk_path.open("w", encoding="utf-8", newline="\n") as chunk_file,
        candidate_path.open("w", encoding="utf-8", newline="\n") as candidate_file,
    ):
        for pdf_page, text, confidence in iterator:
            page_count += 1
            text_chars += len(text)
            confidence_total += confidence
            page_record = {
                "document_id": document_id,
                "knowledge_base": source["knowledge_base"],
                "title": source["title"],
                "source_file": path.name,
                "source_path": str(path),
                "pdf_page": pdf_page,
                "extraction_method": method,
                "confidence": confidence,
                "document_status": source["document_status"],
                "evidence_text": text,
            }
            json_dump_line(page_file, page_record)

            for chunk_index, chunk_text in enumerate(chunks(text), start=1):
                chunk_count += 1
                json_dump_line(
                    chunk_file,
                    {
                        "chunk_id": f"{document_id}-p{pdf_page:03d}-c{chunk_index:02d}",
                        "document_id": document_id,
                        "knowledge_base": source["knowledge_base"],
                        "source_file": path.name,
                        "pdf_page": pdf_page,
                        "text": chunk_text,
                        "extraction_method": method,
                        "confidence": confidence,
                        "document_status": source["document_status"],
                    },
                )

            for sentence_index, sentence in enumerate(
                candidate_sentences(text), start=1
            ):
                candidate_count += 1
                json_dump_line(
                    candidate_file,
                    {
                        "item_id": (
                            f"{source['knowledge_base']}-{document_id}-"
                            f"p{pdf_page:03d}-i{sentence_index:02d}"
                        ),
                        "document_id": document_id,
                        "knowledge_base": source["knowledge_base"],
                        "project_type": [],
                        "rule_category": classify(sentence),
                        "indicator": next(
                            (
                                term
                                for term in INDICATOR_TERMS
                                if term in sentence
                            ),
                            None,
                        ),
                        "operator": None,
                        "value": next(iter(NUMBER_RE.findall(sentence)), None),
                        "unit": None,
                        "mandatory_level": mandatory_level(sentence),
                        "applicable_conditions": {},
                        "evidence": {
                            "source_file": path.name,
                            "pdf_page": pdf_page,
                            "quotation": sentence,
                            "extraction_method": method,
                        },
                        "confidence": confidence,
                        "review_status": "待人工复核",
                        "review_notes": None,
                    },
                )

            print(
                f"[{document_id}] page {pdf_page}: "
                f"chars={len(text)} confidence={confidence:.3f}",
                flush=True,
            )

    return {
        "document_id": document_id,
        "knowledge_base": source["knowledge_base"],
        "title": source["title"],
        "source_path": str(path),
        "source_sha256": sha256(path),
        "document_status": source["document_status"],
        "extraction_method": method,
        "page_count": page_count,
        "text_chars": text_chars,
        "chunk_count": chunk_count,
        "candidate_count": candidate_count,
        "mean_confidence": round(confidence_total / page_count, 4)
        if page_count
        else 0.0,
        "outputs": {
            "pages": str(page_path.relative_to(ROOT)),
            "chunks": str(chunk_path.relative_to(ROOT)),
            "candidates": str(candidate_path.relative_to(ROOT)),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--document",
        action="append",
        help="仅处理指定 document_id；可重复传入。",
    )
    args = parser.parse_args()

    selected = set(args.document or [])
    sources = [
        source
        for source in load_sources()
        if not selected or source["document_id"] in selected
    ]
    if not sources:
        parser.error("没有匹配的文档。")

    results = [process_document(source) for source in sources]
    manifest_path = OUTPUT_ROOT / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline_version": "0.1.0",
        "documents": results,
        "quality_notice": (
            "候选条目仅供人工复核；征求意见稿不等同于正式生效文件。"
        ),
    }
    with manifest_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"manifest: {manifest_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
