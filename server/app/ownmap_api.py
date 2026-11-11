"""HTTP routes of her own map (/api/ownmap/*), key-protected, tenant-scoped.
GET /api/ownmap/{id}/geojson is what the Maps JS Data layer loads with map.data.addGeoJson - from OUR server."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile


def make_router(require_key, current_tenant) -> APIRouter:
    from . import ownmap as O

    r = APIRouter(prefix="/api/ownmap", dependencies=[Depends(require_key)])

    async def run(fn, *a, **k):
        try:
            return await asyncio.to_thread(fn, *a, **k)
        except O.OwnMapError as e:
            raise HTTPException(400, str(e))

    @r.get("")
    async def listing(tenant: str = Depends(current_tenant)):
        return {"maps": await run(O.maps, tenant)}

    @r.get("/{map_id}/geojson")
    async def gj(map_id: str, tenant: str = Depends(current_tenant)):
        return await run(O.geojson, tenant, map_id)

    @r.post("/import")
    async def imp(file: UploadFile = File(...), name: str = Form(""), tenant: str = Depends(current_tenant)):
        data = await file.read(O.MAX_FILE + 1)
        if len(data) > O.MAX_FILE:
            raise HTTPException(413, "The file is larger than 5 MB.")
        return await run(O.import_file, tenant, data, file.filename or "", name)

    @r.delete("/{map_id}")
    async def rm(map_id: str, tenant: str = Depends(current_tenant)):
        return await run(O.delete_map, tenant, map_id)

    return r
