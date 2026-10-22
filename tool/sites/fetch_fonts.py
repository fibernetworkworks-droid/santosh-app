"""Fetch the website font files (SIL Open Font Licence families from Fontsource on npm) into
server/app/site/assets/fonts/ as <slug>-<subset>-<weight>.woff2. Run once when the font list changes:
    python tool/sites/fetch_fonts.py
"""
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "server/app/site/assets/fonts"
sys.path.insert(0, str(ROOT / "server"))
from app.site import taxonomy as T  # noqa: E402

WEIGHTS = (400, 700)


def slug(fam: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", fam.lower()).strip("-")


def main() -> None:
    fams = sorted({v for p in T.FONTS.values() for v in (p["head"], p["body"], p["deva"])})
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {}
    with tempfile.TemporaryDirectory() as td:
        for fam in fams:
            pkg = f"@fontsource/{slug(fam)}"
            r = subprocess.run(["npm", "pack", pkg, "--silent"], cwd=td, capture_output=True, text=True)
            if r.returncode != 0 or not r.stdout.strip():
                print("missing", pkg, r.stderr[:200])
                continue
            tgz = Path(td) / r.stdout.strip().splitlines()[-1]
            dest = Path(td) / slug(fam)
            with tarfile.open(tgz) as tf:
                tf.extractall(dest, filter="data")
            files = list((dest / "package/files").glob("*.woff2"))
            got = []
            for sub in ("latin", "devanagari"):
                for w in WEIGHTS:
                    cands = [f for f in files if f.name == f"{slug(fam)}-{sub}-{w}-normal.woff2"]
                    if not cands:      # single-weight display fonts
                        cands = sorted(f for f in files if re.fullmatch(rf"{slug(fam)}-{sub}-\d+-normal\.woff2", f.name))[:1]
                    if cands:
                        name = f"{slug(fam)}-{sub}-{w}.woff2"
                        shutil.copy(cands[0], OUT / name)
                        got.append(name)
            lic = (dest / "package/LICENSE")
            meta[fam] = {"files": got, "license": lic.read_text()[:120].splitlines()[0] if lic.exists() else "OFL-1.1"}
            print(fam, len(got))
    (OUT / "fonts.json").write_text(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
