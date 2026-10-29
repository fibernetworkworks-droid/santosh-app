"""v0.258 CREATE STUDIO jobs + her creations shelf.

The console's Create Studio pages start work here directly (no chat turn in between, like OpenArt): image (photo_banao's
engine), song, voice-over and dubbing (create/service.py). Each job runs in the background; the page polls
GET /api/create/jobs/{id}. Every finished file is kept twice:
  * on her Create shelf (data/create/<tenant>/, index.json) - stays until she deletes it, served with her login;
  * as a chat card in the conversation the page names (a 24-hour chat file like every other chat output), so the
    chat, the workspace and "My creations" in the console show it too.
Jobs live in memory: a server restart forgets a running job (the page says so); finished files are on disk.
"""
from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import re
import threading
import time
from pathlib import Path
from typing import Any

from ..db import new_id

log = logging.getLogger("santosh.create")

KINDS = ("image", "cast", "song", "voice", "dub")
_JOBS: dict[str, dict[str, Any]] = {}
_TASKS: dict[str, asyncio.Task] = {}
_LOCK = threading.Lock()
MAX_JOBS = 200                       # per server, oldest finished ones are forgotten first
MAX_RUNNING = 3                      # per owner at a time


class JobError(Exception):
    pass


def _safe(tenant: str) -> str:
    return re.sub(r"[^\w-]", "_", tenant)[:64] or "default"


def home(tenant: str) -> Path:
    p = Path("data") / "create" / _safe(tenant)
    (p / "items").mkdir(parents=True, exist_ok=True)
    return p


def _index_path(tenant: str) -> Path:
    return home(tenant) / "index.json"


def shelf(tenant: str) -> list[dict[str, Any]]:
    f = _index_path(tenant)
    try:
        items = json.loads(f.read_text(encoding="utf-8")) if f.is_file() else []
    except (ValueError, OSError):
        items = []
    return [i for i in items if (home(tenant) / "items" / i.get("file", "")).is_file()]


def _write(tenant: str, items: list[dict[str, Any]]) -> None:
    f = _index_path(tenant)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    tmp.replace(f)


def keep(tenant: str, kind: str, title: str, ext: str, data: bytes, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    iid = new_id("cr")
    name = f"{iid}{ext}"
    (home(tenant) / "items" / name).write_bytes(data)
    item = {"id": iid, "kind": kind, "title": (title or "Hoola creation")[:80], "file": name,
            "mime": mimetypes.guess_type(name)[0] or "application/octet-stream", "size": len(data),
            "created": int(time.time()), **({"meta": meta} if meta else {})}
    with _LOCK:
        items = shelf(tenant)
        items.insert(0, item)
        _write(tenant, items[:500])
    return item


def item_file(tenant: str, iid: str) -> tuple[Path, dict[str, Any]]:
    it = next((i for i in shelf(tenant) if i["id"] == iid), None)
    if not it:
        raise JobError("Yeh creation nahi mili")
    return home(tenant) / "items" / it["file"], it


def forget(tenant: str, iid: str) -> bool:
    with _LOCK:
        items = shelf(tenant)
        it = next((i for i in items if i["id"] == iid), None)
        if not it:
            return False
        (home(tenant) / "items" / it["file"]).unlink(missing_ok=True)
        _write(tenant, [i for i in items if i["id"] != iid])
    return True


# ---------------------------------------------------------------- jobs
def public(j: dict[str, Any]) -> dict[str, Any]:
    return {k: j.get(k) for k in ("id", "kind", "status", "title", "error", "items", "created", "done", "note", "step")}


def get(tenant: str, jid: str) -> dict[str, Any]:
    j = _JOBS.get(jid)
    if not j or j["tenant"] != tenant:
        raise JobError("Yeh kaam nahi mila (server dobara chalu hua ho to naya shuru kijiye)")
    return public(j)


def recent(tenant: str) -> list[dict[str, Any]]:
    return [public(j) for j in sorted(_JOBS.values(), key=lambda x: -x["created"]) if j["tenant"] == tenant][:30]


def _trim() -> None:
    if len(_JOBS) <= MAX_JOBS:
        return
    for jid in [j["id"] for j in sorted(_JOBS.values(), key=lambda x: x["created"]) if j["status"] != "running"][:len(_JOBS) - MAX_JOBS]:
        _JOBS.pop(jid, None)


def _title(kind: str, p: dict[str, Any]) -> str:
    t = str(p.get("title") or "").strip()
    if t:
        return t[:80]
    words = str(p.get("prompt") or p.get("brief") or p.get("text") or p.get("genre") or "").strip()
    words = re.sub(r"\s+", " ", words)[:48]
    if kind == "cast":
        return ("Cast · " + str(p.get("name") or "Character"))[:80]
    return words or {"image": "Hoola picture", "song": "Hoola song", "voice": "Voice-over", "dub": "Dub"}[kind]


def start(tenant: str, kind: str, params: dict[str, Any], conversation_id: str = "") -> dict[str, Any]:
    if kind not in KINDS:
        raise JobError("kind: image | cast | song | voice | dub")
    if sum(1 for j in _JOBS.values() if j["tenant"] == tenant and j["status"] == "running") >= MAX_RUNNING:
        raise JobError(f"Ek saath {MAX_RUNNING} kaam chal sakte hain; ek khatam hone dijiye.")
    jid = new_id("cj")
    j = {"id": jid, "tenant": tenant, "kind": kind, "status": "running", "title": _title(kind, params), "error": "",
         "items": [], "created": int(time.time()), "done": 0, "note": "", "step": "", "conv": conversation_id}
    _JOBS[jid] = j
    _trim()
    _TASKS[jid] = asyncio.get_running_loop().create_task(_run(j, params))
    _TASKS[jid].add_done_callback(lambda _t: _TASKS.pop(jid, None))
    return public(j)


def _card(j: dict[str, Any], title: str, ext: str, data: bytes, extra: dict[str, Any]) -> None:
    """The same file as a chat card (photo_made for pictures, pc_file otherwise) in the page's conversation."""
    conv = j.get("conv")
    if not conv:
        return
    try:
        from ..agent.make_tools import _safe as fname
        from ..events import bus
        from ..mailbox import service as ms
        from ..pc.service import public_file
        row = ms.store_bytes(j["tenant"], fname(title, ext), data, "to_phone")
        view = public_file(row)
        view.pop("pc_path", None)
        bus.publish(conv, "photo_made" if j["kind"] in ("image", "cast") else "pc_file",
                    {**view, "title": title, "studio": j["kind"], "ai": True, **extra})
    except Exception:
        log.exception("create card")


async def _run(j: dict[str, Any], p: dict[str, Any]) -> None:
    from .. import usage
    from . import service as cs
    t = j["tenant"]
    try:
        with usage.scope(t, "create"):
            made: list[tuple[str, str, bytes, dict[str, Any]]] = []     # (title, ext, bytes, meta)
            if j["kind"] in ("image", "cast"):
                from .. import photogen
                imgs = [_owner(t, f) for f in (p.get("file_ids") or [])[:photogen.MAX_INPUTS]]
                n = max(1, min(int(p.get("count") or 1), 4))
                if j["kind"] == "cast":
                    prompt = cs.cast_prompt(str(p.get("name") or ""), str(p.get("prompt") or ""), str(p.get("style") or ""))
                    p = {**p, "aspect": "16:9", "style": ""}
                else:
                    prompt = str(p.get("prompt") or "").strip()
                if p.get("style"):
                    prompt += f"\nStyle: {p['style']}."
                for i in range(n):
                    j["step"] = f"{i + 1} / {n}"
                    try:
                        r = await asyncio.to_thread(photogen.make, prompt, imgs, str(p.get("aspect") or ""),
                                                    "best" if p.get("quality") == "best" else "fast")
                    except photogen.Refused as e:
                        raise cs.CreateError(str(e)) from None
                    except photogen.PhotoError as e:
                        raise cs.CreateError(str(e)) from None
                    meta = {"aspect": r["aspect"], "model": r["model"], "quality": r["quality"]}
                    if j["kind"] == "cast":
                        meta.update(name=str(p.get("name") or "")[:40], description=str(p.get("prompt") or "")[:600],
                                    voice=str(p.get("voice") or ""))
                    made.append((j["title"], ".png", r["png"], meta))
            elif j["kind"] == "song":
                r = await cs.song(p.get("brief") or "", p.get("genre") or "", p.get("language") or "Hindi",
                                  p.get("vocals") or "duet", p.get("mood") or "", int(p.get("bpm") or 0),
                                  int(p.get("seconds") or 0), p.get("lyrics") or "")
                made.append((j["title"], r["ext"], r["bytes"], {"genre": p.get("genre") or "", "language": p.get("language") or "",
                                                               "vocals": p.get("vocals") or "", "mood": p.get("mood") or ""}))
            elif j["kind"] == "voice":
                r = await cs.voice(p.get("text") or "", p.get("voice") or "", p.get("language") or "Hindi",
                                   p.get("style") or "friendly", float(p.get("speed") or 1.0), t)
                made.append((j["title"], r["ext"], r["bytes"], {"voice": r["voice"], "seconds": r["seconds"],
                                                               "style": p.get("style") or "", "language": p.get("language") or ""}))
            else:
                fid = str(p.get("file_id") or "")
                if not fid:
                    raise cs.CreateError("Pehle apna video upload kijiye.")
                name, data = _owner_named(t, fid)
                j["step"] = "listening"
                r = await cs.dub(data, name, p.get("languages") or [], p.get("keep_sound", True) is not False,
                                 progress=lambda s: j.__setitem__("step", s))
                j["note"] = "Voices are matched to each speaker, not cloned; lips are not re-synced."
                stem = name.rsplit(".", 1)[0][:30]
                lines = [{"start": ln.get("start"), "speaker": ln.get("speaker"), "text": ln.get("text"),
                          "tr": ln.get("tr") or {}} for ln in r["lines"]][:200]
                for o in r["outputs"]:
                    made.append((f"{stem} · {o['language']} dub", ".mp4", o["bytes"],
                                 {"language": o["language"], "seconds": o["seconds"], "source_language": r["source_language"],
                                  "speakers": r["speakers"], "voices": r["voices"], "lines": lines}))
            for title, ext, data, meta in made:
                it = keep(t, j["kind"], title, ext, data, meta)
                j["items"].append({k: it[k] for k in ("id", "kind", "title", "mime", "size", "created")} | {"meta": meta})
                _card(j, title, ext, data, {k: v for k, v in meta.items() if k not in ("lines", "speakers", "voices")})
        j["status"] = "done"
    except cs.CreateError as e:
        j["status"], j["error"] = "failed", str(e)
    except JobError as e:
        j["status"], j["error"] = "failed", str(e)
    except Exception as e:
        log.exception("create job %s", j["kind"])
        j["status"], j["error"] = "failed", f"Nahi ho paya: {str(e)[:160]}"
    finally:
        j["done"] = int(time.time())
        j["step"] = ""


def _owner_named(tenant: str, fid: str) -> tuple[str, bytes]:
    from ..mailbox import service as ms
    try:
        f = ms._file_row(tenant, str(fid))
    except Exception as e:
        raise JobError(str(e)) from None
    return f.name, Path(f.stored_path).read_bytes()


def _owner(tenant: str, fid: str) -> bytes:
    if str(fid).startswith("cr_"):                      # a picture from her Create shelf
        path, _ = item_file(tenant, str(fid))
        return path.read_bytes()
    return _owner_named(tenant, fid)[1]
