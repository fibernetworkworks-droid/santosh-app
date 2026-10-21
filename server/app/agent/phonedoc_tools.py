"""v0.90 Phone Doctor tool: a phone problem from "kya dikkat hai" to fixed, one step at a time, or to the right shop /
operator / official help. Reads the phone's own state through the Hoola app (nothing personal: settings + battery +
storage + network + the most-used apps' names). Never bypasses a lock, never changes an IMEI, never asks for a password."""
from __future__ import annotations

import asyncio
from typing import Any

from ..events import bus
from .tools import Ctx, ToolError

PHONEDOC_TOOLS = [
    {"name": "phone_doctor", "description": (
        "Fix a phone problem END TO END (her phone, or a customer's / family member's). Use whenever she says her phone "
        "is slow / hangs, battery drains, heats, won't charge, no network / data / Wi-Fi, calls don't ring, no sound / mic, "
        "late notifications, app crashes, storage full, touch / screen broken, fell in water, won't turn on, OTP not "
        "coming, Bluetooth, camera, GPS, phone lost / stolen, forgot lock, hacked / fraud. "
        "action=start: text (her words), issue (optional: slow, battery_drain, heating, not_charging, no_network, "
        "mobile_data, wifi, calls_not_ringing, sound_mic, notifications_late, app_crash, storage_full, touch, screen_broken, "
        "water, wont_turn_on, otp_not_coming, bluetooth, camera, lost_stolen, forgot_lock, hacked_fraud, gps, other), "
        "for_whom (empty = her own phone: the phone checks itself first), device, app_package (for one app crashing). "
        "Returns findings from the phone + step 1. Give ONE step at a time in simple words, the settings screen opens on "
        "her phone by itself; then ask 'theek hua?'. "
        "action=step: case, step_id, result fixed | not_fixed | skipped | cant, note -> the next step (or escalation when "
        "they run out). Steps marked careful (factory reset, network reset, reinstall) only after she clearly says haan. "
        "action=check: read the phone again now. action=recheck: case: did the last step change what the phone says. "
        "action=open: setting (key), package, url: open that screen on her phone again. "
        "action=escalate: case, kind repair | operator | official, make_job (she runs the mobile shop: log a repair job), "
        "phone (customer's). action=close: case. action=cases: status. action=case: case. "
        "Lost / stolen: block SIM, police complaint, CEIR (Sanchar Saathi) block; money lost: 1930 at once. "
        "NEVER bypass FRP / pattern / iCloud locks, never change an IMEI, never ask for a password / PIN / OTP."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["start", "step", "check", "recheck", "open", "escalate", "close", "cases", "case"]},
         "text": {"type": "string"}, "issue": {"type": "string"}, "for_whom": {"type": "string"}, "device": {"type": "string"},
         "app_package": {"type": "string"}, "case": {"type": "string"}, "step_id": {"type": "string"},
         "result": {"type": "string", "enum": ["fixed", "not_fixed", "skipped", "cant"]}, "note": {"type": "string"},
         "setting": {"type": "string"}, "package": {"type": "string"}, "url": {"type": "string"},
         "kind": {"type": "string", "enum": ["repair", "operator", "official"]}, "make_job": {"type": "boolean"},
         "phone": {"type": "string"}, "status": {"type": "string"}},
         "required": ["action"]}},
]
PHONEDOC_LABELS = {"phone_doctor": "Phone ki dikkat theek kar raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


async def _fresh(ctx: Ctx, max_age: int = 600, wait_s: float = 8.0) -> dict:
    """The phone's latest self-check; asks the app for a new one when it's old and waits a few seconds."""
    from ..phonedoc import service as P
    snap, _ = await asyncio.to_thread(P.latest_snapshot, ctx.tenant_id, max_age)
    if snap:
        return snap
    try:
        bus.publish(ctx.conversation_id, "phonedoc_check", {})
    except Exception:
        return {}
    loop = asyncio.get_running_loop()
    end = loop.time() + wait_s
    while loop.time() < end:
        await asyncio.sleep(0.5)
        snap, _ = await asyncio.to_thread(P.latest_snapshot, ctx.tenant_id, 30)
        if snap:
            return snap
    return {}


def _open(ctx: Ctx, st: dict | None) -> None:
    if not st or not (st.get("setting") or st.get("url")):
        return
    try:
        bus.publish(ctx.conversation_id, "phonedoc_open", {"key": st.get("setting") or "", "package": st.get("pkg") or "",
                                                          "url": st.get("url") or "", "label": st.get("title") or ""})
    except Exception:
        pass


async def phone_doctor(ctx: Ctx, action, **a: Any):
    from ..phonedoc import service as P
    t, conv, action = ctx.tenant_id, ctx.conversation_id, str(action)
    by = "owner" if _owner(ctx) else (getattr(ctx, "actor", "") or "staff")
    try:
        if action == "start":
            snap = {} if _s(a.get("for_whom")).strip() else await _fresh(ctx, 3600)
            out = await asyncio.to_thread(P.start, t, _s(a.get("text")), _s(a.get("issue")), _s(a.get("for_whom")),
                                          _s(a.get("device")), _s(a.get("app_package")), snap or None, by, conv)
            if out.get("started") and not _s(a.get("for_whom")).strip():
                _open(ctx, out["case"]["current"])
            return out
        if action == "step":
            out = await asyncio.to_thread(P.step, t, _s(a.get("case")), _s(a.get("step_id")), _s(a.get("result")) or "not_fixed",
                                          _s(a.get("note")), by, conv)
            case = out.get("case") or {}
            if case.get("status") == "open" and not case.get("for_whom"):
                _open(ctx, case.get("current"))
            return out
        if action == "check":
            snap = await _fresh(ctx, 60)
            if not snap:
                return {"snapshot": {}, "say": "Phone ki jaanch nahi aayi: Hoola app khol ke rakhiye (Android par hi chalti hai)."}
            from ..phonedoc.playbooks import findings
            f = findings(snap)
            return {"snapshot": snap, "findings": f, "say": P.summary(snap) + (". " + " ".join(x["text"] for x in f[:5]) if f else ". Sab theek dikh raha hai.")}
        if action == "recheck":
            snap = await _fresh(ctx, 60)
            return await asyncio.to_thread(P.recheck, t, _s(a.get("case")), snap or None)
        if action == "open":
            st = {"setting": _s(a.get("setting")), "pkg": _s(a.get("package")), "url": _s(a.get("url")), "title": ""}
            if not (st["setting"] or st["url"]):
                raise ToolError("setting ya url chahiye.")
            _open(ctx, st)
            return {"say": "Phone par screen khol di."}
        if action == "escalate":
            return await asyncio.to_thread(P.escalate, t, _s(a.get("case")), _s(a.get("kind")), bool(a.get("make_job")),
                                           _s(a.get("phone")), by, conv)
        if action == "close":
            return await asyncio.to_thread(P.close, t, _s(a.get("case")), by)
        if action == "cases":
            return {"cases": await asyncio.to_thread(P.cases, t, _s(a.get("status")), 20)}
        if action == "case":
            return await asyncio.to_thread(P.get_case, t, _s(a.get("case")))
    except P.PhoneDocError as e:
        raise ToolError(str(e))
    raise ToolError("action = start | step | check | recheck | open | escalate | close | cases | case")


PHONEDOC_HANDLERS = {"phone_doctor": phone_doctor}
