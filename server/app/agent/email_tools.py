"""Email tools: the user's own mailboxes (Gmail / Outlook by sign-in, or any email by app password).

Reading, sorting and organising happen straight away. Sending (draft card -> Bhejo), deleting and bulk mail
(always) and delete-forever / draft-send / alias-remove (confirm cards) wait for the user's tap.
"""
from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from ..db import EmailDraft, now, session
from ..events import bus
from ..mailbox import contacts, mime, sync
from ..mailbox import service as ms
from ..mailbox.accounts import (get_box, set_default, set_signature, settings_scope_message, settings_scope_ok, views)
from ..mailbox.base import MailError, NotConnected
from .tools import Ctx, ToolError

ATTACH_SCHEMA = {"type": "array", "description": (
    "Files to attach. Each item is ONE of: {email_id, attachment_id} (a file from a received email, ids from "
    "email_read), {file_id} (a file from the user's PC via pc_send_to_phone, or one the user added), "
    "{drive_file_id} (a file from the user's Google Drive), {artifact_id} (a Santosh page)."),
    "items": {"type": "object", "properties": {"email_id": {"type": "string"}, "attachment_id": {"type": "string"},
                                               "file_id": {"type": "string"}, "drive_file_id": {"type": "string"},
                                               "artifact_id": {"type": "string"}}}}

EMAIL_TOOLS = [
    {"name": "email_check", "description": (
        "List emails (newest first) with a short preview. folder: inbox (default), sent, archive, starred, snoozed "
        "(Gmail's own snooze pile), spam, trash, or a label/folder name. account: a mailbox address, or 'all' for a "
        "unified inbox across every connected mailbox. unread_only for 'koi nayi mail aayi?'. search finds by sender, "
        "subject or words (Gmail accounts accept Gmail search like 'from:bank has:attachment'). Read one fully with "
        "email_read, a whole conversation with email_thread."),
     "input_schema": {"type": "object", "properties": {
         "folder": {"type": "string"}, "unread_only": {"type": "boolean"},
         "limit": {"type": "integer", "description": "How many (default 10, max 50)"},
         "search": {"type": "string"},
         "account": {"type": "string", "description": "Which mailbox (address), or 'all' (default: the first mailbox)"}}}},
    {"name": "email_read", "description": (
        "Read one email fully: sender, recipients, subject, full text and its attachments (id, name, size). "
        "Marks it read."),
     "input_schema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
    {"name": "email_thread", "description": (
        "Read a whole conversation (thread) in order: every message with sender, time and text. id from email_check "
        "or email_read. Use for 'poora baat-cheet dikhao', 'is thread mein kya hua'."),
     "input_schema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
    {"name": "email_triage", "description": (
        "Sort the inbox: what needs the user's reply, bills/payments, OTP and security alerts, newsletters, other. Use "
        "for 'aaj ki mails batao', 'kya zaroori hai', a daily inbox summary. hours = how far back (default 24)."),
     "input_schema": {"type": "object", "properties": {
         "hours": {"type": "integer"}, "unread_only": {"type": "boolean", "description": "default true"},
         "account": {"type": "string"}}}},
    {"name": "email_attachment", "description": (
        "Use an attachment of an email. do='read': get its text (PDF, Word, Excel, CSV, text) to summarise or answer "
        "from it. do='phone': send the file to the user's phone (download card). do='pc': save it on the user's PC "
        "(Santosh Inbox folder)."),
     "input_schema": {"type": "object", "properties": {
         "email_id": {"type": "string"}, "attachment_id": {"type": "string"},
         "do": {"type": "string", "enum": ["read", "phone", "pc"]}}, "required": ["email_id", "attachment_id"]}},
    {"name": "email_draft", "description": (
        "Write an email for the user to approve and send: a reply (reply_to_id = the email being answered; reply_all "
        "to include everyone) or a new mail ('to' = addresses, or people's names: Santosh finds their address from past "
        "mail). WRITE THE FULL BODY yourself in the user's language and tone. markdown=true makes the body rich: "
        "**bold**, *italic*, `code`, [text](url), - bullets, numbered lists, ## headings (sent as nice HTML plus plain "
        "text; never write raw HTML tags yourself). If the mailbox has a signature it is added automatically, so don't "
        "sign then; otherwise sign with the user's name. The user approves with Bhejo in the app; it is NOT sent "
        "automatically. send_at schedules it (local time, e.g. 2026-10-20T09:00). follow_up_days = remind the user if "
        "nobody replies. save_to_gmail=true also puts the draft in their Gmail Drafts folder (they can finish it in "
        "the Gmail app too). from_alias='address' sends from one of her Gmail send-as aliases (only verified ones; "
        "needs the Gmail settings permission — an old mailbox is told to reconnect once). Never put passwords, OTPs "
        "or card numbers in an email."),
     "input_schema": {"type": "object", "properties": {
         "to": {"type": "string", "description": "Emails or names, comma-separated. Omit on a reply to answer the sender."},
         "cc": {"type": "string"}, "bcc": {"type": "string"},
         "subject": {"type": "string", "description": "Omit on a reply to keep 'Re: ...'"},
         "body": {"type": "string", "description": "The full email text, ready to send"},
         "markdown": {"type": "boolean", "description": "body is markdown-lite; goes out as rich HTML + plain text"},
         "reply_to_id": {"type": "string"}, "reply_all": {"type": "boolean"},
         "attachments": ATTACH_SCHEMA,
         "send_at": {"type": "string", "description": "Optional: send later at this local time"},
         "follow_up_days": {"type": "number", "description": "Optional: remind if no reply after this many days"},
         "save_to_gmail": {"type": "boolean", "description": "Also save into the Gmail Drafts folder"},
         "from_alias": {"type": "string", "description": "Send from this Gmail send-as alias (verified ones only)"},
         "account": {"type": "string", "description": "Send from this mailbox (address)"}},
         "required": ["body"]}},
    {"name": "email_forward", "description": (
        "Forward an email (with its attachments) to someone. note = a short message on top, in the user's tone. Makes a "
        "draft card; the user approves with Bhejo."),
     "input_schema": {"type": "object", "properties": {
         "id": {"type": "string"}, "to": {"type": "string", "description": "Emails or names"}, "cc": {"type": "string"},
         "note": {"type": "string"}, "include_attachments": {"type": "boolean", "description": "default true"}},
         "required": ["id", "to"]}},
    {"name": "email_action", "description": (
        "Organise emails (done at once, can be undone): archive, mark_read, mark_unread, star, unstar, move (to "
        "folder/label; created if missing), spam, not_spam, mark_important, mark_not_important, category (folder= "
        "personal / social / updates / forums / promotions; Gmail). ids from email_check. To delete use email_delete."),
     "input_schema": {"type": "object", "properties": {
         "ids": {"type": "array", "items": {"type": "string"}},
         "action": {"type": "string", "enum": list(ms.ACTIONS)}, "folder": {"type": "string"}},
         "required": ["ids", "action"]}},
    {"name": "email_label", "description": (
        "Manage Gmail labels. action='list' shows them as a nested tree (Gmail nests with /). 'create' (name) — "
        "'Office/Clients' creates the nested path too. 'rename' (name, new_name). 'color' (name, color: red / orange / "
        "amber / yellow / green / mint / teal / sky / blue / lavender / purple / grey). 'delete' first asks the user "
        "with a card — mails stay, only the label goes. Star colors are NOT possible through Google's API (say so)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["list", "create", "rename", "delete", "color"]},
         "name": {"type": "string"}, "new_name": {"type": "string"}, "color": {"type": "string"},
         "account": {"type": "string"}}, "required": ["action"]}},
    {"name": "email_drafts", "description": (
        "The drafts saved in the mailbox's own Drafts folder (Gmail). action='list' shows them (subject, to, when). "
        "action='read' with id shows one fully (to, cc, subject, body, attachment names). action='edit' with id + only "
        "the fields that change (to / cc / subject / body / markdown) rewrites that Gmail draft in place — attachments "
        "and the conversation thread stay. action='send' with id sends that Gmail draft — behind a confirm card, "
        "because it really goes out. action='delete' with id removes one — behind a confirm card (a Gmail draft does "
        "not go to Trash). id is the draft_id (or ref) from 'list'. Gmail accounts only; other mailboxes are told so."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["list", "read", "edit", "send", "delete"]}, "id": {"type": "string"},
         "to": {"type": "string"}, "cc": {"type": "string"}, "subject": {"type": "string"},
         "body": {"type": "string"}, "markdown": {"type": "boolean"},
         "limit": {"type": "integer"}, "account": {"type": "string"}}, "required": ["action"]}},
    {"name": "email_filters", "description": (
        "Gmail's OWN filters (Gmail web > Settings > Filters): they run INSIDE Gmail forever — even when the phone is "
        "off and even if Hoola's server is down (unlike email_rule, which runs on Hoola's watcher). action='list' shows "
        "them. action='create' with match + do: match = {from, to, subject, query (raw Gmail search), has_attachment, "
        "larger_kb, smaller_kb, exclude_chats}; do = {label (created if missing), archive, star, mark_read, important, "
        "not_important, category (personal/social/updates/forums/promotions), forward (a VERIFIED forwarding address)"
        "}. Delete-keeping actions are deliberately NOT offered — new mail is never destroyed by a filter. "
        "action='delete' with filter_id removes one (mails it already labelled stay)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["list", "create", "delete"]},
         "match": {"type": "object", "properties": {
             "from": {"type": "string"}, "to": {"type": "string"}, "subject": {"type": "string"},
             "query": {"type": "string"}, "has_attachment": {"type": "boolean"},
             "larger_kb": {"type": "integer"}, "smaller_kb": {"type": "integer"},
             "exclude_chats": {"type": "boolean"}}},
         "do": {"type": "object", "properties": {
             "label": {"type": "string"}, "archive": {"type": "boolean"}, "star": {"type": "boolean"},
             "mark_read": {"type": "boolean"}, "important": {"type": "boolean"}, "not_important": {"type": "boolean"},
             "category": {"type": "string"}, "forward": {"type": "string"}}},
         "filter_id": {"type": "string"}, "account": {"type": "string"}}, "required": ["action"]}},
    {"name": "email_forwarding", "description": (
        "Gmail's forwarding-address book. auto_forward (email_accounts) and a filter's forward both need an address "
        "that is IN this book AND verified. action='list' shows them with status. action='add' with email adds one — "
        "Google mails a verification link to that inbox; she clicks it there, then forwarding can start. "
        "action='remove' with email takes it off the book."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["list", "add", "remove"]}, "email": {"type": "string"},
         "account": {"type": "string"}}, "required": ["action"]}},
    {"name": "email_alias", "description": (
        "Gmail send-as aliases. action='list' shows them (verified / pending, has signature). action='add' with email "
        "(name optional) adds a NEW 'Send mail as' address — Google sends that inbox a confirmation; after it is "
        "verified, email_draft from_alias sends from it. action='remove' with email takes an alias off (the primary "
        "address never) — behind a confirm card."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["list", "add", "remove"]}, "email": {"type": "string"},
         "name": {"type": "string"}, "reply_to": {"type": "string"}, "account": {"type": "string"}},
         "required": ["action"]}},
    {"name": "email_threads", "description": (
        "WHOLE Gmail conversations in one go (threads.modify / threads.trash): action='list' with query (Gmail "
        "search, default in:inbox) + limit shows conversations with ref, subject, from, count, unread, snippet. "
        "action='read' with a message id from email_check reads the whole conversation (same as email_thread). "
        "action='act' with refs + one of archive / trash / inbox / mark_read / mark_unread / star / unstar / move "
        "(folder=) applies it to EVERY mail in those conversations at once. Gmail accounts only."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["list", "read", "act"]},
         "query": {"type": "string"}, "limit": {"type": "integer"},
         "refs": {"type": "array", "items": {"type": "string"}},
         "id": {"type": "string", "description": "a message id for action=read"},
         "act": {"type": "string", "enum": ["archive", "trash", "inbox", "mark_read", "mark_unread", "star", "unstar", "move"]},
         "folder": {"type": "string"}, "account": {"type": "string"}}, "required": ["action"]}},
    {"name": "email_rule", "description": (
        "Her inbox rules and saved searches (Santosh-side, so they work for Gmail AND Outlook/IMAP). "
        "action='create' with match + actions: match = {from: 'hdfcbank' (sender words/emails, comma = any of), "
        "subject: 'words, comma = all of', has_attachment: true, bulk: true (newsletters), unread: true}; actions = "
        "{label: 'Bills', archive: true, star: true, mark_read: true, important: true/false (Gmail), mute: true (no "
        "new-mail announcement), notify: true (announce even in vip mode), forward_to: 'email' (makes a DRAFT card for "
        "her Bhejo tap — Santosh NEVER sends by himself)}. Rules apply to NEW mail from now on, not to old mail. "
        "kind='search' with match (from / subject / has_attachment / bulk / unread, or query: a raw Gmail search like "
        "'from:hdfcbank has:attachment') saves a SEARCH instead: a name she can ask for again any time ('bank wali "
        "mails dikhao') — running one only lists what matches now, it changes nothing. action='list' shows rules with "
        "hit counts, 'searches' shows the saved searches, 'run' with rule_id runs one saved search now, 'pause'/'resume' "
        "with rule_id, 'delete' with rule_id (rules and searches), 'test' dry-runs a rule against the newest inbox mail "
        "(nothing changes)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["create", "list", "searches", "run", "pause", "resume", "delete", "test"]},
         "kind": {"type": "string", "enum": ["rule", "search"], "description": "create: 'rule' (default) or 'search'"},
         "name": {"type": "string"},
         "match": {"type": "object", "properties": {
             "from": {"type": "string"}, "subject": {"type": "string"}, "has_attachment": {"type": "boolean"},
             "bulk": {"type": "boolean"}, "unread": {"type": "boolean"},
             "query": {"type": "string", "description": "saved search: raw Gmail search string"}}},
         "actions": {"type": "object", "properties": {
             "label": {"type": "string"}, "archive": {"type": "boolean"}, "star": {"type": "boolean"},
             "mark_read": {"type": "boolean"}, "important": {"type": "boolean"}, "mute": {"type": "boolean"},
             "notify": {"type": "boolean"}, "forward_to": {"type": "string"}}},
         "rule_id": {"type": "string"}, "account": {"type": "string"}}, "required": ["action"]}},
    {"name": "email_snooze", "description": (
        "Snooze an email: it leaves the inbox now and comes back unread at the chosen time with a reminder card "
        "(like Gmail's snooze). action='add' with email_id + when (local time like 2026-10-26T09:00) or hours / days. "
        "action='list' shows snoozed mail, 'cancel' with snooze_id brings one back at once. Never for OTP mails."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["add", "list", "cancel"]}, "email_id": {"type": "string"},
         "when": {"type": "string", "description": "Local time, e.g. 2026-10-26T09:00"},
         "hours": {"type": "number"}, "days": {"type": "number"}, "snooze_id": {"type": "string"}},
         "required": ["action"]}},
    {"name": "email_vacation", "description": (
        "Gmail ka vacation / out-of-office auto-reply. action='get' shows the current setting. action='set' turns it "
        "on or off: write `message` (the auto-reply text, in the user's language), optional `subject` (Gmail uses "
        "'Re: <their subject>' when empty), optional start / end local times like 2026-10-27T09:00 (no end = until "
        "she switches it off), contacts_only=true answers only saved contacts. Any ON or OFF shows a confirm card "
        "first — it answers EVERY incoming mail until she turns it off."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["get", "set"]},
         "enable": {"type": "boolean", "description": "set: true = on, false = off"},
         "message": {"type": "string", "description": "The auto-reply text (required to switch on)"},
         "subject": {"type": "string", "description": "Optional subject line of the auto-reply"},
         "start": {"type": "string", "description": "Local time, e.g. 2026-10-27T09:00 (default: now)"},
         "end": {"type": "string", "description": "Local time; omit = until switched off"},
         "contacts_only": {"type": "boolean", "description": "Answer only saved contacts"},
         "account": {"type": "string", "description": "Which Gmail mailbox (address)"}}, "required": ["action"]}},
    {"name": "email_delete", "description": (
        "Delete emails. Default: move to Trash (recoverable for 30 days) behind a confirm card. forever=true asks for "
        "a PERMANENT delete instead (Gmail only): the mail skips Trash and cannot be recovered — the card says this "
        "in plain words and only the user's tap does it. OTP / security mails are never deleted by themselves."),
     "input_schema": {"type": "object", "properties": {"ids": {"type": "array", "items": {"type": "string"}},
                      "forever": {"type": "boolean", "description": "true = permanent delete, no Trash (Gmail only)"}},
                      "required": ["ids"]}},
    {"name": "email_follow_up", "description": (
        "Follow-up reminders. action='add' with email_id + days: for a mail the user SENT, remind if the other person "
        "doesn't reply; for a mail the user RECEIVED, remind the user to reply. action='list' shows them, 'cancel' "
        "stops one (watch_id). Tip: email_draft also takes follow_up_days."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["add", "list", "cancel"]}, "email_id": {"type": "string"},
         "days": {"type": "number"}, "watch_id": {"type": "string"}}, "required": ["action"]}},
    {"name": "email_bulk", "description": (
        "Send one email separately to many people (mail merge). Recipients come from source: {email_id, attachment_id} "
        "(an Excel/CSV attached to an email), {file_id} (Excel/CSV from the PC or phone), {lead_list_id} (an uploaded "
        "contact list), or {rows: [{email, name, ...}]}. Use {{column}} in subject/body for each person's details, e.g. "
        "'Namaste {{name}}, aapka bill {{amount}} hai'. Shows a confirm card with a sample; nothing is sent until the user "
        "approves. Only for people who expect mail from the user (customers, members, team), never purchased lists."),
     "input_schema": {"type": "object", "properties": {
         "subject": {"type": "string"}, "body": {"type": "string"},
         "source": {"type": "object", "properties": {
             "email_id": {"type": "string"}, "attachment_id": {"type": "string"}, "file_id": {"type": "string"},
             "lead_list_id": {"type": "string"}, "rows": {"type": "array", "items": {"type": "object"}}}},
         "email_column": {"type": "string"}, "name_column": {"type": "string"},
         "attachments": ATTACH_SCHEMA, "account": {"type": "string"}},
         "required": ["subject", "body", "source"]}},
    {"name": "email_bulk_status", "description": "Progress of a bulk email (bulk_id); cancel=true stops sending the rest.",
     "input_schema": {"type": "object", "properties": {"bulk_id": {"type": "string"}, "cancel": {"type": "boolean"}},
                      "required": ["bulk_id"]}},
    {"name": "email_contacts", "description": "Find people's email addresses by name (learned from the user's mail).",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "email_accounts", "description": (
        "The user's connected mailboxes and their signatures, and settings: signature (set for a mailbox; "
        "signature_push=true also pushes it INTO Gmail itself, behind a confirm card), make_default (address), "
        "daily_summary ('09:00' local time for a daily inbox summary, 'weekly 09:00' for a weekly digest every "
        "weekday of the first run, or 'off'), undo_seconds (0-60: after Bhejo the email waits this many seconds and "
        "can still be cancelled; 0 = send at once), watch_mode ('off' = no new-mail announcements, 'vip' = important "
        "mail + people she mails herself [default], 'all' = every new mail; for one account or all), mute (sender "
        "emails, comma-separated, to never announce; 'clear' empties the list), send_as=true lists the Gmail send-as "
        "aliases plus the current auto-forwarding (read-only), auto_forward=('off', or an email address to forward "
        "new mail to — always behind a confirm card). Call with no arguments to just list everything. If nothing is "
        "connected, tell the user: Profile > Email > Gmail / Outlook / Other."),
     "input_schema": {"type": "object", "properties": {
         "account": {"type": "string"}, "signature": {"type": "string"}, "make_default": {"type": "string"},
         "daily_summary": {"type": "string"},
         "undo_seconds": {"type": "integer", "description": "0-60, 0 = off"},
         "signature_push": {"type": "boolean", "description": "Push this mailbox's signature into Gmail itself"},
         "send_as": {"type": "boolean", "description": "List Gmail send-as aliases + auto-forwarding (read-only)"},
         "auto_forward": {"type": "string", "description": "'off', or an email address to forward new mail to"},
         "imap": {"type": "string", "enum": ["get", "on", "off"], "description": "Gmail ka IMAP setting"},
         "pop": {"type": "string", "enum": ["get", "off", "all", "from_now_on"], "description": "Gmail ka POP download setting"},
         "pop_disposition": {"type": "string", "enum": ["leave_in_inbox", "archive", "trash", "mark_read"],
                             "description": "what Gmail does with mail fetched via POP (with pop)"},
         "language": {"type": "string", "description": "'get', or a Gmail display language code (hi / en / en-GB / mr / ta)"},
         "watch_mode": {"type": "string", "enum": ["off", "vip", "all"],
                        "description": "New-mail announcements: off / vip (default) / all"},
         "mute": {"type": "string", "description": "Sender emails to never announce (comma-separated), or 'clear'"}}}},
]

EMAIL_LABELS = {"email_check": "Inbox dekh raha hoon", "email_read": "Email padh raha hoon",
                "email_thread": "Poora conversation padh raha hoon", "email_triage": "Inbox chhaant raha hoon",
                "email_attachment": "Attachment khol raha hoon",
                "email_draft": "Email likh raha hoon", "email_forward": "Email forward kar raha hoon",
                "email_action": "Emails sambhal raha hoon", "email_label": "Labels sambhal raha hoon",
                "email_drafts": "Mailbox ke drafts sambhal raha hoon",
                "email_filters": "Gmail ka filter sambhal raha hoon",
                "email_forwarding": "Forwarding addresses sambhal raha hoon",
                "email_alias": "Send-as alias sambhal raha hoon",
                "email_threads": "Poore conversations sambhal raha hoon",
                "email_delete": "Delete ki manzoori le raha hoon",
                "email_follow_up": "Follow-up laga raha hoon", "email_bulk": "Bulk email taiyaar kar raha hoon",
                "email_bulk_status": "Bulk email dekh raha hoon", "email_contacts": "Address dhoondh raha hoon",
                "email_accounts": "Email settings dekh raha hoon",
                "email_rule": "Inbox rule sambhal raha hoon", "email_snooze": "Mail snooze kar raha hoon",
                "email_vacation": "Vacation reply sambhal raha hoon"}


async def _t(fn, *a, **kw):
    try:
        return await asyncio.to_thread(fn, *a, **kw)
    except NotConnected as e:
        raise ToolError(str(e))
    except MailError as e:
        raise ToolError(str(e))


async def email_check(ctx: Ctx, folder="inbox", unread_only=False, limit=10, search=None, account=None, **_):
    return await _t(ms.check, ctx.tenant_id, folder or "inbox", bool(unread_only), search, int(limit or 10), account)


async def email_read(ctx: Ctx, id, **_):
    return await _t(ms.read, ctx.tenant_id, str(id))


async def email_thread(ctx: Ctx, id, **_):
    return await _t(ms.thread, ctx.tenant_id, str(id))


async def email_triage(ctx: Ctx, hours=24, unread_only=True, account=None, **_):
    return await _t(ms.triage, ctx.tenant_id, int(hours or 24), 40, account, unread_only is not False)


def _read_image(ctx: Ctx, name: str, mtype: str, data: bytes) -> dict[str, Any]:
    """v0.181.0 a picture attachment: QR + our own OCR first, vision only if that is weak — same ladder as file_read."""
    from ..net import media
    from .. import ocr, qrread
    info = media.analyse(name, mtype, data)
    out: dict[str, Any] = {"name": name, "size": len(data), "kind": "image"}
    codes = qrread.scan(data)
    if codes:
        out["codes"] = codes
    try:
        from .file_tools import _owner_lang
        lang = _owner_lang(ctx.tenant_id)
    except Exception:
        lang = "hinglish"
    r = ocr.read(data, lang)
    if r and r.get("text"):
        out["text"] = r["text"][:15000]
        out["ocr"] = {k: r[k] for k in ("conf", "langs", "good") if k in r}
        return out
    try:
        seen = media.understand(ctx.tenant_id, info, name, mtype, data, "")
    except Exception:
        seen = None
    if seen:
        out["seen"] = seen
    else:
        out["note"] = "Is picture mein padhne layak kuch nahi mila; do='phone' se phone par bhej sakte hain."
    return out


async def email_attachment(ctx: Ctx, email_id, attachment_id, do="read", **_):
    name, mtype, data = await _t(ms.attachment, ctx.tenant_id, str(email_id), str(attachment_id))
    if do == "phone":
        from ..pc import service as pcs
        row = await asyncio.to_thread(ms.store_bytes, ctx.tenant_id, name, data, "to_phone")
        view = pcs.public_file(row)
        bus.publish(ctx.conversation_id, "pc_file", {**view, "source": "email"})
        return {"sent_to_phone": name, "size": len(data), "note": "A download card is in the chat."}
    if do == "pc":
        from ..pc.hub import hub
        if not hub.is_online(ctx.tenant_id):
            raise ToolError("PC offline hai. PC par Santosh Desktop chalu kijiye, ya do='phone' se phone par bhejiye.")
        row = await asyncio.to_thread(ms.store_bytes, ctx.tenant_id, name, data, "to_pc")
        try:
            out = await hub.call(ctx.tenant_id, "save_file", {"file_id": row.id, "name": row.name,
                                                              "url": f"/api/pc/fetch/{row.id}"})
        except Exception as e:
            raise ToolError(f"PC par save nahi hua: {e}")
        return {"saved_on_pc": name, **({k: v for k, v in (out or {}).items() if k in ("path", "message")})}
    if do == "read" and (mtype or "").startswith("image/"):
        return await asyncio.to_thread(_read_image, ctx, name, mtype, data)
    out = await asyncio.to_thread(mime.attachment_text, name, mtype, data)
    return {"name": name, "size": len(data), **out}


def _with_signature(ctx: Ctx, body: str, account: str | None) -> tuple[str, str]:
    box = get_box(ctx.tenant_id, account)
    sig = (box.signature or "").strip()
    body = str(body).rstrip()
    if sig and sig not in body:
        body = body + "\n\n" + sig
    return body, box.key


def _resolve(ctx: Ctx, text: str, field: str) -> str:
    if not (text or "").strip():
        return ""
    addrs, problems = contacts.resolve(ctx.tenant_id, text)
    if problems:
        raise ToolError(f"{field}: " + " ".join(problems))
    return addrs


def _when(ctx: Ctx, send_at: str | None):
    if not send_at:
        return None
    from .. import life
    tz = life.tz_of(ctx.tenant_id)
    try:
        dt = life.parse_local(str(send_at), tz)
    except ValueError as e:
        raise ToolError(f"send_at '{send_at}' samajh nahi aaya ({e}). Local time do, jaise 2026-10-20T09:00.")
    if dt < now() + timedelta(minutes=1):
        raise ToolError("send_at aage ka time hona chahiye.")
    if dt > now() + timedelta(days=60):
        raise ToolError("60 din se aage schedule nahi kar sakte.")
    return dt


def _save_draft(ctx: Ctx, **f) -> dict[str, Any]:
    with session() as s:
        d = EmailDraft(tenant_id=ctx.tenant_id, conversation_id=ctx.conversation_id, **f)
        s.add(d)
        s.flush()
        view = ms.draft_view(d)
    bus.publish(ctx.conversation_id, "email_draft", view)
    return view


async def email_draft(ctx: Ctx, body, to=None, cc="", bcc="", subject=None, reply_to_id=None, reply_all=False,
                      attachments=None, send_at=None, follow_up_days=None, account=None, markdown=False,
                      save_to_gmail=False, from_alias=None, **_):
    def work():
        to_addr = _resolve(ctx, to or "", "to")
        cc_addr = _resolve(ctx, cc or "", "cc")
        bcc_addr = _resolve(ctx, bcc or "", "bcc")
        subj = (subject or "").strip()
        in_reply_to = refs = thread_id = None
        acct = account
        kind = "new"
        if reply_to_id:
            orig = ms.read(ctx.tenant_id, str(reply_to_id), mark_seen=False)
            kind = "reply"
            box, _native = ms.split_ref(ctx.tenant_id, str(reply_to_id))
            acct = acct or box.key
            me = box.address
            if not to_addr:
                reply_to = mime.addr_list(orig.get("reply_to"))
                to_addr = reply_to[0][1] if reply_to else orig["from_email"]
            if reply_all:
                others = [a for _, a in mime.addr_list(orig.get("to")) + mime.addr_list(orig.get("cc"))
                          if a not in (me, to_addr) and a not in cc_addr]
                cc_addr = ", ".join([x for x in [cc_addr] + others if x])
            if not subj:
                osub = orig["subject"]
                subj = osub if osub.lower().startswith("re:") else f"Re: {osub}"
            in_reply_to = orig.get("message_id") or None
            refs = orig.get("references") or None
            thread_id = orig.get("thread_id") or None
        if not to_addr:
            raise ToolError("Kis email par bhejna hai? 'to' address ya naam do, ya reply_to_id do.")
        alias = (str(from_alias or "")).strip().lower()
        if alias:                                        # v0.184.0 send-from-alias: check before the card exists
            abox = get_box(ctx.tenant_id, acct)
            ms._alias_verified(ctx.tenant_id, abox, alias)   # raises the honest reconnect / unverified error
        text, key = _with_signature(ctx, body, acct)
        atts = ms.describe_attachments(ctx.tenant_id, attachments)
        when = _when(ctx, send_at)
        return _save_draft(ctx, to_addr=to_addr[:1000], cc_addr=cc_addr[:1000], bcc_addr=bcc_addr[:1000] or None,
                           subject=(subj or "(no subject)")[:500], body=text, in_reply_to=in_reply_to, references=refs,
                           thread_id=thread_id, account=key, kind=kind, attachments=atts or None, send_at=when,
                           follow_up_days=int(follow_up_days) if follow_up_days else None, markdown=bool(markdown),
                           from_alias=alias or None)
    view = await _t(work)
    if save_to_gmail:
        await _t(ms.push_gmail_draft, ctx.tenant_id, str(view["id"]))
    note = "Draft taiyaar hai. User app mein 'Bhejo' dabakar approve karega; tab tak bheja nahi jayega."
    if save_to_gmail:
        note += " Mailbox ke apne Drafts folder mein bhi save kar diya."
    if view.get("send_at_label"):
        note += f" Bhejo dabane par yeh {view['send_at_label']} ko jayega."
    return {"draft_id": view["id"], "to": view["to"], "cc": view["cc"], "subject": view["subject"],
            "attachments": [a["name"] for a in view["attachments"]], "status": "pending_approval", "note": note}


async def email_forward(ctx: Ctx, id, to, cc="", note="", include_attachments=True, **_):
    def work():
        orig = ms.read(ctx.tenant_id, str(id), mark_seen=False)
        box, _ = ms.split_ref(ctx.tenant_id, str(id))
        to_addr = _resolve(ctx, to, "to")
        cc_addr = _resolve(ctx, cc or "", "cc")
        text = (str(note or "").strip() + "\n\n" if note else "") + mime.forward_block(orig)
        text, key = _with_signature(ctx, text, box.key)
        atts = []
        if include_attachments is not False and orig["attachments"]:
            atts = ms.describe_attachments(ctx.tenant_id, [{"email_id": orig["id"], "attachment_id": a["id"]}
                                                          for a in orig["attachments"]])
        subj = orig["subject"]
        subj = subj if subj.lower().startswith(("fwd:", "fw:")) else f"Fwd: {subj}"
        return _save_draft(ctx, to_addr=to_addr, cc_addr=cc_addr, subject=subj[:500], body=text, account=key,
                           kind="forward", attachments=atts or None)
    view = await _t(work)
    return {"draft_id": view["id"], "to": view["to"], "subject": view["subject"],
            "attachments": [a["name"] for a in view["attachments"]], "status": "pending_approval",
            "note": "Forward ka draft card chat mein hai; user Bhejo dabayega."}


async def email_action(ctx: Ctx, ids, action, folder="", **_):
    return await _t(ms.act, ctx.tenant_id, [str(i) for i in ids or []], action, folder or "")


async def email_label(ctx: Ctx, action, name="", new_name="", color="", account=None, **_):
    if action == "delete":
        out = await _t(_bazar, ctx, "confirm_label_delete", {"name": str(name or "")})
        out.setdefault("say", "A confirm card is in the chat; mails stay, only the label goes after the user approves.")
        return out
    return await _t(ms.label_op, ctx.tenant_id, str(action or "list"), str(name or ""), str(new_name or ""),
                    account, str(color or ""))


async def email_drafts(ctx: Ctx, action="list", id=None, limit=10, account=None, to=None, cc=None, subject=None,
                       body=None, markdown=None, **_):
    if action == "delete":
        if not id:
            raise ToolError("Kaunsa draft? id do (email_drafts list se).")
        out = await _t(_bazar, ctx, "confirm_draft_delete", {"id": str(id)})
        out.setdefault("say", "A confirm card is in the chat; the Gmail draft goes only after the user approves.")
        return out
    if action == "read":
        if not id:
            raise ToolError("Kaunsa draft? id do (email_drafts list se).")
        return await _t(ms.gmail_draft_view, ctx.tenant_id, str(id), account)
    if action == "edit":
        if not id:
            raise ToolError("Kaunsa draft? id do (email_drafts list se).")
        if to is None and cc is None and subject is None and body is None:
            raise ToolError("Kya badalna hai? to / cc / subject / body mein se jo badle wahi dijiye.")
        return await _t(ms.gmail_draft_edit, ctx.tenant_id, str(id), None if to is None else str(to),
                        None if cc is None else str(cc), None if subject is None else str(subject),
                        None if body is None else str(body), markdown, account)
    if action == "send":
        if not id:
            raise ToolError("Kaunsa draft? id do (email_drafts list se).")
        out = await _t(_bazar, ctx, "confirm_draft_send", {"id": str(id), "account": account or ""})
        out.setdefault("say", "A confirm card is in the chat; the Gmail draft really goes out only after the user approves.")
        return out
    return await _t(ms.gmail_drafts, ctx.tenant_id, int(limit or 10), account)


def _bazar(ctx: Ctx, tool: str, args: dict) -> dict:
    from ..bazar import service
    from ..bazar.connectors.base import ToolError as BazarError
    try:
        return service.run(ctx.tenant_id, ctx.conversation_id, "santosh-mail", tool, args)
    except BazarError as e:
        raise ToolError(str(e))


async def email_delete(ctx: Ctx, ids, forever=False, **_):
    out = await _t(_bazar, ctx, "confirm_delete", {"ids": [str(i) for i in ids or []], "forever": bool(forever)})
    out.setdefault("say", "A confirm card is in the chat; nothing is deleted until the user approves "
                         "(Trash normally, forever only if the card says so).")
    return out


async def email_filters(ctx: Ctx, action="list", match=None, do=None, filter_id=None, account=None, **_):
    return await _t(ms.filter_op, ctx.tenant_id, str(action or "list"), dict(match or {}), dict(do or {}),
                    str(filter_id or ""), account)


async def email_forwarding(ctx: Ctx, action="list", email="", account=None, **_):
    return await _t(ms.forwarding_op, ctx.tenant_id, str(action or "list"), str(email or ""), account)


async def email_alias(ctx: Ctx, action="list", email="", name="", reply_to="", account=None, **_):
    if action == "remove":
        out = await _t(_bazar, ctx, "confirm_alias_delete", {"email": str(email or ""), "account": account or ""})
        out.setdefault("say", "A confirm card is in the chat; the alias goes only after the user approves.")
        return out
    return await _t(ms.alias_op, ctx.tenant_id, str(action or "list"), str(email or ""), str(name or ""),
                    str(reply_to or ""), account)


async def email_threads(ctx: Ctx, action="list", query="", limit=10, refs=None, id=None, act="", folder="",
                        account=None, **_):
    if action == "list":
        return await _t(ms.threads_list, ctx.tenant_id, str(query or "in:inbox"), int(limit or 10), account)
    if action == "read":
        if not id:
            raise ToolError("Kaunsa conversation? ek mail ka id do (email_check se).")
        return await _t(ms.thread, ctx.tenant_id, str(id))
    if action == "act":
        return await _t(ms.thread_act, ctx.tenant_id, [str(r) for r in refs or []], str(act or ""), folder or "")
    raise ToolError("action: list / read / act")


async def email_follow_up(ctx: Ctx, action, email_id=None, days=3, watch_id=None, **_):
    if action == "list":
        return {"follow_ups": await _t(ms.watches, ctx.tenant_id)}
    if action == "cancel":
        if not watch_id or not await _t(ms.cancel_watch, ctx.tenant_id, str(watch_id)):
            raise ToolError("Woh follow-up nahi mila (ids email_follow_up list se).")
        return {"cancelled": watch_id}
    if not email_id:
        raise ToolError("email_id do (email_check se).")

    def work():
        m = ms.read(ctx.tenant_id, str(email_id), mark_seen=False)
        box, _ = ms.split_ref(ctx.tenant_id, str(email_id))
        mine = m["from_email"] == box.address
        mode = "their_reply" if mine else "my_reply"
        peer = m.get("to") if mine else m.get("from")
        return ms.add_watch(ctx.tenant_id, ctx.conversation_id, box, mode, m.get("message_id", ""), m.get("thread_id", ""),
                            m["subject"], peer or "", float(days or 3), email_ref=m["id"])
    w = await _t(work)
    return {"follow_up": w, "note": ("Will remind if they don't reply." if w["mode"] == "their_reply"
                                     else "Will remind the user to reply if they haven't by then.")}


async def email_bulk(ctx: Ctx, subject, body, source, email_column="", name_column="", attachments=None, account=None, **_):
    prep = await _t(ms.create_bulk, ctx.tenant_id, ctx.conversation_id, str(subject), str(body), dict(source or {}),
                    email_column or "", name_column or "", account, attachments)
    card = await _t(_bazar, ctx, "confirm_bulk", {"bulk_id": prep["bulk_id"]})
    return {**prep, **{k: v for k, v in card.items() if k in ("needs_approval", "approval_id", "card", "say")},
            "note": "Confirm card is in the chat with a sample. Nothing is sent until the user approves."}


async def email_bulk_status(ctx: Ctx, bulk_id, cancel=False, **_):
    if cancel:
        ok = await _t(ms.cancel_bulk, ctx.tenant_id, str(bulk_id))
        if not ok:
            raise ToolError("Yeh bulk email chal nahi raha.")
    v = await _t(ms.bulk_view, ctx.tenant_id, str(bulk_id))
    if v is None:
        raise ToolError("Bulk email nahi mila")
    return {k: v[k] for k in ("id", "status", "subject", "total", "sent", "failed")}


async def email_contacts(ctx: Ctx, query, **_):
    return {"contacts": await _t(contacts.find, ctx.tenant_id, str(query or ""))}


async def email_accounts(ctx: Ctx, account=None, signature=None, make_default=None, daily_summary=None,
                         undo_seconds=None, watch_mode=None, mute=None, signature_push=None, send_as=None,
                         auto_forward=None, imap=None, pop=None, pop_disposition=None, language=None, **_):
    changed = []
    if signature is not None:
        box = await _t(get_box, ctx.tenant_id, account)
        await _t(set_signature, ctx.tenant_id, box.key, signature)
        changed.append(f"signature for {box.address}")
    if make_default:
        box = await _t(get_box, ctx.tenant_id, make_default)
        await _t(set_default, ctx.tenant_id, box.key)
        changed.append(f"default mailbox {box.address}")
    if daily_summary:
        changed.append(await _daily_summary(ctx, str(daily_summary)))
    if undo_seconds is not None:
        n = await _t(ms.set_undo_seconds, ctx.tenant_id, undo_seconds)
        changed.append(f"undo window {n}s" if n else "undo send off")
    if watch_mode:
        await _t(sync.set_watch_mode, ctx.tenant_id, str(watch_mode), account)
        changed.append(f"new-mail announcements: {watch_mode}" + (f" ({account})" if account else ""))
    if mute is not None:
        s = str(mute).strip()
        if s.lower() in ("clear", "off", "band", "hatao", "sab hatao"):
            await _t(sync.mute_edit, ctx.tenant_id, clear=True)
            changed.append("mute list cleared")
        else:
            lst = await _t(sync.mute_edit, ctx.tenant_id, add=[x for x in s.split(",") if x.strip()])
            changed.append(f"{len(lst)} senders muted")
    if signature_push is not None and signature_push is not False:
        box, blocked = await _settings_gate(ctx, account)
        if blocked:
            return blocked
        out_card = await _t(_bazar, ctx, "confirm_signature_push", {"account": box.key, "signature": str(signature or "")})
        out_card.setdefault("say", "A confirm card is in the chat; the signature goes into Gmail only after the user "
                                   "approves.")
        return out_card
    if auto_forward is not None:
        box, blocked = await _settings_gate(ctx, account)
        if blocked:
            return blocked
        s = str(auto_forward).strip()
        enable = s.lower() not in ("off", "band", "no", "0", "false")
        out_card = await _t(_bazar, ctx, "confirm_auto_forward", {"enable": enable, "to": s if enable else "",
                                                                  "account": box.key})
        out_card.setdefault("say", "A confirm card is in the chat; Gmail's own forwarding changes only after the user "
                                   "approves.")
        return out_card
    if imap is not None:                                   # v0.186.0 Gmail's IMAP / POP / language settings
        box, blocked = await _settings_gate(ctx, account)
        if blocked:
            return blocked
        if str(imap).strip().lower() == "get":
            out = await _t(ms.settings_status, ctx.tenant_id, box.key)
            return {"imap": out.get("imap"), "account": out.get("account"),
                    "note": "'on' / 'off' se badal sakte hain."}
        return await _t(ms.imap_set, ctx.tenant_id, box.key, str(imap).strip().lower() == "on")
    if pop is not None:
        box, blocked = await _settings_gate(ctx, account)
        if blocked:
            return blocked
        if str(pop).strip().lower() == "get":
            out = await _t(ms.settings_status, ctx.tenant_id, box.key)
            return {"pop": out.get("pop"), "account": out.get("account"),
                    "note": "'off' / 'all' / 'from_now_on' se badal sakte hain."}
        return await _t(ms.pop_set, ctx.tenant_id, box.key, str(pop).strip().lower(),
                        str(pop_disposition or "leave_in_inbox"))
    if language is not None:
        box, blocked = await _settings_gate(ctx, account)
        if blocked:
            return blocked
        if str(language).strip().lower() == "get":
            out = await _t(ms.settings_status, ctx.tenant_id, box.key)
            return {"language": out.get("language"), "account": out.get("account"),
                    "note": "Naya code dijiye (hi / en / en-GB / mr / ta)."}
        return await _t(ms.language_set, ctx.tenant_id, box.key, str(language))
    out: dict[str, Any] = {"mailboxes": await _t(views, ctx.tenant_id),
                           "watch": await _t(sync.watch_views, ctx.tenant_id),
                           "muted": await _t(sync.muted, ctx.tenant_id)}
    if send_as:
        out["settings"] = await _t(ms.settings_status, ctx.tenant_id, account)
    if changed:
        out["changed"] = changed
    if not out["mailboxes"]:
        out["note"] = "No mailbox connected. Tell the user: Santosh app > Profile > Email > Gmail / Outlook / Other email."
    return out


SUMMARY_TITLE = "Inbox summary"
SUMMARY_WEEK_TITLE = "Weekly inbox summary"


async def _daily_summary(ctx: Ctx, at: str) -> str:
    """v0.181.0 the daily inbox summary; v0.184.0 'weekly 09:00' makes it a weekly digest instead."""
    from sqlalchemy import select
    from .. import life
    from ..db import Routine
    from .life_tools import create_routine
    with session() as s:
        for r in s.scalars(select(Routine).where(Routine.tenant_id == ctx.tenant_id, Routine.status == "active",
                                                 Routine.title.in_([SUMMARY_TITLE, SUMMARY_WEEK_TITLE]))).all():
            r.status = "cancelled"
    at = at.strip().lower()
    if at in ("off", "band", "no", "stop", "none"):
        bus.publish(ctx.conversation_id, "routines", {"routines": life.active_routines(ctx.tenant_id)})
        return "inbox summary off"
    weekly = at.split()[0] in ("weekly", "week", "weekly:", "weekly-") if at.split() else False
    when = " ".join(at.split()[1:]) if weekly else at
    try:
        hh, mm = [int(x) for x in when.split(":")[:2]]
    except ValueError:
        raise ToolError("daily_summary: time like '09:00', 'weekly 09:00', or 'off'")
    from datetime import datetime as _dt
    tz = life.tz_of(ctx.tenant_id)
    local = _dt.now(tz)
    first = local.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if first <= local:
        first += timedelta(days=1)
    if weekly:
        await create_routine(ctx, title=SUMMARY_WEEK_TITLE, repeat="weekly", first_run=first.strftime("%Y-%m-%dT%H:%M"),
                             instruction=("Use email_triage (last 7 days, unread_only=false) and give me my WEEKLY "
                                          "inbox digest: the mails that still need my reply (one line each), bills or "
                                          "payments due soon, anything important I may have missed, how many "
                                          "newsletters/bulk mails came in, and the top senders of the week. Never read "
                                          "out OTPs. End by offering to draft the pending replies."))
        return f"weekly inbox digest at {hh:02d}:{mm:02d}"
    await create_routine(ctx, title=SUMMARY_TITLE, repeat="daily", first_run=first.strftime("%Y-%m-%dT%H:%M"),
                         instruction=("Use email_triage (last 24 hours) and give me my inbox summary: who needs my reply "
                                      "(one line each), bills or payments due, anything important; one line for how many "
                                      "newsletters. Never read out OTPs. End by offering to draft the replies."))
    return f"daily inbox summary at {hh:02d}:{mm:02d}"


async def email_rule(ctx: Ctx, action="list", name="", match=None, actions=None, rule_id=None, account=None,
                     kind="rule", **_):
    if action == "create" and (str(kind or "rule")).strip().lower() == "search":
        out = await _t(sync.search_save, ctx.tenant_id, str(name or ""), dict(match or {}))
        return {**out, "note": "Saved search taiyaar hai. Boliye 'is naam se dikhao' aur main use chala dunga — "
                               "yeh sirf dikhata hai, kuch nahi badalta."}
    if action == "create":
        out = await _t(sync.rule_create, ctx.tenant_id, str(name or ""), dict(match or {}), dict(actions or {}))
        return {**out, "note": "Rule chalu hai. Ab se aane wali nayi mail par chalega (purani mail par nahi). "
                               "forward_to wala rule sirf draft banata hai — bhejna hamesha user ke Bhejo par."}
    if action == "searches":
        return {"searches": await _t(sync.searches_list, ctx.tenant_id),
                "note": "Saved searches: 'run' se chal sakta hai, delete se hata sakta hai. Run sirf dikhata hai "
                        "jo ABHI match hota hai — kuch nahi badalta."}
    if action == "run":
        if not rule_id:
            raise ToolError("Kaunsa saved search? rule_id do (email_rule action='searches' se).")
        return await _t(sync.search_run, ctx.tenant_id, str(rule_id), account)
    if action in ("pause", "resume"):
        if not rule_id:
            raise ToolError("Kaunsa rule? rule_id do (email_rule list se).")
        out = await _t(sync.rule_edit, ctx.tenant_id, str(rule_id), action == "resume")
        return {**out, "note": "Rule " + ("chalu kar diya." if action == "resume" else "roka (delete nahi hua).")}
    if action == "delete":
        if not rule_id or not await _t(sync.rule_delete, ctx.tenant_id, str(rule_id)):
            raise ToolError("Woh rule / saved search nahi mila (ids email_rule list ya searches se).")
        return {"deleted": rule_id}
    if action == "test":
        if not rule_id:
            raise ToolError("Kaunsa rule? rule_id do (email_rule list se).")
        return await _t(sync.rule_test, ctx.tenant_id, str(rule_id), account)
    return {"rules": await _t(sync.rules_list, ctx.tenant_id),
            "note": "Rules nayi mail par chalte hain. Kaam: label, archive, star, mark_read, important, mute, "
                    "notify; forward_to sirf draft banata hai (Santosh khud kabhi nahi bhejta). "
                    "Saved searches ke liye action='searches'."}


def _snooze_when(ctx: Ctx, when, hours, days):
    from datetime import timedelta as _td
    if when:
        return _when(ctx, str(when))
    try:
        h = float(hours or 0)
    except (TypeError, ValueError):
        h = 0.0
    try:
        d = float(days or 0)
    except (TypeError, ValueError):
        d = 0.0
    if h <= 0 and d <= 0:
        raise ToolError("Kab wapas laaun? when (local time) ya hours ya days do.")
    return now() + _td(hours=h) + _td(days=d)


async def email_snooze(ctx: Ctx, action="list", email_id=None, when=None, hours=None, days=None, snooze_id=None, **_):
    if action == "list":
        return {"snoozed": await _t(sync.snooze_list, ctx.tenant_id)}
    if action == "cancel":
        if not snooze_id or not await _t(sync.snooze_cancel, ctx.tenant_id, str(snooze_id)):
            raise ToolError("Woh snooze nahi mila (ids email_snooze list se).")
        return {"cancelled": snooze_id, "note": "Mail wapas inbox mein aa gayi (unread)."}
    if not email_id:
        raise ToolError("Kaunsi email? email_id do (email_check se).")
    wake = _snooze_when(ctx, when, hours, days)
    out = await _t(sync.snooze_add, ctx.tenant_id, ctx.conversation_id, str(email_id), wake)
    return {**out, "note": f"Mail inbox se hata di; {out['wake_label']} par wapas aayegi (unread mark ho gi)."}


async def _settings_gate(ctx: Ctx, account=None):
    """Resolve the settings mailbox and check it granted gmail.settings.basic; old mailboxes get the honest
    reconnect note instead of a card that can only fail."""
    box = await _t(ms.settings_gmail, ctx.tenant_id, account or None)
    if not await _t(settings_scope_ok, ctx.tenant_id, box):
        return box, {"scope_ok": False, "account": box.address, "note": settings_scope_message(box.address),
                     "say": "Is Gmail ne settings ki permission abhi nahi di — ek baar Profile > Email se is Gmail ko "
                            "dobara jodna hoga (mail sab waisi hi chalegi)."}
    return box, None


async def email_vacation(ctx: Ctx, action="get", enable=None, message="", subject="", start=None, end=None,
                         contacts_only=False, account=None, **_):
    if action == "set":
        _box, blocked = await _settings_gate(ctx, account)
        if blocked:
            return blocked
        on = bool(enable)
        out_card = await _t(_bazar, ctx, "confirm_vacation", {"enable": on, "message": str(message or ""),
                                                              "subject": str(subject or ""), "start": str(start or ""),
                                                              "end": str(end or ""),
                                                              "contacts_only": bool(contacts_only),
                                                              "account": _box.key})
        out_card.setdefault("say", "A confirm card is in the chat; the vacation reply changes only after the user "
                                   "approves.")
        return out_card
    return await _t(ms.vacation_get, ctx.tenant_id, account)


EMAIL_HANDLERS = {"email_check": email_check, "email_read": email_read, "email_thread": email_thread,
                  "email_triage": email_triage,
                  "email_attachment": email_attachment, "email_draft": email_draft, "email_forward": email_forward,
                  "email_action": email_action, "email_label": email_label, "email_drafts": email_drafts,
                  "email_filters": email_filters, "email_forwarding": email_forwarding,
                  "email_alias": email_alias, "email_threads": email_threads,
                  "email_delete": email_delete, "email_follow_up": email_follow_up,
                  "email_bulk": email_bulk, "email_bulk_status": email_bulk_status, "email_contacts": email_contacts,
                  "email_accounts": email_accounts, "email_rule": email_rule, "email_snooze": email_snooze,
                  "email_vacation": email_vacation}
