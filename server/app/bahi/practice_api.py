"""/api/practice/* - the CA document desk (v0.999.46). Signed-in owner only, except two doors that carry their own proof:
the CA's paired PC uploading a dropped file (its device token) and the Telegram / Slack webhooks (their secrets, in main.py).
No route returns a bot token, a signing secret or a password."""
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response


def make_router(require_key, current_tenant):

    from ..config import get_settings
    from . import practice as P

    r = APIRouter()

    def _err(e: Exception):
        raise HTTPException(400, str(e))

    async def _read(upload: UploadFile) -> bytes:
        data = await upload.read(P.MAX_FILE + 1)
        if len(data) > P.MAX_FILE:
            raise HTTPException(413, f"The file is over {P.MAX_FILE // 1024 // 1024} MB.")
        return data

    def _dl(name: str, data: bytes) -> Response:
        from urllib.parse import quote
        import mimetypes
        return Response(data, media_type=mimetypes.guess_type(name)[0] or "application/octet-stream",
                        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}",
                                 "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})

    @r.get("/api/practice", dependencies=[Depends(require_key)])
    def _home(tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return {"settings": P.settings(tenant), "summary": P.summary(tenant), "kinds": P.KINDS}

    @r.put("/api/practice/settings", dependencies=[Depends(require_key)])
    def _set(body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return P.save_settings(tenant, body or {})

    @r.get("/api/practice/clients", dependencies=[Depends(require_key)])
    def _clients(month: str = "", q: str = "", tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return {"clients": P.clients(tenant, month, q), "month": month or P._month_now()}

    @r.post("/api/practice/clients", dependencies=[Depends(require_key)])
    def _add(body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        try:
            return P.save_client(tenant, body or {})
        except P.PracticeError as e:
            _err(e)

    @r.patch("/api/practice/clients/{cid}", dependencies=[Depends(require_key)])
    def _edit(cid: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        try:
            return P.save_client(tenant, body or {}, cid)
        except P.PracticeError as e:
            _err(e)

    @r.get("/api/practice/clients/{cid}/folder", dependencies=[Depends(require_key)])
    def _folder(cid: str, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        try:
            out = P.folder(tenant, cid)
            out["telegram_link"] = P.telegram_link(tenant, cid)
            return out
        except P.PracticeError as e:
            raise HTTPException(404, str(e))

    @r.get("/api/practice/clients/{cid}/zip", dependencies=[Depends(require_key)])
    def _zip(cid: str, month: str, tenant: str = Depends(current_tenant)):
        try:
            name, data = P.month_zip(tenant, cid, month)
        except P.PracticeError as e:
            raise HTTPException(404, str(e))
        return _dl(name, data)

    @r.get("/api/practice/files/{fid}", dependencies=[Depends(require_key)])
    def _file(fid: str, tenant: str = Depends(current_tenant)):
        try:
            name, data = P.get_file(tenant, fid)
        except P.PracticeError as e:
            raise HTTPException(404, str(e))
        return _dl(name, data)

    @r.post("/api/practice/upload", dependencies=[Depends(require_key)])
    async def _upload(file: UploadFile = File(...), client_id: str = Form(""), channel: str = Form("upload"),
                      tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        import asyncio
        data = await _read(file)
        ch = channel if channel in ("upload", "phone") else "upload"
        rows = await asyncio.to_thread(P.collect, tenant, ch, "", file.filename or "file", data, "", client_id)
        return {"files": rows}      # no client picked = it waits in the inbox (never guessed into a folder)

    @r.get("/api/practice/inbox", dependencies=[Depends(require_key)])
    def _inbox(tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return P.today(tenant)

    @r.post("/api/practice/files/{fid}/file", dependencies=[Depends(require_key)])
    def _file_it(fid: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        b = body or {}
        try:
            return P.file_it(tenant, fid, str(b.get("client_id") or ""), month=str(b.get("month") or ""),
                             kind=str(b.get("kind") or ""), remember_sender=bool(b.get("remember_sender")),
                             new_client=b.get("new_client") if isinstance(b.get("new_client"), dict) else None)
        except P.PracticeError as e:
            _err(e)

    @r.post("/api/practice/files/{fid}/drop", dependencies=[Depends(require_key)])
    def _drop(fid: str, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        try:
            return P.drop(tenant, fid)
        except P.PracticeError as e:
            _err(e)

    @r.get("/api/practice/requests", dependencies=[Depends(require_key)])
    def _reqs(month: str = "", tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        return P.requests_view(tenant, month)

    @r.get("/api/practice/requests/{cid}/draft", dependencies=[Depends(require_key)])
    def _draft(cid: str, month: str = "", tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        try:
            return P.request_draft(tenant, cid, month)
        except P.PracticeError as e:
            raise HTTPException(404, str(e))

    @r.post("/api/practice/requests/{cid}/send", dependencies=[Depends(require_key)])
    async def _send(cid: str, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        b = body or {}
        try:
            return await P.send_request(tenant, cid, str(b.get("channel") or "email"), str(b.get("text") or ""),
                                        str(b.get("month") or ""), str(b.get("subject") or ""))
        except P.PracticeError as e:
            _err(e)

    @r.post("/api/practice/telegram", dependencies=[Depends(require_key)])
    async def _tg(request: Request, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        base = (get_settings().public_base_url or str(request.base_url)).rstrip("/")
        try:
            return await P.telegram_setup(tenant, str((body or {}).get("token") or ""), base)
        except P.PracticeError as e:
            _err(e)

    @r.post("/api/practice/slack", dependencies=[Depends(require_key)])
    def _slack(request: Request, body: dict | None = None, tenant: str = Depends(current_tenant)) -> dict[str, Any]:
        b = body or {}
        try:
            out = P.slack_setup(tenant, str(b.get("bot_token") or ""), str(b.get("signing_secret") or ""))
        except P.PracticeError as e:
            _err(e)
        base = (get_settings().public_base_url or str(request.base_url)).rstrip("/")
        out["events_url"] = base + out.pop("events_url_path")
        return out

    @r.post("/api/practice/pcdrop")
    async def _pcdrop(request: Request, file: UploadFile = File(...), folder: str = Form("")) -> dict[str, Any]:
        """The CA's PC (Hoola Desktop, its own device token) uploads a file dropped in a client's '_Drop here' folder."""
        import asyncio
        from ..pc import service as pcs
        tok = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
        dev = pcs.device_for_token(tok)
        if dev is None:
            raise HTTPException(401, "This PC is not paired.")
        data = await _read(file)
        rows = await asyncio.to_thread(P.collect, dev.tenant_id, "pc", str(folder or "")[:120], file.filename or "file", data)
        return {"files": len(rows)}

    return r
