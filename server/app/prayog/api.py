"""Prayogshala routes. The catalogue is public teaching material (no user data), so it is read without a key - the lab
page and its offline cache need that. Nothing here writes."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

THREE = Path(__file__).resolve().parent.parent / "appmaker" / "assets" / "three.min.js"


def make_router() -> APIRouter:
    from . import service as S

    r = APIRouter()

    @r.get("/api/prayog/labs")
    def list_labs(q: str = "", field: str = "", limit: int = 100):
        return {"labs": S.search(q, field, limit), "note": S.NOTE}

    @r.get("/api/prayog/labs/{lab_id}")
    def get_lab(lab_id: str):
        lab = S.get(lab_id)
        if not lab:
            raise HTTPException(404, "Yeh lab nahi mila")
        return {"lab": lab, "note": S.NOTE}

    @r.get("/api/prayog/three.js")
    def three():
        return FileResponse(THREE, media_type="application/javascript", headers={"Cache-Control": "public, max-age=604800"})

    @r.get("/prayog")
    def home():
        return RedirectResponse("/static/prayog/index.html")

    return r
