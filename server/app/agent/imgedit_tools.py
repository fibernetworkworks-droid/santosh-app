"""Tool `image_edit`: edit her photos end to end - resize / crop / colour / filters / text / redact / compress / collage
(local, no key) and background removal / true upscale / object removal / background swap / restyle / old-photo restore
(AI, through the engines the server really has). One call can chain several steps and several photos."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

from ..imgedit import ai, ops, run as pipeline
from .tools import Ctx, ToolError

MAX_FILES = 10
MAX_AI_FILES = 5

GUIDE = (
    "IMAGE_EDIT GUIDE. Photos SHE attached (file_ids) -> edited photos back in chat. Chain steps in order: "
    "steps=[{op:..., ...}]. At most ONE AI step per photo.\n"
    "LOCAL (free, instant, no key): "
    "resize{width|height|percent|preset, fit contain|cover|inside|stretch, bg} (presets: " + ", ".join(sorted(ops.PRESETS)) + ") | "
    "crop{box:[l,t,r,b] 0-1 or px | aspect:'4:5', gravity} | rotate{degrees} | flip{direction h|v} | "
    "adjust{brightness,contrast,saturation,sharpness (-100..100 %), warmth, exposure(-3..3 stops), gamma} | auto_enhance{strength} | "
    "filter{name: grayscale|sepia|invert|blur|sharpen|denoise|pixelate|posterize|vignette|sketch|scan, amount} "
    "(scan = photo of a paper -> flat white page) | redact{regions:[[l,t,r,b]...], mode blur|pixelate|black} (hide a number plate, "
    "a face, an address) | border{size,color,percent} | pad{aspect,color} (square canvas, never crops) | round_corners{radius} | "
    "bg_color{color} (fill transparency) | text{text,position,size_pct,color,opacity,stroke,box,tile,angle} (caption / price / "
    "HER OWN watermark; Devanagari ok) | upscale_local{factor} (plain enlargement, no new detail). "
    "Output: format png|jpg|webp, quality, compress_kb (target size for forms: 'under 100 KB'). Camera EXIF / GPS is always dropped.\n"
    "AI (needs an engine on the server; the answer says which ran): remove_bg (transparent PNG; follow with bg_color for a "
    "colour) | upscale{factor 2-4} (real detail; falls back to plain enlargement if no engine) | remove_object{what} | "
    "replace_bg{what: 'a clean white studio' ...} | restyle{what} | restore (old / scratched photo) | colorize (b&w photo) | "
    "edit{what} (any other change in her words). Generative results carry a small 'AI se bana' label.\n"
    "ASK FIRST when it is not clear what she wants changed; do not guess a cutout or a style.\n"
    "REFUSED, plainly and never retried in other words: fake / altered ID, certificate, marksheet, bill, cheque, note or seal; "
    "removing a watermark / copyright / photographer's name / signature; nudity; face swap; famous people. Resizing, cropping or "
    "compressing her OWN ID photo for a form is fine (local ops only). Other tools: a NEW picture from words = photo_banao; "
    "passport-size photo + print sheet = id_photo; Brand posters = brand; white background for a product = photo_clean."
)

IMAGE_EDIT_TOOLS = [
    {"name": "image_edit", "description": (
        "EDIT her photos: resize to a social / print size, crop, rotate, brightness / colour, filters, scan-a-paper, hide "
        "a face or number plate (redact), border, add a caption / price / her own watermark, convert, compress to a target KB, "
        "collage, before-after (all local, free) and AI jobs: remove background (transparent PNG), upscale, remove an object, "
        "swap the background, restyle, restore an old photo, colourise, or any other change in her words. Actions: guide "
        "(read once: every op and parameter, and which AI engines are set up today) | run (file_ids 1-10 she attached, steps "
        "[{op,...}], format, quality, compress_kb, compare=true for a before/after card) | collage (file_ids 2-20, cols, gap, "
        "bg). One AI step per photo; up to 5 photos when it is an AI step. Results arrive as her files with a card. "
        "Refuses fake documents, watermark removal, nudity, face swap and famous people. A NEW picture from words = photo_banao."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["guide", "run", "collage"]},
         "file_ids": {"type": "array", "items": {"type": "string"}},
         "steps": {"type": "array", "items": {"type": "object", "properties": {"op": {"type": "string"}},
                                              "required": ["op"]}},
         "format": {"type": "string", "enum": ["png", "jpg", "webp"]},
         "quality": {"type": "integer"}, "compress_kb": {"type": "number"},
         "compare": {"type": "boolean"}, "filename": {"type": "string"},
         "cols": {"type": "integer"}, "gap": {"type": "integer"}, "bg": {"type": "string"},
     }, "required": ["action"]}},
]
IMAGE_EDIT_LABELS = {"image_edit": "Editing the photo"}


def _owner_file(ctx: Ctx, fid: str) -> tuple[str, bytes]:
    from .make_tools import _owner_bytes
    return _owner_bytes(ctx, fid)


def _deliver(ctx: Ctx, name: str, data: bytes) -> dict[str, Any]:
    from .make_tools import _deliver as deliver
    return deliver(ctx, name, data, "hoola")


def _out_name(src: str, ext: str, tag: str, custom: str, i: int, n: int) -> str:
    from .make_tools import _safe
    base = custom or f"{Path(src).stem} {tag}"
    if custom and n > 1:
        base = f"{custom} {i}"
    return _safe(base, "." + ext)


def _gate_actor(ctx: Ctx) -> None:
    from .. import usage
    if not str(getattr(ctx, "actor", "owner") or "owner").startswith(("owner", "approved", "goal")):
        if not usage.allowed(ctx.tenant_id, "routine"):
            raise ToolError(usage.blocked_text(ctx.tenant_id))


def _ids(a: dict) -> list[str]:
    ids = [str(x).strip() for x in (a.get("file_ids") or ([a["file_id"]] if a.get("file_id") else [])) if str(x).strip()]
    seen, out = set(), []
    for x in ids:
        if x not in seen:
            seen.add(x); out.append(x)
    return out


async def image_edit(ctx: Ctx, action: str = "guide", **a: Any):
    action = (action or "guide").strip().lower()
    if action == "guide":
        return {"guide": GUIDE, "ai_engines": ai.status(), "local_ops": sorted(ops.OPS), "ai_ops": sorted(ai.AI_OPS),
                "note": "ai_engines.ready=false: the server has no key / package for that job; local ops always work."}
    if action == "run":
        return await _run(ctx, a)
    if action == "collage":
        return await _collage(ctx, a)
    raise ToolError(f"image_edit action '{action}' is not an action: guide | run | collage.")


async def _run(ctx: Ctx, a: dict) -> dict[str, Any]:
    ids = _ids(a)
    if not ids:
        raise ToolError("Which photo? Ask the user to attach the photo in the chat, then give its file_id.")
    if len(ids) > MAX_FILES:
        raise ToolError(f"At most {MAX_FILES} photos at a time.")
    steps = a.get("steps") or []
    try:
        names = {}
        for fid in ids:                                           # safety + shape checked for every photo BEFORE any work
            names[fid] = (await asyncio.to_thread(_owner_file, ctx, fid))[0]
            pipeline.validate(steps, names[fid])
    except (ops.EditError, ai.AIError) as e:
        raise ToolError(str(e) + " (Do not retry a refused job in other words.)")
    uses_ai = any(str(s.get("op", "")).lower() in ai.AI_OPS for s in steps if isinstance(s, dict))
    if uses_ai:
        if len(ids) > MAX_AI_FILES:
            raise ToolError(f"AI edits: at most {MAX_AI_FILES} photos at a time (each photo costs separately).")
        _gate_actor(ctx)
    results: list[dict] = []
    for i, fid in enumerate(ids, 1):
        name, data = await asyncio.to_thread(_owner_file, ctx, fid)
        try:
            r = await pipeline.process(data, steps, fmt=str(a.get("format") or ""), quality=int(a.get("quality") or 92),
                                       compress_kb=a.get("compress_kb"), tenant=ctx.tenant_id, filename=name)
        except (ops.EditError, ai.AIError) as e:
            results.append({"file_id": fid, "name": name, "ok": False, "error": str(e)})
            continue
        tag = "edited"
        view = await asyncio.to_thread(_deliver, ctx, _out_name(name, r["ext"], tag, str(a.get("filename") or ""), i, len(ids)),
                                       r["bytes"])
        row = {"file_id": view["file_id"], "name": view["name"], "ok": True, "from": r["size_in"], "to": r["size_out"],
               "kb": r["kb_out"], "steps": r["report"], "ai": r["ai"]}
        if r["engines"]:
            row["engines"] = r["engines"]
        if r["notes"]:
            row["notes"] = r["notes"]
        if a.get("compare") and i <= 3:
            try:
                from PIL import Image
                import io
                before = ops.load(data)
                both = await asyncio.to_thread(ops.before_after, before, r["image"])
                cmp_bytes, cext = await asyncio.to_thread(ops.encode, both, "jpg", 88, None)
                cview = await asyncio.to_thread(_deliver, ctx, _out_name(name, cext, "before-after", "", i, len(ids)), cmp_bytes)
                row["compare_file_id"] = cview["file_id"]
            except Exception as e:                                   # the compare card is a bonus, never a failure
                row["compare_error"] = str(e)[:120]
        results.append(row)
    done = [r for r in results if r["ok"]]
    out: dict[str, Any] = {"status": "done" if done else "failed", "edited": len(done), "of": len(ids), "results": results}
    if uses_ai:
        out["cost_note"] = "The AI edit ran on the server's gateway / Gemini key; rupees are not priced in this tool (it counts in usage)."
    out["note"] = ("The edited photo is in the chat with its card. Say in one line what changed; name the engine exactly as it is in "
                   "'engines', do not make one up.")
    if not done:
        raise ToolError("No photo was made: " + "; ".join(r["error"] for r in results)[:400])
    return out


async def _collage(ctx: Ctx, a: dict) -> dict[str, Any]:
    ids = _ids(a)
    if not 2 <= len(ids) <= 20:
        raise ToolError("A collage needs the file_ids of 2 to 20 photos.")
    try:
        imgs = []
        for fid in ids:
            _, data = await asyncio.to_thread(_owner_file, ctx, fid)
            imgs.append(await asyncio.to_thread(ops.load, data))
        board = await asyncio.to_thread(ops.collage, imgs, int(a.get("cols") or 0), int(a.get("gap") if a.get("gap") is not None else 12),
                                        str(a.get("bg") or "white"))
        blob, ext = await asyncio.to_thread(ops.encode, board, str(a.get("format") or "jpg"), int(a.get("quality") or 90),
                                            a.get("compress_kb"))
    except ops.EditError as e:
        raise ToolError(str(e))
    view = await asyncio.to_thread(_deliver, ctx, _out_name("collage", ext, "", str(a.get("filename") or "Collage"), 1, 1), blob)
    return {"status": "done", "file_id": view["file_id"], "name": view["name"], "photos": len(ids),
            "size": f"{board.width}x{board.height}", "kb": round(len(blob) / 1024, 1)}


IMAGE_EDIT_HANDLERS = {"image_edit": image_edit}
