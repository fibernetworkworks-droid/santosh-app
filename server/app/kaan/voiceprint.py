"""KAAN W6: real speaker names at transcribe time, matched against HER enrolled voiceprints.

The voiceid lane (Awaaz Pehchaan) already keeps per-tenant speaker embeddings her family
enrolled consented; this module reuses exactly those prints (voiceid.service._prints) and
its identify() threshold law (voiceid_match + voiceid_margin) - nothing new is invented,
nothing is stored twice. Per pause-cut turn, the audio slice is embedded once and scored
against the tenant's prints; sure matches get the person's name, the rest stay unnamed
(no guessing). The unlock is guarded: biometric matching only runs on a tenant whose
retention is bounded (limits.voiceprint_ready). All W6 strings are English (owner rule).

The two seams - _people and _identify - exist so tests patch THIS module's bindings
(the W5 lesson: module objects split after laziness tests pop sys.modules).
"""
from __future__ import annotations

from typing import Any

from . import diarize as DI

VOICEPRINT_METHOD = "voiceprint"
BYTE_RATE = 16000 * 2                       # 16 kHz mono s16le
MIN_TURN_S = 0.5                            # turns shorter than this carry no usable print


def guard(tenant: str) -> None:
    """Fast, honest refusal BEFORE the engine burns a transcription (raises ValueError)."""
    from . import limits as LM
    ok, why = LM.voiceprint_ready(tenant)
    if not ok:
        raise ValueError(why)


def _people(tenant: str) -> list[dict]:
    """Seam: the tenant's enrolled prints (consented Awaaz Pehchaan members)."""
    from ..voiceid import service as VS
    return VS.call_people(tenant) or []


def _identify(people: list[dict], pcm: bytes) -> dict[str, Any]:
    """Seam: one turn slice -> the voiceid identify law (threshold + margin, sure or unnamed)."""
    from ..voiceid import service as VS
    return VS.identify(people, pcm)


def diarize_voiceprint(tenant: str, data: bytes, segments: list[dict[str, Any]],
                       *, pause_s: float | None = None) -> dict[str, Any]:
    """Cut pause turns, embed each turn's audio slice once, match against her prints.
    A technical failure here never destroys the transcript - it degrades to an honest note."""
    p = float(pause_s) if pause_s and float(pause_s) > 0 else DI.PAUSE_S
    try:
        turns = DI.cut_turns(segments, pause_s=p)
        people = _people(tenant)
        from ..voiceid import service as VS
        pcm = VS.pcm16k(bytes(data or b""))
        named = 0
        for t in turns:
            a, b = int(t["start"] * BYTE_RATE), int(t["end"] * BYTE_RATE)
            if (t["end"] - t["start"]) < MIN_TURN_S or b <= a or b > len(pcm):
                t["note"] = "too short to match"
                continue
            hit = _identify(people, pcm[a:b])
            t["score"] = hit.get("score", 0.0)
            t["margin"] = hit.get("margin", 0.0)
            if hit.get("sure") and hit.get("member"):
                t["speaker"] = hit["member"]["name"]
                named += 1
            else:
                t["note"] = f"no sure match (closest: {hit.get('closest') or 'nobody'})"
        return {"method": VOICEPRINT_METHOD, "pause_s": p, "n_turns": len(turns), "turns": turns,
                "named_turns": named,
                "note": (f"Speakers matched against her enrolled voiceprints (voiceid): {named}/{len(turns)} "
                         "turn(s) named; unsure turns stay unnamed - no guessing. Method: voiceprint "
                         f"(pause {p}s cuts the turns, prints name them).")}
    except Exception as e:                   # noqa: BLE001 - the transcript survives, the note is honest
        return {"method": VOICEPRINT_METHOD, "n_turns": 0, "turns": [], "named_turns": 0,
                "error": str(e)[:200],
                "note": f"Voiceprint pass failed after transcription ({str(e)[:120]}). "
                        "The transcript itself is unaffected; retry with diarize=pause_turns or fix the setup."}
