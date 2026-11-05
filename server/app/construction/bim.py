"""C11: the BIM / Information desk (register #18 BIM Manager, #19 CDE & Document Controller, #20 Clash
Detection Coordinator, #21 4D/5D Planner) - Wave 3, v0.550.0, plan docs/CONSTRUCTION_EMPLOYEE_PLAN.md
§7. OPEN FORMATS ONLY (the register's finding 3): Hoola READS IFC (STEP, ISO 16739-1) as text and says
exactly what it read; it WRITES BCF 2.1 issue zips; it checks an IDS SUBSET and says which facets it
could not verify. A PDF was never a model; a point cloud carries no semantics - and this desk never
pretends otherwise.

The honest limits, printed on every output:
- the IFC reader is a STEP text parser: classes, GUIDs, names, IfcElementQuantity values, spatial
  containment and placement POINTS. It does not read exact solid geometry; clash runs on the elements'
  own declared Length/Width/Height extents at their placement point, AXIS-ALIGNED (rotation ignored).
  Elements without quantities or placements are listed as NOT-CHECKABLE, never guessed.
- the model's numbers are THE MODEL'S numbers: a 5D take-off stores qty with its GUID and the quantity
  class it came from; the only arithmetic is qty x rate when a rate with its source is fed.
- clash candidates are candidates: accept / rework / ignore is the BIM coordinator's word (recorded).
- certification never happens here: measurement certifies the billing engineer; design approves the
  design lead; the tier-C gate (construction/gates.py) rides every action."""
from __future__ import annotations

import io
import json
import re
import zipfile
from datetime import date
from xml.sax.saxutils import escape as xesc

from sqlalchemy import select

from ..db import session
from .common import (CstError, _LOCK, _dump, _j, _num, today)
from .models import (CBimCde, CBimClash, CBimElement, CBimLink4d, CBimModel, CBimTakeoff, CBimTransmit)

# ---------------------------------------------------------------- the STEP reader (pure text)
_ENT = re.compile(r"^#(\d+)\s*=\s*([A-Z0-9_]+)\s*\((.*)\)\s*;\s*$")
_SCHEMA = re.compile(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'")
_NUM = re.compile(r"^-?\d+(\.\d+)?([eE][+-]?\d+)?$")
_GUID = re.compile(r"^[0-9A-Za-z_$]{22}$")   # the IFC GlobalId charset, always 22 chars

SPATIAL_CLASSES = {"IFCSITE", "IFCBUILDING", "IFCBUILDINGSTOREY", "IFCSPACE"}
SKIP_QUANTITY_CLASSES = {"IFCELEMENTQUANTITY", "IFCPROPERTYSET", "IFCPROPERTYSINGLEVALUE", "IFCMATERIAL"}
CONTEXT_CLASSES = {"IFCPROJECT"}


def _split_args(s: str) -> list[str]:
    """Top-level comma split honouring () nesting and '...' strings (with '' escapes)."""
    out, depth, cur, q = [], 0, [], False
    i = 0
    while i < len(s):
        c = s[i]
        if q:
            cur.append(c)
            if c == "'":
                if i + 1 < len(s) and s[i + 1] == "'":
                    cur.append("'")
                    i += 1
                else:
                    q = False
        elif c == "'":
            q = True
            cur.append(c)
        elif c == "(":
            depth += 1
            cur.append(c)
        elif c == ")":
            depth -= 1
            cur.append(c)
        elif c == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(c)
        i += 1
    if cur and "".join(cur).strip():
        out.append("".join(cur).strip())
    return out


def _unq(v: str) -> str:
    v = (v or "").strip()
    if v.startswith("'") and v.endswith("'") and len(v) >= 2:
        return v[1:-1].replace("''", "'")
    return v


def _is_ref(v: str) -> int | None:
    v = (v or "").strip()
    if v.startswith("#") and v[1:].isdigit():
        return int(v[1:])
    return None


def _refs(v: str) -> list[int]:
    v = (v or "").strip()
    if v.startswith("(") and v.endswith(")"):
        return [r for r in (_is_ref(x) for x in _split_args(v[1:-1])) if r is not None]
    r = _is_ref(v)
    return [r] if r is not None else []


def _float(v: str) -> float | None:
    v = (v or "").strip().rstrip(".")
    return float(v) if _NUM.match(v) else None


def parse_ifc(text: str) -> dict:
    """Parse a STEP IFC file into {schema, entities: {id: (cls, [args])}} - no deps, no guessing."""
    schema = ""
    entities: dict[int, tuple[str, list[str]]] = {}
    for line in text.splitlines():
        if not schema:
            m = _SCHEMA.search(line)
            if m:
                schema = m.group(1).strip()
        if "=" not in line or not line.strip().startswith("#"):
            continue
        m = _ENT.match(line.strip())
        if not m:
            continue
        eid, cls, args = int(m.group(1)), m.group(2).upper(), _split_args(m.group(3))
        entities[eid] = (cls, args)
    return {"schema": schema, "entities": entities}


def _qty_find(q: dict, *names: str) -> float | None:
    """The quantity under any of the model's own names ('NetVolume', 'GrossVolume', 'Length'...) -
    the value is the MODEL'S; only the lookup is tolerant."""
    for want in names:
        for k, v in q.items():
            if want in k.lower() and isinstance(v, (int, float)) and v:
                return float(v)
    return None


def _quantities(ents: dict, eid: int) -> dict:
    """The element's declared quantities via its IfcRelDefinesByProperties -> IfcElementQuantity
    chain: {QuantityName: value} - the MODEL'S OWN numbers."""
    out: dict[str, float] = {}
    for _k, (cls, args) in ents.items():
        if cls != "IFCRELDEFINESBYPROPERTIES" or len(args) < 6:
            continue
        reldef = _is_ref(args[5])
        if reldef is None or reldef not in ents or eid not in _refs(args[4]):
            continue
        rcls, rargs = ents[reldef]
        if rcls == "IFCELEMENTQUANTITY":
            # schema-correct: Quantities at index 4 (GlobalId, OwnerHistory, Name, Description, Quantities);
            # sloppy exports pad an extra $ - fall back to the last list argument.
            qlists = [rargs[4]]
            if len(rargs) > 5 and not _refs(rargs[4]):
                qlists = [rargs[5]]
            for qlist in qlists:
                for qref in _refs(qlist):
                    q = ents.get(qref)
                    if not q:
                        continue
                    qc, qa = q
                    if qc.startswith("IFCQUANTITY") and len(qa) >= 4:
                        val = _float(qa[-1])
                        nm = _unq(qa[0])
                        if val is not None and nm:
                            out[nm] = val
        elif rcls == "IFCPROPERTYSET" and len(rargs) >= 5:
            for pref in _refs(rargs[4]):
                p = ents.get(pref)
                if p and p[0] == "IFCPROPERTYSINGLEVALUE" and len(p[1]) >= 3:
                    nm = _unq(p[1][0])
                    raw = p[1][2].strip()
                    val = None
                    if raw.startswith("IFC") and "(" in raw:
                        inner = _split_args(raw[raw.index("(") + 1:raw.rindex(")")])
                        val = _float(inner[0]) if inner else None
                    elif _NUM.match(raw):
                        val = float(raw)
                    if val is not None and nm:
                        out[nm] = val
    return out


def _world_point(ents: dict, eid: int) -> dict:
    """The element's world placement POINT: product -> IfcLocalPlacement chain, translated up the
    PlacementRelTo chain. Rotation is IGNORED (axis-aligned boxes only) - the say() says so."""
    cls, args = ents[eid]
    if len(args) < 6:
        return {}
    loc_ref = _is_ref(args[5])
    x = y = z = 0.0
    hops = 0
    while loc_ref is not None and hops < 32:
        lp = ents.get(loc_ref)
        if not lp or lp[0] != "IFCLOCALPLACEMENT" or len(lp[1]) < 2:
            return {}
        rel = _is_ref(lp[1][1])
        if rel is None:
            return {}
        ax = ents.get(rel)
        if not ax or ax[0] not in ("IFCAXIS2PLACEMENT3D", "IFCAXIS2PLACEMENT2D") or not ax[1]:
            return {}
        pt = ents.get(_is_ref(ax[1][0]) or 0)
        if not pt or pt[0] != "IFCCARTESIANPOINT" or not pt[1]:
            return {}
        coords = [_float(c) or 0.0 for c in _split_args(pt[1][0].strip("()"))]
        x += coords[0] if coords else 0.0
        y += coords[1] if len(coords) > 1 else 0.0
        z += coords[2] if len(coords) > 2 else 0.0
        nxt = _is_ref(lp[1][0])
        loc_ref = nxt
        hops += 1
    return {"x": round(x, 3), "y": round(y, 3), "z": round(z, 3)}


def _guid_of(args: list[str]) -> str:
    g = _unq(args[0]) if args else ""
    return g if _GUID.match(g) else ""


def _name_of(cls: str, args: list[str]) -> str:
    """Name attribute position: IfcRoot subtypes carry Name at 2 (GlobalId, OwnerHistory, Name...);
    property/value classes carry it at 0."""
    if cls in SKIP_QUANTITY_CLASSES or cls.startswith("IFCPROPERTY"):
        return _unq(args[0]) if args else ""
    return _unq(args[2]) if len(args) > 2 else ""


def read_model(text: str) -> dict:
    """The honest read: schema, class counts, and the spatial elements (spaces, storeys, products)
    with their quantities, storey chain and placement point. Nothing is invented for what is missing."""
    p = parse_ifc(text)
    ents = p["entities"]
    by_class: dict[str, int] = {}
    for _k, (cls, _a) in ents.items():
        by_class[cls] = by_class.get(cls, 0) + 1
    # spatial containment: IfcRelAggregates (relating -> related) + IfcRelContainedInSpatialStructure
    parent: dict[int, int] = {}
    for _k, (cls, args) in ents.items():
        if cls == "IFCRELAGGREGATES" and len(args) >= 6:
            rel, rels = _is_ref(args[4]), _refs(args[5])
            for r in rels:
                parent[r] = rel
        elif cls == "IFCRELCONTAINEDINSPATIALSTRUCTURE" and len(args) >= 6:
            rels, rel = _refs(args[4]), _is_ref(args[5])
            for r in rels:
                parent[r] = rel
    storey_of: dict[int, str] = {}
    for eid, (cls, args) in ents.items():
        if cls in SPATIAL_CLASSES:
            continue
        chain, cur, hops = [], parent.get(eid), 0
        while cur is not None and hops < 8:
            pc = ents.get(cur)
            if not pc:
                break
            if pc[0] == "IFCBUILDINGSTOREY":
                chain.append(_name_of(pc[0], pc[1]))
                break
            cur = parent.get(cur)
            hops += 1
        if chain:
            storey_of[eid] = chain[0]

    elements = []
    for eid, (cls, args) in ents.items():
        if cls in SPATIAL_CLASSES or cls in CONTEXT_CLASSES or cls.startswith("IFCREL"):
            continue
        if cls in SKIP_QUANTITY_CLASSES or not cls.startswith("IFC"):
            continue
        guid = _guid_of(args)
        if not guid:                     # products carry a GlobalId; units, points, contexts do not
            continue
        elements.append({"eid": eid, "cls": cls, "guid": guid, "name": _name_of(cls, args),
                         "storey": storey_of.get(eid, ""), "qty": _quantities(ents, eid),
                         "world": _world_point(ents, eid)})
    spaces = []
    for eid, (cls, args) in ents.items():
        if cls == "IFCSPACE":
            spaces.append({"eid": eid, "guid": _guid_of(args), "name": _name_of(cls, args),
                           "qty": _quantities(ents, eid)})
    return {"schema": p["schema"], "by_class": by_class, "elements": elements, "spaces": spaces,
            "entities": len(ents)}


# ---------------------------------------------------------------- health (#18)
def _health(m: dict) -> dict:
    guids = [e["guid"] for e in m["elements"] if e["guid"]]
    dupes = sorted({g for g in guids if guids.count(g) > 1})
    nameless = sum(1 for e in m["elements"] if not e["name"])
    no_storey = sum(1 for e in m["elements"] if not e["storey"])
    no_qty = sum(1 for e in m["elements"] if not e["qty"])
    no_world = sum(1 for e in m["elements"] if not e["world"])
    return {"schema": m["schema"], "entities": m["entities"], "elements": len(m["elements"]),
            "spaces": len(m["spaces"]), "storeys": m["by_class"].get("IFCBUILDINGSTOREY", 0),
            "duplicate_guids": dupes[:20], "nameless": nameless, "without_storey": no_storey,
            "without_quantities": no_qty, "without_placement": no_world,
            "note": "STEP text read: classes, GUIDs, names, declared quantities, placement points; "
                    "no solid geometry - rotation ignored in clash boxes"}


# ---------------------------------------------------------------- the desk actions
def ifc_add(tenant: str, project: str, name: str, ifc_text: str, file_ref: str = "", conv: str = "") -> dict:
    """One IFC (STEP) model read and stored - the read says exactly what it saw."""
    if not str(project or "").strip() or not str(name or "").strip():
        raise CstError("Project aur model ka naam bataiye.")
    if "FILE_SCHEMA" not in (ifc_text or "") or "IFC" not in (ifc_text or "")[:4000]:
        raise CstError("Yeh IFC (STEP) text nahi lag raha (FILE_SCHEMA nahi mila) - IFC file ka TEXT bhejo; "
                       "PDF/DWG model nahi hota, unke liye const_drawqa desk hai.")
    m = read_model(ifc_text)
    with _LOCK, session() as s:
        x = CBimModel(tenant_id=tenant, project=project.strip()[:160], name=name.strip()[:200],
                      schema_=m["schema"][:20], entities=m["entities"], stats=_dump({"by_class": dict(
                          sorted(m["by_class"].items(), key=lambda kv: -kv[1])[:24])}),
                      health=_dump(_health(m)), elements=len(m["elements"]), file_ref=file_ref.strip()[:160])
        s.add(x)
        s.flush()
        mid = x.id
        for e in m["elements"][:4000]:
            s.add(CBimElement(tenant_id=tenant, model_id=mid, guid=e["guid"][:40], ifc_class=e["cls"][:60],
                              name=e["name"][:200], storey=e["storey"][:120], qty=_dump(e["qty"]),
                              world=_dump(e["world"])))
    from .common import publish
    publish(tenant, "const_bim", {"kind": "ifc_add", "project": project, "model": name}, conv)
    h = _health(m)
    return {"model_id": mid, "schema": m["schema"], "entities": m["entities"], "elements": h["elements"],
            "spaces": h["spaces"], "storeys": h["storeys"], "nameless": h["nameless"],
            "without_quantities": h["without_quantities"], "without_placement": h["without_placement"],
            "say": f"IFC padha: {name} ({m['schema'] or 'schema ?'}), {m['entities']} entities, "
                   f"{h['elements']} elements, {h['spaces']} spaces, {h['storeys']} storeys. "
                   f"Gap: {h['nameless']} bina naam, {h['without_quantities']} bina quantity, "
                   f"{h['without_placement']} bina placement - jo model mein nahi hai woh guess nahi hota. "
                   "Yeh STEP-text read hai (rotation ignored, solid geometry nahi) - clash isi had tak."}


def health(tenant: str, model_id: str) -> dict:
    """The model-health report (#18): what the model has, and the gaps - as READ, not judged."""
    with session() as s:
        m = s.get(CBimModel, model_id)
        if not m or m.tenant_id != tenant:
            raise CstError("Model nahi mila.")
    return _j(m.health, {}) | {"model_id": model_id, "name": m.name, "project": m.project}


def naming_check(filenames: list, pattern: str = "Project-Originator-Volume-Level-Type-Role-Number") -> dict:
    """ISO 19650 naming check (#18): the filename against HER pattern - segments must exist and be
    filled. The pattern is data (default the standard field order); a violation is a fact, not a fine."""
    pat = [p for p in str(pattern or "").split("-") if p.strip()]
    if not pat:
        raise CstError("Pattern bataiye (jaise Project-Originator-Volume-Level-Type-Role-Number).")
    rows = []
    for f in filenames or []:
        fn = str(f).strip()
        segs = fn.rsplit(".", 1)[0].split("-") if fn else []
        missing = [pat[i] for i in range(len(pat)) if i >= len(segs) or not segs[i].strip()]
        extra = max(0, len(segs) - len(pat))
        rows.append({"file": fn[:120], "segments": len(segs), "required": len(pat),
                     "missing": missing, "extra_segments": extra,
                     "verdict": "ok" if not missing and not extra else "violation"})
    bad = sum(1 for r in rows if r["verdict"] == "violation")
    return {"rows": rows, "violations": bad,
            "say": f"Naam-check: {len(rows)} files, {bad} violation (pattern: {'-'.join(pat)}). "
                   "Naming convention ka maalik BIM manager hai - yeh sirf pattern ke against hai."}


def cde_add(tenant: str, project: str, code: str, title: str, rev: str = "", status: str = "wip",
            file_ref: str = "", note: str = "") -> dict:
    """One file into the CDE register (#19): wip | shared | published | archived - HER status codes.
    Same code + project with a new rev supersedes the old row automatically (the audit trail stays)."""
    if not str(project or "").strip() or not str(code or "").strip():
        raise CstError("Project aur document code bataiye (jaise 'P01-XXX-ZZ-M3-STR-SM-0001').")
    if status not in ("wip", "shared", "published", "archived"):
        raise CstError("status: wip | shared | published | archived (ISO 19650 CDE states).")
    with _LOCK, session() as s:
        old = s.scalars(select(CBimCde).where(CBimCde.tenant_id == tenant, CBimCde.project == project.strip()[:160],
                                              CBimCde.code == code.strip()[:80],
                                              CBimCde.superseded_by == "", CBimCde.rev != rev.strip()[:20])).all()
        x = CBimCde(tenant_id=tenant, project=project.strip()[:160], code=code.strip()[:80],
                    title=title.strip()[:200], rev=rev.strip()[:20], status=status,
                    file_ref=file_ref.strip()[:160], note=note.strip()[:200])
        s.add(x)
        s.flush()
        cid = x.id
        for o in old:
            o.superseded_by = cid
    return {"cde_id": cid, "superseded": len(old),
            "say": f"CDE: {code} rev {rev or '-'} -> {status} (audit trail poora). "
                   f"{len(old)} purani rev superseded." if old else
                   f"CDE: {code} rev {rev or '-'} -> {status}. Status codes AAPKE word se chalte hain - "
                   "Hoola register aur transmittal ka trail rakhta hai."}


def cde_status(tenant: str, cde_id: str, status: str, note: str = "") -> dict:
    """Move a CDE file's state (the document controller's act, recorded)."""
    if status not in ("wip", "shared", "published", "archived"):
        raise CstError("status: wip | shared | published | archived")
    with _LOCK, session() as s:
        x = s.get(CBimCde, cde_id)
        if not x or x.tenant_id != tenant:
            raise CstError("CDE row nahi mili.")
        x.status = status
        if note:
            x.note = note[:200]
        code = x.code
    return {"say": f"{code}: CDE status -> {status}."}


def transmit(tenant: str, project: str, codes: list, to_whom: str, note: str = "", conv: str = "") -> dict:
    """A transmittal (#19): which documents went to whom, which day - the record of the send, not the send."""
    clean = [str(c).strip()[:80] for c in (codes or []) if str(c).strip()]
    if not clean or not str(to_whom or "").strip():
        raise CstError("Codes aur 'kisko' bataiye - transmittal ka record isi se banta hai.")
    with _LOCK, session() as s:
        x = CBimTransmit(tenant_id=tenant, project=project.strip()[:160], codes=_dump(clean),
                         to_whom=to_whom.strip()[:160], day=today(tenant).isoformat(), note=note.strip()[:200])
        s.add(x)
        s.flush()
        tid, day = x.id, x.day
    from .common import publish
    publish(tenant, "const_bim", {"kind": "transmit", "project": project, "to": to_whom}, conv)
    return {"transmittal_id": tid, "codes": clean, "day": day,
            "say": f"Transmittal {len(clean)} documents -> {to_whom} ({day}). Bhejna aapke tap se hota hai - "
                   "yeh record hai."}


def clash_scan(tenant: str, model_id: str, clearance_m: float = 0.02, conv: str = "") -> dict:
    """Clash candidates (#20): the elements' declared Length/Width/Height extents at their placement
    points, axis-aligned, clearance margin ke saath. Elements without the data are NOT-CHECKABLE -
    the say() carries their count. Candidates only: the coordinator accepts or reworks."""
    with session() as s:
        m = s.get(CBimModel, model_id)
        if not m or m.tenant_id != tenant:
            raise CstError("Model nahi mila.")
        els = s.scalars(select(CBimElement).where(CBimElement.tenant_id == tenant,
                                                  CBimElement.model_id == model_id)).all()
    boxes, uncheckable = [], 0
    for e in els:
        q, w = _j(e.qty, {}), _j(e.world, {})
        dims = [_qty_find(q, "length"), _qty_find(q, "width", "breadth", "thickness"), _qty_find(q, "height", "depth")]
        if not w or any(d is None or d <= 0 for d in dims):
            uncheckable += 1
            continue
        L, W, H = dims
        boxes.append({"guid": e.guid, "cls": e.ifc_class, "name": e.name,
                      "min": [w["x"] - L / 2, w["y"] - W / 2, w["z"]],
                      "max": [w["x"] + L / 2, w["y"] + W / 2, w["z"] + H]})
    found = 0
    with _LOCK, session() as s:
        for i in range(len(boxes)):
            a = boxes[i]
            for j in range(i + 1, len(boxes)):
                b = boxes[j]
                ov = [min(a["max"][k], b["max"][k]) - max(a["min"][k], b["min"][k]) + clearance_m for k in range(3)]
                if all(v > 0 for v in ov):
                    x = CBimClash(tenant_id=tenant, model_id=model_id, a_guid=a["guid"][:40], b_guid=b["guid"][:40],
                                  trade_a=a["cls"][:60], trade_b=b["cls"][:60],
                                  group_key=f"{a['cls']} x {b['cls']}"[:120],
                                  overlap=_dump({"dx": round(ov[0] - clearance_m, 3),
                                                 "dy": round(ov[1] - clearance_m, 3),
                                                 "dz": round(ov[2] - clearance_m, 3)}))
                    s.add(x)
                    s.flush()
                    found += 1
    from .common import publish
    publish(tenant, "const_bim", {"kind": "clash_scan", "model": m.name, "found": found}, conv)
    return {"model_id": model_id, "boxes": len(boxes), "candidates": found, "not_checkable": uncheckable,
            "clearance_m": clearance_m,
            "say": f"Clash scan: {len(boxes)} checkable boxes (model ke declared extents + placement), "
                   f"{found} overlap candidates @ clearance {clearance_m:g} m. "
                   f"{uncheckable} elements NOT-CHECKABLE (quantity/placement missing - guess nahi kiya). "
                   "Faisla (accept / rework) BIM coordinator ka - yeh candidates hain, clearance nahi."}


def clash_mark(tenant: str, clash_id: str, status: str, by: str, note: str = "") -> dict:
    """The coordinator's word on a candidate, recorded: assigned | resolved | accepted. The name is
    required - closure without a name is nobody's decision."""
    if status not in ("assigned", "resolved", "accepted"):
        raise CstError("status: assigned | resolved | accepted")
    if not str(by or "").strip():
        raise CstError("Kiske naam se? (BIM coordinator ka naam record hota hai).")
    with _LOCK, session() as s:
        x = s.get(CBimClash, clash_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Clash row nahi mili.")
        x.status, x.by, x.note = status, by.strip()[:120], note.strip()[:200]
    return {"say": f"Clash {x.a_guid[:8]} x {x.b_guid[:8]} -> {status} ({by.strip()}). Record hai - "
                   "BCF bhejne ka decision coordinator ka."}


def _bcf_zip(m: CBimModel, rows: list) -> bytes:
    """The BCF 2.1 zip bytes: project.bcfp + markup.xml with one Topic per open candidate."""
    from uuid import uuid4
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("project.bcfp",
                   '<?xml version="1.0" encoding="UTF-8"?>\n<ProjectExtension><Project ProjectId="'
                   + xesc(m.project[:60]) + '" Name="' + xesc(m.project[:120]) + '"/>\n'
                   '<Extension Schema="bcf.version"><Version Major="2" Minor="1"/></Extension>\n'
                   "</ProjectExtension>")
        topics = []
        for r in rows:
            g = str(uuid4()).upper()
            ov = _j(r.overlap, {})
            topics.append(
                '<Topic Guid="' + g + '" TopicType="Clash" TopicStatus="' + xesc(r.status) + '">'
                "<Title>" + xesc(f"Clash {r.trade_a} x {r.trade_b}") + "</Title>"
                "<Priority>normal</Priority>"
                "<CreationDate>" + r.created_at.date().isoformat() + "</CreationDate>"
                "<Description>" + xesc(
                    f"Hoola clash candidate (AABB, axis-aligned): {r.a_guid} ({r.trade_a}) overlaps "
                    f"{r.b_guid} ({r.trade_b}); overlap dx={ov.get('dx', 0)} dy={ov.get('dy', 0)} "
                    f"dz={ov.get('dz', 0)} m. Candidate only - the BIM coordinator decides.") + "</Description>"
                "</Topic>")
        z.writestr("markup.xml",
                   '<?xml version="1.0" encoding="UTF-8"?>\n<Markup Version="2.1">'
                   + "".join(topics) + "</Markup>")
    return buf.getvalue()


def bcf_export(tenant: str, model_id: str, conv: str = "") -> dict:
    """BCF 2.1 export (#20): the OPEN clash candidates as a proper BCF zip (project.bcfp + markup.xml
    with one Topic per candidate). What leaves is the list; the resolution lives with people."""
    with session() as s:
        m = s.get(CBimModel, model_id)
        if not m or m.tenant_id != tenant:
            raise CstError("Model nahi mila.")
        rows = s.scalars(select(CBimClash).where(CBimClash.tenant_id == tenant, CBimClash.model_id == model_id,
                                                 CBimClash.status.in_(("open", "assigned")))).all()
    if not rows:
        raise CstError("Open clash candidates nahi hain - pehle clash_scan chalao.")
    from .. import chatfiles
    data = _bcf_zip(m, rows)
    f = chatfiles.store(tenant, f"BCF-{m.name[:24].replace(' ', '-')}-{model_id[:6]}.bcf", data,
                        "application/octet-stream")
    with _LOCK, session() as s:
        for r in rows:
            r.bcf_ref = f.get("file_id") or f.get("id") or ""
    return {"file": f, "topics": len(rows),
            "say": f"BCF 2.1 taiyaar: {len(rows)} topics (open/assigned candidates). "
                   "Yeh issue-list hai - resolution discussion insaanon mein hoti hai."}


def _match(e: CBimElement, kind: str, value: str) -> bool:
    v = (value or "").strip().upper()
    if kind == "class":
        return e.ifc_class.upper() == v
    if kind == "storey":
        return (e.storey or "").strip().upper() == v
    return v in (e.name or "").upper()


def link4d(tenant: str, model_id: str, activity: str, match_kind: str, match_value: str,
           start: str = "", finish: str = "", note: str = "") -> dict:
    """4D mapping (#21): HER activity mapped to a class / storey / name slice, with dates. Hoola keeps
    the mapping and reports the model quantities per activity - it never computes a schedule."""
    if match_kind not in ("class", "storey", "name"):
        raise CstError("match_kind: class | storey | name")
    if not str(activity or "").strip() or not str(match_value or "").strip():
        raise CstError("Activity aur match value bataiye (jaise class=IFCWALL, storey='Ground Floor').")
    with session() as s:
        m = s.get(CBimModel, model_id)
        if not m or m.tenant_id != tenant:
            raise CstError("Model nahi mila.")
        els = [e for e in s.scalars(select(CBimElement).where(
            CBimElement.tenant_id == tenant, CBimElement.model_id == model_id)).all()
            if _match(e, match_kind, match_value)]
    with _LOCK, session() as s:
        x = CBimLink4d(tenant_id=tenant, model_id=model_id, activity=activity.strip()[:160],
                       match_kind=match_kind, match_value=match_value.strip()[:120],
                       start=(start or "")[:10], finish=(finish or "")[:10], note=note.strip()[:200])
        s.add(x)
        s.flush()
        lid = x.id
    vol = sum(_qty_find(_j(e.qty, {}), "volume") or 0.0 for e in els)
    return {"link_id": lid, "elements": len(els), "volume_m3": round(vol, 3),
            "say": f"4D link: '{activity}' <-> {match_kind}='{match_value}' ({len(els)} elements, "
                   f"{vol:,.1f} m3 model quantity). Mapping AAPKI hai - schedule Hoola nahi banata."}


def report4d(tenant: str, model_id: str) -> dict:
    """The 4D report: per linked activity, the element count and the model quantities it covers."""
    with session() as s:
        m = s.get(CBimModel, model_id)
        if not m or m.tenant_id != tenant:
            raise CstError("Model nahi mila.")
        links = s.scalars(select(CBimLink4d).where(CBimLink4d.tenant_id == tenant,
                                                   CBimLink4d.model_id == model_id)).all()
        els = s.scalars(select(CBimElement).where(CBimElement.tenant_id == tenant,
                                                  CBimElement.model_id == model_id)).all()
    out = []
    for lk in links:
        hits = [e for e in els if _match(e, lk.match_kind, lk.match_value)]
        out.append({"activity": lk.activity, "match": f"{lk.match_kind}={lk.match_value}",
                    "start": lk.start, "finish": lk.finish, "elements": len(hits),
                    "volume_m3": round(sum(_qty_find(_j(e.qty, {}), "volume") or 0.0 for e in hits), 3)})
    return {"model_id": model_id, "links": out,
            "say": f"4D report: {len(out)} activities mapped. Quantities MODEL ke hain, dates AAPKI - "
                   "yeh mapping report hai, programme nahi."}


def qty5d(tenant: str, model_id: str, match_kind: str = "", match_value: str = "") -> dict:
    """5D take-off (#21): the model's own Volume/Area quantities as rows with their GUID trail.
    Hoola invents no formula here - the quantity is the model's, the trail is the GUID."""
    with session() as s:
        m = s.get(CBimModel, model_id)
        if not m or m.tenant_id != tenant:
            raise CstError("Model nahi mila.")
        els = [e for e in s.scalars(select(CBimElement).where(
            CBimElement.tenant_id == tenant, CBimElement.model_id == model_id)).all()
            if (not match_kind or _match(e, match_kind, match_value))]
    rows, taken = [], 0
    with _LOCK, session() as s:
        for e in els:
            q = _j(e.qty, {})
            vol = _qty_find(q, "volume")
            area = _qty_find(q, "area")
            for kn, unit, val in (("Volume", "m3", vol), ("Area", "m2", area)):
                if val:
                    x = CBimTakeoff(tenant_id=tenant, model_id=model_id, guid=e.guid[:40],
                                    ifc_class=e.ifc_class[:60], name=e.name[:200], qty=val, unit=unit,
                                    source_ref=f"IFC IfcQuantity{kn} of {e.guid}"[:160])
                    s.add(x)
                    s.flush()
                    rows.append({"takeoff_id": x.id, "guid": e.guid, "class": e.ifc_class, "name": e.name,
                                 "qty": val, "unit": unit, "source_ref": x.source_ref})
                    taken += 1
    if not taken:
        raise CstError("Model elements mein koi Volume/Area quantity nahi mili - 5D take-off ke liye "
                       "model ko quantities ke saath export karo (IfcElementQuantity). Guess nahi karta.")
    return {"rows": rows, "taken": taken,
            "say": f"5D: {taken} quantity rows store (qty MODEL ke IfcQuantity se, GUID trail ke saath). "
                   "Rate lagana = qty x rate, rate ka SOURCE saath - phir cost banti hai."}


def cost5d(tenant: str, takeoff_id: str, rate: float, rate_source: str) -> dict:
    """The 5D cost on one row: qty x rate - the ONLY arithmetic, and the rate must carry its source."""
    if _num(rate) <= 0:
        raise CstError("Rate bataiye (> 0).")
    if not str(rate_source or "").strip():
        raise CstError("Rate ka SOURCE bataiye (SOR item / quote / rate build-up id) - bina source ka "
                       "rate cost nahi banta, guess hai.")
    with _LOCK, session() as s:
        x = s.get(CBimTakeoff, takeoff_id)
        if not x or x.tenant_id != tenant:
            raise CstError("Take-off row nahi mili.")
        x.rate, x.rate_source = _num(rate), rate_source.strip()[:160]
        x.amount = round(x.qty * x.rate, 2)
        amt, qty, rt = x.amount, x.qty, x.rate
    return {"takeoff_id": takeoff_id, "qty": qty, "rate": rt, "amount": amt, "rate_source": rate_source,
            "say": f"5D cost: {qty:g} x {rt:g} = {amt:,.2f} (rate: {rate_source[:60]}). Working paper - "
                   "billing ka certification QS/billing engineer ke haath mein."}


def ids_check(tenant: str, model_id: str, ids_text: str) -> dict:
    """IDS subset check (#18/#20 family): the IDS XML's ENTITY facets (class must exist) and PROPERTY
    facets (pset.property must exist with a value) checked against the stored read. Facets we cannot
    verify come back UNVERIFIED - 'we exchanged IFC' becomes checkable only this far, and says so."""
    if "<ids" not in (ids_text or "").lower() and "<Ids" not in (ids_text or ""):
        raise CstError("Yeh IDS XML nahi lag raha - IDS (ids:Ids) ka text bhejo.")
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(ids_text)
    except ET.ParseError as ex:
        raise CstError(f"IDS XML padha nahi ja raha: {ex}") from None
    with session() as s:
        els = s.scalars(select(CBimElement).where(CBimElement.tenant_id == tenant,
                                                  CBimElement.model_id == model_id)).all()
    props_by_guid: dict[str, dict] = {e.guid: _j(e.qty, {}) for e in els}
    specs = []
    for spec in root.iter():
        tag = spec.tag.split("}")[-1]
        if tag != "Specification":
            continue
        ents_req, props_req = [], []
        for node in spec.iter():
            t = node.tag.split("}")[-1]
            if t == "Entity":
                nm = (node.get("name") or "").upper()
                if nm:
                    ents_req.append(nm)
            elif t == "Property":
                ps, pn = node.get("propertySet") or "", node.get("name") or ""
                if pn:
                    props_req.append((ps.upper(), pn.upper()))
        ok = fail = un = 0
        detail = []
        for guid, props in props_by_guid.items():
            cls_hits = [e for e in els if e.guid == guid]
            cls = cls_hits[0].ifc_class.upper() if cls_hits else ""
            if ents_req and cls not in ents_req:
                continue
            row = {"guid": guid, "class": cls, "state": "pass"}
            for ps, pn in props_req:
                if any(pn in k.upper() for k in props):
                    continue
                row["state"] = "unverified" if not props else "fail"
                break
            if row["state"] == "pass":
                ok += 1
            elif row["state"] == "fail":
                fail += 1
            else:
                un += 1
            detail.append(row)
        specs.append({"spec": (spec.get("name") or spec.get("id") or "")[:80],
                      "entity_facets": ents_req, "property_facets": [f"{ps}.{pn}" for ps, pn in props_req],
                      "pass": ok, "fail": fail, "unverified": un})
    return {"specs": specs,
            "say": "IDS subset check: ENTITY (class) aur PROPERTY (pset.property presence) facets only - "
                   "datatype/cardinality facets UNVERIFIED kehlati hain (guess nahi). 'IFC exchange "
                   "checkable hai - is IDS tak.'"}
