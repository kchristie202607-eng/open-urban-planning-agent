from __future__ import annotations

import io
import re
import zipfile
import zlib
from pathlib import Path

OBJECTS = Path(r"C:\Users\admin\Documents\2026-716-New project\.git\objects")
KEYWORDS = ("城市体检", "片区体检", "遵义", "社区体检", "指标体系", "体检报告")


def iter_objects():
    for folder in OBJECTS.iterdir():
        if not folder.is_dir() or len(folder.name) != 2:
            continue
        for file in folder.iterdir():
            if len(file.name) != 38:
                continue
            try:
                raw = zlib.decompress(file.read_bytes())
                header, body = raw.split(b"\x00", 1)
                kind, size = header.decode("ascii").split()
                if kind == "blob":
                    yield folder.name + file.name, int(size), body
            except Exception:
                continue


def xml_text(data: bytes) -> str:
    text = data.decode("utf-8", errors="ignore")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text)


matches = []
for sha, size, body in iter_objects():
    magic = body[:8]
    labels = []
    snippets = []
    if body.startswith(b"PK\x03\x04"):
        labels.append("ZIP")
        try:
            with zipfile.ZipFile(io.BytesIO(body)) as zf:
                names = zf.namelist()
                if "word/document.xml" in names:
                    labels.append("DOCX")
                    text = xml_text(zf.read("word/document.xml"))
                    for keyword in KEYWORDS:
                        pos = text.find(keyword)
                        if pos >= 0:
                            snippets.append(text[max(0, pos - 80) : pos + 220])
                            break
                elif "ppt/presentation.xml" in names:
                    labels.append("PPTX")
                elif "xl/workbook.xml" in names:
                    labels.append("XLSX")
                else:
                    labels.append("ZIP_OTHER")
        except Exception:
            labels.append("ZIP_BROKEN")
    elif body.startswith(b"%PDF"):
        labels.append("PDF")
    elif body.startswith(b"\x89PNG"):
        labels.append("PNG")
    elif body.startswith(b"\xff\xd8\xff"):
        labels.append("JPEG")
    elif body.startswith(b"II*\x00") or body.startswith(b"MM\x00*"):
        labels.append("TIFF")
    elif body[:4] == b"\xd0\xcf\x11\xe0":
        labels.append("OLE")
    else:
        text = body.decode("utf-8", errors="ignore")
        if any(k in text for k in KEYWORDS):
            labels.append("TEXT")
            for keyword in KEYWORDS:
                pos = text.find(keyword)
                if pos >= 0:
                    snippets.append(re.sub(r"\s+", " ", text[max(0, pos - 80) : pos + 220]))
                    break
    if snippets:
        matches.append((sha, size, ",".join(labels), snippets[0]))

print(f"MATCHES={len(matches)}")
for sha, size, labels, snippet in sorted(matches, key=lambda row: row[1], reverse=True):
    print(f"{sha}\t{size}\t{labels}\t{snippet}")
