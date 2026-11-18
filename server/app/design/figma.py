"""D7 bridge A - FIGMA IMPORT (docs/HOOLA_DESIGN_PLAN.md section 7 A).

She imports her own Figma file into a NEW Hoola Design file, through Figma's official REST API with HER personal
access token. The token lives in ONE place: the website builder's sealed store (`site/inspire.py` SiteFigmaKey, one
token per account, shared with Web Studio). It is typed into the page, never into chat; no route returns it, no job
record holds it, no log line names it - it lives in a local variable of the worker thread for the length of a fetch.

    GET / PUT / DELETE /api/design/figma        status / save / forget (thin wrappers over inspire's functions)
    POST /api/design/import/figma {url, name?}  -> {job}        GET /api/design/import/{job} -> the job

A job runs as a task on the server's event loop; every slow step (Figma's API, the picture downloads, the conversion)
runs in this module's own worker threads, and the new file is written THROUGH its room (design.room) in chunks, so it
is an ordinary file: snapshot + journal, open in any editor while it fills.
    queued -> reading (the file JSON) -> images (image fills + Figma's own picture of layers that can not be
    converted) -> writing (ops through the room) -> done | failed
Jobs are kept IN MEMORY (per process, per tenant, the last 20 for a day): a server restart forgets the job record. A
file already being written stays a normal file; its name keeps the "(importing...)" mark it was given until the import
finished, so a cut import is visible for what it is.

Limits: a request budget against api.figma.com per import, 429 answered by waiting Figma's Retry-After (capped), the
document's layer cap, a size cap on each picture and on all of them, pictures only from Figma's own image hosts (no
redirects followed), each picture checked by content like an upload (design.assets).
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import Depends, HTTPException
from pydantic import BaseModel

from ..config import get_settings

log = logging.getLogger("hoola.design.figma")

API = "https://api.figma.com"
REQUEST_BUDGET = 40              # calls to api.figma.com in one import (file + image lists + fallback renders + retries)
RETRY_MAX = 3                    # 429 answers waited out per call
RETRY_WAIT_MAX = 60.0            # seconds: a longer Retry-After ends the import with a plain message
FILE_BYTES_MAX = 200 * 1024 * 1024
IMAGE_BYTES_MAX = 10 * 1024 * 1024
IMAGES_BYTES_MAX = 250 * 1024 * 1024
IMAGES_MAX = 600
RENDER_MAX = 200                 # layers drawn by Figma itself (types Hoola can not convert)
RENDER_BATCH = 50
CHUNK = 1500                     # ops per room batch while writing
JOBS_KEEP = 20
JOBS_TTL_S = 24 * 3600
ACTIVE_MAX = 3                   # imports running at once on this server
IMAGE_HOSTS = (".amazonaws.com", ".figma.com", ".figmafiles.com")
WATCH = "/console/design#/import/"
MARK = " (importing...)"

_TRANSPORT: httpx.BaseTransport | None = None        # tests: a fake Figma
_SLEEP = time.sleep                                 # tests: no real waiting on a 429
_POOL = ThreadPoolExecutor(max_workers=3, thread_name_prefix="design-figma")
_JOBS: dict[str, dict] = {}
_TASKS: set[asyncio.Task] = set()


def set_transport(t: httpx.BaseTransport | None) -> None:
    global _TRANSPORT
    _TRANSPORT = t


class FigmaError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


# ================================================================================ the shared sealed token
NO_TOKEN = ("Add your Figma personal access token first: Hoola Design > Import from Figma. It is stored sealed and "
            "shared with Web Studio. Never paste it into a chat.")


def token_status(tenant: str) -> dict:
    from ..site import inspire
    st = inspire.figma_status(tenant)
    return {"linked": bool(st.get("linked")), "hint": st.get("hint") or ""}


def save_token(tenant: str, token: str) -> dict:
    from ..site import inspire
    try:
        inspire.set_figma_token(tenant, token)
    except inspire.InspireError:
        raise FigmaError("That does not look like a Figma personal access token. Make one in Figma: Settings > "
                         "Security > Personal access tokens (give it read access to file content).") from None
    except Exception:                                    # noqa: BLE001 - e.g. no SECRET_KEY to seal it with
        log.exception("figma token could not be sealed")
        raise FigmaError("The token could not be stored safely on this server (sealing is not set up).", 500) from None
    out = token_status(tenant)
    return {"ok": True, **out}


def forget_token(tenant: str) -> dict:
    from ..site import inspire
    inspire.forget_figma(tenant)
    return {"ok": True, "linked": False, "hint": ""}


def _token(tenant: str) -> str:
    from ..site import inspire
    try:
        return inspire._figma_token(tenant)
    except inspire.InspireError:
        raise FigmaError(NO_TOKEN, 409) from None
    except Exception:                                    # noqa: BLE001 - the seal can not be opened (key changed)
        raise FigmaError("Your saved Figma token can not be read any more. Save it again in Import from Figma.", 409) from None


_KEY = re.compile(r"figma\.com/(?:file|design|proto|board|slides)/([A-Za-z0-9]{10,64})(?:/[^/?#]*)?(?:/branch/([A-Za-z0-9]{10,64}))?")


def file_key(url: str) -> str:
    """The file key of a Figma link (a branch link -> the branch's key, as Figma's own API wants it)."""
    m = _KEY.search(str(url or ""))
    if not m:
        raise FigmaError("Paste the link of a Figma design file (it looks like figma.com/design/<key>/<name>).")
    if "/board/" in m.group(0) or "/slides/" in m.group(0):
        raise FigmaError("That is a FigJam board or a Slides file. Only Figma design files can be imported.")
    return m.group(2) or m.group(1)


# ================================================================================ Figma's API (worker threads)
def _figma_said(r: httpx.Response) -> str:
    try:
        body = r.json()
    except Exception:                                    # noqa: BLE001
        return ""
    said = body.get("err") or body.get("message") if isinstance(body, dict) else ""
    said = re.sub(r"\s+", " ", str(said or "")).strip()[:200]
    return f' Figma said: "{said}".' if said else ""


class _Budget:
    def __init__(self, n: int = REQUEST_BUDGET):
        self.left = n

    def take(self) -> None:
        if self.left <= 0:
            raise FigmaError("This file needs more requests to Figma than one import may make. Import a smaller file, "
                             "or split it into a few files in Figma.", 429)
        self.left -= 1


def _get_json(client: httpx.Client, path: str, params: dict, budget: _Budget, cap: int = FILE_BYTES_MAX) -> dict:
    waited = 0
    while True:
        budget.take()
        try:
            with client.stream("GET", API + path, params=params) as r:
                if r.status_code == 200:
                    declared = r.headers.get("content-length", "")
                    if declared.isdigit() and int(declared) > cap:
                        raise FigmaError("This Figma file is too large to import in one go.", 413)
                    chunks, size = [], 0
                    for chunk in r.iter_bytes():
                        size += len(chunk)
                        if size > cap:
                            raise FigmaError("This Figma file is too large to import in one go.", 413)
                        chunks.append(chunk)
                    raw = b"".join(chunks)
                else:
                    r.read()
                    raw = None
        except httpx.HTTPError as e:
            raise FigmaError(f"Hoola could not reach Figma ({type(e).__name__}). Try again in a minute.", 502) from None
        if raw is not None:
            try:
                data = json.loads(raw)
            except ValueError:
                raise FigmaError("Figma's answer could not be read.", 502) from None
            if not isinstance(data, dict):
                raise FigmaError("Figma's answer could not be read.", 502)
            return data
        code = r.status_code
        if code == 429:
            if waited >= RETRY_MAX:
                raise FigmaError("Figma is limiting requests from your account right now. Try the import again in a "
                                 "few minutes.", 429)
            try:
                wait = float(r.headers.get("retry-after", "") or 5)
            except ValueError:
                wait = 5.0
            if wait > RETRY_WAIT_MAX:
                raise FigmaError(f"Figma asked Hoola to wait {int(wait)} seconds before the next request. Try the "
                                 "import again later.", 429)
            waited += 1
            _SLEEP(max(0.0, wait))
            continue
        said = _figma_said(r)
        if code in (401, 403):
            raise FigmaError("Figma refused (403): the token is wrong or has expired, or your Figma account can not "
                             "open this file. Check that the file is yours or shared with you, or save a new token."
                             + said, 403)
        if code == 404:
            raise FigmaError("Figma has no file at this link (404): check the link, or the file was deleted." + said, 404)
        if code == 400:
            raise FigmaError("Figma did not accept the request (400)." + said, 400)
        raise FigmaError(f"Figma had a problem answering ({code}). Try again in a few minutes." + said, 502)


def _image_url_ok(url: Any) -> bool:
    try:
        u = urlparse(str(url))
    except ValueError:
        return False
    host = (u.hostname or "").lower()
    return u.scheme == "https" and any(host.endswith(h) or host == h.lstrip(".") for h in IMAGE_HOSTS)


def _download(client: httpx.Client, url: str, cap: int) -> bytes | None:
    """One picture from Figma's own storage, never following a redirect, never more than `cap` bytes. No token."""
    if not _image_url_ok(url):
        return None
    try:
        with client.stream("GET", url) as r:
            if r.status_code != 200:
                return None
            declared = r.headers.get("content-length", "")
            if declared.isdigit() and int(declared) > cap:
                return None
            chunks, size = [], 0
            for chunk in r.iter_bytes():
                size += len(chunk)
                if size > cap:
                    return None
                chunks.append(chunk)
            return b"".join(chunks)
    except httpx.HTTPError:
        return None


def _read_file(tenant: str, key: str, budget: _Budget) -> dict:
    tok = _token(tenant)
    with httpx.Client(timeout=90, transport=_TRANSPORT, headers={"X-Figma-Token": tok}, follow_redirects=False) as c:
        return _get_json(c, f"/v1/files/{key}", {"geometry": "paths"}, budget)


def _image_map(tenant: str, key: str, budget: _Budget) -> dict[str, str]:
    """imageRef -> a short-lived download address of every image fill of the file."""
    tok = _token(tenant)
    with httpx.Client(timeout=60, transport=_TRANSPORT, headers={"X-Figma-Token": tok}, follow_redirects=False) as c:
        data = _get_json(c, f"/v1/files/{key}/images", {}, budget, 20 * 1024 * 1024)
    images = (data.get("meta") or {}).get("images") if isinstance(data.get("meta"), dict) else data.get("images")
    return {str(k): str(v) for k, v in (images or {}).items() if isinstance(v, str)} if isinstance(images, dict) else {}


def _render_map(tenant: str, key: str, ids: list[str], budget: _Budget) -> dict[str, str]:
    """Figma's own PNG of the layers Hoola can not convert: node id -> download address."""
    tok = _token(tenant)
    out: dict[str, str] = {}
    with httpx.Client(timeout=90, transport=_TRANSPORT, headers={"X-Figma-Token": tok}, follow_redirects=False) as c:
        for i in range(0, len(ids), RENDER_BATCH):
            part = ids[i:i + RENDER_BATCH]
            data = _get_json(c, f"/v1/images/{key}", {"ids": ",".join(part), "format": "png", "scale": "2"}, budget,
                             20 * 1024 * 1024)
            imgs = data.get("images") if isinstance(data.get("images"), dict) else {}
            out.update({str(k): str(v) for k, v in imgs.items() if isinstance(v, str)})
    return out


def _store_pictures(tenant: str, wanted: dict[str, str], job: dict, label: str) -> tuple[dict[str, str], int]:
    """Download each address ONCE and keep it as a Hoola asset (checked by content); key -> asset hash."""
    from . import assets
    got: dict[str, str] = {}
    by_url: dict[str, str] = {}
    total, bad = job.get("_bytes", 0), 0
    with httpx.Client(timeout=60, transport=_TRANSPORT, follow_redirects=False) as c:
        for key, url in wanted.items():
            if url in by_url:
                got[key] = by_url[url]
                job["done"] += 1
                continue
            data = _download(c, url, min(IMAGE_BYTES_MAX, IMAGES_BYTES_MAX - total)) if total < IMAGES_BYTES_MAX else None
            job["done"] += 1
            job["step"] = f"{label} {job['done']} of {job['total']}"
            if not data:
                bad += 1
                continue
            try:
                saved = assets.save_asset(tenant, data)
            except assets.BadImage:
                bad += 1
                continue
            total += len(data)
            got[key] = by_url[url] = saved["hash"]
    job["_bytes"] = total
    return got, bad


def _convert(doc: dict, cid: int, cap: int):
    from . import figma_convert
    from .ai import id_maker
    return figma_convert.Converter(doc, id_maker(cid), cap).run()


# ================================================================================ jobs
def _view(job: dict) -> dict:
    return {k: v for k, v in job.items() if not k.startswith("_") and k != "tenant"}


def _sweep() -> None:
    edge = time.time() - JOBS_TTL_S
    for jid in [j for j, v in _JOBS.items() if v["_at"] < edge and v["state"] in ("done", "failed")]:
        del _JOBS[jid]
    by: dict[str, list[dict]] = {}
    for v in _JOBS.values():
        by.setdefault(v["tenant"], []).append(v)
    for rows in by.values():
        old = sorted((r for r in rows if r["state"] in ("done", "failed")), key=lambda r: r["_at"])
        for r in old[:max(0, len(rows) - JOBS_KEEP)]:
            _JOBS.pop(r["id"], None)


def job(tenant: str, job_id: str) -> dict | None:
    got = _JOBS.get(str(job_id or ""))
    return _view(got) if got is not None and got["tenant"] == tenant else None


async def _bg(fn, *args):
    return await asyncio.get_running_loop().run_in_executor(_POOL, fn, *args)


async def start(tenant: str, url: str, name: str = "") -> dict:
    """Start an import (on the running event loop). FigmaError for a bad link, no token, or one already running."""
    st = get_settings()
    if not getattr(st, "design_page", False):
        raise FigmaError("Hoola Design is switched off on this server.", 404)
    key = file_key(url)
    if not (await _bg(token_status, tenant))["linked"]:
        raise FigmaError(NO_TOKEN, 409)
    _sweep()
    running = [j for j in _JOBS.values() if j["state"] not in ("done", "failed")]
    if any(j["tenant"] == tenant for j in running):
        raise FigmaError("An import from Figma is already running for you. Wait for it to finish.", 409)
    if len(running) >= ACTIVE_MAX:
        raise FigmaError("This server is busy with other imports. Try again in a few minutes.", 429)
    jid = "fi_" + secrets.token_urlsafe(12)
    rec = {"id": jid, "tenant": tenant, "state": "queued", "step": "Waiting to start", "done": 0, "total": 0,
           "file": None, "name": "", "warnings": [], "error": None, "layers": 0, "pages": 0, "images": 0,
           "watch": WATCH + jid, "created_at": time.time(), "_at": time.time(), "_bytes": 0}
    _JOBS[jid] = rec
    task = asyncio.ensure_future(_run(rec, tenant, key, " ".join(str(name or "").split())[:200]))
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)
    return _view(rec)


def _step(rec: dict, state: str, step: str, done: int = 0, total: int = 0) -> None:
    rec.update(state=state, step=step, done=done, total=total, _at=time.time())


async def _run(rec: dict, tenant: str, key: str, name: str) -> None:
    from . import store
    from .doc import FIRST_PAGE, MAX_NODES, ROOT, dumps_nodes, new_document
    from .room import HUB, bg
    made: dict | None = None
    try:
        budget = _Budget()
        _step(rec, "reading", "Reading the file from Figma")
        doc = await _bg(_read_file, tenant, key, budget)
        if not isinstance(doc.get("document"), dict):
            raise FigmaError("Figma's answer had no document in it.", 502)
        fname = " ".join(str(name or doc.get("name") or "Figma import").split())[:180] or "Figma import"
        rec["name"] = fname
        cap = int(getattr(get_settings(), "design_max_nodes", MAX_NODES) or MAX_NODES)
        nodes = new_document("")
        made = await bg(store.create_file, tenant, fname + MARK, dumps_nodes(nodes), len(nodes))
        rec["file"] = made["id"]
        cid = await HUB.new_cid(made["id"])
        _step(rec, "reading", "Converting the layers")
        conv = await _bg(_convert, doc, cid, cap)
        images: dict[str, str] = {}
        renders: dict[str, str] = {}
        refs = sorted(conv.image_refs)[:IMAGES_MAX]
        if len(conv.image_refs) > IMAGES_MAX:
            conv.w("Image fills over the limit of one import (not imported)", len(conv.image_refs) - IMAGES_MAX)
        fall = list(conv.fallback.items())[:RENDER_MAX]
        if len(conv.fallback) > RENDER_MAX:
            conv.w("Layers to be drawn by Figma over the limit of one import (not imported)", len(conv.fallback) - RENDER_MAX)
        if refs or fall:
            _step(rec, "images", "Asking Figma for the pictures", 0, len(refs) + len(fall))
        if refs:
            where = await _bg(_image_map, tenant, key, budget)
            wanted = {r: where[r] for r in refs if r in where}
            rec["done"] += len(refs) - len(wanted)
            images, _bad = await _bg(_store_pictures, tenant, wanted, rec, "Picture")
        if fall:
            where = await _bg(_render_map, tenant, key, [f for _, f in fall], budget)
            wanted = {f: where[f] for _, f in fall if f in where}
            rec["done"] += len(fall) - len(wanted)
            renders, _bad = await _bg(_store_pictures, tenant, wanted, rec, "Picture")
        rec["images"] = len(set(images.values()) | set(renders.values()))
        ops = await _bg(conv.finish, images, renders)
        _step(rec, "writing", "Writing the layers into the new file", 0, len(ops))
        room = await HUB.open(made["id"], tenant)
        rejected = 0
        try:
            for i in range(0, len(ops), CHUNK):
                part = ops[i:i + CHUNK]
                out = room.apply_external(part)
                rejected += len(out["rejected"])
                rec["done"] = min(len(ops), i + len(part))
                rec["step"] = f"Writing layers {rec['done']:,} of {len(ops):,}"
                rec["_at"] = time.time()
                await asyncio.sleep(0)
        finally:
            await HUB.release(room)
        if rejected:
            conv.w("Layers the document rules refused (not imported)", rejected)
        renamed = await bg(store.patch_file, tenant, made["id"], fname, None)
        if renamed:
            HUB.renamed(made["id"], renamed["name"])
        rec["layers"] = sum(1 for o in ops if o["id"] not in (ROOT, FIRST_PAGE) and "type" in o["p"]) - rejected
        rec["pages"] = sum(1 for o in ops if o["p"].get("type") == "PAGE" or o["id"] == FIRST_PAGE)
        rec["warnings"] = conv.warnings()
        _step(rec, "done", "Imported", len(ops), len(ops))
    except FigmaError as e:
        await _failed(rec, tenant, made, str(e))
    except Exception:                                    # noqa: BLE001 - never a stack trace to her, never a token
        log.exception("figma import %s failed", rec["id"])
        await _failed(rec, tenant, made, "The import stopped because of a problem on Hoola's side. Nothing was "
                                         "changed in Figma; try again, and tell us if it keeps happening.")


async def _failed(rec: dict, tenant: str, made: dict | None, message: str) -> None:
    from . import store
    from .room import HUB, bg
    if made is not None:
        try:
            await bg(store.set_trashed, tenant, made["id"], True)
            HUB.evict(made["id"], 4404)
            message += " The half-made file was moved to the trash."
        except Exception:                                # noqa: BLE001
            log.exception("figma import %s: the half-made file could not be trashed", rec["id"])
    rec.update(state="failed", step="Stopped", error=message, _at=time.time())


# ================================================================================ HTTP
class TokenIn(BaseModel):
    token: str = ""


class ImportIn(BaseModel):
    url: str = ""
    name: str | None = None


def mount(r, current_tenant) -> None:
    """The bridge's routes on the design router (its key check and the design switch already apply)."""

    @r.get("/figma")
    async def figma_status(tenant: str = Depends(current_tenant)):
        return await _bg(token_status, tenant)

    @r.put("/figma")
    async def figma_save(body: TokenIn, tenant: str = Depends(current_tenant)):
        try:
            return await _bg(save_token, tenant, body.token)
        except FigmaError as e:
            raise HTTPException(e.status, str(e)) from None

    @r.delete("/figma")
    async def figma_forget(tenant: str = Depends(current_tenant)):
        return await _bg(forget_token, tenant)

    @r.post("/import/figma")
    async def figma_import(body: ImportIn, tenant: str = Depends(current_tenant)):
        try:
            return {"job": await start(tenant, body.url, body.name or "")}
        except FigmaError as e:
            raise HTTPException(e.status, str(e)) from None

    @r.get("/import/{job_id}")
    async def figma_job(job_id: str, tenant: str = Depends(current_tenant)):
        got = job(tenant, job_id)
        if got is None:
            raise HTTPException(404, "No such import (an import is remembered for a day, and not across a server restart).")
        return got
