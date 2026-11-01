"""Prayogshala catalogue service: every lab is checked once (LSL + its NCERT check) and served as data."""
from __future__ import annotations

import functools
import logging
from typing import Any

from . import catalog, lsl

log = logging.getLogger("santosh.prayog")
NOTE = ("Har reading Hoola ke simulation code se aati hai (andaaza nahi) aur NCERT ke formula se 1% ke andar jaanchi gayi hai. "
        "Yeh asli lab ka abhyaas hai; asli practical exam ki jagah nahi.")


@functools.lru_cache(maxsize=1)
def labs() -> dict[str, dict]:
    """Every catalogue lab that passes the checker AND its own NCERT check. A failing lab is left out and logged."""
    out: dict[str, dict] = {}
    for build in catalog.BUILDERS:
        try:
            lab = lsl.check(build())
            res = lsl.run_check(lab)
            if not res["ok"]:
                raise lsl.LabError(f"NCERT check {res['error'] * 100:.2f}% > {res['tol'] * 100:.1f}%")
            out[lab["id"]] = lab
        except Exception as e:                      # one broken lab never takes the catalogue down
            log.warning("prayog lab %s left out: %s", getattr(build, "__name__", "?"), e)
    return out


def summary(lab: dict) -> dict:
    return {"id": lab["id"], "title": lab["title"], "field": lab["field"], "group": lab.get("group") or lab["field"],
            "level": lab.get("level", ""), "topic": lab.get("topic", ""), "aim": lab["aim"], "kernel": lab["kernel"]}


def search(q: str = "", field: str = "", limit: int = 50) -> list[dict]:
    q = (q or "").strip().lower()
    f = (field or "").strip().lower()
    rows = []
    for lab in labs().values():
        s = summary(lab)
        hay = " ".join(str(v) for v in s.values()).lower()
        if f and f not in (s["field"] + " " + s["group"]).lower():
            continue
        if q and not all(w in hay for w in q.split()):
            continue
        rows.append(s)
    return rows[: max(1, min(int(limit or 50), 200))]


def get(lab_id: str) -> dict | None:
    return labs().get(str(lab_id or ""))


def _base() -> str:
    from ..config import get_settings
    return (get_settings().public_base_url or "").rstrip("/")


def link(lab_id: str) -> str:
    return f"{_base()}/static/prayog/lab.html?id={lab_id}"


def catalogue_link() -> str:
    return f"{_base()}/static/prayog/index.html"


def card(lab: dict) -> dict[str, Any]:
    return {**summary(lab), "url": link(lab["id"]), "knobs": [k["label"] for k in lab.get("knobs") or [] if not k.get("hidden")],
            "steps": lab.get("steps") or [], "note": NOTE}
