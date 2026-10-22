"""Santosh YouTube tools (official YouTube Data API v3, YouTube Analytics API, Gemini video understanding)."""
from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import quote_plus

from ..bazar.connectors.base import ToolError as BazarError
from ..youtube import service as ys
from ..youtube.client import NotConnected, YTError
from .tools import Ctx, ToolError

VID = {"type": "string", "description": "A YouTube link or video id"}

YOUTUBE_TOOLS = [
    {"name": "youtube_search", "description": (
        "Search YouTube (videos by default; kind=channel or playlist). order: relevance, date (newest), viewCount, rating. "
        "duration: short (<4 min), medium, long (>20 min). recent_days limits to recent uploads. channel = search inside "
        "one channel. Shows a video card in the chat."),
     "input_schema": {"type": "object", "properties": {
         "query": {"type": "string"}, "kind": {"type": "string", "enum": ["video", "channel", "playlist"]},
         "order": {"type": "string", "enum": ["relevance", "date", "viewCount", "rating"]},
         "duration": {"type": "string", "enum": ["short", "medium", "long"]}, "recent_days": {"type": "integer"},
         "channel": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["query"]}},
    {"name": "youtube_play", "description": (
        "PLAY a YouTube video for her right now (not just search): 'YouTube pe Kishore Kumar ke gaane lagao', 'TV pe "
        "Masterchef ka naya episode chalao', 'ye video phone pe kholo'. video = a link / id (e.g. from youtube_search), "
        "else query = what to find (the best match plays; order=date for the newest). on='phone' opens it in the YouTube "
        "app on her phone; on='tv' plays it on her smart TV (YouTube app on Android / Google TV, Samsung, LG, Fire TV on the "
        "same Wi-Fi; tv = which TV). Say the title that is playing. For free live TV channels use tv_channel."),
     "input_schema": {"type": "object", "properties": {
         "video": VID, "query": {"type": "string"}, "on": {"type": "string", "enum": ["phone", "tv"]},
         "tv": {"type": "string"}, "order": {"type": "string", "enum": ["relevance", "date", "viewCount"]},
         "duration": {"type": "string", "enum": ["short", "medium", "long"]}}}},
    {"name": "youtube_video", "description": "Details and stats of videos (views, likes, comments, length, date, description).",
     "input_schema": {"type": "object", "properties": {"videos": {"type": "array", "items": VID}}, "required": ["videos"]}},
    {"name": "youtube_watch", "description": (
        "Watch a public YouTube video (Google's Gemini API) and summarise it with timestamps, or answer a question about "
        "it ('is video mein price kya bataya?'). language: hi, hinglish, en, mr. Takes up to a minute for long videos."),
     "input_schema": {"type": "object", "properties": {"video": VID, "question": {"type": "string"},
                                                       "language": {"type": "string", "enum": ["hi", "hinglish", "en", "mr"]}},
                      "required": ["video"]}},
    {"name": "youtube_channel", "description": "A channel's subscribers, views, video count and latest videos (name, @handle or link).",
     "input_schema": {"type": "object", "properties": {"channel": {"type": "string"}, "latest": {"type": "integer"}},
                      "required": ["channel"]}},
    {"name": "youtube_comments", "description": (
        "Top or newest comments of a video (with comment ids, used to reply). mine=true for comments on the user's own "
        "video through their sign-in."),
     "input_schema": {"type": "object", "properties": {"video": VID, "order": {"type": "string", "enum": ["relevance", "time"]},
                                                       "limit": {"type": "integer"}, "mine": {"type": "boolean"}},
                      "required": ["video"]}},
    {"name": "youtube_my_channel", "description": "The user's own YouTube channel: subscribers, views, latest videos with stats.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "youtube_my_videos", "description": "The user's uploaded videos with stats (sort: date or views).",
     "input_schema": {"type": "object", "properties": {"limit": {"type": "integer"}, "sort": {"type": "string", "enum": ["date", "views"]}}}},
    {"name": "youtube_analytics", "description": (
        "The user's channel analytics for the last N days: by=summary (totals), day (trend), video (top 10 videos), "
        "country, traffic (where viewers came from). Views, watch minutes, average view duration, subscribers, likes."),
     "input_schema": {"type": "object", "properties": {"days": {"type": "integer"},
                                                       "by": {"type": "string", "enum": ["summary", "day", "video", "country", "traffic"]}}}},
    {"name": "youtube_playlist", "description": (
        "The user's playlists: action=list, create (private / unlisted), add (videos to one of their private / unlisted playlists)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["list", "create", "add"]}, "title": {"type": "string"},
         "privacy": {"type": "string", "enum": ["private", "unlisted"]}, "playlist": {"type": "string"},
         "videos": {"type": "array", "items": VID}}, "required": ["action"]}},
    {"name": "youtube_reply", "description": (
        "Reply to a comment on the user's video, as the user (comment_id from youtube_comments). Write a warm, short reply "
        "in the commenter's language. The user approves on a card first."),
     "input_schema": {"type": "object", "properties": {"comment_id": {"type": "string"}, "text": {"type": "string"}},
                      "required": ["comment_id", "text"]}},
    {"name": "youtube_update_video", "description": (
        "Change the user's own video: title, description, tags, privacy (public / unlisted / private). Card first."),
     "input_schema": {"type": "object", "properties": {"video": VID, "title": {"type": "string"}, "description": {"type": "string"},
                                                       "tags": {"type": "array", "items": {"type": "string"}},
                                                       "privacy": {"type": "string", "enum": ["public", "unlisted", "private"]}},
                      "required": ["video"]}},
    {"name": "youtube_upload", "description": (
        "Upload a video file to the user's channel (file_id: a PC file via pc_send_to_phone, or one the user added). "
        "Default privacy private. Write a good title, description and tags. Card first."),
     "input_schema": {"type": "object", "properties": {"file_id": {"type": "string"}, "title": {"type": "string"},
                                                       "description": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}},
                                                       "privacy": {"type": "string", "enum": ["private", "unlisted", "public"]}},
                      "required": ["file_id", "title"]}},
]

YOUTUBE_LABELS = {"youtube_search": "YouTube par dhoondh raha hoon", "youtube_play": "YouTube video laga raha hoon", "youtube_video": "Video dekh raha hoon",
                  "youtube_watch": "Video dekh kar samajh raha hoon", "youtube_channel": "Channel dekh raha hoon",
                  "youtube_comments": "Comments padh raha hoon", "youtube_my_channel": "Aapka channel dekh raha hoon",
                  "youtube_my_videos": "Aapke videos dekh raha hoon", "youtube_analytics": "Channel ke numbers dekh raha hoon",
                  "youtube_playlist": "Playlist sambhal raha hoon", "youtube_reply": "Jawab ki manzoori le raha hoon",
                  "youtube_update_video": "Video badalne ki manzoori le raha hoon", "youtube_upload": "Upload ki manzoori le raha hoon"}


async def _t(fn, *a, **kw):
    try:
        return await asyncio.to_thread(fn, *a, **kw)
    except NotConnected as e:
        raise ToolError(str(e))
    except YTError as e:
        raise ToolError(str(e))


def _card(ctx: Ctx, pid: str) -> dict[str, Any]:
    from ..bazar import service
    try:
        out = service.run(ctx.tenant_id, ctx.conversation_id, "santosh-youtube", "confirm_change", {"pending_id": pid})
    except BazarError as e:
        raise ToolError(str(e))
    return {k: v for k, v in out.items() if k in ("needs_approval", "approval_id", "card", "say")} | {"status": "needs_approval"}


async def youtube_search(ctx: Ctx, query, kind="video", order="relevance", duration="", recent_days=0, channel="", limit=8, **_):
    out = await _t(ys.search, ctx.tenant_id, str(query), kind or "video", order or "relevance", int(limit or 8),
                   duration or "", int(recent_days or 0), channel or "")
    if out.get("videos"):
        ys.publish(ctx.conversation_id, out["videos"], f"YouTube: {query}")
    return out


async def youtube_play(ctx: Ctx, video="", query="", on="phone", tv="", order="relevance", duration="", **_):
    """v0.125 Find (or take) one video and play it: phone = the YouTube app, tv = DIAL launch on her smart TV."""
    from ..youtube.client import video_id, watch_url
    on = "tv" if str(on or "").lower() == "tv" else "phone"
    q = str(query or "").strip()
    vid = video_id(str(video or "")) if video else None
    if video and not vid:
        raise ToolError("Yeh YouTube link / video id samajh nahi aaya.")
    if not vid and not q:
        raise ToolError("Kaunsa video? video (link) ya query (kya dhoondhna hai) dijiye.")
    title, channel, picked = "", "", None
    try:
        if vid:
            got = await asyncio.to_thread(ys.video, ctx.tenant_id, [vid])
            picked = got[0] if got else None
        else:
            out = await asyncio.to_thread(ys.search, ctx.tenant_id, q, "video", order or "relevance", 3, duration or "")
            vids = out.get("videos") or []
            if not vids:
                raise ToolError(f"YouTube par '{q}' ka koi video nahi mila. Doosre shabd bataiye.")
            picked = vids[0]
    except NotConnected:
        picked = None            # no API key / sign-in: still open it, by search
    except YTError as e:
        if vid:
            picked = None        # lookup failed but the id is known: play it anyway
        else:
            raise ToolError(str(e))
    if picked:
        vid, title, channel = picked.get("id") or vid, picked.get("title", ""), picked.get("channel", "")
        ys.publish(ctx.conversation_id, [picked], "YouTube: chal raha hai")
    shown = title or q or "video"
    if on == "tv":
        from .bt_tools import _device, _ensure_tv
        await asyncio.to_thread(_ensure_tv, ctx.tenant_id)
        dev = {"device": tv} if tv else {}
        if vid:
            res = await _device(ctx, "smart-tv-remote", "tv_youtube", {"video_id": vid, "title": title or q, **dev})
        else:
            await _device(ctx, "smart-tv-remote", "tv_open_app", {"app": "youtube", **dev})
            res = await _device(ctx, "smart-tv-remote", "tv_search", {"query": q, **dev})
        return {"on": "tv", "video_id": vid, "title": title, "channel": channel, **res,
                "say": f"TV par YouTube mein '{shown}' lag gaya." if res.get("status") == "done" else ""}
    from .life_tools import _device_action
    payload = {"video_id": vid or "", "title": shown[:120], "query": "" if vid else q[:200],
               "url": watch_url(vid) if vid else "https://www.youtube.com/results?search_query=" + quote_plus(q)}
    note = (f"'{shown}' phone par YouTube app mein khul raha hai." if vid else
            f"YouTube app mein '{q}' dhoondh kar khol diya; jo video chahiye usse tap kar lijiye.")
    return {"on": "phone", "video_id": vid, "title": title, "channel": channel, **_device_action(ctx, "youtube_play", payload, note)}


async def youtube_video(ctx: Ctx, videos, **_):
    vids = await _t(ys.video, ctx.tenant_id, [str(v) for v in videos or []])
    ys.publish(ctx.conversation_id, vids)
    return {"videos": vids}


async def youtube_watch(ctx: Ctx, video, question="", language="", **_):
    return await _t(ys.watch, ctx.tenant_id, str(video), str(question or ""), str(language or ""))


async def youtube_channel(ctx: Ctx, channel, latest=6, **_):
    return await _t(ys.channel, ctx.tenant_id, str(channel), int(latest if latest is not None else 6))


async def youtube_comments(ctx: Ctx, video, order="relevance", limit=20, mine=False, **_):
    return await _t(ys.comments, ctx.tenant_id, str(video), order or "relevance", int(limit or 20), bool(mine))


async def youtube_my_channel(ctx: Ctx, **_):
    return await _t(ys.my_channel, ctx.tenant_id)


async def youtube_my_videos(ctx: Ctx, limit=25, sort="date", **_):
    return await _t(ys.my_videos, ctx.tenant_id, int(limit or 25), sort or "date")


async def youtube_analytics(ctx: Ctx, days=28, by="summary", **_):
    return await _t(ys.analytics, ctx.tenant_id, int(days or 28), by or "summary")


async def youtube_playlist(ctx: Ctx, action, title="", privacy="private", playlist="", videos=None, **_):
    if action == "list":
        return {"playlists": await _t(ys.playlists, ctx.tenant_id)}
    if action == "create":
        if not title:
            raise ToolError("Playlist ka naam do.")
        return await _t(ys.playlist_create, ctx.tenant_id, str(title), privacy or "private")
    if action == "add":
        return await _t(ys.playlist_add, ctx.tenant_id, str(playlist), [str(v) for v in videos or []])
    raise ToolError("action: list, create, add")


async def youtube_reply(ctx: Ctx, comment_id, text, **_):
    pid = await _t(ys.plan_reply, ctx.tenant_id, ctx.conversation_id, str(comment_id), str(text))
    return await asyncio.to_thread(_card, ctx, pid)


async def youtube_update_video(ctx: Ctx, video, title=None, description=None, tags=None, privacy=None, **_):
    pid = await _t(ys.plan_update, ctx.tenant_id, ctx.conversation_id, str(video), title, description, tags, privacy)
    return await asyncio.to_thread(_card, ctx, pid)


async def youtube_upload(ctx: Ctx, file_id, title, description="", tags=None, privacy="private", **_):
    pid = await _t(ys.plan_upload, ctx.tenant_id, ctx.conversation_id, str(file_id), str(title), str(description or ""),
                   privacy or "private", tags or [])
    return await asyncio.to_thread(_card, ctx, pid)


YOUTUBE_HANDLERS = {"youtube_search": youtube_search, "youtube_play": youtube_play, "youtube_video": youtube_video, "youtube_watch": youtube_watch,
                    "youtube_channel": youtube_channel, "youtube_comments": youtube_comments,
                    "youtube_my_channel": youtube_my_channel, "youtube_my_videos": youtube_my_videos,
                    "youtube_analytics": youtube_analytics, "youtube_playlist": youtube_playlist,
                    "youtube_reply": youtube_reply, "youtube_update_video": youtube_update_video,
                    "youtube_upload": youtube_upload}
