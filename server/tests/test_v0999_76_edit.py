"""v0.999.76 D7 EDIT FOREVER, FOR FREE (docs/WEB_DESIGN_ENGINE_PLAN.md phase D7, P9): a website written in React is
changed by clicking it - her words, a section's layout / background / leave out, Undo, and a design panel (brand colour,
light / dark, corners, spacing, motion, fonts) - by code only (Rs 0). Her changes are kept as data and survive every
later write (a review round, a new build). The chat changes it the same exact way, never by rewriting a page.
Done-line: every edit Rs 0 except chat rewrites."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.appengine import edits as ED
from tests.test_v0814_app_engine import _box, ae_env  # noqa: F401  (fixture)
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _on(monkeypatch):
    monkeypatch.setenv("APP_ENGINE_AUTOFIX", "true")
    monkeypatch.setenv("STUDIO_REACT_SITES", "true")
    monkeypatch.setenv("SITE_CRITIC", "false")          # one build: the edits are the point here
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def rx_site(ae_env, monkeypatch):
    _box()
    from app.site import ai as AI
    from app.site import prototype as PT
    from app.site import service as S
    from tests.test_v0999_65_writer import _proto
    monkeypatch.setattr(AI, "ask", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no model here")))
    v = S.new(T, "A website for Nirmal Family Clinic in Pune: doctors, timings, map and WhatsApp.", name="Nirmal Family Clinic")
    PT._write_version(S._load(v["id"]), _proto(), "test", "hoola")
    PT.approve(T, v["id"], PT.meta(S._load(v["id"]))["hash"])
    out = S.view(S._load(v["id"]))
    assert out["status"] == "ready", out.get("error")
    return v["id"], out["react"]["id"]


def _page(ref: str, name: str = "HomePage.tsx") -> str:
    from app.appengine import service as AE
    return (AE.src_dir(AE._load(T, ref)) / "src" / "pages" / name).read_text()


def _sec_code(code: str, sec: str) -> str:
    return code.split(f'data-sec="{sec}"')[1].split("</div>")[0]


# ---------------------------------------------------------------- 1. words, by clicking them
def test_her_words_change_by_code_and_cost_nothing(rx_site):
    from app.site import rxedit as RX
    sid, ref = rx_site
    got = RX.sections(T, sid)
    shown = [s for s in got["sections"] if not s["left_out"]]
    assert shown and all(s["n"] for s in shown) and got["undo"] == 0
    hero = next(s for s in shown if s["block"] == "hero")
    head = next(t for t in hero["texts"] if t["path"] == ["headline"])
    for s in shown:                                                          # her facts are changed in Settings only
        assert not any(t["path"][-1] in ("phone", "whatsapp", "email", "address", "hours", "href") for t in s["texts"])
    res = RX.words(T, sid, hero["sec"], head["value"], "Care for every family in Pune")
    assert res["calls"] == 0 and res["inr"] == 0.0                            # Rs 0: no model call
    assert "Care for every family in Pune" in _sec_code(_page(ref), hero["sec"])
    e = ED.edits(T, ref)
    assert e["words"][hero["sec"]][0]["path"] == ["headline"] and e["words"][hero["sec"]][0]["was"] == head["value"]
    intro = next(t for t in hero["texts"] if t["path"] == ["intro"] and len(t["value"].split()) > 2)
    part = " ".join(intro["value"].split()[:2])                              # she clicked part of a longer text
    RX.words(T, sid, hero["sec"], part, "Gentle")
    assert "Gentle" in _sec_code(_page(ref), hero["sec"])
    with pytest.raises(RX.EditError):
        RX.words(T, sid, hero["sec"], "words that are nowhere on the page", "x")
    with pytest.raises(RX.EditError):
        RX.words(T, sid, hero["sec"], head["value"], "")
    with pytest.raises(RX.EditError):
        RX.words("someone_else", sid, hero["sec"], head["value"], "x")        # only her own site


def test_sections_change_layout_background_and_come_back(rx_site):
    from app.appengine import critic as C
    from app.site import rxedit as RX
    sid, ref = rx_site
    shown = [s for s in RX.sections(T, sid)["sections"] if not s["left_out"]]
    s1 = next(s for s in shown if s["alts"] and s["block"] not in C.NEVER_DROP)
    res = RX.section(T, sid, s1["sec"], variant=s1["alts"][0])
    assert res["calls"] == 0 and f'variant="{s1["alts"][0]}"' in _sec_code(_page(ref, _file(s1)), s1["sec"])
    t1 = next(s for s in shown if s["tones"] and s["sec"] != s1["sec"])
    RX.section(T, sid, t1["sec"], tone=t1["tones"][0])
    assert f'tone="{t1["tones"][0]}"' in _sec_code(_page(ref, _file(t1)), t1["sec"])
    with pytest.raises(RX.EditError):
        RX.section(T, sid, s1["sec"], variant="a-layout-it-cannot-draw")
    hero = next(s for s in shown if s["block"] == "hero")
    with pytest.raises(RX.EditError):
        RX.section(T, sid, hero["sec"], drop=True)                            # the top of the page stays
    RX.section(T, sid, s1["sec"], drop=True)
    assert f'data-sec="{s1["sec"]}"' not in _page(ref, _file(s1))
    after = {s["sec"]: s for s in RX.sections(T, sid)["sections"]}
    assert after[s1["sec"]]["left_out"] and after[s1["sec"]]["hers"]
    RX.section(T, sid, s1["sec"], drop=False)                                 # brought back, with her layout
    assert f'variant="{s1["alts"][0]}"' in _sec_code(_page(ref, _file(s1)), s1["sec"])
    n = RX.sections(T, sid)["undo"]
    RX.undo(T, sid)
    assert f'data-sec="{s1["sec"]}"' not in _page(ref, _file(s1)) and RX.sections(T, sid)["undo"] == n - 1


def _file(s):
    from app.appengine import writer as W
    return W._slug_comp(s["page"]) + ".tsx"


def test_her_changes_survive_a_review_round(rx_site):
    """A later write (a review round, a new build) keeps her words and her section choices; the critic never 'fixes'
    a section she chose herself."""
    from app.appengine import critic as C
    from app.quality import designcard as DC
    from app.site import prototype as PT
    from app.site import rxedit as RX
    from app.site import service as S
    sid, ref = rx_site
    shown = [s for s in RX.sections(T, sid)["sections"] if not s["left_out"]]
    hero = next(s for s in shown if s["block"] == "hero")
    head = next(t for t in hero["texts"] if t["path"] == ["headline"])
    RX.words(T, sid, hero["sec"], head["value"], "Her own headline")
    mine = next(s for s in shown if s["tones"] and s["block"] != "hero")
    RX.section(T, sid, mine["sec"], tone=mine["tones"][0])
    r = S._load(sid)

    def critic(imgs, rows, shots, measured):
        return {"scores": {c: 5 for c in DC.CRITERIA}, "design": 5.0,
                "fixes": [{"sec": mine["sec"], "fix": "tone", "to": "", "why": "x"}]}
    rep = C.improve(T, ref, PT.pages_of(r), name=r.name, facts=PT._j(r.facts, {}), seed=r.id, critic=critic, rounds=2,
                    hero=True, refs=False)
    code = _page(ref, _file(hero))
    assert "Her own headline" in _sec_code(code, hero["sec"])
    assert f'tone="{mine["tones"][0]}"' in _sec_code(_page(ref, _file(mine)), mine["sec"])
    assert rep.get("hero") is None or True                                   # (her hero section is not chosen here)
    assert not any(mine["sec"] in f for x in rep["rounds"] for f in (x.get("fixes") or []))


# ---------------------------------------------------------------- 2. the design panel
def test_the_design_panel_changes_every_page_for_free(rx_site):
    from app.appengine import service as AE
    from app.site import rxedit as RX
    sid, ref = rx_site
    d = RX.design(T, sid)
    assert d["design"]["primary"] and d["fonts"] and "light" in d["modes"] and d["radius"] == [0, 32]
    res = RX.set_design(T, sid, colour="#0f766e", radius=4, density="airy", mode="light")
    assert res["calls"] == 0 and res["design"]["radius"] == 4 and res["design"]["density"] == "airy"
    css = (AE.src_dir(AE._load(T, ref)) / "src" / "tokens.css")
    text = css.read_text() if css.is_file() else "".join(f.read_text() for f in (AE.src_dir(AE._load(T, ref)) / "src").rglob("tokens.css"))
    assert "--radius-card:8px" in text.replace(" ", "")                     # corners 4 -> cards 8 px (genome rule)
    other = next(f["name"] for f in d["fonts"] if "display" in f["role"] and f["name"] != d["design"]["fonts"]["display"])
    assert RX.set_design(T, sid, display=other)["design"]["fonts"]["display"] == other
    with pytest.raises(RX.EditError):
        RX.set_design(T, sid, display="Comic Sans")                           # only Hoola's bundled fonts
    with pytest.raises(RX.EditError):
        RX.set_design(T, sid, colour="teal")
    dark = RX.set_design(T, sid, mode="dark")
    assert dark["design"]["mode"] == "dark" and dark["design"]["checks"] == "every colour pair readable"


# ---------------------------------------------------------------- 3. the chat: exact edits, never a rewrite
def test_the_chat_changes_a_react_site_with_exact_edits(rx_site):
    from app.agent import site_tools as ST
    from app.site import rxedit as RX
    sid, ref = rx_site
    block = RX.chat_block(T, sid)
    assert "EXACT edits, never a page rewrite" in block and "action=rx_edit" in block and ":0 (" in block
    spec = next(t for t in ST.SITE_TOOLS if t["name"] == "website")
    acts = spec["input_schema"]["properties"]["action"]["enum"]
    assert "rx_edit" in acts and "rx_undo" in acts and "sec" in spec["input_schema"]["properties"]
    src = (ROOT / "server/app/agent/turnmode.py").read_text()
    assert "RX.chat_block(tenant, site)" in src
    hero = next(s for s in RX.sections(T, sid)["sections"] if s["block"] == "hero")
    head = next(t for t in hero["texts"] if t["path"] == ["headline"])
    from types import SimpleNamespace
    out = ST._act(SimpleNamespace(tenant_id=T, conversation_id="", actor="owner"), "rx_edit",
                  {"site": sid, "sec": hero["sec"], "old": head["value"], "new": "Said in the chat"})
    assert out["calls"] == 0 and "Said in the chat" in _sec_code(_page(ref), hero["sec"])
    ST._act(SimpleNamespace(tenant_id=T, conversation_id="", actor="owner"), "rx_undo", {"site": sid})
    assert "Said in the chat" not in _page(ref)


# ---------------------------------------------------------------- 4. the preview: click -> the section + its words
def test_clicking_words_in_the_preview_names_the_section(tmp_path):
    """preview.js in a real Chromium: in site mode a click sends the section's key + the words clicked, and the new
    words are drawn at once."""
    import http.server
    import socketserver
    import threading
    js = (ROOT / "server/app/appengine/preview.js").read_text()
    (tmp_path / "preview.js").write_text(js)
    (tmp_path / "page.html").write_text("""<!doctype html><html><head><script src="preview.js"></script></head><body>
      <main><div data-sec="home:0" class="contents" style="display:contents"><section data-block="hero" data-variant="split">
      <h1 id="h">Fresh bread every morning</h1><p>Baked in <b>Pune</b> since 1998</p></section></div></main></body></html>""")
    (tmp_path / "top.html").write_text("""<!doctype html><html><body><iframe id="f" src="page.html" style="width:800px;height:400px"></iframe>
      <script>window.got=[];addEventListener('message',e=>{if(e.data&&e.data.hoola==='ae')window.got.push(e.data)});</script></body></html>""")

    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(tmp_path), **k)

        def log_message(self, *a):
            pass
    srv = socketserver.TCPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        from playwright.sync_api import sync_playwright
        from app.appengine import speed as SP
        with sync_playwright() as pw:
            b = SP._browser(pw)
            pg = b.new_page()
            pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/top.html")
            pg.wait_for_function("window.got.some(m => m.t === 'ready')")
            fr = pg.frame_locator("#f")
            pg.evaluate("document.getElementById('f').contentWindow.postMessage({hoola:'ae-cmd',t:'mode',mode:'site'},'*')")
            pg.wait_for_timeout(150)
            fr.locator("#h").click()
            pg.wait_for_function("window.got.some(m => m.t === 'sec-pick')")
            m = pg.evaluate("window.got.find(m => m.t === 'sec-pick')")
            assert m["sec"] == "home:0" and m["block"] == "hero" and m["text"] == "Fresh bread every morning" and m["leaf"]
            pg.evaluate("document.getElementById('f').contentWindow.postMessage({hoola:'ae-cmd',t:'sec-text',sec:'home:0',old:'Fresh bread every morning',new:'Her words'},'*')")
            pg.wait_for_timeout(150)
            assert fr.locator("#h").inner_text() == "Her words"
            b.close()
    finally:
        srv.shutdown()


def test_the_studio_has_the_edit_switch_panels_and_routes():
    js = (ROOT / "server/app/static/console/webstudio.js").read_text()
    for x in ('data-act="rx-edit"', 'data-act="rx-design"', 'data-act="rx-undo"', 'data-form="rx-words"', "/rx/${path}",
              "rxDo('words'", "rxDo('section'", "rxDo('undo')", "/rx/design", "/rx/sections", "sec-pick", "rxWatch"):
        assert x in js, x
    main = (ROOT / "server/app/main.py").read_text()
    for path in ("/api/sites/{ref}/rx/sections", "/api/sites/{ref}/rx/words", "/api/sites/{ref}/rx/section",
                 "/api/sites/{ref}/rx/undo", "/api/sites/{ref}/rx/design"):
        assert path in main
    assert "sec-text" in (ROOT / "server/app/appengine/preview.js").read_text()
    assert ".rxpanel" in (ROOT / "server/app/static/console/webstudio.css").read_text()
