"""v0.999.142 DIALOGUE, PREMIUM (owner: the Dialogue design canvas -> "GO BUILD").

The pieces of a talk that a single mixed file cannot give by itself:

- every line's start and end (measured when the talk is made Line by line; shared out by length in a natural take,
  and said to be an estimate),
- a pause after a line and a line that cuts in over the one before (exact in Line by line; a written hint in a
  natural take, because the engine makes that one recording itself),
- each line's own recording kept beside a Line-by-line talk, so one line can be made again without the others, and
  so each voice can be given on its own track,
- subtitles from the line times,
- for a script written from a document: the page a line came from, and a check that every figure written in digits
  is in the document.

Nothing here calls an engine except remaking one line, which uses the same speaking path as the whole talk.
"""
from __future__ import annotations

import io
import json
import re
import shutil
import zipfile
from array import array
from pathlib import Path
from typing import Any

from . import gvoice as GV
from . import service as V

PAUSE_MAX = 3.0            # the longest pause she can put after one line, in seconds
CUT_S = 0.35               # how far a line that cuts in starts before the last one ends
CUT_SHARE = 0.4            # ...never more than this share of the line it cuts into


def line_opts(x: dict[str, Any]) -> tuple[float, bool]:
    """(pause after the line in seconds, whether the line cuts in over the one before) from one line of the page."""
    try:
        p = float(x.get("pause") or 0)
    except (TypeError, ValueError):
        p = 0.0
    return max(0.0, min(PAUSE_MAX, round(p, 2))), bool(x.get("cut"))


def natural_text(rows: list[tuple[str, str]], opts: list[tuple[float, bool]]) -> list[tuple[str, str]]:
    """A natural take is one recording the engine makes itself, so a pause or a cut-in can only be written in:
    an ellipsis after a line that is followed by a pause, a dash on a line that is cut off, and [interrupting]
    at the start of the line that cuts in."""
    out = []
    for i, (s, t) in enumerate(rows):
        pause, _ = opts[i]
        nxt_cut = i + 1 < len(rows) and opts[i + 1][1]
        t = t.rstrip()
        if nxt_cut:
            t = re.sub(r"[.!?…]+$", "", t) + " —"
        elif pause >= 0.5:
            t = t + " …"
        if opts[i][1] and i > 0:
            t = "[interrupting] " + t
        out.append((s, t))
    return out


def _samples(fmt: tuple[int, int, int], frames: bytes) -> array:
    a = array("h")
    a.frombytes(frames[: len(frames) - len(frames) % 2])
    return a


def join_timed(parts: list[bytes], gaps: list[float], cuts: list[bool]) -> tuple[bytes, list[tuple[float, float]]]:
    """Line recordings -> one WAV, `gaps[i]` seconds of quiet after line i, a line with `cuts[i]` starting a moment
    before the one before it ends (the two mixed). Returns (wav, [(start, end) seconds per line])."""
    if not parts:
        raise V.VocalError("Nothing was spoken.")
    fmt, first = V._wav_info(parts[0])
    frs = [first]
    for p in parts[1:]:
        f2, fr = V._wav_info(p)
        if f2 != fmt and fmt[0] == 1 and fmt[1] == 2:
            f2, fr = V._wav_info(V._resample(p, fmt[2]))
        if f2 != fmt:
            raise V.VocalError("Two voices came back in different sound formats, so they cannot be joined. Use voices of one kind.")
        frs.append(fr)
    ch, width, rate = fmt
    if width != 2:                                  # not 16-bit: join plainly, no overlap
        times, t = [], 0.0
        for i, fr in enumerate(frs):
            n = len(fr) / (ch * width * rate)
            times.append((round(t, 3), round(t + n, 3)))
            t += n + (gaps[i] if i < len(gaps) else 0)
        quiet = [b"\x00" * (int(rate * (gaps[i] if i < len(gaps) else 0)) * ch * width) for i in range(len(frs))]
        return V._wav(fmt, b"".join(fr + quiet[i] for i, fr in enumerate(frs[:-1])) + frs[-1]), times
    out = array("h")
    times: list[tuple[float, float]] = []
    prev_start = prev_end = 0
    for i, fr in enumerate(frs):
        s = _samples(fmt, fr)
        n = len(s)
        if i == 0:
            st = 0
        else:
            st = prev_end + int(rate * (gaps[i - 1] if i - 1 < len(gaps) else 0)) * ch
            if i < len(cuts) and cuts[i]:
                lap = min(int(rate * CUT_S) * ch, int((prev_end - prev_start) * CUT_SHARE))
                st = max(prev_start, prev_end - lap)
        need = st + n
        if len(out) < need:
            out.extend(array("h", bytes(2 * (need - len(out)))))
        old_end = min(prev_end, need) if i else 0
        for k in range(st, max(st, old_end)):      # the overlap: the two voices added, kept in range
            v = out[k] + s[k - st]
            out[k] = 32767 if v > 32767 else (-32768 if v < -32768 else v)
        if old_end < need:
            a = max(st, old_end)
            out[a:need] = s[a - st:]
        times.append((round(st / (ch * rate), 3), round(need / (ch * rate), 3)))
        prev_start, prev_end = st, max(prev_end, need)
    return V._wav(fmt, out.tobytes()), times


def estimate_times(rows: list[tuple[str, str]], total: float) -> list[tuple[float, float]]:
    """A natural take is one recording, so each line's place is shared out by its length (an estimate)."""
    w = [len(GV.strip_feelings(t)) + 12 for _, t in rows]
    s = sum(w) or 1
    out, t = [], 0.0
    for x in w:
        d = total * x / s
        out.append((round(t, 2), round(t + d, 2)))
        t += d
    return out


# ---------------------------------------------------------------- the kept line recordings
def parts_dir(tenant: str, hid: str) -> Path:
    return V._home(tenant) / "parts" / hid


def keep_parts(tenant: str, hid: str, parts: list[bytes]) -> None:
    d = parts_dir(tenant, hid)
    d.mkdir(parents=True, exist_ok=True)
    for i, p in enumerate(parts):
        (d / f"{i:03d}.wav").write_bytes(p)


def drop_parts(tenant: str, hid: str) -> None:
    if re.fullmatch(r"vo_[0-9a-f]{12}", hid or ""):
        shutil.rmtree(parts_dir(tenant, hid), ignore_errors=True)


def _row(tenant: str, hid: str) -> dict[str, Any]:
    h = next((x for x in V._load(tenant)["history"] if x["id"] == hid), None)
    if not h or h.get("kind") != "dialogue":
        raise V.VocalError("That talk was not found.")
    return h


def _parts(tenant: str, h: dict[str, Any]) -> list[bytes]:
    segs = h.get("segments") or []
    d = parts_dir(tenant, h["id"])
    files = [d / f"{i:03d}.wav" for i in range(len(segs))]
    if h.get("mode") != "lines" or not segs or not all(f.is_file() for f in files):
        raise V.VocalError("A natural take is one recording made by the engine, so its voices and lines cannot be taken "
                           "apart. Make the talk Line by line to change one line or get each voice on its own track.")
    return [f.read_bytes() for f in files]


def _gaps_cuts(segs: list[dict[str, Any]]) -> tuple[list[float], list[bool]]:
    return [V.LINE_GAP_S + float(x.get("pause") or 0) for x in segs], [bool(x.get("cut")) for x in segs]


def _base_name(h: dict[str, Any]) -> str:
    return re.sub(r"[^\w .,-]+", "", str(h.get("title") or "Talk"))[:50].strip() or "Talk"


def stems(tenant: str, hid: str) -> tuple[bytes, str]:
    """Each voice of a Line-by-line talk on its own track, the full length of the talk, quiet where the others speak.
    Returns (zip bytes, file name)."""
    h = _row(tenant, hid)
    parts = _parts(tenant, h)
    segs = h["segments"]
    fmt, _ = V._wav_info(parts[0])
    ch, width, rate = fmt
    total = int(round(max(float(x.get("end") or 0) for x in segs) * rate)) * ch + rate * ch
    who = list(dict.fromkeys(x["speaker"] for x in segs))
    zb = io.BytesIO()
    with zipfile.ZipFile(zb, "w", zipfile.ZIP_DEFLATED) as z:
        for k, w in enumerate(who, 1):
            buf = bytearray(total * width)
            for x, p in zip(segs, parts):
                if x["speaker"] != w:
                    continue
                f2, fr = V._wav_info(p)
                if f2 != fmt:
                    f2, fr = V._wav_info(V._resample(p, rate))
                at = int(round(float(x.get("start") or 0) * rate)) * ch * width
                end = min(len(buf), at + len(fr))
                buf[at:end] = fr[: end - at]
            z.writestr(f"{k:02d} {re.sub(r'[^\w -]+', '', w) or 'Voice'}.wav", V.ai_mark(V._wav(fmt, bytes(buf))))
        z.writestr("README.txt", "Each voice of the talk on its own track. All tracks are the same length and line up, so "
                                 "you can put them side by side in any editor.\nMade by AI with Hoola Vocal.\n")
    return zb.getvalue(), f"{_base_name(h)} - voices.zip"


def _t(s: float, sep: str) -> str:
    ms = int(round(max(0.0, s) * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}{sep}{ms % 1000:03d}"


def subtitles(tenant: str, hid: str, fmt: str = "srt") -> tuple[bytes, str]:
    """Subtitles of a talk from its line times: 'Kabir: Welcome back...'. In a natural take the times are an
    estimate and the file says so (VTT carries a note)."""
    h = _row(tenant, hid)
    segs = [x for x in (h.get("segments") or []) if GV.strip_feelings(str(x.get("text") or ""))]
    if not segs:
        raise V.VocalError("This talk was made before line times were kept, so it has no subtitles. Make it again.")
    fmt = "vtt" if str(fmt).lower() in ("vtt", "webvtt") else "srt"
    cues = [(float(x["start"]), max(float(x["end"]), float(x["start"]) + 0.6),
             f"{x['speaker']}: {GV.strip_feelings(str(x['text']))}") for x in segs]
    if fmt == "srt":
        body = "\n".join(f"{k}\n{_t(a, ',')} --> {_t(b, ',')}\n{t}\n" for k, (a, b, t) in enumerate(cues, 1))
    else:
        note = "NOTE The times are shared out by line length (a natural take is one recording).\n\n" if h.get("timing_est") else ""
        body = "WEBVTT\n\n" + note + "\n".join(f"{_t(a, '.')} --> {_t(b, '.')}\n{t}\n" for a, b, t in cues)
    return body.encode("utf-8"), f"{_base_name(h)}.{fmt}"


async def remake_line(tenant: str, hid: str, n: Any, text: Any = None, speaker: Any = None, chat: str = "") -> dict[str, Any]:
    """Line by line: make ONE line again (new words, or another speaker of the talk) and join it with the kept
    recordings of the others. A new take; the old one stays. Only that line is spoken, so only that line costs."""
    h = _row(tenant, hid)
    parts = _parts(tenant, h)
    segs = [dict(x) for x in h["segments"]]
    lines = [i for i, x in enumerate(segs) if not x.get("reaction")]
    try:
        k = lines[int(n)]
    except (TypeError, ValueError, IndexError):
        raise V.VocalError("That line is not in the talk.") from None
    cast = h.get("cast") or {}
    who = V._clean(speaker, 30) if speaker else segs[k]["speaker"]
    if who not in cast:
        raise V.VocalError(f"{who} does not speak in this talk. Choose one of its speakers, or make the whole talk again.")
    words = V._clean(text, 1500) if text is not None else segs[k]["text"]
    if not GV.strip_feelings(words):
        raise V.VocalError("Write the words of the line.")
    d = V._load(tenant)
    voice = V._voice(d, str(cast[who]))
    code = h.get("lang") or "auto"
    spoken, applied = V.apply_rules(words, d["rules"], code)
    V.need_credits(tenant)
    parts[k] = await V._say(tenant, voice, spoken, code, h.get("style") or "friendly", 1.0, hint=V.ipa_hint(words, d["rules"], code))
    segs[k].update(speaker=who, text=words)
    gaps, cuts = _gaps_cuts(segs)
    data, times = join_timed(parts, gaps, cuts)
    for x, (a, b) in zip(segs, times):
        x["start"], x["end"] = a, b
    if h.get("music"):
        from . import more as M
        import asyncio
        data = await asyncio.to_thread(M.music_bed, data, h["music"])
    letters = [x.get("take") for x in d["history"] if x.get("job") == h.get("job")]
    take = next((c for c in "BCDEFGHIJKLMNOPQRSTUVWXYZ" if c not in letters), "Z")
    from . import engines as EN
    script = "\n".join(f"{x['speaker']}: {x['text']}" for x in segs if not x.get("reaction"))
    keep = {k2: h[k2] for k2 in ("title", "voice", "voice_name", "lang", "lines", "mode", "engine", "job", "style",
                                 "reactions", "music", "pages", "source") if k2 in h}
    row = V._keep(tenant, data, "wav", {**keep, "kind": "dialogue", "text": script[:2000], "chars": len(words),
                                        "applied": applied, "seconds": V.wav_seconds(data), "take": take, "chat": chat,
                                        "credits": EN.quote("dialogue", chars=len(words), engine=h.get("engine") or "gemini")["credits"],
                                        "cast": {**cast}, "segments": segs, "timing_est": False, "remade": int(n), "from_take": hid})
    keep_parts(tenant, row["id"], parts)
    V._to_create(tenant, row, data)
    return row


# ---------------------------------------------------------------- a script written from a document
PAGE_RE = re.compile(r"\[page (\d{1,4})\]")


def paged(pages: list[str]) -> str:
    return "".join(f"\n\n[page {i}]\n{p}" for i, p in enumerate(pages, 1) if p.strip())


def figures(text: str) -> list[str]:
    """Numbers written in digits ('400', '20%', '1,200', '5.5')."""
    return [re.sub(r"[,\s]", "", m) for m in re.findall(r"\d[\d,]*(?:\.\d+)?", text or "")]


def check_lines(lines: list[dict[str, Any]], src: str) -> tuple[list[dict[str, Any]], int]:
    """Each line keeps its page only when that page is in the source; a line with a figure (in digits) that the source
    does not have is marked `unchecked`. Returns (lines, how many lines were marked)."""
    have = {int(x) for x in PAGE_RE.findall(src)}
    src_nums = set(figures(src))
    bad = 0
    for x in lines:
        pg = re.search(r"\d{1,4}", str(x.get("from") or ""))
        x["from"] = f"page {int(pg.group(0))}" if pg and int(pg.group(0)) in have else ""
        miss = [f for f in figures(x["text"]) if f not in src_nums]
        if miss:
            x["unchecked"] = miss[:3]
            bad += 1
        else:
            x.pop("unchecked", None)
    return lines, bad


def said(must: str, lines: list[dict[str, Any]]) -> bool:
    """Whether the thing she asked them to say is in the script (most of its words, in any line)."""
    words = [w for w in re.findall(r"\w{3,}", (must or "").lower())]
    if not words:
        return True
    body = " ".join(str(x.get("text") or "") for x in lines).lower()
    return sum(1 for w in words if w in body) >= max(1, round(len(words) * 0.6))


def dumps(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False)
