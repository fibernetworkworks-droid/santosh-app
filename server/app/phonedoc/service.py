"""v0.90 Phone Doctor: "mera phone ... kharab hai" -> fixed, end to end.

  1. Gets the job: she says what is wrong in chat or on a call (her words, any language mix).
  2. Checks the phone itself: the Hoola app reads the phone's own state (battery temperature / health, storage, RAM,
     network, SIM, DND, volumes, date-time, battery saver, the app used most...) and Hoola names what it sees.
  3. Fix steps in the right order, checked against what the phone says and what fixed this problem for others: one step
     at a time, the exact settings screen opens with one tap, then "theek hua?". Steps that lose data (factory reset,
     network reset, reinstall) wait for HER decision.
  4. When the steps run out: the right place, ready as a card: a repair shop / brand service centre near her with what to
     tell them (or a job in her own Mobile Dukaan when she runs one), the operator for SIM / network, and the official
     channels for a lost / stolen phone (block SIM, police complaint, CEIR on Sanchar Saathi) or fraud (1930,
     cybercrime.gov.in, Chakshu).
  5. Delivers and learns: every case keeps a log; which step fixed which problem raises that step for the next person.

Never: bypassing a screen lock / FRP / iCloud (only the owner's own reset or the service centre with the bill), changing
an IMEI, asking for or keeping any password / PIN / OTP. Hoola does not pay or recharge.
"""
from __future__ import annotations

import json
import logging
import re
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from .playbooks import ISSUES, SETTING_LABEL, detect, findings

log = logging.getLogger("santosh.phonedoc")
_LOCK = threading.Lock()
RESULTS = ("fixed", "not_fixed", "skipped", "cant")
STATUS_LABEL = {"open": "Chal raha", "resolved": "Theek ho gaya", "escalated": "Dukaan / madad tak", "closed": "Band"}

GENERIC = {"label": "Kuch aur dikkat", "fault": "other", "escalate": "repair", "steps": [
    {"id": "restart", "title": "Phone restart", "how": "Power button dabake rakhiye > Restart. Bahut si dikkatein yahin theek hoti hain."},
    {"id": "storage", "title": "Storage", "setting": "storage", "check": "storage_used_pct", "how": "Storage 90% se upar ho to jagah khaali kijiye."},
    {"id": "update_apps", "title": "Apps update", "url": "https://play.google.com/store/apps",
     "how": "Play Store > Profile > 'Manage apps & device' > 'Update all'."},
    {"id": "system_update", "title": "Software update", "setting": "system_update", "how": "Settings > Software update > Check."},
    {"id": "safe_mode", "title": "Safe mode", "how": "Power off ko lamba dabaiye > Safe mode: wahan theek ho to koi app wajah hai."},
]}
# urgent playbooks keep their order (money / data first), the phone check doesn't reshuffle them
FIXED_ORDER = {"lost_stolen", "hacked_fraud", "water", "screen_broken", "forgot_lock", "wont_turn_on"}
# finding id -> the snapshot key a step `check`s
FINDING_CHECK = {"storage": "storage_used_pct", "temp": "battery_temp_c", "battery_health": "battery_health",
                 "airplane": "airplane", "sim": "sim_state", "signal": "signal_level", "data_saver": "data_saver",
                 "auto_time": "auto_time", "dnd": "dnd", "ringer": "ring_volume_pct", "media_volume": "media_volume_pct",
                 "bluetooth": "bluetooth_on", "patch": "security_patch", "usb_debugging": "usb_debugging", "top_app": "top_apps",
                 "battery_saver": "battery_saver", "slow_charge": "plugged", "not_charging_now": "plugged", "thermal": "battery_temp_c"}
SNAP_KEYS = {"brand", "model", "sdk", "android", "security_patch", "uptime_hours", "battery_pct", "battery_temp_c", "battery_health",
             "plugged", "charging_status", "battery_voltage_mv", "current_ma", "storage_total_gb", "storage_free_gb",
             "storage_used_pct", "ram_total_gb", "ram_free_pct", "ram_low", "battery_saver", "thermal_status",
             "hoola_battery_unrestricted", "airplane", "sim_state", "operator", "signal_level", "online", "on", "vpn", "data_saver",
             "wifi_on", "bluetooth_on", "ringer", "ring_volume_pct", "media_volume_pct", "call_volume_pct", "dnd", "auto_time",
             "usb_debugging", "developer_options", "brightness_auto", "brightness_pct", "location_on", "screen_timeout_s", "top_apps"}
OPERATOR_HELP = {"jio": "Jio: 199 (Jio number se) / MyJio app", "airtel": "Airtel: 121 / Airtel Thanks app",
                 "vi": "Vi: 199 / Vi app", "bsnl": "BSNL: 1503 / BSNL Selfcare app"}
LOCK_BYPASS = re.compile(r"(frp|google\s*lock|icloud|pattern|password|pin|lock).{0,25}(tod|bypass|hata|khol|remove|crack|todna|unlock)"
                         r"|(bypass|crack|tod).{0,15}(frp|lock|pattern|icloud)", re.IGNORECASE)
IMEI_CHANGE = re.compile(r"imei\s*(?:change|badal|repair|write|likh|null|fix)|(?:change|badal|repair|write)\s*(?:the\s*)?imei", re.IGNORECASE)


class PhoneDocError(Exception):
    pass


class PhoneSnapshot(Base):
    __tablename__ = "phonedoc_snapshots"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ps"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    data: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class PhoneCase(Base):
    __tablename__ = "phonedoc_cases"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pc"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    issue: Mapped[str] = mapped_column(String(32), default="other")
    text: Mapped[str] = mapped_column(Text, default="")
    for_whom: Mapped[str] = mapped_column(String(120), default="")          # "" = her own phone; else a customer / family
    device: Mapped[str] = mapped_column(String(120), default="")
    findings: Mapped[str] = mapped_column(Text, default="[]")
    steps: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(12), default="open")
    fixed_by: Mapped[str] = mapped_column(String(40), default="")
    escalation: Mapped[str] = mapped_column(Text, default="{}")
    mshop_job: Mapped[str] = mapped_column(String(40), default="")
    log: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class PhoneStepStat(Base):
    """What fixed what, across everyone (issue + step -> tried / fixed). No personal data."""
    __tablename__ = "phonedoc_step_stats"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)       # issue:step
    tried: Mapped[int] = mapped_column(Integer, default=0)
    fixed: Mapped[int] = mapped_column(Integer, default=0)


# ---------------------------------------------------------------- helpers
def _j(s: str, default):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(default)) else default
    except (TypeError, ValueError):
        return default


def _aware(d: datetime | None) -> datetime | None:
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _log(c: PhoneCase, what: str, by: str = "hoola") -> None:
    lg = _j(c.log, [])
    lg.append({"at": now().isoformat(timespec="seconds"), "what": what[:300], "by": by})
    c.log = json.dumps(lg[-120:], ensure_ascii=False)


def _publish(tenant: str, kind: str, payload: dict, conv: str = "") -> None:
    from ..events import bus
    try:
        if not conv:
            from ..net.service import home_conv
            conv = home_conv(tenant)
        bus.publish(conv, kind, payload)
    except Exception:
        log.exception("phonedoc publish failed")


def playbook(issue: str) -> dict:
    return ISSUES.get(issue) or GENERIC


def issues() -> list[dict]:
    return [{"id": k, "label": v["label"]} for k, v in ISSUES.items()] + [{"id": "other", "label": GENERIC["label"]}]


# ---------------------------------------------------------------- the phone's own check
def _clean(data: dict) -> dict:
    out: dict[str, Any] = {}
    for k, v in (data or {}).items():
        if k not in SNAP_KEYS:
            continue
        if k == "top_apps":
            apps = []
            for a in (v or [])[:5]:
                if isinstance(a, dict):
                    apps.append({"package": str(a.get("package") or "")[:120], "label": str(a.get("label") or "")[:60],
                                 "minutes": int(a.get("minutes") or 0)})
            out[k] = apps
        elif isinstance(v, (bool, int, float)) or v is None:
            out[k] = round(v, 2) if isinstance(v, float) else v
        else:
            out[k] = str(v)[:80]
    return out


def save_snapshot(tenant: str, data: dict) -> dict[str, Any]:
    snap = _clean(data)
    if not snap:
        raise PhoneDocError("Phone check khaali aaya.")
    with _LOCK, session() as s:
        s.add(PhoneSnapshot(tenant_id=tenant, data=json.dumps(snap, ensure_ascii=False)))
        s.flush()
        old = s.scalars(select(PhoneSnapshot).where(PhoneSnapshot.tenant_id == tenant)
                        .order_by(PhoneSnapshot.created_at.desc()).offset(20)).all()
        for o in old:
            s.delete(o)
    return {"saved": True, "snapshot": snap, "findings": findings(snap)}


def latest_snapshot(tenant: str, max_age_s: int | None = None) -> tuple[dict, datetime | None]:
    with session() as s:
        r = s.scalars(select(PhoneSnapshot).where(PhoneSnapshot.tenant_id == tenant)
                      .order_by(PhoneSnapshot.created_at.desc()).limit(1)).first()
        if not r:
            return {}, None
        at = _aware(r.created_at)
        if max_age_s is not None and at and now() - at > timedelta(seconds=max_age_s):
            return {}, at
        return _j(r.data, {}), at


def summary(snap: dict) -> str:
    """One line about the phone, for chat / call."""
    if not snap:
        return ""
    g = snap.get
    bits = []
    if g("brand") or g("model"):
        bits.append(f"{str(g('brand') or '').title()} {g('model') or ''}".strip())
    if g("battery_pct") is not None:
        bits.append(f"battery {g('battery_pct')}%" + (f", {g('battery_temp_c'):.0f}°C" if isinstance(g("battery_temp_c"), (int, float)) else ""))
    if isinstance(g("storage_used_pct"), (int, float)):
        bits.append(f"storage {g('storage_used_pct'):.0f}% bhari")
    if g("operator"):
        bits.append(f"{g('operator')}" + (f" signal {g('signal_level')}/4" if g("signal_level") is not None else ""))
    if g("on"):
        bits.append(f"net: {g('on')}" + ("" if g("online") in (None, True) else " (internet nahi chal raha)"))
    return ", ".join(bits)


# ---------------------------------------------------------------- steps: order checked against the phone + what worked
def _rate(issue: str, step: str, stats: dict[str, tuple[int, int]]) -> float | None:
    tried, fixed = stats.get(f"{issue}:{step}", (0, 0))
    return (fixed + 1) / (tried + 2) if tried >= 3 else None


def _plan(issue: str, snap: dict, found: list[dict], stats: dict[str, tuple[int, int]], app_pkg: str = "") -> list[dict]:
    spec = playbook(issue)
    hot_checks = {FINDING_CHECK.get(f["id"]) for f in found if issue in f["issues"] or issue == "other"}
    uptime_hot = any(f["id"] == "uptime" for f in found)
    top = (snap.get("top_apps") or [{}])[0] if snap.get("top_apps") else {}
    steps = []
    for i, st in enumerate(spec["steps"]):
        st = dict(st)
        pkg = st.get("pkg", "")
        if pkg == "top":
            pkg = top.get("package", "")
            if top.get("label"):
                st["title"] = f"{st['title']}: {top['label']}"
        if issue == "app_crash" and st.get("setting") == "app_info" and app_pkg:
            pkg = app_pkg
        if st.get("setting") in ("app_info", "app_notifications") and not pkg:
            st["setting"] = "apps"
        st["pkg"] = pkg
        chk = st.get("check")
        matched = (chk in hot_checks) or (st["id"] == "restart" and uptime_hot)
        ok_now = bool(chk) and chk in FINDING_CHECK.values() and chk in snap and not matched and chk != "top_apps"
        st.update(matched=matched, ok_now=ok_now, result=None, at=None, note="",
                  setting_label=SETTING_LABEL.get(st.get("setting") or "", ""))
        if ok_now:
            st["note"] = "Phone check mein yeh theek dikh raha hai."
        r = _rate(issue, st["id"], stats)
        # careful steps always last; fixed-order playbooks keep their order
        if st.get("careful"):
            key = (3, i)
        elif issue in FIXED_ORDER:
            key = (1, i)
        else:
            key = (0 if matched else (2 if ok_now else 1), -(r if r is not None else 0.0), i)
        steps.append((key, st))
    return [st for _, st in sorted(steps, key=lambda x: x[0])]


def _stats(s, issue: str) -> dict[str, tuple[int, int]]:
    rows = s.scalars(select(PhoneStepStat).where(PhoneStepStat.key.like(f"{issue}:%"))).all()
    return {r.key: (r.tried, r.fixed) for r in rows}


def _learn(s, issue: str, step: str, fixed: bool) -> None:
    k = f"{issue}:{step}"[:80]
    r = s.get(PhoneStepStat, k)
    if not r:
        r = PhoneStepStat(key=k, tried=0, fixed=0)
        s.add(r)
    r.tried = (r.tried or 0) + 1
    r.fixed = (r.fixed or 0) + (1 if fixed else 0)


def _current(steps: list[dict]) -> dict | None:
    return next((st for st in steps if st.get("result") is None), None)


def _view(c: PhoneCase) -> dict[str, Any]:
    steps = _j(c.steps, [])
    cur = _current(steps) if c.status == "open" else None
    spec = playbook(c.issue)
    done = [st for st in steps if st.get("result")]
    return {"id": c.id, "issue": c.issue, "label": spec["label"], "text": c.text, "for_whom": c.for_whom, "device": c.device,
            "status": c.status, "status_label": STATUS_LABEL.get(c.status, c.status), "findings": _j(c.findings, []),
            "steps": steps, "current": cur, "step_no": len(done) + 1 if cur else len(done), "total": len(steps),
            "fixed_by": c.fixed_by, "escalation": _j(c.escalation, {}), "mshop_job": c.mshop_job, "log": _j(c.log, [])[-30:],
            "created_at": _aware(c.created_at).isoformat() if c.created_at else ""}


def _step_say(st: dict | None, n: int, total: int) -> str:
    if not st:
        return ""
    s = f"Step {n}/{total}: {st['title']}. {st['how']}"
    if st.get("setting_label"):
        s += f" ('{st['setting_label']}' screen ek tap mein khulegi.)"
    if st.get("careful"):
        s += " Isme data / settings mit sakti hain: aap kahengi tabhi."
    return s + " Ho gaya to bataiye: theek hua ya nahi?"


def _get(s, tenant: str, case: str) -> PhoneCase:
    c = s.get(PhoneCase, str(case or ""))
    if not c and not case:
        c = s.scalars(select(PhoneCase).where(PhoneCase.tenant_id == tenant, PhoneCase.status == "open")
                      .order_by(PhoneCase.updated_at.desc()).limit(1)).first()
    if not c or c.tenant_id != tenant:
        raise PhoneDocError("Yeh phone case nahi mila.")
    return c


# ---------------------------------------------------------------- the job
def refuse(text: str) -> str:
    """Things Hoola never does, in her words."""
    if IMEI_CHANGE.search(text or ""):
        return ("IMEI badalna / likhna kanoonan apraadh hai (Telecommunications Act 2023, dhara 42(3)(c): 3 saal tak jail, "
                "50 lakh tak jurmana). Hoola isme madad nahi karta.")
    if LOCK_BYPASS.search(text or ""):
        return ""   # handled by the forgot_lock playbook (own reset / service centre with bill), never a bypass
    return ""


def start(tenant: str, text: str, issue: str = "", for_whom: str = "", device: str = "", app_package: str = "",
          snapshot: dict | None = None, by: str = "owner", conv: str = "") -> dict[str, Any]:
    text = str(text or "").strip()
    no = refuse(text)
    if no:
        return {"started": False, "say": no}
    if not text and not issue:
        raise PhoneDocError("Phone mein kya dikkat hai? Apne shabdon mein bataiye.")
    guesses = detect(text) if text else []
    issue = issue if issue in ISSUES or issue == "other" else (guesses[0] if guesses else "other")
    own = not for_whom.strip()
    snap: dict = {}
    if own:
        snap = _clean(snapshot) if snapshot else latest_snapshot(tenant, 3600)[0]
    found = findings(snap) if snap else []
    rel = [f for f in found if issue in f["issues"] or issue == "other" or f["level"] == "bad"]
    with _LOCK, session() as s:
        steps = _plan(issue, snap, rel, _stats(s, issue), app_package)
        dev = device.strip() or (f"{str(snap.get('brand') or '').title()} {snap.get('model') or ''}".strip() if snap else "")
        c = PhoneCase(tenant_id=tenant, issue=issue, text=text[:1000], for_whom=for_whom.strip()[:120], device=dev[:120],
                      findings=json.dumps(rel, ensure_ascii=False), steps=json.dumps(steps, ensure_ascii=False))
        s.add(c)
        s.flush()
        _log(c, f"Dikkat: {playbook(issue)['label']} ({text[:120]})" + (f"; phone check: {summary(snap)}" if snap else ""), by)
        v = _view(c)
    say = f"Samajh gaya: {v['label']}."
    if rel:
        say += " Phone check: " + " ".join(f["text"] for f in rel[:4])
    elif own and not snap:
        say += " (Phone ki jaanch abhi nahi mili; Hoola app khulte hi phone khud check ho jayega.)"
    if issue in ("lost_stolen", "hacked_fraud"):
        say += " Pehle wahi jo sabse zaroori hai:"
    say += " " + _step_say(v["current"], v["step_no"], v["total"])
    others = [g for g in guesses[1:3] if g != issue]
    if others:
        say += " (Agar dikkat " + " / ".join(ISSUES[g]["label"] for g in others) + " hai to bataiye, raasta badal dunga.)"
    _publish(tenant, "phonedoc_case", {"case": v["id"], "status": v["status"]}, conv)
    return {"started": True, "case": v, "say": say}


def recheck(tenant: str, case: str = "", snapshot: dict | None = None) -> dict[str, Any]:
    """After a step: what the phone says now vs before (verifies the step did what it should)."""
    snap = _clean(snapshot) if snapshot else latest_snapshot(tenant, 900)[0]
    with _LOCK, session() as s:
        c = _get(s, tenant, case)
        before = {f["id"]: f for f in _j(c.findings, [])}
        if not snap:
            return {"case": _view(c), "say": "Taaza phone check nahi mila: Hoola app khol ke rakhiye."}
        now_f = [f for f in findings(snap) if c.issue in f["issues"] or c.issue == "other" or f["level"] == "bad"]
        after = {f["id"] for f in now_f}
        gone = [before[k]["text"] for k in before if k not in after]
        new = [f["text"] for f in now_f if f["id"] not in before]
        c.findings = json.dumps(now_f, ensure_ascii=False)
        if gone:
            _log(c, "Phone check: theek hua: " + "; ".join(g[:60] for g in gone))
        v = _view(c)
    say = ("Phone check: ab theek: " + " ".join(gone) if gone else "Phone check mein abhi badlaav nahi.")
    if new:
        say += " Naya: " + " ".join(new)
    return {"case": v, "fixed_now": gone, "new": new, "say": say}


def step(tenant: str, case: str, step_id: str = "", result: str = "not_fixed", note: str = "", by: str = "owner",
         conv: str = "") -> dict[str, Any]:
    result = {"theek": "fixed", "haan": "fixed", "yes": "fixed", "nahi": "not_fixed", "no": "not_fixed", "skip": "skipped",
              "chhodo": "skipped", "nahi_ho_paya": "cant"}.get(str(result or "").lower(), str(result or "").lower())
    if result not in RESULTS:
        raise PhoneDocError("result = fixed | not_fixed | skipped | cant")
    with _LOCK, session() as s:
        c = _get(s, tenant, case)
        if c.status != "open":
            return {"case": _view(c), "say": f"Yeh case pehle se '{STATUS_LABEL.get(c.status)}' hai."}
        steps = _j(c.steps, [])
        st = next((x for x in steps if x["id"] == step_id and x.get("result") is None), None) if step_id else _current(steps)
        if not st:
            st = _current(steps)
        if not st:
            raise PhoneDocError("Saare steps ho chuke.")
        if result == "fixed" and st.get("careful") and by not in ("owner", "hoola"):
            raise PhoneDocError("Yeh step sirf owner ki haan se.")
        st["result"], st["at"], st["note"] = result, now().isoformat(timespec="seconds"), (note or st.get("note", ""))[:200]
        if result in ("fixed", "not_fixed"):
            _learn(s, c.issue, st["id"], result == "fixed")
        _log(c, f"{st['title']}: {dict(fixed='theek hua', not_fixed='nahi hua', skipped='chhoda', cant='nahi ho paya')[result]}"
                + (f" ({note[:80]})" if note else ""), by)
        if result == "fixed":
            c.status, c.fixed_by = "resolved", st["id"]
        c.steps = json.dumps(steps, ensure_ascii=False)
        cid, status = c.id, c.status
        v = _view(c)
    if status == "resolved":
        say = f"Badhiya! '{st['title']}' se theek ho gaya. Case band; agli baar yahi step pehle aayega."
        _publish(tenant, "phonedoc_case", {"case": cid, "status": status}, conv)
        return {"case": v, "resolved": True, "say": say}
    if v["current"]:
        return {"case": v, "say": _step_say(v["current"], v["step_no"], v["total"])}
    out = escalate(tenant, cid, by=by, conv=conv)
    out["say"] = "Ghar ke saare upay ho gaye. " + out["say"]
    return out


def _maps(tenant: str, q: str) -> str:
    from .. import maps
    try:
        return maps.search_link(q, maps.where_am_i(tenant))
    except Exception:
        from urllib.parse import quote
        return "https://www.google.com/maps/search/" + quote(q)


def _mshop_on(tenant: str) -> bool:
    try:
        from ..mshop.service import MShopSettings
        with session() as s:
            r = s.get(MShopSettings, tenant)
            return bool(r and r.enabled)
    except Exception:
        return False


def _tell_shop(c: PhoneCase) -> str:
    tried = [st["title"] for st in _j(c.steps, []) if st.get("result") in ("not_fixed", "cant")]
    f = [x["text"] for x in _j(c.findings, [])][:3]
    return (f"{c.device or 'Phone'}: {playbook(c.issue)['label']}." + (f" Ghar par try kiya: {', '.join(tried)}." if tried else "")
            + (f" Phone check: {' '.join(f)}" if f else ""))


def escalate(tenant: str, case: str = "", kind: str = "", make_job: bool = False, phone: str = "", by: str = "owner",
             conv: str = "") -> dict[str, Any]:
    with _LOCK, session() as s:
        c = _get(s, tenant, case)
        spec = playbook(c.issue)
        kind = kind if kind in ("repair", "operator", "official") else spec["escalate"]
        brand = (c.device.split(" ")[0] if c.device else "").strip()
        esc: dict[str, Any] = {"kind": kind, "tell": _tell_shop(c), "links": [], "notes": []}
        if kind == "repair" or c.issue == "forgot_lock":
            esc["links"].append({"label": "Paas ki mobile repair dukaan", "url": _maps(tenant, "mobile repair shop")})
            if brand:
                esc["links"].append({"label": f"{brand} service centre", "url": _maps(tenant, f"{brand} service centre")})
            esc["notes"].append("Phone ka bill / dabba saath le jaiye (warranty mein ho to service centre muft karega).")
            esc["notes"].append("Dene se pehle backup le lijiye; screen lock ka password dukaan ko dena zaroori nahi, "
                                "zaroorat ho to apne saamne kholiye.")
            if c.issue == "forgot_lock":
                esc["notes"].append("Lock hatane ke liye service centre bill aur ID maangega: yahi sahi tareeka hai.")
            if c.issue == "water":
                esc["notes"].append("Aaj hi jaiye: paani wala phone jitni der rukta hai, utna nuksaan.")
        if kind == "operator":
            snap = latest_snapshot(tenant)[0] if not c.for_whom else {}
            opname = str(snap.get("operator") or "").lower()
            for k, line in OPERATOR_HELP.items():
                if k in opname:
                    esc["notes"].append(line)
            esc["notes"].append("198: kisi bhi operator ka shikayat number (network / service).")
            esc["notes"].append("SIM kharab ho to operator store se same number ki nayi SIM (ID ke saath).")
            esc["links"].append({"label": "Operator store paas mein", "url": _maps(tenant, (opname.split()[0] if opname else "mobile") + " store")})
        if kind == "official":
            if c.issue == "lost_stolen":
                esc["links"] += [{"label": "Find My Device (Google)", "url": "https://www.google.com/android/find"},
                                 {"label": "CEIR: phone block (Sanchar Saathi)", "url": "https://ceir.sancharsaathi.gov.in"}]
                esc["notes"] += ["Kram: SIM block > police complaint > nayi SIM > CEIR par IMEI block (bill + complaint copy + ID).",
                                 "IMEI phone ke dabbe ya bill par likha hota hai.",
                                 "CEIR form Hoola browser mein bhar sakta hai: OTP aap dengi, submit se pehle aapki haan."]
            else:
                esc["links"] += [{"label": "Cyber crime shikayat", "url": "https://cybercrime.gov.in"},
                                 {"label": "Chakshu: fraud call / SMS report", "url": "https://sancharsaathi.gov.in"}]
                esc["notes"] += ["Paise gaye hon to turant 1930 par call (jitni jaldi, utna paisa rukne ka mauka).",
                                 "Bank helpline par card / UPI block karwaiye.",
                                 "Kisi ko OTP, PIN ya screen share kabhi nahi."]
        c.status = "escalated"
        c.escalation = json.dumps(esc, ensure_ascii=False)
        _log(c, f"Aage bheja: {kind}", by)
        cid, device, text, for_whom = c.id, c.device, c.text, c.for_whom
        v = _view(c)
    if make_job and kind == "repair" and _mshop_on(tenant):
        from ..mshop import service as M
        note, job_id = "", ""
        try:
            r = M.new_job(tenant, name=for_whom or "Graahak", phone=phone, brand=brand, model=" ".join(device.split(" ")[1:]),
                          problem=f"{spec['label']}: {text}"[:500], faults=[spec.get("fault", "other")], by=by, conv=conv)
            if r.get("saved"):
                job_id, note = r["job"]["id"], f"Aapki dukaan mein job {r['job']['number']} ban gaya."
            else:
                note = "Dukaan ka job nahi bana: " + r.get("say", "")
        except Exception as e:  # mshop rule problems etc.
            note = f"Dukaan ka job nahi bana: {e}"
        esc["notes"].append(note)
        with _LOCK, session() as s:
            c = s.get(PhoneCase, cid)
            c.mshop_job = job_id or c.mshop_job
            c.escalation = json.dumps(esc, ensure_ascii=False)
            _log(c, note, by)
            v = _view(c)
    say = {"repair": "Ab yeh dukaan / service centre ka kaam hai. Paas ki dukaan aur service centre card par hai; "
                     "unhe yeh batana: " + esc["tell"],
           "operator": "Ab operator se baat karni padegi: " + " ".join(esc["notes"][:2]),
           "official": " ".join(esc["notes"][:2])}[kind]
    _publish(tenant, "phonedoc_case", {"case": v["id"], "status": v["status"]}, conv)
    return {"case": v, "escalation": esc, "say": say}


def close(tenant: str, case: str, by: str = "owner") -> dict[str, Any]:
    with _LOCK, session() as s:
        c = _get(s, tenant, case)
        c.status = "closed"
        _log(c, "Band kiya", by)
        return {"case": _view(c), "say": "Case band."}


def get_case(tenant: str, case: str = "") -> dict[str, Any]:
    with session() as s:
        return _view(_get(s, tenant, case))


def cases(tenant: str, status: str = "", limit: int = 30) -> list[dict[str, Any]]:
    with session() as s:
        q = select(PhoneCase).where(PhoneCase.tenant_id == tenant)
        if status:
            q = q.where(PhoneCase.status == status)
        rows = s.scalars(q.order_by(PhoneCase.updated_at.desc()).limit(max(1, min(int(limit), 100)))).all()
        return [{k: v for k, v in _view(r).items() if k not in ("steps", "log")} for r in rows]


def learned(issue: str) -> list[dict]:
    with session() as s:
        st = _stats(s, issue)
    out = [{"step": k.split(":", 1)[1], "tried": t, "fixed": f} for k, (t, f) in st.items()]
    return sorted(out, key=lambda x: (-x["fixed"], x["tried"]))
