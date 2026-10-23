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
    if kind == "photo_made":
        return (f"{name} ne photo {'badli' if p.get('edit') else 'banayi'}", str(p.get("prompt") or "")[:120])
    if kind == "pg_write":
        if p.get("status") != "pending" or p.get("again"):
            return None
        return (f"{name}: database badlav ke liye haan chahiye", str(p.get("say") or "")[:200])
    if kind == "blender3d":
        if not p.get("push") or p.get("status") != "done":
            return None
        return (f"{name} ne 3D banaya", str(p.get("say") or p.get("title") or "")[:200])
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
    if kind == "theka_bill":
        return (f"{name}: {p.get('label', 'RA bill')} taiyaar", f"{p.get('project', '')}: haath mein ~Rs {p.get('net', 0):,.0f}; department ko dene se pehle aapki haan")
    if kind == "theka_letter":
        return (f"{name}: chitthi ka draft", f"{p.get('project', '')}: {p.get('title', '')}")
    if kind == "theka_day":
        return (f"{name}: theka", str(p.get("text") or "")[:300])
    if kind == "fr_statement":
        return (f"{name}: royalty statement", f"{p.get('brand', '')} {p.get('month', '')}: dena Rs {p.get('payable', 0):,.0f}; report bhejne se pehle aapki haan")
    if kind == "fr_day":
        return (f"{name}: outlets", str(p.get("text") or "")[:300])
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
    if kind == "brand_approval":
        dd = p.get("design") or {}
        return (f"{name}: poster final karein?", f"{dd.get('number', '')} {dd.get('title', '')}: proof dekh kar haan dijiye"[:300])
    if kind == "brand_idea":
        return (f"{name}: tyohar ka poster?", str(p.get("say") or "")[:300])
    # v0.133 Seva suite
    if kind == "seva_exception" and p.get("status") in (None, "", "pending", "waiting"):
        return (f"{name}: aapki haan chahiye: {p.get('kind_label', 'arzi')}", str(p.get("say") or "")[:300])
    if kind == "seva_sla" and p.get("breach"):
        return (f"{name}: shikayat ka samay: {p.get('ticket', '')}", str(p.get("text") or "")[:300])
    if kind == "seva_ticket" and p.get("event") == "new" and p.get("priority") == "urgent":
        return (f"{name}: nayi shikayat {p.get('number', '')}", f"{p.get('customer', '')}: {p.get('text', '')}"[:300])
    if kind == "seva_day":
        return (f"{name}: seva aaj", str(p.get("text") or "")[:300])
    if kind == "helpdesk_change" and (p.get("change") or {}).get("status") in (None, "", "waiting"):
        return (f"{name}: IT: aapki haan chahiye", str(p.get("say") or "")[:300])
    if kind == "helpdesk_alert":
        return (f"{name}: IT / suraksha", str(p.get("say") or "")[:300])
    if kind == "helpdesk_escalate":
        return (f"{name}: technician ke liye message taiyaar", str(p.get("say") or "")[:300])
    if kind == "helpdesk_day":
        return (f"{name}: aaj ka IT note", str(p.get("say") or "")[:300])
    if kind == "shikayat_comp" and not p.get("event"):
        c = p.get("comp") or {}
        sh = p.get("show") or {}
        return (f"{name}: muavze ki haan chahiye", f"{sh.get('case') or c.get('number', '')}: {c.get('kind_label', '')} {c.get('amount_text', '')}".strip()[:300])
    if kind == "shikayat_case" and p.get("event") == "new":
        c = p.get("case") or {}
        causes = c.get("cause_labels") or []
        causes = ", ".join(causes) if isinstance(causes, list) else str(causes)
        return (f"{name}: nayi shikayat {c.get('number', '')}", f"{c.get('customer', '')} · {causes}"[:300])
    if kind in ("shikayat_alert", "shikayat_day"):
        return (f"{name}: {'shikayat ki samay-seema' if kind == 'shikayat_alert' else 'aaj ki shikayatein'}", str(p.get("text") or "")[:300])
    if kind == "aftersales_charge" and p.get("status") in ("pending", "needs_price"):
        tot = p.get("total") or 0
        body = f"{p.get('number', '')} {p.get('customer', '')}: " + (f"Rs {tot:,.0f} graahak se lena hai?" if p.get("status") == "pending"
                                                                     else "daam likhiye")
        return (f"{name}: charge par aapki haan", body[:300])
    if kind == "aftersales_reminders" and p.get("count"):
        return (f"{name}: service reminder", f"{p.get('count')} reminder draft bhejne ke liye taiyaar")
    if kind == "aftersales_visit" and p.get("status") in (None, "booked"):
        return (f"{name}: visit book", f"{p.get('number', '')} {p.get('customer', '')}: {p.get('when', '')}, {p.get('tech', '')}"[:300])
    if kind == "aftersales_day":
        return (f"{name}: after-sales aaj", str(p.get("text") or "")[:300])
    if kind == "feedback_reply" and p.get("status") in (None, "draft"):
        it = p.get("item") or {}
        stars = f" {it.get('stars')}*" if it.get("stars") else ""
        return (f"{name}: review ka jawab", f"Jawab ka draft taiyaar: {it.get('source_label', '')}{stars} - Haan dabaiye to jaayega"[:300])
    if kind in ("feedback_alert", "feedback_report"):
        return (f"{name}: {'graahak ki shikayat' if kind == 'feedback_alert' else 'feedback report'}", str(p.get("text") or "")[:300])
    if kind == "wapsi_return" and p.get("event") == "new":
        r = p.get("return") or {}
        cust = r.get("customer") or {}
        cust = cust.get("name", "") if isinstance(cust, dict) else str(cust)
        verdict = {"approve": "return theek lagta hai", "ask_more": "aur saboot chahiye", "reject_suggest": "niyam ke bahar lagta hai"}.get(
            str((r.get("check") or {}).get("verdict") or ""), "dekhiye")
        return (f"{name}: return {r.get('number', '')}", f"{cust}: {r.get('reason_label', '')} - {verdict}"[:300])
    if kind == "wapsi_refund" and (p.get("refund") or {}).get("status") == "waiting" and not p.get("event"):
        f = p.get("refund") or {}
        return (f"{name}: refund ki haan chahiye", f"{p.get('return_number', '')} {p.get('customer', '')}: Rs {f.get('amount') or 0:,.0f} - card par haan (fingerprint)"[:300])
    if kind == "wapsi_day":
        return (f"{name}: wapsi", str(p.get("text") or "")[:300])
    if kind == "samudaay_alert" and p.get("status") in (None, "", "open", "new"):
        return (f"{name}: group mein {p.get('kind', 'alert')}", str(p.get("title") or "")[:300])
    if kind == "samudaay_action" and p.get("status") in (None, "", "pending", "waiting"):
        return (f"{name}: aapki haan chahiye", f"{p.get('label', '')}: {p.get('member', '')} ({p.get('community', '')})"[:300])
    if kind == "samudaay_question":
        return (f"{name}: group mein sawal", f"{p.get('member', '')}: {p.get('text', '')}"[:300])
    if kind == "samudaay_join":
        return (f"{name}: join request", f"{p.get('name', '')} {p.get('community', '')} mein judna chahte hain"[:300])
    if kind == "samudaay_template" and p.get("status") in (None, "", "draft", "waiting"):
        return (f"{name}: welcome message", "Dekh kar 'Haan' dabaiye, tabhi naye logon ko jayega")
    if kind == "samudaay_week":
        return (f"{name}: group ki hafte ki sehat", str(p.get("say") or "")[:300])
    if kind == "callcentre_script" and p.get("status") == "waiting":
        return (f"{name}: call centre script v{p.get('version', '')}", f"Line par chalane ke liye Haan chahiye: {p.get('say', '')}"[:300])
    if kind == "callcentre_message":
        return (f"{name}: call se message", str(p.get("say") or "")[:300])
    if kind == "callcentre_call" and (p.get("outcome") in ("transferred", "message", "complaint", "failed", "callback") or p.get("flags")):
        return (f"{name}: call: {p.get('caller_masked', '')}", str(p.get("summary") or "")[:300])
    # v0.137 Tech suite
    _say = str(p.get("say") or "")[:300]
    if kind == "devsahayak_task":
        t = p.get("task") or {}
        if t.get("status") in ("checks_failed", "refused", "explained") or (t.get("number") and _say.startswith(str(t.get("number"))) and "CI" in _say):
            return (f"{name}: Developer: {t.get('number', '')}", _say)
        return None
    _tech = {"devsahayak_merge": "Merge ke liye aapki haan", "devsahayak_deploy": "Deploy ke liye aapki haan",
             "devsahayak_push": "PR kholne ki haan chahiye", "devsahayak_review": "Code review taiyaar",
             "qa_bug": "Naya bug mila", "qa_export": "GitHub issue: aapki haan chahiye",
             "itadmin_change": "IT: aapki haan chahiye", "itadmin_renewal": "Renewal aa raha hai",
             "itadmin_checklist": "Joiner / leaver checklist", "itadmin_review": "Access review ka samay",
             "itadmin_day": "Aaj ka IT admin note", "ispnoc_change": "Network: aapki haan chahiye", "ispnoc_alert": "Network alert",
             "ispnoc_day": "Aaj ka network", "cyber_action": "Suraksha: aapki haan chahiye", "cyber_alerts": "Zaroori suraksha alert",
             "cyber_incident": "Cyber incident khula", "cyber_advisory": "Software mein khatra", "cyber_day": "Aaj ki suraksha",
             "devops_build": "Build fail hua", "devops_day": "Aaj ka DevOps note", "docwriter_publish": "Docs public karein?",
             "docwriter_sync": "Product badla: docs update", "appreview_handoff": "App review: aapki haan chahiye",
             "appreview_alert": "App review", "product_publish": "Bahar bhejna hai: aapki haan", "product_day": "Aaj ka product note",
             "product_backlog": "Nayi dikkatein backlog mein"}
    if kind in _tech:
        return (f"{name}: {_tech[kind]}", _say)
    if kind == "qa_run":
        r = p.get("run") or {}
        if (r.get("counts") or {}).get("fail") or r.get("status") == "failed":
            return (f"{name}: Test ho gaya", _say)
        return None
    if kind == "ispnoc_fault":
        return (f"{name}: Network mein dikkat", _say) if p.get("new") else None
    if kind == "devops_deploy":
        return (f"{name}: Deploy: aapki haan chahiye", _say) if p.get("push") else None
    if kind == "devops_alert":
        return (f"{name}: DevOps alert", _say) if p.get("push") else None
    # v0.139 Safar suite
    if kind == "customs_filing":
        return (f"{name}: Import filing: aapki haan chahiye", _say) if (p.get("filing") or {}).get("status") == "waiting" else None
    if kind == "travel_booking":
        return (f"{name}: Yatra: booking ki haan chahiye", _say) if p.get("status") == "waiting" else None
    if kind == "warehouse_adjust":
        return (f"{name}: Godown: stock badlav aapki haan ka", _say) if (p.get("adjust") or {}).get("status") == "waiting" else None
    if kind == "courier_card":
        c = p.get("card") or {}
        if c.get("status") != "waiting":
            return None
        b = c.get("body") or {}
        return (f"{name}: Courier: aapki haan chahiye", f"{b.get('title', '')} - {b.get('say', '')}"[:300])
    if kind == "courier_parcel":
        if p.get("event") not in ("exception", "rto", "delivered", "out_for_delivery"):
            return None
        pc = p.get("parcel") or {}
        return (f"{name}: Parcel: {pc.get('number', '')}", f"{pc.get('status_label', '')}: {pc.get('raw', '')}"[:300])
    if kind == "logistics_alert":
        return (f"{name}: Logistics · {p.get('number', '')}", str(p.get("text") or "")[:300])
    _safar_text = {"courier_day": "Aaj ka courier note", "logistics_day": "Aaj ka dispatch"}
    if kind in _safar_text:
        return (f"{name}: {_safar_text[kind]}", str(p.get("text") or "")[:300])
    _safar = {"customs_alert": "Import / customs", "customs_day": "Aaj ka import desk", "travel_quote": "Graahak ka quote taiyaar",
              "travel_reminder": "Yatra yaad", "travel_day": "Aaj ki yatra", "warehouse_day": "Aaj ka godown note",
              "fleet_spend": "Fleet: kharche ki haan chahiye", "fleet_alert": "Fleet", "fleet_day": "Aaj ka fleet note",
              "drivers_alert": "Driver ke kaagaz", "drivers_plan": "Driver duty: bhejne ke liye taiyaar", "drivers_day": "Aaj ke driver",
              "logistics_ewb": "E-way bill: aapka tap chahiye"}
    if kind in _safar:
        return (f"{name}: {_safar[kind]}", _say)
    # v0.144 Makaan suite: cards push only while they wait for her (the same card is re-published when decided)
    _makaan_wait = {"propagent_card": ("card", "Property: aapki haan chahiye"),
                    "rentdesk_approval": ("approval", "Kiraya: aapki haan chahiye"),
                    "sitesup_indent": ("indent", "Site: indent aapki haan chahiye"), "sitesup_stop": ("stop", "Site: kaam rokna hai?"),
                    "sitesup_report": ("report", "Client ke liye report taiyaar"),
                    "interior_quote": ("quote", "Quotation: aapki haan chahiye"), "interior_order": ("order", "Vendor order: aapki haan chahiye"),
                    "interior_change": ("change", "Badlav se daam badla: aapki haan chahiye"),
                    "interior_payment": ("stage", "Client se paise maangne ki haan"),
                    "archassist_transmittal": ("transmittal", "Drawings issue karne ki haan?"),
                    "archassist_submission": ("submission", "Submission ki taiyaari"), "archassist_invoice": ("invoice", "Invoice ki haan chahiye"),
                    "society_card": ("card", "Society: aapki haan chahiye")}
    if kind in _makaan_wait:
        key, title = _makaan_wait[kind]
        return (f"{name}: {title}", _say) if (p.get(key) or {}).get("status") == "waiting" else None
    if kind == "rentdesk_message":
        return (f"{name}: Kirayedar ke liye message taiyaar", _say) if (p.get("message") or {}).get("status") == "draft" else None
    if kind == "rentdesk_alert":
        ok = p.get("kind") in ("renewal", "checklist", "forget") or bool((p.get("request") or {}).get("urgent"))
        return (f"{name}: Kiraya / property", _say) if ok else None
    if kind == "society_complaint":
        return (f"{name}: Zaroori shikayat", _say) if (p.get("complaint") or {}).get("urgent") else None
    _makaan = {"propagent_alert": "Property", "propagent_day": "Aaj ka property note", "rentdesk_day": "Aaj ka kiraya note",
               "sitesup_alert": "Site", "sitesup_day": "Aaj ka site note", "interior_alert": "Interior", "interior_day": "Aaj ka interior note",
               "archassist_alert": "Architect office", "archassist_day": "Aaj ka office note", "society_alert": "Society",
               "society_day": "Aaj society mein"}
    if kind in _makaan:
        return (f"{name}: {_makaan[kind]}", _say)
    # v0.150 Kanoon suite: cards push only while they wait for her (the same card is re-published when decided)
    _kanoon_wait = {"vakil_card": ("card", "waiting", "Vakil: aapki haan chahiye"),
                    "legalres_share": ("share", "waiting", "Memo bhejne ki aapki haan chahiye"),
                    "compliance_filing": ("filing", "waiting", "Compliance: aapki haan chahiye"),
                    "compliance_cert": ("cert", "waiting", "Compliance certificate: sign-off"),
                    "contracts_card": ("card", "waiting", "Contract: aapki haan chahiye"),
                    "cosec_filing": ("filing", "waiting", "MCA filing: aapki haan chahiye"),
                    "cosec_notice": ("meeting", "notice_waiting", "Meeting notice: aapki haan chahiye"),
                    "cosec_minutes": ("meeting", "minutes_waiting", "Minutes: aapki haan chahiye"),
                    "notary_print": ("doc", "waiting", "Notary: final print ke liye aapki haan"),
                    "pidesk_share": ("share", "waiting", "PI desk: aapki haan chahiye"),
                    "dpo_card": ("card", "waiting", "Data suraksha: aapki haan chahiye")}
    if kind in _kanoon_wait:
        key, st, title = _kanoon_wait[kind]
        c = p.get(key) or {}
        if c.get("status") != st:
            return None
        return (f"{name}: {title}", (c.get("title") or _say) if kind == "dpo_card" else _say)
    _kanoon = {"vakil_alert": "Court diary", "vakil_day": "Aaj ki court diary", "legalres_memo": "Research memo taiyaar",
               "compliance_alert": "Compliance yaad", "compliance_day": "Aaj ka compliance note", "contracts_alert": "Contract ki tareekh",
               "contracts_day": "Aaj ke contracts", "cosec_alert": "Company filing yaad", "cosec_day": "Aaj ka company secretary note",
               "notary_alert": "Notary: yaad dilana", "notary_day": "Aaj ka notary desk", "pidesk_alert": "PI desk",
               "dpo_breach": "Data breach: 72 ghante ka clock", "dpo_alert": "Data suraksha", "dpo_day": "Aaj data suraksha mein",
               "dpo_request": "Nayi data maang"}
    if kind in _kanoon:
        return (f"{name}: {_kanoon[kind]}", _say)
    # v0.152 Mehmaan suite: cards / drafts push only while they wait for her
    _mehmaan_wait = {"frontoffice_card": ("card", "waiting", "Hotel: aapki haan chahiye"),
                     "frontoffice_message": ("message", "draft", "Mehmaan ke liye message draft"),
                     "eventplan_booking": ("booking", "waiting", "Vendor booking: aapki haan chahiye"),
                     "eventplan_doc": ("doc", "waiting", "Client ko quotation / invoice: aapki haan chahiye"),
                     "eventplan_message": ("message", "waiting", "Invite / message: aapki haan chahiye"),
                     "eventplan_spend": ("spend", "waiting", "Event ka kharcha: aapki haan chahiye"),
                     "shaadi_card": ("card", "waiting", "Shaadi: aapki haan chahiye"),
                     "tourguide_card": ("card", "waiting", "Tour: aapki haan chahiye"),
                     "homestay_card": ("card", "waiting", "Homestay: aapke tap ka card"),
                     "banquet_card": ("card", "waiting", "Banquet: aapki haan chahiye")}
    if kind in _mehmaan_wait:
        key, st, title = _mehmaan_wait[kind]
        if (p.get(key) or {}).get("status") != st:
            return None
        return (f"{name}: {title}", _say)
    if kind == "frontoffice_alert" and p.get("kind") not in ("overbook", "formc", "no_show", "hold_released"):
        return None
    _mehmaan = {"frontoffice_alert": "Front desk", "frontoffice_day": "Aaj ka front desk", "eventplan_alert": "Event",
                "eventplan_day": "Aaj ka event note", "shaadi_alert": "Shaadi", "shaadi_day": "Aaj ka shaadi note",
                "tourguide_alert": "Tour", "tourguide_day": "Aaj ke tour", "homestay_alert": "Homestay", "homestay_day": "Aaj ka homestay",
                "banquet_alert": "Banquet", "banquet_day": "Aaj ka banquet note"}
    if kind in _mehmaan:
        return (f"{name}: {_mehmaan[kind]}", _say)
    if kind == "site_board":
        if not p.get("push"):
            return None
        return (f"{name}: website {p.get('number', '')}", str(p.get("say") or "")[:300])
    if kind == "app_board":                       # v0.128 app design: plan / looks / design ready
        if not p.get("push"):
            return None
        return (f"{name}: app {p.get('number', '')}", str(p.get("say") or "")[:300])
    if kind == "app_android":                     # v0.132 native Android build: APK ready / failed
        if not p.get("push"):
            return None
        return (f"{name}: Android app {p.get('number', '')}", str(p.get("say") or "")[:300])
    if kind == "site_lead":
        return (f"{name}: website par enquiry", str(p.get("say") or "")[:300])
    if kind in ("site_launch", "site_dns", "site_down"):
        if not p.get("push"):
            return None
        title = {"site_launch": "website live karein?", "site_dns": "domain ke DNS badlav", "site_down": "website nahi khul rahi"}[kind]
        return (f"{name}: {title}", str(p.get("say") or "")[:300])
    if kind == "site_live":
        return (f"{name}: website live!", str(p.get("say") or "")[:300])
    if kind in ("site_care", "site_github"):       # v0.124 monthly care note / GitHub export card
        if not p.get("push"):
            return None
        return (f"{name}: {'website ka mahina' if kind == 'site_care' else 'GitHub mein daalein?'}", str(p.get("say") or "")[:300])
    if kind == "site_domain":                     # v0.123 domain card / bought / KYC / renewal reminders
        if not p.get("push"):
            return None
        title = {"domain": "domain lena hai?", "domain_done": "domain", "domain_reminder": "domain yaad dilana"}.get(p.get("kind"), "domain")
        return (f"{name}: {title}", str(p.get("say") or "")[:300])
    if kind == "ads_change" and not p.get("decided"):
        return (f"{name}: ads mein badlav ki haan?", str(p.get("say") or "")[:300])
    if kind == "ads_report" and p.get("kind") in ("daily", "weekly"):
        return (f"{name}: ads ka hisaab", str(p.get("say") or "")[:300])
    if kind == "kalam_publish" and not p.get("decided"):
        return (f"{name}: publish karne ki haan?", f"{p.get('number', '')} {p.get('kind_label', '')}: {p.get('title', '')} · {p.get('where_label', '')}"[:300])
    if kind == "hoola_deal" and p.get("card") in ("quote", "confirm", "accept", "ready", "pack", "pay", "money", "receipt",
                                                   "check", "dispute", "resolve", "cancel_req", "mandate",
                                                   "booked", "estimate", "photo", "slots", "resched", "warranty"):
        head = {"quote": "list aayi, quote bhejun?", "confirm": "quote aaya, aapki haan?", "accept": "order aaya, pakka karein?",
                "ready": "parcel taiyaar", "pack": "order pakka, pack karna hai", "pay": "payment card aaya",
                "money": "graahak ne paisa bheja?", "receipt": "rasid aayi", "check": "sab sahi mila?",
                "dispute": "shikayat aayi", "resolve": "shikayat ka jawab", "cancel_req": "cancel ki request",
                "mandate": "standing order khud pakka hoga", "booked": "booking pakki", "estimate": "extra kaam: haan / na?",
                "photo": "kaam ki photo", "slots": "naye samay", "resched": "samay badalna hai", "warranty": "warranty shikayat"}[p["card"]]
        return (f"{name}: {head}", f"{p.get('with', '')} · {p.get('say', '')}"[:300])
    if kind == "hoola_rfq" and p.get("card") == "compare":
        return (f"{name}: quotes ki tulna taiyaar", str(p.get("say") or "")[:300])
    if kind == "hoola_promo" and p.get("card") == "offer":
        return (f"{name}: {p.get('with', '')} ka offer", str(p.get("title") or "")[:300])
    if kind == "hoola_mandate":
        return (f"{name}: standing order", str(p.get("say") or "")[:300])
    if kind == "a2a_task" and (p.get("task") or {}).get("waiting"):
        head = {"reply": "bahar ke AI agent ka sawaal", "quote": "bahar se order list aayi", "accept": "bahar ka order: pakka karein?"}
        return (f"{name}: {head.get(p['task']['waiting'], 'bahar ka AI agent')}", str(p.get("say") or "")[:300])
    if kind == "a2a_out":
        return (f"{name}: {(p.get('out') or {}).get('agent', 'agent')}", str(p.get("say") or "")[:300])
    if kind == "handoff_reminder":
        return (f"{name}: consent revoke karein?", str(p.get("say") or "")[:300])
    if kind == "digilocker":
        return (f"{name}: DigiLocker", str(p.get("say") or "")[:300])
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


PUSH_KINDS = {"message", "bazar_approval", "artifact", "pc_file", "photo_made", "blender3d", "pg_write", "email_draft", "bazar_open", "device_action",
              "home_device", "bt_request", "employee_ask", "employee_report", "biz_inbox", "operator_ask", "studio_approval", "google_reconnect", "darzi_quote", "darzi_day", "chai_plan", "office_spend", "office_day", "office_note", "lekhak_sign", "mshop_bill", "mshop_day", "gst_day", "gst_return", "payroll_run", "payroll_day", "fin_alert", "audit_update", "ask_form", "ins_day", "ins_advice", "tele_day", "kalam_publish", "hoola_deal", "seo_week", "seo_alert", "seo_draft", "hoola_pick", "hoola_khata", "thok_order", "thok_alert", "thok_day", "sheet_milaan", "doc_edit", "niryat_pi", "niryat_day", "ads_change", "ads_report", "hoola_rfq", "hoola_promo", "hoola_mandate", "fr_statement", "fr_day", "a2a_task", "a2a_out", "handoff_reminder", "digilocker", "theka_bill", "theka_letter", "theka_day", "brand_approval", "brand_idea", "site_board", "site_lead", "site_launch", "site_live", "site_dns", "site_down", "site_domain", "site_care", "site_github", "app_board", "app_android",
              # v0.133 Seva suite
              "seva_exception", "seva_sla", "seva_ticket", "seva_day", "helpdesk_change", "helpdesk_alert", "helpdesk_escalate", "helpdesk_day", "shikayat_comp", "shikayat_case", "shikayat_alert", "shikayat_day", "aftersales_charge", "aftersales_reminders", "aftersales_visit", "aftersales_day", "feedback_reply", "feedback_alert", "feedback_report", "wapsi_return", "wapsi_refund", "wapsi_day", "samudaay_alert", "samudaay_action", "samudaay_question", "samudaay_join", "samudaay_template", "samudaay_week", "callcentre_script", "callcentre_message", "callcentre_call",
              # v0.137 Tech suite
              "devsahayak_merge", "devsahayak_deploy", "devsahayak_push", "devsahayak_review", "devsahayak_task", "qa_bug", "qa_export", "qa_run", "itadmin_change", "itadmin_renewal", "itadmin_checklist", "itadmin_review", "itadmin_day", "ispnoc_change", "ispnoc_fault", "ispnoc_alert", "ispnoc_day", "cyber_action", "cyber_alerts", "cyber_incident", "cyber_advisory", "cyber_day", "devops_build", "devops_deploy", "devops_alert", "devops_day", "docwriter_publish", "docwriter_sync", "appreview_handoff", "appreview_alert", "product_publish", "product_day", "product_backlog",
              # v0.139 Safar suite
              "customs_filing", "customs_alert", "customs_day", "travel_booking", "travel_quote", "travel_reminder", "travel_day", "warehouse_adjust", "warehouse_day", "fleet_spend", "fleet_alert", "fleet_day", "courier_card", "courier_parcel", "courier_day", "drivers_alert", "drivers_plan", "drivers_day", "logistics_ewb", "logistics_alert", "logistics_day",
              # v0.144 Makaan suite
              "propagent_card", "propagent_alert", "propagent_day", "rentdesk_approval", "rentdesk_message", "rentdesk_alert", "rentdesk_day", "sitesup_indent", "sitesup_stop", "sitesup_report", "sitesup_alert", "sitesup_day", "interior_quote", "interior_order", "interior_change", "interior_payment", "interior_alert", "interior_day", "archassist_transmittal", "archassist_submission", "archassist_invoice", "archassist_alert", "archassist_day", "society_card", "society_complaint", "society_alert", "society_day",
              # v0.150 Kanoon suite
              "vakil_card", "vakil_alert", "vakil_day", "legalres_share", "legalres_memo", "compliance_filing", "compliance_cert", "compliance_alert", "compliance_day", "contracts_card", "contracts_alert", "contracts_day", "cosec_filing", "cosec_notice", "cosec_minutes", "cosec_alert", "cosec_day", "notary_print", "notary_alert", "notary_day", "pidesk_share", "pidesk_alert", "dpo_card", "dpo_breach", "dpo_alert", "dpo_day", "dpo_request",
              # v0.152 Mehmaan suite
              "frontoffice_card", "frontoffice_message", "frontoffice_alert", "frontoffice_day", "eventplan_booking", "eventplan_doc", "eventplan_message", "eventplan_spend", "eventplan_alert", "eventplan_day", "shaadi_card", "shaadi_alert", "shaadi_day", "tourguide_card", "tourguide_alert", "tourguide_day", "homestay_card", "homestay_alert", "homestay_day", "banquet_card", "banquet_alert", "banquet_day"}
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
