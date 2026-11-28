"""The 200 looks of the app's avatar system (lib/ui/avatar_look.dart), served for Hoola DOD.

The files are the same pre-rendered pictures the phone ships in assets/avatars (copied into static/dod/looks so the
server can serve them: the deploy copies server/app only). <id>.webp = the whole person, <id>_head.webp = the face.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

DIR = Path(__file__).resolve().parent.parent / "static" / "dod" / "looks"
_ID = re.compile(r"^[fm]\d{3}$")


@lru_cache(maxsize=1)
def all_looks() -> list[dict]:
    try:
        rows = json.loads((DIR / "looks.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for r in rows:
        lid = str(r.get("id") or "")
        if _ID.match(lid) and (DIR / f"{lid}.webp").exists():
            out.append({"id": lid, "name": r.get("name") or "", "gender": r.get("gender") or lid[0],
                        "city": r.get("city") or "", "country": r.get("country") or "", "region": r.get("region") or "",
                        "head": f"/api/dod/look/{lid}_head.webp", "full": f"/api/dod/look/{lid}.webp"})
    return out


def known(look_id: str) -> bool:
    return any(x["id"] == look_id for x in all_looks())


def file_of(name: str) -> Path | None:
    """The picture for /api/dod/look/<name> - only <id>.webp or <id>_head.webp of a known look."""
    m = re.match(r"^([fm]\d{3})(_head)?\.webp$", name or "")
    if not m or not known(m.group(1)):
        return None
    p = DIR / name
    return p if p.exists() else None
