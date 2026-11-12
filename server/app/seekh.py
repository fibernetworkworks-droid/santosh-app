"""Seekh = a way of working learned by WATCHING a video (v0.713 SEEKH MANCH).

Owner (2026-11-09, verbatim): "NOW LETS WORK ON A HOOLA AI AGENT THAT WILL SEE THE YOUTUBVIDEO FROM
LINK, SHORTS, MP4 OR ANY VIDEO FORMAT. EXAMPLE FEELING [FILLING] THE FORM OR ANY WORK --- AI WILL
LEARN THAT TRAIN ITSELF KEEP IN MEMORY AND IF TASK GIVEN RELATED TO IT IT WILL PERFORM SMOOTHLY"

The bridge between organs that already ship, not a second brain: the Gemini eyes
(youtube/service.gemini_video for links, the videoedit/brain inline-bytes pattern for attached files),
the learned-ways memory (procedures: hint() reads it into every owner turn) and the operator's recipe
box (find() reads it at every job start; a good real run overwrites a draft with reality through
from_trace). SEEKH adds only the middle: perceive the WAY OF WORKING, distill it into steps that each
carry the [m:ss] moment they were seen at, and store them as UNPROVEN.

LAWS (the plan's §5, tested in test_v0713_seekh_manch.py):
  EVIDENCE  every step carries at least one [m:ss] timestamp from the perception; a step the notes do
            not support is dropped into gotchas, never guessed;
  HONESTY   learned is not proven: wins come only from real runs (the procedures counter), and the
            tool's reply always says so until then;
  PRIVACY   no literal personal value from the video is ever kept - values become variable names and
            short hints (the same law as operator recipes and procedures' digit masking);
  CAPS      seekh_enabled kill switch, learns per day, one file's size and length;
  PURITY    pure functions + lazy imports, no new pip, no new keys, no network at import.
"""
from __future__ import annotations

import io
import json
import logging
import re
import threading
import time
import uuid
import datetime as dt
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.seekh")

SEEKH_VERSION = "v0.713"
MAX_SIDECAR = 100
TITLE_MAX = 120
LABEL_MAX = 120
YT_MAX_S = 3 * 3600          # same cap as youtube/service.watch

_TS = re.compile(r"\d{1,2}:\d{2}(?::\d{2})?")
_DIGITS = re.compile(r"\d{3,}")


class SeekhError(Exception):
    """Honest failure: what is missing, in plain words."""


class SeekhStopped(SeekhError):
    """v0.745 she pressed Stop: not a failure, nothing kept."""


# v0.745 LIVE NOTES: while a watch runs, the perceive doors stream Gemini's notes as it writes them. The live sink
# and the stop flag ride a thread-local so every perceive signature stays as it was (the v0.713 tests patch them).
_LIVE = threading.local()


def _check_stop() -> None:
    ev = getattr(_LIVE, "cancel", None)
    if ev is not None and ev.is_set():
        raise SeekhStopped("Stopped - nothing was kept.")


def _stream_text(client, model: str, contents, config=None) -> str:
    """Gemini's notes as they are written: each chunk goes to the live sink; Stop is honoured between chunks.
    No live sink = one plain call (the old path, byte for byte)."""
    sink = getattr(_LIVE, "on_text", None)
    kw = {"model": model, "contents": contents}
    if config is not None:
        kw["config"] = config
    if sink is None or not hasattr(client.models, "generate_content_stream"):
        r = client.models.generate_content(**kw)
        return (getattr(r, "text", "") or "").strip()
    acc = ""
    for ch in client.models.generate_content_stream(**kw):
        _check_stop()
        t = getattr(ch, "text", None) or ""
        if t:
            acc += t
            try:
                sink(acc)
            except Exception:                           # noqa: BLE001 - a UI sink never breaks the watch
                log.exception("seekh live sink failed")
    return acc.strip()


# ---------------------------------------------------------------- stage 2: the ask (perception)
_PERCEIVE_ASK = (
    "Watch this video and write down the WAY OF WORKING it shows, as numbered steps in order: the site or app "
    "open on screen (the URL if visible), every click and button press, every field and what kind of thing goes "
    "into it (describe the value, never write out digits or IDs), the order, and what to watch out for. Give "
    "every step a [m:ss] timestamp of the moment it happens on screen. Also list what is needed before starting. "
    "Only say what is actually shown; say plainly what you could not see clearly."
)

# ---------------------------------------------------------------- stage 3: the distill
_DISTILL_SYSTEM = (
    "You turn raw video-watching notes into one strict JSON recipe of the way of working the video showed. "
    "Never invent a step the notes do not contain; never keep a personal value (names, numbers, IDs, passwords): "
    "a value becomes a variable name plus a short hint of what belongs there. Reply with ONLY one JSON object, "
    "no prose before or after."
)

_DISTILL_PROMPT = """The video watcher's notes:
{perception}

Return this JSON object:
{{
  "title": "short name of this way of working",
  "kind": "website_work" or "other_work",
  "site": "example.com" (website_work only),
  "start_url": "https://..." (only if shown in the video),
  "steps": [
    {{"n": 1, "action": "open|click|fill|select|check|upload|type|wait|other",
      "target": {{"role": "button|textbox|link|dropdown|checkbox|other", "name": "the label on screen", "label": ""}},
      "value_var": "snake_case_variable" (fill / type / select only; NEVER a literal value),
      "value_hint": "what goes there, described",
      "evidence": ["m:ss"] (the moment(s) this step is seen - AT LEAST ONE),
      "note": "one short line of what happens"}}
  ],
  "preconditions": ["what must be ready before starting"],
  "gotchas": ["what to watch out for"],
  "variables": {{"value_var": {{"field": "which field", "why": "why it differs per person"}}}},
  "confidence": 0.62 (0.0-1.0: how complete and correct you believe the steps are),
  "unsure": ["anything you could not see clearly"]
}}
Laws: every step needs at least one [m:ss] evidence that appears in the notes; no literal digits of any
personal value anywhere; a filled value is a variable name, not the value itself; a step the notes do not
support is left out, not guessed.
Problems from the previous attempt (fix every one; "none" if this is the first):
{problems}"""


# ---------------------------------------------------------------- stage 1: classify the reference
def _classify(ref: str) -> tuple[str, str]:
    """(kind, key): youtube (link / Shorts / bare 11-char id), file (a chat file_id) or url (direct media)."""
    r = str(ref or "").strip()
    if not r:
        raise SeekhError("Which video? Give a YouTube link, a video file you attached, or a direct video URL.")
    m = re.fullmatch(r"kept:([\w-]{4,80})", r)
    if m:                                               # v0.785 the learner's own copy of an earlier upload
        return "kept", m.group(1)
    from .youtube.client import video_id
    vid = video_id(r)
    if vid:
        return "youtube", vid
    if r.lower().startswith(("http://", "https://")):
        return "url", r
    if re.fullmatch(r"[\w.-]{4,180}", r):
        return "file", r
    raise SeekhError("That does not look like a video: give a YouTube link, a video file you attached, or a direct video URL.")


# ---------------------------------------------------------------- the sidecar (provenance)
def _dir() -> Path:
    p = Path("data") / "seekh"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _safe(tenant: str) -> str:
    return re.sub(r"[^\w-]", "_", tenant)[:64] or "default"


def _sidecar_path(tenant: str) -> Path:
    return _dir() / f"{_safe(tenant)}.json"


def _load(tenant: str) -> list[dict[str, Any]]:
    p = _sidecar_path(tenant)
    if not p.exists():
        return []
    try:
        v = json.loads(p.read_text(encoding="utf-8"))
        return v if isinstance(v, list) else []
    except Exception:                                   # noqa: BLE001 - a corrupt sidecar never kills the lane
        log.warning("seekh sidecar corrupt for %s", _safe(tenant))
        return []


def _save(tenant: str, rows: list[dict[str, Any]]) -> None:
    for r in rows[:-MAX_SIDECAR]:                       # a row that falls off the list takes its kept video with it
        _media_drop(tenant, r)
    p = _sidecar_path(tenant)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(rows[-MAX_SIDECAR:], ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)                                      # atomic: a reader never sees half a file


def listing(tenant: str, limit: int = 20) -> dict[str, Any]:
    """action=status: what was learned from which video, newest first."""
    rows = list(reversed(_load(tenant)))
    return {"watches": rows[:limit], "total": len(rows)}


# ---------------------------------------------------------------- v0.785 the learner's OWN copy of an uploaded video
# An uploaded video rides the chat file lane, which is swept after 24 hours - so the task page could not play it the
# next day and Re-learn failed. The learner now keeps its own copy beside the sidecar (one file per learned row,
# removed with the row, a per-tenant size cap that drops the oldest copies first).
_SIDECAR_LOCK = threading.RLock()
_EXT = {"video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov", "video/x-matroska": ".mkv",
        "video/3gpp": ".3gp", "video/x-msvideo": ".avi", "video/mpeg": ".mpeg", "video/ogg": ".ogv"}


def _media_dir(tenant: str) -> Path:
    p = _dir() / "media" / _safe(tenant)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _media_drop(tenant: str, row: dict[str, Any]) -> None:
    m = (row or {}).get("media") or {}
    if m.get("file"):
        try:
            (_media_dir(tenant) / Path(str(m["file"])).name).unlink(missing_ok=True)
        except Exception:                               # noqa: BLE001
            log.exception("seekh media drop")


def _media_keep(tenant: str, rid: str, stash) -> dict[str, Any] | None:
    """Write the watched bytes under the row's id. Never raises: a copy that cannot be kept is only a lost replay."""
    try:
        from .config import get_settings
        st = get_settings()
        if not stash or not getattr(st, "seekh_keep_media", True):
            return None
        data, mime, name = stash
        cap = int(getattr(st, "seekh_media_max_mb", 1024)) * 1024 * 1024
        if not data or len(data) > cap:
            return None
        ext = _EXT.get(str(mime).split(";")[0].strip().lower()) or (Path(str(name)).suffix.lower()[:6] or ".mp4")
        fn = re.sub(r"[^\w-]", "_", rid)[:60] + (ext if re.fullmatch(r"\.[a-z0-9]{2,5}", ext) else ".mp4")
        d = _media_dir(tenant)
        (d / fn).write_bytes(data)
        return {"file": fn, "mime": str(mime).split(";")[0].strip() or "video/mp4", "name": str(name or "video")[:160],
                "size": len(data)}
    except Exception:                                   # noqa: BLE001
        log.exception("seekh media keep")
        return None


def _media_trim(tenant: str, rows: list[dict[str, Any]]) -> None:
    """The size cap: the oldest kept copies go first (the learned steps stay; only the replay is lost)."""
    from .config import get_settings
    cap = int(getattr(get_settings(), "seekh_media_max_mb", 1024)) * 1024 * 1024
    total = sum(int((r.get("media") or {}).get("size") or 0) for r in rows)
    for r in rows:                                      # rows are oldest first
        if total <= cap:
            break
        if r.get("media"):
            total -= int(r["media"].get("size") or 0)
            _media_drop(tenant, r)
            r.pop("media", None)


def media_file(tenant: str, tid: str) -> tuple[Path, str, str]:
    """(path, mime, name) of the kept video of one of her rows - the page's player and Re-learn read it."""
    for r in _load(tenant):
        if _row_id(r) == tid and (r.get("media") or {}).get("file"):
            p = _media_dir(tenant) / Path(str(r["media"]["file"])).name
            if p.is_file():
                return p, str(r["media"].get("mime") or "video/mp4"), str(r["media"].get("name") or "video")
    raise SeekhError("This video is not kept any more - give its link or upload it again.")


# ---------------------------------------------------------------- stage 2 doors (all existing)
def _perceive_youtube(vid: str, tenant: str) -> str:
    from .youtube import service as ys
    from .youtube.client import watch_url
    try:                                                # best-effort length cap, exactly like ys.watch
        meta = {}
        try:
            meta = ys.video(tenant, [vid])[0]
        except Exception:                               # noqa: BLE001 - no connector / no meta: Gemini judges
            pass
        if int(meta.get("seconds", 0) or 0) > YT_MAX_S:
            raise SeekhError("This video is longer than 3 hours, which is too long to watch.")
        if getattr(_LIVE, "on_text", None) is None:
            return ys.gemini_video(watch_url(vid), _PERCEIVE_ASK)
        from google.genai import Client, types          # v0.745 the same call, streamed so notes show as written
        from .config import get_settings
        st = get_settings()
        text = _stream_text(Client(api_key=st.gemini_api_key), st.youtube_gemini_model,
                            types.Content(parts=[types.Part(file_data=types.FileData(file_uri=watch_url(vid))),
                                                 types.Part(text=_PERCEIVE_ASK)]))
        if not text:
            raise SeekhError("Google could not watch this video (it may be private, age-restricted or very new).")
        return text
    except SeekhError:
        raise
    except Exception as e:                              # noqa: BLE001 - YTError and friends, said plainly
        raise SeekhError(str(e)) from e


def _gemini_watch_bytes(data: bytes, mime: str, ask: str) -> str:
    """The videoedit/brain inline-bytes pattern with our own ask (no JSON mime: free text with [m:ss] stamps)."""
    from .videoedit import brain
    client, model = brain._gemini_client()
    if client is None:
        raise SeekhError("Learning from a video needs GEMINI_API_KEY on the server.")
    from google.genai import types
    try:
        if len(data) <= brain.INLINE_MAX:
            part = types.Part.from_bytes(data=data, mime_type=mime)
        else:
            f = client.files.upload(file=io.BytesIO(data), config={"mime_type": mime})
            for _ in range(90):
                if str(getattr(f.state, "name", f.state)) != "PROCESSING":
                    break
                time.sleep(2)
                f = client.files.get(name=f.name)
            part = types.Part(file_data=types.FileData(file_uri=f.uri, mime_type=mime))
        text = _stream_text(client, model, types.Content(role="user", parts=[part, types.Part(text=ask)]),
                            types.GenerateContentConfig(temperature=0.1, max_output_tokens=8000))
    except SeekhError:
        raise
    except Exception as e:                              # noqa: BLE001
        raise SeekhError(f"Could not watch the video: {e}") from e
    if not text:
        raise SeekhError("Could not watch the video (the file may be broken or too large).")
    return text


def _file_bytes(tenant: str, fid: str) -> tuple[bytes, str, str]:
    from .mailbox import service as ms
    try:
        f = ms._file_row(tenant, str(fid))
    except Exception as e:                              # noqa: BLE001
        raise SeekhError(f"File not found (attach it again): {e}") from e
    data = Path(f.stored_path).read_bytes()
    import mimetypes
    mime = mimetypes.guess_type(f.name)[0] or "video/mp4"
    return data, mime, f.name


def _perceive_file(tenant: str, fid: str, st) -> str:
    from .net import media
    data, mime, name = _file_bytes(tenant, fid)
    if len(data) > int(st.seekh_file_max_mb) * 1024 * 1024:
        raise SeekhError(f"The video is over {st.seekh_file_max_mb} MB - send a shorter part.")
    info = media.analyse(name, mime, data)
    if info.get("media") != "video":
        raise SeekhError("This is not a video file - Hoola can only learn from a video.")
    if float(info.get("duration") or 0) > float(st.seekh_file_max_s):
        raise SeekhError(f"The video is longer than {int(st.seekh_file_max_s) // 60} minutes - send a shorter part.")
    _LIVE.media = (data, mime, name)                    # v0.785 kept beside the learned row (the chat lane is swept)
    return _gemini_watch_bytes(data, mime, _PERCEIVE_ASK)


def _perceive_kept(tenant: str, tid: str, st) -> str:
    """v0.785 Re-learn / Try again from the learner's own copy of an earlier upload."""
    p, mime, name = media_file(tenant, tid)
    data = p.read_bytes()
    _LIVE.media = (data, mime, name)
    return _gemini_watch_bytes(data, mime, _PERCEIVE_ASK)


def _perceive_url(url: str, st) -> str:
    import httpx
    from .agent.scrape_tools import _guard_url, ToolError as AgentToolError
    from .net import media
    try:
        url = _guard_url(url)
    except AgentToolError as e:
        raise SeekhError(str(e)) from e
    max_b = int(st.seekh_file_max_mb) * 1024 * 1024
    try:
        with httpx.Client(follow_redirects=True, timeout=90.0) as c:
            with c.stream("GET", url) as r:
                r.raise_for_status()
                ctype = r.headers.get("content-type", "")
                buf = bytearray()
                for chunk in r.iter_bytes(1 << 16):
                    buf.extend(chunk)
                    if len(buf) > max_b:
                        raise SeekhError(f"The video is over {st.seekh_file_max_mb} MB - send a shorter part.")
        data = bytes(buf)
    except SeekhError:
        raise
    except Exception as e:                              # noqa: BLE001
        raise SeekhError(f"Could not download the video: {e}") from e
    import mimetypes
    mime = ctype.split(";")[0].strip() or mimetypes.guess_type(url.split("?")[0])[0] or "video/mp4"
    info = media.analyse(url.split("?")[0].split("/")[-1] or "v.mp4", mime, data)
    if info.get("media") != "video":
        raise SeekhError("That link is not a video file.")
    if float(info.get("duration") or 0) > float(st.seekh_file_max_s):
        raise SeekhError(f"The video is longer than {int(st.seekh_file_max_s) // 60} minutes - send a shorter part.")
    _LIVE.media = (data, mime, url.split("?")[0].split("/")[-1] or "video.mp4")   # v0.785 plays on the page later
    return _gemini_watch_bytes(data, mime, _PERCEIVE_ASK)


# ---------------------------------------------------------------- stage 3: distill + validate + salvage
def _validate(sk: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    steps = sk.get("steps")
    if not isinstance(steps, list) or not steps:
        problems.append("steps is empty: every step you saw goes in, in order")
        return problems
    for i, s in enumerate(steps, 1):
        ev = s.get("evidence")
        if not isinstance(ev, list) or not ev or not any(_TS.search(str(x)) for x in ev):
            problems.append(f"step {i} has no [m:ss] evidence")
        for k in ("value", "value_hint", "note"):
            if _DIGITS.search(str(s.get(k) or "")):
                problems.append(f"step {i} carries literal digits in {k}")
        if s.get("value") is not None:                    # the law: a filled value is a variable name, never the value
            problems.append(f"step {i} has a literal value instead of value_var")
    try:
        c = float(sk.get("confidence"))
        if not 0.0 <= c <= 1.0:
            problems.append("confidence is outside 0.0-1.0")
    except (TypeError, ValueError):
        problems.append("confidence is missing or not a number")
    if not str(sk.get("title") or "").strip():
        problems.append("title is empty")
    return problems


def _mask_digits(text: Any) -> str:
    return _DIGITS.sub(lambda m: "#" * len(m.group()), str(text or "")).strip()


def _salvage(sk: dict[str, Any]) -> dict[str, Any]:
    """The honest partial: laws enforced deterministically, unproven steps moved to gotchas, digits masked."""
    out: dict[str, Any] = {
        "title": (re.sub(r"\s+", " ", str(sk.get("title") or "")).strip() or "Task learned from a video")[:TITLE_MAX],
        "kind": sk.get("kind") if sk.get("kind") in ("website_work", "other_work") else "other_work",
        "site": _mask_digits(sk.get("site"))[:120] if sk.get("site") else "",
        "start_url": str(sk.get("start_url") or "")[:500],
        "preconditions": [str(x)[:200] for x in (sk.get("preconditions") or [])[:8]],
        "gotchas": [str(x)[:200] for x in (sk.get("gotchas") or [])[:8]],
        "unsure": [str(x)[:200] for x in (sk.get("unsure") or [])[:8]],
        "variables": {},
        "steps": [],
    }
    try:
        c = float(sk.get("confidence"))
    except (TypeError, ValueError):
        c = 0.5
    out["confidence"] = min(1.0, max(0.0, c))
    for name, meta in (sk.get("variables") or {}).items():
        if isinstance(meta, dict) and re.fullmatch(r"[a-z_][a-z0-9_]{0,39}", str(name)):
            out["variables"][name] = {"field": str(meta.get("field", ""))[:120],
                                      "why": str(meta.get("why", ""))[:200]}
    dropped = out["gotchas"]
    for i, s in enumerate(sk.get("steps") or [], 1):
        if not isinstance(s, dict):
            continue
        ev = [str(x) for x in (s.get("evidence") or []) if _TS.search(str(x))][:3]
        note = _mask_digits(s.get("note"))[:LABEL_MAX]
        if not ev:                                      # the evidence law: not provable -> not a step
            what = note or _mask_digits(s.get("value_hint")) or str(s.get("action") or "a step")
            dropped.append(f"not sure (no clear timestamp): {what}")
            out["confidence"] = min(out["confidence"], 0.5)
            continue
        step = {"n": len(out["steps"]) + 1,
                "action": str(s.get("action") or "other")[:24],
                "target": {k: _mask_digits(v)[:120] for k, v in (s.get("target") or {}).items()
                           if k in ("role", "name", "label")} or None,
                "value_hint": _mask_digits(s.get("value_hint"))[:160],
                "evidence": ev, "note": note}
        v = str(s.get("value_var") or "")
        if v and re.fullmatch(r"[a-z_][a-z0-9_]{0,39}", v):
            step["value_var"] = v
        out["steps"].append(step)
    out["gotchas"] = dropped[:10]
    if not out["steps"]:
        raise SeekhError("No clear steps were seen in the video - what was seen is under Watch out.")
    return out


def _distill(text: str) -> dict[str, Any]:
    """One Claude call through the videoedit brain door; one re-ask on validation problems, then the honest
    partial (salvage enforces every law deterministically)."""
    from .videoedit import brain
    problems: list[str] = []
    sk: dict[str, Any] = {}
    for _attempt in (1, 2):
        sk = brain.think(_DISTILL_SYSTEM, _DISTILL_PROMPT.format(
            perception=str(text or "")[:24000],
            problems=("\n".join(f"- {p}" for p in problems) if problems else "none")), max_tokens=6000)
        if not sk:
            break
        problems = _validate(sk)
        if not problems:
            return _salvage(sk)
    if not sk:
        raise SeekhError("Could not turn the video into steps (try again in a little while).")
    return _salvage(sk)


# ---------------------------------------------------------------- stage 4: the two memories
def _save_procedure(tenant: str, sk: dict[str, Any], ref: str) -> dict[str, Any]:
    from . import procedures as pr
    labels = []
    for s in sk["steps"]:
        label = f"{s.get('n')}. {s.get('action')}: {s.get('note') or s.get('value_hint') or ''} [{s.get('evidence', [''])[0]}]"
        labels.append({"tool": "", "label": label[:LABEL_MAX]})
    steps = labels
    watch_out = [f"precondition: {x}" for x in sk["preconditions"][:3]] + sk["gotchas"][:5]
    trigger = f"seekh: video {sk['title']}"
    return pr.save_video(tenant, sk["title"], trigger, steps, watch_out)


def _operator_home(tenant: str) -> Path:
    """The operator's own home (operator/service.home, replicated so seekh never imports the operator stack)."""
    p = Path("data") / "operator" / _safe(tenant)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _recipe_name(title: str) -> str:
    return re.sub(r"\s+", " ", str(title or "")).strip()[:60] or "Video lesson"


def _save_recipe_draft(tenant: str, sk: dict[str, Any], source: str) -> dict[str, Any]:
    """A DRAFT in the operator's own recipe format (Memory.save: versioned, .vN backup, runs preserved).
    A draft never overwrites a proven recipe (runs > 0): it goes beside it as '<name> (video)'."""
    from .operator.memory import Memory
    mem = Memory(_operator_home(tenant))
    name = _recipe_name(sk["title"])
    p = mem.recipe_path(name)
    if p.exists():
        try:
            if int(json.loads(p.read_text(encoding="utf-8")).get("runs", 0) or 0) > 0:
                name = f"{name} (video)"[:60]
        except Exception:                               # noqa: BLE001 - unreadable old file: overwrite as new
            pass
    steps = []
    for i, s in enumerate(sk["steps"]):
        st = {"action": s["action"], "target": s.get("target") or {}, "evidence": s.get("evidence")}
        if s.get("value_var"):
            st["value"] = "{" + s["value_var"] + "}"
        if i == 0 and sk.get("start_url"):
            st["url"] = sk["start_url"]
        steps.append(st)
    r = {"name": name, "task": sk["title"], "site": sk.get("site", ""), "start_url": sk.get("start_url", ""),
         "created": dt.datetime.now().isoformat(timespec="seconds"), "steps": steps,
         "variables": {k: {"field": v.get("field", ""), "action": "fill"} for k, v in sk["variables"].items()},
         "human_steps": 0,
         "notes": f"DRAFT learned from a video ({source}); never run yet - every step is checked against the "
                  f"live page, the first good run replaces this with reality",
         "runs": 0, "draft": True}
    return mem.save(r)


# ---------------------------------------------------------------- the pipeline
def _emit(on_stage, stage: str, data: dict[str, Any] | None = None) -> None:
    """v0.718: the console lane's progress door - a no-op for every existing caller (the tool, the tests)."""
    try:
        if on_stage:
            on_stage(stage, data or {})                        # never let a UI sink break the watch
    except Exception:                                       # noqa: BLE001
        log.exception("seekh on_stage %s failed", stage)


def watch(tenant: str, ref: str, title: str = "", actor: str = "owner",
          on_stage=None, cancel: "threading.Event | None" = None, replace: str = "") -> dict[str, Any]:
    """v0.745: the live notes sink + Stop flag wrap the v0.713 pipeline below.
    v0.785: `replace` = the row this watch re-learns (Re-learn / Try again): on success the old row, its learned
    procedure and its never-run recipe draft are retired, so her list never holds the same task twice."""
    from .config import get_settings
    live = bool(on_stage) and bool(getattr(get_settings(), "seekh_live_notes", True))
    _LIVE.on_text = (lambda acc: _emit(on_stage, "partial", {"perception": acc})) if live else None
    _LIVE.cancel = cancel
    _LIVE.media = None
    try:
        return _watch(tenant, ref, title, actor, on_stage, replace)
    except Exception as e:
        if not isinstance(e, SeekhStopped):             # a failed watch keeps its upload for Try again
            try:
                e.media = getattr(_LIVE, "media", None)
            except Exception:                           # noqa: BLE001
                pass
        raise
    finally:
        _LIVE.on_text = None
        _LIVE.cancel = None
        _LIVE.media = None


def _retire(tenant: str, row: dict[str, Any], keep_recipe: str = "") -> None:
    """Take one row's belongings away: its learned procedure, a recipe draft that never ran, its kept video.
    A recipe that has really run is hers and stays."""
    if row.get("procedure_id"):
        from . import procedures as pr
        try:
            pr.delete(tenant, row["procedure_id"])
        except Exception:                               # noqa: BLE001 - already gone is fine
            pass
    if row.get("recipe") and row.get("recipe") != keep_recipe:
        try:
            from .operator.memory import Memory
            p = Memory(_operator_home(tenant)).recipe_path(row["recipe"])
            if p.exists() and int(json.loads(p.read_text(encoding="utf-8")).get("runs", 0) or 0) == 0:
                p.unlink()
        except Exception:                               # noqa: BLE001
            log.exception("seekh retire recipe")
    _media_drop(tenant, row)


def _watch(tenant: str, ref: str, title: str = "", actor: str = "owner",
           on_stage=None, replace: str = "") -> dict[str, Any]:
    """Watch one video and keep its way of working. Raises SeekhError honestly; never fakes a step.
    on_stage(stage, data) is called at every real pipeline boundary so a UI can show live progress:
    classify -> fetch -> notes (the perception text) -> distill_start -> distill (the salvaged recipe)
    -> memory (procedure + recipe names) -> done (the result)."""
    from .config import get_settings
    st = get_settings()
    if not st.seekh_enabled:
        raise SeekhError("Learning from videos is switched off on this server.")
    if (actor or "owner") != "owner":
        raise SeekhError("Only the owner can teach Hoola from a video.")
    kind, key = _classify(ref)
    _emit(on_stage, "classify", {"kind": kind, "key": str(key)[:200]})
    today = dt.date.today().isoformat()
    before = _load(tenant)
    if sum(1 for r in before if str(r.get("day", "")) == today and r.get("status") != "failed") \
            >= int(st.seekh_max_per_day):
        raise SeekhError(f"{st.seekh_max_per_day} videos already learned today - try again tomorrow.")
    source = f"{kind}:{key}"[:200]
    if kind == "kept":                                  # the row keeps the label of where the video first came from
        was = next((r for r in before if _row_id(r) == key), None)
        source = str((was or {}).get("source") or "file:kept")[:200]
        if source.startswith("kept:"):
            source = "file:kept"
    _emit(on_stage, "fetch", {"kind": kind})
    if kind == "youtube":
        perception = _perceive_youtube(key, tenant)
    elif kind == "file":
        perception = _perceive_file(tenant, key, st)
    elif kind == "kept":
        perception = _perceive_kept(tenant, key, st)
    else:
        perception = _perceive_url(key, st)
    _check_stop()
    _emit(on_stage, "notes", {"perception": perception})
    _emit(on_stage, "distill_start", {})
    sk = _distill(perception)
    _check_stop()
    _emit(on_stage, "distill", {"steps": len(sk["steps"]), "title": sk["title"]})
    if str(title or "").strip():
        sk["title"] = re.sub(r"\s+", " ", str(title)).strip()[:TITLE_MAX]
    proc = _save_procedure(tenant, sk, ref)
    recipe = ""
    if sk["kind"] == "website_work":
        try:
            recipe = _save_recipe_draft(tenant, sk, source)["name"]
        except Exception:                               # noqa: BLE001 - the procedure stands without it
            log.exception("seekh recipe draft failed")
    _emit(on_stage, "memory", {"procedure_id": proc["id"], "recipe": recipe})
    row = {"id": proc["id"], "status": "learned",
           "ts": dt.datetime.now().isoformat(timespec="seconds"), "day": today,
           "source": source, "title": sk["title"], "procedure_id": proc["id"],
           "recipe": recipe, "steps": len(sk["steps"]), "confidence": sk["confidence"],
           "kind": sk["kind"], "site": sk.get("site", ""), "wins": 0, "fails": 0,
           # v0.745 the task page reads these (values are hints / variable names, never her data)
           "detail": {"steps": [{"n": x.get("n"), "action": x.get("action"), "note": x.get("note", ""),
                                 "evidence": x.get("evidence", []), "value_hint": x.get("value_hint", ""),
                                 "value_var": x.get("value_var", "")} for x in sk["steps"]],
                      "preconditions": sk["preconditions"], "gotchas": sk["gotchas"],
                      "unsure": sk["unsure"], "start_url": sk.get("start_url", "")}}
    old = None
    with _SIDECAR_LOCK:
        rows = _load(tenant)
        if replace:
            old = next((r for r in rows if _row_id(r) == replace and _row_id(r) != row["id"]), None)
        media = _media_keep(tenant, row["id"], getattr(_LIVE, "media", None))
        if media:
            row["media"] = media
        if old is not None:                             # v0.785 Re-learn REPLACES: the old row leaves the list
            rows = [r for r in rows if r is not old]
            row["relearned"] = int(old.get("relearned") or 0) + 1
        rows.append(row)
        _media_trim(tenant, rows)
        _save(tenant, rows)
    if old is not None:
        _retire(tenant, old, keep_recipe=recipe)
    out = {"learned": sk["title"], "kind": sk["kind"], "site": sk["site"], "procedure_id": proc["id"],
            "id": proc["id"], "replaced": _row_id(old) if old is not None else "",
            "recipe": recipe,
            "steps": [{"n": s.get("n"), "action": s.get("action"), "note": s.get("note", ""),
                       "evidence": s.get("evidence", []), "value_hint": s.get("value_hint", "")}
                      for s in sk["steps"]],
            "preconditions": sk["preconditions"], "gotchas": sk["gotchas"], "unsure": sk["unsure"],
            "confidence": sk["confidence"], "source": source,
            "say": "Learned - it is in your learned tasks and comes back by itself when you ask for this kind of "
                   "work. So far it has only been watched: it counts as proven once it has worked for real.",
            "note_for_you": "Learned is NOT proven: until one real run has worked, say exactly that. Tell her "
                            "the steps with their timestamps, the gotchas and what you are unsure about. For "
                            "website work the operator may use the draft as a guide, checking every step "
                            "against the live page."}
    _emit(on_stage, "done", {"learned": out["learned"]})
    return out


# ---------------------------------------------------------------- v0.745 the learner page's own doors
def _row_id(r: dict[str, Any]) -> str:
    return str(r.get("id") or r.get("procedure_id") or "")


def record_failure(tenant: str, ref: str, title: str, error: str, media=None, replace: str = "") -> dict[str, Any]:
    """A watch that could not learn stays on her list with its reason and Try again (never counts toward today).
    v0.785: an uploaded video is kept with the row, so Try again still works after the chat lane is swept; a
    retry that fails again replaces its own earlier failure row (never a learned task)."""
    try:
        kind, key = _classify(ref)
        source = f"{kind}:{key}"[:200]
    except SeekhError:
        kind, key, source = "", "", str(ref or "")[:200]
    row = {"id": "f" + uuid.uuid4().hex[:12], "status": "failed", "ts": dt.datetime.now().isoformat(timespec="seconds"),
           "day": dt.date.today().isoformat(), "source": source, "ref": str(ref or "")[:300],
           "title": re.sub(r"\s+", " ", str(title or "")).strip()[:TITLE_MAX], "error": str(error or "")[:300],
           "steps": 0, "confidence": 0}
    old = None
    with _SIDECAR_LOCK:
        rows = _load(tenant)
        if replace:
            old = next((r for r in rows if _row_id(r) == replace and r.get("status") == "failed"), None)
        if kind == "kept":
            was = next((r for r in rows if _row_id(r) == key), None)
            if was is not None and was.get("status") != "failed":
                media = None                            # a learned task keeps its own copy: Try again reads that one
                row["source"] = str(was.get("source") or source)[:200]
            elif was is not None:
                row["source"] = str(was.get("source") or source)[:200]
        kept = _media_keep(tenant, row["id"], media) if media else None
        if kept:
            row["media"] = kept
            row["ref"] = f"kept:{row['id']}"
        if old is not None:
            rows = [r for r in rows if r is not old]
        rows.append(row)
        _media_trim(tenant, rows)
        _save(tenant, rows)
    if old is not None:
        _media_drop(tenant, old)
    return row


def task(tenant: str, tid: str) -> dict[str, Any]:
    """One learned task with everything the task page shows. Older rows (before v0.745) carry no detail: their
    steps come back from the learned procedure's own labels."""
    for r in _load(tenant):
        if _row_id(r) == tid:
            out = dict(r)
            if not out.get("detail") and out.get("procedure_id"):
                from . import procedures as pr
                p = next((x for x in pr.listing(tenant) if x.get("id") == out["procedure_id"]), None)
                if p:
                    steps = []
                    for i, st in enumerate(p.get("steps") or []):
                        lab = str((st or {}).get("label") or "")
                        m = re.search(r"\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*$", lab)
                        steps.append({"n": i + 1, "action": "", "note": re.sub(r"^\d+\.\s*\w*:\s*|\s*\[[^\]]*\]\s*$", "", lab),
                                      "evidence": [m.group(1)] if m else [], "value_hint": ""})
                    out["detail"] = {"steps": steps, "preconditions": [], "gotchas": p.get("watch_out") or [],
                                     "unsure": []}
            return out
    raise SeekhError("That learned task was not found.")


def forget(tenant: str, tid: str) -> bool:
    """Remove a task from her list, its learned procedure, its never-run recipe draft and its kept video. A
    recipe that has really run is hers and stays."""
    with _SIDECAR_LOCK:
        rows = _load(tenant)
        hit = next((r for r in rows if _row_id(r) == tid), None)
        if hit is None:
            raise SeekhError("That learned task was not found.")
        _save(tenant, [r for r in rows if r is not hit])
    _retire(tenant, hit)
    return True


def mark(tenant: str, tid: str, ok: bool, skip: bool = False) -> dict[str, Any]:
    """Her answer after a run: worked -> one more win (Proven), wrong -> one fail. Also scored on the learned
    procedure so the chat's own hints learn the same. v0.785: the open run is closed here; a run the operator
    already counted as a win is never counted twice (and "wrong" takes that win back); skip = close it unscored."""
    undo = False
    with _SIDECAR_LOCK:
        rows = _load(tenant)
        hit = next((r for r in rows if _row_id(r) == tid), None)
        if hit is None or hit.get("status") == "failed":
            raise SeekhError("That learned task was not found.")
        run = hit.pop("run", None) or {}
        scored = bool(run.get("scored"))
        if skip:
            _save(tenant, rows)
            return hit
        if scored and ok:                               # the operator's own finish already made it Proven
            hit["proven_by"] = "you"
            _save(tenant, rows)
            return hit
        if scored and not ok:
            hit["wins"] = max(0, int(hit.get("wins") or 0) - 1)
            undo = True
        key = "wins" if ok else "fails"
        hit[key] = int(hit.get(key) or 0) + 1
        if ok:
            hit["proven_by"] = "you"
        hit["last_run"] = dt.datetime.now().isoformat(timespec="seconds")
        _save(tenant, rows)
    if hit.get("procedure_id"):
        from . import procedures as pr
        try:
            pr.record_run(tenant, hit["procedure_id"], ok, undo_win=undo)
        except Exception:                               # noqa: BLE001
            log.exception("seekh mark procedure")
    return hit


# ---------------------------------------------------------------- v0.785 the run: kept on the server, proven by real work
RUN_STALE_H = 12            # a run nobody answered: the page stops asking "Did it work?" after this


def run_start(tenant: str, tid: str, cid: str, after: int = 0) -> dict[str, Any]:
    """Do it now was sent: remember which chat carries this run, so leaving the page (or a reload) loses nothing -
    the task shows "Hoola is doing it" / "Did it work?" until she answers."""
    with _SIDECAR_LOCK:
        rows = _load(tenant)
        hit = next((r for r in rows if _row_id(r) == tid), None)
        if hit is None or hit.get("status") == "failed":
            raise SeekhError("That learned task was not found.")
        hit["run"] = {"cid": str(cid or "")[:80], "after": int(after or 0), "scored": False,
                      "ts": dt.datetime.now().isoformat(timespec="seconds")}
        _save(tenant, rows)
        return hit


def run_view(tenant: str, tid: str) -> dict[str, Any]:
    """The open run of one task + the cards of ITS chat that really wait for her right now (their own latest
    state, the same check the chat itself uses)."""
    hit = next((r for r in _load(tenant) if _row_id(r) == tid), None)
    if hit is None:
        raise SeekhError("That learned task was not found.")
    run = dict(hit.get("run") or {})
    waiting: list[dict[str, Any]] = []
    if run.get("cid"):
        try:
            from . import events
            waiting = [{"id": w["id"], "kind": w["kind"], "title": w["title"]}
                       for w in events.waiting_cards(tenant, 6, conversation_id=run["cid"])
                       if int(w["id"]) > int(run.get("after") or 0)]
        except Exception:                               # noqa: BLE001 - the page falls back to "Open in chat"
            log.exception("seekh run cards")
    busy = False                                        # is Hoola still on it? (the chat turn, or its browser job)
    if run.get("cid"):
        try:
            from .agent.santosh import turn_running
            busy = bool(turn_running(run["cid"]))
        except Exception:                               # noqa: BLE001
            pass
        if not busy:
            try:
                from sqlalchemy import select
                from .db import session
                from .operator.models import OperatorTask
                with session() as s:
                    busy = s.scalars(select(OperatorTask.id).where(
                        OperatorTask.tenant_id == tenant, OperatorTask.conversation_id == run["cid"],
                        OperatorTask.status.in_(("queued", "running", "waiting")))).first() is not None
            except Exception:                           # noqa: BLE001
                pass
    return {"id": tid, "run": run or None, "waiting": waiting, "busy": busy, "wins": int(hit.get("wins") or 0),
            "fails": int(hit.get("fails") or 0), "proven_by": hit.get("proven_by", "")}


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]{3,}", str(text or "").lower())}


def operator_done(tenant: str, task: str, recipe: "str | list[str]" = "", conversation_id: str = "") -> str:
    """Called when a computer-operator job FINISHES WELL. A learned task that this job was doing becomes Proven by
    the real work itself - asked from this page or from the chat. Matching, strongest first: the open run of that
    chat; the recipe the job saved or ran; the task's own title inside the job's words. Returns the row id."""
    hit_id, pid = "", ""
    with _SIDECAR_LOCK:
        rows = _load(tenant)
        live = [r for r in rows if r.get("status") != "failed" and (r.get("kind") in ("website_work", None, ""))]
        hit = next((r for r in live if conversation_id and (r.get("run") or {}).get("cid") == conversation_id
                    and not (r.get("run") or {}).get("scored")), None)
        names = {str(x) for x in ([recipe] if isinstance(recipe, str) else list(recipe or [])) if x}
        if hit is None and names:
            hit = next((r for r in live if r.get("recipe") and r.get("recipe") in names), None)
        if hit is None:
            q = _words(task)
            best = 0.0
            for r in live:
                t = _words(r.get("title"))
                score = len(t & q) / len(t) if len(t) >= 2 else 0.0
                if score >= 0.6 and score > best:
                    hit, best = r, score
        if hit is None:
            return ""
        hit["wins"] = int(hit.get("wins") or 0) + 1
        hit["last_run"] = dt.datetime.now().isoformat(timespec="seconds")
        hit.setdefault("proven_by", "run")
        if hit.get("run"):
            hit["run"]["scored"] = True
        _save(tenant, rows)
        hit_id, pid = _row_id(hit), str(hit.get("procedure_id") or "")
    if pid:
        from . import procedures as pr
        try:
            pr.record_run(tenant, pid, True)
        except Exception:                               # noqa: BLE001
            log.exception("seekh operator_done procedure")
    return hit_id
