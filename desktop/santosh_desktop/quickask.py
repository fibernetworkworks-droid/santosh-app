"""The PC -> Hoola quick-ask send (W3's text lane, desktop side) - one honest POST per ask.

The W3 lane: POST /api/pc/quickask with the SAME paired spc_ token the bridge already holds -
no new pairing, no new settings. A quick-ask lands in her conversation like a message from the
phone and Hoola answers there (her tools, her scrape lane for the page). Everything that types
on her PC rides this one door: the PowerToys Run plugin's 'hoola <sawaal>' (--ask), the window's
own ask box, and the browser extension pairs itself on her phone (this module is the desktop's
own lane).

Errors stay honest dicts - the window logs them, nothing beeps, nothing pretends.
"""
from __future__ import annotations

import uuid
from typing import Any

import httpx

TIMEOUT = 20


def client_id() -> str:
    """One send = one id, so a retry after a timeout never makes Hoola act twice (the server dedups)."""
    return "qa_" + uuid.uuid4().hex[:16]


def send(cfg, text: str = "", url: str = "", title: str = "", selection: str = "",
         cid: str | None = None, http: httpx.Client | None = None) -> dict[str, Any]:
    """Bhej do. cfg = the desktop Config (server + token). Jawab honest dict: ok / accepted /
    conversation_id, ya ok=False with a message she can act on."""
    if not getattr(cfg, "paired", False):
        return {"ok": False, "message": "Hoola Desktop is not paired - pair it from the phone first."}
    body: dict[str, str] = {}
    if text.strip():
        body["text"] = text.strip()[:8000]
    if url.strip():
        body["url"] = url.strip()[:2048]
    if title.strip():
        body["title"] = title.strip()[:300]
    if selection.strip():
        body["selection"] = selection.strip()[:4000]
    if not body:
        return {"ok": False, "message": "Send something - a question or a page."}
    body["client_id"] = cid or client_id()
    c = http or httpx.Client(timeout=TIMEOUT)
    try:
        r = c.post(cfg.server.rstrip("/") + "/api/pc/quickask", json=body,
                   headers={"Authorization": f"Bearer {cfg.token}"})
    except Exception as e:
        return {"ok": False, "message": f"Could not reach the server: {type(e).__name__}"}
    if r.status_code == 401:
        return {"ok": False, "message": "This device was removed - pair Hoola Desktop again."}
    if r.status_code == 429:
        try:
            msg = r.json().get("detail", "")
        except ValueError:
            msg = ""
        return {"ok": False, "message": msg or "Too many questions too quickly - try again in a little while."}
    if r.status_code >= 400:
        try:
            msg = r.json().get("detail") or r.text
        except ValueError:
            msg = r.text
        return {"ok": False, "message": str(msg)[:200]}
    d = r.json()
    return {"ok": True, "accepted": True, "conversation_id": d.get("conversation_id", ""),
            "duplicate": bool(d.get("duplicate")), "kind": d.get("kind", "ask"), "client_id": body["client_id"]}


def messages(cfg, conversation_id: str, after: int = 0, http: httpx.Client | None = None) -> dict[str, Any]:
    """The read-back: the window's ask box shows the answer where she asked (the popup's poll)."""
    if not getattr(cfg, "paired", False):
        return {"ok": False, "message": "Hoola Desktop is not paired."}
    c = http or httpx.Client(timeout=TIMEOUT)
    try:
        r = c.get(cfg.server.rstrip("/") + "/api/pc/quickask/messages",
                  params={"conversation_id": conversation_id, "after": int(after)},
                  headers={"Authorization": f"Bearer {cfg.token}"})
    except Exception as e:
        return {"ok": False, "message": f"Could not reach the server: {type(e).__name__}"}
    if r.status_code >= 400:
        return {"ok": False, "message": "No answer found (the conversation does not belong to this device, or the server is busy)."}
    d = r.json()
    return {"ok": True, "messages": d.get("messages", [])}
