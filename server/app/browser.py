"""Santosh Browser (client side): Santosh asks its browser worker (server/browser_worker, browser-use + headless
Chromium) to do a task on a website and turns the worker's answer into what the user sees.

The worker enforces the safety rules; this side only routes results:
  done / failed / blocked   -> the answer goes back to the model (or as a message, when it finished in the background)
  needs_confirm             -> a Bazar confirm card ("Santosh Browser wants to click 'Submit' on xyz.gov.in");
                               only the user's tap lets the worker do that one click
  needs_payment / needs_user-> an Open button: the user finishes the payment / login / OTP on their phone
  running                   -> "working on it", and a background follower posts the result when it's ready
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from .config import get_settings
from .events import bus, notify

log = logging.getLogger("santosh.browser")

PACK_ID = "santosh-browser"


class BrowserError(Exception):
    pass


def configured() -> bool:
    st = get_settings()
    return bool(st.browser_worker_url and st.browser_worker_key)


def llm_config() -> dict[str, Any]:
    """Which model drives the browser. Browsing needs a strong model that can see the page, so Claude comes first."""
    st = get_settings()
    mode = (st.browser_llm or "auto").lower()
    claude = {"provider": "anthropic", "model": st.anthropic_model, "api_key": st.anthropic_api_key}
    omni = {"provider": "openai", "model": st.omniroute_model, "api_key": st.omniroute_key or "none",
            "base_url": st.omniroute_url, "headers": {"x-omniroute-compression": st.omniroute_compression or "off"}}
    glm = {"provider": "openai", "model": st.glm_model, "api_key": st.glm_api_key, "base_url": st.glm_base_url}
    if mode in ("auto", "claude") and st.anthropic_api_key:
        return claude
    if mode in ("auto", "omniroute") and st.omniroute_url:
        return omni
    if mode in ("auto", "glm") and st.glm_api_key:
        return glm
    if st.anthropic_api_key:
        return claude
    raise BrowserError("No AI model is configured for the browser")


def _call(method: str, path: str, *, json: dict | None = None, params: dict | None = None, timeout: float = 30) -> dict:
    st = get_settings()
    if not configured():
        raise BrowserError("Santosh's web browser isn't switched on on this server yet")
    try:
        r = httpx.request(method, st.browser_worker_url.rstrip("/") + path, json=json, params=params,
                          headers={"x-worker-key": st.browser_worker_key}, timeout=timeout)
    except httpx.HTTPError as e:
        raise BrowserError(f"Santosh's browser is not reachable right now ({type(e).__name__})")
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail")
        except Exception:
            detail = r.text[:200]
        raise BrowserError(str(detail or f"browser error {r.status_code}"))
    return r.json()


def start(tenant: str, task: str, start_url: str = "", wait: float | None = None) -> dict:
    st = get_settings()
    wait = max(0, min(int(st.browser_wait_seconds if wait is None else wait), 270))
    return _call("POST", "/tasks", json={"tenant": tenant, "task": task, "start_url": start_url or "",
                                         "llm": llm_config(), "max_steps": max(3, min(st.browser_max_steps, 60)),
                                         "wait_seconds": wait}, timeout=wait + 40)


def get(tenant: str, sid: str, wait: float = 0) -> dict:
    return _call("GET", f"/tasks/{sid}", params={"tenant": tenant, "wait": wait}, timeout=wait + 30)


def approve(tenant: str, sid: str, pending_id: str) -> dict:
    return _call("POST", f"/tasks/{sid}/approve", json={"tenant": tenant, "pending_id": pending_id, "wait_seconds": 0})


def cancel(tenant: str, sid: str) -> dict:
    return _call("POST", f"/tasks/{sid}/cancel", json={"tenant": tenant})


def host_of(url: str) -> str:
    return (urlparse(url or "").hostname or "").removeprefix("www.")


def _open_button(conv: str, url: str, label: str, message: str) -> None:
    if conv and url.startswith(("http://", "https://")):
        bus.publish(conv, "bazar_open", {"kind": "app", "url": url, "package": "", "label": label,
                                         "pack": "Santosh Browser", "message": message})


def deliver(tenant: str, conv: str, res: dict, background: bool = False) -> dict[str, Any]:
    """Show the worker's result to the user. Returns what the model should know (for a chat turn)."""
    status = res.get("status", "")
    sid = res.get("session_id", "")
    url = res.get("url", "")
    site = host_of(url) or "the website"
    answer = (res.get("summary") or "").strip()
    out: dict[str, Any] = {"status": status, "answer": answer, "url": url, "page_title": res.get("title", ""),
                           "steps": res.get("steps", 0)}
    if status == "running":
        follow(tenant, conv, sid)
        out["say"] = ("The browser is still working on it. Tell the user you're on it and will message them in the "
                      "chat as soon as it's done; don't wait.")
        return out
    if status == "needs_confirm":
        from .bazar import service
        try:
            card = service.run(tenant, conv, PACK_ID, "confirm_step", {"session_id": sid})
        except Exception as e:   # bazar ToolError or worker gone
            out.update(status="failed", answer=f"Couldn't prepare the confirm card: {e}")
            return out
        out.update({k: v for k, v in card.items() if k in ("needs_approval", "approval_id", "card", "say")})
        if background:
            label = ((res.get("pending") or {}).get("label")) or "the next step"
            notify(conv, f"{site} par '{label}' karne se pehle aapki manzoori chahiye. Card par Approve dabaiye.")
        return out
    if status in ("needs_payment", "needs_user"):
        why = res.get("reason") or ""
        msg = ("Payment aap khud phone par kariye; Santosh kabhi pay nahi karta." if status == "needs_payment"
               else "Login / OTP / password wala hissa aap khud phone par bhariye; Santosh yeh kabhi nahi bharta.")
        _open_button(conv, url, f"{site} kholiye", msg)
        out["say"] = (f"Stopped before a step only the user may do ({why}). An Open button for {site} is in the chat. "
                      f"Tell them what is ready and that they finish this step themselves.")
        if background:
            notify(conv, (answer + "\n\n" if answer else "") + msg)
        return out
    if background:
        if status == "done":
            notify(conv, answer or f"{site} par kaam ho gaya.")
        elif status == "blocked":
            notify(conv, f"Yeh website Santosh ka browser nahi khol sakta: {res.get('reason') or 'blocked'}.")
        else:
            notify(conv, f"Website par kaam poora nahi ho paya. {answer or res.get('reason') or ''}".strip())
    if status == "blocked":
        out["reason"] = res.get("reason", "")
    if status == "failed":
        out["reason"] = res.get("reason", "") or "the browser could not finish"
    return out


def follow(tenant: str, conv: str, sid: str, max_minutes: float = 10) -> threading.Thread:
    """Wait for a running browser task in the background and post its result to the chat."""
    def loop() -> None:
        deadline = time.time() + max_minutes * 60
        res: dict = {"status": "failed", "reason": "timed out", "session_id": sid}
        while time.time() < deadline:
            try:
                res = get(tenant, sid, wait=60)
            except BrowserError as e:
                res = {"status": "failed", "reason": str(e), "session_id": sid}
                break
            if res.get("status") not in ("running", "starting"):
                break
            time.sleep(1)
        try:
            deliver(tenant, conv, res, background=True)
        except Exception:
            log.exception("browser result delivery failed")
    t = threading.Thread(target=loop, name=f"browser-follow-{sid}", daemon=True)
    t.start()
    return t
