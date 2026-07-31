from __future__ import annotations

import json
import re
from pathlib import Path

from pypdf import PdfReader

SOURCES = {
    "审查要点": Path(
        r"E:\xwechat_files\wxid_jvaqcy7c9eg651_650c\msg\file\2026-07"
        r"\住_260629通知：贵州省住房和城乡建设厅关于印发《贵州省城市更新片区策划方案审查要点(试行)》的通知 .pdf"
    ),
    "试点通知": Path(
        r"E:\xwechat_files\wxid_jvaqcy7c9eg651_650c\msg\file\2026-07\试点通知.pdf"
    ),
}


def normalize(text: str) -> str:
    text = text.replace("\u3000", " ").replace("\xa0", " ")
    text = re.sub(r"(?<=[\u3400-\u9fff]) +(?=[\u3400-\u9fff])", "", text)
    text = re.sub(r"(?<=[\u3400-\u9fff]) +(?=[，。；：、！？）》】])", "", text)
    text = re.sub(r"(?<=[（《【]) +(?=[\u3400-\u9fff])", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main() -> None:
    out_dir = Path("tmp/policy_framework")
    out_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, object] = {}
    for name, path in SOURCES.items():
        reader = PdfReader(str(path))
        pages = []
        for page_number, page in enumerate(reader.pages, start=1):
            pages.append(
                {
                    "page": page_number,
                    "text": normalize(page.extract_text() or ""),
                }
            )
        result[name] = {
            "source": str(path),
            "page_count": len(reader.pages),
            "pages": pages,
        }
        txt = "\n\n".join(
            f"===== 第 {item['page']} 页 =====\n{item['text']}" for item in pages
        )
        (out_dir / f"{name}.txt").write_text(txt, encoding="utf-8")
    (out_dir / "sources.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: v["page_count"] for k, v in result.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
