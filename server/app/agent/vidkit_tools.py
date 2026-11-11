"""Tool `video_kit`: exact video edits she names, end to end on the server's ffmpeg - trim, cut, crop, reframe to Reel /
YouTube shape (blur / pad / crop), resize, rotate, flip, speed / slow motion, reverse, fade, colour, looks, sharpen, grain
removal, light stabilisation, blur a private area, her text / her logo on the video, zoom, fps, mute, volume, loudness,
sound noise removal; compress to a size (WhatsApp), join clips (crossfade), photos -> slideshow, background music with
ducking, burned captions (her SRT or from the speech), thumbnails / frames / contact sheet, GIF, split into parts, two
videos in one frame. All local: no key, no model, no cost.

`video_edit` (the AI editor that watches the footage and makes a Reel from a brief) stays the tool for 'make a reel from
these clips'; this tool is for edits she can name."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from ..vidkit import ops
from .tools import Ctx, ToolError

MAX_FILES = 6
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic"}

GUIDE = (
    "VIDEO_KIT GUIDE. Her own videos -> edited video back in chat. Runs on the server with ffmpeg: free, no key, nothing "
    "leaves the server, location / camera metadata always removed. Output mp4 (H.264 + AAC, plays everywhere), max 1080p.\n"
    "action=run: file_ids (1-6, same steps on each), steps=[{op,...}] in order (max 15), format mp4|mov|webm, quality "
    "high|good|small. Times like 90, 1:30, 1m30s. Ops:\n"
    "  trim{start,end} keep only this part | cut{start,end} remove this part | speed{factor 0.25-4; <1 = slow motion} | "
    "reverse (<=60 s) | fade{in,out seconds} | crop{aspect 9:16|1:1|4:5.., position center|top|left..} or crop{x,y,w,h px "
    "or '10%'} | reframe{aspect 9:16, mode blur|pad|crop, color} = landscape video into a Reel / Status without cutting "
    "people off (blur = soft blurred background) | resize{preset 1080p|720p|480p or width / height / percent} | "
    "rotate{degrees 90|180|270} | flip{direction horizontal|vertical} | color{brightness, contrast, saturation -100..100, "
    "gamma} | look{name bw|sepia|vintage|warm|cool|vivid|cinematic|bright|faded} | sharpen{amount} | "
    "denoise{strength light|medium|strong} (grainy night video) | stabilize (light shake) | "
    "blur_area{x,y,w,h, start,end, strength} (hide a number plate, a phone number, a face she points to) | "
    "text{text, position top|center|bottom|corners, size_pct, color, box, start, end} (Hindi + English + ₹ work) | "
    "watermark{file_id of HER logo photo, position, size_pct, opacity} | zoom{factor, position} | fps{value} | "
    "mute | volume{db or percent} | normalize{target social|podcast|youtube or LUFS} | denoise_audio{strength}.\n"
    "Other actions: info (size, length, shape, sound, tips) | convert (format) | compress (target_mb number or "
    "whatsapp|email|discord|telegram; or quality) | join (file_ids 2-6 in order, crossfade seconds, fit blur|pad) | "
    "slideshow (photo file_ids 1-40, seconds each, aspect, music_file_id, zoom) | music (file_ids [video, music], music_db, "
    "duck, keep_original, fade_out) | captions (file_id + srt_file_id or srt text, or auto=true from the speech; position, "
    "size, color, box; also hands back the .srt) | frames (at [times] or every or count; sheet=true = one contact-sheet "
    "picture; a thumbnail = frames at the best moment) | gif (start, end <=15 s, width, fps) | split (every seconds, e.g. "
    "30 for WhatsApp Status, or at [times]; up to 20 parts) | combine (file_ids [main, second], layout "
    "pip|side_by_side|top_bottom, position, size_pct, audio main|second|both).\n"
    "Recipes: Reel from a YouTube-shape clip = reframe 9:16 blur + normalize social. WhatsApp = compress target whatsapp. "
    "Status = split every 30 (or 60). Slow motion = speed 0.5. Brand video = watermark (her logo) + text.\n"
    "NOT done, say so plainly: removing someone else's watermark / logo, face swap / deepfake / copying a person's face or "
    "voice, downloading other people's videos, making new AI footage (= Create studio / video_studio), choosing the best "
    "moments by itself from a brief (= video_edit). Music only if she has the right to use it."
)

VIDEO_KIT_TOOLS = [
    {"name": "video_kit", "description": (
        "EDIT her video exactly as she says, with ffmpeg on the server (free, no key): trim / cut a part, crop, reframe "
        "landscape to Reel / Short / Status 9:16 with a blurred background, resize 720p / 1080p, rotate, flip, speed and slow "
        "motion, reverse, fade, brightness / contrast / colour looks, sharpen, grain removal, light stabilisation, blur a "
        "private area (number plate, phone number), her text or her logo on the video, zoom, mute, volume, loudness, sound "
        "noise removal; compress to a size (WhatsApp 16 MB), join clips with crossfade, photos into a slideshow with music, "
        "background music with ducking, burned captions (her SRT or auto from speech), thumbnails / frames / contact sheet, "
        "GIF, split into parts (Status 30 s), picture-in-picture / side by side. Actions: guide (read once) | info | run "
        "(file_ids, steps [{op,...}]) | convert | compress | join | slideshow | music | captions | frames | gif | split | "
        "combine. Results arrive as her files. For 'make a Reel from these clips' by itself use video_edit. Does NOT remove "
        "others' watermarks, swap faces or make new AI video."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["guide", "info", "run", "convert", "compress", "join", "slideshow", "music",
                                                "captions", "frames", "gif", "split", "combine"]},
         "file_ids": {"type": "array", "items": {"type": "string"}},
         "steps": {"type": "array", "items": {"type": "object", "properties": {"op": {"type": "string"}}, "required": ["op"]}},
         "format": {"type": "string", "enum": list(ops.FORMATS)},
         "quality": {"type": "string", "enum": list(ops.QUALITY)},
         "target_mb": {"type": "string", "description": "a number of MB, or whatsapp | email | discord | telegram"},
         "crossfade": {"type": "number"}, "fit": {"type": "string", "enum": ["blur", "pad"]},
         "seconds": {"type": "number"}, "aspect": {"type": "string"}, "zoom": {"type": "boolean"},
         "music_file_id": {"type": "string"}, "music_db": {"type": "number"}, "duck": {"type": "boolean"},
         "keep_original": {"type": "boolean"}, "fade_out": {"type": "number"},
         "srt_file_id": {"type": "string"}, "srt": {"type": "string"}, "auto": {"type": "boolean"},
         "language": {"type": "string"}, "position": {"type": "string"}, "size": {"type": "number"},
         "color": {"type": "string"}, "box": {"type": "boolean"},
         "at": {"type": "array", "items": {"type": "string"}}, "every": {"type": "string"}, "count": {"type": "integer"},
         "sheet": {"type": "boolean"}, "width": {"type": "integer"},
         "start": {"type": "string"}, "end": {"type": "string"}, "fps": {"type": "number"},
         "layout": {"type": "string", "enum": ["pip", "side_by_side", "top_bottom"]}, "size_pct": {"type": "number"},
         "audio": {"type": "string", "enum": ["main", "second", "both"]},
         "filename": {"type": "string"},
     }, "required": ["action"]}},
]
VIDEO_KIT_LABELS = {"video_kit": "Video edit kar raha hoon"}


def _owner_path(ctx: Ctx, fid: str) -> tuple[str, str]:
    from ..mailbox import service as ms
    try:
        f = ms._file_row(ctx.tenant_id, str(fid))
    except Exception as e:
        raise ToolError(str(e))
    return f.name, f.stored_path


def _deliver(ctx: Ctx, name: str, data: bytes) -> dict[str, Any]:
    from .make_tools import _deliver as deliver
    return deliver(ctx, name, data, "hoola")


def _name(src: str, tag: str, ext: str, custom: str = "", i: int = 1, n: int = 1) -> str:
    from .make_tools import _safe
    base = (f"{custom} {i}" if n > 1 else custom) if custom else f"{Path(src).stem} {tag}".strip()
    return _safe(base, "." + ext)


def _ids(a: dict) -> list[str]:
    raw = a.get("file_ids") or ([a["file_id"]] if a.get("file_id") else [])
    out: list[str] = []
    for x in raw:
        x = str(x).strip()
        if x and x not in out:
            out.append(x)
    return out


def _need(ids: list[str], lo: int, hi: int, what: str) -> None:
    if not ids:
        raise ToolError("Kaunsa video? Video chat mein attach karne ko kahiye, phir uska file_id do.")
    if not lo <= len(ids) <= hi:
        raise ToolError(f"{what} ke liye {lo} se {hi} file chahiye.")


def _mb(n: int) -> float:
    return round(n / 1048576, 2)


def _resolve_steps(ctx: Ctx, steps: list[dict]) -> list[dict]:
    """Her logo photo for a watermark step is resolved to its stored path (only her own files)."""
    out = []
    for st in steps:
        st = dict(st) if isinstance(st, dict) else st
        if isinstance(st, dict) and str(st.get("op", "")).lower() == "watermark":
            fid = st.get("file_id") or st.get("logo_file_id")
            if not fid:
                raise ToolError("watermark ke liye uske logo ki photo ka file_id chahiye (sirf apna logo).")
            name, path = _owner_path(ctx, str(fid))
            if Path(name).suffix.lower() not in IMAGE_EXT:
                raise ToolError("Watermark ke liye logo ek photo (PNG / JPG) honi chahiye.")
            st["_path"] = path
        out.append(st)
    return out


async def _one(ctx: Ctx, name: str, tag: str, r: dict, custom: str = "") -> dict[str, Any]:
    view = await asyncio.to_thread(_deliver, ctx, _name(name, tag, r["ext"], custom), r["bytes"])
    row = {"file_id": view["file_id"], "name": view["name"], "mb": _mb(len(r["bytes"]))}
    o = r.get("out")
    if o:
        row.update(seconds=round(o["duration"], 2), size=f"{o['width']}x{o['height']}", sound=o["has_audio"])
    return row


async def video_kit(ctx: Ctx, action: str = "guide", **a: Any):
    action = (action or "guide").strip().lower()
    if action == "guide":
        return {"guide": GUIDE, "ffmpeg": ops.ffmpeg_ok(), "ops": sorted(ops.STEP_OPS), "looks": sorted(ops.LOOKS),
                "aspects": sorted(k for k in ops.ASPECTS if ":" in k)}
    if not ops.ffmpeg_ok():
        raise ToolError("Server par ffmpeg nahi hai, isliye video edit abhi nahi ho sakta (owner: apt install ffmpeg).")
    ids = _ids(a)
    custom = str(a.get("filename") or "")
    try:
        if action == "info":
            _need(ids, 1, MAX_FILES, "info")
            out = []
            for fid in ids:
                name, path = await asyncio.to_thread(_owner_path, ctx, fid)
                try:
                    p = await asyncio.to_thread(ops.probe, path)
                    out.append({"file_id": fid, "name": name, "seconds": p["duration"], "size": f"{p['width']}x{p['height']}",
                                "fps": p["fps"], "sound": p["has_audio"], "mb": _mb(p["size"]), "verdict": ops.verdict(p)})
                except ops.VideoError as e:
                    out.append({"file_id": fid, "name": name, "error": str(e)})
            return {"files": out}
        if action in ("run", "convert"):
            _need(ids, 1, MAX_FILES, action)
            steps = []
            if action == "run":
                steps = _resolve_steps(ctx, ops.check_steps(a.get("steps")))
            results = []
            for i, fid in enumerate(ids, 1):
                name, path = await asyncio.to_thread(_owner_path, ctx, fid)
                try:
                    if action == "run":
                        r = await asyncio.to_thread(ops.edit, path, steps, a.get("format") or "mp4", a.get("quality") or "good")
                    else:
                        r = await asyncio.to_thread(ops.convert, path, a.get("format") or "mp4", a.get("quality") or "good")
                except ops.VideoError as e:
                    results.append({"file_id": fid, "name": name, "ok": False, "error": str(e)})
                    continue
                view = await asyncio.to_thread(_deliver, ctx, _name(name, "edited" if action == "run" else "", r["ext"],
                                                                  custom, i, len(ids)), r["bytes"])
                o = r["out"]
                row = {"file_id": view["file_id"], "name": view["name"], "ok": True, "seconds": round(o["duration"], 2),
                       "size": f"{o['width']}x{o['height']}", "mb": _mb(len(r["bytes"])), "sound": o["has_audio"]}
                if action == "run":
                    row["steps"] = r["steps"]
                    if max(r["in"]["width"], r["in"]["height"]) > ops.MAX_LONG_SIDE:
                        row["note"] = "1080p par laaya gaya (chat ke liye)"
                results.append(row)
            done = [r for r in results if r["ok"]]
            if not done:
                raise ToolError("Koi video nahi bana: " + "; ".join(r["error"] for r in results)[:400])
            return {"status": "done", "edited": len(done), "of": len(ids), "results": results,
                    "note": "Video chat mein file ke roop mein hai. Ek line mein batao kya badla."}
        if action == "compress":
            _need(ids, 1, MAX_FILES, "Compress")
            results = []
            for i, fid in enumerate(ids, 1):
                name, path = await asyncio.to_thread(_owner_path, ctx, fid)
                try:
                    r = await asyncio.to_thread(ops.compress, path, a.get("target_mb"), a.get("quality") or "")
                except ops.VideoError as e:
                    results.append({"file_id": fid, "name": name, "ok": False, "error": str(e)})
                    continue
                row = await _one(ctx, name, "small", r, f"{custom} {i}".strip() if custom and len(ids) > 1 else custom)
                row.update(ok=True, from_mb=_mb(r["in"]["size"]), target_mb=r["target_mb"])
                results.append(row)
            if not any(r["ok"] for r in results):
                raise ToolError("; ".join(r["error"] for r in results)[:400])
            return {"status": "done", "results": results}
        if action == "join":
            _need(ids, 2, MAX_FILES, "Jodne")
            paths = [await asyncio.to_thread(_owner_path, ctx, f) for f in ids]
            r = await asyncio.to_thread(ops.join, [p for _, p in paths], a.get("crossfade") or 0, a.get("fit") or "blur",
                                        a.get("format") or "mp4")
            row = await _one(ctx, "joined video", "", r, custom)
            return {"status": "done", **row, "pieces": r["pieces"]}
        if action == "slideshow":
            _need(ids, 1, 40, "Slideshow")
            paths = []
            for f in ids:
                name, path = await asyncio.to_thread(_owner_path, ctx, f)
                if Path(name).suffix.lower() not in IMAGE_EXT:
                    raise ToolError(f"'{name}' photo nahi hai; slideshow sirf photos se banta hai (video jodne ke liye join).")
                paths.append(path)
            music = None
            if a.get("music_file_id"):
                music = (await asyncio.to_thread(_owner_path, ctx, a["music_file_id"]))[1]
            r = await asyncio.to_thread(ops.slideshow, paths, a.get("seconds") or 3, a.get("aspect") or "9:16", music,
                                        a.get("zoom", True) is not False, a.get("music_db", -6))
            row = await _one(ctx, "slideshow", "", r, custom)
            row.update(photos=r["photos"], seconds=r["seconds"], size=r["size"], music=bool(music))
            out = {"status": "done", **row}
            if music:
                out["note"] = "Music sirf wahi jiska haq unke paas ho (apna / licensed)."
            return out
        if action == "music":
            mid = a.get("music_file_id")
            if mid and ids and len(ids) == 1:
                ids = ids + [str(mid)]
            _need(ids, 2, 2, "Music (pehla video, doosra music)")
            (vn, vp), (_, mp) = [await asyncio.to_thread(_owner_path, ctx, f) for f in ids]
            r = await asyncio.to_thread(ops.add_music, vp, mp, a.get("music_db", -16), a.get("duck", True) is not False,
                                        a.get("keep_original", True) is not False, a.get("fade_out", 2))
            row = await _one(ctx, vn, "with music", r, custom)
            return {"status": "done", **row, "original_sound_kept": r["original_sound"], "ducked": r["ducked"],
                    "note": "Music sirf wahi chalaiye jiska haq unke paas ho (apna / licensed); Instagram / YouTube ki "
                            "library ka gaana bahar ki file mein nahi chalta."}
        if action == "captions":
            _need(ids, 1, 1, "Captions")
            name, path = await asyncio.to_thread(_owner_path, ctx, ids[0])
            if a.get("srt_file_id"):
                sn, sp = await asyncio.to_thread(_owner_path, ctx, a["srt_file_id"])
                if Path(sn).suffix.lower() not in (".srt", ".txt", ".vtt"):
                    raise ToolError("Captions ki file .srt honi chahiye.")
                cues = ops.parse_srt(Path(sp).read_text(encoding="utf-8", errors="replace").replace("WEBVTT", ""))
                source = "her SRT file"
            elif a.get("srt"):
                cues = ops.parse_srt(str(a["srt"]))
                source = "the SRT text"
            elif a.get("auto"):
                cues = await asyncio.to_thread(ops.auto_cues, path, a.get("language") or None)
                if not cues:
                    raise ToolError("Awaaz se captions abhi is server par nahi bante (speech engine nahi hai) ya video mein "
                                    "boli hui baat nahi mili. Doosra raasta: kaan se transcript banwa kar uska SRT export "
                                    "kijiye, phir srt_file_id ke saath captions chalaiye; ya video_edit (captions=true).")
                source = "the speech in the video (auto - check spellings)"
            else:
                raise ToolError("Captions kahan se? srt_file_id (uski .srt file), srt (text) ya auto=true (awaaz se).")
            r = await asyncio.to_thread(ops.burn_captions, path, cues, a.get("position") or "bottom", a.get("size"),
                                        a.get("color") or "white", bool(a.get("box")))
            row = await _one(ctx, name, "captions", r, custom)
            srt = await asyncio.to_thread(_deliver, ctx, _name(name, "captions", "srt"), r["srt"].encode("utf-8"))
            return {"status": "done", **row, "captions": r["cues"], "from": source, "srt_file_id": srt["file_id"]}
        if action == "frames":
            _need(ids, 1, 1, "Frames")
            name, path = await asyncio.to_thread(_owner_path, ctx, ids[0])
            r = await asyncio.to_thread(ops.frames, path, a.get("at"), a.get("every"), a.get("count"), bool(a.get("sheet")),
                                        a.get("width"))
            if "sheet" in r:
                v = await asyncio.to_thread(_deliver, ctx, _name(name, "contact sheet", "jpg", custom), r["sheet"])
                return {"status": "done", "file_id": v["file_id"], "name": v["name"], "times": r["times"]}
            out = []
            for i, f in enumerate(r["frames"], 1):
                t = f["at"]
                v = await asyncio.to_thread(_deliver, ctx, _name(name, f"frame {int(t // 60)}m{t % 60:04.1f}s", "jpg"),
                                            f["bytes"])
                out.append({"file_id": v["file_id"], "name": v["name"], "at": t})
            return {"status": "done", "frames": out,
                    "note": "Thumbnail ke upar title chahiye to image_edit (text) us frame par chalaiye."}
        if action == "gif":
            _need(ids, 1, 1, "GIF")
            name, path = await asyncio.to_thread(_owner_path, ctx, ids[0])
            r = await asyncio.to_thread(ops.gif, path, a.get("start") or 0, a.get("end"), a.get("width") or 480,
                                        a.get("fps") or 12)
            row = await _one(ctx, name, "gif", r, custom)
            return {"status": "done", **row, "from": r["from"], "to": r["to"]}
        if action == "split":
            _need(ids, 1, 1, "Split")
            name, path = await asyncio.to_thread(_owner_path, ctx, ids[0])
            parts = await asyncio.to_thread(ops.split, path, a.get("every"), a.get("at"))
            out = []
            for i, p in enumerate(parts, 1):
                v = await asyncio.to_thread(_deliver, ctx, _name(name, f"part {i}", p["ext"]), p["bytes"])
                out.append({"file_id": v["file_id"], "name": v["name"], "from": p["from"], "to": p["to"]})
            return {"status": "done", "parts": out}
        if action == "combine":
            _need(ids, 2, 2, "Combine (pehla main video, doosra chhota / bagal wala)")
            (mn, mp), (_, sp) = [await asyncio.to_thread(_owner_path, ctx, f) for f in ids]
            r = await asyncio.to_thread(ops.combine, mp, sp, a.get("layout") or "pip", a.get("position") or "bottom-right",
                                        a.get("size_pct") or 30, a.get("audio") or "main")
            row = await _one(ctx, mn, r["layout"].replace("_", " "), r, custom)
            return {"status": "done", **row}
    except ops.VideoError as e:
        raise ToolError(str(e))
    raise ToolError(f"video_kit action '{action}' nahi hai: guide | info | run | convert | compress | join | slideshow | "
                    "music | captions | frames | gif | split | combine.")


VIDEO_KIT_HANDLERS = {"video_kit": video_kit}
