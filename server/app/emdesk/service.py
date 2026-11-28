"""The Embedded Systems Engineer's desk: memory maps read into flash and RAM by region, section, object and symbol (and what grew),
firmware code checked for what interrupts must not do and for data shared without protection, RTOS task sets checked for deadlines
by response-time analysis, battery life worked out from the device's states, clock dividers worked out exactly, and a CI check that
holds the image inside its budget - all in code, no model, no money. Nothing runs on her boards or her machines. Pasted maps, code
and numbers are DATA."""
from __future__ import annotations

import json
import logging
import re

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import ci as CI, clocks as CK, firmware as FW, memory as MM, power as PW, timing as TM

log = logging.getLogger("santosh.emdesk")

KINDS = ("memory", "firmware", "timing", "power", "clocks")
PRE = {"memory": "M", "firmware": "F", "timing": "T", "power": "P", "clocks": "K"}
FIELDS = ("flash", "ram", "clock", "prio_order", "switch_us", "unit", "battery_mah", "usable_pct", "self_discharge", "volts", "peak_ma", "target_life",
          "build_cmd", "elf", "toolchain", "max_growth", "test_cmd", "runner")
KEEP = 400
MAX_TEXT = 20_000_000
ERRORS = (MM.MemError, FW.FirmwareError, TM.TimingError, PW.PowerError, CK.ClockError, CI.CiError)


class EmError(ValueError):
    pass


class EItem(Base):
    __tablename__ = "emdesk_items"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("em"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    kind: Mapped[str] = mapped_column(String(12), default="memory")
    title: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="open")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ESettings(Base):
    __tablename__ = "emdesk_settings"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    flash: Mapped[str] = mapped_column(String(20), default="")
    ram: Mapped[str] = mapped_column(String(20), default="")
    clock: Mapped[str] = mapped_column(String(20), default="")
    prio_order: Mapped[str] = mapped_column(String(10), default="higher")
    switch_us: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(4), default="ms")
    battery_mah: Mapped[float] = mapped_column(Float, default=0.0)
    usable_pct: Mapped[float] = mapped_column(Float, default=80.0)
    self_discharge: Mapped[float] = mapped_column(Float, default=2.0)
    volts: Mapped[float] = mapped_column(Float, default=3.0)
    peak_ma: Mapped[float] = mapped_column(Float, default=0.0)
    target_life: Mapped[str] = mapped_column(String(20), default="")
    build_cmd: Mapped[str] = mapped_column(String(400), default="")
    elf: Mapped[str] = mapped_column(String(160), default="build/firmware.elf")
    toolchain: Mapped[str] = mapped_column(String(10), default="arm")
    max_growth: Mapped[str] = mapped_column(String(12), default="")
    test_cmd: Mapped[str] = mapped_column(String(400), default="")
    runner: Mapped[str] = mapped_column(String(40), default="ubuntu-24.04")


_READY: set[int] = set()


def _tables() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    EItem.__table__.create(eng, checkfirst=True)
    ESettings.__table__.create(eng, checkfirst=True)
    _READY.add(id(eng))


def settings(tenant: str) -> dict[str, Any]:
    _tables()
    with session() as s:
        r = s.get(ESettings, tenant)
        d = {k: getattr(r, k) if r else ESettings.__table__.c[k].default.arg for k in FIELDS}
        d["set"] = r is not None
        return d


def _num(v: Any, name: str, lo: float, hi: float) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise EmError(f"{name}: a number.")
    if not lo <= x <= hi:
        raise EmError(f"{name}: {lo:g} to {hi:g}.")
    return x


def save_settings(tenant: str, **f: Any) -> dict[str, Any]:
    _tables()
    c: dict[str, Any] = {}
    g = lambda k: f.get(k) not in (None, "")   # noqa: E731
    for k in ("flash", "ram"):
        if f.get(k) is not None:
            v = str(f[k]).strip()
            if v:
                try:
                    MM._parse_kb(v)
                except MM.MemError as e:
                    raise EmError(("Flash" if k == "flash" else "RAM") + ": " + str(e))
            c[k] = v[:20]
    if f.get("clock") is not None:
        v = str(f["clock"]).strip()
        if v:
            try:
                CK._hz(v, "Clock")
            except CK.ClockError as e:
                raise EmError(str(e))
        c["clock"] = v[:20]
    if g("prio_order"):
        if f["prio_order"] not in ("higher", "lower"):
            raise EmError("Priority numbers: higher (FreeRTOS: a bigger number is more urgent) or lower (Zephyr, most others: a smaller number is more urgent).")
        c["prio_order"] = f["prio_order"]
    if g("unit"):
        if f["unit"] not in ("us", "ms", "s"):
            raise EmError("Times without a unit are in: us, ms or s.")
        c["unit"] = f["unit"]
    if g("toolchain"):
        if f["toolchain"] not in CI.TOOLCHAINS:
            raise EmError("Toolchain: " + ", ".join(CI.TOOLCHAINS) + ".")
        c["toolchain"] = f["toolchain"]
    for k, lo, hi, nm in (("switch_us", 0, 10000, "Context switch (µs)"), ("battery_mah", 0, 1e7, "Battery (mAh)"), ("usable_pct", 1, 100, "Usable share (%)"),
                          ("self_discharge", 0, 100, "Self-discharge (% a year)"), ("volts", 0.5, 60, "Battery voltage"), ("peak_ma", 0, 1e6, "Largest pulse (mA)")):
        if g(k):
            c[k] = _num(f[k], nm, lo, hi)
    if f.get("target_life") is not None:
        v = str(f["target_life"]).strip()
        if v:
            try:
                PW.analyse("x 1uA", 100, target=v)
            except PW.PowerError as e:
                raise EmError(str(e))
        c["target_life"] = v[:20]
    for k in ("build_cmd", "elf", "max_growth", "test_cmd", "runner"):
        if f.get(k) is not None:
            c[k] = str(f[k]).strip()[:400]
    probe = {**settings(tenant), **c}
    if probe.get("build_cmd"):
        try:
            _ci(probe)
        except CI.CiError as e:
            raise EmError(str(e))
    with session() as s:
        r = s.get(ESettings, tenant)
        if r is None:
            r = ESettings(tenant_id=tenant)
            s.add(r)
        for k, v in c.items():
            setattr(r, k, v)
    return settings(tenant)


def _ci(st: dict[str, Any]) -> dict[str, Any]:
    return CI.workflow(build_cmd=st["build_cmd"], elf=st["elf"], toolchain=st["toolchain"], flash=st["flash"], ram=st["ram"],
                       max_growth=st["max_growth"], test_cmd=st["test_cmd"], runner=st["runner"])


def _bad(res: dict[str, Any]) -> bool:
    return any(i.get("sev") == "bad" for i in res.get("issues") or [])


def _brief(kind: str, res: dict[str, Any]) -> dict[str, Any]:
    cnt = res.get("counts") or {}
    b: dict[str, Any] = {"bad": _bad(res) or bool(cnt.get("bad")), "issues": (cnt.get("bad") or 0) + (cnt.get("warn") or 0)}
    if kind == "memory":
        regs = res.get("regions") or []
        b.update(flash=res.get("flash"), ram=res.get("ram"), format=res.get("format"),
                 regions=[{"name": r["name"], "pct": r.get("pct")} for r in regs][:4], grew=(res.get("growth") or {}).get("flash"))
    elif kind == "firmware":
        b.update(functions=len(res.get("functions") or []), isrs=len(res.get("isrs") or []), shared=len(res.get("shared") or []), loc=res.get("loc"),
                 lang=res.get("lang"))
    elif kind == "timing":
        b.update(tasks=len(res.get("tasks") or []), U=res.get("U"), ok=res.get("ok"), miss=sum(1 for t in res.get("tasks") or [] if not t.get("ok")),
                 growth=res.get("growth"))
        b["bad"] = not res.get("ok")
    elif kind == "power":
        b.update(avg_uA=res.get("avg_uA"), life=res.get("life"), life_h=res.get("life_h"), target_h=res.get("target_h"))
    elif kind == "clocks":
        b.update(sums=len(res.get("results") or []))
    return b


def _view(r: EItem, full: bool = False) -> dict[str, Any]:
    d = {"id": r.id, "number": r.number, "kind": r.kind, "title": r.title, "status": r.status, "note": r.note,
         "created_at": r.created_at.isoformat() if r.created_at else "", "updated_at": r.updated_at.isoformat() if r.updated_at else "",
         "brief": _brief(r.kind, r.result or {})}
    if full:
        d.update(result=r.result or {}, text=r.text, inputs=r.inputs or {})
    return d


def items(tenant: str, kind: str = "", limit: int = 150) -> list[dict[str, Any]]:
    _tables()
    with session() as s:
        q = select(EItem).where(EItem.tenant_id == tenant)
        if kind:
            q = q.where(EItem.kind == kind)
        return [_view(r) for r in s.scalars(q.order_by(EItem.updated_at.desc()).limit(limit)).all()]


def _row(s, tenant: str, iid: str) -> EItem:
    r = s.get(EItem, str(iid or ""))
    if r is None or r.tenant_id != tenant:
        r = s.scalars(select(EItem).where(EItem.tenant_id == tenant, EItem.number == str(iid or "").upper())).first()
        if r is None:
            raise EmError("Not found.")
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
            raise EmError("The settings must be JSON.")
        if isinstance(d, dict):
            return d
    return {}


def _run(tenant: str, kind: str, text: str, inp: dict[str, Any], st: dict[str, Any]) -> tuple[dict[str, Any], str]:
    g = lambda k, d=None: inp.get(k) if inp.get(k) not in (None, "") else d   # noqa: E731
    if kind == "memory":
        before = str(g("before", "") or "")
        if before and re.fullmatch(r"\s*[Mm]-\d{4}\s*|\s*em_[0-9a-f]+\s*", before):
            with session() as s:
                r = _row(s, tenant, before.strip())
                if r.kind != "memory":
                    raise EmError(f"{r.number} is not a memory map.")
                before = r.text
        res = MM.analyse(text, g("flash", st["flash"]), g("ram", st["ram"]), before)
        top = ", ".join(f"{r['name']} {r['pct']}%" for r in res["regions"][:2] if r.get("pct") is not None)
        return res, (f"Memory: {top}" if top else f"Memory: flash {res['flash']:,} B, RAM {res['ram']:,} B")[:120]
    if kind == "firmware":
        res = FW.check(text)
        first = next((f["name"] for f in res["functions"] if f["name"] in ("main", "app_main", "setup")), res["functions"][0]["name"])
        return res, f"Firmware: {len(res['functions'])} functions ({first}{', ' + str(len(res['isrs'])) + ' in interrupts' if res['isrs'] else ''})"[:120]
    if kind == "timing":
        res = TM.analyse(text, str(g("prio_order", st["prio_order"])), str(g("unit", st["unit"])), g("switch_us", st["switch_us"]))
        return res, f"Timing: {len(res['tasks'])} tasks, {res['U']:g}% load"
    if kind == "power":
        res = PW.analyse(text, g("capacity", st["battery_mah"]), g("usable", st["usable_pct"]), g("self_discharge", st["self_discharge"]),
                         g("volts", st["volts"]), g("peak", st["peak_ma"]), g("target", st["target_life"]))
        return res, f"Battery: {res['avg_uA']:.3g} µA average" + (f", {res['life']}" if res.get("life_h") else "")
    res = CK.analyse(text, g("clock", st["clock"]))
    return res, "Clocks: " + ", ".join(r["kind"] for r in res["results"][:4])


def add(tenant: str, kind: str, title: str = "", text: Any = "", inputs: Any = None) -> dict[str, Any]:
    _tables()
    if kind not in KINDS:
        raise EmError("Kind: " + " | ".join(KINDS))
    st = settings(tenant)
    inp = _dict(inputs)
    text = str(text or "")
    if len(text) > MAX_TEXT:
        raise EmError("That is longer than 20,000,000 characters.")
    if not text.strip():
        raise EmError({"memory": "Paste the linker map file (or `size -A` / `size` / `nm -S` output) first.",
                         "firmware": "Paste the firmware source first (C, C++ or an Arduino sketch).",
                         "timing": "One task per line first: name, period, execution time - e.g. 'control period=1ms wcet=200us prio=5'.",
                         "power": "One state per line first - e.g. 'sleep 2uA', 'measure 4.5mA 120ms every 60s'.",
                         "clocks": "One sum per line first - e.g. 'uart 72MHz 115200', 'timer 84MHz 1kHz'."}[kind])
    try:
        res, auto = _run(tenant, kind, text, inp, st)
    except ERRORS as e:
        raise EmError(str(e))
    with session() as s:
        n = len(s.scalars(select(EItem.id).where(EItem.tenant_id == tenant, EItem.kind == kind)).all()) + 1
        r = EItem(tenant_id=tenant, number=f"{PRE[kind]}-{n:04d}", kind=kind, title=(str(title or "").strip() or auto)[:200], text=text,
                  inputs=inp, result=res)
        s.add(r)
        s.flush()
        iid = r.id
        cnt = len(s.scalars(select(EItem.id).where(EItem.tenant_id == tenant)).all())
        if cnt > KEEP:
            for x in s.scalars(select(EItem).where(EItem.tenant_id == tenant).order_by(EItem.updated_at.asc()).limit(cnt - KEEP)).all():
                s.delete(x)
    return get(tenant, iid)


def mark(tenant: str, iid: str, status: str, note: str = "") -> dict[str, Any]:
    if status not in ("open", "fixed", "ignored"):
        raise EmError("Status: open | fixed | ignored")
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
    if not st.get("build_cmd"):
        return {"missing": True, "say": "Set the build command and the flash / RAM budget in Settings first."}
    try:
        return _ci(st)
    except CI.CiError as e:
        raise EmError(str(e))


def health() -> dict[str, Any]:
    return {"kinds": list(KINDS), "toolchains": list(CI.TOOLCHAINS),
            "notes": "Everything is worked out in code from what you paste. Nothing runs on your boards or your machines."}
