"""v0.182.0 "Mail aayi!": the proactive mail watcher, her inbox rules and snooze.

Every 60 seconds (worker.mail_jobs) each connected mailbox is checked for NEW mail: Gmail through the official
users.history.list with a stored historyId watermark, IMAP/Outlook through a since-watermark listing. New mail is
run through HER rules (label / archive / star / mark read / important / mute / forward-as-draft), then — only if her
watch mode wants it — announced once into her chat as an email_new card (bus.publish also pushes it to the phone).

Safety: the watcher is read-only plus reversible organising. It NEVER sends mail (a forward rule only prepares a
draft for her Bhejo tap), never deletes, never replies, and never reads out OTP codes (digits are masked).
Everything is tenant-scoped: watermarks, rules, snoozes and mutes all carry the tenant id.
The first pass on a fresh mailbox is silent calibration (watermark bharo, khabar nahi) — nobody gets a flood of
old mail on connecting or on deploying.
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import or_, select

from .. import convs
from ..db import (MailAccount, MailContact, MailRule, MailSetting, MailSnooze, MailSyncState, as_utc, now, session)
from ..events import bus
from . import mime
from .accounts import get_box
from .base import Box, MailError, NotConnected
from .service import OTP_RE, classify, draft_view, split_ref

log = logging.getLogger("santosh.mailbox.sync")

MODES = ("off", "vip", "all")
ACTION_KEYS = ("label", "archive", "star", "important", "mark_read", "mute", "notify", "forward_to")
MATCH_KEYS = ("from", "subject", "has_attachment", "bulk", "unread")
SEARCH_KEYS = ("from", "subject", "has_attachment", "bulk", "unread", "query")   # v0.184.0 saved searches
RECENT_KEEP = 60
FALLBACK_HOURS = 6          # expired history: at most this far back re-list
TS_OVERLAP = timedelta(minutes=2)   # watermark back-dated a little; recent-ids catch the borderline mails
SNOOZE_MIN = timedelta(minutes=5)
SNOOZE_MAX = timedelta(days=30)


# ---------------- watch modes + mute list ----------------
def _state_row(s, tenant: str, account: str) -> MailSyncState:
    row = s.get(MailSyncState, (tenant, account))
    if row is None:
        row = MailSyncState(tenant_id=tenant, account=account, mode="vip")
        s.add(row)
        s.flush()
    return row


def _boxes(tenant: str) -> list[Box]:
    """Call-time lookup: tests (and hot config) may swap the boxes list."""
    from . import accounts as ma
    return ma.boxes(tenant)


def watch_views(tenant: str) -> list[dict[str, Any]]:
    out = []
    with session() as s:
        rows = {r.account: r for r in s.scalars(select(MailSyncState).where(MailSyncState.tenant_id == tenant)).all()}
    for b in _boxes(tenant):
        r = rows.get(b.key)
        out.append({"key": b.key, "address": b.address, "kind": b.kind,
                    "mode": (r.mode if r else "vip"),
                    "last_sync": as_utc(r.last_sync_at).isoformat() if r and r.last_sync_at else None,
                    "error": (r.last_error or "") if r else ""})
    return out


def set_watch_mode(tenant: str, mode: str, account: str | None = None) -> list[dict[str, Any]]:
    mode = (mode or "").strip().lower()
    if mode not in MODES:
        raise MailError(f"watch_mode: {' / '.join(MODES)} mein se ek "
                        f"(off = koi khabar nahi, vip = zaroori + apne log [default], all = sab)")
    with session() as s:
        if account:
            targets = [_state_row(s, tenant, get_box(tenant, account).key)]
        else:
            targets = [_state_row(s, tenant, b.key) for b in _boxes(tenant)]
        for st in targets:
            was_off = st.mode == "off"
            st.mode = mode
            if was_off and mode != "off":
                # off ke dour ki mail par toofan nahi: ab se khabar milegi (Gmail jaisa)
                st.last_ts = now()
    return watch_views(tenant)


def _muted_row(s, tenant: str) -> MailSetting:
    row = s.get(MailSetting, (tenant, "muted"))
    if row is None:
        row = MailSetting(tenant_id=tenant, key="muted", value="[]")
        s.add(row)
        s.flush()
    return row


def muted(tenant: str) -> list[str]:
    with session() as s:
        try:
            return [a for a in json.loads(_muted_row(s, tenant).value or "[]") if a]
        except Exception:
            return []


def mute_edit(tenant: str, add: list[str] | None = None, clear: bool = False) -> list[str]:
    with session() as s:
        row = _muted_row(s, tenant)
        try:
            cur = [a for a in json.loads(row.value or "[]") if a]
        except Exception:
            cur = []
        if clear:
            cur = []
        for a in add or []:
            a = (a or "").strip().lower()
            if "@" in a and a not in cur:
                cur.append(a)
        row.value = json.dumps(cur[:200])
        return cur


# ---------------- rules ----------------
def rule_view(r: MailRule) -> dict[str, Any]:
    return {"id": r.id, "name": r.name, "enabled": bool(r.enabled), "match": dict(r.match or {}),
            "actions": dict(r.actions or {}), "hits": int(r.hits or 0), "kind": (r.kind or "rule")}


def rules_list(tenant: str) -> list[dict[str, Any]]:
    with session() as s:
        return [rule_view(r) for r in s.scalars(select(MailRule)
                                                .where(MailRule.tenant_id == tenant,
                                                       or_(MailRule.kind == "rule", MailRule.kind.is_(None)))
                                                .order_by(MailRule.created_at)).all()]


def _clean(v: Any, cap: int = 120) -> str:
    return re.sub(r"\s+", " ", str(v or "").strip())[:cap]


def rule_create(tenant: str, name: str, match: dict, actions: dict) -> dict[str, Any]:
    match = {k: v for k, v in (match or {}).items() if k in MATCH_KEYS and v not in (None, "", [], False)}
    actions = {k: v for k, v in (actions or {}).items() if k in ACTION_KEYS and v not in (None, "", [], False)}
    if not match:
        raise MailError("Rule mein koi shart nahi hai. from / subject / has_attachment / bulk / unread mein se kuch dijiye.")
    if not actions:
        raise MailError("Rule mein koi kaam nahi hai. label / archive / star / mark_read / important / mute / "
                        "notify / forward_to mein se kuch dijiye.")
    m = {"from": _clean(match.get("from")), "subject": _clean(match.get("subject")),
         "has_attachment": bool(match.get("has_attachment")), "bulk": bool(match.get("bulk")),
         "unread": bool(match.get("unread"))}
    m = {k: v for k, v in m.items() if v not in ("", False)}
    a: dict[str, Any] = {}
    if actions.get("label"):
        a["label"] = _clean(actions["label"], 60)
    for k in ("archive", "star", "mark_read", "mute", "notify"):
        if actions.get(k):
            a[k] = True
    if "important" in actions:
        a["important"] = bool(actions["important"])
    if actions.get("forward_to"):
        a["forward_to"] = _clean(actions["forward_to"], 320)
    if a.get("mute") and (a.get("notify") or a.get("forward_to")):
        raise MailError("Ek rule mute aur notify / forward saath nahi kar sakta.")
    with session() as s:
        r = MailRule(tenant_id=tenant, name=_clean(name, 120) or "Rule", match=m, actions=a)
        s.add(r)
        s.flush()
        return rule_view(r)


def rule_edit(tenant: str, rid: str, enabled: bool) -> dict[str, Any]:
    with session() as s:
        r = s.get(MailRule, rid)
        if r is None or r.tenant_id != tenant:
            raise MailError("Woh rule nahi mila (ids email_rule list se).")
        r.enabled = bool(enabled)
        return rule_view(r)


def rule_delete(tenant: str, rid: str) -> bool:
    with session() as s:
        r = s.get(MailRule, rid)
        if r is None or r.tenant_id != tenant:
            return False
        s.delete(r)
    return True


def matches(rule: MailRule | dict, item: dict[str, Any]) -> bool:
    m = rule if isinstance(rule, dict) else dict(rule.match or {})
    if m.get("from"):
        want = [w.strip().lower() for w in str(m["from"]).split(",") if w.strip()]
        frm = f"{item.get('from_email', '')} {item.get('from', '')}".lower()
        if not any(w in frm for w in want):
            return False
    if m.get("subject"):
        want = [w.strip().lower() for w in str(m["subject"]).split(",") if w.strip()] or \
               [w for w in str(m["subject"]).lower().split() if w]
        subj = f"{item.get('subject', '')} {item.get('snippet', '')}".lower()
        if not all(w in subj for w in want):
            return False
    if m.get("has_attachment") and not item.get("has_attachments"):
        return False
    if m.get("bulk") and not item.get("bulk"):
        return False
    if m.get("unread") and not item.get("unread"):
        return False
    return True


def rules_for(tenant: str) -> list[MailRule]:
    """The watcher's rules only — saved searches (kind='search') never run on new mail."""
    with session() as s:
        rows = s.scalars(select(MailRule).where(MailRule.tenant_id == tenant, MailRule.enabled.is_(True),
                                                or_(MailRule.kind == "rule", MailRule.kind.is_(None)))
                         .order_by(MailRule.created_at)).all()
        for r in rows:
            s.expunge(r)
        return rows


def rule_test(tenant: str, rid: str, account: str | None = None, limit: int = 15) -> dict[str, Any]:
    """Dry-run one rule against the newest inbox mail (kuch badalta nahi)."""
    with session() as s:
        r = s.get(MailRule, rid)
        if r is None or r.tenant_id != tenant:
            raise MailError("Woh rule nahi mila (ids email_rule list se).")
        rule = dict(r.match or {})
        name = r.name
    box = get_box(tenant, account)
    items = box.list("inbox", False, None, max(1, min(int(limit or 15), 50)), None, True)
    hit = [{"id": f"{box.key}~{it['id']}", "from": it.get("from"), "subject": it.get("subject")}
           for it in items if matches(rule, it)]
    return {"rule": name, "account": box.address, "checked": len(items), "matches": hit[:max(1, min(int(limit or 15), 50))]}


# ---------------- v0.184.0 saved searches (email_rule kind=search) ----------------
def search_save(tenant: str, name: str, match: dict) -> dict[str, Any]:
    """A named search she can run again any time ('bank ki mails dikhao'): the same match words as a rule, plus
    query = a raw Gmail search string ('from:hdfcbank has:attachment') for Gmail mailboxes. Read-only: running it
    lists what matches NOW; nothing is moved, nothing is announced."""
    m: dict[str, Any] = {}
    for k in ("from", "subject", "query"):
        if str(match.get(k) or "").strip():
            m[k] = _clean(match[k], 300)
    for k in ("has_attachment", "bulk", "unread"):
        if match.get(k):
            m[k] = True
    if not m:
        raise MailError("Kya dhoondhna hai? from / subject / query (Gmail search) / has_attachment / bulk / unread "
                        "mein se kuch dijiye.")
    with session() as s:
        r = MailRule(tenant_id=tenant, name=_clean(name, 120) or "Search", match=m, actions={}, kind="search")
        s.add(r)
        s.flush()
        return rule_view(r)


def searches_list(tenant: str) -> list[dict[str, Any]]:
    with session() as s:
        return [rule_view(r) for r in s.scalars(select(MailRule).where(MailRule.tenant_id == tenant,
                                                                       MailRule.kind == "search")
                                                .order_by(MailRule.created_at)).all()]


def search_run(tenant: str, rid: str, account: str | None = None, limit: int = 15) -> dict[str, Any]:
    with session() as s:
        r = s.get(MailRule, rid)
        if r is None or r.tenant_id != tenant or (r.kind or "rule") != "search":
            raise MailError("Woh saved search nahi mila (ids email_rule action='searches' se).")
        m, name, enabled = dict(r.match or {}), r.name, bool(r.enabled)
    if not enabled:
        raise MailError(f"'{name}' saved search roka hua hai (email_rule resume se chalu kijiye).")
    limit = max(1, min(int(limit or 15), 50))
    box = get_box(tenant, account)
    q = m.get("query", "")
    if q and box.kind == "gmail":                       # raw Gmail search, straight to the provider
        items = box.list("search", bool(m.get("unread")), q, limit)
    else:
        if q and not any(k in m for k in ("from", "subject", "has_attachment", "bulk", "unread")):
            raise MailError("Yeh saved search Gmail ke apne syntax mein hai; is mailbox par from / subject wale "
                            "search hi chalte hain.")
        items = [it for it in box.list("inbox", bool(m.get("unread")), None, limit * 3, None, True)
                 if matches(m, it)][:limit]
    return {"search": name, "account": box.address, "count": len(items),
            "emails": [{"id": f"{box.key}~{it['id']}", "from": it.get("from"), "subject": it.get("subject"),
                        "date": it.get("date", ""), "unread": bool(it.get("unread")),
                        "snippet": (it.get("snippet") or "")[:160]} for it in items]}


def _apply_rule_actions(tenant: str, box: Box, native: str, actions: dict[str, Any], item: dict[str, Any],
                        conv: str) -> None:
    """Do the rule's mailbox actions (all reversible); a forward becomes a DRAFT, never a send."""
    gmail = box.kind == "gmail"
    if actions.get("label"):
        try:
            if gmail:
                box.apply_label([native], str(actions["label"]))
            else:
                box.move([native], str(actions["label"]))
        except MailError as e:
            log.warning("rule label '%s' nahi lagi: %s", actions["label"], e)
    if actions.get("archive"):
        box.archive([native])
    if actions.get("star"):
        box.star([native], True)
    if actions.get("mark_read"):
        box.mark([native], True)
    if gmail and "important" in actions:
        try:
            box.mark_important([native], bool(actions["important"]))
        except MailError:
            pass
    if actions.get("forward_to") and conv:
        try:
            _forward_draft(tenant, conv, box, f"{box.key}~{native}", str(actions["forward_to"]), item)
        except Exception as e:
            log.warning("rule forward draft nahi bana: %s", e)


def _forward_draft(tenant: str, conv: str, box: Box, ref: str, to_addr: str, item: dict[str, Any]) -> None:
    """A rule's forward = a ready draft card in her chat. She taps Bhejo; Santosh never sends by himself."""
    from ..db import EmailDraft
    from . import service as ms
    try:
        orig = ms.read(tenant, ref, mark_seen=False)
    except (MailError, NotConnected):
        orig = {"from": "", "from_email": "", "to": "", "subject": item.get("subject", ""), "body": "", "date": ""}
    body = "Aapke rule ke hisaab se aapko forward kar raha hoon.\n\n" + mime.forward_block(orig)
    body += "\n(Is draft mein attachments nahi hain; original mail inbox mein hai.)"
    subj = orig.get("subject") or item.get("subject") or "(no subject)"
    subj = subj if subj.lower().startswith(("fwd:", "fw:")) else f"Fwd: {subj}"
    with session() as s:
        d = EmailDraft(tenant_id=tenant, conversation_id=conv, to_addr=to_addr[:1000], subject=subj[:500],
                       body=body[:50000], account=box.key, kind="forward")
        s.add(d)
        s.flush()
        view = draft_view(d)
    bus.publish(conv, "email_draft", view)


# ---------------- snooze ----------------
def _tz(tenant: str):
    try:
        from ..life import tz_of
        return tz_of(tenant)
    except Exception:
        return timezone(timedelta(hours=5, minutes=30))


def snooze_view(w: MailSnooze) -> dict[str, Any]:
    wake = as_utc(w.wake_at)
    return {"id": w.id, "email_ref": w.email_ref, "subject": w.subject, "peer": w.peer, "status": w.status,
            "wake_at": wake.isoformat(), "wake_label": wake.astimezone(_tz(w.tenant_id)).strftime("%d %b, %I:%M %p")}


def _read_quiet(tenant: str, ref: str) -> dict[str, Any]:
    from . import service as ms
    try:
        return ms.read(tenant, ref, mark_seen=False)
    except Exception:
        return {"from": "", "from_email": "", "to": "", "subject": "", "body": "", "attachments": [], "date": ""}


def snooze_add(tenant: str, conv: str, email_ref: str, wake_at: datetime) -> dict[str, Any]:
    box, native = split_ref(tenant, email_ref)
    if wake_at < now() + SNOOZE_MIN - timedelta(seconds=30):
        raise MailError("Snooze ka time aage ka hona chahiye (kam se kam 5 minute aage).")
    if wake_at > now() + SNOOZE_MAX:
        raise MailError("Snooze 30 din se aage nahi hota.")
    m = _read_quiet(tenant, email_ref)
    with session() as s:
        w = MailSnooze(tenant_id=tenant, conversation_id=conv or "", account=box.key, email_ref=email_ref[:300],
                       message_id=(m.get("message_id") or "")[:500], subject=(m.get("subject") or "")[:500],
                       peer=(m.get("from") or m.get("from_email") or "")[:320], wake_at=wake_at)
        s.add(w)
        s.flush()
        view = snooze_view(w)
    try:
        box.archive([native])            # inbox se bahar jab tak wake time na ho (wapas laaya ja sakta hai)
    except MailError:
        pass
    return view


def _wake(tenant: str, w: MailSnooze) -> None:
    """Bring one snoozed mail back: unarchive + mark unread + a reminder card in her chat."""
    try:
        box = get_box(tenant, w.account or None)
        native = w.email_ref.split("~", 1)[-1] if "~" in w.email_ref else w.email_ref
        try:
            box.move([native], "inbox")
        except MailError:
            pass
        try:
            box.mark([native], False)
        except MailError:
            pass
    except (MailError, NotConnected) as e:
        log.warning("snooze wake %s: mailbox nahi khula: %s", w.id, e)
    with session() as s:
        row = s.get(MailSnooze, w.id)
        if row is None or row.status != "snoozed":
            return
        row.status = "woken"
    if w.conversation_id:
        bus.publish(w.conversation_id, "email_snooze", {"id": w.id, "status": "woken", "subject": w.subject,
                                                        "peer": w.peer, "email_ref": w.email_ref})
        from ..events import notify
        notify(w.conversation_id, f"Snooze khatam: \"{w.subject}\" ({w.peer or 'mail'}) wapas inbox mein hai.")


def snooze_list(tenant: str) -> list[dict[str, Any]]:
    with session() as s:
        rows = s.scalars(select(MailSnooze).where(MailSnooze.tenant_id == tenant, MailSnooze.status == "snoozed")
                         .order_by(MailSnooze.wake_at)).all()
        return [snooze_view(w) for w in rows]


def snooze_cancel(tenant: str, sid: str) -> bool:
    """Cancel = wapas abhi (the mail returns to the inbox at once)."""
    with session() as s:
        w = s.get(MailSnooze, sid)
        if w is None or w.tenant_id != tenant or w.status != "snoozed":
            return False
        s.expunge(w)
    _wake(tenant, w)
    return True


def snooze_tick(limit: int = 20) -> int:
    with session() as s:
        due = [(w.id, w.tenant_id) for w in s.scalars(select(MailSnooze)
                                                      .where(MailSnooze.status == "snoozed", MailSnooze.wake_at <= now())
                                                      .order_by(MailSnooze.wake_at).limit(limit)).all()]
    n = 0
    for sid, tenant in due:
        try:
            with session() as s:
                w = s.get(MailSnooze, sid)
                s.expunge(w)
            _wake(tenant, w)
            n += 1
        except Exception:
            log.exception("snooze wake failed")
    return n


# ---------------- the watcher itself ----------------
def _vip_senders(tenant: str) -> set[str]:
    """People she has actually mailed (the learned address book) — 'apne log'."""
    with session() as s:
        return set(s.scalars(select(MailContact.email).where(MailContact.tenant_id == tenant,
                                                             MailContact.sent_to > 0)).all())


def _important(item: dict[str, Any], known: set[str]) -> bool:
    if item.get("important"):
        return True
    cat, _why = classify(item, known)
    return cat in ("needs_reply", "bills_payments")


def _masked(text: str) -> str:
    return re.sub(r"\b\d{4,8}\b", "••••", text or "")


def _announce(tenant: str, conv: str, item: dict[str, Any], ref: str, account: str) -> None:
    if not conv:
        return
    otp = bool(OTP_RE.search(f"{item.get('subject', '')} {item.get('snippet', '')}"))
    bus.publish(conv, "email_new", {
        "id": ref, "account": account, "from": item.get("from"), "from_email": item.get("from_email"),
        "subject": _masked(item.get("subject", "")) or "(no subject)",
        "snippet": _masked(item.get("snippet", ""))[:200], "unread": bool(item.get("unread")),
        "important": bool(item.get("important")), "bulk": bool(item.get("bulk")),
        "thread_id": item.get("thread_id", ""), "otp": otp, "at": now().isoformat()})


def _wants_announce(rule_notify: bool, item: dict[str, Any], known: set[str], mode: str) -> bool:
    if rule_notify:
        return True
    if item.get("bulk"):
        return False
    if OTP_RE.search(f"{item.get('subject', '')} {item.get('snippet', '')}"):
        return True                              # login/OTP alerts are always worth one line (digits stay masked)
    if mode == "vip":
        return _important(item, known) or item.get("from_email", "").lower() in known
    return True


def _new_from_history(box: Box, start_id: str) -> tuple[list[str], str]:
    """Gmail: ids of mail added to the inbox since the watermark (oldest first) + the new watermark."""
    ids: list[str] = []
    page_token, new_wm = None, start_id
    for _page in range(3):
        out = box.history(start_id) if not page_token else box.history(start_id, page_token=page_token)
        new_wm = str(out.get("historyId") or new_wm)
        for h in out.get("history", []):
            for ma in h.get("messagesAdded", []):
                m = ma.get("message") or {}
                labels = m.get("labelIds") or []
                if "INBOX" not in labels or "SENT" in labels or "DRAFT" in labels or "CHAT" in labels:
                    continue
                if m.get("id"):
                    ids.append(m["id"])
        page_token = out.get("nextPageToken")
        if not page_token:
            break
    seen, uniq = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i)
            uniq.append(i)
    return uniq, new_wm


def _summary_of(box: Box, native: str) -> dict[str, Any] | None:
    """One Gmail mail's summary for the announcement (one metadata call)."""
    if box.kind != "gmail":
        return None
    try:
        m = box._req("GET", f"/messages/{native}",
                     params=[("format", "metadata")] + [("metadataHeaders", h) for h in
                                                        ("From", "To", "Subject", "Date", "Message-ID",
                                                         "List-Unsubscribe", "Precedence", "Auto-Submitted")])
        return box._summary(m)
    except MailError:
        return None


def _mark(tenant: str, account: str, error: str = "", wm: str | None = None) -> None:
    with session() as s:
        st = _state_row(s, tenant, account)
        st.last_sync_at = now()
        st.last_ts = now() - TS_OVERLAP
        if wm:
            st.history_id = str(wm)
        st.last_error = (error or "")[:500]


def _save_recent(tenant: str, account: str, native_ids: list[str], recent: list[str]) -> None:
    keep = [n for n in recent if n not in native_ids] + [n for n in native_ids if n not in recent]
    with session() as s:
        _state_row(s, tenant, account).recent = keep[-RECENT_KEEP:]


def sync_account(tenant: str, box: Box) -> int:
    """One mailbox's check: new mail -> rules -> (maybe) announce. Returns how many mails were announced."""
    with session() as s:
        st = _state_row(s, tenant, box.key)
        mode, wm, last_ts = st.mode, st.history_id, as_utc(st.last_ts)
        recent = [str(x) for x in (st.recent or [])]
        calibrated = bool(wm or last_ts)
    if mode == "off":
        _mark(tenant, box.key)
        return 0
    items_map: dict[str, dict[str, Any]] = {}
    new_wm: str | None = None
    try:
        if box.kind == "gmail":
            prof = box.profile()
            new_wm = str(prof.get("historyId") or wm or "")
            if wm:
                try:
                    ids, new_wm = _new_from_history(box, wm)
                except MailError:            # historyId expired (purged) -> safe fallback listing below
                    ids, wm = [], ""
                for nid in ids:
                    sm = _summary_of(box, nid)
                    if sm:
                        items_map[nid] = sm
            if not items_map and not wm:     # first run or expired history: a plain recent listing
                since = last_ts or (now() - timedelta(hours=FALLBACK_HOURS))
                for it in box.list("inbox", False, None, 25, since, True):
                    items_map[it["id"]] = it
        elif last_ts:
            for it in box.list("inbox", False, None, 25, last_ts, True):
                items_map[it["id"]] = it
    except (MailError, NotConnected) as e:
        _mark(tenant, box.key, error=str(e))
        return 0
    except Exception as e:
        _mark(tenant, box.key, error=f"{type(e).__name__}: {e}")
        return 0
    _mark(tenant, box.key, wm=new_wm)
    native_ids = list(items_map)
    fresh = [(nid, items_map[nid]) for nid in native_ids if nid not in recent]
    if not fresh or not calibrated:          # pehli baar: watermark bharo, khabar nahi
        _save_recent(tenant, box.key, native_ids, recent)
        return 0
    conv = convs.current(tenant)
    rules = rules_for(tenant)
    mute = set(muted(tenant))
    known = _vip_senders(tenant)
    from . import contacts
    announced = 0
    ordered = sorted(fresh, key=lambda x: x[1].get("date", ""))
    for native, item in ordered:
        contacts.learn(tenant, [(item.get("from", ""), item.get("from_email", ""))],
                       0.2 if not item.get("bulk") else 0)
        rule_notify = rule_mute = rule_acted = False
        for r in rules:
            if not matches(r, item):
                continue
            try:
                _apply_rule_actions(tenant, box, native, dict(r.actions or {}), item, conv)
            except MailError as e:
                log.warning("rule %s actions failed: %s", r.id, e)
            with session() as s:
                row = s.get(MailRule, r.id)
                if row:
                    row.hits = (row.hits or 0) + 1
            rule_acted = True
            rule_notify |= bool((r.actions or {}).get("notify"))
            rule_mute |= bool((r.actions or {}).get("mute"))
            if rule_mute:
                break
        if rule_mute or item.get("from_email", "").lower() in mute:
            continue
        # a rule works quietly; only its notify action (or a rule-less mail her watch mode wants) makes a card
        if rule_notify or (not rule_acted and _wants_announce(False, item, known, mode)):
            _announce(tenant, conv, item, f"{box.key}~{native}", box.address)
            announced += 1
    if mode == "all" and conv:
        bulk_n = sum(1 for _, it in ordered if it.get("bulk"))
        if bulk_n:
            bus.publish(conv, "email_new", {"id": f"{box.key}~digest~{int(time.time())}", "account": box.address,
                                            "digest": True, "count": bulk_n,
                                            "subject": f"{bulk_n} newsletter/promotion aaye",
                                            "snippet": "Bolo 'newsletters dikhao' ya inbox khud dekhiye.",
                                            "at": now().isoformat()})
    _save_recent(tenant, box.key, native_ids, recent)
    return announced


def watcher_tenants() -> list[str]:
    """Everyone who has a mailbox: app-connected rows, synced states, and Google sign-in connections."""
    out: set[str] = set()
    with session() as s:
        out |= set(s.scalars(select(MailAccount.tenant_id).distinct().where(MailAccount.kind != "_sig")).all())
        out |= set(s.scalars(select(MailSyncState.tenant_id).distinct()).all())
        from ..db import OAuthConnection
        try:
            out |= set(s.scalars(select(OAuthConnection.tenant_id).distinct()
                                 .where(OAuthConnection.scopes.contains("gmail.modify"))).all())
        except Exception:
            pass
    return sorted(t for t in out if t)


def sync_tick(max_accounts: int = 60) -> int:
    """Every mailbox once per tick (60s). At scale the start rotates each minute so no mailbox starves."""
    pairs: list[tuple[str, Box]] = []
    for tenant in watcher_tenants():
        try:
            for b in _boxes(tenant):
                pairs.append((tenant, b))
        except Exception:
            continue
    if not pairs:
        return 0
    start = (int(time.time()) // 60) % len(pairs)
    ordered = pairs[start:] + pairs[:start]
    for tenant, box in ordered[:max(1, int(max_accounts))]:
        try:
            sync_account(tenant, box)
        except Exception:
            log.exception("watch %s/%s failed", tenant, box.key)
            _mark(tenant, box.key, error="watch tick failed")
    return len(ordered[:max(1, int(max_accounts))])
