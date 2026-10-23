"""v0.136.1 Find the exact song / video to PLAY when there is no YouTube Data API key and no Spotify API.

Before: without YOUTUBE_API_KEY, youtube_play opened the YouTube search page and Spotify got only "play from search", so
both apps opened on a list and nothing played. Now the exact item is found on the open web (Parallel search pages with
real links; Gemini + Google Search as a second try) and every candidate is CHECKED with the service's own public oEmbed
endpoint (YouTube / Spotify, no key, no login) before it is used, so a guessed or dead link is never opened.

Only her search words leave the server. Results cached 1 day.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any
from urllib.parse import quote

import os

import httpx

log = logging.getLogger("santosh.mediafind")
_CACHE: dict[str, tuple[float, Any]] = {}
TTL = 24 * 3600
_transport = None          # tests plug in httpx.MockTransport
_search_hook = None        # tests plug in async (query) -> list[str] of urls / text
STATS = {"youtube_found": 0, "spotify_found": 0, "misses": 0}

YT_ID = re.compile(r"(?:youtu\.be/|youtube\.com/(?:watch\?(?:[^\s\"'<>]*&)?v=|shorts/|embed/|live/))([\w-]{11})")
SP = re.compile(r"open\.spotify\.com/(?:intl-[a-z]{2}/)?(track|album|artist|playlist)/([A-Za-z0-9]{22})")
STOP = {"the", "a", "of", "song", "songs", "gaana", "gana", "gaane", "video", "official", "full", "lagao", "chalao", "play",
        "on", "pe", "par", "ka", "ki", "ke", "wala", "wali", "hd", "lyrics", "lyrical", "audio", "new", "latest", "best"}


def _words(t: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9ऀ-ॿ]+", (t or "").lower()) if len(w) > 1 and w not in STOP}


def _overlap(q: str, title: str) -> float:
    a, b = _words(q), _words(title)
    return len(a & b) / len(a) if a else 0.0


def _cached(key: str):
    hit = _CACHE.get(key)
    return hit[1] if hit and time.time() - hit[0] < TTL else None


async def _oembed(url: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=8, transport=_transport, follow_redirects=False) as c:
            r = await c.get(url, headers={"User-Agent": "Hoola/1.0"})
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


async def _texts(query: str) -> list[str]:
    """Pages / answers that may hold the links: Parallel first (real page URLs + text), then Gemini Google Search."""
    if _search_hook is not None:
        return await _search_hook(query)
    if os.environ.get("MEDIA_FIND", "true").lower() in ("0", "false", "off", "no"):
        return []                # switched off (tests): callers fall back to search as before
    from . import web
    out: list[str] = []
    try:
        p = await asyncio.wait_for(web.parallel_search(query, [query]), 40)
        for s in p.get("sources") or []:
            out += [s.get("url", ""), s.get("excerpt", "")]
    except Exception as e:
        log.info("mediafind parallel: %s", e)
    if not out:
        try:
            g = await asyncio.wait_for(web.google_search(query + ". Give the full link."), 45)
            out += [g.get("answer", "")] + [s.get("url", "") for s in g.get("sources") or []]
        except Exception as e:
            log.info("mediafind google: %s", e)
    return out


async def youtube(query: str) -> dict | None:
    """{id, title, channel, url} of a real, playable video for her words, or None."""
    q = " ".join((query or "").split())[:120]
    if not q:
        return None
    key = "yt:" + q.lower()
    if (hit := _cached(key)) is not None:
        return hit or None
    ids: list[str] = []
    for t in await _texts(f"{q} YouTube video"):
        for m in YT_ID.finditer(t or ""):
            if m.group(1) not in ids:
                ids.append(m.group(1))
    best, score = None, -1.0
    for vid in ids[:8]:
        meta = await _oembed("https://www.youtube.com/oembed?format=json&url=" + quote(f"https://www.youtube.com/watch?v={vid}"))
        if not meta:
            continue
        s = _overlap(q, f"{meta.get('title', '')} {meta.get('author_name', '')}")
        if s > score:
            best, score = {"id": vid, "title": str(meta.get("title", ""))[:200],
                           "channel": str(meta.get("author_name", ""))[:120],
                           "url": f"https://www.youtube.com/watch?v={vid}"}, s
        if s >= 0.99:
            break
    if best and score < 0.3:
        best = None           # a real video, but not what she asked for
    if best:
        _CACHE[key] = (time.time(), best)
    STATS["youtube_found" if best else "misses"] += 1
    return best


async def spotify(query: str, kind: str = "") -> dict | None:
    """{uri, url, title, type} of a real Spotify item (track by default), checked with Spotify's oEmbed, or None."""
    q = " ".join((query or "").split())[:120]
    if not q:
        return None
    want = kind if kind in ("album", "artist", "playlist") else "track"
    key = f"sp:{want}:{q.lower()}"
    if (hit := _cached(key)) is not None:
        return hit or None
    found: list[tuple[str, str]] = []
    for t in await _texts(f"{q} Spotify {want if want != 'track' else 'song'} open.spotify.com"):
        for m in SP.finditer(t or ""):
            if m.groups() not in found:
                found.append(m.groups())
    found.sort(key=lambda g: g[0] != want)       # the kind she asked for first
    best, score = None, -1.0
    for typ, sid in found[:8]:
        url = f"https://open.spotify.com/{typ}/{sid}"
        meta = await _oembed("https://open.spotify.com/oembed?url=" + quote(url))
        if not meta:
            continue
        s = _overlap(q, str(meta.get("title", ""))) + (0.2 if typ == want else 0)
        if s > score:
            best, score = {"uri": f"spotify:{typ}:{sid}", "url": url, "title": str(meta.get("title", ""))[:200],
                           "type": typ}, s
    if best and score < 0.3:
        best = None
    if best:
        _CACHE[key] = (time.time(), best)
    STATS["spotify_found" if best else "misses"] += 1
    return best
