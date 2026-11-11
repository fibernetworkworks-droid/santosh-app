"""HOOLA CINEMA routes (/api/cinema/*). Behind `cinema_page` (off = every route 404s). Starting anything that spends
video-engine credits needs confirm=true in the body: the Create button on the page IS her tap.

  GET    /api/cinema                        tools, models, presets, her characters, her jobs (running ones refreshed),
                                            credits left, today's count, what is not connected
  POST   /api/cinema/start                  one video job (motion / swap / edit / restyle / talk / lipsync / animate)
  POST   /api/cinema/still/prompt           her words + camera, lens, focal length, aperture -> the picture prompt
  POST   /api/cinema/factory/scenes         one brief -> up to six different scenes (nothing is spent)
  POST   /api/cinema/factory/start          the batch she edited and confirmed
  POST   /api/cinema/jobs/{id}/check        read one job back; a finished video is copied once to My creations
  DELETE /api/cinema/jobs/{id}              take a job off the list (a saved video stays in My creations)
  POST   /api/cinema/characters             save a character (a real person only with the recorded yes)
  DELETE /api/cinema/characters/{id}
  GET    /api/cinema/characters/{id}/photo/{n}
"""
from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import service as S
from . import specs


class StartIn(BaseModel):
    tool: str = Field(max_length=16)
    model: str = Field(default="", max_length=64)
    prompt: str = Field(default="", max_length=5000)
    look: str = Field(default="", max_length=24)
    camera: str = Field(default="", max_length=24)
    images: list[str] = Field(default_factory=list, max_length=5)
    video: str = Field(default="", max_length=120)
    audio: str = Field(default="", max_length=120)
    text: str = Field(default="", max_length=5000)
    voice: str = Field(default="", max_length=40)
    language: str = Field(default="Hindi", max_length=30)
    style: str = Field(default="friendly", max_length=20)
    character: str = Field(default="", max_length=20)
    resolution: str = Field(default="", max_length=8)
    aspect: str = Field(default="", max_length=8)
    seconds: int | None = Field(default=None, ge=1, le=60)
    avoid: str = Field(default="", max_length=500)
    sound: bool | None = None
    extras: dict[str, str] = Field(default_factory=dict)
    consent: bool = False
    rights: bool = False
    confirm: bool = False


class StillIn(BaseModel):
    prompt: str = Field(default="", max_length=3000)
    camera: str = Field(default="", max_length=24)
    lens: str = Field(default="", max_length=24)
    focal: str = Field(default="", max_length=8)
    aperture: str = Field(default="", max_length=8)
    light: str = Field(default="", max_length=16)


class ScenesIn(BaseModel):
    topic: str = Field(default="", max_length=600)
    count: int = Field(default=3, ge=1, le=6)
    look: str = Field(default="", max_length=24)
    camera: str = Field(default="", max_length=24)
    platform: str = Field(default="", max_length=40)


class BatchIn(BaseModel):
    model: str = Field(default="", max_length=64)
    scenes: list[str] = Field(default_factory=list, max_length=6)
    resolution: str = Field(default="", max_length=8)
    aspect: str = Field(default="", max_length=8)
    seconds: int | None = Field(default=None, ge=1, le=60)
    sound: bool | None = None
    confirm: bool = False


class CharacterIn(BaseModel):
    name: str = Field(default="", max_length=60)
    kind: str = Field(default="", max_length=10)
    photos: list[str] = Field(default_factory=list, max_length=6)
    consent: bool = False
    note: str = Field(default="", max_length=200)


def _on() -> None:
    if not S.enabled():
        raise HTTPException(404, "Hoola Cinema is switched off on this server (CINEMA_PAGE).")


async def _run(coro: Any) -> Any:
    try:
        return await coro
    except S.CinemaError as e:
        raise HTTPException(e.status, str(e)) from None


def _do(fn: Callable, *a: Any, **k: Any) -> Any:
    try:
        return fn(*a, **k)
    except S.CinemaError as e:
        raise HTTPException(e.status, str(e)) from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from None


def make_router(require_key: Callable, current_tenant: Callable) -> APIRouter:
    r = APIRouter(prefix="/api/cinema", tags=["cinema"], dependencies=[Depends(require_key), Depends(_on)])

    @r.get("")
    async def cinema_overview(tenant: str = Depends(current_tenant)):
        return await _run(S.overview(tenant))

    @r.post("/start")
    async def cinema_start(body: StartIn, tenant: str = Depends(current_tenant)):
        return await _run(S.start(tenant, body.model_dump()))

    @r.post("/still/prompt")
    def cinema_still(body: StillIn):
        return {"prompt": _do(specs.still_prompt, body.prompt, body.camera, body.lens, body.focal, body.aperture, body.light)}

    @r.post("/factory/scenes")
    async def cinema_scenes(body: ScenesIn):
        return await _run(S.factory_scenes(body.topic, body.count, body.look, body.camera, body.platform))

    @r.post("/factory/start")
    async def cinema_batch(body: BatchIn, tenant: str = Depends(current_tenant)):
        return await _run(S.factory_start(tenant, body.model_dump()))

    @r.post("/jobs/{jid}/check")
    async def cinema_check(jid: str, tenant: str = Depends(current_tenant)):
        return S._public(await _run(S.check(tenant, jid)))

    @r.delete("/jobs/{jid}")
    def cinema_remove(jid: str, tenant: str = Depends(current_tenant)):
        return _do(S.remove, tenant, jid)

    @r.post("/characters")
    def cinema_character(body: CharacterIn, tenant: str = Depends(current_tenant)):
        c = _do(S.character_add, tenant, body.name, body.kind, body.photos, body.consent, body.note)
        return {k: c.get(k) for k in ("id", "name", "kind", "note", "created")} | {"photos": len(c["photos"])}

    @r.delete("/characters/{cid}")
    def cinema_character_remove(cid: str, tenant: str = Depends(current_tenant)):
        return _do(S.character_remove, tenant, cid)

    @r.get("/characters/{cid}/photo/{n}")
    def cinema_character_photo(cid: str, n: int, tenant: str = Depends(current_tenant)):
        return FileResponse(_do(S.character_photo, tenant, cid, n), media_type="image/jpeg",
                            headers={"Cache-Control": "private, max-age=3600"})

    return r
