"""Captions for the FINISHED video: what was said in the sources, moved onto the edited timeline.

The transcript is in source time (from faster-whisper when it is installed, else from Gemini's timed transcript).
Every word is placed by where its source moment lands in the edit (cuts, speed changes and transitions included),
words that were cut out disappear, and the rest are grouped into short reel-style captions (max 5 words / 30
letters, a new caption after a pause or at the end of a sentence).
"""
from __future__ import annotations

import logging
import re
from fractions import Fraction
from typing import Any

log = logging.getLogger("santosh.videoedit")


def words_from_segments(segments: list[dict[str, Any]], duration: float) -> list[dict[str, Any]]:
    """Timed sentences -> timed words (time shared out by word length inside each sentence)."""
    out = []
    for s in segments or []:
        try:
            a, b = float(s.get("start", 0)), float(s.get("end", 0))
        except (TypeError, ValueError):
            continue
        text = re.sub(r"\s+", " ", str(s.get("text") or "")).strip()
        if not text or b <= a:
            continue
        a, b = max(0.0, a), min(duration or b, b)
        if b <= a:
            continue
        ws = text.split(" ")
        total = sum(len(w) + 1 for w in ws)
        t = a
        for w in ws:
            d = (b - a) * (len(w) + 1) / total
            out.append({"start": round(t, 3), "end": round(t + d, 3), "word": w})
            t += d
    out.sort(key=lambda w: w["start"])
    return out


def whisper_words(path: str, language: str | None) -> list[dict[str, Any]] | None:
    """Word timestamps from faster-whisper (optional; CPU int8). None when it isn't installed or fails."""
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError:
        return None
    try:
        from ..config import get_settings
        size = getattr(get_settings(), "video_whisper_model", "") or "small"
        m = WhisperModel(size, device="cpu", compute_type="int8")
        segs, _ = m.transcribe(path, language=language if language and language not in ("none", "auto") else None,
                               word_timestamps=True, vad_filter=True)
        return [{"start": float(w.start), "end": float(w.end), "word": w.word.strip()} for s in segs for w in (s.words or [])
                if w.word.strip()]
    except Exception as e:
        log.info("whisper failed: %s", e)
        return None


def place(words_by_src: dict[str, list[dict[str, Any]]], tl, src_keys: list[str | None]) -> list[dict[str, Any]]:
    """Source-time words -> output-time words, using the loaded vedit Timeline (frames, speed, transitions).
    src_keys[i] = which source clip i plays (None for photos / colour cards)."""
    fps = Fraction(tl.project.fps)
    out = []
    pos = 0                                   # output frame where clip i starts
    for i, c in enumerate(tl.clips):
        start = pos / fps
        length = Fraction(c.frames) / fps
        key = src_keys[i] if i < len(src_keys) else None
        if key and c.kind == "video":
            for w in words_by_src.get(key, []):
                a, b = float(w["start"]), float(w["end"])
                if b <= c.tin or a >= c.tout:
                    continue
                mid = (a + b) / 2
                if not (c.tin <= mid <= c.tout):      # mostly cut away: drop the word
                    continue
                oa = float(start) + (max(a, c.tin) - c.tin) / c.speed
                ob = float(start) + (min(b, c.tout) - c.tin) / c.speed
                oa, ob = max(float(start), oa), min(float(start + length), ob)
                if ob - oa >= 0.04:
                    out.append({"start": round(oa, 3), "end": round(ob, 3), "word": w["word"], "clip": i})
        pos += c.frames - c.tframes
    out.sort(key=lambda w: w["start"])
    return out


def cues(words: list[dict[str, Any]], max_words: int = 5, max_chars: int = 30, gap: float = 0.6) -> list[dict[str, Any]]:
    out, cur = [], []
    for w in words:
        if cur and (w["start"] - cur[-1]["end"] > gap or w.get("clip") != cur[-1].get("clip")):   # a cut = a new caption
            out.append(cur)
            cur = []
        cur.append(w)
        text = " ".join(x["word"] for x in cur)
        if len(cur) >= max_words or len(text) >= max_chars or re.search(r"[.?!।]$", w["word"]):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    res = []
    for c in out:
        a, b = c[0]["start"], max(c[-1]["end"], c[0]["start"] + 0.5)
        res.append({"start": a, "end": b, "text": " ".join(x["word"] for x in c)})
    for i in range(len(res) - 1):                       # never overlap the next caption
        res[i]["end"] = min(res[i]["end"], res[i + 1]["start"])
    return [r for r in res if r["end"] - r["start"] >= 0.2]


def _t(x: float) -> str:
    ms = int(round(x * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def srt(items: list[dict[str, Any]]) -> str:
    return "\n".join(f"{k}\n{_t(c['start'])} --> {_t(c['end'])}\n{c['text']}\n" for k, c in enumerate(items, 1))
