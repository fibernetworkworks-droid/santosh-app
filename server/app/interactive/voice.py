"""v0.999.170 HOOLA INTERACTIVE REBUILD - the voice of every Interactive video is a Hoola Vocal voice.

Before this, a video could speak only through the GPU voice lab, so with the lab off every video was captions only. Now:

    speaker(tenant, voice_id, lang) -> (sentence, lang) -> wav bytes

wraps `vocal.service._say`, the very function Vocal's Speech page uses: Gemini voices (140 languages), ElevenLabs premium
voices, her own cloned / designed voices, the GPU lab as one more engine. Her Vocal dictionary applies to every line
(names said her way). `voices(tenant)` is the same list the Vocal voice picker shows. `langs()` is Vocal's language table.

Rules:
  HERS     only her own voices or Hoola's ready-made voices - a voice id she does not own is refused (`_voice`);
  CREDITS  no credits = refused before any engine call (`need_credits`);
  SAID     an engine that is not connected is said in its own words (VocalError), never silently replaced.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

log = logging.getLogger("santosh.interactive.voice")


class VoiceError(Exception):
    pass


def langs() -> list[dict[str, Any]]:
    """Every language a Vocal voice speaks: code, English name, its own name, region."""
    from ..vocal import langs as L
    return [{"code": x["code"], "name": x["name"], "native": x["native"], "region": x["region"]}
            for x in L.LANGS if x["gemini"] or x["eleven4"] or x["eleven3"]]


def lang_ok(code: str) -> str:
    """A language code Vocal knows, or '' (unknown codes are refused - a video is never read in another language)."""
    from ..vocal import langs as L
    c = L.code_of(str(code or ""))
    return "" if c in ("", "auto") else c


def lang_name(code: str) -> str:
    from ..vocal import langs as L
    return L.name_of(code) or code


def voices(tenant: str) -> dict[str, Any]:
    """Her own voices first, then the ready-made library (the Vocal picker's list), each with whether it can speak now."""
    from ..vocal import service as V
    d = V._load(tenant)
    mine = [{"id": v["id"], "name": v["name"], "kind": v.get("kind") or "mine", "engine": v.get("engine"),
             "tier": v.get("tier"), "ready": bool(v.get("ready")), "langs": v.get("langs") or [], "any": True,
             "color": v.get("color")} for v in V._mine(d)]
    lib = [{"id": v["id"], "name": v["name"], "gender": v.get("gender") or "", "tone": v.get("tone") or "",
            "accent": v.get("accent") or "", "age": v.get("age") or "", "use": v.get("use") or "",
            "engine": v["engine"], "tier": v["tier"], "ready": bool(v.get("ready")),
            "langs": v.get("langs") or [], "any": bool(v.get("any")), "color": v.get("color")} for v in V.library()]
    favs = list((d.get("favs") or [])) if isinstance(d.get("favs"), list) else []
    return {"mine": mine, "library": lib, "favs": favs, "default": default_voice(tenant),
            "sample_lines": dict(getattr(V, "PREVIEW", {}) or {})}     # v0.999.201 the words each sample says, per language


def apply_voice(tenant: str, vid: str, ids: list[Any]) -> dict[str, Any]:
    """v0.999.201 one voice put into several of her videos. Only the voice changes; a video being made is left out, said."""
    from . import studio as S
    vid = str(vid or "").strip()
    if not vid:
        raise VoiceError("Choose a voice.")
    voice_info(tenant, vid)                     # a voice she does not have is refused here
    done, skipped = [], []
    for pid in [str(x) for x in (ids or [])][:50]:
        try:
            S.save(tenant, pid, {"voice": vid})
            done.append(pid)
        except S.StudioError as e:
            skipped.append({"id": pid, "why": str(e)})
    if not done and not skipped:
        raise VoiceError("Choose at least one video.")
    return {"done": done, "skipped": skipped}


def default_voice(tenant: str) -> str:
    """Her Vocal default voice when she set one, else the first ready-made voice."""
    from ..vocal import service as V
    try:
        d = V._load(tenant)
        pref = (d.get("settings") or {}).get("voice") or ""
        if pref:
            return str(pref)
        b = V.builtin()
        return b[0]["id"] if b else ""
    except Exception:   # noqa: BLE001
        return ""


def voice_info(tenant: str, vid: str) -> dict[str, Any]:
    from ..vocal import service as V
    try:
        v = V._voice(V._load(tenant), vid)
    except V.VocalError as e:
        raise VoiceError(str(e)) from None
    return {"id": v["id"], "name": v.get("name") or "Voice", "engine": V._engine_of(v), "tier": v.get("tier") or "standard"}


def speaker(tenant: str, vid: str, lang: str, style: str = "friendly") -> Callable[[str, str], bytes]:
    """A function the film pipeline calls once per spoken line (it runs in the make thread, so this is synchronous)."""
    from ..vocal import service as V
    d = V._load(tenant)
    try:
        v = V._voice(d, vid) if vid else V._voice_for(d, "", lang, "auto")
        V.need_credits(tenant)
    except V.VocalError as e:
        raise VoiceError(str(e)) from None
    rules = d.get("rules") or []

    def say(sentence: str, _lang: str) -> bytes:
        spoken, _n = V.apply_rules(sentence, rules, lang)
        hint = V.ipa_hint(spoken, rules, lang)
        try:
            return asyncio.run(V._say(tenant, v, spoken, lang, style, 1.0, 0.5, hint))
        except V.VocalError as e:
            raise VoiceError(str(e)) from None

    return say


def seconds_of(text: str, lang: str = "") -> float:
    """Spoken length estimate for the price card: about 2.6 words a second, 14 characters a second for scripts with no
    spaces between words."""
    t = " ".join(str(text or "").split())
    words = len(t.split())
    if words <= 1 and len(t) > 12:
        return max(1.0, len(t) / 14.0)
    return max(1.0, words / 2.6)


def credits_for(tenant: str, vid: str, chars: int) -> dict[str, Any]:
    """Vocal's own price line for speaking `chars` characters in this voice."""
    from ..vocal import engines as EN
    from ..vocal import service as V
    eng = "gemini"
    try:
        eng = V._engine_of(V._voice(V._load(tenant), vid)) if vid else "gemini"
    except Exception:   # noqa: BLE001
        pass
    return EN.quote("tts", chars=chars, takes=1, engine=eng)
