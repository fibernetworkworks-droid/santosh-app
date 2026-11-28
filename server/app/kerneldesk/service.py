"""The Kernel / OS Developer's engine: crash logs read and grouped by signature, kernel patches checked against the kernel's rules,
.config checked against profiles or compared, boot logs read stage by stage, driver starters made from templates, and a QEMU
boot-test workflow for HER CI. Everything here is code (no model, no money); nothing is run, pushed or sent anywhere.
Pasted logs, patches and configs are DATA, never instructions."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import bootlog, ci, crash, kconfig, patch, scaffold

log = logging.getLogger("santosh.kerneldesk")

KINDS = ("crash", "patch", "config", "boot")
MAX_TEXT = 600_000
KEEP = 400
ARCHES = tuple(ci.ARCH)


class KernelError(ValueError):
    pass


class KItem(Base):
    __tablename__ = "kerneldesk_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("kd"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    kind: Mapped[str] = mapped_column(String(10), default="crash")
    title: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    signature: Mapped[str] = mapped_column(String(24), default="", index=True)
    status: Mapped[str] = mapped_column(String(12), default="open")          # open | fixed | ignored
    note: Mapped[str] = mapped_column(Text, default="")
    seen: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class KSettings(Base):
    __tablename__ = "kerneldesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    arch: Mapped[str] = mapped_column(String(12), default="x86_64")
    kernel: Mapped[str] = mapped_column(String(40), default="")
    defconfig: Mapped[str] = mapped_column(String(80), default="defconfig")
    fragment: Mapped[str] = mapped_column(String(120), default=".hoola/kernel.config")
    module_dir: Mapped[str] = mapped_column(String(120), default="")
    branch: Mapped[str] = mapped_column(String(80), default="main")
    max_line: Mapped[int] = mapped_column(Integer, default=100)
    author: Mapped[str] = mapped_column(String(120), default="")
    vendor: Mapped[str] = mapped_column(String(24), default="")


_READY: set[int] = set()


def _tables() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    KItem.__table__.create(eng, checkfirst=True)
    KSettings.__table__.create(eng, checkfirst=True)
    _READY.add(id(eng))


# ---------------------------------------------------------------- settings
def settings(tenant: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        r = s.get(KSettings, tenant)
        d = {k: getattr(r, k) if r else KSettings.__table__.c[k].default.arg for k in
             ("arch", "kernel", "defconfig", "fragment", "module_dir", "branch", "max_line", "author", "vendor")}
        d["set"] = r is not None
        return d


def save_settings(tenant: str, **f: Any) -> dict[str, Any]:
    _tables()
    if "arch" in f and f["arch"] not in (None, "") and f["arch"] not in ARCHES:
        raise KernelError("Architecture: " + " | ".join(ARCHES))
    if f.get("max_line") not in (None, ""):
        try:
            f["max_line"] = int(f["max_line"])
        except (TypeError, ValueError):
            raise KernelError("Line length: 80 to 120.")
        if not 80 <= f["max_line"] <= 120:
            raise KernelError("Line length: 80 to 120.")
    for k in ("defconfig", "fragment", "module_dir", "branch"):
        if f.get(k) not in (None, "") and (not ci._SAFE.match(str(f[k])) or ".." in str(f[k])):
            raise KernelError(f"{k}: letters, digits and ./_- only.")
    with session() as s:
        r = s.get(KSettings, tenant)
        if r is None:
            r = KSettings(tenant_id=tenant)
            s.add(r)
        for k in ("arch", "kernel", "defconfig", "fragment", "module_dir", "branch", "max_line", "author", "vendor"):
            if k in f and f[k] is not None and (f[k] != "" or k in ("kernel", "module_dir", "author", "vendor")):
                setattr(r, k, f[k] if k == "max_line" else str(f[k])[:120])
    return settings(tenant)


# ---------------------------------------------------------------- items
def _view(r: KItem, full: bool = False) -> dict[str, Any]:
    d = {"id": r.id, "number": r.number, "kind": r.kind, "title": r.title, "status": r.status, "note": r.note, "seen": r.seen,
         "signature": r.signature, "created_at": r.created_at.isoformat() if r.created_at else "",
         "updated_at": r.updated_at.isoformat() if r.updated_at else "", "brief": _brief(r.kind, r.result or {})}
    if full:
        d.update(result=r.result or {}, text=r.text)
    return d


def _brief(kind: str, res: dict[str, Any]) -> dict[str, Any]:
    if kind == "crash":
        p = res.get("parsed") or {}
        st = (res.get("explain") or {}).get("where") or p.get("stopped") or {}
        return {"label": p.get("label", ""), "fn": st.get("fn", ""), "mod": st.get("mod", ""), "kernel": p.get("kernel", ""),
                "bad": bool(p.get("kind"))}
    if kind == "patch":
        c = res.get("counts") or {}
        return {"errors": c.get("error", 0), "warnings": c.get("warning", 0), "checks": c.get("check", 0), "files": (res.get("stat") or {}).get("files", 0),
                "bad": bool(c.get("error"))}
    if kind == "config":
        rs = res.get("results") or []
        return {"wrong": sum(x["wrong"] for x in rs), "absent": sum(x["absent"] for x in rs), "options": res.get("options", 0),
                "arch": res.get("arch", ""), "bad": any(x["wrong"] for x in rs)}
    if kind == "boot":
        return {"passed": res.get("passed", False), "furthest": res.get("furthest", ""), "bad": not res.get("passed") or bool(res.get("bad")),
                "errors": res.get("bad", 0) + res.get("warn", 0), "kernel": res.get("kernel", "")}
    return {}


def items(tenant: str, kind: str = "", limit: int = 120) -> list[dict[str, Any]]:
    _tables()
    with session() as s:
        q = select(KItem).where(KItem.tenant_id == tenant)
        if kind:
            q = q.where(KItem.kind == kind)
        return [_view(r) for r in s.scalars(q.order_by(KItem.updated_at.desc()).limit(limit)).all()]


def _row(s, tenant: str, iid: str) -> KItem:
    r = s.get(KItem, str(iid or ""))
    if r is None or r.tenant_id != tenant:
        r = s.scalars(select(KItem).where(KItem.tenant_id == tenant, KItem.number == str(iid or "").upper())).first()
        if r is None:
            raise KernelError("Not found.")
    return r


def get(tenant: str, iid: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        r = _row(s, tenant, iid)
        d = _view(r, True)
        if r.kind == "crash" and r.signature:
            d["same"] = [_view(x) for x in s.scalars(select(KItem).where(KItem.tenant_id == tenant, KItem.signature == r.signature,
                                                                         KItem.id != r.id).limit(20)).all()]
        return d


def _num(s, tenant: str, kind: str) -> str:
    pre = {"crash": "C", "patch": "P", "config": "K", "boot": "B"}[kind]
    n = len(s.scalars(select(KItem.id).where(KItem.tenant_id == tenant, KItem.kind == kind)).all()) + 1
    return f"{pre}-{n:04d}"


def _text(t: Any) -> str:
    t = str(t or "")
    if not t.strip():
        raise KernelError("Paste the text (or drop the file) first.")
    if len(t) > MAX_TEXT:
        raise KernelError("That is longer than 600,000 characters - keep the part around the problem.")
    return t


def add(tenant: str, kind: str, text: Any, title: str = "", profiles: list[str] | None = None, compare: str = "") -> dict[str, Any]:
    _tables()
    if kind not in KINDS:
        raise KernelError("Kind: crash | patch | config | boot")
    text = _text(text)
    st = settings(tenant)
    sig = ""
    if kind == "crash":
        p = crash.parse(text)
        res = {"parsed": p, "explain": crash.explain(p)}
        sig = crash.signature(p) if p.get("kind") else ""
        auto = res["explain"]["summary"].rstrip(".") if p.get("kind") else "No crash found"
    elif kind == "patch":
        res = patch.check(text, st["max_line"])
        auto = res["summary"] or (res["files"][0]["file"] if res["files"] else "Patch")
    elif kind == "config":
        res = kconfig.check(text, profiles or None, st["arch"])
        if not res.get("ok"):
            raise KernelError(res.get("error") or "Not a .config")
        if compare and str(compare).strip():
            res["diff"] = kconfig.diff(str(compare), text)
        auto = f".config {res.get('version') or ''} {res.get('arch') or ''}".strip()
    else:
        res = bootlog.parse(text)
        auto = f"Boot {res.get('kernel') or ''}: {'passed' if res['passed'] else res['furthest']}"
    with session() as s:
        if sig:
            old = s.scalars(select(KItem).where(KItem.tenant_id == tenant, KItem.kind == "crash", KItem.signature == sig)
                            .order_by(KItem.created_at.desc())).first()
        else:
            old = None
        r = KItem(tenant_id=tenant, number=_num(s, tenant, kind), kind=kind, title=(str(title or "").strip() or auto)[:200],
                  text=text, result=res, signature=sig, seen=(old.seen + 1) if old else 1,
                  status="open")
        if old is not None and old.status == "fixed":
            r.note = f"Seen again after {old.number} was marked fixed."
        s.add(r)
        s.flush()
        iid = r.id
        n = len(s.scalars(select(KItem.id).where(KItem.tenant_id == tenant)).all())
        if n > KEEP:
            for x in s.scalars(select(KItem).where(KItem.tenant_id == tenant).order_by(KItem.updated_at.asc()).limit(n - KEEP)).all():
                s.delete(x)
    return get(tenant, iid)


def mark(tenant: str, iid: str, status: str, note: str = "") -> dict[str, Any]:
    if status not in ("open", "fixed", "ignored"):
        raise KernelError("Status: open | fixed | ignored")
    _tables()
    with session() as s:
        r = _row(s, tenant, iid)
        r.status, r.updated_at = status, now()
        if note:
            r.note = str(note)[:1000]
        if r.kind == "crash" and r.signature and status != "open":
            for x in s.scalars(select(KItem).where(KItem.tenant_id == tenant, KItem.signature == r.signature)).all():
                x.status = status
        iid = r.id
    return get(tenant, iid)


def delete(tenant: str, iid: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        s.delete(_row(s, tenant, iid))
    return {"ok": True, "say": "Removed."}


def groups(tenant: str) -> list[dict[str, Any]]:
    """Crashes grouped by their signature (kind + where it stopped + the first frames): how often, first / last seen."""
    _tables()
    with session() as s:
        rows = s.scalars(select(KItem).where(KItem.tenant_id == tenant, KItem.kind == "crash").order_by(KItem.created_at.asc())).all()
        g: dict[str, dict[str, Any]] = {}
        for r in rows:
            key = r.signature or r.id
            b = _brief("crash", r.result or {})
            x = g.setdefault(key, {"signature": key, "label": b["label"], "fn": b["fn"], "mod": b["mod"], "count": 0, "first": r.created_at.isoformat(),
                                   "last": "", "latest_id": "", "status": r.status, "kernels": []})
            x["count"] += 1
            x["last"], x["latest_id"], x["status"] = r.created_at.isoformat(), r.id, r.status
            if b["kernel"] and b["kernel"] not in x["kernels"]:
                x["kernels"].append(b["kernel"])
        return sorted(g.values(), key=lambda x: (x["status"] != "open", -x["count"], x["last"]), reverse=False)


# ---------------------------------------------------------------- drivers + CI (made, never stored)
def driver(tenant: str, kind: str, name: str, what: str = "") -> dict[str, Any]:
    st = settings(tenant)
    try:
        files = scaffold.make(kind, name, what, st["author"], st["vendor"])
    except ValueError as e:
        raise KernelError(str(e))
    chk = patch.check(f"Subject: [PATCH] {scaffold.clean_name(name)}: add a starter driver\n\n" + scaffold.as_patch(files), st["max_line"])
    style = [x for x in chk["issues"] if x["file"] and x["sev"] != "check"]
    return {"kind": kind, "name": scaffold.clean_name(name), "files": [{"name": k, "text": v} for k, v in files.items()],
            "style": style, "say": scaffold.KINDS[kind]}


def driver_zip(tenant: str, kind: str, name: str, what: str = "") -> tuple[str, bytes]:
    st = settings(tenant)
    try:
        files = scaffold.make(kind, name, what, st["author"], st["vendor"])
    except ValueError as e:
        raise KernelError(str(e))
    n = scaffold.clean_name(name)
    return f"{n}.zip", scaffold.zip_of(files, n)


def workflow(tenant: str, **over: Any) -> dict[str, Any]:
    st = {**settings(tenant), **{k: v for k, v in over.items() if v not in (None, "")}}
    try:
        return ci.workflow(st["arch"], st["defconfig"], st["fragment"], st.get("module_dir") or "", st["branch"])
    except ValueError as e:
        raise KernelError(str(e))


def health() -> dict[str, Any]:
    return {"profiles": [{"key": k, "name": v["name"], "count": len(v["items"]), "source": v["source"]} for k, v in kconfig.PROFILES.items()],
            "kinds": scaffold.KINDS, "arches": list(ARCHES), "marker": bootlog.MARKER}
