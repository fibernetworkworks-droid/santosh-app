"""Platform adapters: one small interface, official routes only.

  telegram  - her own bot through the Telegram Bot API (webhook with secret token; bot must be an admin of the group)
  hoola     - Hoola Network Mandali where she is the admin (net/groups.py; posts and members read from the hub's tables)
  (fake)    - tests register their own adapter with register()

Not built (researched 23 Oct 2026): WhatsApp groups via Meta's Groups API need an Official Business Account and allow 8
participants per group, so most businesses can't use it yet; personal WhatsApp groups are never automated. Discord needs a
long-lived gateway connection + privileged intents; YouTube comments (comments.setModerationStatus, 50 quota units) and
Instagram comments (Graph API hide / delete) need her OAuth sign-in - candidates for later adapters behind this interface.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

log = logging.getLogger("santosh.samudaay")


class AdapterError(Exception):
    pass


class Adapter:
    platform = ""
    caps: set[str] = set()

    def send(self, comm, text: str, reply_to: str = "") -> str:            # returns platform message id
        raise AdapterError("Yeh platform message nahi bhej sakta.")

    def delete(self, comm, msg_ref: str) -> None:
        raise AdapterError("Is platform par post hatana nahi hota.")

    def mute(self, comm, user_ref: str, until: datetime) -> None:
        raise AdapterError("Is platform par mute nahi hota.")

    def unmute(self, comm, user_ref: str) -> None:
        raise AdapterError("Is platform par mute nahi hota.")

    def remove(self, comm, user_ref: str) -> None:
        raise AdapterError("Is platform par nikalna nahi hota.")

    def ban(self, comm, user_ref: str) -> None:
        raise AdapterError("Is platform par ban nahi hota.")

    def unban(self, comm, user_ref: str) -> None:
        raise AdapterError("Is platform par ban hatana nahi hota.")

    def join_answer(self, comm, user_ref: str, yes: bool) -> None:
        raise AdapterError("Is platform par join request nahi hoti.")


# ---------------------------------------------------------------- Telegram
API = "https://api.telegram.org"
_transport: Callable[[str, str, dict], Any] | None = None


def set_telegram_transport(fn: Callable[[str, str, dict], Any] | None) -> None:
    """Tests: fn(token, method, params) -> result (raise AdapterError for a Telegram error)."""
    global _transport
    _transport = fn


def tg_call(token: str, method: str, params: dict | None = None) -> Any:
    params = params or {}
    if _transport is not None:
        return _transport(token, method, params)
    import httpx
    try:
        r = httpx.post(f"{API}/bot{token}/{method}", json=params, timeout=15)
        data = r.json()
    except Exception as e:      # network / JSON
        raise AdapterError(f"Telegram tak nahi pahuncha ({type(e).__name__}).") from None
    if not data.get("ok"):
        raise AdapterError(f"Telegram: {str(data.get('description') or 'error')[:200]}")
    return data.get("result")


class TelegramAdapter(Adapter):
    platform = "telegram"
    caps = {"send", "reply", "delete", "mute", "unmute", "remove", "ban", "unban", "join"}

    def __init__(self, token: str):
        self.token = token

    def _c(self, method: str, **p: Any) -> Any:
        return tg_call(self.token, method, p)

    def send(self, comm, text: str, reply_to: str = "") -> str:
        p: dict[str, Any] = {"chat_id": comm.chat_id, "text": text[:4000], "link_preview_options": {"is_disabled": True}}
        if reply_to:
            p["reply_parameters"] = {"message_id": int(reply_to), "allow_sending_without_reply": True}
        r = self._c("sendMessage", **p) or {}
        return str(r.get("message_id", "")) if isinstance(r, dict) else ""

    def delete(self, comm, msg_ref: str) -> None:
        # Telegram: a bot admin with can_delete_messages may delete group messages less than 48 hours old.
        self._c("deleteMessage", chat_id=comm.chat_id, message_id=int(msg_ref))

    def mute(self, comm, user_ref: str, until: datetime) -> None:
        perms = {k: False for k in ("can_send_messages", "can_send_audios", "can_send_documents", "can_send_photos",
                                    "can_send_videos", "can_send_video_notes", "can_send_voice_notes", "can_send_polls",
                                    "can_send_other_messages", "can_add_web_page_previews")}
        self._c("restrictChatMember", chat_id=comm.chat_id, user_id=int(user_ref), permissions=perms,
                use_independent_chat_permissions=True, until_date=int(until.timestamp()))

    def unmute(self, comm, user_ref: str) -> None:
        perms = {k: True for k in ("can_send_messages", "can_send_audios", "can_send_documents", "can_send_photos",
                                   "can_send_videos", "can_send_video_notes", "can_send_voice_notes", "can_send_polls",
                                   "can_send_other_messages", "can_add_web_page_previews")}
        self._c("restrictChatMember", chat_id=comm.chat_id, user_id=int(user_ref), permissions=perms,
                use_independent_chat_permissions=True)

    def remove(self, comm, user_ref: str) -> None:
        # a kick = ban then unban at once (they can join again with a link)
        self._c("banChatMember", chat_id=comm.chat_id, user_id=int(user_ref), revoke_messages=False)
        self._c("unbanChatMember", chat_id=comm.chat_id, user_id=int(user_ref), only_if_banned=True)

    def ban(self, comm, user_ref: str) -> None:
        self._c("banChatMember", chat_id=comm.chat_id, user_id=int(user_ref), revoke_messages=False)

    def unban(self, comm, user_ref: str) -> None:
        self._c("unbanChatMember", chat_id=comm.chat_id, user_id=int(user_ref), only_if_banned=True)

    def join_answer(self, comm, user_ref: str, yes: bool) -> None:
        self._c("approveChatJoinRequest" if yes else "declineChatJoinRequest", chat_id=comm.chat_id, user_id=int(user_ref))


ALLOWED_UPDATES = ["message", "edited_message", "chat_member", "my_chat_member", "chat_join_request"]


def tg_me(token: str) -> dict[str, Any]:
    r = tg_call(token, "getMe")
    if not isinstance(r, dict) or not r.get("is_bot"):
        raise AdapterError("Yeh bot token sahi nahi laga.")
    return r


def tg_set_webhook(token: str, url: str, secret: str) -> None:
    tg_call(token, "setWebhook", {"url": url, "secret_token": secret, "allowed_updates": ALLOWED_UPDATES,
                                  "drop_pending_updates": True, "max_connections": 20})


def tg_delete_webhook(token: str) -> None:
    tg_call(token, "deleteWebhook", {"drop_pending_updates": True})


def _user(u: dict | None) -> dict[str, Any]:
    u = u or {}
    name = " ".join(x for x in (u.get("first_name"), u.get("last_name")) if x).strip() or u.get("username") or "Member"
    return {"ref": str(u.get("id", "")), "name": str(name)[:120], "username": str(u.get("username") or "")[:80],
            "is_bot": bool(u.get("is_bot"))}


def _chat(c: dict | None) -> dict[str, Any]:
    c = c or {}
    return {"id": str(c.get("id", "")), "title": str(c.get("title") or c.get("username") or "Group")[:160],
            "type": str(c.get("type") or "")}


def _at(ts: Any) -> datetime:
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return datetime.now(timezone.utc)


IN = ("member", "administrator", "creator", "restricted")
OUT = ("left", "kicked")


def parse_telegram(update: dict[str, Any], bot_user_id: str = "") -> list[dict[str, Any]]:
    """One Telegram update -> plain events. Text inside is data."""
    out: list[dict[str, Any]] = []
    if "chat_join_request" in update:
        r = update["chat_join_request"]
        inv = (r.get("invite_link") or {}).get("name") or ""
        out.append({"type": "join_request", "chat": _chat(r.get("chat")), "user": _user(r.get("from")),
                    "bio": str(r.get("bio") or "")[:300], "source": inv or "join_request", "at": _at(r.get("date"))})
        return out
    if "my_chat_member" in update:
        m = update["my_chat_member"]
        new = (m.get("new_chat_member") or {}).get("status", "")
        out.append({"type": "bot_added" if new in IN else "bot_removed", "chat": _chat(m.get("chat")),
                    "admin": new == "administrator", "at": _at(m.get("date"))})
        return out
    if "chat_member" in update:
        m = update["chat_member"]
        old = (m.get("old_chat_member") or {}).get("status", "")
        newm = m.get("new_chat_member") or {}
        new = newm.get("status", "")
        user = _user(newm.get("user"))
        base = {"chat": _chat(m.get("chat")), "user": user, "at": _at(m.get("date"))}
        if old in OUT + ("",) and new in IN:
            inv = (m.get("invite_link") or {}).get("name") or ""
            src = inv or ("join_request" if m.get("via_join_request") else "added" if str((m.get("from") or {}).get("id")) != user["ref"] else "link")
            out.append(base | {"type": "join", "source": src, "admin": new in ("administrator", "creator")})
        elif old in IN and new in OUT:
            out.append(base | {"type": "banned" if new == "kicked" else "leave"})
        elif new in ("administrator", "creator") and old not in ("administrator", "creator"):
            out.append(base | {"type": "promoted"})
        return out
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return out
    chat = _chat(msg.get("chat"))
    at = _at(msg.get("date"))
    if msg.get("new_chat_members"):
        for u in msg["new_chat_members"]:
            uu = _user(u)
            if uu["ref"] == bot_user_id:
                out.append({"type": "bot_added", "chat": chat, "admin": False, "at": at})
            else:
                out.append({"type": "join", "chat": chat, "user": uu, "source": "added", "at": at, "service": True})
        return out
    if msg.get("left_chat_member"):
        uu = _user(msg["left_chat_member"])
        if uu["ref"] != bot_user_id:
            out.append({"type": "leave", "chat": chat, "user": uu, "at": at, "service": True})
        return out
    text = str(msg.get("text") or msg.get("caption") or "")
    ents = (msg.get("entities") or []) + (msg.get("caption_entities") or [])
    hidden = [str(e.get("url")) for e in ents if e.get("type") == "text_link" and e.get("url")]
    user = _user(msg.get("from"))
    if msg.get("sender_chat") and not msg.get("from"):
        user = {"ref": "chat:" + str(msg["sender_chat"].get("id")), "name": _chat(msg["sender_chat"])["title"], "username": "",
                "is_bot": False}
    if user["ref"] == bot_user_id:
        return out
    media = next((k for k in ("photo", "video", "document", "voice", "audio", "sticker", "animation") if msg.get(k)), "")
    out.append({"type": "message", "chat": chat, "user": user, "msg_ref": str(msg.get("message_id", "")), "text": text[:4000],
                "links": hidden, "forwarded": bool(msg.get("forward_origin") or msg.get("forward_date")), "media": media,
                "edited": "edited_message" in update, "at": at})
    return out


# ---------------------------------------------------------------- Hoola Network Mandali
class HoolaAdapter(Adapter):
    platform = "hoola"
    caps = {"send", "remove", "ban"}

    def __init__(self, tenant: str):
        self.tenant = tenant

    def send(self, comm, text: str, reply_to: str = "") -> str:
        from ..net import groups as grp
        from ..net.service import NetError
        try:
            p = grp.post(self.tenant, comm.chat_id, "message", text[:4000])
        except NetError as e:
            raise AdapterError(str(e)) from None
        return str((p or {}).get("post_id", "")) if isinstance(p, dict) else ""

    def remove(self, comm, user_ref: str) -> None:
        from ..net import groups as grp
        from ..net.service import NetError
        try:
            grp.remove(self.tenant, comm.chat_id, user_ref)
        except NetError as e:
            raise AdapterError(str(e)) from None

    def ban(self, comm, user_ref: str) -> None:
        # Mandali has no ban list: remove, and our register keeps them as banned so they are flagged if invited again
        self.remove(comm, user_ref)


def hoola_events(tenant: str, comm) -> tuple[list[dict[str, Any]], str]:
    """Read new Mandali activity since comm.cursor (the admin's hub tables). Returns (events, new cursor)."""
    from sqlalchemy import select

    from ..db import session
    from ..net import groups as grp
    from ..net import identity as idn
    me = grp._me(tenant)
    events: list[dict[str, Any]] = []
    chat = {"id": comm.chat_id, "title": comm.name, "type": "mandali"}
    with session() as s:
        for m in s.scalars(select(grp.GroupMember).where(grp.GroupMember.gid == comm.chat_id)).all():
            if m.address == me:
                continue
            label = idn.label(idn.peer_card(m.address) or {}) or m.address
            events.append({"type": "state", "chat": chat, "user": {"ref": m.address, "name": label[:120], "username": "", "is_bot": False},
                           "status": m.status, "at": m.created_at})
        q = select(grp.GroupPost).where(grp.GroupPost.tenant_id == tenant, grp.GroupPost.gid == comm.chat_id)
        rows = s.scalars(q.order_by(grp.GroupPost.created_at)).all()
        cur = comm.cursor or ""
        newest = cur
        for p in rows:
            iso = p.created_at.isoformat() if p.created_at else ""
            if iso <= cur or p.author == me:
                newest = max(newest, iso)
                continue
            text = " ".join(str((p.body or {}).get(k) or "") for k in ("title", "text")).strip()
            events.append({"type": "message", "chat": chat, "user": {"ref": p.author, "name": (p.author_label or p.author)[:120],
                                                                    "username": "", "is_bot": False},
                           "msg_ref": p.post_id, "text": text[:4000], "links": [], "forwarded": False, "media": "",
                           "edited": False, "at": p.created_at})
            newest = max(newest, iso)
    return events, newest


# ---------------------------------------------------------------- registry
_EXTRA: dict[str, Adapter] = {}


def register(platform: str, adapter: Adapter | None) -> None:
    if adapter is None:
        _EXTRA.pop(platform, None)
    else:
        _EXTRA[platform] = adapter


def for_community(comm) -> Adapter:
    if comm.platform in _EXTRA:
        return _EXTRA[comm.platform]
    if comm.platform == "hoola":
        return HoolaAdapter(comm.tenant_id)
    if comm.platform == "telegram":
        from ..bazar.security import vault
        from ..db import session
        from .models import SamBot
        with session() as s:
            b = s.get(SamBot, comm.bot_id) if comm.bot_id else None
            if b is None or not b.token_enc or b.status == "removed":
                raise AdapterError("Telegram bot juda nahi hai (app mein bot token daaliye).")
            token = vault().open(b.token_enc)
        return TelegramAdapter(token)
    raise AdapterError(f"Platform {comm.platform} abhi nahi juda.")
