"""HOOLA PROMPTING routes (/api/prompting/*). main.py: app.include_router(make_router(require_key, current_tenant)).
Everything here only READS and WRITES TEXT: no route sends, spends, builds or publishes. Running a prompt happens in
the engine's own screen, with that engine's own price card and her tap."""
from __future__ import annotations

import asyncio
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field


class UnderstandBody(BaseModel):
    text: str = Field(..., max_length=4000)
    section: str = ""


class BriefBody(BaseModel):
    brief: dict[str, Any]
    set: Optional[dict[str, Any]] = None
    drop: Optional[list[str]] = None


class UseBody(BaseModel):
    recipe_id: str
    values: Optional[dict[str, str]] = None


class SaveBody(BaseModel):
    brief: dict[str, Any]
    title: str = ""
    id: str = ""


class HandBody(BaseModel):
    text: str = Field(..., max_length=8000)
    brief: Optional[dict[str, Any]] = None
    section: str = ""
    recipe_id: str = ""
    origin: str = "page"
    how: str = "use"
    conversation_id: str = ""


class ThumbBody(BaseModel):
    value: str


class PrefBody(BaseModel):
    share: Optional[bool] = None
    ledger: Optional[bool] = None


class EventBody(BaseModel):
    ref: str = Field(..., max_length=80)
    event: str


def _pack(brief: dict[str, Any]) -> dict[str, Any]:
    from . import brief as B
    from . import dialect as D
    return {"brief": brief, "score": B.score(brief), "out": D.render(brief), "source_labels": B.SOURCE_LABEL}


def make_router(require_key, current_tenant) -> APIRouter:
    r = APIRouter(prefix="/api/prompting", dependencies=[Depends(require_key)])

    def _on() -> None:
        from ..config import get_settings
        if not getattr(get_settings(), "prompting_page", True):
            raise HTTPException(404, "Hoola Prompting is switched off.")

    @r.get("/sections")
    async def sections(tenant: str = Depends(current_tenant)):
        _on()
        from . import anatomy as A
        from . import context as C
        known = await asyncio.to_thread(C.known, tenant)
        return {"sections": A.public(), "known": known["items"]}

    @r.post("/understand")
    async def understand(body: UnderstandBody, tenant: str = Depends(current_tenant)):
        """Her rough line -> the brief Hoola understood + its score + the finished prompt for that engine."""
        _on()
        from ..config import get_settings
        from . import brief as B
        use_model = bool(getattr(get_settings(), "prompting_fill_model", True))
        try:
            b = await asyncio.to_thread(B.understand, tenant, body.text, body.section, use_model)
        except ValueError as e:
            if str(e) == "choose_section":
                return {"choose_section": True}
            raise HTTPException(422, str(e)) from None
        return _pack(b)

    @r.post("/compile")
    async def compile_(body: BriefBody):
        """The brief after her edits (set = her answers, drop = a suggestion she removed). No model call."""
        _on()
        from . import brief as B
        try:
            return _pack(B.apply(body.brief, body.set, body.drop))
        except ValueError as e:
            raise HTTPException(422, str(e)) from None

    @r.get("/recipes")
    async def recipes(section: str = "", q: str = ""):
        _on()
        from . import recipes as R
        return await asyncio.to_thread(R.listing, section, q)

    @r.post("/recipes/use")
    async def recipe_use(body: UseBody):
        _on()
        from . import recipes as R
        try:
            got = await asyncio.to_thread(R.use, body.recipe_id, body.values)
        except (ValueError, KeyError, StopIteration) as e:
            raise HTTPException(404, str(e) or "No such recipe.") from None
        return {"ready": got["ready"]} if "ready" in got else _pack(got["brief"])

    @r.get("/saved")
    async def saved(section: str = "", tenant: str = Depends(current_tenant)):
        _on()
        from . import store as S
        return {"items": await asyncio.to_thread(S.listing, tenant, section)}

    @r.post("/saved")
    async def save(body: SaveBody, tenant: str = Depends(current_tenant)):
        _on()
        from . import brief as B
        from . import dialect as D
        from . import store as S
        try:
            b = B.validate(body.brief)
            return await asyncio.to_thread(S.save, tenant, b, D.render(b)["prompt"], body.title, body.id)
        except ValueError as e:
            raise HTTPException(422, str(e)) from None

    @r.get("/saved/{pid}")
    async def saved_one(pid: str, tenant: str = Depends(current_tenant)):
        _on()
        from . import store as S
        got = await asyncio.to_thread(S.get, tenant, pid)
        if got is None:
            raise HTTPException(404, "No such saved prompt.")
        from . import brief as B
        try:
            return {**got, **_pack(B.validate(got.get("brief")))}
        except ValueError:
            return got

    @r.delete("/saved/{pid}")
    async def saved_delete(pid: str, tenant: str = Depends(current_tenant)):
        _on()
        from . import store as S
        if not await asyncio.to_thread(S.delete, tenant, pid):
            raise HTTPException(404, "No such saved prompt.")
        return {"ok": True}

    # ---- BAHI: the outcome ledger (plan P4). Shape only; her words are never stored.

    @r.post("/runs")
    async def run_hand(body: HandBody, tenant: str = Depends(current_tenant)):
        """She took a prompt out (Use / Open in / Copy). Nothing is written from an incognito chat."""
        _on()
        from . import brief as B
        from . import ledger as L
        from ..fence import is_incognito
        b = None
        if body.brief:
            try:
                b = B.validate(body.brief)
            except ValueError:
                b = None
        secret = bool(body.conversation_id) and await asyncio.to_thread(is_incognito, body.conversation_id)
        rid = await asyncio.to_thread(L.hand, tenant, body.text, b, body.section, body.recipe_id, body.origin,
                                      body.how, secret)
        return {"run": rid}

    @r.post("/runs/event")
    async def run_event(body: EventBody, tenant: str = Depends(current_tenant)):
        """Her own act on a result that only the page sees: downloaded | copied."""
        _on()
        if body.event not in ("downloaded", "copied") or " " in body.ref:
            raise HTTPException(422, "event: downloaded | copied")
        from . import ledger as L
        await asyncio.to_thread(L.event, tenant, body.ref, body.event)
        return {"ok": True}

    @r.post("/runs/{rid}/thumb")
    async def run_thumb(rid: str, body: ThumbBody, tenant: str = Depends(current_tenant)):
        _on()
        from . import ledger as L
        if not await asyncio.to_thread(L.thumb, tenant, rid, body.value):
            raise HTTPException(404, "No such run.")
        return {"ok": True}

    @r.get("/ledger")
    async def ledger(days: int = 90, everyone: bool = False, tenant: str = Depends(current_tenant)):
        """Her four numbers + her recent runs. everyone=1 (the owner only) = all users who share, shapes only."""
        _on()
        from ..config import get_settings
        from . import ledger as L
        days = max(7, min(int(days or 90), 365))
        owner = tenant == get_settings().tenant_id
        if everyone and not owner:
            raise HTTPException(403, "Only the owner can see every user's numbers.")
        nums = await asyncio.to_thread(L.numbers, None if everyone else tenant, days)
        return {"numbers": nums, "recent": [] if everyone else await asyncio.to_thread(L.recent, tenant),
                "prefs": await asyncio.to_thread(L.prefs, tenant), "owner": owner, "everyone": bool(everyone)}

    @r.put("/ledger/prefs")
    async def ledger_prefs(body: PrefBody, tenant: str = Depends(current_tenant)):
        _on()
        from . import ledger as L
        return await asyncio.to_thread(L.set_prefs, tenant, body.share, body.ledger)

    @r.delete("/ledger")
    async def ledger_forget(confirm: str = "", tenant: str = Depends(current_tenant)):
        _on()
        if confirm != "DELETE":
            raise HTTPException(422, "confirm=DELETE")
        from . import ledger as L
        return {"deleted": await asyncio.to_thread(L.forget, tenant)}

    return r
