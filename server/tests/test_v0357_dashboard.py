"""v0.357 DASHBOARD (built as 0.353) (web design Phase 7 step 2, owner: "Phase 3b (dashboards and charts)"). Three parts:
(1) charts on her websites: a section writes a plain table inside <figure data-hoola-chart> and ONE drawer
    (static/console/charts.js, copied into the site as assets/hoola-chart.js) turns it into inline SVG - checked in a real
    browser: bars / line / donut / hbar, Indian numbers (lakh / crore), tooltip on hover AND arrow keys, the table kept for
    screen readers, nothing drawn when there are no numbers;
(2) her dashboard: every number the site already records, per IST day, this period vs the one before (visits, enquiries,
    bookings, orders, CONFIRMED sales only, top pages / products, status mix, web-app records) - owner only;
(3) the staff dashboard of her web apps (/admin/ on her site): rows a day, status mix, sums - staff and her only."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0305_web_apps import DESIGN, app_site  # noqa: F401  (fixture)
from tests.test_v0351_dukaan import BUYER, _built_shop, _order
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

CHARTS = Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "charts.js"
IST = timezone(timedelta(hours=5, minutes=30))


# ---------------------------------------------------------------- 1. the chart drawer, in a real browser
PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
.hc{position:relative}.hc-table{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
body{width:640px;font:14px sans-serif}</style></head><body>
<figure id="f1" data-hoola-chart="bar" data-unit="₹"><figcaption>Bikri</figcaption><table>
<thead><tr><th>Saal</th><th>Bikri</th><th>Kharcha</th></tr></thead><tbody>
<tr><th>2022</th><td>50 lakh</td><td>30 lakh</td></tr><tr><th>2023</th><td>₹1.2 Cr</td><td>70 lakh</td></tr>
<tr><th>2024</th><td>2,50,00,000</td><td>1 crore</td></tr></tbody></table></figure>
<figure id="f2" data-hoola-chart="donut"><figcaption>Students</figcaption><table><tr><th>Course</th><th>Students</th></tr>
<tr><td>JEE</td><td>120</td></tr><tr><td>NEET</td><td>80</td></tr></table></figure>
<figure id="f3" data-hoola-chart="line"><table><tr><th>Month</th><th>Visits</th></tr><tr><td>Jan</td><td>12k</td></tr>
<tr><td>Feb</td><td>15k</td></tr><tr><td>Mar</td><td>9k</td></tr></table></figure>
<figure id="f4" data-hoola-chart="hbar"><table><tr><th>Branch</th><th>Patients</th></tr><tr><td>Akola</td><td>340</td></tr>
<tr><td>Amravati</td><td>210</td></tr></table></figure>
<figure id="f5" data-hoola-chart="bar"><table><tr><th>Kya</th><th>Kab</th></tr><tr><td>Diwali</td><td>jald hi</td></tr></table></figure>
<script>SCRIPT</script></body></html>"""


@pytest.fixture
def page():
    pw = pytest.importorskip("playwright.sync_api")
    import os
    exe = os.environ.get("HOOLA_CHROMIUM") or None
    with pw.sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        pg = b.new_page(viewport={"width": 700, "height": 1600})
        pg.set_content(PAGE.replace("SCRIPT", CHARTS.read_text()))
        pg.wait_for_selector("#f4 svg")
        yield pg
        b.close()


def test_numbers_the_indian_way(page):
    got = page.evaluate("""() => [HoolaChart.fmt(12000000), HoolaChart.fmt(125000), HoolaChart.fmt(1500, true),
        HoolaChart.fmt(12500000, true), HoolaChart.fmt(250000000, true), HoolaChart.num('50 lakh'), HoolaChart.num('₹2.5 Cr'),
        HoolaChart.num('12k'), HoolaChart.num('1,20,000'), HoolaChart.num('45%'), HoolaChart.num('jald hi')]""")
    assert got == ["1,20,00,000", "1,25,000", "1.5K", "1.3 Cr", "25 Cr", 5000000, 25000000, 12000, 120000, 45, None]


def test_tables_become_charts(page):
    # bar: 3 years x 2 series = 6 bars, a legend, the table kept (visually hidden) for screen readers
    assert page.locator("#f1 svg .hc-bar").count() == 6
    assert page.locator("#f1 .hc-leg li").all_inner_texts() == ["Bikri", "Kharcha"]
    label = page.get_attribute("#f1 svg", "aria-label")
    assert label.startswith("Bikri. Bar chart, 3 items") and "2024 ₹2,50,00,000" in label
    assert "hc-table" in page.get_attribute("#f1 table", "class") and page.locator("#f1 table").count() == 1
    assert "₹" in " ".join(page.locator("#f1 .hc-ax").all_text_contents())          # axis in rupees (compact: L / Cr)
    # donut: 2 slices + total in the middle; line: one path + 3 dots; hbar: 2 rows with values
    assert page.locator("#f2 .hc-slice").count() == 2 and page.locator("#f2 .hc-big").text_content() == "200"
    assert page.locator("#f3 .hc-line").count() == 1 and page.locator("#f3 .hc-dot").count() == 3
    assert page.locator("#f4 .hc-bar").count() == 2 and page.locator("#f4 .hc-val").all_text_contents() == ["340", "210"]
    # no numbers -> nothing drawn, the table stays as it was
    assert page.locator("#f5 svg").count() == 0 and page.get_attribute("#f5 table", "class") is None


def test_tooltip_by_mouse_and_by_keyboard(page):
    box = page.locator("#f1 svg").bounding_box()
    page.mouse.move(box["x"] + box["width"] * 0.9, box["y"] + box["height"] * 0.5)
    tip = page.locator("#f1 .hc-tip")
    assert tip.is_visible() and "2024" in tip.inner_text() and "Bikri: ₹2,50,00,000" in tip.inner_text()
    page.mouse.move(0, 0)
    assert not tip.is_visible()
    page.focus("#f4 svg")
    page.keyboard.press("ArrowRight")
    assert page.locator("#f4 .hc-tip").inner_text().splitlines() == ["Akola", "340"]
    page.keyboard.press("ArrowRight")
    assert page.locator("#f4 .hc-tip").inner_text().splitlines()[0] == "Amravati"
    page.keyboard.press("Escape")
    assert not page.locator("#f4 .hc-tip").is_visible()


# ---------------------------------------------------------------- 2. the site build carries the drawer
def test_pages_load_the_drawer_only_when_they_draw(app_site):
    from app.site import build as B
    from app.site import service as S
    assert B.uses_charts('<figure data-hoola-chart="bar">') and B.uses_charts('<div data-hoola-app="admin"></div>')
    assert not B.uses_charts("<section>plain</section>")
    from app.main import app
    TestClient(app).post(f"/api/sites/{app_site}/app-design", json={"words": "customers apna order track karein"})
    g = S.get(T, app_site)
    out = B.out_dir(T, app_site, g["version"])
    assert (out / "assets" / "hoola-chart.js").read_text() == CHARTS.read_text()
    assert "assets/hoola-chart.js" in (out / "admin" / "index.html").read_text()      # the staff panel draws charts
    assert "assets/hoola-chart.js" not in (out / "index.html").read_text()
    from app.site import ai as AI
    from app.site import sitemap as SM
    assert "data-hoola-chart" in AI.RUNTIME_GUIDE and "never a made-up chart" in AI.RUNTIME_GUIDE
    assert "growth chart of numbers she gave" in SM.SITEMAP_SYSTEM


# ---------------------------------------------------------------- 3. her dashboard
def _ist(days_ago: int, hour: int = 12) -> datetime:
    d = datetime.now(IST).replace(hour=hour, minute=0, second=0, microsecond=0) - timedelta(days=days_ago)
    return d.astimezone(timezone.utc)


def test_her_dashboard_counts_every_day_and_compares(site_env):
    from app.db import session
    from app.site import care as SC
    from app.site import dash as D
    from app.site import service as S
    from app.site import shop as SH
    from app.site.models import SiteLead
    sid = _built_shop(S)
    with session() as s:
        for ago, views, pages in ((0, 40, {"/": 30, "/shop/": 10}), (3, 25, {"/": 25}), (40, 10, {"/": 10})):   # 40 days ago = previous period
            s.add(SC.SiteCareDay(site_id=sid, tenant_id=T, day=_ist(ago).astimezone(IST).date().isoformat(), views=views,
                                 pages=json.dumps(pages)))
        s.add(SiteLead(site_id=sid, tenant_id=T, name="A", phone="9876500000", created_at=_ist(1)))
        s.add(SiteLead(site_id=sid, tenant_id=T, name="B", phone="9876500001", kind="booking", created_at=_ist(1)))
        s.add(SiteLead(site_id=sid, tenant_id=T, name="spam", phone="9876500002", status="spam", created_at=_ist(1)))
        s.add(SiteLead(site_id=sid, tenant_id=T, name="C", phone="9876500003", created_at=_ist(45)))
    a = _order(S, sid, [{"slug": "kaju-katli", "qty": 2}])                       # ₹1,840 (+₹40 delivery)
    b = _order(S, sid, [{"slug": "motichoor-laddoo", "qty": 1}], method="cod")  # ₹640
    c = _order(S, sid, [{"slug": "motichoor-laddoo", "qty": 1}], method="cod")
    S.shop_move(T, sid, a["number"], "confirmed")
    S.shop_move(T, sid, c["number"], "cancelled")
    d = D.dashboard(T, sid, 30)
    k = {x["key"]: x for x in d["kpis"]}
    assert k["visits"]["value"] == 65 and k["visits"]["prev"] == 10 and k["visits"]["change_pct"] == 550.0
    assert k["enquiries"]["value"] == 2 and k["enquiries"]["prev"] == 1                 # spam never counted
    assert k["orders"]["value"] == 2                                                   # a cancelled order is not an order
    assert k["sales"]["value"] == 1840.0 and k["sales"]["money"]                       # only what SHE confirmed
    assert k["aov"]["value"] == 1840.0 and k["conversion"]["value"] == round(100 * 2 / 65, 1)
    sr = d["series"]
    assert len(sr["days"]) == 30 and sr["days"][-1] == datetime.now(IST).date().isoformat()
    assert sum(sr["visits"]) == 65 and sum(sr["visits_prev"]) == 10 and sr["visits"][-1] == 40
    assert sum(sr["enquiries"]) == 1 and sum(sr["bookings"]) == 1 and sum(sr["sales"]) == 1840.0 and sum(sr["orders"]) == 2
    assert list(d["top_pages"][0]) == ["/", 55] and d["top_products"] == [["Kaju Katli", 2, 1800.0]]
    assert [x[2] for x in d["status_mix"]] == ["new", "confirmed", "cancelled"]
    assert "65 visit" in d["say"] and "₹1,840" in d["say"] and d["shop"] is True and d["app"] is None
    assert D.dashboard(T, sid, 3)["days"] == 7 and len(D.dashboard(T, sid, 9999)["series"]["days"]) == 365   # clamped
    assert b["number"] and SH.WORDS["new"] in [x[0] for x in d["status_mix"]]


def test_dashboard_without_a_shop_and_owner_only(site_env):
    from app.main import app, current_tenant
    from app.site import service as S
    v = S.new(T, "dentist clinic website", name="Smile Clinic", answers={"phone": "9876543210"})
    S.approve_plan(T, v["id"])
    S.choose_look(T, v["id"], 0)
    c = TestClient(app)
    d = c.get(f"/api/sites/{v['id']}/dashboard?days=7").json()
    assert d["shop"] is False and "orders" not in d["series"] and {x["key"] for x in d["kpis"]} == {"visits", "enquiries", "conversion"}
    assert d["series"]["visits"] == [0] * 7 and "0 visit" in d["say"]
    app.dependency_overrides[current_tenant] = lambda: "someone-else"
    try:
        assert c.get(f"/api/sites/{v['id']}/dashboard").status_code in (400, 403, 404)
    finally:
        app.dependency_overrides.pop(current_tenant, None)
    from app.agent import site_tools as ST
    dekho = next(t for t in ST.SITE_TOOLS if t["name"] == "website_dekho")
    assert "dashboard" in dekho["input_schema"]["properties"]["what"]["enum"]
    from types import SimpleNamespace
    out = ST._read(SimpleNamespace(tenant_id=T), "dashboard", {"site": v["id"], "days": 7})
    assert "kpis" in out and "series" not in out and len(out["busiest_days"]) == 5


# ---------------------------------------------------------------- 4. the web app's staff dashboard
def test_staff_dashboard_is_staff_only(app_site):
    from app.main import app
    from app.site import webapp as W
    c = TestClient(app)
    sid = app_site
    c.post(f"/api/sites/{sid}/app-design", json={"words": "customers apna order track karein"})
    base = f"/api/site-app/{sid}"
    a = c.post(f"{base}/signup", json={"email": "asha@x.in", "password": "asha-pass-1", "name": "Asha"}).json()
    ha = {"Authorization": "Bearer " + a["token"]}
    for item, qty in (("Kaju katli", "2"), ("Laddoo", "3")):
        assert c.post(f"{base}/c/orders", headers=ha, json={"item": item, "qty": qty, "phone": "9876500000"}).status_code == 200
    assert c.get(f"{base}/stats").status_code == 401                             # a visitor
    assert c.get(f"{base}/stats", headers=ha).status_code == 403                  # a customer
    m = next(x for x in W.members(sid) if x["email"] == "asha@x.in")
    W.set_role(sid, m["id"], "staff")
    staff = {"Authorization": "Bearer " + c.post(f"{base}/login", json={"email": "asha@x.in", "password": "asha-pass-1"}).json()["token"]}
    st = c.get(f"{base}/stats", headers=staff).json()
    orders = next(x for x in st["lists"] if x["key"] == "orders")
    assert len(st["days"]) == 30 and orders["count"] == 2 and orders["days"][-1] == 2
    assert orders["mix"] == {"field": "Status", "items": [["Naya", 2], ["Ban raha", 0], ["Taiyaar", 0]]}
    assert orders["sums"] == [["Quantity", 5.0]] and st["members"] == 1
    # her own dashboard sees the web app too
    from app.site import dash as D
    d = D.dashboard(T, sid, 30)
    assert d["app"]["total"] == 2 and d["app"]["lists"][0]["days"][-1] == 2
    assert any(x["key"] == "records" and x["value"] == 2 for x in d["kpis"])


# ---------------------------------------------------------------- 5. console + phone
def test_console_and_phone_show_it():
    root = Path(__file__).resolve().parents[2]
    con = root / "server" / "app" / "static" / "console"
    html = (con / "v2.html").read_text()
    assert html.index("console/charts.js") < html.index("console/build.js")         # the drawer before the studio
    js = (con / "build.js").read_text()
    assert "['dash', 'Dashboard']" in js and "loadDash(o, ot)" in js and "/dashboard?days=" in js
    css = (con / "v2.css").read_text()
    assert css.index(".stdash{") < css.index("/* ===== v0.288 SIDEBAR FULLY VISIBLE") and ".hc-in" not in css   # no held motion
    dart = (root / "lib" / "ui" / "site_dash.dart").read_text()
    assert "siteDashboard(widget.id, days: _days)" in dart and "class SiteDashPage" in dart
    assert "SiteDashPage(" in (root / "lib" / "ui" / "site_screen.dart").read_text()
    assert "'/api/sites/$id/dashboard'" in (root / "lib" / "api.dart").read_text()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.367.0"
    assert "0.367.0+407" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
