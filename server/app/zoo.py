"""v0.463 ZOO: the BYOK model zoo - 200+ image & video models behind ONE Muapi.ai gateway.

Purely additive to the curated studios (studio/catalog.py video_studio, photogen.py photo_banao):
nothing here replaces or changes them. The curated studios stay the everyday path; the zoo is for
when she needs a specific model / style / aspect the studios don't cover.

- catalog: server/app/zoo_catalog.json (211 real Muapi endpoints, converted mechanically from the
  upstream Open-Higgsfield-AI registry). Add models by appending entries - no code change.
  HOOLA_ZOO_CATALOG can point at a bigger private catalog file with the same shape.
- BYOK: the owner's Muapi key sits in the server env (ZOO_MUAPI_KEY, MUAPI_KEY also accepted) and is
  sent ONLY to api.muapi.ai as the x-api-key header - never logged, never echoed.
- pattern: POST /api/v1/{endpoint} -> {request_id}; poll GET /api/v1/predictions/{id}/result until
  status completed | succeeded | failed. Images usually finish inside a minute; videos run minutes.
- safety: the SAME refusals as photo_banao run BEFORE any gateway call (imported, not copied).
- usage: every finished job is counted in app/usage.py as model "zoo:{endpoint}" (call + seconds;
  rupee cost shows once the owner adds real contract prices to the catalog's usd fields).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger("zoo")

BASE = os.environ.get("MUAPI_BASE", "https://api.muapi.ai").rstrip("/")
POLL_S = 2.0


class ZooError(Exception):
    def __init__(self, msg: str, transient: bool = False):
        super().__init__(msg)
        self.transient = transient


# ----------------------------------------------------------------------------- catalog
_CAT: dict | None = None
_CAT_MTIME = 0.0


def catalog_path() -> Path:
    env = os.environ.get("HOOLA_ZOO_CATALOG", "").strip()
    if env:
        return Path(env)
    return Path(__file__).with_name("zoo_catalog.json")


def load_catalog() -> dict:
    """The bundled registry, re-read when the file changes (hot-add models without a restart)."""
    global _CAT, _CAT_MTIME
    p = catalog_path()
    if not p.is_file():
        raise ZooError(f"zoo catalog missing: {p}", transient=False)
    mt = p.stat().st_mtime
    if _CAT is None or mt != _CAT_MTIME:
        _CAT = json.loads(p.read_text())
        _CAT_MTIME = mt
    return _CAT


def model(model_id: str) -> dict:
    for m in load_catalog().get("models", []):
        if m.get("id") == (model_id or "").strip():
            return m
    raise ZooError(f"zoo model '{model_id}' nahi mila. action=models se poora naam dekhein.")


def list_models(kind: str = "", mode: str = "", q: str = "", limit: int = 40) -> list[dict]:
    kind, mode, q = (kind or "").strip().lower(), (mode or "").strip().lower(), (q or "").strip().lower()
    out = []
    for m in load_catalog().get("models", []):
        if kind and m.get("kind") != kind:
            continue
        if mode and m.get("mode") != mode:
            continue
        if q and q not in f"{m.get('name','')} {m.get('id','')} {m.get('family','')}".lower():
            continue
        out.append(m)
    out.sort(key=lambda m: (m.get("kind", ""), m.get("name", "").lower()))
    return out[: max(1, min(int(limit or 40), 100))]


def key() -> str:
    return (os.environ.get("ZOO_MUAPI_KEY") or os.environ.get("MUAPI_KEY") or "").strip()


def ready() -> bool:
    return bool(key())


# ----------------------------------------------------------------------------- safety
def gate(prompt: str) -> str:
    """'' when OK, else the plain refusal reason. The SAME rules as photo_banao - imported, never copied."""
    try:
        from .photogen import problem as photo_problem
        return photo_problem(prompt or "")
    except Exception:                       # pragma: no cover - the gate must never crash the tool
        log.exception("zoo gate: photo rules unavailable")
        return ""


def _public(url: str) -> None:
    """Gateway results point at their CDN; never accept a link that points inside the network."""
    try:
        from .studio.providers import _public as check
        check(url)
    except ZooError:
        raise
    except Exception:
        log.exception("zoo: public-address check unavailable; treating %s as accepted", url[:80])


# ----------------------------------------------------------------------------- gateway
def _headers() -> dict:
    return {"x-api-key": key(), "Content-Type": "application/json"}


def _payload(m: dict, prompt: str, image_urls: list[str], aspect: str = "", resolution: str = "",
             duration=None, num=None, extra: dict | None = None) -> dict:
    mode = m.get("mode", "t2i")
    p: dict[str, Any] = {}
    if m.get("has_prompt", True) and prompt:
        p["prompt"] = prompt
    if aspect and (not m.get("aspects") or aspect in m["aspects"]):
        p["aspect_ratio"] = aspect
    if resolution:
        res = m.get("resolutions") or []
        fld = "quality" if (res and res[0] in ("basic", "high", "standard", "hd")) else "resolution"
        if not res or resolution in res:
            p[fld] = resolution
    if duration and m.get("durations"):
        d = str(int(duration))
        p["duration"] = d if d in [str(x) for x in m["durations"]] else m["durations"][0]
    if num:
        fld = "num_images" if m.get("kind") == "image" else "num_videos"
        p[fld] = max(1, int(num))
    if mode in ("i2i", "i2v"):
        if not image_urls:
            raise ZooError("is model ko kam se kam EK image URL chahiye (reference photo / start frame).")
        if m.get("max_images") and len(image_urls) > 1:
            p["images_list"] = image_urls[: int(m["max_images"])]
        else:
            p[m.get("image_field") or "image_url"] = image_urls[0]
    for k, v in (extra or {}).items():
        p[str(k)] = v
    return p


async def submit(m: dict, prompt: str, image_urls: list[str] | None = None, aspect: str = "",
                 resolution: str = "", duration=None, num=None, extra: dict | None = None) -> str:
    if not ready():
        raise ZooError("zoo key server par set nahi hai: owner ZOO_MUAPI_KEY env add karein (Muapi.ai key). "
                       "Tab tak zoo list/search kaam karta hai, generate nahi.")
    url = f"{BASE}/api/v1/{m['endpoint']}"
    body = _payload(m, prompt, list(image_urls or []), aspect, resolution, duration, num, extra)
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=20)) as c:
            r = await c.post(url, json=body, headers=_headers())
            if r.status_code >= 400:
                raise ZooError(f"zoo submit HTTP {r.status_code}: {r.text[:300]}",
                               transient=r.status_code in (408, 429) or r.status_code >= 500)
            j = r.json() if r.content else {}
    except httpx.HTTPError as e:
        raise ZooError(f"zoo submit failed: {e}", transient=True) from None
    rid = j.get("request_id") or j.get("id") or j.get("task_id")
    if not rid:
        raise ZooError(f"zoo submit ne request_id nahi diya: {json.dumps(j)[:200]}")
    return str(rid)


_RESULT_URLS = (("outputs",), ("data", "url"), ("video_url",), ("image_url",), ("output",), ("url",))


def _urls(j: dict) -> list[str]:
    out: list[str] = []
    o = j.get("outputs")
    if isinstance(o, list):
        out = [str(x) for x in o if isinstance(x, str)]
    elif isinstance(o, dict):
        out = [str(v) for v in o.values() if isinstance(v, str) and str(v).startswith("http")]
    if not out:
        for path in _RESULT_URLS:
            v: Any = j
            try:
                for k in path:
                    v = v[k]
            except (KeyError, TypeError):
                continue
            if isinstance(v, str) and v.startswith("http"):
                out = [v]
                break
    return out


async def poll(request_id: str) -> dict:
    """One poll: {'status': 'pending'|'done'|'failed', 'urls': [...], 'elapsed': s, 'raw': status}."""
    url = f"{BASE}/api/v1/predictions/{request_id}/result"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=20)) as c:
            r = await c.get(url, headers=_headers())
            if r.status_code >= 400:
                raise ZooError(f"zoo poll HTTP {r.status_code}: {r.text[:300]}",
                               transient=r.status_code in (408, 429) or r.status_code >= 500)
            j = r.json() if r.content else {}
    except httpx.HTTPError as e:
        raise ZooError(f"zoo poll failed: {e}", transient=True) from None
    st = str(j.get("status", "")).lower()
    if st in ("completed", "succeeded", "success", "done"):
        urls = _urls(j)
        for u in urls:
            _public(u)
        return {"status": "done", "urls": urls, "elapsed": j.get("completed_at"), "raw": st}
    if st in ("failed", "error", "cancelled", "canceled"):
        why = str(j.get("error") or j.get("message") or j.get("failed_reason") or "unknown reason")[:300]
        return {"status": "failed", "urls": [], "error": why, "raw": st}
    return {"status": "pending", "urls": [], "raw": st or "unknown"}


async def wait(request_id: str, wait_s: float) -> dict:
    """Poll until done/failed or wait_s runs out (images ~60-90 s; videos usually outlive the chat turn)."""
    t0 = time.monotonic()
    last = {"status": "pending", "urls": []}
    while time.monotonic() - t0 < max(5.0, wait_s):
        last = await poll(request_id)
        if last["status"] != "pending":
            return last
        await asyncio.sleep(POLL_S)
    return last


def _count(m: dict, tenant: str, seconds: float = 0.0) -> None:
    """Count one finished job in usage (never raises - counting must not break the work)."""
    try:
        from . import usage
        usage.record(f"zoo:{m['endpoint']}", sec_out=float(seconds or 0.0), tenant=tenant)
    except Exception:
        log.exception("zoo: usage record failed")


async def run(m: dict, prompt: str, tenant: str = "", image_urls: list[str] | None = None,
              aspect: str = "", resolution: str = "", duration=None, num=None,
              extra: dict | None = None, wait_s: float = 110.0) -> dict:
    """Submit + poll once. Images: usually done inside wait_s. Videos: pending + request_id to check with status()."""
    rid = await submit(m, prompt, image_urls, aspect, resolution, duration, num, extra)
    r = await wait(rid, wait_s)
    if r["status"] == "done":
        _count(m, tenant, seconds=float(duration or 0))
        r["model"], r["name"] = m["id"], m.get("name")
    return {"request_id": rid, **r}
