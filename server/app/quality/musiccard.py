"""v0.999.79 M0 MUSIC TEST CARD (docs/HOOLA_MUSIC_PLAN.md phase M0): how good Hoola's songs are in the main world
languages, measured the same way every time, so the engine choices (Lyria now; ElevenLabs Music and Hoola Own later)
come from results and every language gets an honest quality mark.

16 fixed songs (music_asks.py: English, Spanish, Portuguese, Hindi, Arabic, French, Japanese, Korean, Mandarin, German,
Swahili, Tamil, Indonesian, a Hindi + English mix, a 30-second jingle, an instrumental) go through the Music page's own
engine (create/service.song) on the hidden tenant `__musiccard__` (never her songs, never her budget). Each song is
scored in code:

  made        audio came back and can be read
  length      the real length (ffprobe) within 35 % of the length asked
  loudness    integrated loudness between -20 and -6 LUFS (not silent, not crushed)
  words       a listener (faster-whisper, when installed) writes down what is sung: the share of the card's lyric words
              heard back (characters for Japanese / Mandarin), and the language it heard; an instrumental must have
              (almost) no words
  mark        per language: tested (words >= 0.6 and the right language) / works (made, words < 0.6 or not checked) /
              failed

`python -m app.quality music`                         FREE: the set is valid, the scorer is calibrated on planted cases,
                                                      which checks can run here (engine, ffmpeg, listener).
`python -m app.quality music --live --budget-inr N [--limit K]`   real songs; stops itself at the rupee budget.
`python -m app.quality music --status`                the newest saved card.

Said plainly: the thresholds (35 %, 0.6, the LUFS window) are judgement, not measured truth; a listener that cannot
hear a word is not proof the singer got it wrong (sung words are harder to transcribe than speech). Her ears are the
final word. No live card had run when this was written."""
from __future__ import annotations

import asyncio
import importlib.util
import json
import re
import tempfile
import time
import unicodedata
from pathlib import Path
from typing import Any

from .music_asks import ASKS, SET_V

TENANT = "__musiccard__"
INR_PER_SONG = 7                    # Lyria about $0.08 a song (the Create page's own price)
LEN_TOL = 0.35
WORDS_OK = 0.6
LUFS_WIN = (-20.0, -6.0)
OUT = Path("data") / "quality" / "musiccard"


# ---------------------------------------------------------------- the scorer (pure: tested on planted cases)
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "").lower()
    return "".join(ch if (unicodedata.category(ch)[0] in "LMN" or ch.isspace()) else " " for ch in s)


def lyric_units(lyrics: str, script: str = "") -> list[str]:
    """The words of the lyrics a listener should hear back: part tags in [brackets] dropped; for languages written
    without spaces (script 'chars') every letter counts on its own."""
    body = "\n".join(ln for ln in (lyrics or "").splitlines() if not re.fullmatch(r"\s*\[[^\]]*\]\s*", ln))
    t = _norm(body)
    if script == "chars":
        return [ch for ch in t if not ch.isspace()]
    return [w for w in t.split() if len(w) > 1 or not w.isascii()]


def recall(lyrics: str, heard: str, script: str = "") -> float:
    """Share of the lyric units found in what was heard (each unit counted as often as it appears in the lyrics)."""
    want = lyric_units(lyrics, script)
    if not want:
        return 0.0
    got = _norm(heard)
    pool = [ch for ch in got if not ch.isspace()] if script == "chars" else got.split()
    bag: dict[str, int] = {}
    for u in pool:
        bag[u] = bag.get(u, 0) + 1
    hit = 0
    for u in want:
        if bag.get(u, 0) > 0:
            bag[u] -= 1
            hit += 1
    return round(hit / len(want), 3)


def score(ask: dict[str, Any], m: dict[str, Any]) -> dict[str, Any]:
    """One song's row from what was measured: m = {made, seconds, lufs, heard (text or None), heard_lang}."""
    row: dict[str, Any] = {"id": ask["id"], "language": ask.get("language") or "instrumental", "made": bool(m.get("made"))}
    if not row["made"]:
        row.update(ok=False, mark="failed", why=m.get("error") or "no audio came back")
        return row
    secs, want = float(m.get("seconds") or 0), float(ask.get("seconds") or 0)
    row["seconds"], row["asked"] = round(secs, 1), want
    row["length_ok"] = bool(want and secs and abs(secs - want) <= LEN_TOL * want)
    lufs = m.get("lufs")
    row["lufs"] = lufs
    row["loud_ok"] = lufs is not None and LUFS_WIN[0] <= float(lufs) <= LUFS_WIN[1]
    heard = m.get("heard")
    instrumental = (ask.get("vocals") or "") == "none"
    if heard is None:
        row["words"] = None
        row["words_note"] = "not checked (no listener on this server)"
    elif instrumental:
        n = len(_norm(heard).split())
        row["words"] = None
        row["sang_anyway"] = n >= 5
    else:
        row["words"] = recall(ask.get("lyrics") or "", heard, ask.get("script") or "")
        hl = (m.get("heard_lang") or "").lower()
        row["heard_lang"] = hl
        row["lang_ok"] = (not ask.get("lang")) or hl in (ask["lang"], ask.get("also") or "")
    if instrumental:
        good = row["length_ok"] and row["loud_ok"] and not row.get("sang_anyway")
        row["mark"] = "tested" if good and heard is not None else "works"
    elif row["words"] is not None and row["words"] >= WORDS_OK and row.get("lang_ok"):
        row["mark"] = "tested"
    else:
        row["mark"] = "works"
    row["ok"] = row["length_ok"] and row["loud_ok"] and row["mark"] == "tested"
    return row


PLANTED = [   # (ask id, measured, the mark the scorer must give, why)
    ("en_pop", {"made": False, "error": "engine refused"}, "failed", "no audio = failed"),
    ("en_pop", {"made": True, "seconds": 88, "lufs": -11, "heard": "new shoes new street the morning sun a brand new door a brand new run today i start today i shine the city lights are almost mine", "heard_lang": "en"}, "tested", "every word heard"),
    ("en_pop", {"made": True, "seconds": 88, "lufs": -11, "heard": "la la la oh yeah", "heard_lang": "en"}, "works", "words not heard"),
    ("es_reggaeton", {"made": True, "seconds": 90, "lufs": -10, "heard": "el sol se va la playa brilla bailamos juntos en la orilla esta noche no se acaba con mis amigos y la luna clara", "heard_lang": "pt"}, "works", "wrong language heard"),
    ("ja_jpop", {"made": True, "seconds": 92, "lufs": -12, "heard": "夏の空に約束したね君と走った海の道ずっと一緒にいようよ夏の約束忘れない", "heard_lang": "ja"}, "tested", "characters counted for Japanese"),
    ("inst_lofi", {"made": True, "seconds": 90, "lufs": -14, "heard": "this is a song with lots of words being sung here", "heard_lang": "en"}, "works", "an instrumental that sings"),
    ("en_pop", {"made": True, "seconds": 88, "lufs": -11, "heard": None}, "works", "no listener = works, never tested"),
]


def calibrate() -> list[str]:
    """The scorer must give each planted case its mark; the length and loudness checks must catch their faults."""
    by = {a["id"]: a for a in ASKS}
    bad = []
    for aid, m, want, why in PLANTED:
        got = score(by[aid], m)["mark"]
        if got != want:
            bad.append(f"{aid} ({why}): got {got}, want {want}")
    r = score(by["en_pop"], {"made": True, "seconds": 30, "lufs": -11, "heard": None})
    if r["length_ok"]:
        bad.append("a 30 s song for a 90 s ask passed the length check")
    r = score(by["en_pop"], {"made": True, "seconds": 90, "lufs": -40, "heard": None})
    if r["loud_ok"]:
        bad.append("a near-silent song passed the loudness check")
    return bad


def check_set() -> list[str]:
    bad, seen = [], set()
    for a in ASKS:
        if a["id"] in seen:
            bad.append(f"{a['id']}: twice")
        seen.add(a["id"])
        if a.get("vocals") != "none" and not lyric_units(a.get("lyrics") or "", a.get("script") or ""):
            bad.append(f"{a['id']}: a sung song needs lyrics")
        if not 10 <= int(a.get("seconds") or 0) <= 240:
            bad.append(f"{a['id']}: length out of range")
    return bad


# ---------------------------------------------------------------- measuring a real song
def _listen(path: str) -> tuple[str | None, str]:
    """What a listener hears (text) and the language it reports; (None, '') when no listener is installed."""
    if importlib.util.find_spec("faster_whisper") is None:
        return None, ""
    try:
        from faster_whisper import WhisperModel  # type: ignore
        from ..config import get_settings
        size = getattr(get_settings(), "video_whisper_model", "") or "small"
        model = WhisperModel(size, device="cpu", compute_type="int8")
        segs, info = model.transcribe(path, vad_filter=True)
        return " ".join(s.text for s in segs).strip(), str(getattr(info, "language", "") or "")
    except Exception as e:   # noqa: BLE001
        return None, f"listener failed: {str(e)[:80]}"


def _measure(data: bytes, ext: str) -> dict[str, Any]:
    from ..audedit import ops
    with tempfile.NamedTemporaryFile(suffix=ext or ".mp3") as f:
        f.write(data)
        f.flush()
        info = ops.loudness(f.name)
        heard, lang = _listen(f.name)
    return {"made": True, "seconds": info.get("duration") or 0, "lufs": info.get("lufs"), "heard": heard, "heard_lang": lang}


def free_card() -> dict[str, Any]:
    from ..create import service as cs
    bad_set, bad_cal = check_set(), calibrate()
    ffmpeg = False
    try:
        from ..audedit import ops
        ffmpeg = ops.ffmpeg_ok()
    except Exception:   # noqa: BLE001
        pass
    return {"set_v": SET_V, "songs": len(ASKS), "languages": sorted({a.get("language") or "instrumental" for a in ASKS}),
            "set_ok": not bad_set, "set_problems": bad_set, "scorer_ok": not bad_cal, "scorer_problems": bad_cal,
            "engine_ready": bool(cs.ready().get("song")), "ffmpeg": ffmpeg,
            "listener": importlib.util.find_spec("faster_whisper") is not None,
            "inr_estimate": INR_PER_SONG * len(ASKS)}


async def live_card(asks: list[dict[str, Any]], budget_inr: float, label: str = "") -> dict[str, Any]:
    from .. import usage
    from ..create import service as cs
    rows, spent, t0 = [], 0.0, time.time()
    for a in asks:
        if spent + INR_PER_SONG > budget_inr:
            rows.append({"id": a["id"], "language": a.get("language") or "instrumental", "made": False, "mark": "not run",
                         "why": "budget reached"})
            continue
        t = time.time()
        try:
            with usage.scope(TENANT, "create"):
                r = await cs.song(a["brief"], a.get("genre") or "", a.get("language") or "English", a.get("vocals") or "duet",
                                  "", 0, int(a.get("seconds") or 0), a.get("lyrics") or "")
            spent += INR_PER_SONG
            m = await asyncio.to_thread(_measure, r["bytes"], r["ext"])
        except Exception as e:   # noqa: BLE001
            spent += INR_PER_SONG
            m = {"made": False, "error": str(e)[:200]}
        row = score(a, m)
        row["make_s"] = round(time.time() - t, 1)
        if m.get("heard"):
            row["heard"] = str(m["heard"])[:300]
        rows.append(row)
        print(f"  {row['id']:<14} {row.get('mark', ''):<8} len {row.get('seconds', '-')}/{row.get('asked', '-')} "
              f"words {row.get('words')} lang {row.get('heard_lang', '-')} lufs {row.get('lufs', '-')}", flush=True)
    card = {"set_v": SET_V, "label": label, "at": int(time.time()), "minutes": round((time.time() - t0) / 60, 1),
            "engine": "lyria", "inr_spent": spent, "rows": rows,
            "marks": {r["language"]: r.get("mark") for r in rows},
            "tested": sum(1 for r in rows if r.get("mark") == "tested"), "made": sum(1 for r in rows if r.get("made"))}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"card-{card['at']}.json").write_text(json.dumps(card, ensure_ascii=False, indent=1), encoding="utf-8")
    return card


def newest() -> dict[str, Any] | None:
    try:
        files = sorted(OUT.glob("card-*.json"))
        return json.loads(files[-1].read_text(encoding="utf-8")) if files else None
    except Exception:   # noqa: BLE001
        return None
