"""KAAN W3 style presets: deterministic renders of a STORED transcript.

Five styles, all extractive - nothing is generated, nothing is invented, no model call, no
network (port law + inertness law). Every output line traces to the stored row, and the note
names exactly what each style did. Style rendering is a READ on text already on her server,
so it is gate-free by the W1 law (the kaan_audio gate owns AUDIO INGEST only).

  verbatim   the stored transcript as-is (the honest baseline)
  clean      deterministic tidy: whitespace, immediate duplicate tokens, space-before-punct,
             sentence-start caps - no words added or reworded, counts in the note
  subtitles  caption lines split on a >0.6s word gap or a sentence ender (the W2 phrase rule);
             wraps by words when the row carries no word timestamps
  minutes    the W1 deterministic minutes skeleton (per-turn stats, keywords, action CANDIDATES)
  social     extractive takeaways: hook sentence + key words + action-candidate lines + stats

New W3 strings are English (owner instruction: results in English).
"""
from __future__ import annotations

import re
from typing import Any

from . import meeting as MT

STYLES = ("verbatim", "clean", "subtitles", "minutes", "social")

DUP_MIN_LEN = 2        # 1-letter repeats ("a a") are normal speech; only longer tokens collapse
LINE_WORDS = 12        # subtitles wrap width when a row has no word timestamps
HOOK_CHARS = 140


def _clean_text(text: str) -> tuple[str, int]:
    """(cleaned, n_duplicate_tokens_collapsed) - deterministic, nothing added."""
    t = re.sub(r"\s+", " ", text or "").strip()
    t = re.sub(r"\s+([.,!?;:।])", r"\1", t)
    toks = t.split(" ") if t else []
    out: list[str] = []
    dupes = 0
    for w in toks:
        if out and len(w) >= DUP_MIN_LEN and out[-1].lower() == w.lower():
            dupes += 1
            continue
        out.append(w)
    t = " ".join(out)

    def _cap(m: re.Match) -> str:
        c = m.group(2)
        return m.group(1) + (c.upper() if c.isascii() else c)

    t = re.sub(r"(^|[.!?।]\s+)([a-z])", _cap, t)
    return t, dupes


def _subtitles_from_words(segs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from .live import _phrases                      # the W2 phrase rule, reused verbatim
    words = [(float(w.get("start") or 0.0), float(w.get("end") or 0.0), (w.get("word") or "").strip())
             for sg in segs for w in (sg.get("words") or []) if (w.get("word") or "").strip()]
    return _phrases(words)


def _subtitles_wrapped(segs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for sg in segs:
        toks = (sg.get("text") or "").split()
        if not toks:
            continue
        for i in range(0, len(toks), LINE_WORDS):
            chunk = toks[i:i + LINE_WORDS]
            lines.append({"start": float(sg.get("start") or 0.0), "end": float(sg.get("end") or 0.0),
                          "text": " ".join(chunk)})
    return lines


def render(style: str, row: dict[str, Any]) -> dict[str, Any]:
    """row = a transcript dict with text + segments (+ speakers/duration for minutes)."""
    style = (style or "").strip().lower()
    if style not in STYLES:
        raise ValueError(f"style '{style}' nahi jaana. Styles: {', '.join(STYLES)}.")
    segs = row.get("segments") if isinstance(row.get("segments"), list) else []
    text = row.get("text") or ""

    if style == "verbatim":
        return {"style": style, "tid": row.get("id"), "rendered": {"text": text, "segments": segs},
                "note": "verbatim: the stored transcript as-is - the honest baseline, untouched."}

    if style == "clean":
        cleaned, dupes = _clean_text(text)
        note = (f"clean: whitespace tidied, {dupes} immediate duplicate token(s) collapsed, "
                "sentence starts capitalized - no words added or reworded.")
        return {"style": style, "tid": row.get("id"), "rendered": {"text": cleaned}, "note": note}

    if style == "subtitles":
        phr = _subtitles_from_words(segs) if any(sg.get("words") for sg in segs) else _subtitles_wrapped(segs)
        lines = [{"n": i + 1, "start": round(p["start"], 3), "end": round(p["end"], 3), "text": p["text"]}
                 for i, p in enumerate(phr)]
        how = "split on a >0.6s word gap or a sentence ender (the W2 phrase rule)" \
            if any(sg.get("words") for sg in segs) else f"wrapped at {LINE_WORDS} words per line (this row has no word timestamps)"
        return {"style": style, "tid": row.get("id"), "rendered": {"lines": lines},
                "note": f"subtitles: {len(lines)} line(s), {how}."}

    if style == "minutes":
        m = MT.minutes(row)
        return {"style": style, "tid": row.get("id"), "rendered": {"minutes": m},
                "note": "minutes: the W1 deterministic skeleton - structure and cue-based candidates only, never decisions."}

    # social
    m = MT.minutes(row)
    first = re.split(r"(?<=[.!?।])\s+|\n+", text)
    hook = next((s.strip() for s in first if s.strip()), "")
    if len(hook) > HOOK_CHARS:
        hook = hook[:HOOK_CHARS - 1].rstrip() + "…"
    bullets: list[str] = []
    if m.get("keywords"):
        bullets.append("Key words: " + ", ".join(m["keywords"][:6]))
    bullets += [f"[{c.get('cue', '')}] {c.get('text', '')}" for c in (m.get("action_candidates") or [])[:5]]
    stats = (f"{m.get('n_turns', 0)} turn(s), {m.get('duration_s', 0.0)}s, "
             f"{len(m.get('keywords') or [])} key words, {len(m.get('action_candidates') or [])} action candidate(s)")
    return {"style": style, "tid": row.get("id"),
            "rendered": {"hook": hook, "bullets": bullets, "stats": stats},
            "note": "social: extractive only - the hook and every bullet trace to the stored row; no generation."}
