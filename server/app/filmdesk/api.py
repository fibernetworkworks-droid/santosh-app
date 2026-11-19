"""HTTP routes of the Film Desk (/api/filmdesk/*). main.py: app.include_router(make_router(require_key, current_tenant)).

HER taps live ONLY here (by_tap=True): POST /cards/{id}/decide {yes, hash, reason} for a message to an outside person and for
marking a film released. Money for AI shots is approved on the STUDIO's own card (/api/studio/approvals/{id}), never here.
All routes key-protected; the app is the owner."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter(prefix="/api/filmdesk", dependencies=[Depends(require_key)])

    def _err(e: Exception):
        raise HTTPException(400, str(e))

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except (S.FilmError, ValueError) as e:
            _err(e)

    async def arun(coro):
        try:
            return await coro
        except (S.FilmError, ValueError) as e:
            _err(e)

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

    # ---- projects
    @r.get("/projects")
    async def list_projects(status: str = "", tenant: str = Depends(current_tenant)):
        return {"projects": await run(S.projects, tenant, status)}

    @r.post("/projects")
    async def new_project(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.project_new, tenant, _s(b.get("title")), _s(b.get("logline")), _s(b.get("format")),
                         _s(b.get("language")), b.get("targets"), _s(b.get("aspect")), b.get("runtime_s"), b.get("budget_inr"),
                         _s(b.get("genre")), _s(b.get("style")), "owner", _s(b.get("conv")))

    @r.get("/projects/{ref}")
    async def get_project(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.project_view, tenant, ref)

    @r.patch("/projects/{ref}")
    async def patch_project(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("title", "logline", "genre", "format", "language", "aspect", "targets", "runtime_s", "budget_inr")
        return await run(S.project_update, tenant, ref, "owner", **{k: b[k] for k in keys if k in b})

    @r.post("/projects/{ref}/script")
    async def write_script(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.script_write, tenant, ref, _s(_b(body).get("notes")), "owner")

    @r.put("/projects/{ref}/script")
    async def set_script(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.script_set, tenant, ref, _s(_b(body).get("text")), "owner")

    @r.post("/projects/{ref}/script/restore")
    async def restore_script(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.script_restore, tenant, ref, int(_b(body).get("n") or 0), "owner")

    @r.post("/projects/{ref}/cast")
    async def set_cast(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.cast_set, tenant, ref, _s(b.get("character")), _s(b.get("person")), _s(b.get("description")), "owner")

    @r.post("/projects/{ref}/shots")
    async def make_shots(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.shots_make, tenant, ref, _s(b.get("scene")), b.get("model", True) is not False, "owner")

    @r.patch("/projects/{ref}/shots/{shot}")
    async def edit_shot(ref: str, shot: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("prompt", "camera", "duration", "characters", "dialogue", "speaker", "caption")
        return await run(S.shot_update, tenant, ref, shot, "owner", **{k: b[k] for k in keys if k in b})

    @r.delete("/projects/{ref}/shots/{shot}")
    async def delete_shot(ref: str, shot: str, tenant: str = Depends(current_tenant)):
        return await run(S.shot_update, tenant, ref, shot, "owner", delete=True)

    @r.post("/projects/{ref}/storyboard")
    async def storyboard(ref: str, tenant: str = Depends(current_tenant)):
        return await arun(S.storyboard_push(tenant, ref, "owner"))

    @r.post("/projects/{ref}/preview")
    async def preview(ref: str, tenant: str = Depends(current_tenant)):
        return await arun(S.preview(tenant, ref, "owner"))

    @r.get("/projects/{ref}/budget")
    async def budget(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.budget, tenant, ref)

    @r.post("/projects/{ref}/spend")
    async def spend(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await arun(S.spend(tenant, ref, _s(b.get("quality")) or "draft", b.get("shot_ids") or None,
                                  int(b.get("variants") or 1), "owner"))

    @r.post("/projects/{ref}/assemble")
    async def assemble(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await arun(S.assemble(tenant, ref, _b(body).get("captions", True) is not False, "owner"))

    @r.get("/projects/{ref}/release")
    async def release(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.release_view, tenant, ref)

    @r.post("/projects/{ref}/tick")
    async def tick_item(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.tick_item, tenant, ref, _s(b.get("key")), b.get("done", True) is not False, "owner")

    @r.put("/projects/{ref}/rating")
    async def rating(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.set_rating, tenant, ref, _s(b.get("rating")), _s(b.get("descriptors")), "owner")

    @r.put("/projects/{ref}/cbfc")
    async def cbfc(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.set_cbfc, tenant, ref, _s(b.get("category")), _s(b.get("number")), _s(b.get("date")),
                         b.get("applied"), "owner")

    @r.post("/projects/{ref}/release-request")
    async def release_request(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.release_request, tenant, ref, b.get("force") or None, _s(b.get("reason")), "owner")

    @r.post("/projects/{ref}/message")
    async def message(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.message_request, tenant, ref, _s(b.get("msg_kind")) or "custom", _s(b.get("person")), _s(b.get("text")),
                         _s(b.get("phone")), _s(b.get("email")), b.get("uses"), _s(b.get("terms")), _s(b.get("item")),
                         _s(b.get("to_name")), "owner")

    @r.get("/projects/{ref}/rights")
    async def list_rights(ref: str, tenant: str = Depends(current_tenant)):
        return {"rights": await run(S.rights, tenant, ref)}

    @r.post("/projects/{ref}/rights")
    async def add_right(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.right_add, tenant, ref, _s(b.get("kind")), _s(b.get("title")), _s(b.get("owner")), _s(b.get("licence")),
                         bool(b.get("sync")), b.get("platforms"), _s(b.get("territory")), _s(b.get("until")), b.get("fee_inr"),
                         _s(b.get("isrc")), _s(b.get("file_id")), _s(b.get("notes")), "owner")

    # ---- consent register
    @r.get("/people")
    async def list_people(tenant: str = Depends(current_tenant)):
        return {"people": await run(S.people, tenant)}

    @r.post("/people")
    async def add_person(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.person_add, tenant, _s(b.get("name")), _s(b.get("role")) or "actor", _s(b.get("phone")),
                         _s(b.get("email")), b.get("real", True) is not False, bool(b.get("public_figure")), bool(b.get("minor")),
                         b.get("photo_files") or [], _s(b.get("notes")), "owner")

    @r.get("/people/{ref}")
    async def get_person(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.person_view, tenant, ref)

    @r.post("/people/{ref}/consent")
    async def consent(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.consent_record, tenant, ref, _s(b.get("how")), _s(b.get("file_id")), b.get("uses"), _s(b.get("until")),
                         b.get("projects"), _s(b.get("guardian")), "owner")

    @r.post("/people/{ref}/consent/upload")
    async def consent_upload(ref: str, file: UploadFile = File(...), how: str = Form(""), uses: str = Form(""),
                             until: str = Form(""), guardian: str = Form(""), tenant: str = Depends(current_tenant)):
        data = await file.read()
        if not data or len(data) > 60 * 1024 * 1024:
            raise HTTPException(400, "The file is empty or larger than 60 MB.")
        from ..mailbox.service import store_bytes
        f = await asyncio.to_thread(store_bytes, tenant, file.filename or "consent", data, "to_phone")
        return await run(S.consent_record, tenant, ref, how, f.id, uses, until, None, guardian, "owner")

    @r.post("/people/{ref}/withdraw")
    async def withdraw(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        return await run(S.consent_withdraw, tenant, ref, _s(_b(body).get("note")), "owner")

    @r.delete("/people/{ref}")
    async def forget(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.forget_person, tenant, ref, "owner")

    # ---- cards (her tap)
    @r.get("/cards")
    async def list_cards(status: str = "waiting", tenant: str = Depends(current_tenant)):
        return {"cards": await run(S.cards, tenant, status)}

    @r.post("/cards/{card_id}/decide")
    async def decide(card_id: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.decide, tenant, card_id, bool(b.get("yes")), _s(b.get("hash")), _s(b.get("reason")), True)

    # ---- producer layers (production / sales / delivery / coverage / previs / royalty): one view and one op route each
    def _only(b: dict, keys) -> dict:
        return {k: b[k] for k in keys if k in b}

    @r.get("/projects/{ref}/coverage")
    async def coverage(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.coverage_view, tenant, ref)

    @r.get("/projects/{ref}/previs")
    async def previs(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.previs_view, tenant, ref)

    @r.get("/projects/{ref}/schedule")
    async def schedule_get(ref: str, what: str = "schedule", day: int | None = None, tenant: str = Depends(current_tenant)):
        if what not in ("schedule", "dood", "plan_budget", "callsheet"):
            raise HTTPException(400, "what: schedule | dood | plan_budget | callsheet")
        return await run(S.plan_view, tenant, ref, what, day)

    @r.post("/projects/{ref}/schedule")
    async def schedule_make(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("start_date", "day_hours", "setup_hours", "hours_per_screen_minute", "days_off", "blocked_dates", "unavailable",
                "call_time")
        return await run(S.plan_schedule, tenant, ref, "owner", **_only(b, keys))

    @r.post("/projects/{ref}/callsheet")
    async def callsheet_make(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(lambda: S.plan_callsheet(tenant, ref, b.get("day"), "owner", "",
                                                  **_only(b, ("call_time", "cast_calls", "location_address", "contacts", "notes"))))

    @r.post("/projects/{ref}/budget-plan")
    async def budget_plan(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.plan_budget, tenant, ref, b.get("rates"), b.get("contingency_pct"), "owner")

    @r.get("/projects/{ref}/festivals")
    async def festivals(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.festival_view, tenant, ref)

    @r.post("/projects/{ref}/festivals")
    async def festival_do(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("entry", "name", "country", "category", "deadline", "event_date", "fee_inr", "requires", "status", "submitted_on",
                "screened_on", "notes", "key", "done")
        return await run(S.festival_op, tenant, ref, _s(b.get("op")) or "add", "owner", **_only(b, keys))

    @r.get("/projects/{ref}/windows")
    async def windows(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.windows_view, tenant, ref)

    @r.post("/projects/{ref}/windows")
    async def window_do(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("entry", "medium", "territory", "start", "end", "exclusive", "licensee", "fee_inr", "notes", "holdbacks")
        return await run(S.window_op, tenant, ref, _s(b.get("op")) or "add", "owner", **_only(b, keys))

    @r.get("/projects/{ref}/waterfall")
    async def waterfall_get(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.waterfall_view, tenant, ref)

    @r.post("/projects/{ref}/waterfall")
    async def waterfall_do(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.waterfall_run, tenant, ref, b.get("gross_inr"), b.get("deductions"), b.get("investors"), b.get("shares"),
                         "owner")

    @r.get("/projects/{ref}/deliverables")
    async def deliverables(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.deliverables_view, tenant, ref)

    @r.post("/projects/{ref}/deliverables")
    async def deliverable_do(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await run(S.deliverable_op, tenant, ref, _s(b.get("op")) or "add", "owner",
                         **_only(b, ("entry", "label", "buyer", "due", "status", "notes", "kind")))

    @r.get("/projects/{ref}/localisation")
    async def localisation(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.localisation_view, tenant, ref)

    @r.post("/projects/{ref}/localisation")
    async def localise_do(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("entry", "language", "kind", "dub_mode", "voice_person", "vendor", "due", "status", "qa_rounds", "notes")
        return await run(S.localise_op, tenant, ref, _s(b.get("op")) or "add", "owner", **_only(b, keys))

    @r.get("/projects/{ref}/royalties")
    async def royalties(ref: str, tenant: str = Depends(current_tenant)):
        return await run(S.royalties_view, tenant, ref)

    @r.post("/projects/{ref}/royalties")
    async def royalty_do(ref: str, body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
        b = _b(body)
        keys = ("entry", "party", "role", "guild", "basis", "rate", "threshold_inr", "cap_inr", "floor_inr", "applies_to", "start",
                "end", "source", "notes", "medium", "amount_inr", "net_inr", "units", "period", "payer")
        return await run(S.royalty_op, tenant, ref, _s(b.get("op")) or "add", "owner", **_only(b, keys))

    return r
