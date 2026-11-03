"""v0.463 ZOO: the BYOK model zoo - 200+ image & video models behind BYOK gateways.

Purely additive to the curated studios (studio/catalog.py video_studio, photogen.py photo_banao):
nothing here replaces or changes them. The curated studios stay the everyday path; the zoo is for
when she needs a specific model / style / aspect the studios don't cover.

- catalog: server/app/zoo_catalog.json (211 real Muapi endpoints, converted mechanically from the
  upstream Open-Higgsfield-AI registry; v0.463.1 adds the kie.ai section - entries marked
  "gateway": "kie", endpoints = kie's createTask model names). Add models by appending entries -
  no code change. HOOLA_ZOO_CATALOG can point at a bigger private catalog file with the same shape.
- BYOK, TWO gateways: the owner's keys sit in the server env and go ONLY to their gateway -
  ZOO_MUAPI_KEY (MUAPI_KEY also accepted) -> api.muapi.ai as x-api-key;
  ZOO_KIE_KEY (KIE_API_KEY also accepted) -> api.kie.ai as Bearer.
  Never logged, never echoed. An entry without "gateway" rides the catalog root default (muapi).
- muapi pattern: POST /api/v1/{endpoint} -> {request_id}; poll GET /api/v1/predictions/{id}/result
  until status completed | succeeded | failed.
- kie pattern (the Open-Higgsfield transport): POST /api/v1/jobs/createTask {model, input} ->
  data.taskId; poll GET /api/v1/jobs/recordInfo?taskId= -> data.state success|fail|waiting...,
  resultJson.resultUrls. Local / data-URI references upload to kie's CDN first. kie request ids
  come back prefixed "kie:" so status() knows which transport to poll; bare ids stay muapi.
- Images usually finish inside a minute; videos run minutes.
- safety: the SAME refusals as photo_banao run BEFORE any gateway call (imported, not copied).
- usage: every finished job is counted in app/usage.py as "zoo:{endpoint}" (muapi) or
  "zoo:kie:{endpoint}" (kie) - call + seconds; rupee cost shows once the owner adds real
  contract prices to the catalog's usd fields.
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
KIE_BASE = os.environ.get("KIE_BASE", "https://api.kie.ai").rstrip("/")
KIE_UPLOAD = os.environ.get("KIE_UPLOAD", "https://kieai.redpandaai.co/api/file-base64-upload").rstrip("/")


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


def muapi_key() -> str:
    return key()


def kie_key() -> str:
    """The kie.ai key (v0.463.1). Server env only - never logged, never echoed."""
    return (os.environ.get("ZOO_KIE_KEY") or os.environ.get("KIE_API_KEY") or "").strip()


def gateway_of(m: dict) -> str:
    """Which transport a model rides: the entry's own "gateway", else the catalog root default."""
    return str(m.get("gateway") or load_catalog().get("gateway") or "muapi").strip().lower()


def ready_for(m: dict) -> bool:
    return bool(kie_key() if gateway_of(m) == "kie" else key())


def ready() -> bool:
    return bool(key() or kie_key())


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
        fld = m.get("resolution_field") or ("quality" if (res and res[0] in ("basic", "high", "standard", "hd")) else "resolution")
        if not res or resolution in res:
            p[fld] = resolution
    if duration and m.get("durations"):
        d = str(int(duration))
        p["duration"] = d if d in [str(x) for x in m["durations"]] else m["durations"][0]
    if num and gateway_of(m) != "kie":        # kie has no standard num field; extra passthrough covers it
        fld = "num_images" if m.get("kind") == "image" else "num_videos"
        p[fld] = max(1, int(num))
    if mode in ("i2i", "i2v"):
        if not image_urls:
            raise ZooError("is model ko kam se kam EK image URL chahiye (reference photo / start frame).")
        if m.get("max_images") and len(image_urls) > 1:
            p[m.get("images_param") or "images_list"] = image_urls[: int(m["max_images"])]
        else:
            p[m.get("image_field") or "image_url"] = image_urls[0]
    for k, v in (extra or {}).items():
        p[str(k)] = v
    return p


async def kie_upload(data_url: str) -> str:
    """A data-URI / local reference -> a public kie CDN URL (their base64 upload), for kie models."""
    k = kie_key()
    if not k:
        raise ZooError("zoo kie: reference upload ke liye ZOO_KIE_KEY chahiye (server env).")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=20)) as c:
            r = await c.post(KIE_UPLOAD, headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"},
                             json={"base64Data": data_url, "uploadPath": "hoola-zoo",
                                   "fileName": f"ref-{int(time.time() * 1000)}.jpg"})
            if r.status_code >= 400:
                raise ZooError(f"zoo kie upload HTTP {r.status_code}: {r.text[:300]}",
                               transient=r.status_code == 429 or r.status_code >= 500)
            j = r.json() if r.content else {}
    except httpx.HTTPError as e:
        raise ZooError(f"zoo kie upload failed: {e}", transient=True) from None
    d = j.get("data") if isinstance(j.get("data"), dict) else {}
    url = d.get("downloadUrl") or d.get("url") or j.get("downloadUrl") or j.get("url")
    if not url:
        raise ZooError(f"zoo kie upload ne URL nahi diya: {json.dumps(j)[:200]}")
    return str(url)


async def _kie_images(image_urls: list[str]) -> list[str]:
    """kie wants public URLs: http(s) passes, data-URIs and local files upload to their CDN first."""
    out: list[str] = []
    for u in image_urls:
        u = str(u or "").strip()
        if u.startswith("http://") or u.startswith("https://"):
            out.append(u)
        elif u.startswith("data:"):
            out.append(await kie_upload(u))
        elif Path(u).is_file():
            from .studio.providers import data_uri
            out.append(await kie_upload(data_uri(u)))
        else:
            out.append(u)               # not ours to fix - the gateway says what is wrong
    return out


async def _kie_submit(m: dict, prompt: str, image_urls: list[str], aspect: str = "",
                      resolution: str = "", duration=None, num=None, extra: dict | None = None) -> str:
    """POST /api/v1/jobs/createTask {model, input} -> "kie:<taskId>" (the prefix routes poll/status)."""
    k = kie_key()
    if not k:
        raise ZooError("zoo key server par set nahi hai: owner ZOO_KIE_KEY env add karein (kie.ai key). "
                       "Tab tak zoo list/search kaam karta hai, generate nahi.")
    input_body = _payload(m, prompt, await _kie_images(image_urls), aspect, resolution, duration, num, extra)
    body = {"model": m["endpoint"], "input": input_body}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=20)) as c:
            r = await c.post(f"{KIE_BASE}/api/v1/jobs/createTask", json=body,
                             headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"})
            if r.status_code >= 400:
                raise ZooError(f"zoo kie submit HTTP {r.status_code}: {r.text[:300]}",
                               transient=r.status_code in (408, 429) or r.status_code >= 500)
            j = r.json() if r.content else {}
    except httpx.HTTPError as e:
        raise ZooError(f"zoo kie submit failed: {e}", transient=True) from None
    d = j.get("data") if isinstance(j.get("data"), dict) else {}
    tid = d.get("taskId") or d.get("task_id")
    if j.get("code") not in (200, 505) or not tid:
        raise ZooError(f"zoo kie submit rejected ({j.get('code')}): {str(j.get('msg') or j.get('message') or '')[:200]} "
                       f"{json.dumps(j)[:200]}")
    return f"kie:{tid}"


async def _kie_poll(task_id: str) -> dict:
    """GET /api/v1/jobs/recordInfo?taskId= -> state success|fail|waiting...; resultJson.resultUrls."""
    k = kie_key()
    if not k:
        raise ZooError("zoo kie key server par set nahi hai (ZOO_KIE_KEY).")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=20)) as c:
            r = await c.get(f"{KIE_BASE}/api/v1/jobs/recordInfo", params={"taskId": task_id},
                            headers={"Authorization": f"Bearer {k}"})
            if r.status_code >= 400:
                raise ZooError(f"zoo kie poll HTTP {r.status_code}: {r.text[:300]}",
                               transient=r.status_code in (408, 429) or r.status_code >= 500)
            j = r.json() if r.content else {}
    except httpx.HTTPError as e:
        raise ZooError(f"zoo kie poll failed: {e}", transient=True) from None
    rec = j.get("data") if isinstance(j.get("data"), dict) else {}
    st = str(rec.get("state", "")).lower()
    if st in ("success", "completed", "done"):
        urls: list[str] = []
        try:
            rj = json.loads(rec.get("resultJson") or "{}")
            urls = [str(x) for x in (rj.get("resultUrls") or []) if str(x).startswith("http")]
        except (ValueError, TypeError):
            pass
        for u in urls:
            _public(u)
        return {"status": "done", "urls": urls, "elapsed": rec.get("completedAt") or rec.get("completed_at"), "raw": st}
    if st in ("fail", "failed", "error", "cancelled", "canceled"):
        why = str(rec.get("failMsg") or rec.get("failmsg") or rec.get("error") or "unknown reason")[:300]
        return {"status": "failed", "urls": [], "error": why, "raw": st}
    return {"status": "pending", "urls": [], "raw": st or "unknown"}


async def submit(m: dict, prompt: str, image_urls: list[str] | None = None, aspect: str = "",
                 resolution: str = "", duration=None, num=None, extra: dict | None = None) -> str:
    if gateway_of(m) == "kie":
        return await _kie_submit(m, prompt, list(image_urls or []), aspect, resolution, duration, num, extra)
    if not ready_for(m):
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
    """One poll: {'status': 'pending'|'done'|'failed', 'urls': [...], 'elapsed': s, 'raw': status}.
    "kie:"-prefixed ids ride the kie recordInfo transport; bare ids stay muapi (old jobs keep working)."""
    if str(request_id).startswith("kie:"):
        return await _kie_poll(str(request_id)[4:])
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
        tag = f"zoo:{m['endpoint']}" if gateway_of(m) != "kie" else f"zoo:kie:{m['endpoint']}"
        usage.record(tag, sec_out=float(seconds or 0.0), tenant=tenant)
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
