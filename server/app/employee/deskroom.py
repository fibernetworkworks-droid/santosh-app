"""v0.796 DESK ROOM: a web-console desk for every AI employee that had none.

The audit (owner, 11 Nov: "LOT OF EMPLOYEE HAS BEEN DEVELOPED IN APP BUT IT IS NOT AVAILABLE IN WEB CONSOLE"): 31 live
employees in the Hub - Finance & Banking (3), Retail & E-commerce (3), Health Insurance (3), Voice (Kaan) and
Construction & Real Estate (21) - were built as chat tools only. Their "Open desk" button pointed at a console view that
did not exist (a dead tap), and the phone fell back to the SEO desk for them.

This module is the one server side for all of them, department by department:

* `DEPTS` - the four departments, their lanes, and which employee sits in each lane.
* `tools_of(key)` - the tools each employee works with (its main tool + its read-only `_dekho` tool when it has one).
* `spec(tool)` - reads the tool's OWN schema and description into forms: one form per action, the fields that action
  uses (with choices, hints, list-of-rows columns), and what the action gives back. Nothing is hand-copied, so a tool
  that grows an action shows it on the desk the same day.
* `run(...)` - runs one action through the SAME `dispatch` the chat uses, as the owner, with the employee's own tool
  only. Every refusal, card and guard inside the tool stays exactly as in chat (sending / paying / filing still waits for
  her tap on a card); the desk adds nothing that can change more than a chat message could.

Routes: GET /api/deskroom, GET /api/deskroom/{dept}, POST /api/deskroom/{key}/run (make_router below).
"""
from __future__ import annotations

import asyncio
import re
from typing import Any

from . import hire as H

# ------------------------------------------------------------------ departments
DEPTS: list[dict[str, Any]] = [
    {"id": "fin", "group": H.FIN_GROUP, "name": "Finance & Banking", "icon": "fin",
     "line": "Money maths and checks: a loan's true cost, hidden charges, scams, TDS, ageing, credit papers and order tickets. "
             "It calculates and drafts; no money moves and no order is placed.",
     "lanes": [{"id": "people", "name": "For people", "keys": ["paisa_sahayak"]},
               {"id": "desk", "name": "Finance desk", "keys": ["vitt_sahayak"]},
               {"id": "risk", "name": "Markets & credit", "keys": ["risk_desk"]}]},
    {"id": "retail", "group": H.RETAIL_GROUP, "name": "Retail & E-commerce", "icon": "retail",
     "line": "A shop and online-seller copilot: today's sales, reorder, margin and MRP checks, growth plans and trust checks. "
             "It prepares; you set prices and place orders.",
     "lanes": [{"id": "shop", "name": "Run the shop", "keys": ["dukaan_desk"]},
               {"id": "grow", "name": "Grow", "keys": ["retail_growth"]},
               {"id": "trust", "name": "Trust & safety", "keys": ["retail_trust"]}]},
    {"id": "healthins", "group": H.HEALTHINS_GROUP, "name": "Health Insurance", "icon": "health",
     "line": "Claims and servicing: documents needed, payable worksheets, appeals, plan comparisons and portfolio risk. "
             "It prepares; the insurer, TPA or a named officer decides.",
     "lanes": [{"id": "claims", "name": "Claims desk", "keys": ["bima_desk"]},
               {"id": "assist", "name": "Customer help", "keys": ["bima_assist"]},
               {"id": "risk", "name": "Risk & pricing", "keys": ["bima_risk"]}]},
    {"id": "const", "group": H.CONST_GROUP, "name": "Construction & Real Estate", "icon": "const",
     "line": "Site records, money, approvals, design checks and handover. Every number is worked from what you give; "
             "it prepares, a licensed person certifies.",
     "lanes": [{"id": "site", "name": "Site & store",
                "keys": ["const_store", "const_labour", "const_quality", "const_ehs", "const_meet"]},
               {"id": "money", "name": "Money & contracts",
                "keys": ["const_customer", "const_qs", "const_contracts", "const_tender", "const_rera"]},
               {"id": "plan", "name": "Plan & approvals",
                "keys": ["const_approvals", "const_plan", "const_delay", "const_land"]},
               {"id": "design", "name": "Design & survey",
                "keys": ["const_predesign", "const_bim", "const_drawqa", "const_survey", "const_green"]},
               {"id": "studio", "name": "Studio & learning", "keys": ["const_studio", "const_learn"]}]},
]
# Kaan (Voice, Meetings & Transcription) already has its own console page: Hoola Flow (/console/flow).
ELSEWHERE = {"kaan": "flow"}


class DeskError(Exception):
    pass


def dept_of(key: str) -> dict[str, Any] | None:
    for d in DEPTS:
        for ln in d["lanes"]:
            if key in ln["keys"]:
                return d
    return None


def keys() -> list[str]:
    return [k for d in DEPTS for ln in d["lanes"] for k in ln["keys"]]


def tools_of(key: str) -> list[str]:
    """The employee's own tools: the main one and, when it exists, its read-only `<name>_dekho`."""
    from ..agent import tools as T
    if key not in keys():
        return []
    out = [n for n in (key, key + "_dekho") if n in T.HANDLERS]
    return out


# ------------------------------------------------------------------ reading a tool into forms
_SHORT_OK = {"add", "day", "sum", "pts", "new", "due", "set", "row", "the", "and", "out", "off", "per", "lot", "log", "map",
             "url", "upi", "kyc", "ok", "abc", "id", "in", "on", "to", "of", "by", "vs", "pdf", "end", "fee", "tat"}
_UPPER = {"kfs", "dcf", "ecl", "dpd", "aml", "tds", "gst", "rwh", "bim", "itp", "ncr", "bbs", "boq", "ids", "bcf", "cde",
          "evm", "pmc", "si", "uw", "fhir", "ppm", "wo", "dlp", "afs", "mep", "gis", "ld", "arb", "jv", "pv", "ve", "mv",
          "tc", "cx", "rto", "rera", "ifc", "hvac", "rwh", "cobie", "sip", "nav", "emi", "apr", "utr", "ehs", "dwg",
          "grn", "otp", "msme", "kpi", "qs", "4d", "5d", "ncb", "opd", "hsn", "mrp", "sku", "vat", "cess", "bocw", "is",
          "cpheeo", "ecbc", "epd", "mrv", "aqi"}
_DONT_UPPER = {"kyc": "KYC", "upi": "UPI", "url": "URL", "abc": "ABC", "pdf": "PDF", "tat": "TAT", "id": "ID"}


def human(word: str) -> str:
    parts = [p for p in re.split(r"[_\s]+", str(word or "")) if p]
    out = []
    for i, p in enumerate(parts):
        lo = p.lower()
        if lo == "pct":
            out.append("%")
        elif lo in _DONT_UPPER:
            out.append(_DONT_UPPER[lo])
        elif lo in _UPPER:
            out.append(lo.upper())
        else:
            out.append(lo.capitalize() if i == 0 else lo)
    return " ".join(out) or str(word)


def _schema(tool: str) -> dict[str, Any]:
    """The tool's FULL spec from its own module (the registry's copy has its description cut to 1,200 chars for the
    model, which drops the later actions' inputs)."""
    import importlib
    from ..agent import tools as T
    h = T.HANDLERS.get(tool)
    mod = importlib.import_module(h.__module__) if h is not None and getattr(h, "__module__", "") else None
    for name, val in (vars(mod).items() if mod else ()):
        if name.endswith("_TOOLS") and isinstance(val, list):
            for t in val:
                if isinstance(t, dict) and t.get("name") == tool:
                    return t
    for t in T.TOOLS:
        if t.get("name") == tool:
            return t
    raise DeskError(f"Unknown tool {tool}")


def _segments(desc: str, actions: list[str], read: bool) -> dict[str, str]:
    """Each action's own stretch of the description (its inputs and what it gives back)."""
    pos: list[tuple[int, int, str]] = []
    for a in actions:
        esc = re.escape(a)
        if read:
            pats = [rf"what=\s*{esc}\b", rf"\|\s*{esc}\b"]
        else:
            pats = [rf"action=\s*{esc}(?![A-Za-z0-9_])[^:.;|>]{{0,60}}?:", rf"action=\s*{esc}(?![A-Za-z0-9_])",
                    rf"(?:^|[.;]\s+|\s){esc}\b(?:\s*\([^)]{{0,60}}\))?\s*:"]
        for p in pats:
            m = re.search(p, desc)
            if m:
                pos.append((m.start(), m.end(), a))
                break
    pos.sort()
    out: dict[str, str] = {}
    for i, (s, e, a) in enumerate(pos):
        end = pos[i + 1][0] if i + 1 < len(pos) else len(desc)
        out[a] = desc[e:end].strip(" ,;|")
    return out


def _field(name: str, prop: dict[str, Any], seg: str) -> dict[str, Any]:
    typ = prop.get("type") or "string"
    f: dict[str, Any] = {"name": name, "label": human(name), "type": typ}
    if prop.get("enum"):
        f["options"] = [str(x) for x in prop["enum"]]
    if prop.get("description"):
        f["hint"] = str(prop["description"])[:160]
    m = re.search(rf"\b{re.escape(name)}\b\s*(\[\{{[^\]]*\}}\]|\[[^\]]*\]|\{{[^}}]*\}}|\([^)]*\)|[A-Za-z0-9_+./-]+(?:\|[A-Za-z0-9_+./ -]+)+)?", seg)
    tail = (m.group(1) or "") if m else ""
    if tail.startswith("[{"):
        cols = [c.strip(" []{}") for c in tail.strip("[]{} ").split(",")]
        cols = [re.sub(r"\s*\(.*$", "", c).strip() for c in cols if c.strip()]
        f["shape"], f["cols"] = "rows", [c for c in cols if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", c)][:10]
        if not f["cols"]:
            f.pop("cols")
            f["shape"] = "json"
    elif tail.startswith("["):
        f["shape"] = "list"
        inner = tail.strip("[] ")
        if inner and not f.get("hint"):
            f["hint"] = inner[:80]
    elif tail.startswith("{"):
        f["shape"] = "map"
        if not f.get("hint"):
            f["hint"] = tail.strip("{} ")[:80]
    elif tail.startswith("("):
        if not f.get("hint"):
            f["hint"] = tail.strip("() ")[:120]
    elif "|" in tail and not f.get("options"):
        f["options"] = [o.strip() for o in tail.split("|") if o.strip()][:16]
    if typ == "array" and "shape" not in f:
        it = (prop.get("items") or {}).get("type")
        f["shape"] = "json" if it == "object" else "list"
    if typ == "object" and "shape" not in f:
        f["shape"] = "map"
    if name == "file_id":
        f["shape"] = "file"
    if typ == "string" and "shape" not in f and name in ("text", "narrative", "description", "body", "note", "notes",
                                                          "message", "csv", "wording", "letter", "paste", "content"):
        f["shape"] = "long"
    return f


def spec(tool: str) -> dict[str, Any]:
    t = _schema(tool)
    props: dict[str, Any] = (t.get("input_schema") or {}).get("properties") or {}
    read = "action" not in props and "what" in props
    param = "what" if read else "action"
    acts = [str(a) for a in ((props.get(param) or {}).get("enum") or [])]
    desc = str(t.get("description") or "")
    head = re.split(r"\b(?:action|what)=", desc, maxsplit=1)[0].strip(" .")
    if not acts and read:   # a read tool whose `what` is not an enum: take the values from "what=a | b | c"
        m = re.search(r"what=(.*)", desc)
        if m:
            acts = [re.match(r"\s*([a-z0-9_]+)", p).group(1) for p in m.group(1).split("|") if re.match(r"\s*[a-z0-9_]+", p)]
    segs = _segments(desc, acts, read)
    names = [n for n in props if n != param]
    out_acts = []
    for a in acts:
        seg = segs.get(a, "")
        give = ""
        if "->" in seg:
            seg, give = seg.split("->", 1)
            give = re.split(r"\.\s+(?=[A-Z])|\baction=", give)[0].strip(" .")
        used = [n for n in names if re.search(rf"\b{re.escape(n)}\b", seg)]
        for w in re.findall(r"\b([a-z_]+)\s*\(id\)", seg):   # "action (id)" when the field is really action_id
            if w + "_id" in names and w + "_id" not in used and (w not in names or w == param):
                used.append(w + "_id")
        if a in segs:
            fields = [_field(n, props[n], seg) for n in used]
            guessed = False
        else:
            fields = [_field(n, props[n], "") for n in names]
            guessed = bool(names)
        lead = seg.strip()
        out_acts.append({"id": a, "label": human(a), "fields": fields, "gives": give[:220], "guessed": guessed,
                         "about": lead[:240] if (read or not fields) else ""})
    return {"tool": tool, "read": read, "param": param, "about": head[:400], "actions": out_acts}


# ------------------------------------------------------------------ the department view
def _emp_view(tenant: str, key: str) -> dict[str, Any]:
    c = H.CATALOG.get(key) or {}
    return {"key": key, "name": c.get("name", key), "pitch": c.get("pitch", ""), "does": c.get("does", [])[:8],
            "needs": c.get("needs", [])[:4], "never": c.get("never", [])[:6], "live": bool(c.get("live")),
            "status": H.status(tenant, key), "tools": [spec(n) for n in tools_of(key)]}


def overview(tenant: str) -> dict[str, Any]:
    hired = H.hired_keys(tenant)
    return {"depts": [{"id": d["id"], "name": d["name"], "line": d["line"], "icon": d["icon"],
                       "count": sum(len(ln["keys"]) for ln in d["lanes"]),
                       "hired": sum(1 for ln in d["lanes"] for k in ln["keys"] if k in hired)} for d in DEPTS],
            "where": {k: d["id"] for d in DEPTS for ln in d["lanes"] for k in ln["keys"]}, "elsewhere": ELSEWHERE}


def dept(tenant: str, dept_id: str) -> dict[str, Any]:
    d = next((x for x in DEPTS if x["id"] == dept_id), None)
    if not d:
        raise DeskError("No such department.")
    from .. import convs
    try:
        conv = convs.notice_chat(tenant)
    except Exception:   # noqa: BLE001 - uploads still work through the chat she opens
        conv = ""
    return {"id": d["id"], "name": d["name"], "line": d["line"], "icon": d["icon"], "conversation_id": conv,
            "lanes": [{"id": ln["id"], "name": ln["name"], "employees": [_emp_view(tenant, k) for k in ln["keys"]]}
                      for ln in d["lanes"]]}


# ------------------------------------------------------------------ running one action
def _clean_args(args: dict[str, Any], props: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in (args or {}).items():
        if k not in props or v is None or v == "" or v == [] or v == {}:
            continue
        out[k] = v
    return out


async def run(tenant: str, key: str, tool: str, action: str, args: dict[str, Any]) -> dict[str, Any]:
    if key not in keys():
        raise DeskError("This employee has no desk here.")
    if tool not in tools_of(key):
        raise DeskError("That tool does not belong to this employee.")
    st = H.status(tenant, key)
    if st not in ("hired", "paused"):
        raise DeskError("Hire this employee first - its desk opens once it is hired.")
    if st == "paused":
        raise DeskError("This employee is paused. Resume it to work on its desk.")
    t = _schema(tool)
    props = (t.get("input_schema") or {}).get("properties") or {}
    sp = spec(tool)
    if action not in [a["id"] for a in sp["actions"]]:
        raise DeskError(f"Unknown {sp['param']} '{action}'.")
    clean = _clean_args(args, props)
    for k in ("account", "card", "card_no"):
        if isinstance(clean.get(k), str) and re.search(r"\d{9,}", clean[k]):
            clean[k] = "XXXX" + re.sub(r"\D", "", clean[k])[-4:]   # a full account / card number never goes in: last 4 only
    clean[sp["param"]] = action
    from .. import convs
    from ..agent.tools import Ctx, ToolError, dispatch
    try:
        conv = convs.notice_chat(tenant)
    except Exception:   # noqa: BLE001
        conv = ""
    ctx = Ctx(tenant_id=tenant, conversation_id=conv, actor="owner")
    try:
        out = await asyncio.wait_for(dispatch(tool, clean, ctx), timeout=90)
    except ToolError as e:
        raise DeskError(str(e))
    except asyncio.TimeoutError:
        raise DeskError("This took too long. Try a smaller input, or ask Hoola in chat.")
    from ..scrub import scrub
    return {"ok": True, "tool": tool, "action": action, "result": scrub(out), "conversation_id": conv}


def make_router(require_key, current_tenant):
    from fastapi import APIRouter, Depends, HTTPException

    r = APIRouter()

    @r.get("/api/deskroom", dependencies=[Depends(require_key)])
    def _overview(tenant: str = Depends(current_tenant)):
        return overview(tenant)

    @r.get("/api/deskroom/{dept_id}", dependencies=[Depends(require_key)])
    def _dept(dept_id: str, tenant: str = Depends(current_tenant)):
        try:
            return dept(tenant, dept_id)
        except DeskError as e:
            raise HTTPException(404, str(e))

    @r.post("/api/deskroom/{key}/run", dependencies=[Depends(require_key)])
    async def _run(key: str, body: dict, tenant: str = Depends(current_tenant)):
        body = body or {}
        try:
            return await run(tenant, key, str(body.get("tool") or key), str(body.get("action") or ""),
                             body.get("args") if isinstance(body.get("args"), dict) else {})
        except DeskError as e:
            raise HTTPException(400, str(e))

    return r
