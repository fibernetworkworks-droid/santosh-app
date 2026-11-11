"""HOOLA DESIGN over HTTP: REST under /api/design and the WebSocket /api/design/ws (contract section 2).

Every REST route needs the caller's key (require_key) and works only on the caller's own rows; the two public
doors are the share-link routes, which a token opens read-only. Handlers are async and do every database / disk
step through `bg` (a worker thread), because they also talk to the open room on the event loop.
"""
from __future__ import annotations

import hmac
import math
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from ..config import get_settings
from . import assets, store
from .doc import Doc, dumps, dumps_nodes, new_document
from .room import HUB, bg

_JSON = "application/json"
# An asset is served as an image and nothing else: even opened directly, an SVG can not run or load anything.
_ASSET_HEADERS = {"X-Content-Type-Options": "nosniff", "Cache-Control": "private, max-age=31536000, immutable",
                  "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox"}


class FileIn(BaseModel):
    name: str | None = None
    template: str | None = None


class FilePatch(BaseModel):
    name: str | None = None
    star: bool | None = None


class VersionIn(BaseModel):
    label: str = ""


class CommentIn(BaseModel):
    text: str
    node: str | None = None
    page: str = ""
    x: float = 0.0
    y: float = 0.0
    parent: str | None = None


class CommentPatch(BaseModel):
    text: str | None = None
    resolved: bool | None = None


class ShareIn(BaseModel):
    role: str = "view"


def _on() -> None:
    if not getattr(get_settings(), "design_page", False):
        raise HTTPException(404, "Hoola Design is switched off on this server.")


def _found(value, what: str = "File"):
    if value is None:
        raise HTTPException(404, f"{what} not found")
    return value


def _doc_response(seq: int, doc_json: str, extra: str = "") -> Response:
    """{seq, doc}: the stored JSON goes out as it is, never parsed and re-written."""
    return Response(f'{{"seq":{seq},"doc":{doc_json}{extra}}}', media_type=_JSON)


def _node_count(doc_json: str) -> int:
    return len(Doc.from_json(doc_json))


async def _upload(request: Request, limit: int) -> bytes:
    """The uploaded bytes (a raw body, or the `file` part of a form), never reading more than `limit`."""
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit + 64 * 1024:
        raise HTTPException(413, f"The file is larger than {limit // 1024} KB.")
    if request.headers.get("content-type", "").startswith("multipart/form-data"):
        if not declared.isdigit():
            raise HTTPException(411, "Send the upload with its length.")
        part = (await request.form()).get("file")
        data = await part.read() if hasattr(part, "read") else b""
    else:
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > limit:
                raise HTTPException(413, f"The file is larger than {limit // 1024} KB.")
            chunks.append(chunk)
        data = b"".join(chunks)
    if len(data) > limit:
        raise HTTPException(413, f"The file is larger than {limit // 1024} KB.")
    return data


def _ws_tenant(ws: WebSocket) -> str | None:
    """Who is on this socket - read exactly like /api/voice/ws: the Authorization header, or (a browser can not
    set headers on a WebSocket) the subprotocols "hoola, hoola-key.<token>". Never from the address."""
    from .. import accounts
    st = get_settings()
    got = ws.headers.get("authorization", "").removeprefix("Bearer ").strip()
    if not got:
        protos = [p.strip() for p in ws.headers.get("sec-websocket-protocol", "").split(",")]
        got = next((p[len("hoola-key."):] for p in protos if p.startswith("hoola-key.")), "")
    if st.api_key and got and hmac.compare_digest(got, st.api_key):
        return st.tenant_id
    user = accounts.tenant_for_session(got) if got else None
    if user:
        return accounts.tenant_of_user(user)
    return None if st.api_key else st.tenant_id


def make_router(require_key: Callable, current_tenant: Callable) -> APIRouter:
    r = APIRouter(prefix="/api/design", tags=["design"], dependencies=[Depends(_on), Depends(require_key)])
    pub = APIRouter(prefix="/api/design", tags=["design"])

    # ------------------------------------------------------------------------------------------ files
    @r.get("/files")
    async def files(q: str = "", trash: int = 0, tenant: str = Depends(current_tenant)):
        return {"files": await bg(store.list_files, tenant, q, bool(trash))}

    @r.post("/files")
    async def file_new(body: FileIn | None = None, tenant: str = Depends(current_tenant)):
        body = body or FileIn()
        nodes = new_document(body.template or "")
        return await bg(store.create_file, tenant, body.name or "Untitled", dumps_nodes(nodes), len(nodes))

    @r.get("/files/{file_id}")
    async def file_get(file_id: str, tenant: str = Depends(current_tenant)):
        return _found(await bg(store.get_file, tenant, file_id))

    @r.patch("/files/{file_id}")
    async def file_patch(file_id: str, body: FilePatch, tenant: str = Depends(current_tenant)):
        out = _found(await bg(store.patch_file, tenant, file_id, body.name, body.star))
        if body.name is not None:
            HUB.renamed(file_id, out["name"])
        return out

    @r.delete("/files/{file_id}")
    async def file_delete(file_id: str, forever: int = 0, tenant: str = Depends(current_tenant)):
        if not forever:
            out = _found(await bg(store.set_trashed, tenant, file_id, True))
            HUB.evict(file_id, 4404)
            return {"ok": True, "trashed": True, "file": out}
        state = await bg(store.delete_forever, tenant, file_id)
        if state == "missing":
            raise HTTPException(404, "File not found")
        if state == "not_trashed":
            raise HTTPException(409, "Move the file to the trash first; only a file in the trash is deleted for good.")
        await bg(assets.drop_thumb, tenant, file_id)
        return {"ok": True, "deleted": True}

    @r.post("/files/{file_id}/restore")
    async def file_restore(file_id: str, tenant: str = Depends(current_tenant)):
        out = _found(await bg(store.set_trashed, tenant, file_id, False))
        HUB.restored(file_id)
        return out

    @r.post("/files/{file_id}/duplicate")
    async def file_duplicate(file_id: str, tenant: str = Depends(current_tenant)):
        _, doc_json = _found(await HUB.read(file_id, tenant, True))
        return _found(await bg(store.duplicate_file, tenant, file_id, doc_json, await bg(_node_count, doc_json)))

    @r.get("/files/{file_id}/doc")
    async def file_doc(file_id: str, tenant: str = Depends(current_tenant)):
        return _doc_response(*_found(await HUB.read(file_id, tenant, True)))

    @r.put("/files/{file_id}/thumb")
    async def thumb_put(file_id: str, request: Request, tenant: str = Depends(current_tenant)):
        _found(await bg(store.get_file, tenant, file_id))
        data = await _upload(request, assets.THUMB_MAX)
        try:
            await bg(assets.save_thumb, tenant, file_id, data)
        except assets.BadImage as e:
            raise HTTPException(415, str(e)) from None
        return {"ok": True, "thumb_at": await bg(store.set_thumb, tenant, file_id)}

    @r.get("/files/{file_id}/thumb")
    async def thumb_get(file_id: str, tenant: str = Depends(current_tenant)):
        _found(await bg(store.get_file, tenant, file_id))
        path = assets.thumb_path(tenant, file_id)
        if not await bg(path.is_file):
            raise HTTPException(404, "This file has no thumbnail yet")
        return FileResponse(path, media_type="image/png", headers={"X-Content-Type-Options": "nosniff",
                                                                    "Cache-Control": "private, no-cache"})

    # --------------------------------------------------------------------------------------- versions
    @r.get("/files/{file_id}/versions")
    async def versions(file_id: str, tenant: str = Depends(current_tenant)):
        return {"versions": _found(await bg(store.list_versions, tenant, file_id))}

    @r.post("/files/{file_id}/versions")
    async def version_new(file_id: str, body: VersionIn | None = None, tenant: str = Depends(current_tenant)):
        seq, doc_json = _found(await HUB.read(file_id, tenant))
        count, by = await bg(_node_count, doc_json), await bg(store.who, tenant)
        return _found(await bg(store.add_version, tenant, file_id, (body or VersionIn()).label, doc_json, seq, count, by))

    @r.get("/versions/{version_id}/doc")
    async def version_doc(version_id: str, tenant: str = Depends(current_tenant)):
        v = _found(await bg(store.version_doc, tenant, version_id), "Version")
        return _doc_response(v["seq"], v["doc"])

    @r.post("/versions/{version_id}/restore")
    async def version_restore(version_id: str, tenant: str = Depends(current_tenant)):
        """The file becomes this version. What it was until now is kept as a version first, so a restore can be
        undone; then the room swaps the document and every open editor is told to fetch it again."""
        v = _found(await bg(store.version_doc, tenant, version_id), "Version")
        seq, doc_json = _found(await HUB.read(v["file"], tenant))
        count, by = await bg(_node_count, doc_json), await bg(store.who, tenant)
        kept = _found(await bg(store.add_version, tenant, v["file"], "Before restore", doc_json, seq, count, by))
        try:
            new_seq = await HUB.replace(v["file"], tenant, v["doc"])
        except LookupError:
            raise HTTPException(404, "File not found") from None
        return {"ok": True, "seq": new_seq, "saved": kept}

    # --------------------------------------------------------------------------------------- comments
    @r.get("/files/{file_id}/comments")
    async def comments(file_id: str, tenant: str = Depends(current_tenant)):
        return {"comments": _found(await bg(store.list_comments, tenant, file_id))}

    @r.post("/files/{file_id}/comments")
    async def comment_new(file_id: str, body: CommentIn, tenant: str = Depends(current_tenant)):
        text = body.text.strip()
        if not text or not (math.isfinite(body.x) and math.isfinite(body.y)):
            raise HTTPException(400, "A comment needs some text and a place on the page.")
        by = await bg(store.who, tenant)
        try:
            out = _found(await bg(store.add_comment, tenant, file_id, by, text, body.node, body.page, body.x, body.y,
                                  body.parent))
        except ValueError as e:
            raise HTTPException(400, str(e)) from None
        HUB.tell(file_id, dumps({"t": "comment", "action": "add", "comment": out}))
        return out

    @r.patch("/comments/{comment_id}")
    async def comment_patch(comment_id: str, body: CommentPatch, tenant: str = Depends(current_tenant)):
        text = body.text.strip() if body.text is not None else None
        if text == "":
            raise HTTPException(400, "A comment can not be empty; delete it instead.")
        out = _found(await bg(store.patch_comment, tenant, comment_id, text, body.resolved), "Comment")
        HUB.tell(out["file"], dumps({"t": "comment", "action": "update", "comment": out}))
        return out

    @r.delete("/comments/{comment_id}")
    async def comment_delete(comment_id: str, tenant: str = Depends(current_tenant)):
        gone = _found(await bg(store.delete_comment, tenant, comment_id), "Comment")
        HUB.tell(gone["file"], dumps({"t": "comment", "action": "delete", "comment": gone}))
        return {"ok": True}

    # ----------------------------------------------------------------------------------------- assets
    @r.post("/files/{file_id}/assets")
    async def asset_new(file_id: str, request: Request, tenant: str = Depends(current_tenant)):
        _found(await bg(store.get_file, tenant, file_id))
        data = await _upload(request, assets.ASSET_MAX)
        try:
            return await bg(assets.save_asset, tenant, data)
        except assets.BadImage as e:
            raise HTTPException(415, str(e)) from None

    def _asset(tenant: str, sha: str) -> FileResponse:
        path = _found(assets.asset_path(tenant, sha), "Image")
        return FileResponse(path, media_type=assets.stored_mime(path), headers=_ASSET_HEADERS)

    @r.get("/assets/{sha}")
    async def asset_get(sha: str, tenant: str = Depends(current_tenant)):
        return await bg(_asset, tenant, sha)

    # ------------------------------------------------------------------------------------------ share
    @r.post("/files/{file_id}/share")
    async def share(file_id: str, body: ShareIn | None = None, tenant: str = Depends(current_tenant)):
        role = (body or ShareIn()).role
        if role not in ("view", "none"):
            raise HTTPException(400, 'role is "view" or "none"')
        return _found(await bg(store.set_share, tenant, file_id, role))

    @pub.get("/shared/{token}/doc", dependencies=[Depends(_on)])
    async def shared_doc(token: str):
        """The public, read-only door of a share link."""
        target = _found(await bg(store.share_target, token), "Shared file")
        seq, doc_json = _found(await HUB.read(target["file"], None), "Shared file")
        info = dumps({"id": target["file"], "name": target["name"], "role": "view"})
        return _doc_response(seq, doc_json, f',"file":{info}')

    @pub.get("/shared/{token}/assets/{sha}", dependencies=[Depends(_on)])
    async def shared_asset(token: str, sha: str):
        """The images a shared file draws (the viewer has no key for /assets)."""
        target = _found(await bg(store.share_target, token), "Shared file")
        return await bg(_asset, target["tenant"], sha)

    # --------------------------------------------------------------------------------------------- AI
    # HOOK (phase D5, added by another phase): POST /files/{file_id}/ai {prompt, page, x, y}.
    # It must build ops and hand them to `await HUB.apply_ops(file_id, tenant, ops)` - never write the document
    # itself - with node ids minted under `await HUB.new_cid(file_id)`, so every open editor sees the result.

    # -------------------------------------------------------------------------------------- WebSocket
    @pub.websocket("/ws")
    async def design_ws(ws: WebSocket, file: str = "", share: str = ""):
        """One editor in one file. Signed in = an editor of the caller's own file; `share=<token>` = a view-only
        guest of a shared file (may send presence, its ops are refused). The socket is accepted BEFORE a refusal
        so that a browser can read the close code: 4401 not signed in, 4404 no such file, 4403 view-only writer."""
        protos = [p.strip() for p in ws.headers.get("sec-websocket-protocol", "").split(",")]
        await ws.accept(subprotocol="hoola" if "hoola" in protos else None)
        st = get_settings()
        if not getattr(st, "design_page", False):
            return await ws.close(code=4404)
        if share:
            target = await bg(store.share_target, share)
            if target is None or (file and file != target["file"]):
                return await ws.close(code=4404)
            tenant, file, role, name = target["tenant"], target["file"], "view", "Guest"
        else:
            tenant = await bg(_ws_tenant, ws)
            if tenant is None:
                return await ws.close(code=4401)
            role, name = "edit", await bg(store.who, tenant)
        try:
            room = await HUB.open(file, tenant)
        except LookupError:
            return await ws.close(code=4404)
        conn = None
        try:
            if len(room.conns) >= int(st.design_room_max):
                return await ws.close(code=1013)             # the room is full: the browser tries again later
            conn = await room.admit(ws, role, name)
            await room.serve(conn)
        except LookupError:
            await ws.close(code=4404)
        finally:
            if conn is not None:
                room.remove(conn)
            await HUB.release(room)

    root = APIRouter()
    root.include_router(r)
    root.include_router(pub)
    return root
