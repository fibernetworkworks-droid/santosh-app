"""v0.999.53 IMAGE CHAT (owner: "DESIGN SHOULD BE SAME AS HOOLA VIDEO SECTION -- SHOW DESIGN FIRST" -> design canvas
claude.ai/artifact/MADqzZqiUDde71pFpJ95f7 -> "GO BUILD").

The Create > Image page is the Video page's twin: its own chat (Conversation kind 'image'), the same chat bar (+, one
settings button, Improve, Send), Picture settings above the box, picture sets inside the chat, Your pictures in their real
shapes, an opened picture with its words and what to do next. Hoola makes the pictures with create_studio action=image on
the same engine and shelf as before. These tests hold the server half, the page's pieces and a walk in a real browser."""
import asyncio
import io
import json
import os
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server" / "app" / "static" / "console"
JS = (CON / "studio.js").read_text()
CSS = (CON / "studio.css").read_text()


def test_image_chat_is_its_own_chat(env):
    from app import imagechat
    from app.callconv import not_call
    from app.db import Conversation, session
    from sqlalchemy import select
    c = imagechat.new_chat("default")
    assert c["new"] and imagechat.is_image(c["id"]) and imagechat.owns("default", c["id"])
    assert imagechat.new_chat("default")["id"] == c["id"]          # an untouched one is reused
    assert imagechat.current("default")["id"] == c["id"]
    with session() as s:                                            # never in her Hoola chat lists
        ids = [x.id for x in s.scalars(select(Conversation).where(Conversation.tenant_id == "default", not_call())).all()]
    assert c["id"] not in ids
    assert not imagechat.owns("someone-else", c["id"])
    b = imagechat.block("default", c["id"])
    assert "<image_chat>" in b and "create_studio action=image" in b and "file_read" in b and "Rs 3" in b
    assert "No pictures made in this chat yet." in b


def test_turn_hooks_and_routes():
    sant = (ROOT / "server" / "app" / "agent" / "santosh.py").read_text()
    assert "_imgc.is_image(conversation_id)" in sant and "_imgc.block, tenant_id, conversation_id" in sant
    assert "adm.admit_families(_imgc.FAMILIES)" in sant
    main = (ROOT / "server" / "app" / "main.py").read_text()
    assert "_imagechat_mod.mount(app, current_tenant, require_key)" in main
    for f in ("callconv.py", "convs.py"):
        assert '"video", "image", "accounts"' in (ROOT / "server" / "app" / f).read_text()
    from app import imagechat
    from app.agent.tools import FAMILY_OF
    assert FAMILY_OF["create_studio"] in imagechat.FAMILIES and FAMILY_OF["file_read"] in imagechat.FAMILIES


def test_pictures_land_on_the_shelf_and_in_the_chat(env, monkeypatch):
    """create_studio action=image starts a job on the Image page's engine; its pictures carry the chat, the set and the words."""
    from PIL import Image
    from app import photogen
    from app.agent.create_tools import create_studio
    from app.create import jobs, service as cs
    monkeypatch.setattr(cs, "ready", lambda: {"image": True})
    buf = io.BytesIO(); Image.new("RGB", (8, 10), (200, 120, 60)).save(buf, "PNG")
    seen = []

    def fake_make(prompt, imgs, aspect, quality):
        seen.append((prompt, aspect, quality))
        return {"png": buf.getvalue(), "aspect": aspect, "model": "test", "quality": quality}
    monkeypatch.setattr(photogen, "make", fake_make)

    class Ctx:
        tenant_id, conversation_id, actor = "default", "conv_img_1", "owner"

    async def go():
        r = await create_studio(Ctx(), "image", prompt="A Diwali poster for Newtika Chai", aspect="4:5", style="Festive glow", count=2)
        assert r["status"] == "making" and r["about_inr"] == 6 and "do not say they are ready" in r["note"]
        pub = jobs.get("default", r["job"])
        assert pub["conv"] == "conv_img_1" and pub["aspect"] == "4:5" and pub["count"] == 2 and pub["style"] == "Festive glow"
        for _ in range(50):
            if jobs.get("default", r["job"])["status"] != "running":
                break
            await asyncio.sleep(0.05)
        return r
    r = asyncio.run(go())
    assert jobs.get("default", r["job"])["status"] == "done" and len(seen) == 2 and seen[0][1] == "4:5"
    its = [i for i in jobs.shelf("default") if (i.get("meta") or {}).get("job") == r["job"]]
    assert len(its) == 2 and all(i["meta"]["chat"] == "conv_img_1" and i["meta"]["inr"] == 3 and i["meta"]["style"] == "Festive glow"
                                 and i["meta"]["prompt"].startswith("A Diwali poster") for i in its)
    from app import imagechat
    b = imagechat.block("default", "conv_img_1")
    assert "4:5 Festive glow: ready" in b


def test_the_tool_refuses_clearly(env, monkeypatch):
    from app.agent.create_tools import create_studio
    from app.agent.tools import ToolError
    from app.create import service as cs

    class Ctx:
        tenant_id, conversation_id, actor = "default", "c", "owner"
    monkeypatch.setattr(cs, "ready", lambda: {"image": False})
    try:
        asyncio.run(create_studio(Ctx(), "image", prompt="a poster"))
        raise AssertionError("should refuse")
    except ToolError as e:
        assert "GEMINI_API_KEY" in str(e)
    monkeypatch.setattr(cs, "ready", lambda: {"image": True})
    try:
        asyncio.run(create_studio(Ctx(), "image"))
        raise AssertionError("should refuse")
    except ToolError as e:
        assert "prompt" in str(e)


def test_page_pieces():
    for k in ('<div class="gen vchat ichat">', 'id="ithread"', 'id="itray"', 'data-iplus', 'data-iset', 'id="isetp"', 'data-istyopen',
              'data-ibrand', 'id="iavoid"', 'data-ifilt', 'id="iq"', 'data-ihist', 'data-inew', 'id="imgGo"', 'data-improve',
              "HoolaChat.mount($('#ithread')", "hints: [hint]", "hint = await iHint()", "'/api/image/chat'", "'/api/image/chats'",
              "Make them with create_studio action=image.", "Make the pictures straight away", "data-idirect", "function iThreadList()",
              "function chatSet(s)", "data-iset-id", "function iStyleSheet()", "data-ichange", "Change this picture", "More like this",
              "Copy the words", "iAddFiles(e.dataTransfer.files)", "e.clipboardData?.files", "30 * 1024 * 1024", "class=\"sgrid pgrid\"",
              "--ar:${arOf(", "conversation_id: IMG.chat || ''", "markWork(!!working && VIEW === 'image')", "clearTimeout(iPoll)"):
        assert k in JS, k
    assert JS.count("const STYLES = [") == 1 and "'Indian folk art'" in JS
    for k in ("#imgq{", ".pgrid{", ".iscard{", ".isp{", ".istg{", ".ivin{", ".ilb .lbm img{"):
        assert k in CSS, k
    assert CSS.count("{") == CSS.count("}")
    assert "Readable Indian scripts" not in JS and "data-imode" not in JS      # the old form is gone


def test_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    shots = os.environ.get("CONSOLE_SHOTS")
    chat = {}

    def chat_id():
        if not chat:
            rq = urllib.request.Request(base + "/api/image/chat", headers={"Authorization": "Bearer " + key})
            chat["id"] = json.loads(urllib.request.urlopen(rq).read())["id"]
        return chat["id"]
    from PIL import Image
    now = int(time.time())

    def png(w, h, c):
        b = io.BytesIO(); Image.new("RGB", (w, h), c).save(b, "PNG"); return b.getvalue()
    its = [{"id": "cr_a1", "kind": "image", "mime": "image/png", "size": 1, "title": "Diwali poster for Newtika Chai", "created": now - 5,
            "meta": {"aspect": "4:5", "style": "Festive glow", "inr": 3, "job": "cj_1", "chat": chat_id(), "prompt": "A Diwali poster for Newtika Chai with a Hindi headline"}},
           {"id": "cr_a2", "kind": "image", "mime": "image/png", "size": 1, "title": "Diwali poster for Newtika Chai", "created": now - 5,
            "meta": {"aspect": "4:5", "style": "Festive glow", "inr": 3, "job": "cj_1", "chat": chat_id(), "prompt": "A Diwali poster for Newtika Chai with a Hindi headline"}},
           {"id": "cr_b1", "kind": "image", "mime": "image/png", "size": 1, "title": "Monsoon offer banner", "created": now - 90000,
            "meta": {"aspect": "16:9", "style": "Cinematic", "inr": 12}}]

    def items(route):
        u = route.request.url.split("?")[0]
        if u.endswith("/api/create/items"):
            route.fulfill(status=200, content_type="application/json", body=json.dumps({"items": its})); return
        i = u.rsplit("/", 1)[1]
        route.fulfill(status=200, content_type="image/png", body=png(*({"cr_b1": (32, 18)}.get(i, (16, 20))), (210, 140, 70)))
    made = []

    def jobs(route):
        if route.request.method == "POST":
            made.append(route.request.post_data_json)
            route.fulfill(status=200, content_type="application/json", body=json.dumps({"id": "cj_9", "kind": "image", "status": "running", "title": "x",
                                                                                        "conv": chat_id(), "aspect": "4:5", "count": 2, "created": now}))
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
        if scheme == "light":                     # the picture engine set up; in dark it is not, as on this test server
            pg.route("**/api/create", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(
                {"ready": {"image": True}, "need": {}, "voices": {"male": {}, "female": {}}, "styles": [], "languages": []})))
        pg.goto(base + "/console/?v=creative")
        pg.wait_for_selector("#cstudio #snav [data-go]", timeout=20000)
        pg.locator("#cstudio button.sn[data-go='image']").click()
        pg.wait_for_selector("#cstudio #ithread .hck-ho", timeout=15000)
        assert "Tell me the picture you want" in pg.locator("#cstudio #ithread").inner_text()
        # the chat bar: + , one settings button, the engine, Improve, Send
        assert pg.locator("#cstudio #iopts > button").count() == 1
        pg.locator("#cstudio [data-iset]").click()
        pg.wait_for_selector("#cstudio #isetp.on")
        pg.locator("#cstudio #isetp [data-is='aspect'][data-isv='4:5']").click()
        pg.locator("#cstudio #isetp [data-is='count'][data-isv='2']").click()
        assert "4:5" in pg.locator("#cstudio [data-iset]").inner_text() and "₹6" in pg.locator("#cstudio #isetCost").inner_text()
        if shots:
            pg.wait_for_timeout(400)
            pg.screenshot(path=f"{shots}/image-settings-{scheme}.png")
        pg.locator("#cstudio #isetp [data-istyopen]").click()
        pg.wait_for_selector("#cstudio #camsheet .csm")
        assert pg.locator("#cstudio #camsheet [data-isty]").count() == 9
        if shots:
            pg.wait_for_timeout(300)
            pg.screenshot(path=f"{shots}/image-style-{scheme}.png")
        pg.locator("#cstudio #camsheet [data-isty='3']").click()
        assert "Festive glow" in pg.locator("#cstudio #isetp [data-istyopen]").inner_text()
        pg.locator("#cstudio [data-isdone]").click()
        assert pg.locator("#cstudio #isetp").is_hidden()
        # the set made in this chat sits in the chat; Your pictures keep their shapes
        pg.wait_for_selector("#cstudio [data-iset-id='cj_1'] .isp img[src^='blob:']", timeout=15000)
        assert pg.locator("#cstudio [data-iset-id='cj_1'] .isp").count() == 2
        assert pg.locator("#cstudio #results .res.pic").count() == 3
        assert pg.locator("#cstudio #results .res.pic").last.get_attribute("style") == "--ar:16 / 9"
        pg.locator("#cstudio #iq").fill("monsoon")
        assert pg.locator("#cstudio #results .res.pic").count() == 1
        pg.locator("#cstudio #iq").fill("")
        pg.locator("#cstudio [data-ifilt='mk']").click()
        assert pg.locator("#cstudio #results .res.pic").count() == 0
        pg.locator("#cstudio [data-ifilt='all']").click()
        if shots:
            pg.wait_for_timeout(500)
            pg.screenshot(path=f"{shots}/image-chat-{scheme}.png")
        # an opened picture: its words, settings, price and what to do next
        pg.locator("#cstudio [data-iset-id='cj_1'] .isp").first.click()
        pg.wait_for_selector("#cstudio #lightbox .ilb")
        lb = pg.locator("#cstudio #lightbox").inner_text()
        assert "A Diwali poster for Newtika Chai" in lb and "Festive glow" in lb and "4:5 · Instagram post" in lb and "₹3" in lb
        for t in ("Download", "Change this picture", "More like this", "Use as a reference", "Delete"):
            assert t in lb, t
        if shots:
            pg.wait_for_timeout(400)
            pg.screenshot(path=f"{shots}/image-open-{scheme}.png")
        pg.locator("#cstudio #lightbox [data-ichange]").click()
        assert pg.locator("#cstudio #lightbox").is_hidden()
        assert pg.locator("#cstudio #itray .vfile").count() == 1 and pg.locator("#cstudio #imgq").input_value() == "Change this picture: "
        if scheme == "light":
            sent = []
            pg.on("request", lambda r: sent.append(r.post_data_json) if r.method == "POST" and r.url.endswith("/messages") else None)
            pg.locator("#cstudio #imgq").fill("Change this picture: make the headline bigger")
            pg.locator("#cstudio #imgGo").click()
            pg.wait_for_function("() => document.querySelector('#cstudio').shadowRoot.querySelectorAll('#ithread .hck-me').length >= 1", timeout=10000)
            pg.wait_for_timeout(600)
            assert sent and "Image settings: shape 4:5, style Festive glow" in sent[0]["text"] and "2 pictures" in sent[0]["text"]
            assert "reference pictures file_ids cr_a" in sent[0]["text"] and sent[0]["files"] == []     # a shelf picture rides the settings note
            assert "[Web console" not in pg.locator("#cstudio #ithread .hck-me").first.inner_text()
            assert pg.locator("#cstudio #itray .vfile").count() == 0
            # More like this: the same words and settings, straight away, into this chat
            pg.locator("#cstudio [data-iset-id='cj_1'] [data-imore]").click()
            pg.wait_for_timeout(600)
            assert made and made[0]["conversation_id"] == chat_id() and made[0]["aspect"] == "4:5" and made[0]["count"] == 2
            assert made[0]["style"] == "Festive glow" and made[0]["prompt"].startswith("A Diwali poster")
        if scheme == "dark":                      # an engine that is not set up is said under the box, and nothing starts
            assert "GEMINI_API_KEY" in pg.locator("#cstudio #iprice").inner_text()
            n = len(made)
            pg.locator("#cstudio [data-iset-id='cj_1'] [data-imore]").click()
            pg.wait_for_timeout(600)
            assert len(made) == n
        ctx.close()
    assert errs == [], errs


from tests.test_v0312_arena_screen import arena_server  # noqa: E402,F401
from tests.test_v121_site import site_env  # noqa: E402,F401
