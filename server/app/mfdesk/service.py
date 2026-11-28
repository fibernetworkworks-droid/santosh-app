"""The Mainframe Modernization Architect's desk: COBOL programs read (paragraphs, dead code, calls, SQL, CICS, files, risks),
copybook layouts with target types and records decoded from their bytes, JCL, the whole inventory as a dependency map with migration
waves, translations proved side by side against the old output, and a CI check that keeps them proved - all in code, no model, no
money. Nothing runs on her mainframe or her servers. Pasted sources, records and outputs are DATA."""
from __future__ import annotations

import json
import logging

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import ci as CI, cobol as CB, inventory as IV, jcl as JC, layout as LY, proof as PF

log = logging.getLogger("santosh.mfdesk")

KINDS = ("program", "copybook", "jcl", "inventory", "proof")
PRE = {"program": "P", "copybook": "C", "jcl": "J", "inventory": "I", "proof": "D"}
FIELDS = ("encoding", "target", "keys", "ignore", "tolerance", "run_cmd", "build_cmd", "golden", "out_file", "ci_copybook", "runner", "setup")
KEEP = 400
MAX_TEXT = 30_000_000
ERRORS = (CB.CobolError, LY.LayoutError, JC.JclError, IV.InventoryError, PF.ProofError, CI.CiError)
TARGETS = ("java", "python", "csharp")
SETUPS = ("", "java", "python", "dotnet", "gnucobol")


class MfError(ValueError):
    pass


class MItem(Base):
    __tablename__ = "mfdesk_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("mf"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    kind: Mapped[str] = mapped_column(String(12), default="program")
    title: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="open")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MSettings(Base):
    __tablename__ = "mfdesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    encoding: Mapped[str] = mapped_column(String(10), default="cp037")
    target: Mapped[str] = mapped_column(String(10), default="java")
    keys: Mapped[str] = mapped_column(String(200), default="")
    ignore: Mapped[str] = mapped_column(String(300), default="")
    tolerance: Mapped[float] = mapped_column(Float, default=0.0)
    run_cmd: Mapped[str] = mapped_column(String(400), default="")
    build_cmd: Mapped[str] = mapped_column(String(400), default="")
    golden: Mapped[str] = mapped_column(String(160), default="tests/golden/output.txt")
    out_file: Mapped[str] = mapped_column(String(160), default="output.txt")
    ci_copybook: Mapped[str] = mapped_column(String(40), default="")
    runner: Mapped[str] = mapped_column(String(40), default="ubuntu-24.04")
    setup: Mapped[str] = mapped_column(String(12), default="java")


_READY: set[int] = set()


def _tables() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    MItem.__table__.create(eng, checkfirst=True)
    MSettings.__table__.create(eng, checkfirst=True)
    _READY.add(id(eng))


def settings(tenant: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        r = s.get(MSettings, tenant)
        d = {k: getattr(r, k) if r else MSettings.__table__.c[k].default.arg for k in FIELDS}
        d["set"] = r is not None
        return d


def _num(v: Any, name: str, lo: float, hi: float, whole: bool = False) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise MfError(f"{name}: a number.")
    if whole and x != int(x):
        raise MfError(f"{name}: a whole number.")
    if not lo <= x <= hi:
        raise MfError(f"{name}: {lo:g} to {hi:g}.")
    return int(x) if whole else x


def save_settings(tenant: str, **f: Any) -> dict[str, Any]:
    _tables()
    c: dict[str, Any] = {}
    g = lambda k: f.get(k) not in (None, "")   # noqa: E731
    if g("encoding"):
        if f["encoding"] not in LY.ENCODINGS:
            raise MfError("Character set: " + ", ".join(LY.ENCODINGS) + ".")
        c["encoding"] = f["encoding"]
    if g("target"):
        if f["target"] not in TARGETS:
            raise MfError("Target language: java, python or csharp.")
        c["target"] = f["target"]
    if "setup" in f:
        if str(f["setup"] or "") not in SETUPS:
            raise MfError("Toolchain: java, python, dotnet, gnucobol or none.")
        c["setup"] = str(f["setup"] or "")
    if g("tolerance"):
        c["tolerance"] = _num(f["tolerance"], "Tolerance", 0, 1e6)
    for k in ("keys", "ignore", "run_cmd", "build_cmd", "golden", "out_file", "ci_copybook", "runner"):
        if f.get(k) is not None:
            c[k] = str(f[k]).strip()[:400]
    probe = {**settings(tenant), **c}
    if probe.get("ci_copybook"):
        _layout_of(tenant, probe["ci_copybook"])
    if probe.get("run_cmd"):
        try:
            _ci(tenant, probe)
        except CI.CiError as e:
            raise MfError(str(e))
    with session() as s:
        r = s.get(MSettings, tenant)
        if r is None:
            r = MSettings(tenant_id=tenant)
            s.add(r)
        for k, v in c.items():
            setattr(r, k, v)
    return settings(tenant)


def _layout_of(tenant: str, ref: str) -> list[dict[str, Any]]:
    with session() as s:
        r = _row(s, tenant, ref)
        if r.kind != "copybook":
            raise MfError(f"{r.number} is not a copybook layout.")
        return list((r.result or {}).get("rows") or [])


def _ci(tenant: str, st: dict[str, Any]) -> dict[str, Any]:
    lay = _layout_of(tenant, st["ci_copybook"]) if st.get("ci_copybook") else None
    return CI.workflow(run_cmd=st["run_cmd"], build_cmd=st["build_cmd"], golden=st["golden"], out_file=st["out_file"], layout=lay,
                       keys=st["keys"] if lay else "", ignore=st["ignore"] if lay else "", tolerance=st["tolerance"], runner=st["runner"], setup=st["setup"])


def _bad(res: dict[str, Any]) -> bool:
    return any(i.get("sev") == "bad" for i in res.get("issues") or [])


def _brief(kind: str, res: dict[str, Any]) -> dict[str, Any]:
    cnt = res.get("counts") or {}
    b: dict[str, Any] = {"bad": _bad(res) or bool(cnt.get("bad")), "issues": (cnt.get("bad") or 0) + (cnt.get("warn") or 0)}
    if kind == "program":
        ps = res.get("programs") or []
        p0 = ps[0] if ps else {}
        b.update(programs=len(ps), loc=sum(p.get("loc", 0) for p in ps), dead=sum(len(p.get("dead") or []) for p in ps),
                 online=any(p.get("online") for p in ps), tables=len({t for p in ps for t in p.get("tables") or []}), name=p0.get("name"))
    elif kind == "copybook":
        b.update(length=res.get("length"), fields=res.get("fields"), packed=(res.get("kinds") or {}).get("packed"), decoded=bool(res.get("decoded")))
    elif kind == "jcl":
        b.update(jobs=len(res.get("jobs") or []), steps=len(res.get("steps") or []), programs=len(res.get("programs") or []))
    elif kind == "inventory":
        t = res.get("totals") or {}
        b.update(programs=t.get("programs"), loc=t.get("loc"), waves=len(res.get("waves") or []), missing=sum(len(v) for v in (res.get("missing") or {}).values()),
                 cycles=len(res.get("cycles") or []))
    elif kind == "proof":
        b.update(proved=res.get("proved"), records=res.get("pairs"), differ=res.get("differ"), reordered=res.get("reordered"),
                 only=(res.get("only_old") or 0) + (res.get("only_new") or 0))
        b["bad"] = not res.get("proved")
    return b


def _view(r: MItem, full: bool = False) -> dict[str, Any]:
    d = {"id": r.id, "number": r.number, "kind": r.kind, "title": r.title, "status": r.status, "note": r.note,
         "created_at": r.created_at.isoformat() if r.created_at else "", "updated_at": r.updated_at.isoformat() if r.updated_at else "",
         "brief": _brief(r.kind, r.result or {})}
    if full:
        d.update(result=r.result or {}, text=r.text, inputs=r.inputs or {})
    return d


def items(tenant: str, kind: str = "", limit: int = 150) -> list[dict[str, Any]]:
    _tables()
    with session() as s:
        q = select(MItem).where(MItem.tenant_id == tenant)
        if kind:
            q = q.where(MItem.kind == kind)
        return [_view(r) for r in s.scalars(q.order_by(MItem.updated_at.desc()).limit(limit)).all()]


def _row(s, tenant: str, iid: str) -> MItem:
    r = s.get(MItem, str(iid or ""))
    if r is None or r.tenant_id != tenant:
        r = s.scalars(select(MItem).where(MItem.tenant_id == tenant, MItem.number == str(iid or "").upper())).first()
        if r is None:
            raise MfError("Not found.")
    return r


def get(tenant: str, iid: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        return _view(_row(s, tenant, iid), True)


def _dict(v: Any) -> dict[str, Any]:
    if isinstance(v, dict):
        return v
    if isinstance(v, str) and v.strip():
        try:
            d = json.loads(v)
        except ValueError:
            raise MfError("The settings must be JSON.")
        if isinstance(d, dict):
            return d
    return {}


def _run(tenant: str, kind: str, text: str, inp: dict[str, Any], st: dict[str, Any]) -> tuple[dict[str, Any], str]:
    g = lambda k, d=None: inp.get(k) if inp.get(k) not in (None, "") else d   # noqa: E731
    if kind == "program":
        res = CB.analyse(text)
        ps = res["programs"]
        return res, (f"Program {ps[0]['name']}" if len(ps) == 1 else f"{len(ps)} programs: " + ", ".join(p["name"] for p in ps[:3]))[:120]
    if kind == "copybook":
        enc = str(g("encoding", st["encoding"]))
        if enc not in LY.ENCODINGS:
            raise MfError("Character set: " + ", ".join(LY.ENCODINGS) + ".")
        res = LY.analyse(text, enc, str(g("sample", "")))
        return res, "Layout " + ", ".join(r["name"] for r in res["records"][:3])
    if kind == "jcl":
        res = JC.analyse(text)
        return res, "JCL " + ", ".join(j["name"] for j in res["jobs"][:3])
    if kind == "inventory":
        res = IV.analyse(text)
        return res, f"Map: {res['totals']['programs']} program{'' if res['totals']['programs'] == 1 else 's'}, {res['totals']['jobs']} job{'' if res['totals']['jobs'] == 1 else 's'}"
    lay = _layout_of(tenant, str(g("copybook"))) if g("copybook") else None
    res = PF.prove(text, lay, str(g("keys", st["keys"] if lay else "")), str(g("ignore", st["ignore"] if lay else "")), g("tolerance", st["tolerance"]), str(g("mode", "")))
    return res, f"Proof: {res['old']['name']} vs {res['new']['name']}"[:120]


def add(tenant: str, kind: str, title: str = "", text: Any = "", inputs: Any = None) -> dict[str, Any]:
    _tables()
    if kind not in KINDS:
        raise MfError("Kind: " + " | ".join(KINDS))
    st = settings(tenant)
    inp = _dict(inputs)
    text = str(text or "")
    if len(text) > MAX_TEXT:
        raise MfError("That is longer than 30,000,000 characters.")
    if not text.strip():
        raise MfError({"program": "Paste the COBOL source first.", "copybook": "Paste the copybook (01 / 05 levels with PIC clauses) first.",
                         "jcl": "Paste the JCL first: the JOB card, its EXEC steps and DD statements.",
                         "inventory": "Paste the sources first, each under '## name'.",
                         "proof": "Paste the old output under '## old' and the new output under '## new'."}[kind])
    try:
        res, auto = _run(tenant, kind, text, inp, st)
    except ERRORS as e:
        raise MfError(str(e))
    with session() as s:
        n = len(s.scalars(select(MItem.id).where(MItem.tenant_id == tenant, MItem.kind == kind)).all()) + 1
        r = MItem(tenant_id=tenant, number=f"{PRE[kind]}-{n:04d}", kind=kind, title=(str(title or "").strip() or auto)[:200], text=text,
                  inputs=inp, result=res)
        s.add(r)
        s.flush()
        iid = r.id
        cnt = len(s.scalars(select(MItem.id).where(MItem.tenant_id == tenant)).all())
        if cnt > KEEP:
            for x in s.scalars(select(MItem).where(MItem.tenant_id == tenant).order_by(MItem.updated_at.asc()).limit(cnt - KEEP)).all():
                s.delete(x)
    return get(tenant, iid)


def mark(tenant: str, iid: str, status: str, note: str = "") -> dict[str, Any]:
    if status not in ("open", "fixed", "ignored"):
        raise MfError("Status: open | fixed | ignored")
    _tables()
    with session() as s:
        r = _row(s, tenant, iid)
        r.status, r.updated_at = status, now()
        if note:
            r.note = str(note)[:1000]
        iid = r.id
    return get(tenant, iid)


def delete(tenant: str, iid: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        s.delete(_row(s, tenant, iid))
    return {"ok": True, "say": "Removed."}


def ci_for(tenant: str) -> dict[str, Any]:
    st = settings(tenant)
    if not st.get("run_cmd"):
        return {"missing": True, "say": "Set the command that runs the new program on the saved input in Settings first."}
    try:
        return _ci(tenant, st)
    except CI.CiError as e:
        raise MfError(str(e))


def health() -> dict[str, Any]:
    return {"kinds": list(KINDS), "encodings": list(LY.ENCODINGS), "targets": list(TARGETS), "utilities": len(JC.UTIL),
            "notes": "Everything is worked out in code from what you paste. Nothing runs on your mainframe or your servers."}
