"""HTTP routes of the Kitab Sahayak (/api/kitab/*). main.py: app.include_router(make_router(require_key, current_tenant)).

HER taps live ONLY here (by_tap=True):
  * POST /chapters/{id}/suggestions/decide {ids, yes, hash} - accept / reject tracked suggestions on the chapter text she sees;
  * POST /cards/{id}/decide {yes, hash, reason} - accept batch / permission letter / pitch / invoice / delivery.
All routes key-protected; no public routes."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/kitab", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except S.KitabError as e:
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
        return await run(S.save_settings, tenant, **{k: b[k] for k in S._SET_KEYS if k in b})

    # ---- books
    @r.get("/books")
    async def list_books(status: str = "", tenant: str = Depends(current_tenant)):
        return {"books": await run(S.books, tenant, status)}

    @r.post("/books")
    async def save_book(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.book_save, tenant, _s(b.get("book")), "owner", "", **{k: b[k] for k in S._BOOK_KEYS if k in b})

    @r.get("/books/{ref}")
    async def get_book(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.book_view, tenant, ref)

    @r.post("/books/{ref}/import")
    async def import_book(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.import_text, tenant, ref, _s(b.get("text")), _s(b.get("file_id")), bool(b.get("replace")))

    @r.post("/books/{ref}/chapters")
    async def new_chapter(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.chapter_save, tenant, "new", _s(b.get("text")), _s(b.get("title")), ref)

    @r.get("/books/{ref}/style")
    async def get_style(ref: str, tenant: str = Depends(current_tenant)):
        v = await run(S.book_view, tenant, ref)
        return {"style": v["style"], **(await run(S.consistency, tenant, ref))}

    @r.put("/books/{ref}/style")
    async def put_style(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.style_save, tenant, ref, b.get("characters"), b.get("places"), b.get("terms"), b.get("spellings"),
                         b.get("conventions"), b.get("notes"), _s(b.get("choose")))

    @r.get("/books/{ref}/permissions")
    async def get_perms(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.permissions, tenant, ref)

    @r.post("/books/{ref}/permissions/scan")
    async def scan_perms(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.permissions_scan, tenant, ref)

    @r.post("/books/{ref}/permissions")
    async def save_perm(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.permission_save, tenant, ref, _s(b.get("permission")), "owner", **{k: b[k] for k in S._PERM_KEYS if k in b})

    @r.post("/books/{ref}/permissions/{pid}/request")
    async def perm_request(ref: str, pid: str, tenant: str = Depends(current_tenant)):
        return await run(S.permission_request, tenant, ref, pid)

    @r.post("/books/{ref}/similarity")
    async def sim(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.similarity_check, tenant, ref, _s(b.get("chapter")), b.get("file_ids") or [], _s(b.get("text")), bool(b.get("web")))

    @r.get("/books/{ref}/checklist")
    async def get_check(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.checklist, tenant, ref)

    @r.post("/books/{ref}/checklist")
    async def set_check(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.checklist_set, tenant, ref, _s(b.get("item")), _s(b.get("status")), _s(b.get("ref")))

    @r.post("/books/{ref}/isbn")
    async def set_isbn(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.isbn_set, tenant, ref, _s(b.get("format")), _s(b.get("isbn")))

    @r.get("/books/{ref}/verso")
    async def get_verso(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.verso, tenant, ref)

    @r.get("/books/{ref}/submissions")
    async def list_subs(ref: str, tenant: str = Depends(current_tenant)):
        return {"submissions": await run(S.submissions, tenant, ref)}

    @r.post("/books/{ref}/submissions")
    async def save_sub(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.submission_save, tenant, ref, _s(b.get("submission")), "owner", **{k: b[k] for k in S._SUB_KEYS if k in b})

    @r.post("/books/{ref}/submissions/{sid}/pitch")
    async def pitch(ref: str, sid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        if any(k in b for k in ("subject", "letter", "synopsis")):
            return await run(S.pitch_edit, tenant, ref, sid, b.get("subject"), b.get("letter"), b.get("synopsis"))
        return await run(S.pitch_request, tenant, ref, sid, int(b.get("sample") or 3))

    @r.get("/books/{ref}/royalties")
    async def get_roy(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.royalties, tenant, ref)

    @r.put("/books/{ref}/contract")
    async def put_contract(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.contract_save, tenant, ref, _s(b.get("publisher")), b.get("rates"), b.get("advance"), b.get("period_months"),
                         b.get("term_years"), _s(b.get("territory")), b.get("formats"), _s(b.get("notes")))

    @r.post("/books/{ref}/statements")
    async def add_stmt(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.statement_add, tenant, ref, _s(b.get("period")), _s(b.get("format")) or "paperback", b.get("units"),
                         b.get("returns"), b.get("price"), b.get("net"), b.get("stated"), b.get("tds"), _s(b.get("period_end")),
                         _s(b.get("source")) or "publisher", b.get("received"), _s(b.get("note")))

    @r.get("/books/{ref}/estimate")
    async def est(ref: str, hours: str = "", tenant: str = Depends(current_tenant)):
        return await run(S.estimate, tenant, ref, hours or None)

    @r.post("/books/{ref}/invoice")
    async def inv(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.invoice_request, tenant, ref, b.get("amount"), b.get("hours"), _s(b.get("note")))

    @r.post("/books/{ref}/deliver")
    async def deliver(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.deliver_request, tenant, ref)

    @r.post("/books/{ref}/export")
    async def exp(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.export, tenant, ref, _s(b.get("what")) or "docx", "", int(b.get("chapters") or 0))

    @r.post("/books/{ref}/forget")
    async def forget(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget, tenant, ref)

    @r.post("/platform")
    async def platform(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.platform_calc, _s(b.get("platform")), b.get("price"), _s(b.get("plan")) or "70", b.get("delivery"),
                         bool(b.get("select")), b.get("print_cost"), b.get("share_pct"))

    # ---- chapters + tracked suggestions
    @r.get("/chapters/{cid}")
    async def get_chapter(cid: str, tenant: str = Depends(current_tenant)):
        return await run(S.chapter_view, tenant, cid)

    @r.put("/chapters/{cid}")
    async def put_chapter(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.chapter_save, tenant, cid, b.get("text"), b.get("title"), "", _s(b.get("status")))

    @r.post("/chapters/{cid}/pass")
    async def run_pass(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.run_pass, tenant, cid, _s(_b(body).get("pass")) or "proof")

    @r.post("/chapters/{cid}/suggestions/decide")
    async def decide_sugs(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        ids = [str(x) for x in (b.get("ids") or [])]
        if not b.get("yes", True):
            return await run(S.reject, tenant, cid, ids, None, bool(b.get("remember")))
        return await run(S.decide_suggestions, tenant, cid, ids, True, _s(b.get("hash")), True)

    @r.post("/chapters/{cid}/restore")
    async def restore(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.restore, tenant, cid, int(_b(body).get("version") or 0))

    @r.post("/chapters/{cid}/translate")
    async def tr(cid: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.translate_chapter, tenant, cid, _s(_b(body).get("to")))

    # ---- cards
    @r.get("/cards")
    async def list_cards(status: str = "waiting", tenant: str = Depends(current_tenant)):
        return {"cards": await run(S.cards, tenant, status)}

    @r.post("/cards/{card_id}/decide")
    async def decide(card_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide, tenant, card_id, bool(b.get("yes")), _s(b.get("hash")), _s(b.get("reason")), True)

    return r
