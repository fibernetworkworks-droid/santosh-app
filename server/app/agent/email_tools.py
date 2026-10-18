"""Email tools: read the inbox, draft replies. Sending always waits for the user's approval."""
from __future__ import annotations

from .. import mail
from ..db import EmailDraft, now, session
from ..events import bus
from .tools import Ctx, ToolError

EMAIL_TOOLS = [
    {"name": "email_check", "description": (
        "List recent emails in the user's inbox (newest first). Use unread_only for 'koi nayi mail aayi?'. "
        "Returns each mail's id, sender, subject and date. To read one fully, call email_read with its id."),
     "input_schema": {"type": "object", "properties": {
         "unread_only": {"type": "boolean", "description": "Only unread mails"},
         "limit": {"type": "integer", "description": "How many (default 10, max 25)"},
         "search": {"type": "string", "description": "Optional: only mails matching this sender, subject or word"}}}},
    {"name": "email_read", "description": "Read one email fully (sender, subject, full text). id comes from email_check. Marks it read.",
     "input_schema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
    {"name": "email_draft", "description": (
        "Write an email for the user to approve and send. Use for a reply (pass reply_to_id = the id of the email being "
        "answered, so it threads) or a new mail (pass 'to'). WRITE THE FULL BODY yourself in the user's language and tone, "
        "signed with their name. The user approves and sends it from the app; it is NOT sent automatically. "
        "Never put passwords, OTPs or card numbers in an email."),
     "input_schema": {"type": "object", "properties": {
         "to": {"type": "string", "description": "Recipient email(s), comma-separated. Omit when reply_to_id is given and you want the original sender."},
         "cc": {"type": "string"},
         "subject": {"type": "string", "description": "Omit on a reply to keep 'Re: ...'"},
         "body": {"type": "string", "description": "The full email text, ready to send"},
         "reply_to_id": {"type": "string", "description": "id of the email this answers (from email_check/email_read)"}},
         "required": ["body"]}},
]

EMAIL_LABELS = {"email_check": "Inbox dekh raha hoon", "email_read": "Email padh raha hoon",
                "email_draft": "Email likh raha hoon"}


def _require(ctx: Ctx):
    from ..config import get_settings
    if mail.configured() and ctx.tenant_id != get_settings().tenant_id:
        raise ToolError("Aapka email abhi Santosh se connect nahi hai (server ka email sirf owner ke liye hai). "
                        "Apna Gmail jodne ka option jald aa raha hai.")
    if not mail.configured():
        raise ToolError("Email abhi connect nahi hai. Server ke .env mein EMAIL_ADDRESS aur EMAIL_PASSWORD (app password) daaliye.")


async def email_check(ctx: Ctx, unread_only=False, limit=10, search=None, **_):
    _require(ctx)
    try:
        items = await mail.fetch_recent(limit=int(limit or 10), unread_only=bool(unread_only), search=search)
    except mail.MailError as e:
        raise ToolError(str(e))
    return {"count": len(items), "emails": items}


async def email_read(ctx: Ctx, id, **_):
    _require(ctx)
    try:
        return await mail.read_email(str(id))
    except mail.MailError as e:
        raise ToolError(str(e))


async def email_draft(ctx: Ctx, body, to=None, cc="", subject=None, reply_to_id=None, **_):
    _require(ctx)
    to_addr = (to or "").strip()
    subj = (subject or "").strip()
    in_reply_to = refs = None
    if reply_to_id:
        try:
            orig = await mail.read_email(str(reply_to_id), mark_seen=False)
        except mail.MailError as e:
            raise ToolError(str(e))
        if not to_addr:
            to_addr = orig["from_email"]
        if not subj:
            osub = orig["subject"]
            subj = osub if osub.lower().startswith("re:") else f"Re: {osub}"
        in_reply_to = orig.get("message_id") or None
        refs = orig.get("references") or None
    if not to_addr:
        raise ToolError("Kis email par bhejna hai? 'to' address do, ya reply_to_id do.")
    if "@" not in to_addr:
        raise ToolError(f"'{to_addr}' sahi email address nahi lagta.")
    if not subj:
        subj = "(no subject)"
    with session() as s:
        d = EmailDraft(tenant_id=ctx.tenant_id, conversation_id=ctx.conversation_id, to_addr=to_addr[:1000],
                       cc_addr=(cc or "")[:1000], subject=subj[:500], body=str(body), in_reply_to=in_reply_to, references=refs)
        s.add(d)
        s.flush()
        view = {"id": d.id, "to": d.to_addr, "cc": d.cc_addr, "subject": d.subject, "body": d.body, "status": "pending"}
    bus.publish(ctx.conversation_id, "email_draft", view)
    return {"draft_id": view["id"], "to": to_addr, "subject": subj, "status": "pending_approval",
            "note": "Draft taiyaar hai. User app mein 'Bhejo' dabakar approve karega; tab tak bheja nahi jayega."}


EMAIL_HANDLERS = {"email_check": email_check, "email_read": email_read, "email_draft": email_draft}
