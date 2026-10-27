"""HTTP routes for Hoola Postgres (Profile > Postgres database in the app).

GET    /api/pgdb                         her databases + recent change cards
POST   /api/pgdb/conns                   {name, dsn}  (typed only in the app; test-connected, sealed, never returned)
POST   /api/pgdb/conns/{id}/test
DELETE /api/pgdb/conns/{id}
GET    /api/pgdb/conns/{id}/schema?schema=public    schemas + tables
GET    /api/pgdb/conns/{id}/tables/{table}          describe
POST   /api/pgdb/conns/{id}/query        {sql, limit}   (READ ONLY, same checks as the tool)
GET    /api/pgdb/conns/{id}/health
GET    /api/pgdb/writes
POST   /api/pgdb/writes/{id}/decide      {yes, hash}    (her tap = the only way a change runs)"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException


def make_router(require_key, current_tenant) -> APIRouter:
    from . import service as S

    r = APIRouter()

    async def call(fn, *a, **kw):
        try:
            return await asyncio.to_thread(fn, *a, **kw)
        except S.PgError as e:
            raise HTTPException(400, str(e))

    def _b(body: Any) -> dict:
        return body if isinstance(body, dict) else {}

    @r.get("/api/pgdb", dependencies=[Depends(require_key)])
    async def home(tenant: str = Depends(current_tenant)):
        return {"databases": await call(S.conns, tenant), "writes": await call(S.writes, tenant),
                "rules": ["Padhna READ ONLY transaction mein, timeout ke saath",
                          "Har badlav ek card: aapki Haan ke baad hi, ek transaction mein",
                          "Connection string sirf yahan app mein; Hoola ise kabhi nahi dikhata",
                          "Sirf public host + SSL"]}

    @r.post("/api/pgdb/conns", dependencies=[Depends(require_key)])
    async def add(body: Any = Body(...), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await call(S.add, tenant, str(b.get("name") or ""), str(b.get("dsn") or ""))

    @r.post("/api/pgdb/conns/{cid}/test", dependencies=[Depends(require_key)])
    async def test(cid: str, tenant: str = Depends(current_tenant)):
        return await call(S.test, tenant, cid)

    @r.delete("/api/pgdb/conns/{cid}", dependencies=[Depends(require_key)])
    async def remove(cid: str, tenant: str = Depends(current_tenant)):
        return await call(S.remove, tenant, cid)

    @r.get("/api/pgdb/conns/{cid}/schema", dependencies=[Depends(require_key)])
    async def schema(cid: str, schema: str = "public", tenant: str = Depends(current_tenant)):
        sch = await call(S.schemas, tenant, cid)
        tb = await call(S.tables, tenant, cid, schema)
        return {**sch, "tables": tb["tables"], "schema": tb["schema"]}

    @r.get("/api/pgdb/conns/{cid}/tables/{table}", dependencies=[Depends(require_key)])
    async def describe(cid: str, table: str, tenant: str = Depends(current_tenant)):
        return await call(S.describe, tenant, cid, table)

    @r.post("/api/pgdb/conns/{cid}/query", dependencies=[Depends(require_key)])
    async def query(cid: str, body: Any = Body(...), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await call(S.query, tenant, cid, str(b.get("sql") or ""), b.get("limit"))

    @r.get("/api/pgdb/conns/{cid}/health", dependencies=[Depends(require_key)])
    async def health(cid: str, tenant: str = Depends(current_tenant)):
        return await call(S.health, tenant, cid)

    @r.get("/api/pgdb/writes", dependencies=[Depends(require_key)])
    async def writes(status: str = "", tenant: str = Depends(current_tenant)):
        return {"writes": await call(S.writes, tenant, status)}

    @r.post("/api/pgdb/writes/{wid}/decide", dependencies=[Depends(require_key)])
    async def decide(wid: str, body: Any = Body(...), tenant: str = Depends(current_tenant)):
        b = _b(body)
        return await call(S.decide, tenant, wid, bool(b.get("yes")), str(b.get("hash") or ""), by_tap=True)

    return r
