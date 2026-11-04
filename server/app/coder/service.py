"""HOOLA CODER HTTP surface (v0.480.0) - the three memory layers as routes, plus the manual
write path and the admin drain. Loopback-keyed like every house router (require_key), scoped to
the caller's tenant. Read paths never return another tenant's rows."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from . import capture, inject, observer, search, store

log = logging.getLogger("coder.service")


def make_router(require_key, current_tenant) -> APIRouter:
    r = APIRouter(prefix="/api/coder", tags=["coder"])

    @r.get("/context")
    async def context(request: Request, conv: str = "", compact: bool = False):
        await require_key(request)
        return {"block": inject.primer(current_tenant(request), conv or None, compact=compact)}

    @r.get("/search")
    async def search_route(request: Request, query: str, limit: int = 20, obs_type: str = "",
                           date_start: str = "", date_end: str = ""):
        await require_key(request)
        res = search.search(current_tenant(request), query, limit=limit,
                            obs_type=obs_type or None, date_start=date_start or None,
                            date_end=date_end or None)
        return {**res, "text": search.render_index(res)}

    @r.get("/timeline")
    async def timeline_route(request: Request, anchor: str = "", depth_before: int = 5,
                             depth_after: int = 5):
        await require_key(request)
        t = search.timeline(current_tenant(request), anchor or None, depth_before, depth_after)
        return {**t, "text": search.render_timeline(t)}

    @r.post("/observations/batch")
    async def observations_batch(request: Request):
        await require_key(request)
        body = await request.json()
        ids = [i for i in (body.get("ids") or []) if str(i).isdigit()][:100]
        return {"observations": search.get_observations(ids)}

    @r.post("/tool-uses/batch")
    async def tool_uses_batch(request: Request):
        await require_key(request)
        body = await request.json()
        ids = [i for i in (body.get("ids") or []) if str(i).isdigit()][:100]
        return {"tool_uses": store.tool_uses_by_ids(ids)}

    @r.get("/work-state")
    async def work_state_get(request: Request, list: str = "", include_closed: bool = False):
        await require_key(request)
        return store.work_read(list or None, include_closed)

    @r.post("/work-state")
    async def work_state_post(request: Request):
        await require_key(request)
        body = await request.json()
        lst = str(body.get("list") or "default")
        items = body.get("items") or []
        if not isinstance(items, list):
            return {"error": "items must be a list"}
        store.work_write(lst, items)
        return {"ok": True, "list": lst}

    @r.post("/memory")
    async def memory(request: Request):
        """The manual save_memory: the agent (or she) writes a durable note directly."""
        await require_key(request)
        body = await request.json()
        text = str(body.get("text") or "")
        title = body.get("title")
        conv = str(body.get("conv") or "")
        oid = capture.save_memory(current_tenant(request), conv, text,
                                  str(title) if title else None)
        return {"id": oid}

    @r.get("/skills")
    async def skills_list(request: Request):
        """The skill index (v0.474): the vault rows behind the SKILL.md files."""
        await require_key(request)
        from ..config import get_settings
        if not getattr(get_settings(), "coder_skills", True):
            return {"skills": []}
        from . import skills_store
        return {"skills": skills_store.listing(current_tenant(request))}

    @r.post("/skills")
    async def skills_apply(request: Request):
        """The same operations the skill_manage tool takes (read/list/create/update/delete),
        applied atomically for the owner's console / the nudge's tests."""
        await require_key(request)
        from ..config import get_settings
        if not getattr(get_settings(), "coder_skills", True):
            return {"error": "skills are switched off (coder_skills)"}
        body = await request.json()
        from . import skills_store
        return skills_store.apply(current_tenant(request), body.get("operations") or [])

    @r.get("/stats")
    async def stats_route(request: Request):
        await require_key(request)
        return store.stats()

    @r.get("/dreams")
    async def dreams_route(request: Request):
        """v0.484 SAPNE: the tenant's dreams digest - everything the nightly curator did, in the
        open (the file's previous version sits beside it as dreams.md.pre, the undo line)."""
        await require_key(request)
        from . import dreams
        from ..config import get_settings
        st = get_settings()
        if not getattr(st, "coder_dreams", False):
            return {"digest": "", "note": "dreams are switched off (coder_dreams)", "stats": dreams.stats()}
        return {"digest": dreams.read_digest(current_tenant(request)),
                "state": {k: store.dreams_state_get(current_tenant(request), k)
                          for k in ("light", "deep")},
                "stats": dreams.stats()}

    @r.get("/curator")
    async def curator_route(request: Request):
        """The curator's ledger (v0.480): its own stats, the vault's pending pile, whether a run is due."""
        await require_key(request)
        from . import curator
        from ..config import get_settings
        st = get_settings()
        return {"armed": curator.armed(), "due": curator.due(),
                "every_hours": curator._every_hours(), "stats": curator.stats(),
                "vault": store.curator_counts(),
                "config": {"coder_enabled": getattr(st, "coder_enabled", True),
                           "coder_curator": getattr(st, "coder_curator", False),
                           "coder_skills": getattr(st, "coder_skills", True)}}

    @r.post("/curator/run")
    async def curator_run(request: Request):
        """Admin: run one consolidation now, due-gate bypassed (also the test entry). The kill
        switch stays absolute - a switched-off curator cannot be invoked through this route."""
        await require_key(request)
        from . import curator
        from ..config import get_settings
        if not curator.armed():
            return {"ran": False, "error": "curator is switched off (coder_curator)"}
        return await curator.tick(get_settings(), force=True)

    @r.post("/drain")
    async def drain(request: Request):
        """Admin: run one observer pass now (also the test entry)."""
        await require_key(request)
        from ..config import get_settings
        stats = await observer.tick(get_settings(), max_sessions=10)
        return {"ok": True, **stats}

    return r
