"""v0.126 Spotify (and other music apps) by name: "Spotify pe Arijit lagao" -> Android's "play from search" aimed at that
app on her phone, with the app's own search link as a fallback; no Spotify API, no login, no user limit."""
import asyncio

import pytest

from tests.test_bt import _both, _phone_answers, conv  # noqa: F401


def _play(conv, args, answer):
    from app.agent.tools import Ctx, dispatch
    return asyncio.run(_both(dispatch("music_control", args, Ctx("default", conv)), _phone_answers("home_device", answer)))


def test_spotify_play_goes_to_the_spotify_app(conv):
    from app.bazar import devices as dsvc

    out, job = _play(conv, {"action": "play", "query": "Arijit Singh", "app": "spotify", "kind": "artist"},
                     lambda p: dsvc.command_result("default", p["command_id"], True))
    op = job["ops"][0]
    assert op["op"] == "play_from_search" and op["package"] == "com.spotify.music" and op["kind"] == "artist"
    assert op["fallback"] == "spotify:search:Arijit%20Singh"
    assert out["status"] == "done" and "Spotify" in out["message"] and "tap play" in out["note"]


def test_default_app_and_other_apps(conv):
    from app.bazar import devices as dsvc
    ok = lambda p: dsvc.command_result("default", p["command_id"], True)      # noqa: E731
    _, job = _play(conv, {"action": "play", "query": "bhajan"}, ok)
    assert "package" not in job["ops"][0] and "fallback" not in job["ops"][0]
    _, job = _play(conv, {"action": "play", "query": "lata", "app": "jiosaavn"}, ok)
    assert job["ops"][0]["package"] == "com.jio.media.jiobeats" and "fallback" not in job["ops"][0]
    _, job = _play(conv, {"action": "play", "query": "lofi", "app": "youtube_music"}, ok)
    assert job["ops"][0]["fallback"].startswith("https://music.youtube.com/search?q=lofi")


def test_app_missing_is_said_plainly(conv):
    from app.bazar import devices as dsvc
    out, _ = _play(conv, {"action": "play", "query": "Arijit", "app": "spotify"},
                   lambda p: dsvc.command_result("default", p["command_id"], False, "app_missing"))
    assert out["status"] == "failed" and "isn't on this phone" in out["error"]


def test_names_and_pause_still_work(conv):
    from app.bazar.connectors.base import ToolError
    from app.bazar.connectors.device import music_app
    from app.bazar import devices as dsvc
    assert music_app("Spotyfy") == "spotify" and music_app("YT Music") == "youtube_music" and music_app("") == ""
    with pytest.raises(ToolError):
        music_app("napster")
    out, job = _play(conv, {"action": "pause", "app": "spotify"}, lambda p: dsvc.command_result("default", p["command_id"], True))
    assert job["ops"][0] == {"op": "media_key", "key": "PAUSE"} and out["status"] == "done"


def test_kotlin_targets_the_app():
    from pathlib import Path
    kt = (Path(__file__).resolve().parents[2] / "tool/android/kotlin/HomeDevices.kt").read_text()
    assert "intent.setPackage(pkg)" in kt and '"app_missing"' in kt and "EXTRA_MEDIA_ARTIST" in kt
    man = (Path(__file__).resolve().parents[2] / "tool/AndroidManifest.xml").read_text()
    assert 'android:name="com.spotify.music"' in man and 'android:scheme="spotify"' in man
