"""v0.999.278 SENDING (owner: "make this functional for Hoola Route" - the mails that waited as drafts and the
Telegram / Slack / Discord / Mattermost posts that only came to her Hoola chat).

A Send step really sends:
- email       from one of her connected mailboxes (Gmail, Outlook or any email she joined by IMAP)
- telegram    through her bot (a sign-in that holds the bot's token) to a chat id
- slack       through a Slack incoming webhook, or a bot token + a channel
- discord     through a Discord channel webhook, or a bot token + a channel id
- mattermost  through a Mattermost incoming webhook, or her server + a bot token + a channel id

The house rule (sending -> her tap) is kept per ROUTE, not per message: a route with Send steps sends nothing until she
taps "Allow sending" on its page. Her tap is bound to a fingerprint of WHERE it sends (the way, the account / sign-in,
the addresses / chats / channels as written in the steps); change any of that and the route stops sending until she
allows it again. The words of a message may change freely. A test run never sends (it shows what it would send).
Limits: 50 sends in one run, and a per-day limit per route (her setting sends_per_day, default 100, at most 2,000).
Every send is written down (route_sends): when, which way, where to, and whether it went.

A Telegram bot can also START a route: the route's start is its web address, and "Connect the bot" tells Telegram to
deliver the bot's messages there (Telegram's own setWebhook). Its message is {{vars.body.message}}; a reply goes to
{{vars.body.message.chat.id}}.
"""
from __future__ import annotations

import email.utils
import hashlib
import json
import re
import time
import uuid
from typing import Any
from urllib.parse import urlparse

VIAS = ("email", "telegram", "slack", "discord", "mattermost")
APPS = {"telegram": "Telegram", "slack": "Slack", "discord": "Discord", "mattermost": "Mattermost", "email": "email"}
DEST_KEYS = {"email": ("to", "cc", "bcc", "account"), "telegram": ("chat",), "slack": ("channel",),
             "discord": ("channel",), "mattermost": ("channel",)}
TEXT_MAX = {"telegram": 4096, "slack": 39_000, "discord": 2000, "mattermost": 16_000, "email": 200_000}
RUN_MAX = 50
DAY_DEFAULT = 100
DAY_MAX = 2000
_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,49}$")


class SendError(ValueError):
    pass


# ---------------------------------------------------------------- the step
def validate(step: dict, sid: str) -> None:
    from ..agent.tools import ToolError
    via = str(step.get("via") or "")
    if via not in VIAS:
        raise ToolError(f"Step '{sid}': a send step goes by one of: {', '.join(VIAS)}")
    con = str(step.get("connection") or "")
    if con and not _NAME.match(con):
        raise ToolError(f"Step '{sid}': the sign-in name has letters, digits and _")
    if via == "email":
        if not str(step.get("body") or "").strip() and not str(step.get("subject") or "").strip():
            raise ToolError(f"Step '{sid}': a mail needs a subject or some words")
    elif not str(step.get("text") or "").strip() and not (via == "telegram" and str(step.get("photo") or "").strip()):
        raise ToolError(f"Step '{sid}': say what the message says (text)")
    if step.get("format") not in (None, "", "markdown", "html"):
        raise ToolError(f"Step '{sid}': format is markdown or html (or nothing)")


def _walk(steps: list) -> list[dict]:
    out: list[dict] = []
    for st in steps or []:
        if not isinstance(st, dict):
            continue
        if st.get("type") == "send":
            out.append(st)
        for k in ("then", "else", "fallback"):
            out += _walk(st.get(k) or [])
        if st.get("type") == "loop":
            out += _walk(st.get("body") or [])
        for rt in st.get("routes") or []:
            if isinstance(rt, dict):
                out += _walk(rt.get("steps") or [])
        oe = st.get("on_error")
        if isinstance(oe, dict):
            out += _walk(oe.get("steps") or [])
    return out


def destination(step: dict) -> dict:
    via = str(step.get("via") or "")
    d = {"via": via, "connection": str(step.get("connection") or "")}
    for k in DEST_KEYS.get(via, ()):
        v = step.get(k)
        if v not in (None, ""):
            d[k] = v if isinstance(v, str) else json.dumps(v, sort_keys=True, default=str)
    return d


def fingerprint(steps: list) -> str:
    ds = sorted((str(s.get("id")), json.dumps(destination(s), sort_keys=True)) for s in _walk(steps))
    return hashlib.sha256(json.dumps(ds).encode()).hexdigest()[:24] if ds else ""


def _where_words(d: dict) -> str:
    via = d["via"]
    if via == "email":
        w = "mail to " + (d.get("to") or "(nobody yet)")
        if d.get("cc"):
            w += ", copy to " + d["cc"]
        if d.get("account"):
            w += f" from {d['account']}"
        return w
    tgt = d.get("chat") or d.get("channel") or ""
    w = f"{APPS[via]} message" + (f" to {tgt}" if tgt else "")
    return w + (f" with the sign-in {d['connection']}" if d.get("connection") else "")


# ---------------------------------------------------------------- her permission + the record
def _con(tenant: str):
    from ..agent import dhara_tools as D
    con = D._con(tenant)
    con.execute("CREATE TABLE IF NOT EXISTS route_send_ok (workflow_id TEXT PRIMARY KEY, hash TEXT, at REAL)")
    con.execute("CREATE TABLE IF NOT EXISTS route_sends (id TEXT PRIMARY KEY, workflow_id TEXT, run_id TEXT, at REAL, "
                "via TEXT, dest TEXT, ok INTEGER, error TEXT)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_route_sends ON route_sends (workflow_id, at)")
    con.execute("CREATE TABLE IF NOT EXISTS route_bots (workflow_id TEXT PRIMARY KEY, app TEXT, connection TEXT, "
                "username TEXT, at REAL)")
    return con


def bot_of(tenant: str, wf_id: str) -> dict | None:
    con = _con(tenant)
    try:
        r = con.execute("SELECT * FROM route_bots WHERE workflow_id = ?", (wf_id,)).fetchone()
    finally:
        con.close()
    return dict(r) if r is not None else None


def per_day(wf: dict) -> int:
    try:
        n = int((wf.get("settings") or {}).get("sends_per_day") or DAY_DEFAULT)
    except (TypeError, ValueError):
        n = DAY_DEFAULT
    return max(1, min(n, DAY_MAX))


def status(tenant: str, wf: dict) -> dict:
    steps = _walk(wf.get("steps") or [])
    h = fingerprint(wf.get("steps") or [])
    con = _con(tenant)
    try:
        r = con.execute("SELECT hash, at FROM route_send_ok WHERE workflow_id = ?", (wf["id"],)).fetchone()
        today = con.execute("SELECT COUNT(*) FROM route_sends WHERE workflow_id = ? AND ok = 1 AND at > ?",
                            (wf["id"], time.time() - 86400)).fetchone()[0]
        last = con.execute("SELECT at, via, dest, ok, error FROM route_sends WHERE workflow_id = ? ORDER BY at DESC LIMIT 20",
                           (wf["id"],)).fetchall()
    finally:
        con.close()
    allowed = bool(r is not None and h and r["hash"] == h)
    return {"sends": [{"id": s.get("id"), "label": s.get("label") or "", "via": s.get("via"),
                       "words": _where_words(destination(s))} for s in steps],
            "hash": h, "allowed": allowed, "allowed_at": r["at"] if r is not None else None,
            "changed": bool(r is not None and h and r["hash"] != h), "today": int(today), "per_day": per_day(wf),
            "per_run": RUN_MAX, "last": [dict(x) for x in last], "bot": bot_of(tenant, wf["id"])}


def allow(tenant: str, wf: dict, h: str, on: bool = True) -> dict:
    con = _con(tenant)
    try:
        if not on:
            con.execute("DELETE FROM route_send_ok WHERE workflow_id = ?", (wf["id"],))
        else:
            now_h = fingerprint(wf.get("steps") or [])
            if not now_h:
                raise SendError("This route has no Send steps")
            if str(h or "") != now_h:
                raise SendError("The route's sends changed while you looked - read them again and allow")
            con.execute("INSERT OR REPLACE INTO route_send_ok (workflow_id, hash, at) VALUES (?, ?, ?)",
                        (wf["id"], now_h, time.time()))
        con.commit()
    finally:
        con.close()
    return status(tenant, wf)


def _record(tenant: str, wf_id: str, run_id: str, via: str, dest: str, ok: bool, error: str = "") -> None:
    con = _con(tenant)
    try:
        con.execute("INSERT INTO route_sends (id, workflow_id, run_id, at, via, dest, ok, error) VALUES (?,?,?,?,?,?,?,?)",
                    (uuid.uuid4().hex[:16], wf_id, run_id, time.time(), via, dest[:300], 1 if ok else 0, error[:300]))
        con.execute("DELETE FROM route_sends WHERE workflow_id = ? AND at < ?", (wf_id, time.time() - 30 * 86400))
        con.commit()
    finally:
        con.close()


# ---------------------------------------------------------------- the sign-in a step uses
def _secret(tenant: str, wf: dict, step: dict) -> dict:
    from . import workspace as WS
    via = step["via"]
    name = str(step.get("connection") or "")
    if not name and via == "telegram":
        name = str((bot_of(tenant, wf["id"]) or {}).get("connection") or "")
    if not name:
        mine = [c for c in WS.credentials(tenant) if c["kind"] == via]
        if len(mine) == 1:
            name = mine[0]["name"]
        elif not mine:
            raise SendError(f"Save a {APPS[via]} sign-in first (Sign-ins > kind {APPS[via]}) and pick it on this step")
        else:
            raise SendError(f"You have {len(mine)} {APPS[via]} sign-ins - pick the one this step uses")
    d = WS.messaging_secret(tenant, name, via)
    d["_name"] = name
    return d


def _post(url: str, js: dict, headers: dict | None = None, guard: bool = False) -> tuple[int, Any]:
    import httpx
    if guard:
        from ..agent import scrape_tools as st
        url = st._guard_url(url)
    try:
        r = httpx.post(url, json=js, headers=headers or {}, timeout=httpx.Timeout(20.0), follow_redirects=False)
    except httpx.HTTPError as e:
        raise SendError(f"Could not reach it ({type(e).__name__})")
    try:
        body: Any = r.json()
    except ValueError:
        body = r.text[:500]
    return r.status_code, body


def _why(app: str, code: int, body: Any) -> str:
    msg = ""
    if isinstance(body, dict):
        msg = str(body.get("description") or body.get("error") or body.get("message") or "")
    elif isinstance(body, str):
        msg = body[:120]
    return f"{app} refused it ({code}{': ' + msg[:160] if msg else ''})"


def _telegram(sec: dict, chat: str, text: str, fmt: str, silent: bool, photo: str = "") -> dict:
    if not chat:
        raise SendError("Say which Telegram chat it goes to (a chat id, like 123456789, or @channelname)")
    if photo and not photo.startswith("https://"):
        raise SendError("A photo goes by its https:// address")
    js: dict[str, Any] = {"chat_id": chat, "photo": photo, "caption": text[:1024]} if photo else {"chat_id": chat, "text": text}
    if fmt:
        js["parse_mode"] = "HTML" if fmt == "html" else "Markdown"
    if silent:
        js["disable_notification"] = True
    code, body = _post(f"https://api.telegram.org/bot{sec['token']}/{'sendPhoto' if photo else 'sendMessage'}", js)
    if code >= 400 or not (isinstance(body, dict) and body.get("ok")):
        raise SendError(_why("Telegram", code, body))
    res = body.get("result") or {}
    return {"sent": True, "message_id": res.get("message_id"), "chat": (res.get("chat") or {}).get("id", chat)}


def _slack(sec: dict, channel: str, text: str, thread: str) -> dict:
    if sec.get("webhook"):
        code, body = _post(sec["webhook"], {"text": text})
        if code >= 400:
            raise SendError(_why("Slack", code, body))
        return {"sent": True}
    if not channel:
        raise SendError("Say which Slack channel it goes to (like #general or a channel id)")
    js: dict[str, Any] = {"channel": channel, "text": text}
    if thread:
        js["thread_ts"] = thread
    code, body = _post("https://slack.com/api/chat.postMessage", js, {"Authorization": "Bearer " + sec["token"]})
    if code >= 400 or not (isinstance(body, dict) and body.get("ok")):
        raise SendError(_why("Slack", code, body))
    return {"sent": True, "ts": body.get("ts"), "channel": body.get("channel")}


def _discord(sec: dict, channel: str, text: str) -> dict:
    if sec.get("webhook"):
        code, body = _post(sec["webhook"] + ("&" if "?" in sec["webhook"] else "?") + "wait=true", {"content": text})
        if code >= 400:
            raise SendError(_why("Discord", code, body))
        return {"sent": True, "message_id": (body or {}).get("id") if isinstance(body, dict) else None}
    if not re.match(r"^\d{5,25}$", channel or ""):
        raise SendError("Say which Discord channel it goes to (its channel id, a long number)")
    code, body = _post(f"https://discord.com/api/v10/channels/{channel}/messages", {"content": text},
                       {"Authorization": "Bot " + sec["token"]})
    if code >= 400:
        raise SendError(_why("Discord", code, body))
    return {"sent": True, "message_id": (body or {}).get("id") if isinstance(body, dict) else None}


def _mattermost(sec: dict, channel: str, text: str) -> dict:
    if sec.get("webhook"):
        js = {"text": text, **({"channel": channel} if channel else {})}
        code, body = _post(sec["webhook"], js, guard=True)
        if code >= 400:
            raise SendError(_why("Mattermost", code, body))
        return {"sent": True}
    if not channel:
        raise SendError("Say which Mattermost channel it goes to (its channel id)")
    code, body = _post(sec["server"].rstrip("/") + "/api/v4/posts", {"channel_id": channel, "message": text},
                       {"Authorization": "Bearer " + sec["token"]}, guard=True)
    if code >= 400:
        raise SendError(_why("Mattermost", code, body))
    return {"sent": True, "post_id": (body or {}).get("id") if isinstance(body, dict) else None}


def _email(tenant: str, to: str, cc: str, bcc: str, subject: str, body: str, account: str, md: bool) -> dict:
    from ..mailbox import contacts, mime
    from ..mailbox import service as ms
    from ..mailbox.accounts import get_box
    from ..mailbox.base import MailError, NotConnected
    if not to.strip():
        raise SendError("Say who the mail goes to")
    people = email.utils.getaddresses([x for x in (to, cc, bcc) if x])
    if len(people) > 50:
        raise SendError("One mail goes to at most 50 people - use a Repeat for each to send one mail each")
    for nm, a in people:
        if not contacts.valid(a):
            raise SendError(f"'{(nm + ' ' + a).strip()}' is not an email address")
    md = md or mime.looks_md(body)
    try:
        box = get_box(tenant, account or None)
        msg = mime.build(from_addr=box.address, from_name=ms.sender_name(tenant, box), to=to, cc=cc, bcc=bcc,
                         subject=subject or "(no subject)", body=mime.md_to_plain(body) if md else body,
                         html_body=mime.md_to_html(body) if md else None)
        sent = ms._guard(box, lambda: box.send(msg, None))
    except (MailError, NotConnected) as e:
        raise SendError(str(e)[:240])
    try:
        contacts.learn(tenant, people, 1.0, sent=True)
    except Exception:   # noqa: BLE001
        pass
    return {"sent": True, "to": to, "from": box.address, "message_id": (sent or {}).get("message_id")}


async def run(tenant: str, step: dict, ctx: dict, resolve, run_id: str) -> tuple[bool, Any, str]:
    import asyncio
    from ..agent import dhara_tools as D
    sid, via = str(step.get("id")), str(step.get("via") or "")
    r = lambda k: resolve(step.get(k) if step.get(k) is not None else "", ctx)     # noqa: E731
    as_s = lambda v: v if isinstance(v, str) else ("" if v is None else json.dumps(v, ensure_ascii=False, default=str))  # noqa: E731
    out: dict[str, Any] = {"via": via}
    if via == "email":
        f = {k: as_s(r(k)).strip() for k in ("to", "cc", "bcc", "subject", "account")}
        f["body"] = as_s(r("body"))
        where = f["to"]
        out.update({k: v for k, v in f.items() if k != "body" and v})
    else:
        text = as_s(r("text"))
        tgt = as_s(r("chat" if via == "telegram" else "channel")).strip()
        if len(text) > TEXT_MAX[via]:
            text = text[:TEXT_MAX[via] - 1] + "…"
        where = tgt or "(its webhook)"
        out.update({"to": where, "text": text[:300]})
    test = run_id == "step-test" or bool((ctx.get("run") or {}).get("test"))
    if test:
        out["would_send"] = True
        out["note"] = "A test run does not send - this is what it would send"
        ctx["steps"][sid] = {"output": out}
        return True, out, ""
    wf_id = str((ctx.get("run") or {}).get("route_id") or "")
    wf = D.get_workflow(tenant, wf_id=wf_id) if wf_id else None
    if wf is None:
        return False, out, "the route is gone"
    st = await asyncio.to_thread(status, tenant, wf)
    if not st["allowed"]:
        return False, out, ("The route's sends changed since you allowed them - open the route and tap Allow sending again"
                            if st["changed"] else "This route may not send yet - open the route and tap Allow sending")
    n = int(ctx.get("_sends") or 0)
    if n >= RUN_MAX:
        return False, out, f"One run sends at most {RUN_MAX} messages"
    if st["today"] >= st["per_day"]:
        return False, out, f"The route sent {st['today']} today - its limit is {st['per_day']} a day (Settings)"
    ctx["_sends"] = n + 1
    try:
        if via == "email":
            got = await asyncio.to_thread(_email, tenant, f["to"], f["cc"], f["bcc"], f["subject"], f["body"], f["account"],
                                          bool(step.get("markdown")))
        else:
            sec = await asyncio.to_thread(_secret, tenant, wf, step)
            if via == "telegram":
                got = await asyncio.to_thread(_telegram, sec, where if where != "(its webhook)" else "", text,
                                              str(step.get("format") or ""), bool(step.get("silent")), as_s(r("photo")).strip())
            elif via == "slack":
                got = await asyncio.to_thread(_slack, sec, tgt, text, as_s(r("thread")).strip())
            elif via == "discord":
                got = await asyncio.to_thread(_discord, sec, tgt, text)
            else:
                got = await asyncio.to_thread(_mattermost, sec, tgt, text)
    except SendError as e:
        await asyncio.to_thread(_record, tenant, wf_id, run_id, via, where, False, str(e))
        return False, out, str(e)
    except Exception as e:   # noqa: BLE001
        from . import workspace as WS
        why = str(e) if isinstance(e, WS.WorkspaceError) else f"{type(e).__name__}: it did not go"
        await asyncio.to_thread(_record, tenant, wf_id, run_id, via, where, False, why)
        return False, out, why
    await asyncio.to_thread(_record, tenant, wf_id, run_id, via, where, True)
    out.update(got)
    ctx["steps"][sid] = {"output": out}
    return True, out, ""


# ---------------------------------------------------------------- a Telegram bot starts the route
def connect_bot(tenant: str, wf: dict, connection: str, base_url: str) -> dict:
    """Point the bot's messages at the route's web address (Telegram setWebhook). A new address is made for it."""
    from ..agent import dhara_tools as D
    from . import workspace as WS
    if wf.get("trigger_kind") != "webhook":
        raise SendError("A bot starts a route whose start is its web address (What starts it > Web address)")
    if not base_url.startswith("https://"):
        raise SendError("The server's public address must start with https:// for Telegram to reach it")
    sec = WS.messaging_secret(tenant, connection, "telegram")
    tok = D.webhook_token_reveal(tenant, wf["id"])
    hook = f"{base_url.rstrip('/')}/api/dhara/hook/{tok}"
    code, body = _post(f"https://api.telegram.org/bot{sec['token']}/setWebhook",
                       {"url": hook, "allowed_updates": ["message", "callback_query"]})
    if code >= 400 or not (isinstance(body, dict) and body.get("ok")):
        raise SendError(_why("Telegram", code, body))
    code, me = _post(f"https://api.telegram.org/bot{sec['token']}/getMe", {})
    user = ((me or {}).get("result") or {}).get("username") if isinstance(me, dict) else None
    con = _con(tenant)
    try:
        con.execute("INSERT OR REPLACE INTO route_bots (workflow_id, app, connection, username, at) VALUES (?,?,?,?,?)",
                    (wf["id"], "telegram", connection, user or "", time.time()))
        con.commit()
    finally:
        con.close()
    return {"connected": True, "bot": user or "", "note": "The bot's messages now start this route. The old address of "
            "this route no longer works."}


def disconnect_bot(tenant: str, wf: dict) -> dict:
    from . import workspace as WS
    bot = bot_of(tenant, wf["id"]) or {}
    if bot.get("connection"):
        try:
            sec = WS.messaging_secret(tenant, bot["connection"], "telegram")
            _post(f"https://api.telegram.org/bot{sec['token']}/deleteWebhook", {})
        except Exception:   # noqa: BLE001
            pass
    con = _con(tenant)
    try:
        con.execute("DELETE FROM route_bots WHERE workflow_id = ?", (wf["id"],))
        con.commit()
    finally:
        con.close()
    return {"connected": False}


def host_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower()
