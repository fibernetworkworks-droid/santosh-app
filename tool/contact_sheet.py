"""R0: put every screen picture side by side in one PNG, with its name under it (CI: app-screens.yml).

python3 tool/contact_sheet.py <folder of pngs> <out.png>
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

W = 390          # each picture is shown at its logical width
GAP, LABEL, PER_ROW = 24, 40, 5


def main(src: str, out: str) -> int:
    files = sorted(Path(src).glob("*.png"))
    if not files:
        print("no pictures")
        return 1
    shots = []
    for f in files:
        im = Image.open(f).convert("RGB")
        shots.append((f.stem, im.resize((W, int(im.height * W / im.width)))))
    h = max(im.height for _, im in shots)
    rows = (len(shots) + PER_ROW - 1) // PER_ROW
    cols = min(PER_ROW, len(shots))
    sheet = Image.new("RGB", (cols * W + (cols + 1) * GAP, rows * (h + LABEL) + (rows + 1) * GAP), "#E9E7E1")
    draw = ImageDraw.Draw(sheet)
    for i, (name, im) in enumerate(shots):
        x = GAP + (i % PER_ROW) * (W + GAP)
        y = GAP + (i // PER_ROW) * (h + LABEL + GAP)
        sheet.paste(im, (x, y))
        draw.text((x, y + im.height + 10), name, fill="#1B1A17")
    sheet.save(out)
    print(f"{len(shots)} pictures -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
