"""v0.752 ARTCRAFT IN CREATE - the page door over the v0.730 SHILP lane (owner: "now lets develop a artcraft in create
section in hoola --- artcraft is already developed in backend").

The `shilp` tool (agent/shilp_tools.py) is the only thing that talks to ArtCraft's Omni API; this router never builds a
request of its own, so every law of that lane holds here too (BYOK key in the VPS .env, a fresh idempotency token per
generation, reference urls through the lane's wall, a 402 is final, job states raw). What a PAGE needs on top:

  GET    /api/shilp                     the lane's state (key set or the setup steps), the curated catalog, her jobs
                                        (running ones refreshed in one batch call), the model ids she used before
  POST   /api/shilp/generate            start a video / picture - needs confirm=true (the Create button IS her tap,
                                        it spends her ArtCraft credits); every job token it returns is kept
  POST   /api/shilp/jobs/{token}/check  poll one job; the first time it finishes, the file is fetched ONCE from the
                                        cdn_url ArtCraft returned and kept on her Create shelf (My creations), so it
                                        survives their link expiring - only that recorded url is ever fetched
  DELETE /api/shilp/jobs/{token}        take a job off this list (a file already on her shelf stays there)

Behind `shilp_page` (off = every route 404s) and the lane's own `shilp_enabled`. Her jobs live in
data/shilp/<tenant>/jobs.json.
"""
from __future__ import annotations

import json
import mimetypes
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..agent import shilp_tools as SH

_LOCK = threading.Lock()
_KEEP = 200                     # jobs remembered per person
_MAX_FILE = 300 * 1024 * 1024   # a finished file bigger than this is not copied (the link is kept)
_RUNNING = ("pending", "started", "attempt_failed", "unknown")


class GenIn(BaseModel):
    kind: str = "video"
    model: str = ""
    prompt: str = ""
    duration_seconds: int | None = None
    aspect_ratio: str = ""
    resolution: str = ""
    negative_prompt: str = ""
    generate_audio: bool | None = None
    start_frame_image_url: str = ""
    end_frame_image_url: str = ""
    reference_image_urls: list[str] = []
    image_urls: list[str] = []
    confirm: bool = False


def _on() -> None:
    from ..config import get_settings
    if not bool(getattr(get_settings(), "shilp_page", False)):
        raise HTTPException(404, "ArtCraft in Create is switched off on this server (SHILP_PAGE).")


def _dir(tenant: str) -> Path:
    from ..config import get_settings
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", tenant or "default")[:80] or "default"
    base = Path(getattr(get_settings(), "data_dir", "./data") or "./data")
    p = base / "shilp" / safe
    p.mkdir(parents=True, exist_ok=True)
    return p


def _read(tenant: str) -> list[dict[str, Any]]:
    f = _dir(tenant) / "jobs.json"
    try:
        data = json.loads(f.read_text())
        return data if isinstance(data, list) else []
    except Exception:                                   # noqa: BLE001 - a missing / torn file = no jobs yet
        return []


def _write(tenant: str, jobs: list[dict[str, Any]]) -> None:
    f = _dir(tenant) / "jobs.json"
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(jobs[:_KEEP], ensure_ascii=False))
    tmp.replace(f)


def _update(tenant: str, token: str, **fields: Any) -> dict[str, Any] | None:
    with _LOCK:
        jobs = _read(tenant)
        for j in jobs:
            if j.get("token") == token:
                j.update(fields)
                j["updated"] = int(time.time())
                _write(tenant, jobs)
                return dict(j)
    return None


def _public(j: dict[str, Any]) -> dict[str, Any]:
    return dict(j) | {"has_link": bool(j.get("cdn_url"))}


def _err(env: dict[str, Any]) -> HTTPException:
    e = env.get("error") or {}
    code = {"BAD_INPUT": 400, "NOT_ALLOWED": 400, "NEED_SETUP": 409, "AUTH": 401, "PAYMENT": 402}.get(e.get("code"), 502)
    msg = e.get("message") or "ArtCraft did not answer."
    if e.get("hint"):
        msg = f"{msg}. {e['hint']}"
    return HTTPException(code, msg)


def _title(prompt: str, kind: str) -> str:
    t = " ".join((prompt or "").split())
    return (t[:60] + ("…" if len(t) > 60 else "")) or ("ArtCraft video" if kind == "video" else "ArtCraft picture")


async def _fetch(url: str) -> tuple[str, bytes]:
    """The ONE download seam (tests replace exactly this): the finished file at ArtCraft's link, size-capped."""
    import httpx
    data = b""
    async with httpx.AsyncClient(timeout=180, follow_redirects=True, max_redirects=5) as c:
        async with c.stream("GET", url) as r:
            if r.status_code != 200:
                raise ValueError(f"their file link answered {r.status_code}")
            ctype = (r.headers.get("content-type") or "").split(";")[0].strip()
            async for chunk in r.aiter_bytes():
                data += chunk
                if len(data) > _MAX_FILE:
                    raise ValueError("the file is bigger than 300 MB - open it from ArtCraft's link")
    return ctype, data


async def _save(tenant: str, j: dict[str, Any]) -> dict[str, Any]:
    """Copy the finished file onto her Create shelf, once. Only the url ArtCraft returned for THIS job is fetched,
    and it must pass the lane's own wall (public https, no private hosts)."""
    url = j.get("cdn_url") or ""
    try:
        url = SH._ref_url(url, "cdn_url")
        if not url.startswith("https://"):
            raise ValueError("the finished file's link is not https")
        ctype, data = await _fetch(url)
        kind = j.get("kind") or "video"
        want = "video/" if kind == "video" else "image/"
        if not ctype.startswith(want):
            guess = mimetypes.guess_type(url.split("?")[0])[0] or ""
            ctype = guess if guess.startswith(want) else ctype
        if not ctype.startswith(want):
            raise ValueError(f"the file is not a {kind} ({ctype or 'unknown type'})")
        ext = mimetypes.guess_extension(ctype) or (".mp4" if kind == "video" else ".png")
        ext = {".jpe": ".jpg", ".jpeg": ".jpg"}.get(ext, ext)
        from ..create import jobs as CJ
        item = CJ.keep(tenant, "video" if kind == "video" else "image", _title(j.get("prompt", ""), kind), ext, data,
                       {"source": "ArtCraft", "model": j.get("model", ""), "job": j.get("token", ""),
                        "aspect": j.get("aspect_ratio", "")})
        return _update(tenant, j["token"], item_id=item["id"], save_error="") or j
    except Exception as e:                              # noqa: BLE001 - the link stays; she can open it at ArtCraft
        return _update(tenant, j["token"], save_error=str(e)[:200]) or j


def _apply(tenant: str, m: dict[str, Any]) -> dict[str, Any] | None:
    st = m.get("job_status") or "unknown"
    fields: dict[str, Any] = {"status": st, "progress": m.get("progress"), "done": bool(m.get("done")),
                              "ok": bool(m.get("job_ok")), "failure": m.get("failure_category") or ""}
    if m.get("cdn_url"):
        fields["cdn_url"] = m["cdn_url"]
    prev = m.get("previews") or {}
    if prev.get("still"):
        fields["still"] = prev["still"]
    return _update(tenant, m.get("job_token") or "", **fields)


async def overview(tenant: str) -> dict[str, Any]:
    st = await SH.shilp(None, "status")
    cat = await SH.shilp(None, "models")
    jobs = _read(tenant)
    live = [j["token"] for j in jobs if not j.get("done")][:SH._MAX_TOKENS]
    refresh_error = ""
    if live and st.get("ok") and st.get("key_set"):
        env = await SH.shilp(None, "jobs", tokens=live)
        if env.get("ok"):
            for m in env.get("jobs") or []:
                _apply(tenant, m)
        else:
            refresh_error = (env.get("error") or {}).get("message", "")
        jobs = _read(tenant)
        for j in jobs:
            if j.get("ok") and not j.get("item_id") and not j.get("save_error") and j.get("cdn_url"):
                await _save(tenant, j)
        jobs = _read(tenant)
    used = []
    for j in jobs:
        key = (j.get("kind"), j.get("model"))
        if j.get("model") and key not in [(u["kind"], u["model"]) for u in used]:
            used.append({"kind": j.get("kind"), "model": j.get("model")})
    return {"enabled": bool(st.get("ok")), "key_set": bool(st.get("key_set")),
            "setup": st.get("setup") or "", "lane_error": (st.get("error") or {}).get("message", "") if not st.get("ok") else "",
            "catalog": cat.get("catalog") or {}, "catalog_note": cat.get("note") or "", "counts": cat.get("counts") or {},
            "documented_example": "seedance_2p0", "used_models": used[:12],
            "refresh_error": refresh_error, "jobs": [_public(j) for j in jobs]}


async def generate(tenant: str, body: GenIn) -> dict[str, Any]:
    if not body.confirm:
        raise HTTPException(400, "Starting an ArtCraft job spends your ArtCraft credits - confirm it first.")
    kind = "image" if body.kind == "image" else "video"
    args: dict[str, Any] = {"model": body.model.strip(), "prompt": body.prompt.strip()}
    if kind == "video":
        args.update({"duration_seconds": body.duration_seconds, "aspect_ratio": body.aspect_ratio or None,
                     "resolution": body.resolution or None, "negative_prompt": body.negative_prompt or None,
                     "generate_audio": body.generate_audio,
                     "start_frame_image_url": body.start_frame_image_url or None,
                     "end_frame_image_url": body.end_frame_image_url or None,
                     "reference_image_urls": [u for u in body.reference_image_urls if u.strip()] or None})
    else:
        args["image_urls"] = [u for u in body.image_urls if u.strip()] or None
    if not args["prompt"]:
        raise HTTPException(400, "Describe what ArtCraft should make.")
    env = await SH.shilp(None, kind, **args)
    if not env.get("ok"):
        raise _err(env)
    tokens = [t for t in (env.get("all_job_tokens") or []) if t] or [env.get("job_token")]
    now = int(time.time())
    rows = [{"token": t, "kind": kind, "model": env.get("model", args["model"]), "prompt": args["prompt"],
             "aspect_ratio": args.get("aspect_ratio") or "", "resolution": args.get("resolution") or "",
             "duration_seconds": args.get("duration_seconds"), "idempotency": env.get("idempotency_token", ""),
             "status": "pending", "progress": None, "done": False, "ok": False, "created": now, "updated": now}
            for t in tokens if t]
    with _LOCK:
        jobs = _read(tenant)
        have = {j.get("token") for j in jobs}
        _write(tenant, [r for r in rows if r["token"] not in have] + jobs)
    return {"started": [_public(r) for r in rows], "note": "Started. This spent ArtCraft credits."}


async def check(tenant: str, token: str) -> dict[str, Any]:
    if not any(j.get("token") == token for j in _read(tenant)):
        raise HTTPException(404, "That job is not on your list.")
    env = await SH.shilp(None, "job", token=token)
    if not env.get("ok"):
        raise _err(env)
    j = _apply(tenant, env) or {}
    if j.get("ok") and not j.get("item_id") and j.get("cdn_url"):
        j = await _save(tenant, j)
    return _public(j)


def remove(tenant: str, token: str) -> dict[str, Any]:
    with _LOCK:
        jobs = _read(tenant)
        left = [j for j in jobs if j.get("token") != token]
        if len(left) == len(jobs):
            raise HTTPException(404, "That job is not on your list.")
        _write(tenant, left)
    return {"removed": token}


def _shilp_router(require_key: Callable, current_tenant: Callable) -> APIRouter:
    r = APIRouter(prefix="/api/shilp", tags=["shilp"], dependencies=[Depends(require_key), Depends(_on)])

    @r.get("")
    async def shilp_overview(tenant: str = Depends(current_tenant)):
        return await overview(tenant)

    @r.post("/generate")
    async def shilp_generate(body: GenIn, tenant: str = Depends(current_tenant)):
        return await generate(tenant, body)

    @r.post("/jobs/{token}/check")
    async def shilp_check(token: str, tenant: str = Depends(current_tenant)):
        return await check(tenant, token)

    @r.delete("/jobs/{token}")
    def shilp_remove(token: str, tenant: str = Depends(current_tenant)):
        return remove(tenant, token)

    return r
