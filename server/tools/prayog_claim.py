"""Apply built-claims to the physics syllabus, then re-measure coverage.

Each build agent writes `<claims dir>/<name>.json` = {"<syllabus set-up id>": "<lab id>", ...}. This applies every
claim whose lab REALLY opens, refuses the rest by name, and prints the coverage meter. Agents never edit the
syllabus themselves, so parallel waves cannot collide.

    python3 tools/prayog_claim.py <claims-dir> [--dry]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.prayog import count, service as S  # noqa: E402

SYL = Path(__file__).resolve().parent.parent / "app" / "prayog" / "syllabus" / "physics"


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    claims_dir = Path(argv[0])
    dry = "--dry" in argv
    claims: dict[str, str] = {}
    for f in sorted(claims_dir.glob("*.json")):
        try:
            for k, v in json.loads(f.read_text(encoding="utf-8")).items():
                claims[str(k)] = str(v)
        except Exception as e:                       # noqa: BLE001
            print(f"  ! {f.name} unreadable: {e}")
    print(f"{len(claims)} claim(s) from {claims_dir}")

    applied, refused, unknown = [], [], []
    for path in sorted(SYL.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        for ch in doc.get("chapters") or []:
            for st in ch.get("setups") or []:
                lab_id = claims.pop(st["id"], None)
                if not lab_id:
                    continue
                if not S.get(lab_id):                # a lab that does not open is NOT coverage
                    refused.append((st["id"], lab_id))
                    continue
                if st.get("built") != lab_id:
                    st["built"] = lab_id
                    changed = True
                applied.append((st["id"], lab_id))
        if changed and not dry:
            path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    unknown = sorted(claims)                         # ids that are in no syllabus file

    print(f"  applied {len(applied)}   refused {len(refused)}   unknown set-up id {len(unknown)}")
    for sid, lab in refused:
        print(f"  REFUSED (lab does not open): {sid} -> {lab}")
    for sid in unknown:
        print(f"  UNKNOWN set-up id: {sid}")
    if not dry:
        count.load.__wrapped__ if hasattr(count.load, "__wrapped__") else None
        print()
        count.main(["--cover"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
