"""G6 of docs/SUPPORT_GLOBAL_PLAN.md: her support email address in the one support desk.

- IN: her own mailbox read over IMAP (any provider: Gmail / Microsoft 365 / Zoho with an app password, or her host's
  mail), and / or a Hoola forwarding address support-<code>@<HOOLA_MAIL_DOMAIN> she forwards her support mail to (the
  owner's email worker posts it, signed - agentmail.py hands it here).
- OUT: her own mailbox over SMTP, from HER address, in the same thread (Re: subject, In-Reply-To, References), her
  signature under every mail, the ticket number in the subject so a reply finds its ticket.
- THREADS: a reply finds its ticket by the [T-1001] in the subject or by Hoola's own Message-ID it answers. A reply on an
  open ticket goes onto that ticket for the person working it (Hoola answers it only when it is "did this fix it?" or a
  rating); a new mail goes through the answer engine like every channel (answer / hand-over / ticket).
- SAFETY: auto-replies, mailing lists, bounces and her own address are never answered (no mail loops), at most a few
  answers an hour to one address, attachments kept (PDF / pictures / documents, 10 MB) with a PDF's text noted on the
  ticket, the mail's words are data, never instructions, her password sealed and never shown.
Not built: a direct Google / Microsoft sign-in for the support mailbox (use an app password, or forwarding).
"""
from __future__ import annotations

import email
import email.utils
import imaplib
import json
import logging
import re
import secrets
import smtplib
import ssl
import time
from collections import defaultdict, deque
from datetime import timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select

from ..db import new_id, session

log = logging.getLogger(__name__)

UPLOADS = Path("data") / "seva_uploads"
MAX_FILE = 10 * 1024 * 1024
PER_HOUR = 5                                   # answers to one address an hour (a loop stops here)
POLL_EVERY = 120                               # seconds between IMAP reads
TAG = re.compile(r"\[([A-Z]{1,6}-\d{1,9})\]")
MID = re.compile(r"seva\.([A-Z]{1,6}-\d{1,9})\.")
BOUNCE = re.compile(r"^(mailer-daemon|postmaster|no-?reply|do-?not-?reply|bounce)", re.I)
QUOTE_START = re.compile(r"^(on .{4,200} wrote:|-{2,}\s*original message\s*-{2,}|from:\s.+@.+|_{5,})\s*$", re.I)
_SENT: dict[str, deque] = defaultdict(deque)


class MailError(Exception):
    pass


def _CH():
    from . import channels as CH
    return CH


def _S():
    from . import service as S
    return S


# ---------------------------------------------------------------- the outside (tests swap these)
def _imap_fetch(k: dict, since_uid: int) -> tuple[list[tuple[int, bytes]], int]:
    """New mails in INBOX with a UID above since_uid -> ([(uid, raw)], highest uid). Marks them read."""
    M = imaplib.IMAP4_SSL(k["imap_host"], int(k.get("imap_port") or 993), ssl_context=ssl.create_default_context())
    try:
        M.login(k["user"], k["password"])
        M.select("INBOX")
        typ, data = M.uid("search", None, f"UID {since_uid + 1}:*")
        uids = [int(x) for x in (data[0] or b"").split() if int(x) > since_uid][:50]
        out = []
        for u in uids:
            typ, d = M.uid("fetch", str(u), "(RFC822)")
            raw = next((x[1] for x in d if isinstance(x, tuple)), b"")
            if raw:
                out.append((u, raw))
            M.uid("store", str(u), "+FLAGS", "(\\Seen)")
        return out, max([since_uid] + uids)
    finally:
        try:
            M.logout()
        except Exception:   # noqa: BLE001
            pass


def _imap_check(k: dict) -> int:
    """Log in, read the highest UID (so only mail from now on is answered)."""
    M = imaplib.IMAP4_SSL(k["imap_host"], int(k.get("imap_port") or 993), ssl_context=ssl.create_default_context())
    try:
        M.login(k["user"], k["password"])
        M.select("INBOX")
        typ, data = M.uid("search", None, "ALL")
        uids = [int(x) for x in (data[0] or b"").split()]
        return max(uids) if uids else 0
    finally:
        try:
            M.logout()
        except Exception:   # noqa: BLE001
            pass


def _smtp_send(k: dict, msg) -> None:
    port = int(k.get("smtp_port") or 465)
    if port == 465:
        with smtplib.SMTP_SSL(k["smtp_host"], port, context=ssl.create_default_context(), timeout=30) as s:
            s.login(k.get("smtp_user") or k["user"], k.get("smtp_password") or k["password"])
            s.send_message(msg)
    else:
        with smtplib.SMTP(k["smtp_host"], port, timeout=30) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(k.get("smtp_user") or k["user"], k.get("smtp_password") or k["password"])
            s.send_message(msg)


def _smtp_check(k: dict) -> None:
    port = int(k.get("smtp_port") or 465)
    if port == 465:
        with smtplib.SMTP_SSL(k["smtp_host"], port, context=ssl.create_default_context(), timeout=20) as s:
            s.login(k.get("smtp_user") or k["user"], k.get("smtp_password") or k["password"])
    else:
        with smtplib.SMTP(k["smtp_host"], port, timeout=20) as s:
            s.starttls(context=ssl.create_default_context())
            s.login(k.get("smtp_user") or k["user"], k.get("smtp_password") or k["password"])


# ---------------------------------------------------------------- her setup
def _row(tenant: str):
    CH = _CH()
    CH._ensure()
    with session() as s:
        c = s.scalars(select(CH.SevaChannel).where(CH.SevaChannel.tenant_id == tenant, CH.SevaChannel.kind == "email",
                                                   CH.SevaChannel.status != "off")).first()
        if c is None:
            return None, {}
        s.expunge(c)
    return c, CH._open(c.sealed)


def _st(c) -> dict:
    try:
        return json.loads(c.settings or "{}")
    except ValueError:
        return {}


def forward_address(c) -> str:
    from .. import agentmail
    st = _st(c)
    if not agentmail.configured() or not st.get("fwd"):
        return ""
    return f"support-{st['fwd']}@{agentmail.domain()}"


def view(tenant: str) -> dict | None:
    c, k = _row(tenant)
    if c is None:
        return None
    st = _st(c)
    return {"id": c.id, "address": st.get("address", ""), "name": st.get("name", ""), "signature": st.get("signature", ""),
            "imap": bool(k.get("imap_host")), "smtp": bool(k.get("smtp_host")), "imap_host": k.get("imap_host", ""),
            "smtp_host": k.get("smtp_host", ""), "smtp_port": k.get("smtp_port", "") or "465", "user": k.get("user", ""), "status": c.status, "note": c.note,
            "forward": forward_address(c), "last_poll": st.get("last_poll", ""), "hints": json.loads(c.hints or "{}")}


def setup(tenant: str, body: dict) -> dict:
    """Her support address: who it is from, her signature, how mail comes in (IMAP and / or forwarding) and goes out
    (SMTP). A password is sealed at once and never shown; leaving it empty keeps the one saved."""
    CH = _CH()
    S = _S()
    CH._ensure()
    b = body if isinstance(body, dict) else {}
    addr = str(b.get("address") or "").strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", addr):
        raise MailError("Give your support email address, like help@yourshop.com.")
    c, old = _row(tenant)
    keys = dict(old)
    for f in ("imap_host", "imap_port", "smtp_host", "smtp_port", "user", "smtp_user"):
        if f in b:
            keys[f] = str(b[f] or "").strip()[:200]
    for f in ("password", "smtp_password"):
        if str(b.get(f) or ""):
            keys[f] = str(b[f])
    if keys.get("imap_host") and not (keys.get("user") and keys.get("password")):
        raise MailError("Reading by IMAP needs the mailbox user and its (app) password.")
    if keys.get("smtp_host") and not ((keys.get("smtp_user") or keys.get("user")) and (keys.get("smtp_password") or keys.get("password"))):
        raise MailError("Sending by SMTP needs the user and its (app) password.")
    st = _st(c) if c is not None else {}
    st.update({"address": addr, "name": S._clean(b.get("name"), 80) or st.get("name", ""),
               "signature": S._clean(b.get("signature"), 600) if "signature" in b else st.get("signature", "")})
    st.setdefault("fwd", secrets.token_hex(6))
    hints = {"password": "set"} if keys.get("password") else {}
    with session() as s:
        if c is None:
            r = CH.SevaChannel(tenant_id=tenant, kind="email", name="Email", token=secrets.token_urlsafe(18), sealed=CH._seal(keys),
                               hints=json.dumps(hints), status="set", settings=json.dumps(st))
            s.add(r)
        else:
            r = s.get(CH.SevaChannel, c.id)
            r.sealed, r.hints, r.settings = CH._seal(keys), json.dumps(hints), json.dumps(st)
    return check(tenant) | {"say": "Support email saved. Your password is sealed and is never shown again."}


def check(tenant: str) -> dict:
    """Log in to her mailbox (reading only) and to her sending server; note what works. Only mail from now on is answered."""
    CH = _CH()
    c, k = _row(tenant)
    if c is None:
        raise MailError("Set your support email first.")
    st = _st(c)
    notes, ok = [], True
    if k.get("imap_host"):
        try:
            top = _imap_check(k)
            if "uid" not in st:
                st["uid"] = top
            notes.append("Reading works.")
        except Exception as e:   # noqa: BLE001
            ok = False
            notes.append(f"Reading failed: {str(e)[:120]}")
    if k.get("smtp_host"):
        try:
            _smtp_check(k)
            notes.append("Sending works.")
        except Exception as e:   # noqa: BLE001
            ok = False
            notes.append(f"Sending failed: {str(e)[:120]}")
    else:
        notes.append("No sending server: replies wait as drafts for you to send.")
    if forward_address(c):
        notes.append(f"Forwarding address: {forward_address(c)}.")
    elif not k.get("imap_host"):
        ok = False
        notes.append("No way in yet: add IMAP, or ask the owner to set HOOLA_MAIL_DOMAIN for a forwarding address.")
    with session() as s:
        r = s.get(CH.SevaChannel, c.id)
        r.status, r.note, r.settings = ("ok" if ok else "error"), " ".join(notes)[:400], json.dumps(st)
    return view(tenant)


# ---------------------------------------------------------------- reading one mail
def strip_quoted(text: str) -> str:
    """The customer's new words only: the quoted earlier mail and '>' lines left out."""
    out = []
    for line in (text or "").splitlines():
        if line.lstrip().startswith(">") or QUOTE_START.match(line.strip()):
            if QUOTE_START.match(line.strip()):
                break
            continue
        out.append(line)
    return "\n".join(out).strip()


def _ticket_of(tenant: str, subject: str, refs: str) -> str:
    S = _S()
    for n in TAG.findall(subject or "") + MID.findall(refs or ""):
        with session() as s:
            t = s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant, S.SevaTicket.number == n)).first()
            if t is not None:
                return t.number
    return ""


def _save_files(tenant: str, raw: bytes, atts: list[dict]) -> tuple[list[dict], str]:
    from ..mailbox import mime
    d = UPLOADS / re.sub(r"[^A-Za-z0-9_-]", "_", tenant)
    files, read = [], []
    for a in atts[:8]:
        try:
            name, ctype, data = mime.get_attachment(raw, str(a["id"]))
        except KeyError:
            continue
        if not data or len(data) > MAX_FILE:
            continue
        fid = new_id("wf")
        d.mkdir(parents=True, exist_ok=True)
        (d / fid).write_bytes(data)
        safe = re.sub(r"[^\w. -]", "_", name)[:80] or "file"
        (d / (fid + ".json")).write_text(json.dumps({"name": safe, "mime": ctype or "application/octet-stream", "customer": ""}))
        files.append({"id": fid, "name": safe, "size": len(data)})
        if (ctype or "").startswith(("application/pdf", "text/")) or safe.lower().endswith((".pdf", ".txt", ".docx", ".csv")):
            try:
                t = mime.attachment_text(safe, ctype, data, limit=1500, max_pages=5).get("text", "")
                if t:
                    read.append(f"{safe}: {t[:1500]}")
            except Exception:   # noqa: BLE001
                pass
    return files, "\n\n".join(read)


def take(tenant: str, raw: bytes, source: str = "imap") -> dict:
    """One mail to her support address -> answered, put on its ticket, or dropped with the reason."""
    from ..mailbox import mime
    from . import watch as W
    CH = _CH()
    S = _S()
    c, k = _row(tenant)
    if c is None:
        return {"dropped": "no support email"}
    st = _st(c)
    m = mime.parse(raw)
    sender = str(m.get("from_email") or "").strip().lower()
    mine = st.get("address", "")
    if not sender or sender == mine or BOUNCE.match(sender.split("@")[0]):
        return {"dropped": "own address / bounce / no-reply"}
    if m.get("bulk") or mime.is_automated(sender):
        return {"dropped": "an automatic mail or a mailing list"}
    customer = "email:" + sender
    if CH._seen(tenant, c.id, m.get("message_id", "")):
        return {"dropped": "already read"}
    subject = S._clean(m.get("subject"), 300)
    words = strip_quoted(m.get("body") or "") or S._clean(m.get("body"), 3000)
    files, read = _save_files(tenant, raw, m.get("attachments") or [])
    text = S._clean(words, 3000) + (("\n\n[Attached: " + ", ".join(f["name"] for f in files) + "]") if files else "")
    meta = {"message_id": m.get("message_id", ""), "subject": subject, "refs": (m.get("references", "") + " " + m.get("in_reply_to", "")).strip(),
            "files": files}
    if files:
        meta["file"] = files[0]["id"]
    number = _ticket_of(tenant, subject, meta["refs"])
    if number:
        CH._store(tenant, c.id, customer, m.get("from", ""), "in", "customer", f"{subject}\n{text}".strip(), m.get("message_id", ""),
                  "", "", meta)
        ans = W.customer_answer(tenant, customer, words)
        if ans:
            _reply(tenant, customer, ans.get("reply", ""), ans["decision"])
            return {"ticket": number, "decision": ans["decision"]}
        with session() as s:
            t = s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant, S.SevaTicket.number == number)).first()
            reopen = t.status in ("resolved", "closed")
            S._add_note(t, "customer", f"Email from the customer: {S.mask(words)[:1500]}" + (f"\n\nRead from the files: {S.mask(read)[:1500]}" if read else ""))
            t.awaiting_since = t.awaiting_since or S.clock()
            t.updated_at = S.clock()
            tid = t.id
        if reopen and W.rules(tenant).get("reopen_days"):
            W.reopen(tenant, tid, words, "customer")
        S._publish(tenant, "seva_chat", {"customer": customer, "kind": "email", "text": S.mask(words)[:300], "ticket": number})
        return {"ticket": number, "decision": "on_ticket"}
    replies = CH.handle(tenant, c.id, [{"from": sender, "customer": customer, "name": m.get("from", ""),
                                        "text": (subject + "\n" + text).strip(), "ext_id": m.get("message_id", "") or new_id("em"),
                                        "meta": meta}])
    if read:
        with session() as s:
            t = s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant, S.SevaTicket.customer == customer,
                                                     S.SevaTicket.status.in_(S.R.OPEN)).order_by(S.SevaTicket.created_at.desc())).first()
            if t is not None:
                S._add_note(t, "hoola", f"Read from the attached files: {S.mask(read)[:2000]}")
    return {"decision": "handled", "replies": replies}


def _reply(tenant: str, customer: str, words: str, decision: str) -> None:
    try:
        _CH().send_to(tenant, customer, words, "hoola", decision)
    except Exception as e:   # noqa: BLE001
        log.info("support mail reply not sent: %s", e)


# ---------------------------------------------------------------- sending one mail
def send(c, k: dict, to_addr: str, text: str, meta: dict | None = None) -> bool:
    """From HER address, in the thread, her signature under it, the ticket number in the subject."""
    from ..mailbox import mime
    S = _S()
    st = _st(c)
    if not k.get("smtp_host"):
        return False
    key = f"{c.tenant_id}:{to_addr}"
    q, t0 = _SENT[key], time.monotonic()
    while q and q[0] < t0 - 3600:
        q.popleft()
    if len(q) >= PER_HOUR:
        log.warning("support mail: %s got %d answers this hour; holding the next", to_addr, PER_HOUR)
        return False
    meta = meta or {}
    subj = str(meta.get("subject") or "Your request")
    with session() as s:
        t = s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == c.tenant_id, S.SevaTicket.customer == "email:" + to_addr)
                      .order_by(S.SevaTicket.updated_at.desc())).first()
        number = t.number if t is not None else ""
    if number and f"[{number}]" not in subj:
        subj = f"{subj} [{number}]"
    if not subj.lower().startswith("re:"):
        subj = "Re: " + subj
    body = text + (f"\n\n-- \n{st['signature']}" if st.get("signature") else "")
    msg = mime.build(from_addr=st.get("address", ""), from_name=st.get("name", "") or st.get("address", ""), to=to_addr, subject=subj,
                     body=body, in_reply_to=meta.get("message_id") or None, references=meta.get("refs") or None)
    dom = (st.get("address") or "x@hoola.local").split("@")[-1]
    del msg["Message-ID"]
    msg["Message-ID"] = email.utils.make_msgid(idstring=f"seva.{number or 'X-0'}.{secrets.token_hex(4)}", domain=dom)
    msg["Auto-Submitted"] = "auto-replied" if meta.get("auto") else "no"
    _smtp_send(k, msg)
    q.append(t0)
    return True


# ---------------------------------------------------------------- the worker + forwarding
def poll(tenant: str, force: bool = False) -> int:
    CH = _CH()
    c, k = _row(tenant)
    if c is None or not k.get("imap_host") or c.status == "off":
        return 0
    st = _st(c)
    if not force and time.time() - float(st.get("last_ts") or 0) < POLL_EVERY:
        return 0
    try:
        mails, top = _imap_fetch(k, int(st.get("uid") or 0))
    except Exception as e:   # noqa: BLE001
        with session() as s:
            r = s.get(CH.SevaChannel, c.id)
            r.status, r.note = "error", f"Reading failed: {str(e)[:160]}"
            stt = _st(r)
            stt["last_ts"] = time.time()
            r.settings = json.dumps(stt)
        return 0
    n = 0
    for uid, raw in mails:
        try:
            take(tenant, raw)
            n += 1
        except Exception:   # noqa: BLE001 - one bad mail never stops the rest
            log.exception("support mail take")
    with session() as s:
        r = s.get(CH.SevaChannel, c.id)
        stt = _st(r)
        stt.update(uid=top, last_ts=time.time(), last_poll=_S().clock().isoformat())
        r.settings, r.status = json.dumps(stt), "ok"
    return n


def poll_all() -> int:
    CH = _CH()
    CH._ensure()
    with session() as s:
        tenants = list({c.tenant_id for c in s.scalars(select(CH.SevaChannel).where(CH.SevaChannel.kind == "email",
                                                                                    CH.SevaChannel.status != "off")).all()})
    total = 0
    for t in tenants:
        try:
            total += poll(t)
        except Exception:   # noqa: BLE001
            log.exception("support mail poll %s", t)
    return total


def from_forward(local: str, raw: bytes) -> dict | None:
    """agentmail.inbound: a mail to support-<code>@<domain> (already signature-checked) -> her support desk."""
    CH = _CH()
    if not local.startswith("support-"):
        return None
    code = local[len("support-"):]
    CH._ensure()
    with session() as s:
        for c in s.scalars(select(CH.SevaChannel).where(CH.SevaChannel.kind == "email", CH.SevaChannel.status != "off")).all():
            if _st(c).get("fwd") == code:
                tenant = c.tenant_id
                break
        else:
            return {"ok": True, "dropped": "no such support address"}
    out = take(tenant, raw, "forward")
    return {"ok": True} | out
