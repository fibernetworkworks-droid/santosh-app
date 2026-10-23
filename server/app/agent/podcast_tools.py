"""Podcast Sahayak tools (podcast producer). `podcast_dekho` only reads; `podcast` does the work.

Publishing an episode, any message to a guest or sponsor (invite, release request, script) and any sponsor invoice become CARDS
here; only HER tap in the app (API) decides them. Transcripts come only from her audio or her own caption file; quotes / chapters
are checked against the real transcript; sponsor reads carry #Ad at the start and the end. Hoola never invents a fact, a fee or a
statistic, never posts anything itself and never takes or pays money."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

_ACTIONS = ["settings", "artwork", "feed", "guest", "invite", "release_request", "release_got", "release_revoke", "forget_guest",
            "episode", "run_sheet", "audio", "loudness", "normalize", "transcribe", "speakers", "notes", "notes_edit", "crosspost",
            "music", "music_use", "sponsor", "read", "sponsor_message", "invoice", "paid", "message", "publish", "posted",
            "unpublish", "stats"]
_OWNER_ONLY = {"settings", "artwork", "feed", "release_got", "release_revoke", "forget_guest", "paid", "posted", "unpublish"}

PODCAST_TOOLS = [
    {"name": "podcast", "description": (
        "Podcast producer. NEVER invent facts, quotes, fees, dates or stats. Cards = only her tap decides (say 'aapki haan ka card "
        "bheja hai'). action=settings*: show, host, author, description, language, category (Apple), explicit, owner_email, "
        "website, gstin, upi_id, record_minutes, gap_minutes, release_terms, morning_time. artwork*: file_id. feed*: on. "
        "guest: name, phone, email, bio, topics, status (guest=G-001 to update). invite / release_request (fee): guest, episode "
        "-> card. release_got*: guest, how file|text|audio, file_id / text / at+episode. release_revoke* / forget_guest*: guest. "
        "episode: title, topics, guests, record_at, publish_on, season, episode_no, kind, explicit, news, ai_parts (episode=EP-001 "
        "to update). run_sheet: episode. audio: episode, file_id. loudness / normalize: episode. transcribe: episode (file_id "
        "of her SRT/VTT optional). speakers: episode, names {S1: name}. notes: episode, links. notes_edit: episode, summary, "
        "points, chapters. crosspost: episode. music: title, licence own|commissioned|cc0|cc_by|royalty_free|paid|unknown, "
        "attribution, valid_until. music_use: episode, music. sponsor: brand, amount*, deliverables, status. read: episode, "
        "sponsor, slot pre|mid|post, script. sponsor_message: sponsor, episode/text -> card. invoice: sponsor, amount -> card. "
        "paid*: sponsor, amount, tds. message: to, text -> card. publish: episode, where feed|pack -> card. posted*: episode, "
        "platform, url. unpublish*: episode. stats: text / file_id (her export). * = owner only."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": _ACTIONS},
         "episode": {"type": "string"}, "guest": {"type": "string"}, "sponsor": {"type": "string"}, "music": {"type": "string"},
         "name": {"type": "string"}, "phone": {"type": "string"}, "email": {"type": "string"}, "bio": {"type": "string"},
         "topics": {"type": "array", "items": {"type": "string"}}, "guests": {"type": "array", "items": {"type": "string"}},
         "status": {"type": "string"}, "notes": {"type": "string"}, "text": {"type": "string"}, "file_id": {"type": "string"},
         "how": {"type": "string"}, "at": {"type": "string"}, "fee": {"type": "string"},
         "title": {"type": "string"}, "record_at": {"type": "string"}, "record_minutes": {"type": "integer"},
         "record_place": {"type": "string"}, "publish_on": {"type": "string"}, "season": {"type": "integer"},
         "episode_no": {"type": "integer"}, "kind": {"type": "string"}, "explicit": {"type": "boolean"}, "news": {"type": "boolean"},
         "ai_parts": {"type": "array", "items": {"type": "string"}}, "minutes": {"type": "integer"},
         "names": {"type": "object"}, "links": {"type": "array", "items": {"type": "string"}}, "summary": {"type": "string"},
         "points": {"type": "array", "items": {"type": "string"}}, "chapters": {"type": "string"},
         "licence": {"type": "string"}, "artist": {"type": "string"}, "source": {"type": "string"}, "proof": {"type": "string"},
         "attribution": {"type": "string"}, "valid_until": {"type": "string"}, "commercial_ok": {"type": "boolean"},
         "remove": {"type": "boolean"}, "brand": {"type": "string"}, "contact": {"type": "string"}, "gstin": {"type": "string"},
         "amount": {"type": "number"}, "deliverables": {"type": "string"}, "slot": {"type": "string"}, "script": {"type": "string"},
         "brand_ok": {"type": "boolean"}, "tds": {"type": "number"}, "ref": {"type": "string"}, "to": {"type": "string"},
         "where": {"type": "string"}, "platform": {"type": "string"}, "url": {"type": "string"}, "reason": {"type": "string"},
         "on": {"type": "boolean"}, "show": {"type": "string"}, "host": {"type": "string"}, "author": {"type": "string"},
         "description": {"type": "string"}, "language": {"type": "string"}, "category": {"type": "string"},
         "owner_email": {"type": "string"}, "website": {"type": "string"}, "upi_id": {"type": "string"},
         "gap_minutes": {"type": "integer"}, "release_terms": {"type": "string"}, "morning_time": {"type": "string"},
         "business": {"type": "string"}, "address": {"type": "string"}, "rules": {"type": "string"}, "feed_url": {"type": "string"},
         "host_platform": {"type": "string"}},
         "required": ["action"]}},
    {"name": "podcast_dekho", "description": (
        "Read podcast work (nothing changes). what=day (recordings, releases missing, publish dates, cards waiting, unpaid "
        "sponsors) | episodes (status) | episode (episode: notes, run sheet, music, reads, checks) | checks (episode: what blocks "
        "publishing) | guests | guest (guest) | release_text (guest, episode) | sponsors | music | cards | stats | feed | "
        "description (episode, platform) | settings."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["day", "episodes", "episode", "checks", "guests", "guest", "release_text", "sponsors",
                                             "music", "cards", "stats", "feed", "description", "settings"]},
         "episode": {"type": "string"}, "guest": {"type": "string"}, "status": {"type": "string"}, "platform": {"type": "string"}},
         "required": ["what"]}},
]
PODCAST_LABELS = {"podcast": "Podcast ka kaam kar raha hoon", "podcast_dekho": "Podcast dekh raha hoon"}

_SET_KEYS = ("show", "host", "author", "description", "language", "category", "explicit", "owner_email", "website", "gstin",
             "upi_id", "record_minutes", "gap_minutes", "release_terms", "morning_time", "business", "address", "phone", "rules",
             "feed_url", "host_platform")


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _actor(ctx: Ctx) -> str:
    return getattr(ctx, "actor", "owner") or "owner"


def _owner(ctx: Ctx) -> bool:
    a = _actor(ctx)
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..podcast import service as S
    t, conv, actor = ctx.tenant_id, ctx.conversation_id, _actor(ctx)
    if actor.startswith("customer:"):
        raise ToolError("Yeh kaam graahak ke liye nahi.")
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Sirf owner.")
    ep, g, sp = _s(a.get("episode")), _s(a.get("guest")), _s(a.get("sponsor"))
    try:
        if action == "settings":
            return S.save_settings(t, **{k: a[k] for k in _SET_KEYS if k in a})
        if action == "artwork":
            return S.set_artwork(t, _s(a.get("file_id")))
        if action == "feed":
            return S.feed_set(t, bool(a.get("on")), actor=actor)
        if action == "guest":
            return S.guest_save(t, _s(a.get("name")), _s(a.get("phone")), _s(a.get("email")), _s(a.get("bio")), a.get("topics"),
                                a.get("links"), _s(a.get("status")), _s(a.get("notes")), g)
        if action == "invite":
            return S.invite_request(t, g or _s(a.get("name")), ep, _s(a.get("text")), actor, conv)
        if action == "release_request":
            return S.release_request(t, g or _s(a.get("name")), ep, _s(a.get("fee")), actor, conv)
        if action == "release_got":
            return S.release_got(t, g, _s(a.get("how")), _s(a.get("file_id")), _s(a.get("text")), ep, a.get("at"), actor)
        if action == "release_revoke":
            return S.release_revoke(t, g, _s(a.get("reason") or a.get("notes")), actor)
        if action == "forget_guest":
            return S.forget_guest(t, g, actor)
        if action == "episode":
            title = _s(a.get("title")) or ("" if ep else _s(a.get("text") or a.get("name")))
            return S.episode_save(t, ep, title, a.get("season"), a.get("episode_no"), _s(a.get("kind")), a.get("topics"),
                                  a.get("guests"), a.get("record_at"), a.get("record_minutes"), _s(a.get("record_place")),
                                  _s(a.get("publish_on")), a.get("explicit"), a.get("news"), a.get("ai_parts"), actor, conv)
        if action == "run_sheet":
            return S.run_sheet(t, ep, a.get("minutes"))
        if action == "audio":
            return S.attach_audio(t, ep, _s(a.get("file_id")), actor=actor)
        if action == "loudness":
            return S.measure_loudness(t, ep)
        if action == "normalize":
            return S.normalize(t, ep, actor)
        if action == "transcribe":
            return S.transcribe(t, ep, _s(a.get("file_id")), _s(a.get("text")), actor)
        if action == "speakers":
            return S.set_speakers(t, ep, a.get("names") or {})
        if action == "notes":
            return S.make_notes(t, ep, a.get("links"), actor=actor)
        if action == "notes_edit":
            return S.edit_notes(t, ep, a.get("summary"), a.get("points"), a.get("chapters"), a.get("links"), None, actor)
        if action == "crosspost":
            return S.crosspost(t, ep, _s(a.get("url")))
        if action == "music":
            return S.music_save(t, _s(a.get("title") or a.get("name")),
                                _s(a.get("licence")) or "unknown", _s(a.get("artist")), _s(a.get("source")), _s(a.get("proof")),
                                _s(a.get("attribution")), _s(a.get("valid_until")), a.get("commercial_ok"), _s(a.get("music")))
        if action == "music_use":
            return S.music_use(t, ep, _s(a.get("music")), bool(a.get("remove")))
        if action == "sponsor":
            return S.sponsor_save(t, _s(a.get("brand")), _s(a.get("contact")), _s(a.get("phone")), _s(a.get("email")),
                                  _s(a.get("gstin")), a.get("amount"), _s(a.get("deliverables")), _s(a.get("status")),
                                  _s(a.get("notes")), sp, actor)
        if action == "read":
            return S.read_save(t, ep, sp, _s(a.get("script") or a.get("text")), _s(a.get("slot")) or "mid", True, a.get("brand_ok"))
        if action == "sponsor_message":
            return S.sponsor_request(t, sp, ep, _s(a.get("text")), actor, conv)
        if action == "invoice":
            return S.invoice_request(t, sp, a.get("amount"), _s(a.get("notes") or a.get("text")), actor, conv)
        if action == "paid":
            return S.paid(t, sp, a.get("amount"), _s(a.get("ref")), a.get("tds"), actor)
        if action == "message":
            return S.message_request(t, _s(a.get("to")) or g or sp, _s(a.get("text")), actor, conv)
        if action == "publish":
            return S.publish_request(t, ep, _s(a.get("where")) or "feed", actor, conv)
        if action == "posted":
            return S.posted(t, ep, _s(a.get("platform")), _s(a.get("url")), actor)
        if action == "unpublish":
            return S.unpublish(t, ep, _s(a.get("reason")), actor)
        if action == "stats":
            return S.stats_import(t, _s(a.get("text")), _s(a.get("file_id")), _s(a.get("platform")))
    except S.PodcastError as e:
        raise ToolError(str(e))
    raise ToolError(f"action '{action}' nahi pehchana.")


def _see(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..podcast import service as S
    t, ep = ctx.tenant_id, _s(a.get("episode"))
    try:
        if what == "day":
            return S.day(t)
        if what == "episodes":
            return {"episodes": S.episodes(t, _s(a.get("status")))}
        if what == "episode":
            return S.episode_view(t, ep)
        if what == "checks":
            return S.checks(t, ep)
        if what == "guests":
            return {"guests": S.guests(t)}
        if what == "guest":
            return S.guest_view(t, _s(a.get("guest")))
        if what == "release_text":
            return S.release_text(t, _s(a.get("guest")), ep)
        if what == "sponsors":
            return {"sponsors": S.sponsors(t)}
        if what == "music":
            return {"music": S.music_list(t)}
        if what == "cards":
            return {"cards": S.cards(t, _s(a.get("status")) or "waiting")}
        if what == "stats":
            return S.stats_report(t)
        if what == "feed":
            return S.feed_info(t)
        if what == "description":
            return {"text": S.description(t, ep, _s(a.get("platform")) or "spotify")}
        if what == "settings":
            return S.settings(t)
    except S.PodcastError as e:
        raise ToolError(str(e))
    raise ToolError(f"what '{what}' nahi pehchana.")


async def _podcast(ctx: Ctx, action: str = "", **a: Any) -> dict[str, Any]:
    return await asyncio.to_thread(_act, ctx, action, a)


async def _podcast_dekho(ctx: Ctx, what: str = "", **a: Any) -> dict[str, Any]:
    return await asyncio.to_thread(_see, ctx, what, a)


PODCAST_HANDLERS = {"podcast": _podcast, "podcast_dekho": _podcast_dekho}
