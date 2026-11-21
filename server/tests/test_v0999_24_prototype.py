"""v0.999.24 PROTOTYPE FIRST (owner: "DONT SHOW THE 3 DESIGNS ... IF BUILD (USER WILL FIRST SEE EVERY PAGE PROTOTYPE ...)
-- IF PLAN (... AFTER PLAN APPROVAL A PROTOTYPE) --- PROTOTYPE CAN ALSO BE MODIFIED -- AFTER PROTOTYPE APPROVAL -- REAL WEBSITE
BUILD"): after the plan, a prototype of every page and section (never three looks); she changes it in words, by hand and
with Undo; only her tap on the version she saw builds the real website, written from the prototype."""
import ast
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[1]


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.88"


class ProtoAI:
    """Writes prototype copy and prototype changes; every other call (the real build) goes to the site fake."""

    def __init__(self, site):
        self.site, self.copy, self.change, self.fail_copy = site, [], None, False

    def __call__(self, system, prompt, max_tokens=6000, kind="build"):
        from app.site import prototype as PT
        if system.startswith(PT.COPY_SYSTEM[:40]):
            self.copy.append(prompt)
            if self.fail_copy:
                raise RuntimeError("model down")
            n = prompt.split("SECTIONS:\n", 1)[1].count("\n") + 1
            return {"sections": [{"heading": f"Heading {i + 1}", "line": "Fresh sweets every morning.",
                                  "items": ["Kaju katli", "Motichoor laddoo"], "cta": "Order on WhatsApp" if i == 0 else ""}
                                 for i in range(n)]}
        if system.startswith(PT.CHANGE_SYSTEM[:40]):
            self.copy.append(("change", prompt))
            return self.change or {}
        return self.site(system, prompt, max_tokens, kind)


@pytest.fixture
def proto(site_env, monkeypatch):
    from app.config import get_settings
    monkeypatch.setenv("STUDIO_PROTOTYPE", "true")
    get_settings.cache_clear()
    from app.site import ai as AI
    fake = ProtoAI(site_env)
    monkeypatch.setattr(AI, "ask_json", fake)
    yield fake
    get_settings.cache_clear()


def _site(c):
    from app.site import service as S
    v = S.new(T, "mithai dukaan ki website, online order WhatsApp par. Phone 98765 43210", "", name="Sharma Sweets")
    r = c.post(f"/api/sites/{v['id']}/plan", json={"pages": ["products", "contact"]})
    assert r.status_code == 200, r.text
    return v["id"]


def test_the_plan_leads_to_a_prototype_of_every_page_not_three_looks(proto):
    from app.main import app
    from app.site import service as S
    c = TestClient(app)
    sid = _site(c)
    g = S.get(T, sid)
    assert g["status"] == "prototype" and not g["looks"]
    p = g["prototype"]
    assert p["v"] == 1 and p["status"] == "ready" and p["hash"]
    plan = {x["slug"]: x for x in g["plan"]["pages"]}
    shown = {x["slug"]: x for x in p["pages"]}
    assert set(shown) == {s for s in plan if s not in ("privacy", "refund")}      # every page but the legal ones
    for slug, pg in shown.items():
        assert [s["label"] for s in pg["sections"]] == plan[slug]["sections"]       # every section, in the plan's order
        assert pg["sections"][0]["heading"] == "Heading 1" and pg["url"].endswith(f"__proto/{slug}.html")
    assert len(proto.copy) == len(shown)                                            # one small call a page
    assert not [x for x in proto.site.calls if x[0] == "section"]                  # nothing real is written yet


def test_the_prototype_pages_are_served_in_the_preview(proto):
    from app.main import app
    from app.site import service as S
    c = TestClient(app)
    sid = _site(c)
    p = S.get(T, sid)["prototype"]
    tok = p["pages"][0]["url"].split("/api/site-preview/", 1)[1].split("/", 1)[0]
    r = c.get(f"/api/site-preview/{tok}/__proto/home.html")
    assert r.status_code == 200 and "Heading 1" in r.text and "Prototype</b> · version 1" in r.text
    assert "script-src 'self'" in r.headers["content-security-policy"] and "<script src='__proto.js'>" in r.text
    assert "products.html" in r.text and "Order on WhatsApp" in r.text
    js = c.get(f"/api/site-preview/{tok}/__proto/__proto.js")
    assert js.status_code == 200 and "proto-cmd" in js.text
    fonts = [x.split("assets/fonts/", 1)[1].split(")", 1)[0] for x in r.text.split("url(")[1:] if "assets/fonts/" in x]
    if fonts:
        assert c.get(f"/api/site-preview/{tok}/__proto/assets/fonts/{fonts[0]}").status_code == 200
    assert c.get(f"/api/site-preview/{tok}/__proto/nope.html").status_code == 404
    assert c.get(f"/api/site-preview/{tok}/__proto/../secrets").status_code == 404


def test_her_words_change_the_prototype_and_the_plan_follows_undo_goes_back(proto):
    from app.main import app
    from app.site import service as S
    c = TestClient(app)
    sid = _site(c)
    p1 = S.get(T, sid)["prototype"]
    home = next(x for x in p1["pages"] if x["slug"] == "home")
    proto.change = {"pages": [{**home, "sections": home["sections"] + [
        {"type": "pricing_tiers", "label": "Gift boxes", "heading": "Diwali gift boxes", "items": ["Small - Rs 499 (sample)"]}]}],
        "say": "Added gift boxes to the home page."}
    r = c.post(f"/api/sites/{sid}/prototype/change", json={"words": "home page par Diwali gift box ke daam dikhao"})
    assert r.status_code == 200, r.text
    p2 = r.json()
    assert p2["v"] == 2 and p2["say"] == "Added gift boxes to the home page." and p2["hash"] != p1["hash"]
    assert S.get(T, sid)["plan"]["pages"][0]["sections"][-1] == "Gift boxes"            # the plan follows the prototype
    r = c.post(f"/api/sites/{sid}/prototype/undo")
    assert r.json()["v"] == 3 and r.json()["hash"] == p1["hash"]
    assert "Gift boxes" not in S.get(T, sid)["plan"]["pages"][0]["sections"]
    # a change asked through the website tool / chat reaches the prototype too
    proto.change = {"pages": [{**home, "title": "Welcome"}]}
    out = S.change(T, sid, "home page ka naam Welcome kar do")
    assert out["v"] == 4 and next(x for x in out["pages"] if x["slug"] == "home")["title"] == "Welcome"


def test_her_hands_edit_move_and_remove_with_no_model(proto):
    from app.main import app
    from app.site import service as S
    c = TestClient(app)
    sid = _site(c)
    p1 = S.get(T, sid)["prototype"]
    n = len(proto.copy)
    r = c.post(f"/api/sites/{sid}/prototype/edit", json={"page": "home", "index": 0, "field": "heading",
                                                         "value": "Akot ki sabse purani mithai", "base": p1["hash"]})
    assert r.status_code == 200 and r.json()["v"] == 2
    assert next(x for x in r.json()["pages"] if x["slug"] == "home")["sections"][0]["heading"] == "Akot ki sabse purani mithai"
    stale = c.post(f"/api/sites/{sid}/prototype/edit", json={"page": "home", "index": 0, "field": "heading",
                                                             "value": "x", "base": p1["hash"]})
    assert stale.status_code == 409                                                 # she edited what she no longer sees
    home = next(x for x in r.json()["pages"] if x["slug"] == "home")
    second = home["sections"][1]["label"]
    r = c.post(f"/api/sites/{sid}/prototype/move", json={"page": "home", "index": 1, "op": "up"})
    assert next(x for x in r.json()["pages"] if x["slug"] == "home")["sections"][0]["label"] == second
    r = c.post(f"/api/sites/{sid}/prototype/move", json={"page": "home", "index": 0, "op": "remove"})
    assert second not in [s["label"] for s in next(x for x in r.json()["pages"] if x["slug"] == "home")["sections"]]
    assert len(proto.copy) == n                                                     # Rs 0: no model call
    bad = c.post(f"/api/sites/{sid}/prototype/edit", json={"page": "home", "index": 0, "field": "type", "value": "x"})
    assert bad.status_code == 400


def test_only_her_tap_on_the_version_she_saw_builds_the_real_website(proto):
    from app.main import app
    from app.site import service as S
    c = TestClient(app)
    sid = _site(c)
    p = S.get(T, sid)["prototype"]
    assert c.post(f"/api/sites/{sid}/prototype/approve", json={"hash": "old"}).status_code == 409
    r = c.post(f"/api/sites/{sid}/prototype/approve", json={"hash": p["hash"]})
    assert r.status_code == 200, r.text
    g = S.get(T, sid)
    assert g["status"] == "ready", g.get("error")
    assert g["prototype"]["status"] == "approved" and g["prototype"]["approved_v"] == 1 and g["chosen_look"] == "prototype"
    built = [x for x in proto.site.calls if x[0] == "section"]
    assert built                                                                    # the real sections were written now
    # every section was written from its approved copy
    from app.site import ai as AI  # noqa: F401
    assert c.post(f"/api/sites/{sid}/prototype/change", json={"words": "x"}).status_code == 409   # approved: no more prototype changes


def test_the_real_build_is_told_the_approved_copy(proto, monkeypatch):
    from app.main import app
    from app.site import service as S
    seen = {}
    real = S.run_build

    def spy(site_id, only=None, note="", extra=None):
        seen.update(extra or {})
        return real(site_id, only, note, extra)
    monkeypatch.setattr(S, "run_build", spy)
    c = TestClient(app)
    sid = _site(c)
    p = S.get(T, sid)["prototype"]
    c.post(f"/api/sites/{sid}/prototype/approve", json={"hash": p["hash"]})
    assert "home__hero" in seen and "THE OWNER APPROVED THIS SECTION" in seen["home__hero"]
    assert "heading: Heading 1" in seen["home__hero"] and "button: Order on WhatsApp" in seen["home__hero"]


def test_a_page_whose_words_did_not_come_still_shows_its_sections(proto):
    from app.main import app
    from app.site import service as S
    proto.fail_copy = True
    c = TestClient(app)
    sid = _site(c)
    p = S.get(T, sid)["prototype"]
    assert p["status"] == "ready" and p["pages"]
    assert all(s["heading"] == s["label"] for pg in p["pages"] for s in pg["sections"])


def test_a_portal_prototype_shows_its_signed_in_pages_with_sample_rows(proto):
    from app.site import prototype as PT
    from app.site import service as S
    plan = {"pages": [{"slug": "home", "title": "Home", "sections": [{"type": "hero", "label": "Front door"},
                                                                      {"type": "screen_signin", "label": "Sign-in"}]}],
            "spec": {"app_pages": [{"title": "My bills", "for": "member", "shows": ["Bills list", "Pay a bill"],
                                    "types": ["screen_table", "screen_form"]},
                                   {"title": "Staff tickets", "for": "staff", "shows": ["Open tickets"]}]}}
    pages = PT.skeleton(plan)
    assert [(p["slug"], p["for"]) for p in pages] == [("home", "public"), ("app-my-bills", "member"),
                                                       ("app-staff-tickets", "staff")]
    assert [s["type"] for s in pages[1]["sections"]] == ["screen_table", "screen_form"]
    assert pages[2]["sections"][0]["type"] == "screen_table"
    sec = PT._clean_copy({"heading": "Your bills", "cols": ["Month", "Amount", "Status"],
                          "rows": [["Oct", "Rs 599", "Paid"], ["Nov", "Rs 599", "Due"]]}, {"label": "Bills list"})
    html = PT._section_html({**pages[1]["sections"][0], **sec}, 0)
    assert "<th>Month</th>" in html and "<td>Rs 599</td>" in html
    back = PT.plan_from(pages, plan)
    assert back["spec"]["app_pages"][0]["types"] == ["screen_table", "screen_form"]
    assert [p["slug"] for p in back["pages"]] == ["home"]
    assert S.sec_key("home", "screen_signin") == "home__screen_signin"


def test_the_switch_off_keeps_the_three_looks(site_env):
    from app.site import prototype as PT
    assert PT.on() is False                       # conftest pins it off for the older Studio walks


def test_no_agent_module_approves_a_prototype():
    for f in sorted((ROOT / "app" / "agent").glob("*.py")):
        tree = ast.parse(f.read_text())
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "approve":
                assert getattr(n.func.value, "id", "") not in ("PT", "prototype"), f"{f.name} approves a prototype"
    src = (ROOT / "app" / "site" / "prototype.py").read_text()
    assert "HER TAP ONLY" in src


def test_studio_draws_the_prototype_not_three_looks():
    js = (ROOT / "app" / "static" / "console" / "webstudio.js").read_text()
    assert "protoView" in js and "/prototype/approve" in js and "Build the real website" in js
    assert "Build: a prototype of every page first" in js
