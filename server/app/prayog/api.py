"""Prayogshala routes. The catalogue is public teaching material (no user data), so it is read without a key - the lab
page and its offline cache need that. Nothing here writes."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse, Response

THREE = Path(__file__).resolve().parent.parent / "appmaker" / "assets" / "three.min.js"
PRAYOG_STATIC = Path(__file__).resolve().parent.parent / "static" / "prayog"


def _kernels_js() -> str:
    """kernels.js plus every pack, as ONE script: new physics is a new file, never an edit to the shared one."""
    parts = [(PRAYOG_STATIC / "kernels.js").read_text(encoding="utf-8")]
    pack_dir = PRAYOG_STATIC / "packs"
    if pack_dir.is_dir():
        for f in sorted(pack_dir.glob("*.js")):
            parts.append(f"\n/* ---- pack: {f.name} ---- */\n" + f.read_text(encoding="utf-8"))
    return "\n".join(parts)


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
    def list_labs(q: str = "", field: str = "", limit: int = 100, level: str = "", chapter: str = "", base: str = "",
                  page: int = 1, variants: bool = True):
        out = S.search_page(q, field, limit, level, chapter, base, page, variants)
        out["note"] = S.NOTE
        return out

    @r.get("/api/prayog/labs/{lab_id}")
    def get_lab(lab_id: str):
        lab = S.get(lab_id)
        if not lab:
            raise HTTPException(404, "Yeh lab nahi mila")
        return {"lab": lab, "note": S.NOTE}

    @r.get("/api/prayog/kernels.js")
    def kernels_js():
        return Response(_kernels_js(), media_type="application/javascript",
                        headers={"Cache-Control": "public, max-age=300"})

    @r.get("/api/prayog/three.js")
    def three():
        return FileResponse(THREE, media_type="application/javascript", headers={"Cache-Control": "public, max-age=604800"})

    @r.get("/prayog")
    def home():
        return RedirectResponse("/static/prayog/index.html")

    return r
