"""Prayogshala variants: one studio RIG serves a whole family of experiments (P1 of docs/PRAYOG_PHYSICS_LAKH_PLAN.md).

A family file `prayog/families/<base>.json` names a base lab from the catalogue and lists its variants - a different
sample, method, unknown, level or condition. A variant is DATA only:

    {"base": "hookes-law", "chapter": "Mechanical Properties of Solids",
     "variants": [{"key": "soft", "title": "...", "sample": "Soft spring", "params": {"k": 12},
                   "unknown": "spring constant k", "note": "...", "source": {"title": "..."}}],
     "grid": {"title": "Hooke's law: {spring}", "axes": {"spring": [{"key": "k12", "label": "a soft spring",
              "params": {"k": 12}}, ...]}}}

`grid` is the generator: the product of its axes, each combination one variant (keys joined with '-', titles filled
from each axis item's `label`, params merged in axis order). A variant becomes a lab by `apply()`: a copy of the base
lab with the variant's params (the hidden unknown is one of them), its own id / title / sample line and its own
NCERT check run on the NEW numbers. A variant that fails the checker or its check is never served (logged).

The variant list is built from the family files alone (no lab is built for the list); a lab is built on first open
and cached, so the catalogue can grow to 1 lakh without building them all at start."""
from __future__ import annotations

import copy
import functools
import itertools
import json
import logging
import re
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.prayog")
FAM_DIR = Path(__file__).resolve().parent / "families"
KEY = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
VAR_KEYS = {"key", "title", "sample", "method", "unknown", "note", "source", "params", "level", "aim", "topic", "chapter", "check", "cfg"}


class SpecError(ValueError):
    pass


def _fill(tpl: str, labels: dict[str, str]) -> str:
    out = str(tpl or "")
    for k, v in labels.items():
        out = out.replace("{" + k + "}", str(v))
    return out


def _grid(fam: dict) -> list[dict]:
    g = fam.get("grid") or {}
    axes = g.get("axes") or {}
    if not axes:
        return []
    names = list(axes)
    out = []
    for combo in itertools.product(*(axes[n] for n in names)):
        labels = {n: (it.get("label") or it.get("key")) for n, it in zip(names, combo)}
        v: dict[str, Any] = {"key": "-".join(str(it["key"]) for it in combo), "params": {}}
        for it in combo:                                     # later axes win, in axis order
            v["params"].update(it.get("params") or {})
            for k in ("sample", "method", "unknown", "level", "source", "check"):
                if it.get(k) is not None:
                    v[k] = it[k]
            if it.get("note"):
                v["note"] = (v.get("note", "") + " " + it["note"]).strip()
        v["title"] = _fill(g.get("title") or "", labels)
        for k in ("sample", "method", "unknown", "aim"):
            if g.get(k):
                v[k] = _fill(g[k], labels)
        out.append(v)
    return out


def _validate_family(fam: dict, where: str) -> None:
    if not isinstance(fam, dict) or not isinstance(fam.get("base"), str):
        raise SpecError(f"{where}: needs 'base' (a catalogue lab id)")
    for v in fam.get("variants") or []:
        extra = set(v) - VAR_KEYS
        if extra:
            raise SpecError(f"{where}: variant has unknown keys {sorted(extra)}")


@functools.lru_cache(maxsize=1)
def families() -> dict[str, dict]:
    """base id -> family (variants already expanded from the grid). A bad file is logged and skipped."""
    out: dict[str, dict] = {}
    if not FAM_DIR.is_dir():
        return out
    for f in sorted(FAM_DIR.glob("*.json")):
        try:
            fam = json.loads(f.read_text(encoding="utf-8"))
            _validate_family(fam, f.name)
            vs = list(fam.get("variants") or []) + _grid(fam)
            seen = set()
            for v in vs:
                if not KEY.match(str(v.get("key") or "")):
                    raise SpecError(f"{f.name}: variant key '{v.get('key')}' must be a short slug")
                if v["key"] in seen:
                    raise SpecError(f"{f.name}: variant key '{v['key']}' twice")
                seen.add(v["key"])
                if not (v.get("title") or "").strip():
                    raise SpecError(f"{f.name}: variant '{v['key']}' needs a title")
            fam = dict(fam, variants=vs)
            out[fam["base"]] = fam
        except Exception as e:                     # one bad family never takes the catalogue down
            log.warning("prayog family %s left out: %s", f.name, e)
    return out


def vid(base: str, key: str) -> str:
    return f"{base}--{key}"


def split(lab_id: str) -> tuple[str, str] | None:
    if "--" not in (lab_id or ""):
        return None
    b, k = lab_id.split("--", 1)
    return b, k


def apply(base_lab: dict, fam: dict, v: dict) -> dict:
    """The variant as a full lab: the base lab with the variant's numbers, id, title and sample line."""
    lab = copy.deepcopy(base_lab)
    over = {k: float(x) for k, x in (v.get("params") or {}).items()}
    lab["id"] = vid(base_lab["id"], v["key"])
    lab["rig"] = fam.get("rig") or base_lab.get("rig") or base_lab["id"]
    lab["title"] = v["title"]
    for k in ("level", "aim", "topic"):
        if v.get(k):
            lab[k] = v[k]
    lab["chapter"] = v.get("chapter") or fam.get("chapter") or base_lab.get("chapter") or base_lab.get("topic") or ""
    lab["params"] = {**(lab.get("params") or {}), **over}
    for kn in lab.get("knobs") or []:                         # a hidden unknown's knob starts at the variant's value
        if kn.get("param") in over:
            val = round(over[kn["param"]] / float(kn.get("k", 1.0)), 9)
            kn["value"] = val
            kn["min"] = min(kn.get("min", val), val)       # the ROUNDED value, or a knob at its own edge fails
            kn["max"] = max(kn.get("max", val), val)
    vcfg = v.get("cfg")
    if vcfg:                                          # e.g. a universal bridge: R, L and C settings balance differently
        merged = dict(lab.get("cfg") or {})
        for k, x in vcfg.items():
            merged[k] = x                              # a block (measure, net...) is replaced whole, never half-merged
        lab["cfg"] = merged
    chk = lab.get("check") or {}
    cp = dict(chk.get("params") or {})
    for k in list(cp):                                        # the check must run on the variant's numbers
        if k in over:
            cp[k] = over[k]
    for k, x in ((v.get("check") or {}).get("params") or {}).items():
        cp[k] = float(x)
    if chk:
        lab["check"] = dict(chk, params=cp)
    meta = {"base": base_lab["id"], "key": v["key"]}
    for k in ("sample", "method", "unknown", "note", "source"):
        if v.get(k):
            meta[k] = v[k]
    lab["variant"] = meta
    if v.get("source"):
        lab["sources"] = list(lab.get("sources") or []) + [v["source"]]
    return lab


def rows(bases: dict[str, dict]) -> list[dict]:
    """Summary rows for every variant of every family whose base lab is served (no lab is built)."""
    out = []
    for b, fam in families().items():
        base = bases.get(b)
        if not base:
            continue
        for v in fam["variants"]:
            out.append({"id": vid(b, v["key"]), "title": v["title"], "field": base["field"],
                        "group": base.get("group") or base["field"], "level": v.get("level") or base.get("level", ""),
                        "topic": v.get("topic") or base.get("topic", ""),
                        "chapter": v.get("chapter") or fam.get("chapter") or base.get("topic", ""),
                        "aim": v.get("aim") or base["aim"], "kernel": base["kernel"], "base": b,
                        "sample": v.get("sample", "")})
    return out
