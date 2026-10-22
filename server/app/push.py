"""Push notifications through Firebase Cloud Messaging (HTTP v1), Google Play's way to reach a phone whose app is
closed or whose screen is locked. Every Santosh event that matters to the user (a reply, an approval card, a
finished page or file, a phone action like an alarm) is also sent as a high-priority data push; the phone shows it
only when the app isn't on screen, so there are no duplicates. No message content is stored at Google beyond
delivery; device actions are re-checked by the phone (claimed once, ignored when old)."""
from __future__ import annotations

import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx
from sqlalchemy import select

from .config import get_settings
from .db import Conversation, PushToken, now, session

log = logging.getLogger("santosh.push")

SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="push")
_lock = threading.Lock()
_creds = None
_project = ""
_tenant_of: dict[str, str] = {}


def configured() -> bool:
    return bool(get_settings().fcm_service_account_file)


def _credentials():
    """(credentials, project_id), cached; refreshed when the access token is near expiry."""
    global _creds, _project
    with _lock:
        if _creds is None:
            from google.oauth2 import service_account
            path = get_settings().fcm_service_account_file
            with open(path, encoding="utf-8") as f:
                info = json.load(f)
            _project = info["project_id"]
            _creds = service_account.Credentials.from_service_account_info(info, scopes=[SCOPE])
        if not _creds.valid or (_creds.expiry and (_creds.expiry.timestamp() - time.time()) < 120):
            import google.auth.transport.requests
            _creds.refresh(google.auth.transport.requests.Request())
        return _creds, _project


def reset() -> None:   # tests / config change
    global _creds, _project
    with _lock:
        _creds, _project = None, ""
    _tenant_of.clear()


def register(tenant: str, token: str, platform: str = "android") -> None:
    token = (token or "").strip()
    if not token or len(token) > 300:
        raise ValueError("bad token")
    with session() as s:
        row = s.get(PushToken, token)
        if row is None:
            s.add(PushToken(token=token, tenant_id=tenant, platform=platform[:16]))
        else:
            row.tenant_id, row.platform = tenant, platform[:16]


def unregister(tenant: str, token: str) -> None:
    with session() as s:
        row = s.get(PushToken, token)
        if row is not None and row.tenant_id == tenant:
            s.delete(row)


def _tokens(tenant: str) -> list[str]:
    with session() as s:
        return [t.token for t in s.scalars(select(PushToken).where(PushToken.tenant_id == tenant)).all()]


def _tenant(conversation_id: str) -> str:
    t = _tenant_of.get(conversation_id)
    if t is None:
        with session() as s:
            c = s.get(Conversation, conversation_id)
            t = c.tenant_id if c else ""
        if t:
            _tenant_of[conversation_id] = t
    return t


def render(kind: str, p: dict[str, Any], name: str = "Santosh") -> tuple[str, str] | None:
    """(title, body) the phone shows for this event, or None when it doesn't need a push."""
    if kind == "message":
        if p.get("role") != "assistant":
            return None
        text = str(p.get("text") or "").strip()
        return (name, text[:400]) if text else None
    if kind == "bazar_approval":
        if p.get("status") not in (None, "", "pending") or p.get("result"):
            return None
        return ("Approve karein", f"{p.get('title', '')} {p.get('amount', '')}".strip())
    if kind == "artifact":
        return (f"{name} ne banaya", str(p.get("title") or "Page taiyaar hai")) if p.get("status") == "ready" else None
    if kind == "pc_file":
        return (f"{name} ne PDF banaya" if p.get("source") == "bazar" else "PC se file aayi", str(p.get("name") or ""))
    if kind == "email_draft":
        return ("Email draft taiyaar", str(p.get("subject") or "Dekh kar bhejiye"))
    if kind == "hoola_knock" and not p.get("quiet") and p.get("status") in (None, "pending"):
        b = p.get("body") or {}
        said = str(b.get("text") or "")[:200] or (f"📎 {b.get('name')}" if b.get("name") else "")
        return (f"{p.get('from', 'Hoola')}", f"{p.get('what', '')}: {said}".strip(": "))
    if kind == "hoola_connect" and p.get("status") == "incoming" and not p.get("quiet"):
        return ("Connect request", f"{p.get('label', '')} judna chahte hain")
    if kind == "hoola_msg" and not p.get("quiet") and not p.get("fyi"):
        return (f"{name}: {p.get('from', '')}", str(p.get("text") or "")[:300])
    if kind == "employee_ask" and p.get("status") == "pending":
        return ("Aapki haan chahiye", f"{p.get('what', '')} · {p.get('who', '')}: {p.get('detail', '')}"[:300])
    if kind == "darzi_quote" and p.get("status") == "pending":
        return (f"{name}: naya daam, aapki haan?", f"{p.get('customer', '')} · {p.get('label', '')}: {p.get('price') or 'daam bataiye'}"[:300])
    if kind == "chai_plan":
        return (f"{name}: kal ka saamaan", str(p.get("say") or "")[:300])
    if kind == "darzi_day":
        return (f"{name}: aaj ki silai", str(p.get("text") or "")[:300])
    if kind == "office_spend" and p.get("status") == "pending":
        return (f"{name}: kharcha, aapki haan?", f"{p.get('number', '')} {p.get('title', '')}: {p.get('amount') or 'rakam bataiye'}"[:300])
    if kind == "mshop_bill" and p.get("status") == "pending":
        return (f"{name}: bill par aapki haan?", f"{p.get('number', '')} {p.get('customer', '')} · {p.get('device', '')}: {p.get('total', '')}"[:300])
    if kind == "niryat_pi":
        return (f"{name}: PI taiyaar", f"{p.get('buyer', '')}: {p.get('currency', '')} {p.get('total', 0):,.2f}; bhejne se pehle aapki haan")
    if kind == "niryat_day":
        return (f"{name}: export", str(p.get("text") or "")[:300])
    if kind == "thok_order":
        return (f"{name}: order, bill banaun?", f"{p.get('party', '')}: Rs {p.get('total', 0):,.0f}" + (" (credit dekhiye)" if p.get("level") != "ok" else ""))
    if kind in ("thok_alert", "thok_day"):
        return (f"{name}: thok", str(p.get("text") or "")[:300])
    if kind in ("seo_week", "seo_alert"):
        return (f"{name}: SEO", str(p.get("text") or "")[:300])
    if kind == "seo_draft":
        return (f"{name}: SEO draft", f"{p.get('title', '')}: final karne ke liye aapki haan")
    if kind == "ins_day":
        return (f"{name}: bima", str(p.get("text") or "")[:300])
    if kind == "ins_advice":
        return (f"{name}: salah taiyaar", f"{p.get('client', '')} ke liye options; bhejne se pehle aapki haan")
    if kind == "ads_change" and not p.get("decided"):
        return (f"{name}: ads mein badlav ki haan?", str(p.get("say") or "")[:300])
    if kind == "ads_report" and p.get("kind") in ("daily", "weekly"):
        return (f"{name}: ads ka hisaab", str(p.get("say") or "")[:300])
    if kind == "kalam_publish" and not p.get("decided"):
        return (f"{name}: publish karne ki haan?", f"{p.get('number', '')} {p.get('kind_label', '')}: {p.get('title', '')} · {p.get('where_label', '')}"[:300])
    if kind == "hoola_deal" and p.get("card") in ("quote", "confirm", "accept", "ready", "pack", "pay", "money", "receipt",
                                                   "check", "dispute", "resolve", "cancel_req"):
        head = {"quote": "list aayi, quote bhejun?", "confirm": "quote aaya, aapki haan?", "accept": "order aaya, pakka karein?",
                "ready": "parcel taiyaar", "pack": "order pakka, pack karna hai", "pay": "payment card aaya",
                "money": "graahak ne paisa bheja?", "receipt": "rasid aayi", "check": "sab sahi mila?",
                "dispute": "shikayat aayi", "resolve": "shikayat ka jawab", "cancel_req": "cancel ki request"}[p["card"]]
        return (f"{name}: {head}", f"{p.get('with', '')} · {p.get('say', '')}"[:300])
    if kind == "hoola_khata" and p.get("card") in ("pay", "money", "receipt", "due"):
        head = {"pay": "khata ka payment card", "money": "khata ka paisa bheja?", "receipt": "khata ki rasid",
                "due": "khata ki taareekh"}[p["card"]]
        return (f"{name}: {head}", f"{p.get('with', '')} · {p.get('say', '')}"[:300])
    if kind == "hoola_pick" and p.get("card") in ("task", "ready"):
        return (f"{name}: {'pick list' if p.get('card') == 'task' else 'parcel taiyaar'}", str(p.get("say") or "")[:300])
    if kind in ("sheet_milaan", "doc_edit") and p.get("status") == "ready":
        head = "Sheet Milaan taiyaar" if kind == "sheet_milaan" else "file mein badlav taiyaar"
        return (f"{name}: {head}", f"{p.get('name', '')}: {p.get('say', '')}"[:300])
    if kind == "tele_day":
        return (f"{name}: aaj ki call list", str(p.get("text") or "")[:300])
    if kind == "audit_update":
        return (f"{name}: audit jaanch poori", f"{p.get('findings', 0)} baatein dekhni hain")
    if kind == "fin_alert":
        return (f"{name}: paisa", str(p.get("text") or "")[:300])
    if kind == "payroll_run" and p.get("status") == "ready":
        return (f"{name}: salary par aapki haan?", "Payroll taiyaar hai, dekhkar haan dijiye")
    if kind == "payroll_day":
        return (f"{name}: payroll", str(p.get("text") or "")[:300])
    if kind == "gst_day":
        return (f"{name}: aaj ka GST", str(p.get("text") or "")[:300])
    if kind == "gst_return" and p.get("status") == "ready":
        return (f"{name}: return par aapki haan?", "GST return taiyaar hai, dekhkar haan dijiye")
    if kind == "mshop_day":
        return (f"{name}: aaj ki dukaan", str(p.get("text") or "")[:300])
    if kind == "office_day":
        return (f"{name}: aaj ka office", str(p.get("text") or "")[:300])
    if kind == "office_note":
        return (f"{name}: hafte ka office note", "Note taiyaar hai, dekhiye")
    if kind == "lekhak_sign" and p.get("status") == "waiting_sign":
        return (f"{name}: letter sign karna hai?", f"{p.get('number', '')} {p.get('title', '')}: final dekhkar Haan dabaiye"[:300])
    if kind == "ask_form" and p.get("status") == "pending":
        return (f"{name}: ek form bhariye", f"{p.get('title', '')}: {len(p.get('fields') or [])} sawaal, ek baar mein"[:300])
    if kind == "google_reconnect":
        return (f"{name}: Google dobara jodiye", str(p.get("text") or "")[:300])
    if kind == "studio_approval" and p.get("status") == "pending":
        return (f"{name}: video ka kharcha ₹{p.get('inr', '')}", f"{p.get('project', '')}: {p.get('shots', 0)} shot, Haan dabaiye tabhi banega"[:300])
    if kind == "operator_ask" and p.get("status") == "pending":
        title = {"otp": "OTP chahiye", "captcha": "CAPTCHA bhariye", "secret": "Aap khud bhariye", "payment": "Payment aap kijiye",
                 "approve": "Aapki haan chahiye"}.get(p.get("kind", ""), "Aapse sawaal")
        return (f"{name}: {title}", f"{p.get('site', '')}: {p.get('reason', '')}"[:300])
    if kind == "biz_inbox" and p.get("handover"):
        c = p.get("contact") or {}
        return ("WhatsApp: aapki zaroorat hai", f"{c.get('name', '')}: {p.get('reason', '')}"[:300])
    if kind == "biz_inbox" and (p.get("message") or {}).get("direction") == "in" and (p.get("contact") or {}).get("human"):
        c = p.get("contact") or {}
        return (f"WhatsApp: {c.get('name', '')}", str((p.get('message') or {}).get('text') or "")[:300])
    if kind == "employee_report":
        return (f"{name} ki aaj ki report", str(p.get("text") or "")[:600])
    if kind == "bazar_open":
        msg = str(p.get("message") or "").strip()
        return (name, msg[:300]) if msg else None
    return None


def build(token: str, ev: dict[str, Any], name: str = "Santosh") -> dict[str, Any] | None:
    kind, p = ev["kind"], ev.get("payload") or {}
    data: dict[str, str] = {"kind": kind, "event_id": str(ev.get("id", "")), "at": str(ev.get("at", ""))}
    ttl = "3600s"
    if kind in RAW_KINDS:
        data["payload"] = json.dumps(p, ensure_ascii=False)[:3000]
        ttl = "600s"
    else:
        shown = render(kind, p, name)
        if shown is None:
            return None
        data["title"], data["body"] = shown[0][:80], shown[1][:900]
    return {"message": {"token": token, "data": data, "android": {"priority": "HIGH", "ttl": ttl}}}


def _avatar_name(tenant: str) -> str:
    from .avatar.service import persona
    return persona(tenant)[0]


def _send(tenant: str, ev: dict[str, Any]) -> int:
    tokens = _tokens(tenant)
    if not tokens:
        return 0
    try:
        creds, project = _credentials()
    except Exception:
        log.exception("FCM credentials not usable (FCM_SERVICE_ACCOUNT_FILE)")
        return 0
    url = f"https://fcm.googleapis.com/v1/projects/{project}/messages:send"
    sent = 0
    with httpx.Client(timeout=15) as c:
        for tok in tokens:
            body = build(tok, ev, _avatar_name(tenant))
            if body is None:
                return 0
            try:
                r = c.post(url, json=body, headers={"Authorization": f"Bearer {creds.token}"})
            except httpx.HTTPError as e:
                log.warning("FCM send failed: %s", e)
                continue
            if r.status_code == 200:
                sent += 1
                with session() as s:
                    row = s.get(PushToken, tok)
                    if row:
                        row.last_ok = now()
            elif r.status_code in (400, 404) and ("UNREGISTERED" in r.text or "registration-token-not-registered" in r.text
                                                  or "INVALID_ARGUMENT" in r.text):
                with session() as s:   # the app was uninstalled or the token rotated
                    row = s.get(PushToken, tok)
                    if row:
                        s.delete(row)
            else:
                log.warning("FCM %s: %s", r.status_code, r.text[:300])
    return sent


PUSH_KINDS = {"message", "bazar_approval", "artifact", "pc_file", "email_draft", "bazar_open", "device_action",
              "home_device", "bt_request", "employee_ask", "employee_report", "biz_inbox", "operator_ask", "studio_approval", "google_reconnect", "darzi_quote", "darzi_day", "chai_plan", "office_spend", "office_day", "office_note", "lekhak_sign", "mshop_bill", "mshop_day", "gst_day", "gst_return", "payroll_run", "payroll_day", "fin_alert", "audit_update", "ask_form", "ins_day", "ins_advice", "tele_day", "kalam_publish", "hoola_deal", "seo_week", "seo_alert", "seo_draft", "hoola_pick", "hoola_khata", "thok_order", "thok_alert", "thok_day", "sheet_milaan", "doc_edit", "niryat_pi", "niryat_day", "ads_change", "ads_report"}
RAW_KINDS = {"device_action", "home_device", "bt_request"}   # the phone runs these itself; no notification text


def on_event(conversation_id: str, ev: dict[str, Any]) -> None:
    """Called for every published event; sends the push in the background (never slows the caller)."""
    if ev.get("kind") not in PUSH_KINDS or not configured():
        return
    if ev["kind"] not in RAW_KINDS and build("x", ev) is None:
        return
    tenant = _tenant(conversation_id)
    if not tenant:
        return
    try:
        _pool.submit(_send, tenant, ev)
    except RuntimeError:
        pass
