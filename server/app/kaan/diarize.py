"""KAAN W1 diarization: turn attribution from the transcript's own timeline (pause turns).

HONESTY FIRST: this is NOT voiceprint speaker ID. The W0 pipeline stores no audio (local-first:
the temp file dies the moment the engine is done), so the only honest signal is the transcript's
own shape - the pauses. A gap longer than PAUSE_S between consecutive words (when the engine gave
word timings) or between segments (when it did not) cuts a TURN boundary. Turns are labelled
neutrally; WHO spoke is unknown until the owner names the turns (names={'1': 'Gupta ji'}).
Real acoustic diarization (speaker embeddings, the sherpa-onnx voiceid path) needs STORED audio -
a W6 retention decision, never smuggled in here. Hand-built, CPU-light, zero dependencies
(port law + inertness law: importing this module loads nothing, touches nothing).
"""
from __future__ import annotations

from typing import Any

PAUSE_S = 0.8          # gap (seconds) that marks a turn boundary - a natural conversational pause
MAX_TURNS = 400        # safety cap - a pathological transcript never hangs the tool
PAUSE_METHOD = "pause_turns"   # the honest method name, surfaced in status + stored rows


def cut_turns(segments: list[dict[str, Any]], *, pause_s: float = PAUSE_S) -> list[dict[str, Any]]:
    """Cut the timeline into turns at pause boundaries. Word gaps beat segment gaps when both exist.
    Deterministic: the same segments in -> the same turns out (no clock, no randomness)."""
    stream: list[tuple[float, float, str]] = []      # (start, end, chunk text)
    segs = sorted([s for s in (segments or []) if s.get("text")],
                  key=lambda s: float(s.get("start") or 0.0))
    for s in segs:
        words = s.get("words") or []
        if words:
            for w in words:
                t = (w.get("word") or "").strip()
                if t:
                    stream.append((float(w.get("start") or 0.0), float(w.get("end") or 0.0), t))
        else:
            stream.append((float(s.get("start") or 0.0), float(s.get("end") or 0.0),
                           (s.get("text") or "").strip()))

    turns: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    for start, end, text in stream:
        if cur is None or (start - cur["end"]) > pause_s:
            if cur is not None:
                turns.append(cur)
            cur = {"start": round(start, 3), "end": round(end, 3), "chunks": [(text, start, end)]}
        else:
            cur["end"] = round(max(cur["end"], end), 3)
            cur["chunks"].append((text, start, end))
        if len(turns) >= MAX_TURNS:
            break
    if cur is not None and len(turns) < MAX_TURNS:
        turns.append(cur)

    out: list[dict[str, Any]] = []
    for i, t in enumerate(turns, 1):
        text = " ".join(c for c, _s, _e in t["chunks"]).strip()
        out.append({"turn": i, "speaker": "", "start": t["start"], "end": t["end"],
                    "n_words": len(t["chunks"]), "text": text})
    return out


def diarize(segments: list[dict[str, Any]], *, names: dict[str, str] | None = None,
            pause_s: float | None = None) -> dict[str, Any]:
    """The W1 answer: pause-cut turns + optional owner-given names + the honest note."""
    p = float(pause_s) if pause_s and float(pause_s) > 0 else PAUSE_S
    turns = cut_turns(segments, pause_s=p)
    clean: dict[str, str] = {}
    for k, v in (names or {}).items():
        if str(v).strip():
            clean[str(k).strip()] = str(v).strip()
    named = 0
    for t in turns:
        nm = clean.get(str(t["turn"]), "")
        if nm:
            t["speaker"] = nm
            named += 1
    unknown = sorted(set(clean) - {str(t["turn"]) for t in turns})
    return {"method": PAUSE_METHOD, "pause_s": p, "n_turns": len(turns), "turns": turns,
            "named_turns": named, "unknown_names": unknown,
            "truncated": len(turns) >= MAX_TURNS,
            "note": ("yeh turns pauses se kate hain (method: pause_turns), speaker pehchaan nahi - kaun bola "
                     "woh audio se nahi jaanta (audio store nahi hota). Naam action=diarize mein "
                     "names={'1': 'naam'} se dein; ek hi Speaker ki do baatein ek turn lag sakti hain - "
                     "faisla aapka, tool guess nahi karta.")}
