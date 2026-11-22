"""v0.989 LIVE SCREENS + OWN DATA (owner: "GO B1 B2" on docs/research/lovable/03_backend_vs_hoola.md).

B1: a portal's designed screens are tied to the site's REAL lists at build time (data-list / data-fields checked against
the schema, data-sample dropped, data-bound added) and the page script fills them with the rows the visitor may see;
sample rows stay only in the Studio preview while a list is empty.
B2: the Studio preview and every draft have their OWN data (a twin project): the preview follows the website's structure,
a draft is a fork whose Accept carries only new lists / fields (never rows); twins never reach the outside world."""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_v0305_web_apps import DESIGN, T, app_site  # noqa: F401  (fixture)
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

ASSETS = Path(__file__).resolve().parents[1] / "app" / "site" / "assets"
SCHEMA = {"collections": [
    {"key": "connections", "label": "Connections", "rules": {"read": "members", "create": "admin"},
     "fields": [{"key": "name", "type": "text"}, {"key": "plan", "type": "choice", "options": ["50 Mbps", "100 Mbps"]},
                {"key": "bill", "type": "number"}, {"key": "secret_note", "type": "text", "hidden": True}]},
    {"key": "tickets", "label": "Support tickets", "rules": {"read": "own", "create": "member"},
     "fields": [{"key": "subject", "type": "text"}, {"key": "status", "type": "choice", "options": ["Open", "Closed"]}]}]}


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.117"


# ---------------------------------------------------------------- B1: binding screens to real lists
def test_bind_ties_a_screen_to_the_real_list_and_fields():
    from app.site import screens as SC
    html = ('<section><div class="hoola-screen" data-hoola-screen="screen_table" data-list="Connection" '
            'data-fields="name,plan,nope,secret_note" data-sample><span data-sample-chip>Sample data</span>'
            '<table><tbody data-hoola-live><tr><td>Asha</td></tr></tbody></table></div></section>')
    out, probs = SC.bind(html, SCHEMA)
    assert probs == []
    assert 'data-list="connections"' in out and 'data-fields="name,plan"' in out      # matched by label; unknown / hidden dropped
    assert "data-bound" in out and "data-sample=" not in out.replace("data-sample-chip", "")
    assert "<td>Asha</td>" in out                                                        # samples stay for the preview


def test_bind_keeps_an_unmatched_screen_as_sample_and_says_so():
    from app.site import screens as SC
    html = '<div class="hoola-screen" data-hoola-screen="screen_board" data-list="leads" data-sample><p>x</p></div>'
    out, probs = SC.bind(html, SCHEMA)
    assert "data-sample" in out and "data-bound" not in out
    assert probs and "board screen is not tied" in probs[0]
    out2, probs2 = SC.bind(html, {})                                                     # no lists at all
    assert "data-sample" in out2 and probs2


def test_bind_stats_signin_and_fallbacks():
    from app.site import screens as SC
    html = ('<div class="hoola-screen" data-hoola-screen="screen_dashboard" data-list="tickets" data-sample>'
            '<div data-hoola-stat="sum:bill" data-list="connections"><b data-hoola-num>12</b></div>'
            '<div data-hoola-stat="sum:nothing"><b data-hoola-num>3</b></div></div>'
            '<div class="hoola-screen" data-hoola-screen="screen_signin" data-sample><div data-hoola-live><input></div></div>')
    out, probs = SC.bind(html, SCHEMA)
    assert probs == []
    assert 'data-hoola-stat="sum:bill"' in out                                          # a real field: kept
    assert 'data-hoola-stat="count" data-list="tickets"' in out or (
        'data-hoola-stat="count"' in out and out.count('data-list="tickets"') >= 2)      # unknown sum -> count of the screen's list
    assert '<div data-hoola-app="login"></div>' in out and "<input" not in out           # Hoola's own sign-in, never hers
    assert out.count("data-bound") == 2
    assert SC.bind("<p>no screens</p>", SCHEMA) == ("<p>no screens</p>", [])


def test_writer_is_told_the_real_lists_for_a_screen(app_site):
    from app.site import ai as AI
    from app.site import service as S
    from app.site import screens as SC
    S.design_app(T, app_site, "customers apna order track karein")
    r = S._load(app_site)
    line = S._screen_lists(r)
    assert line.startswith("LISTS") and "orders" in line and "read" in line
    assert "data-list" in AI.SCREEN_NOTE and "data-hoola-live" in AI.SCREEN_NOTE and "data-hoola-stat" in AI.SCREEN_NOTE
    assert "never write your own login" in S._app_line(r, screen=True)
    assert "orders" in SC.lists_line(S.app_schema(r))


def test_page_script_and_styles_fill_live_screens():
    js = (ASSETS / "hoola-app.js").read_text()
    css = (ASSETS / "hoola-site.css").read_text()
    assert "function screens()" in js and "screens();                         // v0.989" in js
    assert "data-ds') === 'preview'" in js and "[data-hoola-screen][data-bound]" in js
    assert "if (!rows.length) { if (!PREVIEW) scrMsg(live, t.empty); return; }" in js      # live: empty says so, preview keeps samples
    assert "html:not([data-hoola-ds]) .hoola-screen[data-bound] [data-hoola-live]:not([data-live]){visibility:hidden}" in css
    assert "html:not([data-hoola-ds]) .hoola-screen[data-bound] [data-sample-chip]{display:none}" in css


# ---------------------------------------------------------------- B2: the preview's own data
def test_preview_pages_are_rewritten_to_the_preview_dataset(app_site):
    from app.site import service as S
    S.design_app(T, app_site, "customers apna order track karein")
    r = S._load(app_site)
    api = S.app_api(r)
    html = f'<!doctype html><html lang="en"><head><meta name="hoola-app" content="{api}" data-lang="en"></head></html>'.encode()
    out = S.preview_dataset(html, r).decode()
    assert f'content="{api}~p" data-ds="preview"' in out and '<html data-hoola-ds="preview" lang="en">' in out
    assert S.preview_dataset(b"<html><p>no app</p></html>", r) == b"<html><p>no app</p></html>"


def test_preview_has_its_own_rows_and_members(app_site):
    from app.main import app
    from app.site import applink as AL
    from app.site import service as S
    from app.site import twin as TW
    from app.site import webapp as W
    sid = app_site
    c = TestClient(app)
    S.design_app(T, sid, "customers apna order track karein")
    c.post(f"/api/sites/{sid}/link-app")
    live, prev = f"/api/site-app/{sid}", f"/api/site-app/{sid}{TW.PREVIEW}"
    main = AL.project(S._load(sid))
    assert main is not None and not TW.is_twin(main)
    # a staff account of the website exists before the preview is first used: it is copied in
    W._RATE.clear()
    a = c.post(f"{live}/signup", json={"email": "boss@x.in", "password": "boss-pass-1", "name": "Boss"}).json()
    with W.session() as s:
        m = s.query(W.SiteAppMember).filter_by(site_id="app:" + main.id, email="boss@x.in").one()
        m.role = "admin"
    assert a["token"]
    # the preview sign-up and order land in the twin, never in the live data
    W._RATE.clear()
    t = c.post(f"{prev}/signup", json={"email": "test@x.in", "password": "test-pass-1", "name": "Tester"}).json()
    h = {"Authorization": "Bearer " + t["token"]}
    row = c.post(f"{prev}/c/orders", headers=h, json={"item": "Test order", "phone": "9876500000"})
    assert row.status_code == 200, row.text
    tw = TW.preview_of(main)
    assert TW.is_twin(tw) and TW.of(tw) == main.id and tw.status == "twin"
    with W.session() as s:
        assert s.query(W.SiteAppRow).filter_by(site_id="app:" + main.id).count() == 0
        assert s.query(W.SiteAppRow).filter_by(site_id="app:" + tw.id).count() == 1
        assert s.query(W.SiteAppMember).filter_by(site_id="app:" + main.id, email="test@x.in").count() == 0
        assert s.query(W.SiteAppMember).filter_by(site_id="app:" + tw.id, email="boss@x.in", role="admin").count() == 1
    # the preview test account cannot sign in to the live site
    assert c.post(f"{live}/login", json={"email": "test@x.in", "password": "test-pass-1"}).status_code >= 400
    # same twin next time; it follows a structure change of the website (never its rows)
    assert TW.preview_of(AL.project(S._load(sid))).id == tw.id
    from app.appmaker import backend as BE
    BE.change_schema(AL.project(S._load(sid)), {"add": [{"coll": "orders", "key": "landmark", "type": "text"}]}, "test")
    keys = [f["key"] for c_ in c.get(f"{prev}/schema").json()["collections"] if c_["key"] == "orders" for f in c_["fields"]]
    assert "landmark" in keys
    with W.session() as s:
        assert s.query(W.SiteAppRow).filter_by(site_id="app:" + tw.id).count() == 1


def test_twins_never_reach_the_outside_world(app_site):
    from app.appmaker import connect as CN
    from app.appmaker import service as AS
    from app.main import app
    from app.site import applink as AL
    from app.site import service as S
    from app.site import twin as TW
    sid = app_site
    c = TestClient(app)
    S.design_app(T, sid, "customers apna order track karein")
    c.post(f"/api/sites/{sid}/link-app")
    from app.appmaker import backend as BE
    main = AL.project(S._load(sid))
    BE.patch_backend(main, fn=lambda be: be.update({"pay": {"key": "sealed"}, "connect": {"actions": []}}))
    tw = TW.preview_of(AL.project(S._load(sid)))
    be = json.loads(tw.backend)
    assert "pay" not in be and "connect" not in be and "twins" not in be                   # never copied
    assert CN.fire(tw, "orders", "x", "created") == 0
    try:
        CN.run(tw, "anything")
        raise AssertionError("a twin must not run an outside action")
    except CN.ConnError as e:
        assert e.code == 409 and "outside services are not called" in str(e)
    assert tw.id not in [x.get("id") for x in (AS.apps(T) or {}).get("apps", [])] if isinstance(AS.apps(T), dict) else True
    TW.drop(tw.id)
    assert TW._load(tw.id) is None
    TW.drop(main.id)                                                                     # only a twin ever goes
    assert TW._load(main.id) is not None


# ---------------------------------------------------------------- B2: a draft's own data
def test_a_draft_has_its_own_data_and_accept_moves_structure_not_rows(app_site, monkeypatch):
    from tests.test_v0808_wapas import _fast_checks
    _fast_checks(monkeypatch)
    from app.appmaker import backend as BE
    from app.main import app
    from app.site import applink as AL
    from app.site import drafts as DF
    from app.site import service as S
    from app.site import twin as TW
    from app.site import webapp as W
    sid = app_site
    c = TestClient(app)
    S.design_app(T, sid, "customers apna order track karein")
    c.post(f"/api/sites/{sid}/link-app")
    main = AL.project(S._load(sid))
    d = DF.create(T, sid, "Try data")["id"]
    dp = AL.project(S._load(d))
    assert dp is not None and dp.id != main.id and TW.of(dp) == main.id                # the draft's own data
    W._RATE.clear()
    u = c.post(f"/api/site-app/{d}/signup", json={"email": "d@x.in", "password": "draft-pass-1", "name": "D"}).json()
    c.post(f"/api/site-app/{d}/c/orders", headers={"Authorization": "Bearer " + u["token"]}, json={"item": "Draft row", "phone": "9876500001"})
    with W.session() as s:
        assert s.query(W.SiteAppRow).filter_by(site_id="app:" + main.id).count() == 0
        assert s.query(W.SiteAppRow).filter_by(site_id="app:" + dp.id).count() == 1
    BE.change_schema(dp, {"add_list": [{"key": "feedback", "label": "Feedback", "rules": {"create": "public", "read": "admin"},
                                        "fields": [{"key": "note", "type": "text"}]}],
                          "add": [{"coll": "orders", "key": "gift_wrap", "type": "yes_no"}]}, "draft test")
    moved = TW.carry(dp.id, main.id)
    assert "list feedback" in moved and "field orders.gift_wrap" in moved
    keys = [x["key"] for x in BE.schema(AL.project(S._load(sid)))["collections"]]
    assert "feedback" in keys
    with W.session() as s:                                                               # rows never move
        assert s.query(W.SiteAppRow).filter_by(site_id="app:" + main.id).count() == 0
    assert TW.carry(dp.id, main.id) == []                                                # nothing new the second time
    DF.discard(T, sid, d)
    assert TW._load(dp.id) is None                                                       # the draft's data went with it
    with W.session() as s:
        assert s.query(W.SiteAppMember).filter_by(site_id="app:" + dp.id).count() == 0


def test_browser_walk_live_vs_preview():
    """The page script in a real browser against a fake data server: live shows real rows (never the samples), an empty
    live list says so, a list behind a login says that; the preview keeps its samples while a list is empty."""
    import pytest
    pw = pytest.importorskip("playwright.sync_api")
    js, css = (ASSETS / "hoola-app.js").read_text(), (ASSETS / "hoola-site.css").read_text()
    schema = {"collections": [
        {"key": "connections", "label": "Connections", "rules": {"read": "public", "create": "public", "update": "admin", "delete": "admin"},
         "fields": [{"key": "name", "label": "Name", "type": "text"}, {"key": "plan", "label": "Plan", "type": "choice", "options": ["50 Mbps", "100 Mbps"]},
                    {"key": "bill", "label": "Bill", "type": "number"}]},
        {"key": "tickets", "label": "Tickets", "rules": {"read": "own", "create": "member"}, "fields": [{"key": "subject", "label": "Subject", "type": "text"}]}]}

    def page(ds):
        meta = '<meta name="hoola-app" content="http://api.test/x"%s data-lang="en">' % (' data-ds="preview"' if ds else "")
        return (f'<!doctype html><html{" data-hoola-ds=preview" if ds else ""}><head>{meta}<style>{css}</style></head><body>'
                '<div class="hoola-screen" data-hoola-screen="screen_table" data-list="connections" data-fields="name,plan" data-bound>'
                '<span data-sample-chip>Sample data</span><button data-hoola-add>Add</button>'
                '<table><tbody data-hoola-live><tr><td>Sample Asha</td><td>50 Mbps</td></tr></tbody></table>'
                '<div data-hoola-stat="sum:bill" data-list="connections"><b data-hoola-num>999</b></div></div>'
                '<div class="hoola-screen" data-hoola-screen="screen_board" data-list="tickets" data-bound><div data-hoola-live><p>Sample ticket</p></div></div>'
                f'<script>{js}</script></body></html>')

    def run(ds, rows):
        hdr = {"content-type": "application/json", "access-control-allow-origin": "*"}
        with pw.sync_playwright() as p:
            try:
                b = p.chromium.launch()
            except Exception as e:                       # noqa: BLE001
                pytest.skip(f"no Chromium here: {e}")
            pg = b.new_page()

            def api(route):
                u = route.request.url
                if "/c/tickets" in u:
                    return route.fulfill(status=401, body=json.dumps({"error": "login"}), headers=hdr)
                body = schema if u.endswith("/schema") else {"rows": rows} if "/c/connections" in u else {}
                route.fulfill(status=200, body=json.dumps(body), headers=hdr)
            pg.route("http://api.test/**", api)
            pg.route("http://site.test/", lambda r: r.fulfill(status=200, body=page(ds), headers={"content-type": "text/html"}))
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto("http://site.test/")
            pg.wait_for_timeout(800)
            out = pg.evaluate("""() => ({tbody: document.querySelector('tbody').innerText, chip: getComputedStyle(document.querySelector('[data-sample-chip]')).display,
              num: document.querySelector('[data-hoola-num]').textContent, board: document.querySelectorAll('[data-hoola-live]')[1].innerText})""")
            pg.click("[data-hoola-add]")
            pg.wait_for_timeout(200)
            out["form"] = pg.evaluate("() => !!document.querySelector('.hs-screen-add form')")
            b.close()
        assert errs == [], errs
        return out

    rows = [{"id": "r1", "name": "Ravi", "plan": "100 Mbps", "bill": 799}, {"id": "r2", "name": "Meena", "plan": "50 Mbps", "bill": 499}]
    live = run(False, rows)
    assert "Ravi" in live["tbody"] and "Sample" not in live["tbody"] and live["chip"] == "none" and live["num"] == "1,298"
    assert live["board"] == "Please log in first." and live["form"]
    assert run(False, [])["tbody"] == "Nothing here yet."
    prev = run(True, [])
    assert "Sample Asha" in prev["tbody"] and prev["chip"] != "none" and prev["num"] == "999" and prev["board"] == "Sample ticket"
