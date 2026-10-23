"""v0.136.1 YouTube / Spotify PLAY the thing, not a search list: the exact video / track is found on the open web and checked
with the service's own oEmbed before the phone opens it; the phone then presses play itself."""
import asyncio
from pathlib import Path

import httpx
import pytest

from tests.test_bazar import _events
from tests.test_bt import _both, _phone_answers, conv  # noqa: F401
from tests.test_life import conv_ctx

YT_GOOD = "dQw4w9WgXcQ"
YT_OTHER = "aaaaaaaaaaa"
SP_TRACK = "4uLU6hMCjMI75M1A2tKUQC"


def _oembed(req: httpx.Request) -> httpx.Response:
    u = str(req.url)
    if "youtube.com/oembed" in u:
        if YT_GOOD in u:
            return httpx.Response(200, json={"title": "Pal Pal Dil Ke Paas - Kishore Kumar", "author_name": "Saregama"})
        if YT_OTHER in u:
            return httpx.Response(200, json={"title": "Cooking tips for beginners", "author_name": "Chef"})
        return httpx.Response(404)
    if "open.spotify.com/oembed" in u:
        if SP_TRACK in u:
            return httpx.Response(200, json={"title": "Tum Hi Ho"})
        return httpx.Response(404)
    return httpx.Response(404)


@pytest.fixture()
def finder(monkeypatch):
    from app import mediafind
    mediafind._CACHE.clear()
    seen = []

    async def hook(q):
        seen.append(q)
        return [f"https://www.youtube.com/watch?v={YT_OTHER}", f"see https://youtu.be/{YT_GOOD}?si=x",
                "https://youtube.com/watch?v=zzzzzzzzzzz",            # dead: oEmbed 404, never used
                f"https://open.spotify.com/intl-in/track/{SP_TRACK}?si=abc",
                "https://open.spotify.com/track/0000000000000000000000"]
    monkeypatch.setattr(mediafind, "_search_hook", hook)
    monkeypatch.setattr(mediafind, "_transport", httpx.MockTransport(_oembed))
    return seen


def test_youtube_finder_checks_and_picks_the_matching_video(finder):
    from app import mediafind
    got = asyncio.run(mediafind.youtube("Kishore Kumar pal pal dil ke paas"))
    assert got["id"] == YT_GOOD and "Kishore" in got["title"]
    asyncio.run(mediafind.youtube("Kishore Kumar pal pal dil ke paas"))
    assert len(finder) == 1                                        # cached
    assert asyncio.run(mediafind.youtube("totally unrelated words xyz")) is None   # real videos, but not hers


def test_spotify_finder_gives_a_checked_track_uri(finder):
    from app import mediafind
    got = asyncio.run(mediafind.spotify("tum hi ho arijit"))
    assert got["uri"] == f"spotify:track:{SP_TRACK}" and got["title"] == "Tum Hi Ho"


def test_youtube_play_without_key_plays_the_found_video(env, monkeypatch, finder):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    from app.agent.tools import Ctx, dispatch  # noqa: F401
    from app.config import get_settings
    get_settings.cache_clear()
    ctx = conv_ctx()
    from app.agent.tools import dispatch as d
    out = asyncio.run(d("youtube_play", {"query": "Kishore Kumar pal pal dil ke paas"}, ctx))
    act = _events(ctx.conversation_id, "device_action")[-1]
    assert out["video_id"] == YT_GOOD and act["video_id"] == YT_GOOD and act["url"].endswith(YT_GOOD)
    assert _events(ctx.conversation_id, "youtube")[-1]["items"][0]["id"] == YT_GOOD


def test_spotify_play_sends_the_exact_uri(conv, finder):
    from app.agent.tools import Ctx, dispatch
    from app.bazar import devices as dsvc
    out, job = asyncio.run(_both(dispatch("music_control", {"action": "play", "query": "tum hi ho arijit", "app": "spotify"},
                                          Ctx("default", conv)),
                                 _phone_answers("home_device", lambda p: dsvc.command_result("default", p["command_id"], True))))
    op = job["ops"][0]
    assert op["uri"] == f"spotify:track:{SP_TRACK}" and op["package"] == "com.spotify.music"
    assert op["fallback"].startswith("spotify:search:")             # still there if the app can't open the item
    assert out["playing_title"] == "Tum Hi Ho" and "Tum Hi Ho" in out["message"]


def test_bad_uri_never_reaches_the_phone(conv):
    from app.bazar import devices as dsvc
    from app.bazar import service
    ok = lambda p: dsvc.command_result("default", p["command_id"], True)      # noqa: E731
    for bad in ["intent://evil#Intent;end", "https://evil.com/watch?v=" + YT_GOOD, "spotify:track:short"]:
        _, job = asyncio.run(_both(asyncio.to_thread(service.run, "default", conv, "bluetooth-speaker", "media",
                                                     {"action": "play", "query": "x", "app": "spotify", "uri": bad}),
                                   _phone_answers("home_device", ok)))
        assert "uri" not in job["ops"][0]
    _, job = asyncio.run(_both(asyncio.to_thread(service.run, "default", conv, "bluetooth-speaker", "media",
                                                 {"action": "play", "query": "x", "app": "youtube_music",
                                                  "uri": f"https://music.youtube.com/watch?v={YT_GOOD}"}),
                               _phone_answers("home_device", ok)))
    assert job["ops"][0]["uri"].endswith(YT_GOOD)


def test_kotlin_opens_exact_and_presses_play():
    kt = (Path(__file__).resolve().parents[2] / "tool/android/kotlin/HomeDevices.kt").read_text()
    assert "openExact(pkg, uri)" in kt and "autoPlay(" in kt and "getActiveSessions" in kt
    assert "playFromUri" in kt and "transportControls.play()" in kt and 'key("PLAY")' in kt


def test_call_keeps_going_while_music_plays():
    """v0.136.2: a song taking the audio no longer pauses the voice call; only a real phone call does."""
    kt = (Path(__file__).resolve().parents[2] / "tool/android/kotlin/VoiceAudio.kt").read_text()
    assert "decideLoss" in kt and "MODE_IN_CALL" in kt and "isMusicActive" in kt
    assert "musicGate(chunk)" in kt and 'onState?.invoke("music"' in kt
    loss = kt[kt.index("AudioManager.AUDIOFOCUS_LOSS ->"):kt.index("AudioManager.AUDIOFOCUS_GAIN ->")]
    assert "paused = true" not in loss                      # no instant pause on focus loss any more
