"""v0.999.79 HOOLA MUSIC (owner: "WE WILL BUILD OUR OWN SUNO -- FOR MUSIC" -> "MAKE IT FOR GLOBAL ... ALL LANGUAGES" ->
"ADD AI CHAT TO ALL BOARDS -- SAME LIKE VIDEOS AND IMAGE" -> "START THE BUILD"; canvas claude.ai/artifact/Qq4WmnjktJD7VS9torkejn).

The Create > Music page is the Image page's twin: its own chat (Conversation kind 'music'), the same chat bar, Song settings
above the box (any language), songs made in versions on the Create shelf and shown as sets in the chat, free edits as new
versions, and the M0 music test card. These tests hold the server half, the card, the page's pieces and a browser walk."""
import asyncio
import io
import json
import os
import shutil
import subprocess
import time
import urllib.request
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server" / "app" / "static" / "console"
JS = (CON / "studio.js").read_text()
CSS = (CON / "studio.css").read_text()


def _wav(seconds=2.0, rate=8000):
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        import math
        w.writeframes(b"".join(int(8000 * math.sin(i / 8)).to_bytes(2, "little", signed=True) for i in range(int(seconds * rate))))
    return b.getvalue()


def test_music_chat_is_its_own_chat(env):
    from app import musicchat
    from app.callconv import not_call
    from app.db import Conversation, session
    from sqlalchemy import select
    c = musicchat.new_chat("default")
    assert c["new"] and musicchat.is_music(c["id"]) and musicchat.owns("default", c["id"])
    assert musicchat.new_chat("default")["id"] == c["id"]
    with session() as s:
        ids = [x.id for x in s.scalars(select(Conversation).where(Conversation.tenant_id == "default", not_call())).all()]
    assert c["id"] not in ids
    b = musicchat.block("default", c["id"])
    for k in ("<music_chat>", "create_studio action=song", "action=song_edit", "ANY language", "Rs 7", "No songs made in this chat yet.",
              "Never copy a named real singer"):
        assert k in b, k


def test_turn_hooks_routes_and_schema():
    sant = (ROOT / "server" / "app" / "agent" / "santosh.py").read_text()
    assert "_musc.is_music(conversation_id)" in sant and "_musc.block, tenant_id, conversation_id" in sant
    assert "adm.admit_families(_musc.FAMILIES)" in sant
    main = (ROOT / "server" / "app" / "main.py").read_text()
    assert "_musicchat_mod.mount(app, current_tenant, require_key)" in main
    assert "versions: int = Field(default=1, ge=1, le=4)" in main and 'language: str = Field(default="Auto"' in main
    from app.agent import tools
    spec = next(t for t in tools.TOOLS if t["name"] == "create_studio")
    props = spec["input_schema"]["properties"]
    assert "song_edit" in props["action"]["enum"] and {"versions", "keep_out", "id", "steps"} <= set(props)


def test_song_prompt_is_for_the_whole_world():
    from app.create import service as cs
    p = cs.song_prompt("a road trip with friends", "Reggaeton", "Auto", "group", lyrics="[Coro]\nEsta noche no se acaba")
    assert "in the language(s) of the lyrics" in p and "group of singers" in p and "pop" not in p.split(",")[0].lower().replace("reggaeton", "")
    assert "Indian" not in cs.song_prompt("study", "", vocals="none")
    q = cs.song_prompt("x", "Pop", "Japanese", "female", keep_out="autotune", take=1)
    assert "in Japanese" in q and "Keep these out of the song: autotune." in q and "another version" in q


def test_songs_land_on_the_shelf_in_versions_and_in_the_chat(env, monkeypatch):
    from app import musicchat
    from app.agent.create_tools import create_studio
    from app.create import jobs, service as cs
    monkeypatch.setattr(cs, "ready", lambda: {"song": True})
    calls = []

    async def fake_song(*a):
        calls.append(a)
        return {"bytes": _wav(), "ext": ".wav", "prompt": "p", "model": "test"}
    monkeypatch.setattr(cs, "song", fake_song)
    conv = musicchat.new_chat("default")["id"]

    class Ctx:
        tenant_id, conversation_id, actor = "default", conv, "owner"

    async def go():
        r = await create_studio(Ctx(), "song", brief="a summer song", genre="Afrobeats", language="Swahili", vocals="female",
                                versions=2, keep_out="autotune", lyrics="[Chorus]\nTucheze pamoja")
        assert r["status"] == "making" and r["versions"] == 2 and r["about_inr"] == 14 and r["credits"] == 160
        assert "do not say they are ready" in r["note"]
        pub = jobs.get("default", r["job"])
        assert pub["conv"] == conv and pub["count"] == 2
        for _ in range(100):
            if jobs.get("default", r["job"])["status"] != "running":
                break
            await asyncio.sleep(0.05)
        return r
    r = asyncio.run(go())
    assert jobs.get("default", r["job"])["status"] == "done", jobs.get("default", r["job"])
    assert len(calls) == 2 and calls[0][8] == "autotune" and calls[0][9] == 0 and calls[1][9] == 1   # keep_out, take
    its = [i for i in jobs.shelf("default") if (i.get("meta") or {}).get("job") == r["job"]]
    assert sorted(i["meta"]["version"] for i in its) == ["A", "B"] and all(i["meta"]["chat"] == conv and i["meta"]["credits"] == 80 for i in its)
    if shutil.which("ffprobe"):
        assert all(abs(i["meta"]["seconds"] - 2.0) < 0.3 for i in its)
    b = musicchat.block("default", conv)
    assert "version A" in b and "version B" in b and its[0]["id"] in b and "Tucheze pamoja" in b
    # outside the Music chat a song is still made at once, as before
    assert "_in_music(ctx)" in (ROOT / "server" / "app" / "agent" / "create_tools.py").read_text()


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg")
def test_a_free_edit_is_a_new_version(env):
    from app import musicchat
    from app.agent.create_tools import create_studio
    from app.agent.tools import ToolError
    from app.create import jobs
    conv = musicchat.new_chat("default")["id"]
    src = jobs.keep("default", "song", "Lagos Nights · A", ".wav", _wav(4.0), {"chat": conv, "job": "cj_x", "version": "A", "genre": "Afrobeats"})

    class Ctx:
        tenant_id, conversation_id, actor = "default", conv, "owner"
    r = asyncio.run(create_studio(Ctx(), "song_edit", id=src["id"], steps=[{"op": "trim", "start": 0, "end": 2}, {"op": "fade", "out": 1}]))
    assert r["status"] == "done" and r["from"] == src["id"] and abs(r["seconds"] - 2.0) < 0.3
    new = next(i for i in jobs.shelf("default") if i["id"] == r["id"])
    assert new["kind"] == "song" and new["meta"]["parent"] == src["id"] and new["meta"]["inr"] == 0 and new["meta"]["chat"] == conv
    assert new["meta"]["edit"] == "trim, fade" and new["meta"]["genre"] == "Afrobeats"
    assert any(i["id"] == src["id"] for i in jobs.shelf("default"))          # the old version stays
    assert f"edited from {src['id']}" in musicchat.block("default", conv)
    for bad in ({"id": "file_123", "steps": [{"op": "fade", "out": 1}]}, {"id": src["id"], "steps": []},
                {"id": src["id"], "steps": [{"op": "explode"}]}):
        with pytest.raises(ToolError):
            asyncio.run(create_studio(Ctx(), "song_edit", **bad))


def test_music_card_set_and_scorer():
    from app.quality import musiccard as MC
    assert MC.check_set() == [] and MC.calibrate() == []
    langs = {a["language"] for a in MC.ASKS}
    assert {"English", "Spanish", "Portuguese", "Hindi", "Arabic", "French", "Japanese", "Korean", "German", "Swahili"} <= langs
    assert MC.recall("[Chorus]\nhello bright world", "Hello, bright world!") == 1.0
    assert MC.recall("[V]\n夏の空", "夏の", "chars") == pytest.approx(2 / 3, abs=0.01)
    c = MC.free_card()
    assert c["songs"] == len(MC.ASKS) and c["scorer_ok"] and c["set_ok"] and c["inr_estimate"] == 7 * len(MC.ASKS)
    yml = (ROOT / ".github" / "workflows" / "vps-ops.yml").read_text()
    assert "music_card_check)" in yml and "music_card_try)" in yml and "--budget-inr 60" in yml
    out = subprocess.run(["python", "-m", "app.quality", "music", "--live"], capture_output=True, text=True, cwd=ROOT / "server", timeout=120)
    assert out.returncode == 2 and "--budget-inr" in out.stdout         # a live card never runs without a budget


def test_page_pieces():
    for k in ('<div class="gen vchat mchat">', 'id="mthread"', 'id="mtray"', 'data-mplus', 'data-mset', 'id="msetp"', 'id="mlyrics"',
              'data-mpick', 'id="mkeep"', 'id="mgenre"', 'data-mfilt', 'id="msq"', 'data-mhist', 'data-mnew', 'id="muGo"', 'data-improve',
              "HoolaChat.mount($('#mthread')", "hints: [hint]", "'/api/music/chat'", "'/api/music/chats'", "Song settings: kind",
              "create_studio action=song_edit", "Make the song straight away", "data-mdirect", "function mThreadList()",
              "function mChatSet(s)", "data-mset-id", "data-mchange", "data-mask", "data-mmore", "Reel cut", "'Auto', 'English', 'Spanish'",
              "'Afrobeats'", "'K-pop'", "conversation_id: MU.chat || ''", "markWork(!!working && VIEW === 'music')", "clearTimeout(mPoll)",
              "mAddFiles(e.dataTransfer.files)", "30 * 1024 * 1024"):
        assert k in JS, k
    for k in ("#muq{", ".mscard{", ".msl{", ".mver{", ".mlyr textarea{"):
        assert k in CSS, k
    assert CSS.count("{") == CSS.count("}")
    assert 'id="muGo"' in JS and "data-mtab" not in JS                    # the old form is gone


def test_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    shots = os.environ.get("CONSOLE_SHOTS")
    chat = {}

    def chat_id():
        if not chat:
            rq = urllib.request.Request(base + "/api/music/chat", headers={"Authorization": "Bearer " + key})
            chat["id"] = json.loads(urllib.request.urlopen(rq).read())["id"]
        return chat["id"]
    now = int(time.time())
    meta = {"genre": "Afrobeats", "language": "Swahili", "vocals": "female", "job": "cj_m1", "chat": chat_id(), "inr": 7, "seconds": 2,
            "brief": "a summer song for my family", "lyrics": "[Chorus]\nTucheze pamoja", "asked_seconds": 90}
    its = [{"id": "cr_s1", "kind": "song", "mime": "audio/wav", "size": 1, "title": "Family summer · A", "created": now - 5, "meta": {**meta, "version": "A"}},
           {"id": "cr_s2", "kind": "song", "mime": "audio/wav", "size": 1, "title": "Family summer · B", "created": now - 5, "meta": {**meta, "version": "B"}},
           {"id": "cr_s3", "kind": "song", "mime": "audio/wav", "size": 1, "title": "Old jingle", "created": now - 90000, "meta": {"genre": "Jingle", "language": "English"}}]

    def items(route):
        u = route.request.url.split("?")[0]
        if u.endswith("/api/create/items"):
            route.fulfill(status=200, content_type="application/json", body=json.dumps({"items": its})); return
        route.fulfill(status=200, content_type="audio/wav", body=_wav(1.0))
    made = []

    def jobs(route):
        if route.request.method == "POST":
            made.append(route.request.post_data_json)
            route.fulfill(status=200, content_type="application/json", body=json.dumps({"id": "cj_9", "kind": "song", "status": "running", "title": "x",
                                                                                        "conv": chat_id(), "count": 2, "created": now}))
            return
        route.fulfill(status=200, content_type="application/json", body=json.dumps({"jobs": []}))
    errs = []
    for scheme in ("light", "dark"):
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.route("**/api/create/items**", items)
        pg.route("**/api/create/jobs", jobs)
        if scheme == "light":
            pg.route("**/api/create", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(
                {"ready": {"song": True}, "need": {}, "voices": {"male": {}, "female": {}}, "styles": [], "languages": []})))
        pg.goto(base + "/console/?v=creative")
        pg.wait_for_selector("#cstudio #snav [data-go]", timeout=20000)
        pg.locator("#cstudio button.sn[data-go='music']").click()
        pg.wait_for_selector("#cstudio #mthread .hck-ho", timeout=15000)
        assert "Tell me the song you want, in any language" in pg.locator("#cstudio #mthread").inner_text()
        assert pg.locator("#cstudio #mopts > button").count() == 1
        pg.locator("#cstudio [data-mset]").click()
        pg.wait_for_selector("#cstudio #msetp.on")
        pg.locator("#cstudio #msetp [data-ms='versions'][data-msv='4']").click()
        assert "4 versions" in pg.locator("#cstudio [data-mset]").inner_text() and "₹28" in pg.locator("#cstudio #msetCost").inner_text()
        pg.locator("#cstudio #msetp [data-mpick='lang']").click()
        pg.wait_for_selector("#cstudio #pop:not([hidden])")
        assert pg.locator("#cstudio #pop [data-i]").count() >= 40
        pg.locator("#cstudio #pop [data-i]", has_text="Japanese").evaluate("b => b.click()")
        assert "Japanese" in pg.locator("#cstudio [data-mset]").inner_text()
        pg.locator("#cstudio #msetp [data-ms='versions'][data-msv='2']").click()
        pg.locator("#cstudio #mgenre").fill("J-pop")
        pg.locator("#cstudio #mlyrics").fill("[Chorus]\n夏の約束")
        if shots:
            pg.wait_for_timeout(400)
            pg.screenshot(path=f"{shots}/music-settings-{scheme}.png")
        pg.locator("#cstudio [data-msdone]").click()
        assert pg.locator("#cstudio #msetp").is_hidden()
        # the set made in this chat sits in the chat with both versions; Your songs on the right
        pg.wait_for_selector("#cstudio [data-mset-id='cj_m1'] .track", timeout=15000)
        assert pg.locator("#cstudio [data-mset-id='cj_m1'] .track").count() == 2
        assert pg.locator("#cstudio #tracks > .track").count() == 3
        pg.locator("#cstudio #msq").fill("jingle")
        assert pg.locator("#cstudio #tracks > .track").count() == 1
        pg.locator("#cstudio #msq").fill("")
        if shots:
            pg.wait_for_timeout(500)
            pg.screenshot(path=f"{shots}/music-chat-{scheme}.png")
        if scheme == "light":
            sent = []
            pg.on("request", lambda r: sent.append(r.post_data_json) if r.method == "POST" and r.url.endswith("/messages") else None)
            pg.locator("#cstudio #muq").fill("A summer J-pop song about a promise between friends")
            pg.locator("#cstudio #muGo").click()
            pg.wait_for_function("() => document.querySelector('#cstudio').shadowRoot.querySelectorAll('#mthread .hck-me').length >= 1", timeout=10000)
            pg.wait_for_timeout(600)
            t = sent[0]["text"]
            assert "Song settings: kind Song, language Japanese" in t and "2 versions" in t and "style J-pop" in t
            assert "{Chorus} / 夏の約束" in t and "[Web console" not in pg.locator("#cstudio #mthread .hck-me").first.inner_text()
            # a free change from the set's button is a chat message about that song
            pg.locator("#cstudio [data-mset-id='cj_m1'] [data-mask]").first.click()
            pg.wait_for_timeout(800)
            assert len(sent) == 2 and "30 second reel cut of Family summer · A" in sent[1]["text"]
            # More like this: the same words and settings, straight away, into this chat
            pg.locator("#cstudio [data-mset-id='cj_m1'] [data-mmore]").click()
            pg.wait_for_timeout(600)
            assert made and made[0]["conversation_id"] == chat_id() and made[0]["versions"] == 2 and made[0]["genre"] == "Afrobeats"
            assert made[0]["language"] == "Swahili" and made[0]["title"] == "Family summer"
        if scheme == "dark":
            # her message read back from the server shows only her words, never the settings note
            pg.wait_for_selector("#cstudio #mthread .hck-me", timeout=10000)
            assert "Song settings" not in pg.locator("#cstudio #mthread").inner_text()
            assert "A summer J-pop song about a promise between friends" in pg.locator("#cstudio #mthread").inner_text()
            assert "GEMINI_API_KEY" in pg.locator("#cstudio #mprice").inner_text()
            n = len(made)
            pg.locator("#cstudio [data-mset-id='cj_m1'] [data-mmore]").click()
            pg.wait_for_timeout(600)
            assert len(made) == n
        ctx.close()
    assert errs == [], errs


from tests.test_v0312_arena_screen import arena_server  # noqa: E402,F401
from tests.test_v121_site import site_env  # noqa: E402,F401
