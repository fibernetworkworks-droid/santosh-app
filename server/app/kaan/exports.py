"""KAAN W4 exports: deterministic SRT / VTT / TXT / JSON of a STORED transcript.

All four formats are pure serializations of the row - nothing is generated, nothing is invented,
no model call, no network (port law + inertness law). SRT/VTT cues are exactly the W3 subtitles
lines (one code path, so captions and exports always agree); TXT is the stored text verbatim;
JSON is the full row (text + segments + word timings) with sort_keys so the bytes are
deterministic. Exporting is a READ on text already on her server - gate-free by the W1 law.

New W4 strings are English (owner instruction).
"""
from __future__ import annotations

import json
from typing import Any

from .styles import LINE_WORDS, _subtitles_from_words, _subtitles_wrapped

FORMATS = ("srt", "vtt", "txt", "json")


def _stamp(sec: float, ms_sep: str) -> str:
    """HH:MM:SS,mmm (srt) or HH:MM:SS.mmm (vtt) - clamped at 0, rounding spill carried up."""
    s = max(0.0, float(sec or 0.0))
    h, rem = divmod(int(s), 3600)
    m, si = divmod(rem, 60)
    ms = int(round((s - int(s)) * 1000))
    if ms == 1000:
        ms = 0
        si += 1
        if si == 60:
            si, m = 0, m + 1
            if m == 60:
                m, h = 0, h + 1
    return f"{h:02d}:{m:02d}:{si:02d}{ms_sep}{ms:03d}"


def _cues(row: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    """(cues, how) - the cue source is named so the note can say exactly where the lines came from."""
    segs = row.get("segments") if isinstance(row.get("segments"), list) else []
    if any(sg.get("words") for sg in segs):
        return (_subtitles_from_words(segs),
                "the W2 phrase rule (>0.6s word gap or sentence ender)")
    if segs:
        return (_subtitles_wrapped(segs),
                f"per-segment lines wrapped at {LINE_WORDS} words (this row has no word timestamps)")
    text = (row.get("text") or "").strip()
    if text:
        return ([{"start": 0.0, "end": float(row.get("duration_s") or 0.0), "text": text}],
                "one cue from the row text (no segment timing stored)")
    return [], "no cues"


def render(fmt: str, row: dict[str, Any]) -> dict[str, Any]:
    """row = a transcript dict with text + segments (+ language/task/model/duration/speakers for json)."""
    fmt = (fmt or "").strip().lower()
    if fmt not in FORMATS:
        raise ValueError(f"export format '{fmt}' is not known. Formats: {', '.join(FORMATS)}.")
    text = row.get("text") or ""
    segs = row.get("segments") if isinstance(row.get("segments"), list) else []
    if not (text or segs):
        raise ValueError("This transcript is empty (no text, no segments) - there is nothing to export.")
    tid = row.get("id") or ""

    if fmt == "txt":
        out = (text.rstrip() + "\n") if text.strip() else "\n"
        return {"fmt": fmt, "tid": tid, "filename": f"{tid}.{fmt}", "text": out, "n_cues": 0,
                "chars": len(out),
                "note": "txt: the stored text verbatim - nothing added, nothing changed."}

    if fmt == "json":
        doc = {"id": tid, "text": text, "language": row.get("language") or "",
               "task": row.get("task") or "", "model": row.get("model") or "",
               "duration_s": row.get("duration_s"), "n_segments": len(segs),
               "speakers": row.get("speakers"), "segments": segs}
        out = json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        return {"fmt": fmt, "tid": tid, "filename": f"{tid}.{fmt}", "text": out, "n_cues": len(segs),
                "chars": len(out),
                "note": f"json: the full row - text + {len(segs)} segment(s) with word timings; sort_keys so the bytes are deterministic."}

    cues, how = _cues(row)
    sep = "," if fmt == "srt" else "."
    blocks = [f"{i}\n{_stamp(c['start'], sep)} --> {_stamp(c['end'], sep)}\n{c['text']}"
              for i, c in enumerate(cues, 1)]
    out = ("\n\n".join(blocks) + "\n") if blocks else ""
    if fmt == "vtt":
        out = "WEBVTT\n\n" + out
    return {"fmt": fmt, "tid": tid, "filename": f"{tid}.{fmt}", "text": out, "n_cues": len(cues),
            "chars": len(out),
            "note": f"{fmt}: {len(cues)} cue(s) from {how} - extractive, every cue traces to the stored row."}
