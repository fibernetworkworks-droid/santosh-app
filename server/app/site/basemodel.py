"""v0.999.13 B8 BUSINESS MODELS (gap 10 of docs/research/lovable/03_backend_vs_hoola.md).

App Sahayak already knows the data of 43 complex businesses (`appmaker/archetypes.py` + the tables in `appmaker/datamodel.py`:
an ISP has internet plans, subscribers, OLT / PON / ONT, fiber routes, fault tickets, work orders, bills and payments). The
website path never read them: an ISP portal's lists came only from the plan's `app_words`, so whatever the model happened to
write was all she got. Now:

- `match(text)` picks the business model her words name (whole words / phrases from each archetype's word list, in code);
- `lists(key)` is that model's lists + fields, compact, in Hoola's own field types - handed to the data draft as
  `starting_model`, so the draft starts from the tested model and only renames / drops / adds what her words say;
- `missing(key, drafted)` names the model's lists the draft left out, shown on the plan card (a note, never forced).

Pure: reads data tables only, no model call, no I/O."""
from __future__ import annotations

import re
from typing import Any

MAX_LISTS = 24           # the reference the draft reads; the website itself is capped by webapp.MAX_COLLECTIONS
MAX_FIELDS = 12
PER_MODULE = 3          # tables taken from each of the model's later modules (plus what they point to)
SECRET = re.compile(r"(?i)(password|pin|otp|cvv|card|aadhaar|pan_no|account_no_bank|ifsc|token|secret)")


def _hit(text: str, phrase: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(phrase.lower()) + r"(?![a-z0-9])", text) is not None


def match(text: str) -> str:
    """The archetype whose words her text names, or "". Longest / most matched words win; ties keep the table's order."""
    from ..appmaker import archetypes as A
    t = (text or "").lower()
    if not t.strip():
        return ""
    best, score = "", 0
    for key, a in A.ARCHETYPES.items():
        s = sum(len(w) for w in a.get("words") or [] if _hit(t, w))
        if s > score:
            best, score = key, s
    return best


def label(key: str) -> str:
    from ..appmaker import archetypes as A
    return str((A.ARCHETYPES.get(key) or {}).get("label") or key)


def _ordered_entities(key: str) -> list[str]:
    """The model's own modules in its order; each module's tables followed by the tables they point to (an ISP's
    subscriber needs its customer, a work order its ticket)."""
    from ..appmaker import archetypes as A
    from ..appmaker import backend as BE
    from ..appmaker import datamodel as D
    mods = [m for m in (A.ARCHETYPES.get(key) or {}).get("modules") or [] if m not in BE.INFRA_MODULES and m in D.MODULES]
    out: list[str] = []

    def ok(e: str) -> bool:
        v = D.ENTITIES.get(e)
        return bool(v) and v[0] not in BE.INFRA_MODULES and "s" not in v[3] and not BE.SKIP_ENT.search(e)

    def add(e: str) -> None:
        if e in out or not ok(e):
            return
        out.append(e)
        for f in D.parse_fields(D.ENTITIES[e][2]):
            if f["type"] in ("ref", "many") and f["arg"] in D.ENTITIES and f["arg"] not in out and ok(f["arg"]) \
                    and D.ENTITIES[f["arg"]][0] not in mods:
                out.append(f["arg"])
    def rank(e: str, i: int) -> tuple[int, int, int]:
        v = D.ENTITIES[e]
        linked = any(f["type"] in ("ref", "many") and f["arg"] in out for f in D.parse_fields(v[2]))
        return (0 if "o" in v[3] else 1, 0 if linked else 1, i)

    for n, m in enumerate(mods):                 # the business's own module whole; every other module its main records
        tables = [e for e, v in D.ENTITIES.items() if v[0] == m]   # first (orders, bills, payments - not price lists)
        if n:
            tables = sorted(tables, key=lambda e: rank(e, tables.index(e)))[:PER_MODULE]
        for e in tables:
            add(e)
    return out


def lists(key: str) -> list[dict[str, Any]]:
    """The model's lists as the data draft reads them: key, label, fields (key, type, options, to)."""
    from ..appmaker import backend as BE
    from ..appmaker import datamodel as D
    if not key:
        return []
    out = []
    for e in _ordered_entities(key):
        fields = []
        for f in D.parse_fields(D.ENTITIES[e][2]):
            t = BE.DM_TYPE.get(f["type"])
            if not t or f["name"] in ("id", "owner", "created", "updated") or SECRET.search(f["name"]):
                continue
            fd: dict[str, Any] = {"key": f["name"], "type": t}
            if f["type"] == "ref" and f["arg"] in D.ENTITIES:
                fd["type"], fd["to"] = "ref", f["arg"]
            if t == "choice":
                if not f.get("values"):
                    continue
                fd["options"] = f["values"][:12]
            if f["required"]:
                fd["required"] = True
            fields.append(fd)
            if len(fields) >= MAX_FIELDS:
                break
        if fields:
            out.append({"key": e, "label": D.ENTITIES[e][1], "fields": fields})
        if len(out) >= MAX_LISTS:
            break
    keys = {c["key"] for c in out}
    for c in out:                                # a link to a table outside the reference stays a plain name / id
        for fd in c["fields"]:
            if fd.get("to") and fd["to"] not in keys:
                fd["type"] = "text"
                fd.pop("to")
    return out


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s or "").lower().replace("&", "and"))


def missing(key: str, drafted: list[dict[str, Any]]) -> list[str]:
    """The model's lists the draft did not keep (by key or by label, either way round). Only the model's first tables
    count - its own business data, not every table it pulled in."""
    from ..appmaker import archetypes as A
    from ..appmaker import datamodel as D
    if not key:
        return []
    own = set((A.ARCHETYPES.get(key) or {}).get("modules", [])[:1])
    have = {_norm(c.get("key")) for c in drafted} | {_norm(c.get("label")) for c in drafted}
    out = []
    for c in lists(key):
        if D.ENTITIES[c["key"]][0] not in own:
            continue
        names = {_norm(c["key"]), _norm(c["label"])} | {_norm(x) for x in re.split(r"[/(),]", c["label"]) if x.strip()}
        if not any(n and (n in have or any(n in h or h in n for h in have if len(h) >= 3)) for n in names):
            out.append(c["label"])
    return out
