"""v0.986 PLAN PEEK (owner, her screenshot of the Studio's 'Starting' screen: "NO PROPER LOADING ... SECTION IN CHAT SPACE
... NOT CHAT SECTION EXPOSED ... EVERY THING FEEL STALE ... WHAT KIND ON PREVIEW IT IS WORKING ON"): her long first
message pushed the work card below the fold, the preview was a grey skeleton for the whole plan call, and the typing box
was locked. Now the long message folds, the card is in view, the plan is read from the model's own words AS THEY ARRIVE
(name, pages, sections) into the preview, the steps name the real stages (checks, gaps, data), and she can write her next
message while Hoola works - it waits in the workspace's box, never sent by itself."""
import json
from pathlib import Path

import pytest

from tests.test_v0312_arena_screen import arena_server  # noqa: F401  (fixture: uvicorn + Chromium)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

CONSOLE = Path(__file__).parents[1] / "app" / "static" / "console"
PLAN = {"name": "Halden & Co.", "summary": "A specialty coffee roaster with a shop and subscriptions", "kind": "shop",
        "roles": [{"key": "buyer", "label": "Buyer", "can": "orders coffee"}],
        "pages": [{"slug": "home", "title": "Home", "purpose": "First look", "for": "public",
                   "sections": [{"type": "hero", "design": "a"}, {"type": "custom", "name": "Roast finder", "design": "b"}]},
                  {"slug": "shop", "title": "Shop", "purpose": "Every bean", "for": "public",
                   "sections": [{"type": "product_grid", "design": "c"}]},
                  {"slug": "account", "title": "My subscription", "purpose": "Pause or skip", "for": "member",
                   "sections": [{"type": "table", "design": "d"}]}],
        "flows": [{"name": "Subscribe", "who": "Buyer", "steps": ["picks", "pays"]}]}


@pytest.fixture
def qwen_env(env, monkeypatch, tmp_path):
    """Sites on disk + the plan on Qwen, with the REAL ask_json (site_env replaces it with a fake)."""
    from app.config import get_settings
    monkeypatch.setenv("SITE_DIR", str(tmp_path / "sites"))
    monkeypatch.setenv("SITE_WORKER", "false")
    monkeypatch.setenv("WEB_BRAIN", "qwen")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.999.156")
    assert "v0.986.0 PLAN PEEK" in (Path(__file__).parents[1] / "app" / "main.py").read_text()


def test_peek_reads_a_half_written_plan():
    from app.site import architect as AR
    full = json.dumps(PLAN)
    cut = full[:full.index('"My subscription"') + 8]                       # cut inside the third page's title
    pk = AR.peek_of(cut)
    assert pk["name"] == "Halden & Co." and pk["kind"] == "shop" and pk["summary"].startswith("A specialty")
    assert [p["title"] for p in pk["pages"]][:2] == ["Home", "Shop"] and pk["pages"][2]["title"].startswith("My sub")
    assert pk["pages"][0]["sections"] == ["hero", "Roast finder"] and pk["pages"][0]["for"] == "Public"
    assert pk["pages"][1]["sections"] == ["product grid"]
    whole = AR.peek_of(full)                                                 # the flows' names never become pages
    assert [p["title"] for p in whole["pages"]] == ["Home", "Shop", "My subscription"]
    assert whole["pages"][2]["for"] == "Signed-in users"
    assert AR.peek_of("") == {"name": "", "summary": "", "kind": "", "pages": []}
    assert AR.peek_of('{"name": "Hal')["name"] == "Hal"                       # a name still being written shows so far


def test_the_plan_streams_into_the_stage(qwen_env, monkeypatch):
    from app.devsahayak import brain as DB
    from app.site import activity as AC
    from app.site import architect as AR
    full = json.dumps(PLAN)
    seen_peeks = []

    def stream(url, body, headers, timeout, on_text):
        for n in (60, full.index('"Shop"') + 30, len(full)):
            on_text(full[:n])
            seen_peeks.append(AC.read(T, "stage-pk-12345678").get("peek"))
        return {"choices": [{"finish_reason": "stop", "message": {"content": full}}], "usage": {}}

    def no_post(*a, **k):
        raise AssertionError("the plan was asked without streaming while the start screen watches")
    monkeypatch.setattr(DB, "QWEN_STREAM", stream)
    monkeypatch.setattr(DB, "QWEN_POST", no_post)
    monkeypatch.setattr(AR.time, "time", iter(range(1000, 100000, 5)).__next__)   # every piece passes the 1 s throttle
    st, _ = AR._stager(T, "pk-12345678")
    st("Planning the pages and what each one holds.")
    tok = AR.STAGE.set((st, AR._Peeker(T, "pk-12345678")))
    try:
        out = AR._ask("You are Hoola's solution architect.", "{}", 16000, "site_art")
    finally:
        AR.STAGE.reset(tok)
    assert out["name"] == "Halden & Co."                                       # the answer itself is unchanged
    pk = AC.read(T, "stage-pk-12345678")["peek"]
    assert [p["title"] for p in pk["pages"]] == ["Home", "Shop", "My subscription"] and pk["pass"] == "first"
    assert [p["title"] for p in (seen_peeks[1] or {}).get("pages", [])][:2] == ["Home", "Shop"]   # it grew while written


def test_no_watcher_no_stream(qwen_env, monkeypatch):
    from app.devsahayak import brain as DB
    from app.site import architect as AR
    monkeypatch.setattr(DB, "QWEN_STREAM", lambda *a, **k: (_ for _ in ()).throw(AssertionError("streamed")))
    monkeypatch.setattr(DB, "QWEN_POST", lambda *a, **k: {"choices": [{"message": {"content": json.dumps(PLAN)}}], "usage": {}})
    assert AR._ask("You are Hoola's solution architect.", "{}", 16000, "site_art")["kind"] == "shop"


def test_deepen_never_shrinks_what_is_shown(site_env, monkeypatch):
    from app.site import activity as AC
    from app.site import architect as AR
    monkeypatch.setattr(AR.time, "time", iter(range(1000, 100000, 5)).__next__)
    st, _ = AR._stager(T, "dp-12345678")
    st("Planning the pages and what each one holds.")
    pe = AR._Peeker(T, "dp-12345678")
    tok = AR.STAGE.set((st, pe))
    try:
        pe(AR._peek_spec(AR.clean(PLAN, "a coffee roaster shop", "standard")))
        sink = AR._watch("deepen")
        sink('{"name": "Halden & Co.", "pages": [{"slug": "home", "title": "Home", "sections": []}')
        assert len(AC.read(T, "stage-dp-12345678")["peek"]["pages"]) >= 3     # the deeper pass has not caught up yet
        AR._say("Checking the plan: 9 of 12 checks pass.")
    finally:
        AR.STAGE.reset(tok)
    r = AC.read(T, "stage-dp-12345678")
    assert r["peek"]["done"] is True and r["steps"][-1]["label"] == "Checking the plan: 9 of 12 checks pass."
    AR._say("no stage, nothing written")                                    # outside build_now it is a quiet no-op


def test_build_now_names_the_real_stages(site_env, monkeypatch):
    from app.site import activity as AC
    from app.site import architect as AR
    from app.site import service as S

    def draft(*a, **k):
        assert AR.STAGE.get() is not None                                     # draft runs with the start screen watching
        AR._show(AR.clean(PLAN, "coffee", "standard"))
        AR._say("Writing the data and the rules: who can see and change what.")
        return {"id": "c1", "hash": "h", "number": 1}
    monkeypatch.setattr(AR, "draft", draft)
    monkeypatch.setattr(AR, "approve", lambda *a, **k: {"site": "s1", "say": "ok"})
    monkeypatch.setattr(S, "_load", lambda sid: object())
    monkeypatch.setattr(S, "view", lambda row: {"id": "s1"})
    AR.build_now(T, "a coffee roaster website with a shop", "", "bn-12345678")
    r = AC.read(T, "stage-bn-12345678")
    labels = [s["label"] for s in r["steps"]]
    assert "Writing the data and the rules: who can see and change what." in labels
    assert labels[-1] == "The workspace is ready." and r["peek"]["name"] == "Halden & Co."
    assert AR.STAGE.get() is None                                             # never left set after the call


def test_the_start_screen_shows_its_work_statically():
    js = (CONSOLE / "webstudio.js").read_text()
    css = (CONSOLE / "webstudio.css").read_text()
    pend = js[js.index("function drawPending("):js.index("/* ================= v0.988 PROMPT FIRST")]   # v0.988: the next block was renamed
    assert "textarea rows=\"2\" disabled" not in pend and 'id="wsPendTa"' in pend    # she can write while it works
    assert "${pendMe(text)}" in pend and "pendScroll();" in pend and "peekView(r.peek" in pend
    assert "data-t0=\"${Number(x.at)}\"" in pend                               # the running step's clock keeps ticking
    assert "store.set(PEND_KEY, ''" in js and "ta.value = pd" in js             # kept for the workspace, never sent
    assert "act === 'pend-more'" in js and ".me.clip .mtx{max-height:9.2em" in css and ".doc.peek .pkp li.now" in css


def test_the_start_screen_in_a_browser(arena_server, site_env):
    base, browser, key = arena_server
    from app.site import activity as AC
    from app.site import architect as AR
    errors, held = [], []
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    ctx.add_init_script(f"try {{ localStorage.setItem('hoola.console.token', '{key}') }} catch (e) {{}}")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    tk = {}

    def hold(route):
        t = (route.request.post_data_json or {}).get("ticket") or ""
        tk["t"] = t
        AC.step(T, "stage-" + t, "Reading your idea.")
        AC.step(T, "stage-" + t, "Planning the pages and what each one holds.")
        held.append(route)                                                     # never answered: still planning
    page.route("**/api/sites", lambda r: hold(r) if r.request.method == "POST" else r.continue_())
    page.goto(f"{base}/console/web#/")
    page.locator("#wsAsk").wait_for(timeout=20000)
    ask = "Build the website for Halden & Co., a specialty coffee roaster in Portland.\n" + "\n".join(
        f"- Requirement {i}: a detailed line about the shop, subscriptions, wholesale, events and the journal." for i in range(14))
    page.fill("#wsAsk", ask)
    page.click("button.go")
    page.locator("[data-pending] b", has_text="Setting the stage").wait_for(timeout=20000)
    assert page.locator("#wsPendMe.clip").count() == 1                         # the long message is folded
    box = page.locator("#wsPendMsgs").bounding_box()
    card = page.locator("#wsPendMsgs .wcard").bounding_box()
    assert card["y"] < box["y"] + box["height"] - 40, (card, box)             # the work card is in view, not below the fold
    assert page.locator(".doc.skel").count() == 1                              # nothing planned yet: the honest empty state
    page.fill("#wsPendTa", "Make the shop page show the roast date first")
    assert page.evaluate("localStorage.getItem('hoola.ws.pend.draft')") == "Make the shop page show the roast date first"
    AC.peek(T, "stage-" + tk["t"], {**AR.peek_of(json.dumps(PLAN)[:json.dumps(PLAN).index('"account"')]), "pass": "first"})
    page.locator(".doc.peek .pkp li", has_text="Shop").wait_for(timeout=10000)   # the plan grows in the preview
    assert "Halden & Co." in page.inner_text(".doc.peek .pkn")
    assert page.locator(".doc.peek .pkc span", has_text="Roast finder").count() == 1
    assert page.locator(".doc.peek .pkp li.now").count() == 1                  # the page being written is marked
    import os
    if os.environ.get("CONSOLE_SHOTS"):
        page.screenshot(path=os.path.join(os.environ["CONSOLE_SHOTS"], "v0986-start.png"))
    page.click("[data-act='pend-more']")
    assert page.get_attribute("[data-act='pend-more']", "aria-expanded") == "true"
    ctx.close()
    assert not errors, errors
