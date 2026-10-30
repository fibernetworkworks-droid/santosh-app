"""v0.308 STUDIO APIS: which real engine behind Create is switched on, checked for real, without ever showing a key.

Keys stay where the rules put them - the VPS .env, read at start (`app/config.py`). This module only reads WHETHER a
key is set and asks each provider one free question (a key / model listing, never a paid call), so she sees:
ready / no key / key refused / provider not reachable / set but not checked (no free check exists for it).

    report(fresh=False) -> {"engines": [...], "features": [...], "checked_at": t}
    python -m app.studio.apis            # the same on the VPS (vps-ops job `studio_apis`), keys never printed
"""
from __future__ import annotations

import asyncio
import shutil
import time
from typing import Any

import httpx

from ..config import get_settings

# id, name, .env name(s), what it powers in Create, where to get the key, cost note, needed
ENGINES: list[dict[str, Any]] = [
    {"id": "gemini", "name": "Google Gemini", "env": ["GEMINI_API_KEY"],
     "powers": ["Pictures", "Voice-overs", "Songs (Lyria)", "Dubbing", "Video understanding"],
     "get": "https://aistudio.google.com/apikey", "cost": "Pictures ~₹3-12, a song ~₹7, voice-overs paise per line",
     "need": True},
    {"id": "openrouter", "name": "OpenRouter (video models)", "env": ["OPENROUTER_API_KEY"],
     "powers": ["Video clips: Seedance, Veo, Kling, Wan and the rest of the picker", "Live video prices"],
     "get": "https://openrouter.ai/keys", "cost": "Pay per second of video; every clip shows its price card first",
     "need": True},
    {"id": "anthropic", "name": "Anthropic (Claude)", "env": ["ANTHROPIC_API_KEY"],
     "powers": ["Storyboards (Director)", "Script writer", "Enhance / Improve on prompts"],
     "get": "https://console.anthropic.com/settings/keys", "cost": "Already used by Hoola's chat - no new key if chat works",
     "need": True},
    {"id": "sync", "name": "Sync Labs (lip sync)", "env": ["SYNC_API_KEY"],
     "powers": ["Lip sync on talking shots (any language)"],
     "get": "https://sync.so", "cost": "Per second of lip-synced video, on a price card", "need": False},
    {"id": "fal", "name": "fal.ai (backup video)", "env": ["FAL_KEY"],
     "powers": ["Backup route for Seedance when OpenRouter is busy"],
     "get": "https://fal.ai/dashboard/keys", "cost": "Only if you want a second route", "need": False},
    {"id": "ark", "name": "BytePlus ModelArk (backup video)", "env": ["ARK_API_KEY"],
     "powers": ["Seedance straight from BytePlus"],
     "get": "https://console.byteplus.com/ark", "cost": "Only if you want a third route", "need": False},
]
FEATURES = [  # what she can make, and which engines can make it (any one is enough)
    ("Pictures", ["gemini"]), ("Voice-overs", ["gemini"]), ("Songs", ["gemini"]), ("Dubbing", ["gemini", "+ffmpeg"]),
    ("Video clips", ["openrouter", "fal", "ark"]), ("Director films", ["openrouter", "fal", "ark"]),
    ("Storyboards and scripts", ["anthropic"]), ("Lip sync", ["sync"]), ("Video editor", ["+ffmpeg"]),
]
TTL = 600.0
_CACHE: dict[str, Any] = {}


def _key(eid: str) -> str:
    s = get_settings()
    return str({"gemini": s.gemini_api_key, "openrouter": s.openrouter_api_key, "anthropic": s.anthropic_api_key,
                "sync": s.sync_api_key, "fal": s.fal_key, "ark": s.ark_api_key}.get(eid) or "").strip()


async def _ping(eid: str, key: str, c: httpx.AsyncClient) -> tuple[str, str]:
    """One FREE question per provider -> (state, detail). Never a generation, never the key in the detail."""
    s = get_settings()
    try:
        if eid == "openrouter":
            base = (s.studio_openrouter_url or "https://openrouter.ai/api/v1").rstrip("/")
            r = await c.get(f"{base}/key", headers={"Authorization": f"Bearer {key}"})
            if r.status_code == 200:
                d = (r.json() or {}).get("data") or {}
                left = d.get("limit_remaining")
                return "ready", f"credit left ${left:.2f}" if isinstance(left, (int, float)) else "key accepted"
        elif eid == "gemini":
            base = (s.studio_gemini_url or "https://generativelanguage.googleapis.com").rstrip("/")
            r = await c.get(f"{base}/v1beta/models", params={"pageSize": 1}, headers={"x-goog-api-key": key})
            if r.status_code == 200:
                return "ready", "key accepted"
        elif eid == "anthropic":
            r = await c.get("https://api.anthropic.com/v1/models", params={"limit": 1},
                            headers={"x-api-key": key, "anthropic-version": "2023-06-01"})
            if r.status_code == 200:
                return "ready", "key accepted"
        else:
            return "unchecked", "key is set; this provider has no free check, the first job will tell"
        if r.status_code == 400 and "API_KEY_INVALID" in r.text:      # Google answers a bad key with 400, not 401
            return "refused", "the provider refused this key (invalid) - make a new one"
        if r.status_code in (401, 403):
            return "refused", f"the provider refused this key ({r.status_code}) - make a new one"
        if r.status_code == 402:
            return "refused", "the account has no credit left (402)"
        return "unreachable", f"the provider answered {r.status_code}"
    except httpx.HTTPError as e:
        return "unreachable", f"could not reach the provider ({type(e).__name__})"


async def _report() -> dict[str, Any]:
    engines = []
    async with httpx.AsyncClient(timeout=12.0) as c:
        async def one(e: dict[str, Any]) -> dict[str, Any]:
            key = _key(e["id"])
            state, detail = ("missing", "no key in the server .env") if not key else await _ping(e["id"], key, c)
            return {k: e[k] for k in ("id", "name", "env", "powers", "get", "cost", "need")} | {"state": state, "detail": detail}
        engines = list(await asyncio.gather(*(one(e) for e in ENGINES)))
    ok = {e["id"] for e in engines if e["state"] in ("ready", "unchecked")}
    ff = bool(shutil.which("ffmpeg"))
    feats = []
    for name, needs in FEATURES:
        eng = [n for n in needs if not n.startswith("+")]
        tools_ok = all(ff for n in needs if n == "+ffmpeg")
        works = tools_ok and (not eng or any(n in ok for n in eng))
        feats.append({"name": name, "ready": works,
                      "why": "" if works else ("ffmpeg is not installed on the server" if not tools_ok
                                               else "needs " + " or ".join(next(x["name"] for x in ENGINES if x["id"] == n) for n in eng))})
    return {"engines": engines, "features": feats, "ffmpeg": ff, "checked_at": int(time.time())}


async def report(fresh: bool = False) -> dict[str, Any]:
    if not fresh and _CACHE.get("at", 0) > time.time() - TTL:
        return _CACHE["r"]
    r = await _report()
    _CACHE.update(at=time.time(), r=r)
    return r


def _main() -> None:
    r = asyncio.run(report(fresh=True))
    mark = {"ready": "OK  ", "unchecked": "SET ", "missing": "--  ", "refused": "BAD ", "unreachable": "??  "}
    print("Hoola Create - engines (keys are never printed)\n")
    for e in r["engines"]:
        print(f"  {mark.get(e['state'], '    ')} {e['name']:<34} {'/'.join(e['env']):<20} {e['detail']}")
    print(f"\n  {'OK  ' if r['ffmpeg'] else '--  '} ffmpeg on the server")
    print("\nWhat she can make now:")
    for f in r["features"]:
        print(f"  {'yes' if f['ready'] else 'no '}  {f['name']}{'' if f['ready'] else '  (' + f['why'] + ')'}")


if __name__ == "__main__":
    _main()
