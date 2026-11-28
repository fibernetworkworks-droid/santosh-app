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


class WorldFillBody(BaseModel):
    values: Optional[dict[str, str]] = None


class PasteBody(BaseModel):
    text: str
    values: Optional[dict[str, str]] = None


class UseBody(BaseModel):
    recipe_id: str
    values: Optional[dict[str, str]] = None


class SaveBody(BaseModel):
    brief: dict[str, Any]
    title: str = ""
    id: str = ""


class AskBody(BaseModel):
    ask: list[str] | None = None
    title: str | None = None


class FillBody(BaseModel):
    values: dict[str, str] = {}


class ScheduleBody(BaseModel):
    repeat: str = "weekly"
    at: str = ""
    conversation_id: str = ""


class CompareBody(BaseModel):
    a: dict[str, Any]
    b: dict[str, Any]
    quality: str = "fast"
    token: str = ""


class PickBody(BaseModel):
    side: str


class LessonBody(BaseModel):
    state: str = "got_it"


class ChangeBody(BaseModel):
    kind: str
    section: str
    slot: str = ""
    recipe: str = ""
    value: str = ""


class UsualBody(BaseModel):
    on: bool = True


class ExportBody(BaseModel):
    brief: dict
    target: str = Field(max_length=20)


class OfferBody(BaseModel):
    saved_id: str = Field(max_length=60)
    title: str = Field(default="", max_length=120)
    makes: str = Field(default="", max_length=200)
    by: str = Field(default="", max_length=60)


class DecideBody(BaseModel):
    reason: str = Field(default="", max_length=300)


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

    # ---- World prompts: the prompts.chat library (CC0), read-only; opening one makes a brief like a recipe
    @r.get("/world")
    async def world_list(q: str = "", group: str = "", page: int = 1, kind: str = ""):
        _on()
        from . import world as W
        return await asyncio.to_thread(W.search, q, group, page, kind)

    @r.get("/world/{wid}")
    async def world_one(wid: str):
        _on()
        from . import world as W
        got = await asyncio.to_thread(W.get, wid)
        if got is None:
            raise HTTPException(404, "No such prompt.")
        return got

    @r.post("/world/{wid}/fill")
    async def world_fill(wid: str, body: WorldFillBody):
        _on()
        from . import world as W
        try:
            return await asyncio.to_thread(W.fill, wid, body.values)
        except ValueError as e:
            raise HTTPException(404, str(e))

    # ---- Paste reader: blanks of every shape in a prompt she pasted; fill = her values in, empty ones left [Name]
    @r.post("/paste")
    async def paste_read(body: PasteBody):
        _on()
        from . import paste as PR
        text = body.text[:6000]
        return {"blanks": PR.blanks(text), "found": len(PR.find(text))}

    @r.post("/paste/fill")
    async def paste_fill(body: PasteBody):
        _on()
        from . import paste as PR
        return PR.fill(body.text[:6000], body.values)

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

    # ---- P7 MERE PROMPT: versions, parts she fills each time, a schedule, a share link
    async def _st(fn, *a):
        from . import store as S
        try:
            return await asyncio.to_thread(fn, *a)
        except KeyError:
            raise HTTPException(404, "No such saved prompt.") from None
        except S.PromptError as e:
            raise HTTPException(400, str(e)) from None

    @r.get("/saved/{pid}/versions")
    async def saved_versions(pid: str, tenant: str = Depends(current_tenant)):
        _on()
        from . import store as S
        return {"versions": await _st(S.versions, tenant, pid)}

    @r.get("/saved/{pid}/versions/{n}")
    async def saved_version(pid: str, n: int, tenant: str = Depends(current_tenant)):
        _on()
        from . import store as S
        return await _st(S.version, tenant, pid, n)

    @r.post("/saved/{pid}/versions/{n}/restore")
    async def saved_restore(pid: str, n: int, tenant: str = Depends(current_tenant)):
        _on()
        from . import store as S
        return await _st(S.restore, tenant, pid, n)

    @r.patch("/saved/{pid}")
    async def saved_patch(pid: str, body: AskBody, tenant: str = Depends(current_tenant)):
        _on()
        from . import store as S
        return await _st(S.set_ask, tenant, pid, body.ask, body.title)

    @r.post("/saved/{pid}/fill")
    async def saved_fill(pid: str, body: FillBody, tenant: str = Depends(current_tenant)):
        """Her values for the parts she fills each time -> the finished prompt for THIS use (the saved one is unchanged)."""
        _on()
        from . import brief as B
        from . import store as S
        got = await asyncio.to_thread(S.get, tenant, pid)
        if got is None:
            raise HTTPException(404, "No such saved prompt.")
        empty = [k for k in got.get("ask") or [] if not str(body.values.get(k) or "").strip()]
        if empty:
            raise HTTPException(422, "Fill in: " + S._labels(got.get("section") or "", empty) + ".")
        try:
            b = B.apply(got.get("brief"), {k: v for k, v in body.values.items() if k in (got.get("ask") or [])})
        except ValueError as e:
            raise HTTPException(422, str(e)) from None
        return _pack(b)

    @r.get("/saved/{pid}/schedule")
    async def saved_schedule_get(pid: str, tenant: str = Depends(current_tenant)):
        _on()
        from . import store as S
        return {"schedule": await _st(S.schedule_of, tenant, pid)}

    @r.put("/saved/{pid}/schedule")
    async def saved_schedule(pid: str, body: ScheduleBody, tenant: str = Depends(current_tenant)):
        _on()
        from . import store as S
        return await _st(S.schedule, tenant, pid, body.repeat, body.at, body.conversation_id)

    @r.delete("/saved/{pid}/schedule")
    async def saved_unschedule(pid: str, tenant: str = Depends(current_tenant)):
        _on()
        from . import store as S
        return await _st(S.unschedule, tenant, pid)

    @r.post("/saved/{pid}/share")
    async def saved_share(pid: str, tenant: str = Depends(current_tenant)):
        _on()
        from . import store as S
        return await _st(S.share, tenant, pid)

    @r.delete("/saved/{pid}/share")
    async def saved_unshare(pid: str, tenant: str = Depends(current_tenant)):
        _on()
        from . import store as S
        return await _st(S.unshare, tenant, pid)

    @r.get("/shared/{token}")
    async def shared_one(token: str, tenant: str = Depends(current_tenant)):
        _on()
        from . import store as S
        try:
            got = await asyncio.to_thread(S.shared, token)
        except KeyError:
            raise HTTPException(404, "This link has expired or was turned off.") from None
        return got

    @r.post("/shared/{token}/copy")
    async def shared_copy(token: str, tenant: str = Depends(current_tenant)):
        _on()
        from . import store as S
        try:
            return await asyncio.to_thread(S.copy_shared, tenant, token)
        except KeyError:
            raise HTTPException(404, "This link has expired or was turned off.") from None
        except S.PromptError as e:
            raise HTTPException(400, str(e)) from None

    # ---- P8 MUQABLA: two prompts side by side - free in code; running both only after the price is shown and confirmed
    def _cmp_err(e: Exception) -> HTTPException:
        return HTTPException(422 if isinstance(e, ValueError) else 400, str(e))

    @r.post("/compare")
    async def compare(body: CompareBody, tenant: str = Depends(current_tenant)):
        _on()
        from . import compare as CM
        try:
            pr = await asyncio.to_thread(CM.pair, body.a, body.b)
        except ValueError as e:
            raise _cmp_err(e) from None
        return pr

    @r.post("/compare/quote")
    async def compare_quote(body: CompareBody, tenant: str = Depends(current_tenant)):
        _on()
        from . import compare as CM
        try:
            return await asyncio.to_thread(CM.quote, body.a, body.b, body.quality)
        except ValueError as e:
            raise _cmp_err(e) from None

    @r.post("/compare/run")
    async def compare_run(body: CompareBody, tenant: str = Depends(current_tenant)):
        """Both sides, only with the token of the quote she saw. Pictures = two Create jobs; scripts = written now."""
        _on()
        from . import compare as CM
        from . import ledger as L
        try:
            pr, q = await asyncio.to_thread(CM.check_token, body.a, body.b, body.quality, body.token)
        except ValueError as e:
            raise _cmp_err(e) from None
        refs, runs, out = {}, {}, {}
        if pr["section"] == "image":
            from ..create import jobs
            for side in CM.SIDES:
                o = pr[side]["out"]
                text = o["prompt"]
                rid = await asyncio.to_thread(L.hand, tenant, text, pr[side]["brief"], "", "", "page", "run")
                try:
                    j = jobs.start(tenant, "image", {"prompt": text, "aspect": (o.get("fields") or {}).get("aspect") or "",
                                                     "quality": q["quality"], "count": 1})
                except jobs.JobError as e:
                    raise HTTPException(400, str(e)) from None
                await asyncio.to_thread(L.claim, tenant, "image", text, j["id"])
                refs[side], runs[side], out[side] = [j["id"]], rid or "", {"job": j}
        else:
            from .. import usage
            from ..create import jobs
            from ..create import service as cs

            async def one(side):
                o = pr[side]["out"]
                f = o.get("fields") or {}
                rid = await asyncio.to_thread(L.hand, tenant, o["prompt"], pr[side]["brief"], "", "", "page", "run")
                with usage.scope(tenant, "create"):
                    text = await cs.write("script", o["prompt"], f.get("fmt", ""), f.get("length", ""),
                                          f.get("language") or "English", f.get("tone", ""))
                it = jobs.keep(tenant, "script", f"Compare {side.upper()} · " + pr[side]["brief"]["intent"][:40], ".txt",
                               text.encode("utf-8"), {"compare": side})
                if L.claim(tenant, "script", o["prompt"], str(it["id"])):
                    L.ready(str(it["id"]), seconds=0)
                return side, rid, it, text
            try:
                got = await asyncio.gather(one("a"), one("b"))
            except cs.CreateError as e:
                raise HTTPException(400, str(e)) from None
            for side, rid, it, text in got:
                refs[side], runs[side], out[side] = [it["id"]], rid or "", {"text": text, "item": it["id"]}
        cid = await asyncio.to_thread(CM.record, tenant, pr, "both", q["total"], refs, runs)
        return {"id": cid, "section": pr["section"], "credits": q["total"], **out}

    @r.post("/compare/judge")
    async def compare_judge(body: CompareBody, tenant: str = Depends(current_tenant)):
        """She judged the two PROMPTS without running them (any kind): kept as shape, so her pick can still teach."""
        _on()
        from . import compare as CM
        try:
            pr = await asyncio.to_thread(CM.pair, body.a, body.b)
        except ValueError as e:
            raise _cmp_err(e) from None
        return {"id": await asyncio.to_thread(CM.record, tenant, pr)}

    @r.post("/compare/{cid}/pick")
    async def compare_pick(cid: str, body: PickBody, tenant: str = Depends(current_tenant)):
        _on()
        from . import compare as CM
        try:
            return await asyncio.to_thread(CM.pick, tenant, cid, body.side)
        except KeyError:
            raise HTTPException(404, "No such comparison.") from None
        except ValueError as e:
            raise _cmp_err(e) from None

    @r.get("/compare/tally")
    async def compare_tally(tenant: str = Depends(current_tenant)):
        _on()
        from . import compare as CM
        return await asyncio.to_thread(CM.tally, tenant)

    # ---- P9 SEEKHO: lessons from her own prompts
    @r.get("/learn")
    async def learn_page(tenant: str = Depends(current_tenant)):
        _on()
        from . import learn as LN
        return await asyncio.to_thread(LN.page, tenant)

    @r.post("/learn/brief")
    async def learn_brief(body: dict, tenant: str = Depends(current_tenant)):
        _on()
        from . import brief as B
        from . import learn as LN
        try:
            b = B.validate(body.get("brief"))
        except ValueError as e:
            raise HTTPException(422, str(e)) from None
        return {"lessons": await asyncio.to_thread(LN.for_brief, tenant, b)}

    @r.put("/learn/{lesson}")
    async def learn_mark(lesson: str, body: LessonBody, tenant: str = Depends(current_tenant)):
        _on()
        from . import learn as LN
        try:
            return await asyncio.to_thread(LN.mark, tenant, lesson, body.state)
        except ValueError as e:
            raise HTTPException(422, str(e)) from None

    # ---- P10 KHUD SEEKHE: changes Hoola proposes to itself (owner taps) + her own usual choices (her taps)
    def _owner(tenant: str) -> None:
        from ..config import get_settings
        if tenant != get_settings().tenant_id:
            raise HTTPException(403, "Only the owner decides how Hoola Prompting changes itself.")

    async def _kh(fn, *a):
        from . import khud as K
        try:
            return await asyncio.to_thread(fn, *a)
        except KeyError:
            raise HTTPException(404, "No such change.") from None
        except K.KhudError as e:
            raise HTTPException(400, str(e)) from None

    @r.get("/khud")
    async def khud_list(tenant: str = Depends(current_tenant)):
        _on()
        _owner(tenant)
        from . import khud as K
        new = await _kh(K.scan)
        return {"new": new, "changes": await _kh(K.listing, ""),
                "rules": {"min_each_side": K.MIN_SIDE, "gain_points": K.MARGIN, "same_points": K.SAME}}

    @r.post("/khud")
    async def khud_propose(body: ChangeBody, tenant: str = Depends(current_tenant)):
        _on()
        _owner(tenant)
        from . import khud as K
        return await _kh(K.propose, body.kind, body.section, body.slot, body.recipe, body.value)

    @r.post("/khud/{cid}/{action}")
    async def khud_decide(cid: str, action: str, tenant: str = Depends(current_tenant)):
        _on()
        _owner(tenant)
        from . import khud as K
        return await _kh(K.decide, cid, action)

    @r.get("/usual")
    async def usual_list(tenant: str = Depends(current_tenant)):
        _on()
        from . import khud as K
        await _kh(K.usual_scan, tenant)
        return {"usual": await _kh(K.usuals, tenant)}

    @r.post("/usual/{uid}")
    async def usual_set(uid: str, body: UsualBody, tenant: str = Depends(current_tenant)):
        _on()
        from . import khud as K
        return await _kh(K.usual_decide, tenant, uid, body.on)

    # ---- P12 PROOF: Hoola's own brief vs her raw line vs a hand-filled brief + ten users before / after (owner only)
    @r.get("/proof")
    async def proof(tenant: str = Depends(current_tenant)):
        _on()
        _owner(tenant)
        from ..quality import promptproof as PP
        card = await asyncio.to_thread(PP.proof)
        return {**card, "lines": PP.lines(card)}

    # ---- P11 BAHAR: a brief written for an AI tool outside Hoola (copy only, nothing sent, nothing counted)
    @r.get("/export/targets")
    async def export_targets(section: str = ""):
        _on()
        from ..config import get_settings
        from . import bahar as X
        if not getattr(get_settings(), "prompting_outside", True):
            return {"targets": [], "note": ""}
        return {"targets": X.targets(section), "note": X.NOTE}

    @r.post("/export")
    async def export(body: ExportBody):
        _on()
        from ..config import get_settings
        from . import bahar as X
        if not getattr(get_settings(), "prompting_outside", True):
            raise HTTPException(404, "Copying for other AI tools is switched off.")
        try:
            return X.export(body.brief, body.target)
        except (ValueError, KeyError) as e:
            raise HTTPException(422, str(e)) from None

    # ---- P11 SAMUDAAY: recipes written by users (off until the owner switches it on; the owner approves each one)
    async def _sm(fn, *a):
        from . import samudaay as SM
        try:
            return await asyncio.to_thread(fn, *a)
        except KeyError:
            raise HTTPException(404, "Not found.") from None
        except SM.CommunityError as e:
            raise HTTPException(400, str(e)) from None

    @r.get("/community")
    async def community_mine(tenant: str = Depends(current_tenant)):
        _on()
        from . import samudaay as SM
        owner = False
        try:
            _owner(tenant)
            owner = True
        except HTTPException:
            pass
        return {"on": SM.on(), "mine": await _sm(SM.mine, tenant), "owner": owner,
                "review": (await _sm(SM.review_list)) if owner else [],
                "note": "Writers see how often results from their recipe were kept. Hoola pays nobody for recipes yet."}

    @r.post("/community")
    async def community_offer(body: OfferBody, tenant: str = Depends(current_tenant)):
        _on()
        from . import samudaay as SM
        return await _sm(SM.submit, tenant, body.saved_id, body.title, body.makes, body.by)

    @r.post("/community/{cid}/withdraw")
    async def community_withdraw(cid: str, tenant: str = Depends(current_tenant)):
        _on()
        from . import samudaay as SM
        return await _sm(SM.withdraw, tenant, cid)

    @r.post("/community/{cid}/{action}")
    async def community_decide(cid: str, action: str, body: DecideBody, tenant: str = Depends(current_tenant)):
        _on()
        _owner(tenant)
        from . import samudaay as SM
        return await _sm(SM.decide, cid, action, body.reason)

    @r.delete("/saved/{pid}")
    async def saved_delete(pid: str, tenant: str = Depends(current_tenant)):
        _on()
        from . import store as S
        if not await asyncio.to_thread(S.delete, tenant, pid):
            raise HTTPException(404, "No such saved prompt.")
        return {"ok": True}

    # ---- NATIJA KHATA: the outcome ledger (plan P4). Shape only; her words are never stored.

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
