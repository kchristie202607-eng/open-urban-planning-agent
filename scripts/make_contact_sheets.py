import argparse
from pathlib import Path

from PIL import Image, ImageDraw

parser = argparse.ArgumentParser()
parser.add_argument(
    "source",
    nargs="?",
    default="tmp/policy_framework/docx_render",
    help="Directory containing page-*.png files",
)
args = parser.parse_args()

SOURCE = Path(args.source)
DEST = SOURCE / "contact_sheets"
DEST.mkdir(parents=True, exist_ok=True)

pages = sorted(
    SOURCE.glob("page-*.png"),
    key=lambda p: int(p.stem.split("-")[-1]),
)

thumb_w = 420
margin = 24
label_h = 32
per_sheet = 4

for start in range(0, len(pages), per_sheet):
    subset = pages[start : start + per_sheet]
    thumbs = []
    for path in subset:
        image = Image.open(path).convert("RGB")
        ratio = thumb_w / image.width
        thumb = image.resize((thumb_w, int(image.height * ratio)))
        thumbs.append((path, thumb))
    height = margin + sum(img.height + label_h + margin for _, img in thumbs)
    sheet = Image.new("RGB", (thumb_w + margin * 2, height), "white")
    draw = ImageDraw.Draw(sheet)
    y = margin
    for path, thumb in thumbs:
        draw.text((margin, y), path.stem, fill="#243240")
        y += label_h
        sheet.paste(thumb, (margin, y))
        y += thumb.height + margin
    sheet.save(DEST / f"sheet-{start // per_sheet + 1}.png")

print(f"{len(pages)} pages -> {len(list(DEST.glob('sheet-*.png')))} sheets")
