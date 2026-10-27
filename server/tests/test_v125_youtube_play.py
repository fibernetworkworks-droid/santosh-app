"""v0.125 YouTube play: find the best match (or take a link) and play it in the YouTube app on her phone, or on her smart
TV by a DIAL launch of the YouTube app with v=<id> (search fallback when the TV has no DIAL)."""
import asyncio

import pytest

from app.agent.tools import Ctx, ToolError, dispatch
from tests.test_bazar import _events
from tests.test_bt import _both, _phone_answers
from tests.test_life import conv_ctx
from tests.test_youtube import yt  # noqa: F401


def run(name, args, ctx):
    return asyncio.run(dispatch(name, args, ctx))


def test_play_on_phone_by_search_opens_youtube_app(yt):
    ctx = conv_ctx()
    out = run("youtube_play", {"query": "gpon"}, ctx)
    assert out["on"] == "phone" and out["video_id"] == "aaaaaaaaaaa" and out["title"] == "GPON basics in Hindi"
    act = _events(ctx.conversation_id, "device_action")[-1]
    assert act["type"] == "youtube_play" and act["video_id"] == "aaaaaaaaaaa"
    assert act["url"] == "https://www.youtube.com/watch?v=aaaaaaaaaaa"
    assert _events(ctx.conversation_id, "youtube")[-1]["items"][0]["id"] == "aaaaaaaaaaa"     # the card shows what plays


def test_play_by_link_and_bad_input(yt):
    ctx = conv_ctx()
    out = run("youtube_play", {"video": "https://youtu.be/bbbbbbbbbbb"}, ctx)
    assert out["video_id"] == "bbbbbbbbbbb" and out["sent_to_phone"]
    with pytest.raises(ToolError):
        run("youtube_play", {}, ctx)
    with pytest.raises(ToolError):
        run("youtube_play", {"video": "not a link"}, ctx)
    with pytest.raises(ToolError):
        run("youtube_play", {"query": "nothing matches this"}, ctx)


def test_without_api_key_phone_opens_search(env, monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    from app.config import get_settings
    get_settings.cache_clear()
    ctx = conv_ctx()
    out = run("youtube_play", {"query": "kishore kumar gaane"}, ctx)
    act = _events(ctx.conversation_id, "device_action")[-1]
    assert out["video_id"] is None and act["query"] == "kishore kumar gaane"
    assert act["url"] == "https://www.youtube.com/results?search_query=kishore+kumar+gaane"


def test_play_on_tv_dial_launch_with_video_id(yt, monkeypatch):
    from app.bazar import devices as dsvc
    ctx = conv_ctx()
    tctx = Ctx(ctx.tenant_id, ctx.conversation_id)

    def ok(p):
        dsvc.command_result(ctx.tenant_id, p["command_id"], True)

    out, job = asyncio.run(_both(dispatch("youtube_play", {"query": "gpon", "on": "tv"}, tctx),
                                 _phone_answers("home_device", ok)))
    assert out["status"] == "done" and out["on"] == "tv" and "GPON basics" in out["say"]
    op = job["ops"][0]
    assert op["op"] == "dial_launch" and op["app"] == "YouTube" and op["body"] == "v=aaaaaaaaaaa"
    assert op["fallback"] and op["fallback"][0]["label"] == "SEARCH"


def test_hid_ops_refuse_a_bad_id():
    from app.bazar.connectors import device_hid as hid
    with pytest.raises(ValueError):
        hid.youtube_video_ops("x; rm", "t")
    assert hid.youtube_video_ops("aaaaaaaaaaa")[0]["body"] == "v=aaaaaaaaaaa"


def test_voice_and_family_can_use_it():
    from app import voice
    from app.voiceid import permissions
    assert "youtube_play" in voice.VOICE_TOOL_NAMES and "youtube_play" in permissions.FAMILY
