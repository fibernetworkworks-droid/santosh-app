"""HOOLA CINEMA - the one client for the video engine (kie.ai Market API), read from its own docs on 2026-11-11.

  POST https://api.kie.ai/api/v1/jobs/createTask          {model, input} -> data.taskId
  GET  https://api.kie.ai/api/v1/jobs/recordInfo?taskId=  -> data.state waiting | queuing | generating | success | fail,
                                                            data.resultJson '{"resultUrls": [...]}', failMsg, creditsConsumed
  GET  https://api.kie.ai/api/v1/chat/credit              -> data = credits left
  POST https://kieai.redpandaai.co/api/file-stream-upload multipart file + uploadPath -> data.downloadUrl (kept 24 hours)

The key is KIE_API_KEY in the server's .env only: never in chat, never in an answer, never in a log line. `_http` is the
ONE network seam (tests replace exactly it). A 402 (no credits) and a 401 are FINAL - never retried. Nothing here retries
a createTask at all: a second send could be a second charge.
"""
from __future__ import annotations

import json
import re
from typing import Any

API = "https://api.kie.ai/api/v1"
UPLOAD = "https://kieai.redpandaai.co/api/file-stream-upload"
RUNNING = ("waiting", "queuing", "generating")


class KieError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def key() -> str:
    from ..config import get_settings
    return str(getattr(get_settings(), "kie_api_key", "") or "").strip()


def configured() -> bool:
    return bool(key())


SETUP = ("The owner adds the video engine's key to the server settings (KIE_API_KEY in the server's .env file, from "
         "kie.ai > API key) and restarts Hoola. The key is never typed in chat.")


def _scrub(text: str) -> str:
    k = key()
    text = str(text or "")
    if k:
        text = text.replace(k, "[key]")
    return re.sub(r"Bearer\s+\S+", "Bearer [key]", text)[:300]


async def _http(method: str, url: str, *, json_body: dict | None = None, files: dict | None = None,
                data: dict | None = None, params: dict | None = None, timeout: float = 60) -> tuple[int, Any]:
    """The only place a request leaves for the engine. Returns (http status, parsed JSON or {})."""
    import httpx
    k = key()
    if not k:
        raise KieError("NEED_SETUP", SETUP)
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.request(method, url, headers={"Authorization": f"Bearer {k}"}, json=json_body, files=files,
                                data=data, params=params)
    except httpx.HTTPError as e:
        raise KieError("NETWORK", f"The video engine could not be reached ({type(e).__name__}).") from None
    try:
        body = r.json()
    except (ValueError, json.JSONDecodeError):
        body = {}
    return r.status_code, body if isinstance(body, dict) else {}


def _check(status: int, body: dict, what: str) -> None:
    code = body.get("code") if isinstance(body.get("code"), int) else status
    if status == 200 and code == 200:
        return
    msg = _scrub(body.get("msg") or body.get("message") or "")
    worst = code if code != 200 else status
    if worst == 401:
        raise KieError("AUTH", "The video engine refused the key. The owner checks KIE_API_KEY in the server settings.")
    if worst == 402:
        raise KieError("PAYMENT", "The video engine account has no credits left. The owner tops it up at kie.ai; nothing was started.")
    if worst == 429:
        raise KieError("RATE", "The video engine is rate-limiting this account. Try again in a minute.")
    if worst == 455:
        raise KieError("DOWN", "The video engine is under maintenance. Try again later.")
    if worst in (400, 422):
        raise KieError("BAD_INPUT", f"The video engine did not accept the {what}: {msg or 'no reason given'}")
    raise KieError("UPSTREAM", f"The video engine answered {worst} for the {what}{': ' + msg if msg else ''}")


async def upload(data: bytes, name: str, mime: str) -> str:
    """Hand one of HER files to the engine; returns its temporary link (the engine deletes it after 24 hours)."""
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)[-80:] or "file"
    status, body = await _http("POST", UPLOAD, files={"file": (safe, data, mime or "application/octet-stream")},
                               data={"uploadPath": "hoola-cinema", "fileName": safe}, timeout=300)
    _check(status, body, "file")
    url = ((body.get("data") or {}).get("downloadUrl") or "").strip()
    if not url.startswith("https://"):
        raise KieError("UPSTREAM", "The video engine took the file but gave no link for it.")
    return url


async def create(model: str, input_: dict[str, Any]) -> str:
    status, body = await _http("POST", f"{API}/jobs/createTask", json_body={"model": model, "input": input_})
    _check(status, body, "request")
    tid = str((body.get("data") or {}).get("taskId") or "").strip()
    if not tid:
        raise KieError("UPSTREAM", "The video engine started nothing (no task id came back).")
    return tid


async def task(task_id: str) -> dict[str, Any]:
    status, body = await _http("GET", f"{API}/jobs/recordInfo", params={"taskId": task_id}, timeout=30)
    _check(status, body, "status check")
    rec = body.get("data") or {}
    urls: list[str] = []
    try:
        res = json.loads(rec.get("resultJson") or "{}")
        urls = [u for u in (res.get("resultUrls") or []) if isinstance(u, str)]
    except (ValueError, TypeError):
        urls = []
    state = str(rec.get("state") or "").lower()
    credits = rec.get("creditsConsumed")
    return {"state": state if state in RUNNING + ("success", "fail") else "waiting", "urls": urls,
            "credits": float(credits) if isinstance(credits, (int, float)) else None,
            "error": _scrub(rec.get("failMsg") or "")}


async def credits() -> float | None:
    status, body = await _http("GET", f"{API}/chat/credit", timeout=20)
    _check(status, body, "balance check")
    d = body.get("data")
    return float(d) if isinstance(d, (int, float)) else None
