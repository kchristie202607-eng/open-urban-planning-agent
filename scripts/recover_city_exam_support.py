from __future__ import annotations

import zlib
from pathlib import Path

OBJECTS = Path(r"C:\Users\admin\Documents\2026-716-New project\.git\objects")
OUTPUT = Path("tmp/city_exam_support")
OUTPUT.mkdir(parents=True, exist_ok=True)

TARGETS = {
    "7258b7f194d83eaf81c1360be9945ee40a38447c": "遵义市2026年城市体检报告_社区维度成果补充稿.docx",
    "21e39b793ad12e4376de5589d1bbf7d76d2868b9": "遵义片区体检工作任务书解析初稿.docx",
    "769de1f0ac0bb261665f901fb7ce5f0d0f8ad924": "遵义片区体检工作任务书解析初稿_另一版本.docx",
    "01947fee7499df39be28cabb9f7ff0809db6e930": "资料需求清单.json",
    "1025eebf8f7c7657fb309f4e36e397eb7d033fd9": "project.yaml",
    "043b65beb5e45af5036cf8ba2279c4c0f7197b60": "初始化记录.md",
}

for sha, name in TARGETS.items():
    obj = OBJECTS / sha[:2] / sha[2:]
    raw = zlib.decompress(obj.read_bytes())
    header, body = raw.split(b"\x00", 1)
    kind, size = header.decode("ascii").split()
    if kind != "blob" or int(size) != len(body):
        raise ValueError(f"Invalid blob: {sha}")
    (OUTPUT / name).write_bytes(body)
    print(f"{name}\t{len(body)}")
