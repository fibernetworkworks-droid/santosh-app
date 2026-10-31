"""v0.295 WEB DESIGN PHASE 2, editing like Lovable: every word / link / picture of a built site has an edit number, the
edit preview carries the in-page editor, her own changes (words, link, picture, remove, colours) need no AI call, each
one can be undone, each becomes a checked version, and the live site / versions / exports never carry the edit numbers."""
import json

import pytest
from fastapi.testclient import TestClient

from tests.test_life import conv_ctx
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

T = "default"


def _ready(site_env):
    from app.site import service as S
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210", "address": "Main Road, Akot"})
    S.approve_plan(T, v["id"], pages=["contact"])
    S.choose_look(T, v["id"], 0)
    g = S.get(T, v["id"])
    assert g["status"] == "ready", g.get("error")
    return g


def _el(html, e):
    from app.site import edit as E
    return E.describe(html, e)


# ---------------------------------------------------------------- 1. numbering + applying (pure)
def test_tag_and_apply_rules():
    from app.site import build as B
    from app.site import edit as E
    html = ('<section id="s"><h1>Sharma Sweets</h1><p class="lead">Akot ki purani dukaan.</p>'
            '<a class="btn" href="tel:+919876543210"><i data-icon="phone"></i> Call karein</a>'
            '<img data-hoola-img="shop" alt="shop"><div><ul><li>Kaju katli</li></ul></div></section>')
    h, n = E.tag(html)
    assert n == 5 and E.tag(h)[1] == 0                         # numbered once, stable on the next pass
    nums = {_el(h, str(i))["tag"]: str(i) for i in range(1, 6)}
    assert set(nums) == {"h1", "p", "a", "img", "li"}
    h2, what = E.apply(h, nums["a"], "text", "WhatsApp karein", {"shop"}, B._ok_href)
    a = _el(h2, nums["a"])
    assert a["text"] == "WhatsApp karein" and 'data-icon="phone"' in h2          # the icon inside the button stays
    h3, _ = E.apply(h2, nums["a"], "link", "https://wa.me/919876543210", {"shop"}, B._ok_href)
    assert 'href="https://wa.me/919876543210"' in h3 and 'target="_blank"' in h3
    with pytest.raises(E.EditError):
        E.apply(h3, nums["a"], "link", "javascript:alert(1)", {"shop"}, B._ok_href)
    with pytest.raises(E.EditError):
        E.apply(h3, nums["img"], "image", "not-hers", {"shop"}, B._ok_href)
    with pytest.raises(E.EditError):
        E.apply(h3, nums["h1"], "remove", "", {"shop"}, B._ok_href)                # the page keeps its h1
    with pytest.raises(E.EditError):
        E.apply(h3, nums["p"], "text", "   ", {"shop"}, B._ok_href)
    h4, _ = E.apply(h3, nums["p"], "text", "<script>alert(1)</script> Naya", {"shop"}, B._ok_href)
    assert "<script>" not in h4 and "&lt;script&gt;" in h4                     # her words are text, never markup
    h5, _ = E.apply(h4, nums["li"], "remove", "", {"shop"}, B._ok_href)
    assert "Kaju katli" not in h5
    assert 'data-e=' not in E.strip(h5)


# ---------------------------------------------------------------- 2. the whole flow, no AI
def test_edit_flow_no_ai_undo_versions_and_clean_live(site_env, monkeypatch):
    from app.main import app
    from app.site import build as B
    from app.site import service as S
    g = _ready(site_env)
    sid, ver0 = g["id"], g["version"]
    c = TestClient(app)
    m = c.post(f"/api/sites/{sid}/edit-mode").json()
    assert m["url"].endswith("/__edit/")
    token = m["url"].rstrip("/").split("/")[-2]
    page = c.get(f"/api/site-preview/{token}/__edit/")
    assert page.status_code == 200 and f"/api/site-preview/{token}/__edit.js" in page.text and 'data-e="' in page.text
    assert 'data-k="home__hero"' in page.text
    js = c.get(f"/api/site-preview/{token}/__edit.js")
    assert js.status_code == 200 and "HoolaEdit" in js.text and "postMessage" in js.text
    normal = c.get(f"/api/site-preview/{token}/").text
    assert "data-e=" not in normal and "__edit.js" not in normal               # the normal preview stays clean
    r = S._load(sid)
    hero = S._sections(r)["home__hero"]["html"]
    e = next(x for x in range(1, 40) if _safe(hero, str(x)) and _el(hero, str(x))["tag"] == "h1")
    calls_before = len(site_env.calls)
    out = c.post(f"/api/sites/{sid}/edit", json={"k": "home__hero", "e": str(e), "op": "text", "value": "Akot ki sabse meethi dukaan"}).json()
    assert "Badal diya" in out["say"] and len(site_env.calls) == calls_before        # no AI call at all
    g2 = S.get(T, sid)
    assert g2["version"] == ver0 + 1 and g2["status"] == "ready"                     # a checked version of her edit
    live = (B.out_dir(T, sid, g2["version"]) / "index.html").read_text()
    assert "Akot ki sabse meethi dukaan" in live and "data-e=" not in live           # versions never carry edit numbers
    assert S.edits(T, sid)["edits"][0]["what"].endswith('"Akot ki sabse meethi dukaan"')
    # colours by hand
    t = c.post(f"/api/sites/{sid}/theme", json={"tokens": {"primary": "#0B6E4F"}}).json()
    assert t["tokens"]["primary"].lower() == "#0b6e4f"
    assert c.post(f"/api/sites/{sid}/theme", json={"tokens": {"primary": "green"}}).status_code == 400
    # undo twice: the colour, then the words
    c.post(f"/api/sites/{sid}/undo")
    assert json.loads(S._load(sid).look)["tokens"]["primary"].lower() != "#0b6e4f"
    c.post(f"/api/sites/{sid}/undo")
    assert "Akot ki sabse meethi dukaan" not in S._sections(S._load(sid))["home__hero"]["html"]
    assert c.post(f"/api/sites/{sid}/undo").status_code == 400                        # nothing left to undo
    assert S.get(T, sid)["version"] == ver0 + 4


def _safe(html, e):
    try:
        _el(html, e)
        return True
    except Exception:
        return False


def test_edits_wait_for_a_running_build_and_old_sections_get_numbers(site_env, monkeypatch):
    from app.site import service as S
    g = _ready(site_env)
    sid = g["id"]
    r = S._load(sid)
    k = "home__hero"
    sec = S._sections(r)[k]
    from app.site import edit as E
    S._put_sec(r, k, {**sec, "html": E.strip(sec["html"])})                  # a section from before v0.295
    assert "data-e=" not in S._sections(r)[k]["html"]
    S.edit_mode(T, sid)
    assert "data-e=" in S._sections(S._load(sid))[k]["html"]
    monkeypatch.setattr(S, "busy", lambda site_id: True)
    S._JOBS[sid] = "build"
    with pytest.raises(S.SiteError):
        S.edit_element(T, sid, k, "1", "text", "x")
    S._JOBS[sid] = "save"                                                    # her last edits being checked: go on
    monkeypatch.setattr(S, "_start", lambda *a, **kw: False)
    out = S.edit_element(T, sid, k, "1", "text", "Naya shabd")
    assert sid in S._SAVE_PENDING and "Badal diya" in out["say"]
    S._SAVE_PENDING.discard(sid)
    S._JOBS.pop(sid, None)


def test_tool_undo_and_version():
    from app.agent import site_tools as ST
    assert "undo" in ST.SITE_TOOLS[0]["input_schema"]["properties"]["action"]["enum"]
    from app.main import APP_VERSION
    from pathlib import Path
    assert APP_VERSION == "0.314.0"
    assert "0.314.0+354" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
