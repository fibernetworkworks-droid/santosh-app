"""Santosh's email work: reading, sorting, organising, attachments, sending approved drafts, scheduled send,
follow-up reminders and bulk mail. Blocking functions; the agent tools and API run them in a thread.

Ids handed to the model are "<mailbox key>~<provider id>" so several mailboxes can be used side by side.
Sending, deleting and bulk mail only ever happen after the user's tap (draft card / Bazar approval card).
"""
from __future__ import annotations

import email.utils
import logging
import mimetypes
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from ..config import get_settings
from ..db import (BulkMail, BulkRecipient, EmailDraft, MailWatch, PcFile, Profile, as_utc, now, session)
from ..events import bus, notify
from . import contacts, mime
from .accounts import get_box, mark_error
from .base import Box, MailError, NotConnected

log = logging.getLogger("santosh.mailbox")

OTP_RE = re.compile(r"\b(otp|one[- ]time password|verification code|security code|login code|sign[- ]in|"
                    r"new login|security alert|password reset)\b", re.I)
BILL_RE = re.compile(r"\b(invoice|bill|payment|due date|statement|receipt|gst|tax invoice|amount (payable|due)|"
                     r"emi|premium|renewal|overdue|outstanding)\b|₹|\brs\.?\s?\d|\binr\s?\d", re.I)
ASK_RE = re.compile(r"\?|\b(please|kindly|request|confirm|urgent|asap|reply|revert|let me know|could you|can you|"
                    r"quotation|quote|meeting|call me|kripya|bataiye|batayein|bhejiye|bhej do|chahiye|jaldi)\b", re.I)


# ---------------- ids ----------------
def make_ref(box: Box, native: str) -> str:
    return f"{box.key}~{native}"


def split_ref(tenant: str, ref: str) -> tuple[Box, str]:
    ref = str(ref or "").strip()
    if "~" in ref:
        key, native = ref.split("~", 1)
        return get_box(tenant, key), native
    return get_box(tenant), ref


def _guard(box: Box, fn):
    try:
        return fn()
    except NotConnected:
        raise
    except MailError as e:
        if "login" in str(e).lower() or "expire" in str(e).lower():
            mark_error(box.key, str(e))
        raise


# ---------------- reading ----------------
def _public(box: Box, item: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in item.items() if not k.startswith("_")}
    out["id"] = make_ref(box, item["id"])
    out["account"] = box.address
    return out


def check(tenant: str, folder: str = "inbox", unread_only: bool = False, search: str | None = None, limit: int = 10,
          account: str | None = None, since: datetime | None = None, snippets: bool = True) -> dict[str, Any]:
    box = get_box(tenant, account)
    items = _guard(box, lambda: box.list(folder or "inbox", unread_only, search, limit, since, snippets))
    contacts.learn(tenant, [(i.get("from", ""), i.get("from_email", "")) for i in items if not i.get("bulk")], 0.2)
    return {"account": box.address, "folder": folder or "inbox", "count": len(items),
            "emails": [_public(box, i) for i in items]}


def read(tenant: str, ref: str, mark_seen: bool = True) -> dict[str, Any]:
    box, native = split_ref(tenant, ref)
    raw = _guard(box, lambda: box.raw(native))
    out = mime.parse(raw)
    out["id"] = make_ref(box, native)
    out["account"] = box.address
    try:
        out["thread_id"] = box.thread_of(native) if box.kind in ("gmail", "outlook") else ""
    except MailError:
        out["thread_id"] = ""
    if mark_seen:
        try:
            box.mark([native], True)
        except MailError:
            pass
    people = [(out["from"], out["from_email"])] + mime.addr_list(out.get("to")) + mime.addr_list(out.get("cc"))
    contacts.learn(tenant, [p for p in people if p[1] != box.address], 0.3 if not out.get("bulk") else 0)
    return out


def attachment(tenant: str, ref: str, att_id: str) -> tuple[str, str, bytes]:
    box, native = split_ref(tenant, ref)
    raw = _guard(box, lambda: box.raw(native))
    try:
        return mime.get_attachment(raw, str(att_id))
    except KeyError:
        raise MailError("Is email mein yeh attachment nahi mila. email_read se attachment id dekhiye.")


def _by_box(tenant: str, refs: list[str]) -> dict[str, tuple[Box, list[str]]]:
    groups: dict[str, tuple[Box, list[str]]] = {}
    for r in refs:
        box, native = split_ref(tenant, r)
        groups.setdefault(box.key, (box, []))[1].append(native)
    return groups


ACTIONS = ("archive", "mark_read", "mark_unread", "star", "unstar", "move", "spam", "not_spam")


def act(tenant: str, refs: list[str], action: str, folder: str = "") -> dict[str, Any]:
    if action not in ACTIONS:
        raise MailError(f"action must be one of {', '.join(ACTIONS)} (deleting goes through email_delete)")
    if not refs:
        raise MailError("Kaunsi emails? ids do (email_check se).")
    if action == "move" and not folder:
        raise MailError("Kis folder/label mein?")
    for box, natives in _by_box(tenant, refs).values():
        def go(box=box, natives=natives):
            if action == "archive":
                box.archive(natives)
            elif action in ("mark_read", "mark_unread"):
                box.mark(natives, action == "mark_read")
            elif action in ("star", "unstar"):
                box.star(natives, action == "star")
            elif action == "spam":
                box.move(natives, "spam")
            elif action == "not_spam":
                box.move(natives, "inbox")
            else:
                box.move(natives, folder)
        _guard(box, go)
    return {"done": action, "count": len(refs), "folder": folder or None}


def trash(tenant: str, refs: list[str]) -> int:
    for box, natives in _by_box(tenant, refs).values():
        _guard(box, lambda box=box, natives=natives: box.trash(natives))
    return len(refs)


def folders(tenant: str, account: str | None = None) -> list[str]:
    box = get_box(tenant, account)
    return _guard(box, box.folders)


# ---------------- sorting the inbox ----------------
def classify(item: dict[str, Any], known: set[str]) -> tuple[str, str]:
    text = f"{item.get('subject', '')} {item.get('snippet', '')}"
    sender = item.get("from_email", "")
    if OTP_RE.search(text):
        return "otp_alerts", "login / OTP / security alert"
    if BILL_RE.search(text) and (item.get("bulk") or mime.is_automated(sender) or "invoice" in text.lower() or "bill" in text.lower()):
        return "bills_payments", "bill, invoice or payment"
    if item.get("bulk") or mime.is_automated(sender):
        return "newsletters_updates", "newsletter / promotion / automatic update"
    if sender in known:
        return "needs_reply", "from someone you email with"
    if ASK_RE.search(text):
        return "needs_reply", "asks something or requests action"
    if BILL_RE.search(text):
        return "bills_payments", "mentions a payment"
    return "other", "personal mail"


def triage(tenant: str, hours: int = 24, limit: int = 40, account: str | None = None, unread_only: bool = True) -> dict[str, Any]:
    since = now() - timedelta(hours=max(1, min(int(hours or 24), 24 * 14)))
    box = get_box(tenant, account)
    items = _guard(box, lambda: box.list("inbox", unread_only, None, max(5, min(int(limit or 40), 50)), since, True))
    with session() as s:
        from ..db import MailContact
        known = set(s.scalars(select(MailContact.email).where(MailContact.tenant_id == tenant, MailContact.sent_to > 0)).all())
    groups: dict[str, list] = {"needs_reply": [], "bills_payments": [], "otp_alerts": [], "other": [], "newsletters_updates": []}
    for it in items:
        cat, why = classify(it, known)
        pub = _public(box, it)
        pub["why"] = why
        if cat == "otp_alerts":
            pub["snippet"] = re.sub(r"\b\d{4,8}\b", "••••", pub.get("snippet", ""))   # never read codes out
        groups[cat].append(pub)
    counts = {k: len(v) for k, v in groups.items()}
    for k in ("newsletters_updates",):
        groups[k] = [{"id": i["id"], "from": i["from"], "subject": i["subject"]} for i in groups[k][:15]]
    return {"account": box.address, "hours": hours, "unread_only": unread_only, "total": len(items), "counts": counts,
            "groups": groups,
            "note": "Lead with needs_reply and bills. Never read out OTPs or codes. Offer: reply drafts, archive the "
                    "newsletters (email_action archive), follow-up reminders."}


# ---------------- attachments for outgoing mail ----------------
def _file_row(tenant: str, file_id: str) -> PcFile:
    with session() as s:
        f = s.get(PcFile, file_id)
        if f is None or f.tenant_id != tenant:
            raise MailError(f"File {file_id} nahi mili (files 24 ghante baad hat jaati hain).")
        s.expunge(f)
        return f


def describe_attachments(tenant: str, refs: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Check each attachment the model asked for and fill in its real name and size (server-side, not model text)."""
    out = []
    for a in refs or []:
        if not isinstance(a, dict):
            raise MailError("attachments: each item is an object like {email_id, attachment_id} / {file_id} / {artifact_id}")
        if a.get("email_id"):
            msg = read(tenant, str(a["email_id"]), mark_seen=False)
            att = next((x for x in msg["attachments"] if x["id"] == str(a.get("attachment_id", ""))), None)
            if att is None and len(msg["attachments"]) == 1 and not a.get("attachment_id"):
                att = msg["attachments"][0]
            if att is None:
                raise MailError(f"Email {a['email_id']} mein attachment {a.get('attachment_id')} nahi mila. "
                                f"Attachments: {[(x['id'], x['name']) for x in msg['attachments']]}")
            out.append({"type": "email", "email_id": msg["id"], "attachment_id": att["id"], "name": att["name"],
                        "size": att["size"], "mime": att["mime"]})
        elif a.get("file_id"):
            f = _file_row(tenant, str(a["file_id"]))
            out.append({"type": "file", "file_id": f.id, "name": f.name, "size": f.size,
                        "mime": mimetypes.guess_type(f.name)[0] or "application/octet-stream"})
        elif a.get("artifact_id"):
            from .. import artifacts
            art = artifacts.get(tenant, str(a["artifact_id"]))
            if art is None or not art.version:
                raise MailError("Woh Santosh page (artifact) nahi mila ya abhi ban raha hai.")
            name = re.sub(r"[^\w\- ]+", "", art.title).strip() or "santosh-page"
            out.append({"type": "artifact", "artifact_id": art.id, "name": f"{name}.html", "size": 0, "mime": "text/html"})
        else:
            raise MailError("attachments: use {email_id, attachment_id}, {file_id} or {artifact_id}")
    cap = get_settings().mail_max_attach_mb * 1024 * 1024
    if sum(int(x.get("size") or 0) for x in out) > cap:
        raise MailError(f"Attachments {get_settings().mail_max_attach_mb} MB se bade hain; email itna bada nahi ja sakta. "
                        "Badi file ke liye Drive link bhejiye.")
    return out


def load_files(tenant: str, refs: list[dict[str, Any]] | None) -> list[tuple[str, str, bytes]]:
    files = []
    for a in refs or []:
        t = a.get("type")
        if t == "email":
            name, mtype, data = attachment(tenant, a["email_id"], a["attachment_id"])
            files.append((a.get("name") or name, mtype, data))
        elif t == "file":
            f = _file_row(tenant, a["file_id"])
            p = Path(f.stored_path)
            if not p.exists():
                raise MailError(f"{f.name} ab server par nahi hai (files 24 ghante baad hat jaati hain). Dobara bhejiye.")
            files.append((f.name, a.get("mime") or "application/octet-stream", p.read_bytes()))
        elif t == "artifact":
            from .. import artifacts
            html = artifacts.latest_html(a["artifact_id"])
            if not html:
                raise MailError("Santosh page nahi mila")
            files.append((a["name"], "text/html", html.encode("utf-8")))
    cap = get_settings().mail_max_attach_mb * 1024 * 1024
    if sum(len(d) for _, _, d in files) > cap:
        raise MailError(f"Attachments {get_settings().mail_max_attach_mb} MB se bade hain.")
    return files


# ---------------- sending ----------------
def sender_name(tenant: str, box: Box) -> str:
    if box.name:
        return box.name
    with session() as s:
        p = s.get(Profile, tenant)
        if p and p.name:
            return p.name
    return box.address.split("@")[0]


def _tz(tenant: str):
    from ..life import tz_of
    try:
        return tz_of(tenant)
    except Exception:
        return timezone(timedelta(hours=5, minutes=30))


def draft_view(d: EmailDraft) -> dict[str, Any]:
    tz = _tz(d.tenant_id)
    send_at = as_utc(d.send_at)
    return {"id": d.id, "to": d.to_addr, "cc": d.cc_addr, "bcc": d.bcc_addr or "", "subject": d.subject, "body": d.body,
            "status": d.status, "error": d.error, "account": d.account or "", "kind": d.kind or "new",
            "attachments": [{k: v for k, v in a.items() if k in ("name", "size", "type")} for a in (d.attachments or [])],
            "send_at": send_at.isoformat() if send_at else None,
            "send_at_label": send_at.astimezone(tz).strftime("%d %b, %I:%M %p") if send_at else None,
            "follow_up_days": d.follow_up_days}


def send_draft(tenant: str, draft_id: str, edits: dict[str, Any] | None = None, from_worker: bool = False) -> dict[str, Any]:
    """The user tapped Bhejo (or a scheduled time came). Sends now, or schedules if send_at is still ahead."""
    with session() as s:
        d = s.get(EmailDraft, draft_id)
        if d is None or d.tenant_id != tenant:
            raise LookupError("Draft not found")
        if d.status in ("sent", "sending"):
            return {"status": d.status, "already": True}      # a double tap never sends twice
        if d.status == "cancelled":
            raise MailError("Yeh draft cancel ho chuka hai.")
        for k, col in (("to", "to_addr"), ("cc", "cc_addr"), ("bcc", "bcc_addr"), ("subject", "subject"), ("body", "body")):
            if edits and edits.get(k) is not None:
                setattr(d, col, str(edits[k]).strip()[:1000] if k != "body" else str(edits[k]))
        if edits and "send_at" in edits:
            d.send_at = edits["send_at"]
        to_addr, cc, bcc, subject, body = d.to_addr, d.cc_addr or "", d.bcc_addr or "", d.subject, d.body
        send_at = as_utc(d.send_at)
        scheduled = bool(send_at and send_at > now() + timedelta(seconds=30) and not from_worker)
        if scheduled:
            d.status = "scheduled"
            s.flush()
            view, conv = draft_view(d), d.conversation_id
    if scheduled:
        bus.publish(conv, "email_sent", view)
        return {"status": "scheduled", "send_at": send_at.isoformat()}
    with session() as s:
        d = s.get(EmailDraft, draft_id)
        if d.status in ("sent", "sending"):
            return {"status": d.status, "already": True}
        d.status = "sending"
        irt, refs, conv, account, thread_id = d.in_reply_to, d.references, d.conversation_id, d.account, d.thread_id
        atts, follow = list(d.attachments or []), d.follow_up_days
    try:
        for a in [x for x in (to_addr + "," + cc + "," + bcc).split(",") if x.strip()]:
            if not contacts.valid(email.utils.parseaddr(a)[1]):
                raise MailError(f"'{a.strip()}' sahi email address nahi hai")
        box = get_box(tenant, account or None)
        files = load_files(tenant, atts)
        msg = mime.build(from_addr=box.address, from_name=sender_name(tenant, box), to=to_addr, cc=cc, bcc=bcc,
                         subject=subject, body=body, in_reply_to=irt, references=refs, files=files)
        sent = _guard(box, lambda: box.send(msg, thread_id or None))
    except (MailError, NotConnected) as e:
        with session() as s:
            d = s.get(EmailDraft, draft_id)
            d.status, d.error = "failed", str(e)
            view = draft_view(d)
        bus.publish(conv, "email_sent", view)
        raise
    with session() as s:
        d = s.get(EmailDraft, draft_id)
        d.status, d.sent_at, d.error = "sent", now(), None
        d.sent_message_id = sent.get("message_id")
        d.account = box.key
        view = draft_view(d)
    bus.publish(conv, "email_sent", view)
    people = mime.addr_list(to_addr) + mime.addr_list(cc) + mime.addr_list(bcc)
    contacts.learn(tenant, people, 1.0, sent=True)
    if follow:
        add_watch(tenant, conv, box, "their_reply", sent.get("message_id", ""), sent.get("thread_id") or thread_id or "",
                  subject, to_addr, int(follow))
    extra = f" ({len(atts)} attachment)" if atts else ""
    notify(conv, f"Email bhej diya: {to_addr} ko \"{subject}\"{extra}." +
           (f" {follow} din mein jawab nahi aaya to yaad dilaunga." if follow else ""))
    return {"status": "sent", "to": to_addr, "message_id": sent.get("message_id")}


def send_due_scheduled() -> int:
    with session() as s:
        due = [(d.tenant_id, d.id) for d in s.scalars(select(EmailDraft).where(
            EmailDraft.status == "scheduled", EmailDraft.send_at <= now())).all()]
    n = 0
    for tenant, did in due:
        try:
            send_draft(tenant, did, from_worker=True)
            n += 1
        except Exception as e:
            log.warning("scheduled mail %s failed: %s", did, e)
            with session() as s:
                d = s.get(EmailDraft, did)
                conv = d.conversation_id if d else ""
            if conv:
                notify(conv, f"Scheduled email nahi ja paya: {e}. Chat mein email card par 'Phir bhejo' dabaiye.")
    return n


# ---------------- follow-ups ----------------
def add_watch(tenant: str, conv: str, box: Box, mode: str, message_id: str, thread_id: str, subject: str, peer: str,
              days: float, email_ref: str = "", since: datetime | None = None) -> dict[str, Any]:
    days = max(0.04, min(float(days or 3), 60))
    with session() as s:
        w = MailWatch(tenant_id=tenant, conversation_id=conv, account=box.key, mode=mode, message_id=message_id or "",
                      thread_id=thread_id or "", subject=subject[:500], peer=peer[:320], email_ref=email_ref,
                      since=since or now(), due_at=now() + timedelta(days=days))
        s.add(w)
        s.flush()
        return watch_view(w)


def watch_view(w: MailWatch) -> dict[str, Any]:
    tz = _tz(w.tenant_id)
    return {"id": w.id, "mode": w.mode, "subject": w.subject, "peer": w.peer, "status": w.status,
            "due": as_utc(w.due_at).astimezone(tz).strftime("%d %b, %I:%M %p")}


def watches(tenant: str) -> list[dict[str, Any]]:
    with session() as s:
        return [watch_view(w) for w in s.scalars(select(MailWatch).where(MailWatch.tenant_id == tenant,
                                                                          MailWatch.status == "waiting")
                                                 .order_by(MailWatch.due_at)).all()]


def cancel_watch(tenant: str, wid: str) -> bool:
    with session() as s:
        w = s.get(MailWatch, wid)
        if w is None or w.tenant_id != tenant:
            return False
        w.status = "cancelled"
        return True


def check_watches(limit: int = 30) -> int:
    with session() as s:
        due = [(w.id, w.tenant_id, w.account, w.mode, w.message_id, w.thread_id, as_utc(w.since), w.subject, w.peer,
                w.conversation_id, w.email_ref)
               for w in s.scalars(select(MailWatch).where(MailWatch.status == "waiting", MailWatch.due_at <= now())
                                  .order_by(MailWatch.due_at).limit(limit)).all()]
    n = 0
    for wid, tenant, account, mode, mid, tid, since, subject, peer, conv, ref in due:
        try:
            box = get_box(tenant, account or None)
            res = box.replies(mid, tid, since)
        except Exception as e:
            log.warning("watch %s check failed: %s", wid, e)
            with session() as s:     # try again in an hour, give up after a day of errors
                w = s.get(MailWatch, wid)
                w.due_at = now() + timedelta(hours=1)
                if as_utc(w.created_at) < now() - timedelta(days=90):
                    w.status = "cancelled"
            continue
        answered = res["from_them"] if mode == "their_reply" else res["from_me"]
        with session() as s:
            w = s.get(MailWatch, wid)
            w.status = "replied" if answered else "reminded"
        if not answered and conv:
            who = peer.split(",")[0].strip() or "unhone"
            if mode == "their_reply":
                notify(conv, f"Follow-up: {who} ne \"{subject}\" ka abhi tak jawab nahi diya. Ek follow-up email likh doon?")
            else:
                notify(conv, f"Yaad dila raha hoon: {who} ki email \"{subject}\" ka jawab abhi baaki hai. Jawab likh doon?"
                             + (f" (email id {ref})" if ref else ""))
            n += 1
    return n


# ---------------- bulk mail ----------------
PLACEHOLDER = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")


def _norm(k: Any) -> str:
    return re.sub(r"\s+", " ", str(k or "")).strip().lower()


def render(tpl: str, fields: dict[str, Any]) -> str:
    return PLACEHOLDER.sub(lambda m: str(fields.get(_norm(m.group(1)), "")).strip(), tpl)


def table_from_rows(rows: list[list[Any]], email_column: str = "", name_column: str = "") -> list[dict[str, Any]]:
    """Header row + data rows -> [{email, name, fields}] (fields keyed by lowercased header)."""
    if not rows:
        raise MailError("List khaali hai.")
    header = [_norm(h) or f"col{i + 1}" for i, h in enumerate(rows[0])]
    data = rows[1:]
    ecol = None
    if email_column:
        ecol = header.index(_norm(email_column)) if _norm(email_column) in header else None
        if ecol is None:
            raise MailError(f"'{email_column}' column nahi mila. Columns: {', '.join(header)}")
    if ecol is None:
        for i, h in enumerate(header):
            if re.search(r"e-?mail|mail id|email id", h):
                ecol = i
                break
    if ecol is None:   # no header naming it: the column whose values look like emails
        for i in range(len(header)):
            vals = [str(r[i]) for r in data[:20] if i < len(r) and str(r[i]).strip()]
            if vals and sum(contacts.valid(v) for v in vals) >= max(1, len(vals) // 2):
                ecol = i
                break
    if ecol is None:
        raise MailError(f"Email wala column nahi mila. Columns: {', '.join(header)}. email_column bataiye.")
    ncol = header.index(_norm(name_column)) if name_column and _norm(name_column) in header else None
    if ncol is None:
        for i, h in enumerate(header):
            if i != ecol and re.search(r"\b(name|naam|customer|contact|client|party)\b", h):
                ncol = i
                break
    out = []
    for r in data:
        cells = list(r) + [""] * (len(header) - len(r))
        addr_ = str(cells[ecol]).strip()
        fields = {header[i]: ("" if cells[i] is None else str(cells[i]).strip()) for i in range(len(header))}
        name = fields.get(header[ncol], "") if ncol is not None else ""
        fields.setdefault("name", name)
        out.append({"email": addr_, "name": name, "fields": fields})
    return out


def rows_from_source(tenant: str, source: dict[str, Any]) -> tuple[list[list[Any]], str]:
    if source.get("rows"):
        rows = source["rows"]
        if rows and isinstance(rows[0], dict):
            keys = list(rows[0].keys())
            return [keys] + [[r.get(k, "") for k in keys] for r in rows], "list from chat"
        return rows, "list from chat"
    if source.get("email_id"):
        name, mtype, data = attachment(tenant, source["email_id"], str(source.get("attachment_id") or "0"))
        return mime.table_rows(name, data), name
    if source.get("file_id"):
        f = _file_row(tenant, source["file_id"])
        return mime.table_rows(f.name, Path(f.stored_path).read_bytes()), f.name
    if source.get("lead_list_id"):
        from ..db import Lead, LeadList
        with session() as s:
            ll = s.get(LeadList, source["lead_list_id"])
            if ll is None or ll.tenant_id != tenant:
                raise MailError("Contact list nahi mili")
            leads = s.scalars(select(Lead).where(Lead.list_id == ll.id)).all()
            keys = sorted({k for ld in leads for k in (ld.extra or {}).keys()})
            rows = [["name", *keys]] + [[ld.name or "", *[(ld.extra or {}).get(k, "") for k in keys]] for ld in leads]
            return rows, ll.name
    raise MailError("recipients ka source do: rows, email_id+attachment_id (Excel/CSV), file_id ya lead_list_id")


def create_bulk(tenant: str, conv: str, subject: str, body: str, source: dict[str, Any], email_column: str = "",
                name_column: str = "", account: str | None = None, attachments: list | None = None) -> dict[str, Any]:
    st = get_settings()
    box = get_box(tenant, account)
    rows, src_name = rows_from_source(tenant, source)
    people = table_from_rows(rows, email_column, name_column)
    seen, good, bad = set(), [], []
    for p in people:
        a = p["email"].lower()
        if not contacts.valid(a):
            if a:
                bad.append(a)
            continue
        if a in seen:
            continue
        seen.add(a)
        p["email"] = a
        good.append(p)
    if not good:
        raise MailError("List mein ek bhi sahi email address nahi mila.")
    if len(good) > st.mail_bulk_max:
        raise MailError(f"Ek baar mein zyada se zyada {st.mail_bulk_max} logon ko. List mein {len(good)} hain.")
    keys = set(good[0]["fields"].keys()) | {"name", "email"}
    unknown = sorted({_norm(m) for m in PLACEHOLDER.findall(subject + body)} - keys)
    if unknown:
        raise MailError(f"Template mein {{{{{', '.join(unknown)}}}}} hai par list mein yeh column nahi. Columns: {', '.join(sorted(keys))}")
    files = describe_attachments(tenant, attachments)
    sig = box.signature.strip()
    if sig and sig not in body:
        body = body.rstrip() + "\n\n" + sig
    with session() as s:
        b = BulkMail(tenant_id=tenant, conversation_id=conv, account=box.key, subject=subject[:500], body=body,
                     attachments=files or None, source=src_name[:300], total=len(good))
        s.add(b)
        s.flush()
        for p in good:
            f = dict(p["fields"])
            f["email"] = p["email"]
            s.add(BulkRecipient(bulk_id=b.id, email=p["email"], name=p["name"][:200], fields=f))
        bid = b.id
    sample = good[0]["fields"] | {"email": good[0]["email"]}
    return {"bulk_id": bid, "account": box.address, "recipients": len(good), "invalid_skipped": len(bad),
            "invalid_examples": bad[:5], "source": src_name, "sample_to": good[0]["email"],
            "sample_subject": render(subject, sample), "sample_body": render(body, sample)[:1500],
            "attachments": [a["name"] for a in files],
            "minutes_needed": round(len(good) / max(1, st.mail_bulk_per_minute))}


def bulk_view(tenant: str, bid: str) -> dict[str, Any] | None:
    with session() as s:
        b = s.get(BulkMail, bid)
        if b is None or b.tenant_id != tenant:
            return None
        first = s.scalars(select(BulkRecipient).where(BulkRecipient.bulk_id == bid).order_by(BulkRecipient.id).limit(3)).all()
        return {"id": b.id, "status": b.status, "subject": b.subject, "body": b.body, "total": b.total, "sent": b.sent,
                "failed": b.failed, "account": b.account, "source": b.source,
                "attachments": [a["name"] for a in (b.attachments or [])],
                "first": [{"email": r.email, "fields": r.fields} for r in first]}


def start_bulk(tenant: str, bid: str) -> dict[str, Any]:
    with session() as s:
        b = s.get(BulkMail, bid)
        if b is None or b.tenant_id != tenant:
            raise MailError("Bulk mail nahi mila")
        if b.status != "pending":
            return {"status": b.status}
        b.status = "sending"
        conv, total = b.conversation_id, b.total
    st = get_settings()
    notify(conv, f"{total} logon ko email bhejna shuru. Har minute ~{st.mail_bulk_per_minute}; khatam hone par report dunga.")
    return {"status": "sending", "total": total}


def cancel_bulk(tenant: str, bid: str) -> bool:
    with session() as s:
        b = s.get(BulkMail, bid)
        if b is None or b.tenant_id != tenant or b.status not in ("pending", "sending"):
            return False
        b.status = "cancelled"
        return True


_bulk_last: dict[str, float] = {}


def _sent_today(account: str) -> int:
    with session() as s:
        return s.scalar(select(func.count()).select_from(BulkRecipient).join(BulkMail, BulkMail.id == BulkRecipient.bulk_id)
                        .where(BulkMail.account == account, BulkRecipient.status == "sent",
                               BulkRecipient.sent_at >= now() - timedelta(hours=24))) or 0


def bulk_tick() -> int:
    """Send the next mail of each running bulk job, at the configured pace."""
    st = get_settings()
    gap = 60.0 / max(1, st.mail_bulk_per_minute)
    with session() as s:
        jobs = [(b.id, b.tenant_id, b.account, b.subject, b.body, list(b.attachments or []), b.conversation_id)
                for b in s.scalars(select(BulkMail).where(BulkMail.status == "sending")).all()]
    n = 0
    for bid, tenant, account, subject, body, atts, conv in jobs:
        if time.time() - _bulk_last.get(bid, 0) < gap:
            continue
        with session() as s:
            r = s.scalars(select(BulkRecipient).where(BulkRecipient.bulk_id == bid, BulkRecipient.status == "queued")
                          .order_by(BulkRecipient.id).limit(1)).first()
            rid = r.id if r else None
            to, fields = (r.email, dict(r.fields or {})) if r else ("", {})
        if rid is None:
            _finish_bulk(bid)
            continue
        if _sent_today(account) >= st.mail_bulk_daily_cap:
            if _bulk_last.get(bid + ":cap", 0) < time.time() - 3600:
                _bulk_last[bid + ":cap"] = time.time()
                notify(conv, f"Aaj ki email limit ({st.mail_bulk_daily_cap}) poori. Baaki mails kal apne aap jayengi.")
            continue
        _bulk_last[bid] = time.time()
        try:
            box = get_box(tenant, account or None)
            files = load_files(tenant, atts)
            msg = mime.build(from_addr=box.address, from_name=sender_name(tenant, box), to=to,
                             subject=render(subject, fields), body=render(body, fields), files=files)
            box.send(msg)
            ok, err = True, ""
        except Exception as e:
            ok, err = False, str(e)[:500]
            if isinstance(e, (NotConnected,)) or "login" in err.lower():
                with session() as s:   # mailbox broken: pause, don't burn the whole list
                    b = s.get(BulkMail, bid)
                    b.status = "cancelled"
                notify(conv, f"Bulk email ruk gaya: {err}. Mailbox theek karke dobara boliye.")
        with session() as s:
            r = s.get(BulkRecipient, rid)
            r.status, r.error, r.sent_at = ("sent" if ok else "failed"), err, now()
            b = s.get(BulkMail, bid)
            if ok:
                b.sent += 1
            else:
                b.failed += 1
        if ok:
            contacts.learn(tenant, [(fields.get("name", ""), to)], 0.5, sent=True)
        n += 1
    return n


def _finish_bulk(bid: str) -> None:
    with session() as s:
        b = s.get(BulkMail, bid)
        if b.status != "sending":
            return
        b.status, b.finished_at = "done", now()
        conv, sent, failed, subject = b.conversation_id, b.sent, b.failed, b.subject
        bad = [f"{r.email} ({r.error[:60]})" for r in s.scalars(select(BulkRecipient).where(
            BulkRecipient.bulk_id == bid, BulkRecipient.status == "failed").limit(5)).all()]
    text = f"Bulk email \"{subject}\" poora: {sent} ko gaya" + (f", {failed} fail" if failed else "") + "."
    if bad:
        text += " Fail: " + "; ".join(bad)
    notify(conv, text)
    bus.publish(conv, "bulk_mail", {"id": bid, "status": "done", "sent": sent, "failed": failed})


# ---------------- files for the phone / PC ----------------
def store_bytes(tenant: str, name: str, data: bytes, direction: str = "to_phone") -> PcFile:
    import hashlib
    from ..db import new_id
    from ..pc.service import files_dir, safe_name
    fid = new_id("file")
    path = files_dir() / fid
    path.write_bytes(data)
    with session() as s:
        row = PcFile(id=fid, tenant_id=tenant, device_id="", direction=direction, name=safe_name(name), size=len(data),
                     sha256=hashlib.sha256(data).hexdigest(), stored_path=str(path))
        s.add(row)
        s.flush()
        s.expunge(row)
    return row
