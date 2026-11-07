"""HOOLA FRAMES tool: the avatar composes and renders a real MP4 from chat (v0.471).

One multi-action tool, the rea_khoj shape: action=render|check|timeline|snapshot|add|status.
The model authors the HTML composition (contract: app/studio/frames_contract.md, carried in
a SYSTEM bullet); the worker (app/studio/frames.py) is the only thing that runs it. Assets
come from files she already has — the SAME owner-checked intake as every other tool
(file_id from the phone / email attachment / Drive); the worker copies them into the
project, never re-uploads anything, never fetches the web mid-render.

A render is minutes of CPU at the lowest priority, one at a time on the whole box — so on
a VOICE CALL it goes through santosh_kaam exactly like rea_khoj: the call hears "video ban
rahi hai", the full brain's goal turn runs it, the MP4 lands as a file card she taps.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from ..studio import frames
from .tools import Ctx, ToolError

FRAMES_TOOLS = [
    {"name": "hoola_frames", "description": (
        "Make a REAL MP4 video from chat: you write the HTML composition (timing in data "
        "attributes, one paused GSAP timeline on window.__timelines), the server checks it and "
        "renders it deterministically with the HyperFrames engine. Use when she asks for a "
        "video: 'is product ka video banao', 'ek chhota promo film', 'yeh script ka video', "
        "reels, launch films, explainers, kinetic captions. Actions: render (html -> MP4 file "
        "card in chat), check (the quality gate before rendering - run it first on any new "
        "composition and fix every error), timeline (what plays when), snapshot (a few PNG "
        "stills to look at before rendering), add (install a ready-made registry block like a "
        "transition / caption style / chart into the project), avatar_film (NO HTML needed: "
        "send a spec - shape talking_head|product|reel + script - and the server speaks it "
        "with the Model Lab voice, times every word, builds and renders the film; use this "
        "whenever she wants a video where someone TALKS), status (is FRAMES installed here, "
        "is the render queue free, is the voice lab up). The render contract's 12 rules are "
        "in the SYSTEM guidance - follow them or check fails. Assets: files she already has "
        "by file_id (logo, product photo, voice audio), delivered into assets/. Video length "
        "is the root's data-duration; default 1920x1080 at 30 fps, 1080x1920 for reels. One "
        "render at a time on the whole server - if the queue is busy, say so and retry "
        "shortly. Never render content she has no right to use (other people's private "
        "photos, IDs); say no plainly."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["render", "check", "timeline", "snapshot", "add", "status", "avatar_film"]},
         "html": {"type": "string", "description": "the full index.html composition (required for render/check/timeline/snapshot)"},
         "spec": {"type": "object", "description": ("for action=avatar_film: {shape: talking_head|product|reel, script (one short "
                "line per beat, the voice speaks it), title, brand {name, color #RRGGBB}, items "
                "[{name, price, note, file_id photo}] for product, cta {text, file_id image e.g. "
                "UPI QR}, avatar_file_id (her photo; optional - else an illustrated disc), lang hi|en, "
                "voice chatterbox, aspect 16:9|9:16|1:1 (reel is always 9:16), silent true = no "
                "voice}. Use REAL data only - never invent a price."), "properties": {
             "shape": {"type": "string", "enum": ["talking_head", "product", "reel"]},
             "script": {"type": "string"}, "title": {"type": "string"},
             "brand": {"type": "object", "properties": {"name": {"type": "string"}, "color": {"type": "string"}}},
             "items": {"type": "array", "items": {"type": "object", "properties": {
                 "name": {"type": "string"}, "price": {"type": "string"}, "note": {"type": "string"},
                 "file_id": {"type": "string"}}}},
             "cta": {"type": "object", "properties": {"text": {"type": "string"}, "file_id": {"type": "string"}}},
             "avatar_file_id": {"type": "string"}, "lang": {"type": "string"},
             "voice": {"type": "string"}, "aspect": {"type": "string"}, "silent": {"type": "boolean"}}},
         "files": {"type": "array", "description": "project files: assets and sub-compositions", "items": {
             "type": "object", "properties": {
                 "name": {"type": "string", "description": "project-relative: assets/... or compositions/... (index.html is the html argument)"},
                 "file_id": {"type": "string", "description": "a file she has (phone / email attachment / Drive) copied into the project"},
                 "text": {"type": "string", "description": "for small text files (e.g. a sub-composition) written inline"}}}},
         "name": {"type": "string", "description": "output film name for the chat card, e.g. 'Diwali offer film'"},
         "block": {"type": "string", "description": "for action=add: registry block name, e.g. flash-through-white"},
         "times": {"type": "array", "items": {"type": "number"}, "description": "for action=snapshot: seconds to still-capture"},
     }, "required": ["action"]}},
]
FRAMES_LABELS = {"hoola_frames": "HOOLA FRAMES se video ban rahi hai"}


def _resolve_files(ctx: Ctx, files: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """file_id -> absolute stored path, OWNER-CHECKED here (the worker never sees ids)."""
    from ..mailbox import service as ms
    out: list[dict[str, Any]] = []
    for f in files or []:
        if not isinstance(f, dict) or not str(f.get("name", "")).strip():
            raise ToolError("har file mein name (assets/... ya compositions/...) hona chahiye.")
        fid = str(f.get("file_id", "") or "")
        item = {"name": str(f.get("name", ""))}
        if f.get("text") is not None:
            item["text"] = str(f["text"])
        elif fid:
            try:
                row = ms._file_row(ctx.tenant_id, fid)
            except Exception as e:
                raise ToolError(f"file {fid}: {e}")
            item["path"] = str(Path(row.stored_path))
        else:
            raise ToolError(f"{item['name']}: file_id ya text ek dijiye.")
        out.append(item)
    return out


_IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")


def _resolve_spec(ctx: Ctx, spec: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """file_id -> asset name + stored path, OWNER-CHECKED here. The spec keeps only the
    asset NAME (assets/avatar.jpg, assets/item-2.png, assets/cta.png); the worker copies
    the real bytes from `files`. Photos only - png/jpg/webp, the engine draws everything else."""
    from ..mailbox import service as ms
    if not isinstance(spec, dict):
        raise ToolError("spec ek object hona chahiye (shape, script, ...).")
    spec = dict(spec)
    files: list[dict[str, Any]] = []

    def take(fid: Any, kind: str, idx: int | None = None) -> str:
        try:
            row = ms._file_row(ctx.tenant_id, str(fid))
        except Exception as e:
            raise ToolError(f"file {fid}: {e}")
        p = Path(row.stored_path)
        ext = p.suffix.lower()
        if ext not in _IMG_EXT:
            raise ToolError(f"{kind} ke liye photo png/jpg/webp honi chahiye (mili: {ext or 'bina ext'}).")
        name = f"assets/{kind}" + (f"-{idx}" if idx else "") + ext
        files.append({"name": name, "path": str(p)})
        return name

    if spec.get("avatar_file_id"):
        spec["avatar"] = take(spec.pop("avatar_file_id"), "avatar")
    items = []
    for i, it in enumerate(spec.get("items") or []):
        if not isinstance(it, dict):
            raise ToolError(f"item {i + 1} ek object hona chahiye.")
        it = dict(it)
        if it.get("file_id"):
            it["photo"] = take(it.pop("file_id"), "item", i + 1)
        items.append(it)
    if items:
        spec["items"] = items
    cta = spec.get("cta") if isinstance(spec.get("cta"), dict) else None
    if cta and cta.get("file_id"):
        cta = dict(cta)
        cta["image"] = take(cta.pop("file_id"), "cta")
        spec["cta"] = cta
    return spec, files


def _deliver_mp4(ctx: Ctx, name: str, path: str) -> dict[str, Any]:
    from ..agent.make_tools import _deliver  # the house delivery: mailbox + bus file card
    data = Path(path).read_bytes()
    safe = "".join(c if c.isalnum() or c in " ._-" else "_" for c in (name or "film"))[:80].strip() or "film"
    return _deliver(ctx, safe + ".mp4", data, "hoola")


async def hoola_frames(ctx: Ctx, action: str = "status", html: str = "", files: list[dict[str, Any]] | None = None,
                       name: str = "film", block: str = "", times: list[float] | None = None,
                       spec: dict[str, Any] | None = None, **_) -> dict[str, Any]:
    if action == "status":
        return await asyncio.to_thread(frames.status)
    if action == "add":
        if not (block or "").strip():
            raise ToolError("Kaunsa block? action=add ko block naam dijiye (status mein list).")
        try:
            return await asyncio.to_thread(frames.run, ctx.tenant_id, "add", block=block)
        except frames.FramesError as e:
            raise ToolError(str(e))
    if action == "avatar_film":
        if not spec:
            raise ToolError("Spec kahaan hai? avatar_film ko dijiye: {shape, script, ...} - HTML ki zaroorat nahi.")
        spec, files = await asyncio.to_thread(_resolve_spec, ctx, spec)
        try:
            res = await asyncio.to_thread(frames.run, ctx.tenant_id, "avatar_film",
                                          files=files, out_name=name, spec=spec)
        except frames.NotConfigured as e:
            raise ToolError(str(e))
        except frames.FramesError as e:
            raise ToolError(str(e))
        if not res.get("ok"):
            return {"ok": False, "stage": "check",
                    "errors": res.get("errors") or [],
                    "note": "check pe fail hua - yeh errors theek karke dobara avatar_film kijiye."}
        view = await asyncio.to_thread(_deliver_mp4, ctx, name, res["mp4_path"])
        return view | {"made": "mp4", "shape": res.get("shape"), "scenes": res.get("scenes"),
                       "duration_s": res.get("duration_s") or res.get("total_s"),
                       "size_mb": round(res.get("size_bytes", 0) / 1048576, 1),
                       "words_estimated": res.get("words_estimated"), "silent": res.get("silent"),
                       "note": "Video ka file card chat mein hai."}
    if not (html or "").strip():
        raise ToolError("Composition kahaan hai? html (poora index.html) dijiye - pehle action=check, phir render.")
    resolved = await asyncio.to_thread(_resolve_files, ctx, files)
    try:
        if action == "render":
            res = await asyncio.to_thread(frames.run, ctx.tenant_id, "render", html=html,
                                          files=resolved, out_name=name)
            if not res.get("ok"):
                return {"ok": False, "stage": "check",
                        "errors": res.get("errors") or [],
                        "note": "check pe fail hua - yeh errors theek karke dobara render kijiye."}
            view = await asyncio.to_thread(_deliver_mp4, ctx, name, res["mp4_path"])
            return view | {"made": "mp4", "duration_s": res.get("duration_s"),
                           "size_mb": round(res.get("size_bytes", 0) / 1048576, 1),
                           "note": "Video ka file card chat mein hai."}
        return await asyncio.to_thread(frames.run, ctx.tenant_id, action, html=html,
                                       files=resolved, times=times)
    except frames.NotConfigured as e:
        raise ToolError(str(e))
    except frames.FramesError as e:
        raise ToolError(str(e))


FRAMES_HANDLERS = {"hoola_frames": hoola_frames}
