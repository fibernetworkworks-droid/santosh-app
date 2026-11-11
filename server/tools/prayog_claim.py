"""Apply built-claims to the physics syllabus, then re-measure coverage.

Each build agent writes `<claims dir>/<name>.json` = {"<syllabus set-up id>": "<lab id>", ...}. A set-up id that is
in more than one level file (e.g. `stefan-constant` in ug and pg) is claimed as "<level>:<id>" (`ug:stefan-constant`);
a bare id still lands on the FIRST file that has it, and the run warns when a bare id is ambiguous. This applies every
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
    for f in sorted(p for p in claims_dir.glob("*.json") if not p.name.startswith("_")):
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
            # a flat {set-up: lab} map, or a report whose "built" / "claims" key holds it
            for src in ([doc] + [doc[k] for k in ("built", "claims", "mapping") if isinstance(doc.get(k), dict)]):
                for k, v in src.items():
                    if isinstance(v, str):
                        claims[str(k)] = v
        except Exception as e:                       # noqa: BLE001
            print(f"  ! {f.name} unreadable: {e}")
    # A decision to NOT count a row must be durable: `_revoked.json` (a list of set-up ids) wins over any claim and
    # clears a `built` already written, so a row dropped as a partial match never creeps back in on a later run.
    revoked: set[str] = set()
    rf = SYL.parent / "revoked.json"
    if rf.exists():
        revoked = set((json.loads(rf.read_text(encoding="utf-8")).get("revoked") or {}))
        for rid in revoked:
            claims.pop(rid, None)
    print(f"{len(claims)} claim(s) from {claims_dir}" + (f"  ({len(revoked)} revoked)" if revoked else ""))
    seen: dict[str, list[str]] = {}
    for path in sorted(SYL.glob("*.json")):
        for ch in json.loads(path.read_text(encoding="utf-8")).get("chapters") or []:
            for st in ch.get("setups") or []:
                seen.setdefault(st["id"], []).append(path.stem)
    for k in claims:
        if ":" not in k and len(seen.get(k, [])) > 1:
            print(f"  ! '{k}' is in {', '.join(seen[k])}: it lands on {seen[k][0]}; write '<level>:{k}' to pick the level")

    applied, refused, unknown = [], [], []
    for path in sorted(SYL.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        level = path.stem
        for ch in doc.get("chapters") or []:
            for st in ch.get("setups") or []:
                if st["id"] in revoked and st.get("built"):
                    del st["built"]
                    changed = True
                lab_id = claims.pop(f"{level}:{st['id']}", None) or claims.pop(st["id"], None)
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
