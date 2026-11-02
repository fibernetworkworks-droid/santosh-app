"""Prayogshala routes. The catalogue is public teaching material (no user data), so it is read without a key - the lab
page and its offline cache need that. Nothing here writes."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

THREE = Path(__file__).resolve().parent.parent / "appmaker" / "assets" / "three.min.js"


def make_router(require_key=None, current_tenant=None) -> APIRouter:
    from . import service as S

    r = APIRouter()

    if require_key is not None and current_tenant is not None:
        @r.post("/api/prayog/ask", dependencies=[Depends(require_key)])
        def ask(body: dict = Body(default={}), tenant: str = Depends(current_tenant)):
            """Ask Hoola inside one experiment: answers ONLY about that lab, from its theory + the live state."""
            b = dict(body or {})
            try:
                return S.ask(tenant, str(b.get("lab_id") or ""), str(b.get("question") or ""), b.get("turns") or [], b.get("state") or {})
            except S.AskError as e:
                raise HTTPException(e.status, str(e))

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
