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
import time
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
    """Honest failure: what is missing, in her language."""


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
        raise SeekhError("Kaunsa video? YouTube ka link, chat mein attach kiye video ka file_id, ya direct video URL dijiye.")
    from .youtube.client import video_id
    vid = video_id(r)
    if vid:
        return "youtube", vid
    if r.lower().startswith(("http://", "https://")):
        return "url", r
    if re.fullmatch(r"[\w.-]{4,180}", r):
        return "file", r
    raise SeekhError("Yeh video samajh nahi aaya: YouTube link, video file ka file_id, ya direct video URL dijiye.")


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
    _sidecar_path(tenant).write_text(json.dumps(rows[-MAX_SIDECAR:], ensure_ascii=False, indent=1),
                                     encoding="utf-8")


def listing(tenant: str, limit: int = 20) -> dict[str, Any]:
    """action=status: what was learned from which video, newest first."""
    rows = list(reversed(_load(tenant)))
    return {"watches": rows[:limit], "total": len(rows)}


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
            raise SeekhError("Yeh video 3 ghante se lamba hai; itna lamba video nahi dekh sakte.")
        return ys.gemini_video(watch_url(vid), _PERCEIVE_ASK)
    except SeekhError:
        raise
    except Exception as e:                              # noqa: BLE001 - YTError and friends, said plainly
        raise SeekhError(str(e)) from e


def _gemini_watch_bytes(data: bytes, mime: str, ask: str) -> str:
    """The videoedit/brain inline-bytes pattern with our own ask (no JSON mime: free text with [m:ss] stamps)."""
    from .videoedit import brain
    client, model = brain._gemini_client()
    if client is None:
        raise SeekhError("Video dekh kar seekhne ke liye server par GEMINI_API_KEY chahiye.")
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
        r = client.models.generate_content(
            model=model, contents=types.Content(role="user", parts=[part, types.Part(text=ask)]),
            config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=8000))
        text = (r.text or "").strip()
    except Exception as e:                              # noqa: BLE001
        raise SeekhError(f"Video nahi dekh paya: {e}") from e
    if not text:
        raise SeekhError("Video nahi dekh paya (file kharab ya bahut badi ho sakti hai).")
    return text


def _file_bytes(tenant: str, fid: str) -> tuple[bytes, str, str]:
    from .mailbox import service as ms
    try:
        f = ms._file_row(tenant, str(fid))
    except Exception as e:                              # noqa: BLE001
        raise SeekhError(f"File nahi mili (chat mein attach kijiye): {e}") from e
    data = Path(f.stored_path).read_bytes()
    import mimetypes
    mime = mimetypes.guess_type(f.name)[0] or "video/mp4"
    return data, mime, f.name


def _perceive_file(tenant: str, fid: str, st) -> str:
    from .net import media
    data, mime, name = _file_bytes(tenant, fid)
    if len(data) > int(st.seekh_file_max_mb) * 1024 * 1024:
        raise SeekhError(f"Video {st.seekh_file_max_mb} MB se badi hai - chhota hissa bhejiye.")
    info = media.analyse(name, mime, data)
    if info.get("media") != "video":
        raise SeekhError("Yeh video file nahi lag rahi - sirf video se seekha ja sakta hai.")
    if float(info.get("duration") or 0) > float(st.seekh_file_max_s):
        raise SeekhError(f"Video {int(st.seekh_file_max_s) // 60} minute se lambi hai - chhota hissa bhejiye.")
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
                        raise SeekhError(f"Video {st.seekh_file_max_mb} MB se badi hai - chhota hissa bhejiye.")
        data = bytes(buf)
    except SeekhError:
        raise
    except Exception as e:                              # noqa: BLE001
        raise SeekhError(f"Video download nahi ho paya: {e}") from e
    import mimetypes
    mime = ctype.split(";")[0].strip() or mimetypes.guess_type(url.split("?")[0])[0] or "video/mp4"
    info = media.analyse(url.split("?")[0].split("/")[-1] or "v.mp4", mime, data)
    if info.get("media") != "video":
        raise SeekhError("Yeh link video file nahi nikla.")
    if float(info.get("duration") or 0) > float(st.seekh_file_max_s):
        raise SeekhError(f"Video {int(st.seekh_file_max_s) // 60} minute se lambi hai - chhota hissa bhejiye.")
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
        "title": (re.sub(r"\s+", " ", str(sk.get("title") or "")).strip() or "Video se seekha kaam")[:TITLE_MAX],
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
        raise SeekhError("Video mein koi saaf kaam ke steps nahi dikhe - jo dikha woh gotchas mein hai.")
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
        raise SeekhError("Video dekh kar steps nahi bana paya (thodi der baad try kijiye).")
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
    return re.sub(r"\s+", " ", str(title or "")).strip()[:60] or "Video seekh"


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
    """v0.716: the console lane's progress door - a no-op for every existing caller (the tool, the tests)."""
    try:
        if on_stage:
            on_stage(stage, data or {})                        # never let a UI sink break the watch
    except Exception:                                       # noqa: BLE001
        log.exception("seekh on_stage %s failed", stage)


def watch(tenant: str, ref: str, title: str = "", actor: str = "owner",
          on_stage=None) -> dict[str, Any]:
    """Watch one video and keep its way of working. Raises SeekhError honestly; never fakes a step.
    on_stage(stage, data) is called at every real pipeline boundary so a UI can show live progress:
    classify -> fetch -> notes (the perception text) -> distill_start -> distill (the salvaged recipe)
    -> memory (procedure + recipe names) -> done (the result)."""
    from .config import get_settings
    st = get_settings()
    if not st.seekh_enabled:
        raise SeekhError("Video se seekhna abhi band hai.")
    if (actor or "owner") != "owner":
        raise SeekhError("Sirf owner ka bheja video seekha ja sakta hai.")
    kind, key = _classify(ref)
    _emit(on_stage, "classify", {"kind": kind, "key": str(key)[:200]})
    today = dt.date.today().isoformat()
    if sum(1 for r in _load(tenant) if str(r.get("day", "")) == today) >= int(st.seekh_max_per_day):
        raise SeekhError(f"Aaj ke liye {st.seekh_max_per_day} video seekh liye - kal phir try kijiye.")
    _emit(on_stage, "fetch", {"kind": kind})
    if kind == "youtube":
        perception = _perceive_youtube(key, tenant)
    elif kind == "file":
        perception = _perceive_file(tenant, key, st)
    else:
        perception = _perceive_url(key, st)
    _emit(on_stage, "notes", {"perception": perception})
    _emit(on_stage, "distill_start", {})
    sk = _distill(perception)
    _emit(on_stage, "distill", {"steps": len(sk["steps"]), "title": sk["title"]})
    if str(title or "").strip():
        sk["title"] = re.sub(r"\s+", " ", str(title)).strip()[:TITLE_MAX]
    proc = _save_procedure(tenant, sk, ref)
    recipe = ""
    if sk["kind"] == "website_work":
        try:
            recipe = _save_recipe_draft(tenant, sk, f"{kind}:{key}")["name"]
        except Exception:                               # noqa: BLE001 - the procedure stands without it
            log.exception("seekh recipe draft failed")
    _emit(on_stage, "memory", {"procedure_id": proc["id"], "recipe": recipe})
    rows = _load(tenant)
    rows.append({"ts": dt.datetime.now().isoformat(timespec="seconds"), "day": today,
                 "source": f"{kind}:{key}"[:200], "title": sk["title"], "procedure_id": proc["id"],
                 "recipe": recipe, "steps": len(sk["steps"]), "confidence": sk["confidence"]})
    _save(tenant, rows)
    out = {"learned": sk["title"], "kind": sk["kind"], "site": sk["site"], "procedure_id": proc["id"],
            "recipe": recipe,
            "steps": [{"n": s.get("n"), "action": s.get("action"), "note": s.get("note", ""),
                       "evidence": s.get("evidence", []), "value_hint": s.get("value_hint", "")}
                      for s in sk["steps"]],
            "preconditions": sk["preconditions"], "gotchas": sk["gotchas"], "unsure": sk["unsure"],
            "confidence": sk["confidence"], "source": f"{kind}:{key}"[:200],
            "say": "Seekh liya - yeh 'Seekhe hue kaam' mein hai aur jab aap aisa kaam kahenge to khud yaad "
                   "aayega. Abhi tak sirf dekha hai: pehle ek baar sahi se chal ke dekhein, tab hi pakka "
                   "maanenge.",
            "note_for_you": "Learned is NOT proven: until one real run has worked, say exactly that. Tell her "
                            "the steps with their timestamps, the gotchas and what you are unsure about. For "
                            "website work the operator may use the draft as a guide, checking every step "
                            "against the live page."}
    _emit(on_stage, "done", {"learned": out["learned"]})
    return out
