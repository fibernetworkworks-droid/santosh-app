"""Push notifications through Firebase Cloud Messaging (HTTP v1), Google Play's way to reach a phone whose app is
closed or whose screen is locked. Every Santosh event that matters to the user (a reply, an approval card, a
finished page or file, a phone action like an alarm) is also sent as a high-priority data push; the phone shows it
only when the app isn't on screen, so there are no duplicates. No message content is stored at Google beyond
delivery; device actions are re-checked by the phone (claimed once, ignored when old)."""
from __future__ import annotations

import json
import re
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
        from .agent.replystyle import plain   # v0.222 the notification shows words, never ** or ###
        text = plain(str(p.get("text") or ""))
        return (name, text[:400]) if text else None
    if kind == "goal":   # v0.186 lamba kaam: push only when it blocks on her, or it is done
        st = p.get("status")
        title = str(p.get("title") or p.get("goal") or "Long task")[:80]
        if st == "blocked":
            return (f"{name}: needs you", f"Long task is blocked: {title} — {str(p.get('reason') or 'your answer is needed')[:200]}")
        if st == "done":
            rep = p.get("report") if isinstance(p.get("report"), dict) else {}
            extra = (" · " + str(rep.get("aapka"))[:120]) if rep.get("aapka") and "Kuch nahi" not in str(rep.get("aapka")) else ""
            return (f"{name}: task complete", f"Long task done: {title}{extra}")
        if st == "working" and p.get("milestone"):   # v0.228 a real milestone, at most a few per job (never every step)
            stage = str(p.get("stage") or "")[:100]
            return (f"{name}: task in progress",
                    f"{title} — {p['milestone']} steps done" + (f". Now: {stage}" if stage else ""))
        return None
    if kind == "bazar_approval":
        if p.get("status") not in (None, "", "pending") or p.get("result"):
            return None
        return ("Please approve", f"{p.get('title', '')} {p.get('amount', '')}".strip())
    if kind == "artifact":
        return (f"{name} made this", str(p.get("title") or "Page is ready")) if p.get("status") == "ready" else None
    if kind == "pc_file":
        return (f"{name} made a PDF" if p.get("source") == "bazar" else "File from your PC", str(p.get("name") or ""))
    if kind == "photo_made":
        return (f"{name} {'edited' if p.get('edit') else 'made'} a photo", str(p.get("prompt") or "")[:120])
    if kind == "pg_write":
        if p.get("status") != "pending" or p.get("again"):
            return None
        return (f"{name}: database change needs your yes", str(p.get("say") or "")[:200])
    if kind == "blender3d":
        if not p.get("push") or p.get("status") != "done":
            return None
        return (f"{name} made a 3D model", str(p.get("say") or p.get("title") or "")[:200])
    if kind == "notebook_output":
        if not p.get("push") or p.get("status") not in ("ready", "failed"):
            return None
        head = f"{p.get('icon', '📒')} {p.get('label', 'Notebook')} ready" if p.get("status") == "ready" else f"{p.get('label', 'Notebook')} could not be made"
        return (head, str(p.get("title") if p.get("status") == "ready" else p.get("error") or "")[:200])
    if kind == "email_draft":
        return ("Email draft ready", str(p.get("subject") or "Review and send"))
    if kind == "email_new":
        if p.get("digest"):
            return (str(p.get("subject") or "New email"), str(p.get("snippet") or "")[:200])
        return (f"New email: {str(p.get('from') or p.get('from_email') or '')[:60]}",
                str(p.get("subject") or "").strip()[:200])
    if kind == "email_snooze":
        return ("Snooze ended", str(p.get("subject") or "Email is back in your inbox"))
    if kind == "hoola_knock" and not p.get("quiet") and p.get("status") in (None, "pending"):
        b = p.get("body") or {}
        said = str(b.get("text") or "")[:200] or (f"📎 {b.get('name')}" if b.get("name") else "")
        return (f"{p.get('from', 'Hoola')}", f"{p.get('what', '')}: {said}".strip(": "))
    if kind == "hoola_connect" and p.get("status") == "incoming" and not p.get("quiet"):
        return ("Connect request", f"{p.get('label', '')} wants to connect")
    if kind == "hoola_msg" and not p.get("quiet") and not p.get("fyi"):
        return (f"{name}: {p.get('from', '')}", str(p.get("text") or "")[:300])
    if kind == "employee_ask" and p.get("status") == "pending":
        return ("Needs your yes", f"{p.get('what', '')} · {p.get('who', '')}: {p.get('detail', '')}"[:300])
    if kind == "darzi_quote" and p.get("status") == "pending":
        return (f"{name}: new price, your yes?", f"{p.get('customer', '')} · {p.get('label', '')}: {p.get('price') or 'enter the price'}"[:300])
    if kind == "chai_plan":
        return (f"{name}: tomorrow's supplies", str(p.get("say") or "")[:300])
    if kind == "darzi_day":
        return (f"{name}: today's tailoring", str(p.get("text") or "")[:300])
    if kind == "office_spend" and p.get("status") == "pending":
        return (f"{name}: expense, your yes?", f"{p.get('number', '')} {p.get('title', '')}: {p.get('amount') or 'enter the amount'}"[:300])
    if kind == "mshop_bill" and p.get("status") == "pending":
        return (f"{name}: bill needs your yes", f"{p.get('number', '')} {p.get('customer', '')} · {p.get('device', '')}: {p.get('total', '')}"[:300])
    if kind == "theka_bill":
        return (f"{name}: {p.get('label', 'RA bill')} ready", f"{p.get('project', '')}: net in hand ~Rs {p.get('net', 0):,.0f}; needs your yes before it goes to the department")
    if kind == "theka_letter":
        return (f"{name}: letter draft", f"{p.get('project', '')}: {p.get('title', '')}")
    if kind == "theka_day":
        return (f"{name}: contract work", str(p.get("text") or "")[:300])
    if kind == "fr_statement":
        return (f"{name}: royalty statement", f"{p.get('brand', '')} {p.get('month', '')}: payable Rs {p.get('payable', 0):,.0f}; needs your yes before the report is sent")
    if kind == "fr_day":
        return (f"{name}: outlets", str(p.get("text") or "")[:300])
    if kind == "niryat_pi":
        return (f"{name}: PI ready", f"{p.get('buyer', '')}: {p.get('currency', '')} {p.get('total', 0):,.2f}; needs your yes before sending")
    if kind == "niryat_day":
        return (f"{name}: exports", str(p.get("text") or "")[:300])
    if kind == "thok_order":
        return (f"{name}: order, make the bill?", f"{p.get('party', '')}: Rs {p.get('total', 0):,.0f}" + (" (check credit)" if p.get("level") != "ok" else ""))
    if kind in ("thok_alert", "thok_day"):
        return (f"{name}: wholesale", str(p.get("text") or "")[:300])
    if kind in ("seo_week", "seo_alert"):
        return (f"{name}: SEO", str(p.get("text") or "")[:300])
    if kind == "social_lead":
        return (f"{name}: lead on Instagram / Facebook", str(p.get("text") or "")[:300])
    if kind in ("social_alert", "social_day", "social_week"):
        return (f"{name}: social media", str(p.get("text") or "")[:300])
    if kind == "seo_draft":
        return (f"{name}: SEO draft", f"{p.get('title', '')}: needs your yes to finalize")
    if kind == "ins_day":
        return (f"{name}: insurance", str(p.get("text") or "")[:300])
    if kind == "ins_advice":
        return (f"{name}: advice ready", f"Options for {p.get('client', '')}; needs your yes before sending")
    if kind == "brand_approval":
        dd = p.get("design") or {}
        return (f"{name}: finalize the poster?", f"{dd.get('number', '')} {dd.get('title', '')}: review the proof and say yes"[:300])
    if kind == "brand_idea":
        return (f"{name}: festival poster?", str(p.get("say") or "")[:300])
    # v0.133 Seva suite
    if kind == "seva_exception" and p.get("status") in (None, "", "pending", "waiting"):
        return (f"{name}: needs your yes: {p.get('kind_label', 'request')}", str(p.get("say") or "")[:300])
    if kind == "seva_sla" and p.get("breach"):
        return (f"{name}: complaint deadline: {p.get('ticket', '')}", str(p.get("text") or "")[:300])
    if kind == "seva_ticket" and p.get("event") == "new" and p.get("priority") == "urgent":
        return (f"{name}: new complaint {p.get('number', '')}", f"{p.get('customer', '')}: {p.get('text', '')}"[:300])
    if kind == "seva_day":
        return (f"{name}: service today", str(p.get("text") or "")[:300])
    if kind == "helpdesk_change" and (p.get("change") or {}).get("status") in (None, "", "waiting"):
        return (f"{name}: IT: needs your yes", str(p.get("say") or "")[:300])
    if kind == "helpdesk_alert":
        return (f"{name}: IT / security", str(p.get("say") or "")[:300])
    if kind == "helpdesk_escalate":
        return (f"{name}: message for the technician is ready", str(p.get("say") or "")[:300])
    if kind == "helpdesk_day":
        return (f"{name}: today's IT note", str(p.get("say") or "")[:300])
    if kind == "shikayat_comp" and not p.get("event"):
        c = p.get("comp") or {}
        sh = p.get("show") or {}
        return (f"{name}: compensation needs your yes", f"{sh.get('case') or c.get('number', '')}: {c.get('kind_label', '')} {c.get('amount_text', '')}".strip()[:300])
    if kind == "shikayat_case" and p.get("event") == "new":
        c = p.get("case") or {}
        causes = c.get("cause_labels") or []
        causes = ", ".join(causes) if isinstance(causes, list) else str(causes)
        return (f"{name}: new complaint {c.get('number', '')}", f"{c.get('customer', '')} · {causes}"[:300])
    if kind in ("shikayat_alert", "shikayat_day"):
        return (f"{name}: {'complaint deadline' if kind == 'shikayat_alert' else 'today\'s complaints'}", str(p.get("text") or "")[:300])
    if kind == "aftersales_charge" and p.get("status") in ("pending", "needs_price"):
        tot = p.get("total") or 0
        body = f"{p.get('number', '')} {p.get('customer', '')}: " + (f"Charge the customer Rs {tot:,.0f}?" if p.get("status") == "pending"
                                                                     else "enter the price")
        return (f"{name}: charge needs your yes", body[:300])
    if kind == "aftersales_reminders" and p.get("count"):
        return (f"{name}: service reminder", f"{p.get('count')} reminder drafts ready to send")
    if kind == "aftersales_visit" and p.get("status") in (None, "booked"):
        return (f"{name}: visit booked", f"{p.get('number', '')} {p.get('customer', '')}: {p.get('when', '')}, {p.get('tech', '')}"[:300])
    if kind == "aftersales_day":
        return (f"{name}: after-sales today", str(p.get("text") or "")[:300])
    if kind == "feedback_reply" and p.get("status") in (None, "draft"):
        it = p.get("item") or {}
        stars = f" {it.get('stars')}*" if it.get("stars") else ""
        return (f"{name}: review reply", f"Reply draft ready: {it.get('source_label', '')}{stars} - it goes out when you tap Yes"[:300])
    if kind in ("feedback_alert", "feedback_report"):
        return (f"{name}: {'customer complaint' if kind == 'feedback_alert' else 'feedback report'}", str(p.get("text") or "")[:300])
    if kind == "wapsi_return" and p.get("event") == "new":
        r = p.get("return") or {}
        cust = r.get("customer") or {}
        cust = cust.get("name", "") if isinstance(cust, dict) else str(cust)
        verdict = {"approve": "return looks fine", "ask_more": "needs more proof", "reject_suggest": "looks outside the rules"}.get(
            str((r.get("check") or {}).get("verdict") or ""), "take a look")
        return (f"{name}: return {r.get('number', '')}", f"{cust}: {r.get('reason_label', '')} - {verdict}"[:300])
    if kind == "wapsi_refund" and (p.get("refund") or {}).get("status") == "waiting" and not p.get("event"):
        f = p.get("refund") or {}
        return (f"{name}: refund needs your yes", f"{p.get('return_number', '')} {p.get('customer', '')}: Rs {f.get('amount') or 0:,.0f} - approve on the card (fingerprint)"[:300])
    if kind == "wapsi_day":
        return (f"{name}: returns", str(p.get("text") or "")[:300])
    if kind == "samudaay_alert" and p.get("status") in (None, "", "open", "new"):
        return (f"{name}: {p.get('kind', 'alert')} in the group", str(p.get("title") or "")[:300])
    if kind == "samudaay_action" and p.get("status") in (None, "", "pending", "waiting"):
        return (f"{name}: needs your yes", f"{p.get('label', '')}: {p.get('member', '')} ({p.get('community', '')})"[:300])
    if kind == "samudaay_question":
        return (f"{name}: question in the group", f"{p.get('member', '')}: {p.get('text', '')}"[:300])
    if kind == "samudaay_join":
        return (f"{name}: join request", f"{p.get('name', '')} wants to join {p.get('community', '')}"[:300])
    if kind == "samudaay_template" and p.get("status") in (None, "", "draft", "waiting"):
        return (f"{name}: welcome message", "Review it and tap Yes; only then will it go to new members")
    if kind == "samudaay_week":
        return (f"{name}: group's weekly health", str(p.get("say") or "")[:300])
    if kind == "callcentre_script" and p.get("status") == "waiting":
        return (f"{name}: call centre script v{p.get('version', '')}", f"Needs your Yes to go live: {p.get('say', '')}"[:300])
    if kind == "callcentre_message":
        return (f"{name}: message from a call", str(p.get("say") or "")[:300])
    if kind == "callcentre_call" and (p.get("outcome") in ("transferred", "message", "complaint", "failed", "callback") or p.get("flags")):
        return (f"{name}: call: {p.get('caller_masked', '')}", str(p.get("summary") or "")[:300])
    # v0.137 Tech suite
    _say = str(p.get("say") or "")[:300]
    if kind == "devsahayak_task":
        t = p.get("task") or {}
        if p.get("end"):          # Hoola Code Phase 5: a background run just ended - done, or it needs her
            head = "Hoola Code: done" if p.get("end") == "done" else "Hoola Code needs you"
            return (f"{name}: {head}", _say or str(t.get("title") or ""))
        if t.get("status") in ("checks_failed", "refused", "explained") or (t.get("number") and _say.startswith(str(t.get("number"))) and "CI" in _say):
            return (f"{name}: Developer: {t.get('number', '')}", _say)
        return None
    _tech = {"devsahayak_merge": "Merge needs your yes", "devsahayak_deploy": "Deploy needs your yes",
             "devsahayak_push": "Opening a PR needs your yes", "devsahayak_plan": "Plan ready: needs your yes to start", "devsahayak_review": "Code review ready",
             "qa_bug": "New bug found", "qa_export": "GitHub issue: needs your yes",
             "itadmin_change": "IT: needs your yes", "itadmin_renewal": "Renewal coming up",
             "itadmin_checklist": "Joiner / leaver checklist", "itadmin_review": "Time for an access review",
             "itadmin_day": "Today's IT admin note", "ispnoc_change": "Network: needs your yes", "ispnoc_alert": "Network alert",
             "ispnoc_day": "Today's network", "cyber_action": "Security: needs your yes", "cyber_alerts": "Important security alert",
             "cyber_incident": "Cyber incident opened", "cyber_advisory": "Software risk", "cyber_day": "Today's security",
             "devops_build": "Build failed", "devops_day": "Today's DevOps note", "docwriter_publish": "Make the docs public?",
             "docwriter_sync": "Product changed: update the docs", "appreview_handoff": "App review: needs your yes",
             "appreview_alert": "App review", "product_publish": "Sending out: needs your yes", "product_day": "Today's product note",
             "product_backlog": "New issues in the backlog"}
    if kind in _tech:
        return (f"{name}: {_tech[kind]}", _say)
    if kind == "qa_run":
        r = p.get("run") or {}
        if (r.get("counts") or {}).get("fail") or r.get("status") == "failed":
            return (f"{name}: Test finished", _say)
        return None
    if kind == "ispnoc_fault":
        return (f"{name}: Network problem", _say) if p.get("new") else None
    if kind == "devops_deploy":
        return (f"{name}: Deploy: needs your yes", _say) if p.get("push") else None
    if kind == "devops_alert":
        return (f"{name}: DevOps alert", _say) if p.get("push") else None
    # v0.139 Safar suite
    if kind == "customs_filing":
        return (f"{name}: Import filing: needs your yes", _say) if (p.get("filing") or {}).get("status") == "waiting" else None
    if kind == "travel_booking":
        return (f"{name}: Travel: booking needs your yes", _say) if p.get("status") == "waiting" else None
    if kind == "warehouse_adjust":
        return (f"{name}: Warehouse: stock change needs your yes", _say) if (p.get("adjust") or {}).get("status") == "waiting" else None
    if kind == "courier_card":
        c = p.get("card") or {}
        if c.get("status") != "waiting":
            return None
        b = c.get("body") or {}
        return (f"{name}: Courier: needs your yes", f"{b.get('title', '')} - {b.get('say', '')}"[:300])
    if kind == "courier_parcel":
        if p.get("event") not in ("exception", "rto", "delivered", "out_for_delivery"):
            return None
        pc = p.get("parcel") or {}
        return (f"{name}: Parcel: {pc.get('number', '')}", f"{pc.get('status_label', '')}: {pc.get('raw', '')}"[:300])
    if kind == "logistics_alert":
        return (f"{name}: Logistics · {p.get('number', '')}", str(p.get("text") or "")[:300])
    _safar_text = {"courier_day": "Today's courier note", "logistics_day": "Today's dispatch"}
    if kind in _safar_text:
        return (f"{name}: {_safar_text[kind]}", str(p.get("text") or "")[:300])
    _safar = {"customs_alert": "Import / customs", "customs_day": "Today's import desk", "travel_quote": "Customer quote ready",
              "travel_reminder": "Travel reminder", "travel_day": "Today's travel", "warehouse_day": "Today's warehouse note",
              "fleet_spend": "Fleet: expense needs your yes", "fleet_alert": "Fleet", "fleet_day": "Today's fleet note",
              "drivers_alert": "Driver documents", "drivers_plan": "Driver duty: ready to send", "drivers_day": "Today's drivers",
              "logistics_ewb": "E-way bill: needs your tap"}
    if kind in _safar:
        return (f"{name}: {_safar[kind]}", _say)
    # v0.144 Makaan suite: cards push only while they wait for her (the same card is re-published when decided)
    _makaan_wait = {"propagent_card": ("card", "Property: needs your yes"),
                    "rentdesk_approval": ("approval", "Rent: needs your yes"),
                    "sitesup_indent": ("indent", "Site: indent needs your yes"), "sitesup_stop": ("stop", "Site: stop work?"),
                    "sitesup_report": ("report", "Report ready for the client"),
                    "interior_quote": ("quote", "Quotation: needs your yes"), "interior_order": ("order", "Vendor order: needs your yes"),
                    "interior_change": ("change", "Change affects the price: needs your yes"),
                    "interior_payment": ("stage", "Ask the client for payment: needs your yes"),
                    "archassist_transmittal": ("transmittal", "Issue the drawings?"),
                    "archassist_submission": ("submission", "Submission prep"), "archassist_invoice": ("invoice", "Invoice needs your yes"),
                    "society_card": ("card", "Society: needs your yes")}
    if kind in _makaan_wait:
        key, title = _makaan_wait[kind]
        return (f"{name}: {title}", _say) if (p.get(key) or {}).get("status") == "waiting" else None
    if kind == "rentdesk_message":
        return (f"{name}: Message for the tenant is ready", _say) if (p.get("message") or {}).get("status") == "draft" else None
    if kind == "rentdesk_alert":
        ok = p.get("kind") in ("renewal", "checklist", "forget") or bool((p.get("request") or {}).get("urgent"))
        return (f"{name}: Rent / property", _say) if ok else None
    if kind == "society_complaint":
        return (f"{name}: Urgent complaint", _say) if (p.get("complaint") or {}).get("urgent") else None
    _makaan = {"propagent_alert": "Property", "propagent_day": "Today's property note", "rentdesk_day": "Today's rent note",
               "sitesup_alert": "Site", "sitesup_day": "Today's site note", "interior_alert": "Interior", "interior_day": "Today's interior note",
               "archassist_alert": "Architect office", "archassist_day": "Today's office note", "society_alert": "Society",
               "society_day": "Today in the society"}
    if kind in _makaan:
        return (f"{name}: {_makaan[kind]}", _say)
    # v0.150 Kanoon suite: cards push only while they wait for her (the same card is re-published when decided)
    _kanoon_wait = {"vakil_card": ("card", "waiting", "Lawyer: needs your yes"),
                    "legalres_share": ("share", "waiting", "Sending the memo needs your yes"),
                    "pathyakram_share": ("share", "waiting", "Sending the paper / plan needs your yes"),
                    "guru_report": ("share", "waiting", "Study report: sending to the guardian needs your yes"),
                    "daftar_share": ("share", "waiting", "School: sending to the guardian needs your yes"),   # v0.381
                    "compliance_filing": ("filing", "waiting", "Compliance: needs your yes"),
                    "compliance_cert": ("cert", "waiting", "Compliance certificate: sign-off"),
                    "contracts_card": ("card", "waiting", "Contract: needs your yes"),
                    "cosec_filing": ("filing", "waiting", "MCA filing: needs your yes"),
                    "cosec_notice": ("meeting", "notice_waiting", "Meeting notice: needs your yes"),
                    "cosec_minutes": ("meeting", "minutes_waiting", "Minutes: need your yes"),
                    "notary_print": ("doc", "waiting", "Notary: final print needs your yes"),
                    "pidesk_share": ("share", "waiting", "PI desk: needs your yes"),
                    "dpo_card": ("card", "waiting", "Data protection: needs your yes")}
    if kind in _kanoon_wait:
        key, st, title = _kanoon_wait[kind]
        c = p.get(key) or {}
        if c.get("status") != st:
            return None
        return (f"{name}: {title}", (c.get("title") or _say) if kind == "dpo_card" else _say)
    _kanoon = {"pathyakram_paper": "Paper ready", "pathyakram_plan": "Plan ready", "vakil_alert": "Court diary", "vakil_day": "Today's court diary", "legalres_memo": "Research memo ready",
               "compliance_alert": "Compliance reminder", "compliance_day": "Today's compliance note", "contracts_alert": "Contract date",
               "contracts_day": "Today's contracts", "cosec_alert": "Company filing reminder", "cosec_day": "Today's company secretary note",
               "notary_alert": "Notary: reminder", "notary_day": "Today's notary desk", "pidesk_alert": "PI desk",
               "dpo_breach": "Data breach: 72-hour clock", "dpo_alert": "Data protection", "dpo_day": "Today in data protection",
               "dpo_request": "New data request"}
    if kind in _kanoon:
        return (f"{name}: {_kanoon[kind]}", _say)
    # v0.152 Mehmaan suite: cards / drafts push only while they wait for her
    _mehmaan_wait = {"frontoffice_card": ("card", "waiting", "Hotel: needs your yes"),
                     "frontoffice_message": ("message", "draft", "Guest message draft"),
                     "eventplan_booking": ("booking", "waiting", "Vendor booking: needs your yes"),
                     "eventplan_doc": ("doc", "waiting", "Quotation / invoice to the client: needs your yes"),
                     "eventplan_message": ("message", "waiting", "Invite / message: needs your yes"),
                     "eventplan_spend": ("spend", "waiting", "Event expense: needs your yes"),
                     "shaadi_card": ("card", "waiting", "Wedding: needs your yes"),
                     "tourguide_card": ("card", "waiting", "Tour: needs your yes"),
                     "homestay_card": ("card", "waiting", "Homestay: card for your tap"),
                     "banquet_card": ("card", "waiting", "Banquet: needs your yes")}
    if kind in _mehmaan_wait:
        key, st, title = _mehmaan_wait[kind]
        if (p.get(key) or {}).get("status") != st:
            return None
        return (f"{name}: {title}", _say)
    if kind == "frontoffice_alert" and p.get("kind") not in ("overbook", "formc", "no_show", "hold_released"):
        return None
    _mehmaan = {"frontoffice_alert": "Front desk", "frontoffice_day": "Today's front desk", "eventplan_alert": "Event",
                "eventplan_day": "Today's event note", "shaadi_alert": "Wedding", "shaadi_day": "Today's wedding note",
                "tourguide_alert": "Tour", "tourguide_day": "Today's tours", "homestay_alert": "Homestay", "homestay_day": "Today's homestay",
                "banquet_alert": "Banquet", "banquet_day": "Today's banquet note"}
    if kind in _mehmaan:
        return (f"{name}: {_mehmaan[kind]}", _say)
    # v0.156 Kala suite: cards push only while they wait for her
    _kala_wait = {"editdesk_card": "Edit desk: needs your yes", "motiondesk_card": "Motion studio: needs your yes",
                  "filmdesk_card": "Film desk: needs your yes", "patrakar_card": "News: needs your yes",
                  "photoassist_card": "Photo: needs your yes", "graphic_card": "Design: needs your yes",
                  "artistmgr_card": "Artist: needs your yes", "kitab_card": "Book: needs your yes",
                  "podcast_card": "Podcast: needs your yes", "influencer_card": "Influencer: needs your yes"}
    if kind in _kala_wait:
        if (p.get("card") or {}).get("status") != "waiting":
            return None
        return (f"{name}: {_kala_wait[kind]}", _say)
    if kind == "motiondesk_update" and p.get("kind") not in (None, "", "rendered"):
        return None
    _kala = {"editdesk_alert": "Edit desk", "editdesk_day": "Today's edit desk", "editdesk_note": "New edit version ready",
             "motiondesk_alert": "Motion studio", "motiondesk_day": "Today's studio note", "motiondesk_update": "Render ready",
             "filmdesk_alert": "Film desk", "filmdesk_day": "Today's film desk note", "patrakar_alert": "News desk",
             "patrakar_day": "Today's news note", "photoassist_alert": "Photo studio", "photoassist_day": "Today's photo note",
             "graphic_alert": "Design desk", "graphic_day": "Today's design note", "artistmgr_alert": "Artist manager",
             "artistmgr_day": "Today's artist note", "kitab_alert": "Book", "kitab_day": "Today's book note",
             "podcast_alert": "Podcast", "podcast_day": "Today's podcast note", "influencer_alert": "Influencer",
             "influencer_day": "Today's influencer note"}
    if kind in _kala:
        return (f"{name}: {_kala[kind]}", _say)
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
    if kind == "app_ios":                         # v0.332 IPHONE: iPhone build ready / on TestFlight / failed
        if not p.get("push"):
            return None
        return (f"{name}: iPhone app {p.get('number', '')}", str(p.get("say") or "")[:300])
    if kind == "site_lead":
        return (f"{name}: {'booking request' if p.get('booking') else 'enquiry'} on the website", str(p.get("say") or "")[:300])
    if kind in ("site_launch", "site_dns", "site_down"):
        if not p.get("push"):
            return None
        title = {"site_launch": "go live with the website?", "site_dns": "domain DNS changes", "site_down": "website is not opening"}[kind]
        return (f"{name}: {title}", str(p.get("say") or "")[:300])
    if kind == "site_live":
        return (f"{name}: website is live!", str(p.get("say") or "")[:300])
    if kind == "site_ops":                        # v0.564 her website: an error spike / slow pages / a backup that did not come back
        if not p.get("push"):
            return None
        title = {"errors": "errors on the website", "slow": "website is slow", "backup": "backup check failed"}.get(p.get("kind"), "website")
        return (f"{name}: {title}", str(p.get("say") or "")[:300])
    if kind in ("site_care", "site_github"):       # v0.124 monthly care note / GitHub export card
        if not p.get("push"):
            return None
        return (f"{name}: {'website monthly note' if kind == 'site_care' else 'Add to GitHub?'}", str(p.get("say") or "")[:300])
    if kind == "site_domain":                     # v0.123 domain card / bought / KYC / renewal reminders
        if not p.get("push"):
            return None
        title = {"domain": "buy the domain?", "domain_done": "domain", "domain_reminder": "domain reminder"}.get(p.get("kind"), "domain")
        return (f"{name}: {title}", str(p.get("say") or "")[:300])
    if kind == "ads_change" and not p.get("decided"):
        return (f"{name}: ads change, your yes?", str(p.get("say") or "")[:300])
    if kind == "ads_report" and p.get("kind") in ("daily", "weekly"):
        return (f"{name}: ads report", str(p.get("say") or "")[:300])
    if kind == "kalam_publish" and not p.get("decided"):
        return (f"{name}: publish, your yes?", f"{p.get('number', '')} {p.get('kind_label', '')}: {p.get('title', '')} · {p.get('where_label', '')}"[:300])
    if kind == "hoola_deal" and p.get("card") in ("quote", "confirm", "accept", "ready", "pack", "pay", "money", "receipt",
                                                   "check", "dispute", "resolve", "cancel_req", "mandate",
                                                   "booked", "estimate", "photo", "slots", "resched", "warranty"):
        head = {"quote": "list received, send a quote?", "confirm": "quote received, your yes?", "accept": "order received, confirm it?",
                "ready": "parcel ready", "pack": "order confirmed, pack it", "pay": "payment card received",
                "money": "customer sent the money?", "receipt": "receipt received", "check": "everything correct?",
                "dispute": "complaint received", "resolve": "complaint reply", "cancel_req": "cancel request",
                "mandate": "standing order will confirm itself", "booked": "booking confirmed", "estimate": "extra work: yes / no?",
                "photo": "photo of the work", "slots": "new time slots", "resched": "needs a new time", "warranty": "warranty complaint"}[p["card"]]
        return (f"{name}: {head}", f"{p.get('with', '')} · {p.get('say', '')}"[:300])
    if kind == "hoola_rfq" and p.get("card") == "compare":
        return (f"{name}: quote comparison ready", str(p.get("say") or "")[:300])
    if kind == "hoola_promo" and p.get("card") == "offer":
        return (f"{name}: offer from {p.get('with', '')}", str(p.get("title") or "")[:300])
    if kind == "hoola_mandate":
        return (f"{name}: standing order", str(p.get("say") or "")[:300])
    if kind == "hoola_dosti" and p.get("card") in ("doc_ask", "skill", "paused", "msg"):
        head = {"doc_ask": "document requested: send it?", "skill": "friend's skill: learn it?",
                "paused": "friend chat paused", "msg": "message from a friend's avatar"}[p["card"]]
        return (f"{name}: {head}", f"{p.get('with', '')} · {p.get('say', '')}"[:300])
    if kind == "a2a_task" and (p.get("task") or {}).get("waiting"):
        head = {"reply": "question from an outside AI agent", "quote": "order list from outside", "accept": "outside order: confirm it?"}
        return (f"{name}: {head.get(p['task']['waiting'], 'outside AI agent')}", str(p.get("say") or "")[:300])
    if kind == "a2a_out":
        return (f"{name}: {(p.get('out') or {}).get('agent', 'agent')}", str(p.get("say") or "")[:300])
    if kind == "handoff_reminder":
        return (f"{name}: revoke consent?", str(p.get("say") or "")[:300])
    if kind == "digilocker":
        return (f"{name}: DigiLocker", str(p.get("say") or "")[:300])
    if kind == "hoola_khata" and p.get("card") in ("pay", "money", "receipt", "due"):
        head = {"pay": "ledger payment card", "money": "ledger payment sent?", "receipt": "ledger receipt",
                "due": "ledger due date"}[p["card"]]
        return (f"{name}: {head}", f"{p.get('with', '')} · {p.get('say', '')}"[:300])
    if kind == "hoola_pick" and p.get("card") in ("task", "ready"):
        return (f"{name}: {'pick list' if p.get('card') == 'task' else 'parcel ready'}", str(p.get("say") or "")[:300])
    if kind in ("sheet_milaan", "doc_edit") and p.get("status") == "ready":
        head = "Sheet match ready" if kind == "sheet_milaan" else "file changes ready"
        return (f"{name}: {head}", f"{p.get('name', '')}: {p.get('say', '')}"[:300])
    if kind == "tele_day":
        return (f"{name}: today's call list", str(p.get("text") or "")[:300])
    if kind == "audit_update":
        return (f"{name}: audit check complete", f"{p.get('findings', 0)} findings to review")
    if kind == "fin_alert":
        return (f"{name}: money", str(p.get("text") or "")[:300])
    if kind == "voice_alert":   # v0.234 voice Phase 5: the call's slow tail / broken calls, once a day
        return (f"{name}: call check", str(p.get("text") or "")[:300])
    if kind == "payroll_run" and p.get("status") == "ready":
        return (f"{name}: salary needs your yes", "Payroll is ready, review it and say yes")
    if kind == "payroll_day":
        return (f"{name}: payroll", str(p.get("text") or "")[:300])
    if kind == "gst_day":
        return (f"{name}: today's GST", str(p.get("text") or "")[:300])
    if kind == "gst_return" and p.get("status") == "ready":
        return (f"{name}: return needs your yes", "GST return is ready, review it and say yes")
    if kind == "mshop_day":
        return (f"{name}: today's shop", str(p.get("text") or "")[:300])
    if kind == "office_day":
        return (f"{name}: today's office", str(p.get("text") or "")[:300])
    if kind == "office_note":
        return (f"{name}: weekly office note", "The note is ready, take a look")
    if kind == "lekhak_sign" and p.get("status") == "waiting_sign":
        return (f"{name}: sign the letter?", f"{p.get('number', '')} {p.get('title', '')}: review the final and tap Yes"[:300])
    if kind == "ask_form" and p.get("status") == "pending":
        return (f"{name}: please fill in a form", f"{p.get('title', '')}: {len(p.get('fields') or [])} questions, all at once"[:300])
    if kind == "google_reconnect":
        return (f"{name}: reconnect Google", str(p.get("text") or "")[:300])
    if kind == "studio_approval" and p.get("status") == "pending":
        return (f"{name}: video cost ₹{p.get('inr', '')}", f"{p.get('project', '')}: {p.get('shots', 0)} shots, it is made only after you tap Yes"[:300])
    if kind == "operator_ask" and p.get("status") == "pending":
        title = {"otp": "OTP needed", "captcha": "Fill in the CAPTCHA", "secret": "Please enter it yourself", "payment": "Please make the payment yourself",
                 "approve": "Needs your yes"}.get(p.get("kind", ""), "A question for you")
        return (f"{name}: {title}", f"{p.get('site', '')}: {p.get('reason', '')}"[:300])
    if kind == "biz_inbox" and p.get("handover"):
        c = p.get("contact") or {}
        return ("WhatsApp: needs you", f"{c.get('name', '')}: {p.get('reason', '')}"[:300])
    if kind == "biz_inbox" and (p.get("message") or {}).get("direction") == "in" and (p.get("contact") or {}).get("human"):
        c = p.get("contact") or {}
        return (f"WhatsApp: {c.get('name', '')}", str((p.get('message') or {}).get('text') or "")[:300])
    if kind == "employee_report":
        return (f"{name}'s report for today", str(p.get("text") or "")[:600])
    if kind == "bazar_open":
        msg = str(p.get("message") or "").strip()
        return (name, msg[:300]) if msg else None
    return None


def quick_yes(p: dict[str, Any]) -> bool:
    """v0.864 R4 may this confirm card be answered from the notification? Only a pending card that SAYS it moves no
    money (money is explicitly False), with no amount, no payment method, no PIN, not a demo and not tier 3. Anything
    unsure = no buttons (she opens the app). The tap itself goes through the same route, which checks again."""
    if not isinstance(p, dict) or not p.get("id"):
        return False
    if p.get("status") not in (None, "", "pending") or p.get("result"):
        return False
    if p.get("money") is not False:
        return False
    if str(p.get("amount") or "").strip() or str(p.get("pay_method") or "").strip():
        return False
    if p.get("needs_pin") or p.get("demo") or (p.get("tier") or 0) >= 3:
        return False
    return True


def build(token: str, ev: dict[str, Any], name: str = "Santosh") -> dict[str, Any] | None:
    kind, p = ev["kind"], ev.get("payload") or {}
    data: dict[str, str] = {"kind": kind, "event_id": str(ev.get("id", "")), "at": str(ev.get("at", ""))}
    try:   # v0.648 a notification from a call record opens THAT record when tapped (a chat's opens the app as before)
        from . import callconv
        if ev.get("conv") and callconv.is_call(str(ev["conv"])):
            data["open_conv"] = str(ev["conv"])
    except Exception:
        pass
    ttl = "3600s"
    if kind in RAW_KINDS:
        data["payload"] = json.dumps(p, ensure_ascii=False)[:3000]
        ttl = "600s"
    else:
        shown = render(kind, p, name)
        if shown is None:
            return None
        data["title"], data["body"] = shown[0][:80], shown[1][:900]
    if kind == "bazar_approval" and quick_yes(p):
        data["yes_card"] = str(p["id"])   # v0.864 R4 Yes / Not now on the notification (never for money)
    if kind == "message" and p.get("role") == "assistant" and ev.get("conv") and token != "x":
        try:   # v0.863 R3s the notification carries the same turn result the chat list shows
            from .turnresult import brief
            r = brief(str(ev.get("tenant") or _tenant(str(ev["conv"])) or ""), str(ev["conv"]))
            if r.get("status"):
                data["status"], data["needs_you"] = r["status"], "1" if r["needs_you"] else "0"
        except Exception:
            pass
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


PUSH_KINDS = {"message", "goal", "bazar_approval", "artifact", "pc_file", "photo_made", "blender3d", "notebook_output", "pg_write", "email_draft", "email_new", "email_snooze", "bazar_open", "device_action",
              "home_device", "bt_request", "voice_ring", "employee_ask", "employee_report", "biz_inbox", "operator_ask", "studio_approval", "google_reconnect", "darzi_quote", "darzi_day", "chai_plan", "office_spend", "office_day", "office_note", "lekhak_sign", "mshop_bill", "mshop_day", "gst_day", "gst_return", "payroll_run", "payroll_day", "fin_alert", "voice_alert", "audit_update", "ask_form", "ins_day", "ins_advice", "tele_day", "kalam_publish", "hoola_deal", "seo_week", "seo_alert", "seo_draft", "social_lead", "social_alert", "social_day", "social_week", "hoola_pick", "hoola_khata", "thok_order", "thok_alert", "thok_day", "sheet_milaan", "doc_edit", "niryat_pi", "niryat_day", "ads_change", "ads_report", "hoola_rfq", "hoola_promo", "hoola_mandate", "hoola_dosti", "fr_statement", "fr_day", "a2a_task", "a2a_out", "handoff_reminder", "digilocker", "theka_bill", "theka_letter", "theka_day", "brand_approval", "brand_idea", "site_board", "site_lead", "site_order", "site_launch", "site_live", "site_dns", "site_down", "site_domain", "site_care", "site_ops", "site_github", "app_board", "app_android", "app_ios",
              # v0.133 Seva suite
              "seva_exception", "seva_sla", "seva_ticket", "seva_day", "helpdesk_change", "helpdesk_alert", "helpdesk_escalate", "helpdesk_day", "shikayat_comp", "shikayat_case", "shikayat_alert", "shikayat_day", "aftersales_charge", "aftersales_reminders", "aftersales_visit", "aftersales_day", "feedback_reply", "feedback_alert", "feedback_report", "wapsi_return", "wapsi_refund", "wapsi_day", "samudaay_alert", "samudaay_action", "samudaay_question", "samudaay_join", "samudaay_template", "samudaay_week", "callcentre_script", "callcentre_message", "callcentre_call",
              # v0.137 Tech suite
              "devsahayak_merge", "devsahayak_deploy", "devsahayak_push", "devsahayak_plan", "devsahayak_review", "devsahayak_task", "qa_bug", "qa_export", "qa_run", "itadmin_change", "itadmin_renewal", "itadmin_checklist", "itadmin_review", "itadmin_day", "ispnoc_change", "ispnoc_fault", "ispnoc_alert", "ispnoc_day", "cyber_action", "cyber_alerts", "cyber_incident", "cyber_advisory", "cyber_day", "devops_build", "devops_deploy", "devops_alert", "devops_day", "docwriter_publish", "docwriter_sync", "appreview_handoff", "appreview_alert", "product_publish", "product_day", "product_backlog",
              # v0.139 Safar suite
              "customs_filing", "customs_alert", "customs_day", "travel_booking", "travel_quote", "travel_reminder", "travel_day", "warehouse_adjust", "warehouse_day", "fleet_spend", "fleet_alert", "fleet_day", "courier_card", "courier_parcel", "courier_day", "drivers_alert", "drivers_plan", "drivers_day", "logistics_ewb", "logistics_alert", "logistics_day",
              # v0.144 Makaan suite
              "propagent_card", "propagent_alert", "propagent_day", "rentdesk_approval", "rentdesk_message", "rentdesk_alert", "rentdesk_day", "sitesup_indent", "sitesup_stop", "sitesup_report", "sitesup_alert", "sitesup_day", "interior_quote", "interior_order", "interior_change", "interior_payment", "interior_alert", "interior_day", "archassist_transmittal", "archassist_submission", "archassist_invoice", "archassist_alert", "archassist_day", "society_card", "society_complaint", "society_alert", "society_day",
              # v0.150 Kanoon suite
              "pathyakram_share", "pathyakram_paper", "pathyakram_plan", "guru_report", "daftar_share",   # v0.381 Shiksha suite
              "vakil_card", "vakil_alert", "vakil_day", "legalres_share", "legalres_memo", "compliance_filing", "compliance_cert", "compliance_alert", "compliance_day", "contracts_card", "contracts_alert", "contracts_day", "cosec_filing", "cosec_notice", "cosec_minutes", "cosec_alert", "cosec_day", "notary_print", "notary_alert", "notary_day", "pidesk_share", "pidesk_alert", "dpo_card", "dpo_breach", "dpo_alert", "dpo_day", "dpo_request",
              # v0.152 Mehmaan suite
              "frontoffice_card", "frontoffice_message", "frontoffice_alert", "frontoffice_day", "eventplan_booking", "eventplan_doc", "eventplan_message", "eventplan_spend", "eventplan_alert", "eventplan_day", "shaadi_card", "shaadi_alert", "shaadi_day", "tourguide_card", "tourguide_alert", "tourguide_day", "homestay_card", "homestay_alert", "homestay_day", "banquet_card", "banquet_alert", "banquet_day",
              # v0.156 Kala suite
              "editdesk_card", "editdesk_alert", "editdesk_day", "motiondesk_card", "motiondesk_alert", "motiondesk_day", "filmdesk_card", "filmdesk_alert", "filmdesk_day", "patrakar_card", "patrakar_alert", "patrakar_day", "photoassist_card", "photoassist_alert", "photoassist_day", "graphic_card", "graphic_alert", "graphic_day", "artistmgr_card", "artistmgr_alert", "artistmgr_day", "kitab_card", "kitab_alert", "kitab_day", "podcast_card", "podcast_alert", "podcast_day", "influencer_card", "influencer_alert", "influencer_day", "editdesk_note", "motiondesk_update"}
RAW_KINDS = {"device_action", "home_device", "bt_request", "voice_ring"}   # the phone runs these itself; no notification text (voice_ring: the SERVER calls HER - the native side turns it into the wake: broadcast and the app auto-starts the call; learned in v0.219)


STATS_QUIET: dict[str, int] = {"call_message": 0, "call_card": 0, "night_held": 0, "night_dropped": 0}


def _heard_on_call(conv: str, kind: str) -> bool:
    """v0.646 CHUP NOTIFICATION: she is ON a live call there - she hears the answer, and the call screen shows the
    card. So no phone notification for a reply on a conversation with a live call, and none for a card made by a
    live call's own record. After the call ended, a late result notifies her as before (that IS news)."""
    try:
        import sys as _sys
        v = _sys.modules.get(__package__ + ".voice")
        if v is None or not v.ACTIVE.get(conv):
            return False
        if kind == "message":
            STATS_QUIET["call_message"] += 1
            return True
        from . import callconv
        if callconv.is_call(conv):
            STATS_QUIET["call_card"] += 1
            return True
    except Exception:
        return False
    return False


# wave 13 RAAT KI NEEND: every push went out as Android HIGH priority at any hour - a 2 am routine result, a finished
# job, a desk report or an outage line woke her phone. In her quiet hours (push_quiet, default the ring's 22-8) a push
# that does not need her NOW is held and the newest few go out when the night ends. Never held: a card or ask that
# needs her tap, a site / security / data-breach alarm, her OWN reminder, and anything while she is awake and using
# the app (she wrote in the last 20 minutes).
URGENT_KINDS = {"operator_ask", "bazar_approval", "studio_approval", "ask_form", "employee_ask", "site_down",
                "cyber_incident", "dpo_breach", "google_reconnect"}
_OWN_REMINDER = re.compile(r"^Yaad dila ra(?:ha|hi) hoon:")
_AWAKE: dict[str, float] = {}
_HELD: dict[str, list[dict[str, Any]]] = {}
NIGHT_SEND_MAX = 3


def is_quiet_now(tenant: str) -> bool:
    try:
        from datetime import datetime
        from .life import tz_of
        st = get_settings()
        h = datetime.now(tz_of(tenant)).hour
        a, b = (getattr(st, "push_quiet", "") or st.voice_ring_quiet or "22-8").split("-")[:2]
        a, b = int(a), int(b)
        return (a > b and (h >= a or h < b)) or (a <= b and a <= h < b)
    except Exception:
        return False


def _hold_for_night(tenant: str, ev: dict[str, Any]) -> bool:
    if not getattr(get_settings(), "push_night_hold", True):
        return False
    kind = ev.get("kind")
    if kind in RAW_KINDS or kind in URGENT_KINDS:
        return False
    p = ev.get("payload") or {}
    if kind == "message" and _OWN_REMINDER.match(str(p.get("text") or "")):
        return False
    if time.time() - _AWAKE.get(tenant, 0.0) < 1200:
        return False
    return is_quiet_now(tenant)


def flush_night() -> int:
    """Send what the night held, once the quiet hours are over: the newest few, oldest of them first."""
    sent = 0
    for tenant in list(_HELD):
        if is_quiet_now(tenant):
            continue
        held = _HELD.pop(tenant, [])
        for ev in held[-NIGHT_SEND_MAX:]:
            try:
                _pool.submit(_send, tenant, ev)
                sent += 1
            except RuntimeError:
                pass
        STATS_QUIET["night_dropped"] = STATS_QUIET.get("night_dropped", 0) + max(0, len(held) - NIGHT_SEND_MAX)
    return sent


def on_event(conversation_id: str, ev: dict[str, Any]) -> None:
    """Called for every published event; sends the push in the background (never slows the caller)."""
    if not configured():
        return
    if ev.get("kind") == "message" and (ev.get("payload") or {}).get("role") == "user":
        t = _tenant(conversation_id)
        if t:
            _AWAKE[t] = time.time()     # wave 13: she is awake and using the app - nothing of hers is held
        return
    if ev.get("kind") not in PUSH_KINDS:
        return
    if ev["kind"] not in RAW_KINDS and build("x", ev) is None:
        return
    tenant = _tenant(conversation_id)
    if not tenant:
        return
    if ev["kind"] not in RAW_KINDS and _heard_on_call(conversation_id, ev["kind"]):
        return
    if _hold_for_night(tenant, ev):
        _HELD.setdefault(tenant, []).append(ev)
        del _HELD[tenant][:-30]
        STATS_QUIET["night_held"] = STATS_QUIET.get("night_held", 0) + 1
        return
    if ev["kind"] == "voice_ring" and not _ring_allowed(tenant, conversation_id,
                                                         reminder=bool((ev.get("payload") or {}).get("reminder"))):
        return
    try:
        _pool.submit(_send, tenant, ev)
    except RuntimeError:
        pass


# v0.211 the server-initiated voice ring: a finished job calls HER phone when no call is live. Gated hard in
# code (the phone is not an alarm clock): tenant-tz quiet hours, a small daily budget, and never while a call
# is already live on that chat. Off until v0.219, when the phone's native side learned the kind.
_RING_DAY: dict[str, tuple[str, int]] = {}


_REM_DAY: dict[str, tuple[str, int]] = {}


def _ring_allowed(tenant: str, conv: str, reminder: bool = False) -> bool:
    st = get_settings()
    if not st.voice_ring:
        return False
    if reminder:   # v0.621 her OWN reminder at the time SHE chose: no quiet hours, no job budget - only a sanity cap
        try:
            from . import voice
            if voice.tenant_live(tenant):
                return False
            from datetime import datetime, timezone
            day = datetime.now(timezone.utc).strftime("%Y%m%d")
            prev_day, n = _REM_DAY.get(tenant, ("", 0))
            n = n + 1 if prev_day == day else 1
            if n > max(1, st.voice_ring_reminder_max_day):
                return False
            _REM_DAY[tenant] = (day, n)
            return True
        except Exception:
            return False
    try:   # a live call on this chat would hear the phone ring for nothing
        from . import voice
        if voice.ACTIVE.get(conv):
            return False
    except Exception:
        pass
    try:
        from datetime import datetime, timezone
        from .life import tz_of
        h = datetime.now(tz_of(tenant)).hour
        a, b = (st.voice_ring_quiet or "22-8").split("-")[:2]
        a, b = int(a), int(b)
        if (a > b and (h >= a or h < b)) or (a <= b and a <= h < b):
            return False                      # inside the quiet hours
        day = datetime.now(timezone.utc).strftime("%Y%m%d")
        prev_day, n = _RING_DAY.get(tenant, ("", 0))
        n = n + 1 if prev_day == day else 1
        if n > max(1, st.voice_ring_max_day):
            return False
        _RING_DAY[tenant] = (day, n)
    except Exception:
        return False
    return True
