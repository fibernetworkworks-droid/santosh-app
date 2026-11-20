"""v0.999.43 VIDEO CHAT (owner, on the design canvas: "THIS IS TO BE A FULL CHAT PANEL -- AND AT BOTTOM THERE IS DIFFERENT
OPTIONS REGARDING VIDEO -- ALSO IN THIS CHAT USER CAN UPLOAD IMAGES, VIDEOS, DOCUMENTS, EVERY FILE" -> "GO BUILD").

The Create > Video page is a chat of its own (Conversation kind 'video'): her words + files + the options under the box go to
Hoola, who makes the clip with video_studio action=clip (one call: plan, her photo as the first frame, the price card); the
clip's card sits in the chat; Your videos has filters + search; if Hoola cannot answer, the clip can still be made straight
away. These tests hold the server half, the page's pieces and a walk in a real browser."""
import asyncio
import json
import os
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server" / "app" / "static" / "console"
JS = (CON / "studio.js").read_text()
CSS = (CON / "studio.css").read_text()


def test_video_chat_is_its_own_chat(env):
    from app import videochat
    from app.callconv import not_call
    from app.db import Conversation, session
    from sqlalchemy import select
    c = videochat.new_chat("default")
    assert c["new"] and videochat.is_video(c["id"]) and videochat.owns("default", c["id"])
    assert videochat.new_chat("default")["id"] == c["id"]          # an untouched one is reused, no pile of empty chats
    assert videochat.current("default")["id"] == c["id"]
    with session() as s:                                            # never in her Hoola chat lists
        ids = [x.id for x in s.scalars(select(Conversation).where(Conversation.tenant_id == "default", not_call())).all()]
    assert c["id"] not in ids
    assert not videochat.owns("someone-else", c["id"])
    b = videochat.block("default", c["id"])
    assert "<video_chat>" in b and "video_studio action=clip" in b and "start_image_file_id" in b and "file_read" in b
    assert "No clips made in this chat yet." in b and "nothing is spent until she" in b


def test_turn_hooks_and_routes():
    sant = (ROOT / "server" / "app" / "agent" / "santosh.py").read_text()
    assert "_vidc.is_video(conversation_id)" in sant and "_vidc.block, tenant_id, conversation_id" in sant
    assert "adm.admit_families(_vidc.FAMILIES)" in sant
    main = (ROOT / "server" / "app" / "main.py").read_text()
    assert "_videochat_mod.mount(app, current_tenant, require_key)" in main
    assert "start_image_file_id: str = Field(" in main and "conversation_id: str = Field(" in main
    assert "await _studio_call(ss.clip)(" in main
    for f in ("callconv.py", "convs.py"):
        assert '"seo", "social", "video", "accounts")' in (ROOT / "server" / "app" / f).read_text()
    tool = (ROOT / "server" / "app" / "agent" / "studio_tools.py").read_text()
    assert '"clip", "create"' in tool and "await ss.clip(t," in tool and '"start_image_file_id": {"type": "string"}' in tool


def _fake(env, tmp_path, monkeypatch):
    from app.studio import service as ss
    from app.studio import studio as stmod
    st = stmod.Studio(tmp_path / "st")

    async def fake_studio(tenant):
        return st

    async def fake_plan(tenant, project, brief="", seconds=30, conversation_id=""):
        st.storyboard_set(project, [{"kind": "scene", "prompt": "Steam over a kulhad of chai", "duration": 8}])
        return {"status": "planning"}
    seen = {}

    async def fake_generate(tenant, project, quality="preview", shot_ids=None, variants=1, model=None, conversation_id="", compare=None):
        seen.update(project=project, quality=quality, variants=variants, model=model, conv=conversation_id, compare=compare,
                    shots=st.load(project)["shots"])
        return {"card": True}
    monkeypatch.setattr(ss, "studio", fake_studio)
    monkeypatch.setattr(ss, "studio_sync", lambda tenant: st)
    monkeypatch.setattr(ss, "plan", fake_plan)
    monkeypatch.setattr(ss, "generate", fake_generate)
    monkeypatch.setattr(ss, "_changed", lambda *a, **k: None)
    monkeypatch.setattr(ss, "_publish", lambda *a, **k: None)
    return ss, st, seen


def test_one_call_clip_with_her_photo_as_the_first_frame(env, tmp_path, monkeypatch):
    ss, st, seen = _fake(env, tmp_path, monkeypatch)
    pic = st.home / "uploads" / "frames" / "f1.png"
    pic.parent.mkdir(parents=True, exist_ok=True)
    pic.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    monkeypatch.setattr(ss, "_her_file", lambda tenant, s, fid, sub, kinds: pic)

    async def main():
        v = await ss.clip("default", "Chai on a rainy balcony", name="Clip 20 Nov 10:01", aspect="9:16", seconds=8,
                          resolution="1080p", auto="value", variants=2, audio=False, start_image_file_id="f1",
                          conversation_id="vc1")
        await ss._then[ss._key("default", v["project"])]
        return v
    v = asyncio.run(main())
    assert v["chat"] == "vc1" and v["start_frame"] is True and v["created_ts"] > 0
    assert seen["project"] == "Clip 20 Nov 10:01" and seen["variants"] == 2 and seen["conv"] == "vc1"
    assert seen["shots"][0]["start_image"] == str(pic)               # her photo is the first frame of the first shot
    assert seen["shots"][0]["audio"] is False                        # Sound off reached every shot
    assert st.load(v["project"])["prefs"]["auto"] == "value" and st.load(v["project"])["prefs"]["resolution"] == "1080p"

    async def again():           # a second clip in the same minute gets its own name, never overwrites the first
        return await ss.clip("default", "Second one", name="Clip 20 Nov 10:01", then="")
    v2 = asyncio.run(again())
    assert v2["project"] == "Clip 20 Nov 10:01 (2)"


def test_clip_refuses_clearly(env, tmp_path, monkeypatch):
    ss, st, seen = _fake(env, tmp_path, monkeypatch)
    for kw, msg in ((dict(brief=""), "Describe the shot first"), (dict(brief="x", compare=["a"]), "2 or 3 models"),
                    (dict(brief="x", then="later"), "then = generate")):
        b = kw.pop("brief")
        try:
            asyncio.run(ss.clip("default", b, **kw))
        except ss.StudioJobError as e:
            assert msg in str(e)
        else:
            raise AssertionError(kw)


def test_page_pieces():
    for k in ('<div class="gen vchat">', 'id="vthread"', 'id="vtray"', 'data-vplus', 'data-vcamopen', 'data-pickmodel',
              "data-vopt", 'data-vaudio', 'data-vfilt', 'id="vq"', 'data-vhist', 'data-vnew', 'id="vidGo"', 'data-improve',
              "HoolaChat.mount($('#vthread')", "hints: [hint]", "hint = settingsLine()", "'/api/video/chat'", "'/api/video/chats'",
              "/files`, undefined, {form: fd}", "start_image_file_id: first?.file_id || ''", "conversation_id: VID.chat || ''",
              "Make the clip straight away", "data-vdirect", "function threadList()", "function chatClip(p)", "data-vclip",
              "function camSheet()", "CAMG.map(", "data-vagain", "Change and make again", "addFiles(e.dataTransfer.files)",
              "e.clipboardData?.files", "30 * 1024 * 1024", "rzBind($('.rz-pane', gen), gen.classList.contains('vchat') ? 'cw' : 'pw')",
              '<link rel="stylesheet" href="/static/console/chatkit.css'):
        assert k in JS, k
    # the 26 camera moves, each with its own drawing, in seven groups
    names = [n for _, ms in __import__("re").findall(r"\['([^']+)', \[([^\]]+)\]\]", JS[JS.index("const CAMG"):JS.index("const CAMD")]) for n in [ms]]
    moves = sum(len(__import__("re").findall(r"'([^']+)'", m)) for m in names)
    assert moves == 26
    for k in (".gen.vchat{", ".vbox{", ".vfile{", ".vo{", ".vseg{", ".camsheet{", ".csm[aria-pressed=\"true\"]", ".vcl{", ".vlbb{"):
        assert k in CSS, k
    assert CSS.count("{") == CSS.count("}")


def test_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    shots = os.environ.get("CONSOLE_SHOTS")
    chat = {}

    def chat_id():
        if not chat:
            rq = urllib.request.Request(base + "/api/video/chat", headers={"Authorization": "Bearer " + key})
            chat["id"] = json.loads(urllib.request.urlopen(rq).read())["id"]
        return chat["id"]
    now = time.time()
    shot = {"id": "s1", "prompt": "Steam rising from a clay kulhad of chai on a rainy balcony, slow dolly in", "duration": 8,
            "kind": "scene", "phase": "", "take_list": []}
    appr = {"id": "ap1", "kind": "generate", "shots": 1, "quality": "final", "inr": 136,
            "rows": [{"name": "Hoola Auto", "seconds": 8, "takes": 1, "resolution": "1080p", "inr": 136}]}

    made = {"clip": False}

    def studio(route):
        ps = [{"project": "Chai reel", "aspect": "9:16", "brief": "Chai on a rainy balcony", "shots": [shot], "outputs": [],
               "approvals": [appr], "seconds": 8, "chat": chat_id(), "created_ts": now + 5, "start_frame": True},
              {"project": "Mountain dawn", "aspect": "16:9", "brief": "Mountain dawn, slow drone", "shots": [], "outputs": [],
               "approvals": [], "seconds": 6, "chat": "", "created_ts": now - 900, "error": "The video engine is not connected."}]
        route.fulfill(status=200, content_type="application/json", body=json.dumps({"projects": ps[0 if made["clip"] else 1:], "available": True}))
    direct = []

    def projects(route):
        direct.append(route.request.post_data_json)
        made["clip"] = True
        route.fulfill(status=200, content_type="application/json", body="{}")
    errs = []
    for scheme in ("light", "dark"):
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.route("**/api/studio", studio)
        pg.route("**/api/studio/projects", projects)
        pg.goto(base + "/console/?v=creative")
        pg.wait_for_selector("#cstudio #snav [data-go]", timeout=20000)
        pg.locator("#cstudio button.sn[data-go='video']").click()
        pg.wait_for_selector("#cstudio #vthread .hck-ho", timeout=15000)
        assert "Tell me the shot you want" in pg.locator("#cstudio #vthread").inner_text()
        # every option sits under the box, the drawn menus open, the camera sheet has all 26 moves
        pg.locator("#cstudio [data-vopt='shape']").click()
        pg.wait_for_selector("#cstudio #pop:not([hidden])")
        pg.locator("#cstudio #pop [role=menuitemradio]", has_text="16:9").click()
        assert "16:9" in pg.locator("#cstudio [data-vopt='shape']").inner_text()
        pg.locator("#cstudio [data-vcamopen]").click()
        pg.wait_for_selector("#cstudio #camsheet .csm")
        assert pg.locator("#cstudio #camsheet [data-vcam]").count() == 26
        if shots:
            pg.wait_for_timeout(300)
            pg.screenshot(path=f"{shots}/video-camera-{scheme}.png")
        pg.locator("#cstudio #camsheet [data-vcam='Dolly in']").click()
        assert "Dolly in" in pg.locator("#cstudio [data-vcamopen]").inner_text()
        # a photo goes into the tray and is the first frame
        with pg.expect_file_chooser() as fc:
            pg.locator("#cstudio [data-vplus]").click()
        fc.value.set_files(files=[{"name": "kulhad.png", "mimeType": "image/png", "buffer": b"\x89PNG\r\n\x1a\n" + b"0" * 200}])
        pg.wait_for_selector("#cstudio .vfile .vff[aria-pressed='true']", timeout=10000)
        # Your videos: the filters work
        pg.wait_for_selector("#cstudio #results .res", timeout=10000)
        n0 = pg.locator("#cstudio #results .res").count()
        pg.locator("#cstudio [data-vfilt='ok']").click()
        assert pg.locator("#cstudio #results .res").count() == 0
        pg.locator("#cstudio [data-vfilt='na']").click()
        assert pg.locator("#cstudio #results .res").count() == n0      # a price card / a failure both need her
        pg.locator("#cstudio [data-vfilt='all']").click()
        pg.locator("#cstudio #vq").fill("mountain")
        assert pg.locator("#cstudio #results .res").count() == 1
        pg.locator("#cstudio #vq").fill("")
        if scheme == "light":
            sent = []
            pg.on("request", lambda r: sent.append(r.post_data_json) if r.method == "POST" and r.url.endswith("/messages") else None)
            pg.locator("#cstudio #vidq").fill("Make an 8 second reel of this kulhad for Instagram")
            pg.locator("#cstudio #vidGo").click()
            pg.wait_for_function("() => document.querySelector('#cstudio').shadowRoot.querySelectorAll('#vthread .hck-me').length >= 1", timeout=10000)
            pg.wait_for_timeout(600)
            assert sent and sent[0]["files"] and "Video settings: shape 16:9" in sent[0]["text"] and "camera Dolly in" in sent[0]["text"]
            assert "start_image_file_id" in sent[0]["text"]
            assert "[Web console" not in pg.locator("#cstudio #vthread .hck-me").first.inner_text()   # her bubble = her words
            assert pg.locator("#cstudio .vtray .vfile").count() == 0
            # Hoola cannot answer here (no model key): the same clip can be made straight away, into this chat
            pg.wait_for_selector("#cstudio [data-vdirect]", timeout=30000)
            pg.locator("#cstudio [data-vdirect]").click()
            pg.wait_for_timeout(600)
            assert direct and direct[0]["conversation_id"] == chat_id() and direct[0]["start_image_file_id"].startswith("file_")
            assert direct[0]["aspect"] == "16:9" and direct[0]["then"] == "generate" and "Dolly in" not in direct[0]["brief"].split("\n")[0]
        # the clip made in this chat shows its card in the chat, with the price card
        pg.wait_for_selector("#cstudio [data-vclip='Chai reel'] .appr", timeout=15000)
        if shots:
            pg.wait_for_timeout(500)
            pg.screenshot(path=f"{shots}/video-chat-{scheme}.png")
        ctx.close()
    assert not errs, errs


from tests.test_v0312_arena_screen import arena_server  # noqa: E402,F401
from tests.test_v121_site import site_env  # noqa: E402,F401
