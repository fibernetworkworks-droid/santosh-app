"""v0.999.35 STUDIO WORKSPACE (owner, her screenshots of the "Setting the stage" screen and the Hoola chat: "WHY PREVIEW IS
THERE AND CODE IS THERE ... PLAN LOADING WILL BE LIKE A 2ND IMAGE ... A HOOLA LOGO ANIMATION AND JUST BELOW THAT A PLAN UPDATE
... THE CHAT PANEL SHOULD BE FLEXIBLE ... BUILD WILL START DIRECT BUILDING PROTOTYPE IN THAT SPACE ... LIVE PAGES ... ARTIFACT
SPACE SAME AS CLAUDE" -> the animated design -> "GO BUILD"): while Hoola works the chat shows ONE working row (the Hoola
mark, the real step, a clock), the panel shows the animated mark with each planned part under it, then the plan or each
prototype page the moment it is made; no Preview / Code tabs until there is something to look at; one Claude-style header
row (Preview / Code switch, title, More, close); the chat is resizable and the panel can be closed and opened again."""
import concurrent.futures
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v0999_24_prototype import _site, proto  # noqa: F401  (fixture)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

CONSOLE = Path(__file__).parents[1] / "app" / "static" / "console"


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.142"


def test_the_design_is_in_the_studio():
    js, css = (CONSOLE / "webstudio.js").read_text(), (CONSOLE / "webstudio.css").read_text()
    for m in ("function workRow(", "function workPane(", "hmThink(84)", "hmThink(22)", 'class="wsplit"', "data-act=\"views-more\"",
              "data-act=\"pane-close\"", "data-act=\"pane-open\"", "act === 'wrow'", "PPICK = true", "L(p.made)"):
        assert m in js, m
    pend = js[js.index("function drawPending("):js.index("/* ================= v0.988 PROMPT FIRST")]
    assert "Setting the stage" not in pend and 'class="views"' not in pend and "data-view" not in pend   # no tabs while it plans
    assert "workRow($('#wsPendRow')" in pend and "workPane($('#wsPeek')" in pend
    bar = js[js.index("function viewsBar("):js.index("const devSeg = () =>")]
    first = bar[:bar.index("const pv =")]
    assert "panelHead(" in first and "data-view" not in first            # the first build: title + status + close, no tabs
    state = js[js.index("function drawState()"):js.index("} else if (st.length && a.ended) {")]
    assert "workRow(box," in state and "chatact wcard" not in state       # the chat's work card is the working row now
    block = css.split("v0.999.35 STUDIO WORKSPACE", 1)[1]
    for m in (".wsplit{", ".wsp.pclosed .pane", ".pvseg button[aria-pressed=\"true\"]", ".wsx-ups li", ".vmenu{", "prefers-reduced-motion"):
        assert m in block, m
    assert "font-weight:700" not in block and "font-weight:800" not in block


class _Serial:
    """One page after another, so the test can look between pages."""

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def map(self, fn, items):
        return [fn(x) for x in items]

    def submit(self, fn, *a, **k):                   # asyncio uses the same name for its own pool
        f = concurrent.futures.Future()
        try:
            f.set_result(fn(*a, **k))
        except BaseException as e:                   # noqa: BLE001
            f.set_exception(e)
        return f

    def shutdown(self, *a, **k):
        pass


def test_each_prototype_page_shows_the_moment_it_is_made(proto, monkeypatch):
    from app.main import app
    from app.site import prototype as PT
    from app.site import service as S
    monkeypatch.setattr(concurrent.futures, "ThreadPoolExecutor", _Serial)
    seen, orig = [], PT._page_copy

    def spy(r, pg, brief):
        r2 = S._load(r.id)
        made = PT.view(r2)["made"]
        seen.append([m["slug"] for m in made])
        if made:
            page = PT.render(r2, made[0]["slug"])
            assert "being made" in page and made[0]["title"] in page
            assert made[0]["url"].split("?")[0].endswith(f"__proto/{made[0]['slug']}.html") and made[0]["sections"]
            assert PT.view(r2)["total"] >= len(made)
        return orig(r, pg, brief)
    monkeypatch.setattr(PT, "_page_copy", spy)
    sid = _site(TestClient(app))
    assert seen and seen[0] == [] and all(len(seen[i]) == i for i in range(len(seen)))   # one more page each time
    g = S.get(T, sid)["prototype"]
    assert g["status"] == "ready" and g["made"] == [] and g["total"] == 0          # the version is written: no half list
    assert not (PT._dir(S._load(sid)) / "making.json").exists()
    assert "version 1" in PT.render(S._load(sid), g["pages"][0]["slug"])


def test_the_workspace_in_a_browser(arena_server, proto):
    base, browser, key = arena_server
    from app.site import activity as AC
    errors, held, tk = [], [], {}
    ctx = browser.new_context(viewport={"width": 1400, "height": 860})
    ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))

    def hold(route):
        if not tk:
            tk["t"] = (route.request.post_data_json or {}).get("ticket") or ""
            AC.step(T, "stage-" + tk["t"], "Reading your idea.")
            AC.step(T, "stage-" + tk["t"], "Planning the pages and what each one holds.")
            held.append(route)
        else:
            route.continue_()
    page.route("**/api/sites", lambda r: hold(r) if r.request.method == "POST" else r.continue_())
    page.goto(f"{base}/console/web#/")
    page.locator("#wsAsk").wait_for(timeout=20000)
    page.fill("#wsAsk", "Sharma Sweets mithai dukaan ki website, online order WhatsApp par")
    page.click("button.go")
    # the start: one working row in the chat, the animated mark in the panel, no tabs
    page.wait_for_selector("#wsPendMsgs .wrow .hck-work .hck-mark .hm3", timeout=20000)
    page.wait_for_selector("#wsPeek #wsX .wsx-mark .hm3")
    page.locator("#wsPendMsgs .hck-label", has_text="Planning the pages").wait_for(timeout=10000)
    assert page.locator("#wsPeek [data-view], #wsPeek .views").count() == 0
    assert page.locator("#wsPendMsgs .wcard").count() == 0 and "Setting the stage" not in page.inner_text("#ws")
    AC.peek(T, "stage-" + tk["t"], {"name": "Sharma Sweets", "pages": [{"title": "Home", "sections": ["Hero", "Sweets"]},
                                                                     {"title": "Order", "sections": ["WhatsApp order"]}]})
    page.locator("#wsX .wsx-ups li", has_text="Order: WhatsApp order").wait_for(timeout=10000)
    assert page.locator("#wsX .wsx-ups li.ok").count() == 1 and page.locator("#wsX .wsx-ups li.now").count() == 1
    assert page.inner_text("#wsPeek .pttl") == "Sharma Sweets"
    # the steps fold behind the row's arrow
    page.click("#wsPendMsgs [data-act='wrow']")
    assert page.locator("#wsPendMsgs .hck-work.open #wsPendSteps li").count() >= 2
    held[0].continue_()
    # the prototype: the Claude-style header (Preview / Code switch, More, close)
    page.wait_for_selector("#wsPane .pvseg [data-view='code']", timeout=60000)
    assert page.locator("#wsPane .views").count() == 0
    assert page.get_attribute("#wsPane .pvseg [data-view='preview']", "aria-label") == "Prototype"
    page.click("#wsPane [data-act='views-more']")
    page.click("#wsPane .vmenu [data-view='settings']")
    page.wait_for_selector("#wsPane :text('Business details')", timeout=15000)
    assert "Settings" in page.inner_text("#wsPane .vmore")
    page.click("#wsPane .pvseg [data-view='preview']")
    page.wait_for_selector("#wsPane .frame iframe")
    # the chat is resizable and remembers it
    w0 = page.evaluate("document.querySelector('.wsp .chat').getBoundingClientRect().width")
    sp = page.locator(".wsplit").bounding_box()
    page.mouse.move(sp["x"] + 4, sp["y"] + 200)
    page.mouse.down()
    page.mouse.move(sp["x"] + 124, sp["y"] + 200, steps=6)
    page.mouse.up()
    w1 = page.evaluate("document.querySelector('.wsp .chat').getBoundingClientRect().width")
    assert 100 < w1 - w0 < 140, (w0, w1)
    assert abs(int(page.evaluate("localStorage.getItem('hoola.ws.chatw')")) - w1) <= 1
    page.dblclick(".wsplit")
    assert abs(page.evaluate("document.querySelector('.wsp .chat').getBoundingClientRect().width") - w0) <= 1
    # close the panel: the chat takes the width; Show panel brings it back
    page.click("#wsPane [data-act='pane-close']")
    assert page.locator(".wsp.pclosed").count() == 1 and not page.locator("#wsPane").is_visible()
    page.click(".top [data-act='pane-open']")
    assert page.locator(".wsp.pclosed").count() == 0 and page.locator("#wsPane").is_visible()
    ctx.close()
    errors = [e for e in errors if "The document is sandboxed" not in e]
    assert not errors, errors
