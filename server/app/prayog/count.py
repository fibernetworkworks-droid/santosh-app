"""P0 of docs/PRAYOG_PHYSICS_LAKH_PLAN.md: the physics catalogue of real set-ups, counted honestly.

`prayog/syllabus/physics/<level>.json` lists every distinct experimental set-up of one level, chapter by chapter, each
row citing the syllabus / lab manual it comes from. A set-up's variants are the product of its lists (methods x
samples x unknowns x conditions, each list only what real manuals use). Nothing is counted that is not listed.

    python -m app.prayog.count            # totals per level and chapter
    python -m app.prayog.count --json     # the same as JSON
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

DIR = Path(__file__).resolve().parent / "syllabus" / "physics"
LEVELS = ("school-6-10", "school-11-12", "ug", "pg", "phd")
KINDS = {"practical", "activity", "project", "demonstration", "research-technique", "computational"}
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,80}$")
LISTS = ("methods", "samples", "unknowns", "conditions")


class SyllabusError(ValueError):
    pass


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise SyllabusError(msg)


def check(doc: dict, where: str) -> dict:
    """Validate one level file; raise naming the first problem."""
    _need(isinstance(doc, dict) and doc.get("level") in LEVELS, f"{where}: level must be one of {LEVELS}")
    srcs = {s.get("id"): s for s in doc.get("sources") or []}
    _need(bool(srcs), f"{where}: needs sources")
    for sid, s in srcs.items():
        _need(isinstance(sid, str) and bool(SLUG.match(sid)), f"{where}: source id '{sid}'")
        _need(bool((s.get("title") or "").strip()), f"{where}: source {sid} needs a title")
        _need(isinstance(s.get("checked"), bool), f"{where}: source {sid} needs checked true/false")
    seen: set[str] = set()
    for ch in doc.get("chapters") or []:
        _need(bool((ch.get("name") or "").strip()), f"{where}: a chapter needs a name")
        for st in ch.get("setups") or []:
            sid = st.get("id")
            w = f"{where}/{ch['name']}/{sid}"
            _need(isinstance(sid, str) and bool(SLUG.match(sid)), f"{w}: id must be a slug")
            _need(sid not in seen, f"{w}: duplicate id")
            seen.add(sid)
            _need(bool((st.get("title") or "").strip()), f"{w}: needs a title")
            _need(st.get("src") in srcs, f"{w}: src must name one of the file's sources")
            _need(st.get("kind") in KINDS, f"{w}: kind must be one of {sorted(KINDS)}")
            for k in LISTS:
                v = st.get(k, [])
                _need(isinstance(v, list) and all(isinstance(x, str) and x.strip() for x in v), f"{w}: {k} must be a list of text")
                _need(len(set(v)) == len(v), f"{w}: {k} has repeats")
    return doc


def variants(st: dict) -> int:
    n = 1
    for k in LISTS:
        n *= max(1, len(st.get(k) or []))
    return n


def load() -> list[dict]:
    out = []
    for f in sorted(DIR.glob("*.json")):
        out.append(check(json.loads(f.read_text(encoding="utf-8")), f.name))
    return out


def totals(docs: list[dict] | None = None) -> dict[str, Any]:
    docs = load() if docs is None else docs
    levels: dict[str, Any] = {}
    for d in docs:
        lv = levels.setdefault(d["level"], {"setups": 0, "variants": 0, "chapters": {}, "built": 0,
                                            "sources": len(d["sources"]), "sources_checked": sum(1 for s in d["sources"] if s["checked"])})
        for ch in d.get("chapters") or []:
            c = lv["chapters"].setdefault(ch["name"], {"setups": 0, "variants": 0})
            for st in ch.get("setups") or []:
                v = variants(st)
                c["setups"] += 1
                c["variants"] += v
                lv["setups"] += 1
                lv["variants"] += v
                lv["built"] += 1 if st.get("built") else 0
    return {"levels": levels, "setups": sum(l["setups"] for l in levels.values()),
            "variants": sum(l["variants"] for l in levels.values())}


def main(argv: list[str]) -> int:
    t = totals()
    if "--json" in argv:
        print(json.dumps(t, indent=1))
        return 0
    for name in LEVELS:
        lv = t["levels"].get(name)
        if not lv:
            print(f"{name:14s}  (no file yet)")
            continue
        print(f"{name:14s}  {lv['setups']:5d} set-ups  {lv['variants']:7d} variants  "
              f"sources {lv['sources_checked']}/{lv['sources']} checked against the document  built {lv['built']}")
        if "-v" in argv:
            for cn, c in lv["chapters"].items():
                print(f"    {c['setups']:4d} {c['variants']:6d}  {cn}")
    print(f"TOTAL           {t['setups']:5d} set-ups  {t['variants']:7d} variants")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
