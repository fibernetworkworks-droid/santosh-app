"""HOOLA CODER HTTP surface (v0.484.0) - the three memory layers as routes, plus the manual
write path, the admin drain and the SKILL DESK's own surface (the owner's skills platform:
index with usage, park/unpark, import/export, the share ledger, the pack shelf). Loopback-keyed
like every house router (require_key), scoped to the caller's tenant. Read paths never return
another tenant's rows."""
from __future__ import annotations

import inspect

import logging

from fastapi import APIRouter, Request

from . import capture, inject, observer, search, store

log = logging.getLogger("coder.service")


def make_router(require_key, current_tenant) -> APIRouter:
    r = APIRouter(prefix="/api/coder", tags=["coder"])
    _auth = require_key

    async def require_key(request):          # main.require_key is a plain function; tests pass an async one
        out = _auth(request)
        if inspect.isawaitable(out):
            await out

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
        """The desk's index (v0.484): the SKILL.md files with their telemetry (shown / read
        counts, last activity) and the enabled flag. Seeds the starter library once ever."""
        await require_key(request)
        from ..config import get_settings
        if not getattr(get_settings(), "coder_skills", True):
            return {"skills": []}
        tenant = current_tenant(request)
        from . import skill_packs, skills_store
        skill_packs.seed_all(tenant)                 # starters + BYOX + Claude pack, each exactly-once (own stamps)
        counts = store.skill_use_counts(tenant)
        out = []
        for s in skills_store.listing(tenant):
            u = counts.get(s["name"], {})
            out.append({**s, "shown": u.get("shown", 0), "read": u.get("read", 0),
                        "last_shown": u.get("last_shown", ""), "last_read": u.get("last_read", "")})
        return {"skills": out}

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

    @r.post("/skills/enabled")
    async def skills_enabled(request: Request):
        """v0.484 the desk's park/unpark (the ONE enabled writer - the model has no such op).
        {name, enabled: true|false}."""
        await require_key(request)
        from ..config import get_settings
        if not getattr(get_settings(), "coder_skills", True):
            return {"error": "skills are switched off (coder_skills)"}
        body = await request.json()
        from . import skills_store
        try:
            return skills_store.set_enabled(current_tenant(request), str(body.get("name") or ""),
                                            bool(body.get("enabled", True)))
        except skills_store.SkillError as e:
            return {"error": str(e)}

    @r.post("/skills/import")
    async def skills_import(request: Request):
        """v0.484 bring skills in: JSON rows {name, description, body} or raw SKILL.md markdown
        strings (the Claude Code / ClawHub file shape). Create-if-missing, <=25 per call."""
        await require_key(request)
        from ..config import get_settings
        if not getattr(get_settings(), "coder_skills", True):
            return {"error": "skills are switched off (coder_skills)"}
        body = await request.json()
        from . import skill_packs
        return skill_packs.import_skills(current_tenant(request), body.get("items") or [],
                                         full=str(body.get("format") or "") == "claude")

    @r.post("/skills/import-zip")
    async def skills_import_zip(request: Request):
        """v0.494 ONE skill from a .zip sent as the raw request body (SKILL.md + its reference /
        examples / scripts files, the claude.ai upload shape). Stored, never executed."""
        await require_key(request)
        from ..config import get_settings
        if not getattr(get_settings(), "coder_skills", True):
            return {"error": "skills are switched off (coder_skills)"}
        from . import skill_packs
        return skill_packs.import_zip(current_tenant(request), await request.body())

    @r.get("/skills/export-zip")
    async def skills_export_zip(request: Request, name: str = ""):
        """v0.494 one skill as a .zip (the same shape import-zip takes)."""
        await require_key(request)
        from fastapi.responses import Response
        from . import skill_packs
        data = skill_packs.export_zip(current_tenant(request), name)
        if data is None:
            return {"error": "skill not found"}
        return Response(content=data, media_type="application/zip",
                        headers={"Content-Disposition": f'attachment; filename="{name}.zip"'})

    @r.get("/skills/export")
    async def skills_export(request: Request, names: str = ""):
        """v0.484 her library out as JSON rows (the same shape import takes)."""
        await require_key(request)
        from ..config import get_settings
        if not getattr(get_settings(), "coder_skills", True):
            return {"skills": [], "ok": True}
        from . import skill_packs
        want = [n for n in names.split(",") if n.strip()] if names else None
        return skill_packs.export_skills(current_tenant(request), want)

    @r.get("/skills/shares")
    async def skills_shares(request: Request):
        """v0.484 the share ledger: the pending nominations (the curator's proposals, the
        telemetry as evidence) and everything already decided."""
        await require_key(request)
        from ..config import get_settings
        st = get_settings()
        if not getattr(st, "coder_skills", True):
            return {"pending": [], "decided": [], "armed": False}
        tenant = current_tenant(request)
        rows = store.skill_share_rows(tenant)
        return {"armed": bool(getattr(st, "coder_skills_share", True)),
                "pending": [r for r in rows if r["status"] == "pending"],
                "decided": [r for r in rows if r["status"] != "pending"]}

    @r.post("/skills/shares/decide")
    async def skills_share_decide(request: Request):
        """v0.484 THE TAP: {name, approve: true|false}. approve publishes the REDACTED body to
        the anonymous shelf; nothing ever leaves the tenant without this call."""
        await require_key(request)
        body = await request.json()
        from . import skill_packs
        return skill_packs.share_decide(current_tenant(request), str(body.get("name") or ""),
                                        bool(body.get("approve", False)),
                                        str(body.get("note") or ""))

    @r.get("/skills/packs")
    async def skills_packs(request: Request):
        """v0.484 the shelf: every published pack, anonymous by construction."""
        await require_key(request)
        from ..config import get_settings
        if not getattr(get_settings(), "coder_skills", True):
            return {"packs": []}
        from . import skill_packs
        return {"packs": skill_packs.packs()}

    @r.post("/skills/packs/read")
    async def skills_pack_read(request: Request):
        """v0.484 one pack's full body (the shelf read - no telemetry, no tenant law crossed)."""
        await require_key(request)
        body = await request.json()
        from . import skill_packs
        row = skill_packs.pack_read(str(body.get("name") or ""))
        return row or {"error": "pack not found"}

    @r.post("/skills/packs/install")
    async def skills_pack_install(request: Request):
        """v0.484 one shelf pack into the tenant's own library (create-if-missing - hers win)."""
        await require_key(request)
        body = await request.json()
        from . import skill_packs
        return skill_packs.pack_install(current_tenant(request), str(body.get("name") or ""))

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
