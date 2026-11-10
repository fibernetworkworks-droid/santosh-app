"""v0.487 W3 - the PC -> Hoola TEXT LANE (the quick-ask lane the whole Platforms W-line rides).

TODAY'S TRUTH (v0.486 and before): a paired PC talks to Hoola only through the desktop bridge's
JOB channel (/api/pc/ws -> job -> result). Text could not flow the other way - a quick-ask typed on
the PC (PowerToys Run 'hoola <sawaal>', the Ctrl+Alt+H window box, the browser extension's
"send page to Hoola") had no door into the Hoola conversation. W3 builds exactly that door.

THE LANE: POST /api/pc/quickask - a PAIRED device (the desktop's own spc_ token, or the browser
extension paired through the SAME /api/pc/pair flow - it shows up on her phone's Mera PC list like
any PC) sends {text?, url?, title?, selection?, client_id?}. The server composes ONE honest user
message (the Hinglish wrapper, the page link, the selection quoted) and rides the SAME turn pipeline
the phone uses (convs.mark + bus.publish + turn_inbox.accept + run_owned) - so Hoola ANSWERS in her
conversation, with every tool she already has (the page itself she reads with her own scrape lane,
v0.483's cache + stealth; this lane never fetches anything itself).

GET /api/pc/quickask/messages - the same device reads the last display rows of a conversation it
belongs to, so the extension popup / the desktop window can show her the answer where she asked.

GUARDS: device-token auth only (revoked token = 401, same as the WS), the conversation must belong
to the device's tenant, a per-device rate cap (QUICK_ASK_PER_HOUR) against a stuck loop, and the
client_id dedup so a retry after a timeout never makes Hoola act twice (the phone's own rule).
No new settings, no new tables - the lane is a POST that walks the front door like she does.
"""
from __future__ import annotations

import time
from collections import OrderedDict, deque
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from . import convs, turn_inbox
from .db import Message, session
from .events import bus
from .pc import service as pcs

router = APIRouter()

MAX_TEXT = 8000          # her typed ask
MAX_URL = 2048           # the page link
MAX_TITLE = 300
MAX_SELECTION = 4000     # "is page ka ye tukda" - a book stays a link, not a paste
QUICK_ASK_PER_HOUR = 30  # per device; a paired device is trusted, a loop is not


class QuickAsk(BaseModel):
    text: str = Field(default="", max_length=MAX_TEXT)
    url: str = Field(default="", max_length=MAX_URL)
    title: str = Field(default="", max_length=MAX_TITLE)
    selection: str = Field(default="", max_length=MAX_SELECTION)
    client_id: str | None = Field(default=None, max_length=64)


# ---- device auth (the SAME spc_ token the desktop bridge pairs with; reading pc/service, not changing it) ----
def _device(request: Request):
    tok = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    dev = pcs.device_for_token(tok)
    if dev is None:
        raise HTTPException(401, "This device is not paired (or was removed). Pair it again.")
    return dev


# ---- per-device rate cap (a stuck extension must not be able to run her bill up) ----
_RATE: "OrderedDict[str, deque]" = OrderedDict()


def _rate_ok(device_id: str) -> bool:
    now = time.monotonic()
    while len(_RATE) > 5000:
        _RATE.popitem(last=False)
    q = _RATE.get(device_id)
    if q is None:
        q = _RATE[device_id] = deque()
        _RATE.move_to_end(device_id)
    while q and now - q[0] > 3600:
        q.popleft()
    if len(q) >= QUICK_ASK_PER_HOUR:
        return False
    q.append(now)
    return True


# ---- retry dedup: the same rule the phone's POST /messages lives by ----
_SEEN_SENDS: "OrderedDict[tuple[str, str, str], float]" = OrderedDict()


def _already_sent(tenant: str, conversation_id: str, client_id: str | None) -> bool:
    if not client_id:
        return False
    now = time.monotonic()
    while _SEEN_SENDS and (len(_SEEN_SENDS) > 2000 or now - next(iter(_SEEN_SENDS.values())) > 600):
        _SEEN_SENDS.popitem(last=False)
    key = (tenant, conversation_id, client_id)
    if key in _SEEN_SENDS:
        return True
    _SEEN_SENDS[key] = now
    return False


def compose(text: str, url: str, title: str, selection: str) -> str:
    """ONE honest user message out of the structured pieces (server-side, so every client - the
    desktop doors, the extension, a future lane - lands the same shape in her conversation)."""
    parts: list[str] = []
    if url:
        head = f'Please look at this page — "{title}"' if title else "Please look at this page:"
        parts.append(f"{head}\n{url}")
        if selection:
            parts.append(f'I selected this part:\n"""\n{selection}\n"""')
        if not text:
            parts.append("Tell me about it.")
    if text:
        parts.append(text)
    return "\n\n".join(parts).strip()


@router.post("/api/pc/quickask")
def quickask(body: QuickAsk, request: Request, background: BackgroundTasks) -> dict[str, Any]:
    dev = _device(request)
    text = (body.text or "").strip()
    url = (body.url or "").strip()
    title = (body.title or "").strip()
    selection = (body.selection or "").strip()
    if not text and not url:
        raise HTTPException(422, "Send something - a question, or a page (url).")
    if url and not url.startswith(("http://", "https://")):
        raise HTTPException(422, "The url must start with http:// or https://.")
    if not _rate_ok(dev.id):
        raise HTTPException(429, f"Too many questions too fast (limit {QUICK_ASK_PER_HOUR}/hour). Try again in a little while.")
    tenant = dev.tenant_id
    conv = convs.current_or_new(tenant)          # the chat she is in, else her newest, else a new one
    if _already_sent(tenant, conv, body.client_id):
        return {"accepted": True, "duplicate": True, "conversation_id": conv}
    turn_text = compose(text, url, title, selection)
    convs.mark(tenant, conv, "message")
    bus.publish(conv, "message", {"role": "user", "text": turn_text, "source": "user",
                                  **({"client_id": body.client_id} if body.client_id else {})})
    ti_id = turn_inbox.accept(tenant, conv, turn_text, False, "", body.client_id or "")
    background.add_task(turn_inbox.run_owned, ti_id, conv, turn_text, tenant, False,
                        client_id=body.client_id or "")
    return {"accepted": True, "conversation_id": conv, "kind": "page" if url else "ask"}


@router.get("/api/pc/quickask/messages")
def quickask_messages(request: Request, conversation_id: str, after: int = 0, limit: int = 20) -> dict[str, Any]:
    """The asker's read-back: the extension popup / desktop window shows the answer where she asked.
    Only a device of the conversation's own tenant, only display rows, bounded."""
    dev = _device(request)
    conv = (conversation_id or "").strip()
    if not conv or convs.tenant_of(conv) != dev.tenant_id:
        raise HTTPException(404, "This conversation does not belong to this device's tenant.")
    lim = min(max(int(limit or 20), 1), 50)
    with session() as s:
        rows = list(reversed(s.scalars(
            select(Message)
            .where(Message.conversation_id == conv, Message.display.is_not(None), Message.id > int(after or 0))
            .order_by(Message.id.desc()).limit(lim)).all()))
    return {"conversation_id": conv,
            "messages": [{"id": r.id, "role": r.role, "text": r.display, "at": r.created_at.isoformat()}
                         for r in rows]}
