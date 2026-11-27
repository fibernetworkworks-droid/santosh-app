"""DATABASE DESK: the Database Engine Developer's own section, built like the finance desks - its own chat (kind 'dbengine') with
the desk block + the database tool in view; query plans read from PostgreSQL (text + JSON), MySQL (tree + table) and SQLite with the
findings first (a full scan that throws rows away + the index to try, an estimate far off reported once at its source, a sort that
spilled, a repeated scan in a nested loop, lossy bitmaps); one query checked and the index it asks for; a schema reviewed; the index
PROVED in a throwaway SQLite lab (used, same rows, faster) and the lab refusing anything but one SELECT; benchmarks read and
compared; walked in a browser."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from tests import db_samples as D

T = "default"


@pytest.fixture
def dbc(env):
    from app import dbchat as C
    C._OF.clear()
    C._BLOCK.clear()
    return C


def _hire():
    from app.employee import hire
    hire.hire(T, "dbengine_dev", trust="seekh")


# ---------------------------------------------------------------- the readers (pure code)
def test_plans_in_every_format():
    from app.dbdesk import plans
    r = plans.read(D.PG_TEXT)
    kinds = [(f["sev"], f["kind"]) for f in r["findings"]]
    assert r["engine"] == "PostgreSQL" and r["analyzed"] and r["steps"] == 5 and r["total_ms"] == 414.208 and r["planning_ms"] == 0.311
    assert kinds[:2] == [("bad", "spill"), ("bad", "scan")] and [k for k in kinds if k[1] == "estimate"] == [("warn", "estimate")]
    scan = next(f for f in r["findings"] if f["kind"] == "scan")
    assert scan["rel"] == "orders" and scan["cols"] == ["status", "customer_id"] and "1,000,000 rows to keep 4,980" in scan["say"]
    seq = r["root"]["children"][0]["children"][0]
    assert seq["op"] == "Seq Scan" and seq["alias"] == "o" and round(seq["self_ms"], 1) == 390.4
    lp = plans.read(D.PG_LOOP)
    assert any(f["kind"] == "loop" and "3,000 times" in f["say"] for f in lp["findings"])
    j = plans.read(D.PG_JSON)
    assert j["format"] == "postgres-json" and any(f["kind"] == "bitmap" for f in j["findings"])
    assert [f["where"] for f in j["findings"] if f["kind"] == "estimate"] == ["Bitmap Index Scan"]          # reported once, at its source
    m = plans.read(D.MYSQL_TREE)
    assert m["engine"] == "MySQL" and any(f["kind"] == "scan" and f["cols"] == ["customer_id"] and f["sev"] == "bad" for f in m["findings"])
    t = plans.read(D.MYSQL_TABLE)
    assert {f["kind"] for f in t["findings"]} == {"scan", "sort"} and "idx_status" in t["findings"][0]["say"] and not t["analyzed"]
    s = plans.read(D.SQLITE_EQP)
    assert s["engine"] == "SQLite" and s["steps"] == 4 and {f["kind"] for f in s["findings"]} == {"scan", "sort"}
    assert not plans.read("hello")["ok"]


def test_query_schema_lab_bench():
    from app.dbdesk import bench, lab, schema, sqlcheck
    q = sqlcheck.check(D.QUERY)
    assert q["suggest"][0]["sql"] == "CREATE INDEX ON orders (customer_id, status, created_at);"
    b = sqlcheck.check("select id from users u where lower(u.email) = 'a@b.c' and name like '%sha%' and x not in (select y from z) order by id limit 20 offset 50000")
    says = " ".join(i["say"] for i in b["issues"])
    assert "lower(u.email)" in says and "LIKE '%...'" in says and "NOT IN" in says and "OFFSET 50000" in says and b["counts"]["bad"] == 3
    assert "UPDATE / DELETE without WHERE" in " ".join(i["say"] for i in sqlcheck.check("DELETE FROM orders")["issues"])
    sc = schema.review(D.SCHEMA)
    says = [i["say"] for i in sc["issues"]]
    assert sc["counts"]["bad"] == 1 and "audit_log has no primary key" in says[0]
    assert any("orders.customer_id references customers but has no index" in x for x in says)
    assert any("orders_status_idx (status) is covered by orders_status_created_idx" in x for x in says)
    assert not any("references" in x for x in schema.review(D.SCHEMA, "mysql")["issues"])            # InnoDB indexes FKs itself
    r = lab.prove(D.SCHEMA, D.QUERY, "CREATE INDEX ON orders (customer_id, status, created_at);", 20000)
    assert r["used"] and r["same_result"] and r["after"]["ms"] < r["before"]["ms"] and r["rows"] == {"customers": 1000, "orders": 20000}
    assert any("lab_orders_customer_id_status_created_at" in p for p in r["after"]["plan"])
    for bad, why in (("DELETE FROM orders", "SELECT queries only"), ("SELECT 1; DROP TABLE orders", "One query only"),
                     ("SELECT * FROM orders WHERE id IN (SELECT load_extension('x'))", "not allowed"),
                     ("SELECT * FROM nowhere", "None of the query's tables")):
        with pytest.raises(lab.LabError, match=why):
            lab.prove(D.SCHEMA, bad, "", 100)
    with pytest.raises(lab.LabError, match="CREATE INDEX"):
        lab.prove(D.SCHEMA, D.QUERY, "DROP TABLE orders", 100)
    a, s2 = bench.read(D.PGBENCH), bench.read(D.PGBENCH_SLOW)
    assert (a["tool"], a["tps"], a["clients"], a["lat_avg"]) == ("pgbench", 8538.912345, 16, 1.874)
    c = bench.compare(a, s2, 5)
    assert c["verdict"].startswith("Slower") and next(x for x in c["rows"] if x["key"] == "tps")["change_pct"] == -28.2
    sy = bench.read(D.SYSBENCH)
    assert (sy["tool"], sy["tps"], sy["lat_p95"]) == ("sysbench", 1668.41, 15.27)
    assert bench.compare(a, a)["verdict"] == "No change bigger than the noise."


def test_hire_chat_wiring_store_and_guards(dbc):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert dbc.summary(T)["hired"] is False and "Hire me from AI Employees" in dbc.greeting(T)
    with pytest.raises(PermissionError):
        dbc.do(T, "add", {"kind": "plan", "text": D.PG_TEXT})
    _hire()
    d = dbc.summary(T)
    assert d["hired"] and "never connects to your database" in d["foot"] and {n["go"] for n in d["desk"]["needs"]} >= {"plans", "settings"}
    chat = dbc.current(T)
    assert dbc.is_dbengine(chat["id"]) and dbc.owns(T, chat["id"]) and "<database_desk>" in dbc.block(T)
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_dbc.is_dbengine(conversation_id)" in src and "adm.admit_families(_dbc.FAMILIES)" in src
    for f_ in ("callconv.py", "convs.py"):
        assert '"dbengine"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/database")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "dbdesk.js" in r.text
    html = (root / "server/app/static/console/dbdesk.html").read_text()
    for x in ("chatkit.js", "dbdesk.css", "dbdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/database')" in (root / "server/app/static/console/v2.js").read_text()
    assert "dbengine_dev: 'dbdesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["dbengine_dev"]["live"] is True
    from app.agent.tools import FAMILY_OF, HANDLERS
    assert FAMILY_OF["db_desk"] in dbc.FAMILIES and "db_desk" in HANDLERS
    p = dbc.do(T, "add", {"kind": "plan", "text": D.PG_TEXT})
    assert p["number"] == "P-0001" and p["brief"]["bad"] and any(n["go"] == "plans/" + p["id"] for n in dbc.summary(T)["desk"]["needs"])
    q = dbc.do(T, "add", {"kind": "query", "text": D.QUERY})
    assert q["number"] == "Q-0001" and q["brief"]["suggest"] == 1
    with pytest.raises(dbc.DbDeskError, match="needs your schema"):
        dbc.do(T, "add", {"kind": "lab", "text": D.QUERY, "indexes": q["result"]["suggest"][0]["sql"]})
    s = dbc.do(T, "add", {"kind": "schema", "text": D.SCHEMA})
    assert s["brief"]["errors"] == 1
    lb = dbc.do(T, "add", {"kind": "lab", "text": D.QUERY, "indexes": q["result"]["suggest"][0]["sql"], "rows": 10000})
    assert lb["result"]["schema_from"] == "your latest schema" and lb["status"] == "fixed" and lb["brief"]["used"]
    assert dbc.summary(T)["desk"]["proved"] == 1
    b1 = dbc.do(T, "add", {"kind": "bench", "text": D.PGBENCH})
    b2 = dbc.do(T, "add", {"kind": "bench", "text": D.PGBENCH_SLOW, "baseline": b1["id"]})
    assert b2["brief"]["worse"] and b2["result"]["baseline"]["number"] == "B-0001"
    assert any("slower than its baseline" in n["say"] for n in dbc.summary(T)["desk"]["needs"])
    st = dbc.do(T, "settings", {"engine": "mysql", "version": "8.4", "big_rows": "5000"})
    assert st["engine"] == "mysql" and st["big_rows"] == 5000
    dbc.forget(T)
    assert "mysql 8.4" in dbc.block(T)
    assert dbc.do(T, "check", {"text": "select * from t"})["counts"]["warn"] == 1
    # guards
    with pytest.raises(PermissionError):
        dbc.do(T, "settings", {"version": "my password is hunter2"})
    assert dbc.do(T, "add", {"kind": "query", "text": "SELECT 'password: hunter2' FROM t"})["kind"] == "query"     # a query is data
    with pytest.raises(dbc.DbDeskError):
        dbc.do(T, "settings", {"engine": "dbase"})
    with pytest.raises(dbc.DbDeskError):
        dbc.do(T, "settings", {"big_rows": "5"})
    with pytest.raises(dbc.DbDeskError):
        dbc.do(T, "add", {"kind": "plan", "text": "not a plan"})
    with pytest.raises(dbc.DbDeskError):
        dbc.do(T, "add", {"kind": "bench", "text": D.PGBENCH, "baseline": p["id"]})
    with pytest.raises(dbc.DbDeskError):
        dbc.do(T, "nope", {})
    from app.employee import hire as H
    H.pause(T, "dbengine_dev")
    assert dbc.do(T, "get", {"id": p["id"]})["id"] == p["id"]
    with pytest.raises(PermissionError):
        dbc.do(T, "add", {"kind": "plan", "text": D.PG_TEXT})


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def db_server(dbc, monkeypatch):
    import threading
    import time as _t
    sync_api = pytest.importorskip("playwright.sync_api")
    if not os.environ.get("HOOLA_CHROMIUM"):
        pytest.skip("set HOOLA_CHROMIUM for the browser walk")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    _hire()
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        _t.sleep(0.05)
    assert srv.started
    try:
        pw = sync_api.sync_playwright().start()
        browser = pw.chromium.launch(executable_path=os.environ["HOOLA_CHROMIUM"])
        yield f"http://127.0.0.1:{port}", browser, KEY
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_desk_in_a_real_browser(dbc, db_server):
    base, browser, key = db_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    def go(pg, route, sel):
        pg.evaluate(f"location.hash = '{route}'")
        pg.wait_for_selector(sel, timeout=30000)

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errs.append("console: " + m.text))
    pg.goto(base + "/console/database")
    pg.wait_for_selector(".dbk-starts", timeout=20000)
    # a plan
    go(pg, "#/plans", "form[data-form=add]")
    pg.fill("form[data-form=add] [name=text]", D.PG_TEXT)
    pg.click("form[data-form=add] [type=submit]")
    pg.wait_for_selector(".dbk-tree", timeout=30000)
    assert "1,000,000 rows to keep 4,980" in pg.inner_text("#dbPage") and pg.locator(".dbk-node").count() == 5
    snap(pg, "db-plan-1440")
    # the schema, then a query and its index proved in the lab
    go(pg, "#/schema", "form[data-form=add]")
    pg.fill("form[data-form=add] [name=text]", D.SCHEMA)
    pg.click("form[data-form=add] [type=submit]")
    pg.wait_for_selector(".dbk-tables", timeout=30000)
    assert "audit_log has no primary key" in pg.inner_text("#dbPage")
    snap(pg, "db-schema-1440")
    go(pg, "#/queries", "form[data-form=add]")
    pg.fill("form[data-form=add] [name=text]", D.QUERY)
    pg.click("form[data-form=add] [type=submit]")
    pg.wait_for_selector("[data-tolab]", timeout=30000)
    snap(pg, "db-query-1440")
    pg.click("[data-tolab]")
    pg.wait_for_selector("form[data-form=lab]", timeout=20000)
    assert "customer_id, status, created_at" in pg.input_value("form[data-form=lab] [name=indexes]")
    pg.select_option("form[data-form=lab] [name=rows]", "10000")
    pg.click("form[data-form=lab] [type=submit]")
    pg.wait_for_selector(".dbk-two", timeout=60000)
    assert "With the index SQLite used it" in pg.inner_text(".dbk-sum") and pg.locator(".dbk-eqp code.seek").count() >= 2
    snap(pg, "db-lab-1440")
    # benchmarks with a baseline
    go(pg, "#/bench", "form[data-form=add]")
    pg.fill("form[data-form=add] [name=text]", D.PGBENCH)
    pg.click("form[data-form=add] [type=submit]")
    pg.wait_for_selector(".dbk-head", timeout=30000)
    go(pg, "#/bench", "form[data-form=add] [name=baseline]")
    pg.fill("form[data-form=add] [name=text]", D.PGBENCH_SLOW)
    pg.select_option("form[data-form=add] [name=baseline]", index=1)
    pg.click("form[data-form=add] [type=submit]")
    pg.wait_for_selector(".dbk-sum", timeout=30000)
    assert "Slower" in pg.inner_text(".dbk-sum")
    snap(pg, "db-bench-1440")
    go(pg, "#/settings", "form[data-form=settings]")
    pg.select_option("form[data-form=settings] [name=engine]", "mysql")
    pg.click("form[data-form=settings] [type=submit]")
    pg.wait_for_selector("#toast:has-text('Saved')", timeout=20000)
    assert "MySQL" in pg.inner_text("#dbSite")
    go(pg, "#/today", ".dbk-list")
    snap(pg, "db-today-1440")
    for route, sel in (("#/today", ".dbk-list"), ("#/plans", ".dbk-item"), ("#/queries", ".dbk-item"), ("#/schema", ".dbk-item"),
                       ("#/lab", ".dbk-item"), ("#/bench", ".dbk-item"), ("#/settings", "form[data-form=settings]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('#dbPage *')].filter(e => !e.closest('pre,textarea,table') && e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
    go(pg, "#/plans", ".dbk-item")
    pg.click(".dbk-item")
    pg.wait_for_selector(".dbk-tree", timeout=20000)
    w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
    assert w[0] <= w[1] + 1, w
    snap(pg, "db-plan-390")
    go(pg, "#/lab", ".dbk-item")
    pg.click(".dbk-item")
    pg.wait_for_selector(".dbk-two", timeout=20000)
    snap(pg, "db-lab-390")
    assert not errs, errs
