"""HTTP routes of the Patrakar Sahayak (/api/patrakar/*). main.py: app.include_router(make_router(require_key, current_tenant)).

HER taps live ONLY here (by_tap=True): POST /cards/{id}/decide {yes, hash, reason} (publish / right-of-reply letter / pitch /
correction / grievance answer) and POST /sources/{ref}/reveal (a source's identity on her own screen). All routes key-protected."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import Response


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/patrakar", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.PatrakarError as e:
            raise HTTPException(400, str(e))
        except ValueError as e:
            raise HTTPException(400, str(e))

    def _b(body: dict | None) -> dict[str, Any]:
        return dict(body or {})

    def _s(v) -> str:
        return "" if v is None else str(v)

    @r.get("")
    async def overview(tenant: str = Depends(current_tenant)):
        return await run(S.overview, tenant)

    @r.get("/day")
    async def day(tenant: str = Depends(current_tenant)):
        return await run(S.day, tenant)

    @r.get("/settings")
    async def get_settings(tenant: str = Depends(current_tenant)):
        return await run(S.settings, tenant)

    @r.put("/settings")
    async def put_settings(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.save_settings, tenant, "owner", **{k: b[k] for k in S._SET_KEYS if k in b})

    # ---- stories
    @r.get("/stories")
    async def list_stories(status: str = "", tenant: str = Depends(current_tenant)):
        return {"stories": await run(S.stories, tenant, status)}

    @r.post("/stories")
    async def new_story(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.story_new, tenant, _s(b.get("pitch")), _s(b.get("slug")), _s(b.get("beat")), _s(b.get("kind")) or "news",
                         _s(b.get("deadline")), _s(b.get("area")), _s(b.get("notes")), b.get("protect"))

    @r.get("/stories/{ref}")
    async def get_story(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.story_view, tenant, ref)

    @r.patch("/stories/{ref}")
    async def patch_story(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("headline", "dek", "body", "notes", "status", "kind", "slug", "beat", "area", "pitch", "deadline", "embargo",
                "ai_media", "sponsored_label", "protect", "sources", "reply_state")
        return await run(S.story_update, tenant, ref, "owner", **{k: b[k] for k in keys if k in b})

    @r.post("/stories/{ref}/write")
    async def write(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.write, tenant, ref, _s(_b(body).get("ask")))

    @r.post("/stories/{ref}/check")
    async def check(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.check, tenant, ref)

    @r.get("/stories/{ref}/style")
    async def style(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.style_suggest, tenant, ref)

    @r.post("/stories/{ref}/claims/extract")
    async def extract(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.claims_extract, tenant, ref)

    @r.post("/stories/{ref}/claims")
    async def add_claim(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.claim_add, tenant, ref, _s(b.get("text")), _s(b.get("kind")) or "other")

    @r.post("/claims/{cid}/check")
    async def claim_check(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if b.get("url"):
            return await run(S.claim_check, tenant, cid, _s(b.get("url")))
        return await run(S.claim_search, tenant, cid)

    @r.post("/claims/{cid}/mark")
    async def claim_mark(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.claim_mark, tenant, cid, _s(b.get("status")), _s(b.get("note")), _s(b.get("source")), _s(b.get("file_id")))

    @r.post("/stories/{ref}/interviews")
    async def add_interview(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.interview_add, tenant, ref, _s(b.get("file_id")), _s(b.get("transcript")), _s(b.get("who")),
                         _s(b.get("source")), _s(b.get("terms")) or "on_record", bool(b.get("consent")), _s(b.get("lang")))

    @r.post("/interviews/{iid}/quote")
    async def quote(iid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.interview_quote, tenant, iid, _s(_b(body).get("text")))

    @r.get("/interviews/{iid}/suggest")
    async def suggest(iid: str, tenant: str = Depends(current_tenant)):
        return await run(S.suggest_quotes, tenant, iid)

    @r.post("/stories/{ref}/publish")
    async def publish(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.publish_request, tenant, ref, _s(b.get("dest")) or "copy", _s(b.get("mode")) or "draft")

    @r.post("/stories/{ref}/published")
    async def published(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.published_at, tenant, ref, _s(_b(body).get("url")))

    @r.post("/stories/{ref}/pitch")
    async def pitch(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.pitch_request, tenant, ref, _s(b.get("to")), _s(b.get("phone")), _s(b.get("email")), _s(b.get("text")))

    @r.post("/stories/{ref}/reply")
    async def reply(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.reply_request, tenant, ref, _s(b.get("party")), _s(b.get("phone")), _s(b.get("email")),
                         b.get("allegations"), b.get("questions"), b.get("days"))

    @r.post("/replies/{rid}/answer")
    async def reply_answer(rid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.reply_answer, tenant, rid, _s(_b(body).get("response")))

    @r.post("/replies/{rid}/none")
    async def reply_none(rid: str, tenant: str = Depends(current_tenant)):
        return await run(S.reply_none, tenant, rid)

    @r.post("/stories/{ref}/correction")
    async def correction(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.correction_request, tenant, ref, _s(b.get("wrong")), _s(b.get("right")),
                         _s(b.get("kind")) or "correction", _s(b.get("why")))

    @r.get("/corrections")
    async def list_corrections(tenant: str = Depends(current_tenant)):
        return await run(S.corrections, tenant)

    @r.post("/stories/{ref}/files")
    async def files(ref: str, tenant: str = Depends(current_tenant)):
        a = await run(S.story_docx, tenant, ref)
        b = await run(S.fact_sheet_xlsx, tenant, ref)
        return {"files": [a["file"], b["file"]], "say": "Word copy + fact sheet Excel taiyaar."}

    @r.post("/stories/{ref}/forget")
    async def forget(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.story_forget, tenant, ref)

    # ---- sources (identity only on her screen)
    @r.get("/sources")
    async def list_sources(tenant: str = Depends(current_tenant)):
        return {"sources": await run(S.sources, tenant)}

    @r.post("/sources")
    async def add_source(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.source_add, tenant, _s(b.get("name")), _s(b.get("phone")), _s(b.get("contact")), _s(b.get("notes")),
                         _s(b.get("beat")), _s(b.get("kind")) or "other", _s(b.get("terms")) or "background", b.get("reliability"))

    @r.post("/sources/{ref}/said")
    async def source_said(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.source_said, tenant, ref, _s(b.get("text")), bool(b.get("off_record")))

    @r.post("/sources/{ref}/reveal")
    async def reveal(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.source_reveal, tenant, ref, by_tap=True)

    @r.delete("/sources/{ref}")
    async def forget_source(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.source_forget, tenant, ref)

    # ---- grievances
    @r.get("/grievances")
    async def list_gr(tenant: str = Depends(current_tenant)):
        return {"grievances": await run(S.grievances, tenant)}

    @r.post("/grievances")
    async def add_gr(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.grievance_add, tenant, _s(b.get("text")), _s(b.get("who")), _s(b.get("contact")), _s(b.get("story")),
                         _s(b.get("received")))

    @r.post("/grievances/{gid}/answer")
    async def answer_gr(gid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.grievance_answer_request, tenant, gid, _s(_b(body).get("answer")))

    # ---- cards (her tap)
    @r.get("/cards")
    async def list_cards(status: str = "waiting", tenant: str = Depends(current_tenant)):
        return {"cards": await run(S.cards, tenant, status)}

    @r.get("/cards/{cid}")
    async def get_card(cid: str, tenant: str = Depends(current_tenant)):
        return await run(S.card_view, tenant, cid)

    @r.post("/cards/{cid}/decide")
    async def decide(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide, tenant, cid, bool(b.get("yes")), _s(b.get("hash")), _s(b.get("reason")), by_tap=True)

    @r.get("/stories/{ref}/copy.txt")
    async def copy_txt(ref: str, tenant: str = Depends(current_tenant)):
        v = await run(S.story_view, tenant, ref)
        return Response(f"{v['headline']}\n\n{v['dek']}\n\n{v['body']}", media_type="text/plain; charset=utf-8")

    return r
