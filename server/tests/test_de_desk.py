"""DATA ENGINEER DESK: the Data Engineer's own section, built like the finance desks - its own chat (kind 'dataeng') with the desk
block and the data tool in view; pipelines read as graphs (the critical path pinned to networkx's longest path on random DAGs,
loops found, Airflow / arrow / list / dbt manifest forms); schemas compared with contracts (SQL, Avro, JSON Schema, YAML, lines;
breaking and safe changes); source and target reconciled (pinned to set arithmetic); run histories (medians pinned to the
statistics module, failing / slow / zero-row / stale); storage from s3 / gsutil / hdfs listings; the CI check really fails a pull
request that drops a column; walked in a browser."""
from __future__ import annotations

import json
import os
import random
import statistics
import subprocess
import sys
from datetime import datetime, timedelta

import pytest
import yaml
from fastapi.testclient import TestClient

T = "default"

DAG = """extract_orders >> clean_orders >> join >> load
extract_customers >> clean_customers >> join
[clean_orders, clean_customers] >> quality
extract_orders = 12m
clean_orders = 25m
extract_customers = 4m
clean_customers = 6m
join = 18m
load = 9m
quality = 3m
orphan_task
"""
OLD = """CREATE TABLE sales.orders (
  order_id BIGINT NOT NULL,
  customer_id INT NOT NULL,
  amount DECIMAL(12,2),
  status VARCHAR(20),
  created_at TIMESTAMP,
  note TEXT,
  PRIMARY KEY (order_id)
);"""
NEW = """CREATE TABLE sales.orders (
  order_id BIGINT NOT NULL,
  customer_id BIGINT NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  order_status VARCHAR(20),
  created_at TIMESTAMP WITH TIME ZONE,
  channel VARCHAR(10) NOT NULL,
  discount DOUBLE PRECISION,
  PRIMARY KEY (order_id)
);"""


def tables(seed=1, n=500):
    R = random.Random(seed)
    src = ["order_id,amount,status,city"] + [f"{i},{R.randint(1, 900)}.{R.randint(0, 99):02d},paid,Pune" for i in range(1, n + 1)]
    tgt = [src[0]] + [x for x in src[1:] if not x.startswith(("17,", "18,"))]
    tgt = [x.replace(",paid,", ",PAID,") if x.startswith(("25,", "26,", "27,")) else x for x in tgt] + ["9999,1.00,paid,Lima", "3," + src[3].split(",", 1)[1]]
    return "\n".join(src), "\n".join(tgt)


def history(seed=2, days=25):
    R = random.Random(seed)
    rows = ["job,start,end,status,rows"]
    t0 = datetime(2026, 11, 1, 2, 0)
    durs: dict[str, list[float]] = {"load_orders": [], "build_marts": []}
    for d in range(days):
        for j, base in (("load_orders", 20), ("build_marts", 45)):
            s = t0 + timedelta(days=d)
            dur = round(base + R.uniform(-3, 3) + (d * 1.6 if j == "build_marts" else 0), 2)
            st = "failed" if (j == "load_orders" and d in (5, 23, 24)) else "success"
            if st == "success":
                durs[j].append(dur)
            rows.append(f"{j},{s.isoformat()},{(s + timedelta(minutes=dur)).isoformat()},{st},{0 if (j == 'build_marts' and d == days - 1) else R.randint(9000, 11000)}")
    return "\n".join(rows), durs


def listing(seed=3, n=400):
    R = random.Random(seed)
    sizes = [R.randint(200_000, 4_000_000) for _ in range(n)]
    ls = "\n".join(f"2026-11-0{1 + i % 9} 02:00:00 {sizes[i]:>10} warehouse/orders/dt=2026-11-{1 + i % 20:02d}/part-{i:05d}.snappy.parquet" for i in range(n))
    ls += "\n2026-11-01 02:00:00 9000000000 warehouse/orders/dt=2026-11-01/big.parquet\n2026-11-01 02:00:00 0 warehouse/orders/_SUCCESS"
    return ls, sizes + [9_000_000_000]


@pytest.fixture
def dec(env):
    from app import dechat as C
    C._OF.clear()
    C._BLOCK.clear()
    return C


def _hire():
    from app.employee import hire
    hire.hire(T, "data_eng", trust="seekh")


# ---------------------------------------------------------------- the engine (pure code)
def test_pipelines():
    import networkx as nx
    from app.dedesk import dag as DG
    r = DG.analyse(DAG, window=60)
    assert r["critical"]["path"] == ["extract_orders", "clean_orders", "join", "load"] and r["critical"]["minutes"] == 64
    assert r["lone"] == ["orphan_task"] and r["depth"] == 4 and any(i["area"] == "Window" and i["sev"] == "bad" for i in r["issues"])
    assert r["critical"]["slack"]["clean_customers"] == 25 + 12 - 10
    R = random.Random(7)
    for _ in range(40):
        n = R.randint(3, 30)
        g = nx.gnp_random_graph(n, 0.2, seed=R.randint(0, 10 ** 6), directed=True)
        edges = [(a, b) for a, b in g.edges() if a < b]
        dur = {i: R.randint(1, 60) for i in range(n)}
        text = "\n".join(f"t{a} >> t{b}" for a, b in edges) + "\n" + "\n".join(f"t{i} = {dur[i]}m" for i in range(n))
        r = DG.analyse(text)
        h = nx.DiGraph()
        h.add_nodes_from(range(n))
        for a, b in edges:
            h.add_edge(a, b, w=dur[b])
        for v in list(h.nodes):   # a node's own minutes on the edges into it, plus a source node carrying the start node's minutes
            h.add_edge("S", v, w=dur[v])
        brute = nx.dag_longest_path_length(h, weight="w")
        assert abs(r["critical"]["minutes"] - brute) < 1e-9, (text, r["critical"], brute)
        assert sum(dur[int(t[1:])] for t in r["critical"]["path"]) == brute
    loop = DG.analyse("a -> b\nb -> c\nc -> a\nd >> a")
    assert loop["cycle"][0] == loop["cycle"][-1] and set(loop["cycle"]) == {"a", "b", "c"} and loop["issues"][0]["sev"] == "bad"
    lst = DG.analyse("orders: stg_orders, stg_customers\nstg_orders: raw_orders\nrevenue: orders\nrevenue: 5m")
    assert lst["tasks"] == 5 and ["stg_orders", "orders"] in lst["edges"] and lst["durations"] == {"revenue": 5}
    man = {"nodes": {"model.shop.orders": {"depends_on": {"nodes": ["model.shop.stg_orders", "source.shop.raw.orders"]}},
                     "model.shop.stg_orders": {"depends_on": {"nodes": ["source.shop.raw.orders"]}},
                     "test.shop.not_null_orders_id": {"resource_type": "test", "depends_on": {"nodes": ["model.shop.orders"]}}}}
    m = DG.analyse(json.dumps(man))
    assert m["tasks"] == 3 and ["raw.orders", "stg_orders"] in m["edges"] and m["redundant"] == [["raw.orders", "orders"]]
    red = DG.analyse("a >> b >> c\na >> c")
    assert red["redundant"] == [["a", "c"]] and "flowchart LR" in red["mermaid"]
    for bad in ("", "a >> b >> a b c d e\n!!\n??\n..\n,,", "a -> a"):
        with pytest.raises(DG.DagError):
            DG.analyse(bad)


def test_contracts_and_recon():
    from app.dedesk import contract as CT, recon as RC
    c = CT.compare(OLD, NEW)
    by = {(x["column"], x["kind"]): x for x in c["changes"]}
    assert by[("customer_id", "type")]["sev"] == "safe" and by[("amount", "type")]["sev"] == "breaking" and by[("amount", "nullability")]["sev"] == "breaking"
    assert by[("status", "removed")]["say"].endswith("order_status?") and by[("channel", "added")]["sev"] == "breaking" and by[("discount", "added")]["sev"] == "safe"
    assert by[("created_at", "type")]["sev"] == "breaking" and c["renames"] == [["status", "order_status"]] and c["breaking"] == 6
    same = CT.compare(OLD, OLD)
    assert same["changes"] == [] and same["breaking"] == 0
    avro = '{"type":"record","name":"o","fields":[{"name":"id","type":"long"},{"name":"price","type":["null","float"]}]}'
    a = CT.compare(avro, '{"type":"record","name":"o","fields":[{"name":"id","type":"int"},{"name":"price","type":["null","double"]}]}')
    assert {(x["column"], x["sev"]) for x in a["changes"]} == {("id", "breaking"), ("price", "safe")}
    assert any(i["area"] == "Money" for i in CT.compare(avro)["issues"])
    js = CT.compare('{"properties":{"id":{"type":"integer"},"email":{"type":"string","maxLength":50}},"required":["id"]}',
                    '{"properties":{"id":{"type":"integer"},"email":{"type":"string","maxLength":40}},"required":["id","email"]}')
    assert {x["kind"] for x in js["changes"]} == {"type", "nullability"} and js["breaking"] == 2
    y = CT.compare("- name: id\n  data_type: bigint\n  tests:\n    - not_null\n- name: email\n  data_type: varchar(100)")
    assert y["columns"][0]["nullable"] is False and y["columns"][1]["family"] == "string"
    lines = CT.compare("id bigint not null\nname varchar(20)", "id bigint not null\nname varchar(30)\nage int")
    assert lines["breaking"] == 0 and lines["safe"] == 2
    for bad in ("", "{}", "CREATE TABLE t (a int, a int)"):
        with pytest.raises(CT.ContractError):
            CT.compare(bad)
    src, tgt = tables()
    r = RC.reconcile(src, tgt, "order_id")
    S = {x.split(",")[0]: x for x in src.split("\n")[1:]}
    Tg = {}
    for x in tgt.split("\n")[1:]:
        Tg.setdefault(x.split(",")[0], x)
    assert r["missing"] == len(set(S) - set(Tg)) == 2 and r["extra"] == len(set(Tg) - set(S)) == 1
    assert r["changed"] == sum(1 for k in set(S) & set(Tg) if S[k] != Tg[k]) == 3 and r["dup_target"] == 1 and r["diff_cols"] == {"status": 3}
    tot = next(t for t in r["totals"] if t["column"] == "amount")
    assert abs(tot["source"] - sum(float(x.split(",")[1]) for x in S.values())) < 1e-6
    ok = RC.reconcile(src, src, "order_id")
    assert ok["verdict"].startswith("Reconciled") and not ok["issues"]
    tol = RC.reconcile("id,v\n1,10.00\n2,5", "id,v\n1,10.004\n2,5", "id", tol=0.01)
    assert tol["changed"] == 0 and RC.reconcile("id,v\n1,10.00\n2,5", "id,v\n1,10.004\n2,5", "id")["changed"] == 1
    with pytest.raises(RC.ReconError):
        RC.reconcile(src, tgt, "nope")


def test_runs_storage_ci(tmp_path):
    from app.dedesk import ci as CI, runs as RU, storage as SG
    h, durs = history()
    r = RU.analyse(h, sla=60, freshness_h=24)
    J = {j["job"]: j for j in r["jobs"]}
    assert J["load_orders"]["failing_now"] == 2 and J["load_orders"]["failed"] == 3 and r["runs"] == 50
    for k, v in durs.items():
        assert abs(J[k]["median"] - statistics.median(v)) < 1e-6
    areas = {(i["area"], i["fn"]) for i in r["issues"]}
    assert {("Failing", "load_orders"), ("Stale", "load_orders"), ("Rows", "build_marts"), ("Slowing", "build_marts"), ("Time limit", "build_marts")} <= areas
    assert abs(J["load_orders"]["age_h"] - (24 * 3 - (J["load_orders"]["median"] - durs["load_orders"][-1]) / 60 + 0)) < 30
    d = RU.analyse("task,duration_s,state\na,60,success\na,120,success\na,90,failed")
    assert d["jobs"][0]["median"] == 1.5 and d["jobs"][0]["failing_now"] == 1
    with pytest.raises(RU.RunsError):
        RU.analyse("job,start\na,2026-01-01")
    ls, sizes = listing()
    s = SG.analyse(ls, price_tb=6.25)
    assert s["files"] == 401 and s["total"] == sum(sizes) and s["median"] == statistics.median(sizes) and s["partitions"]["count"] == 20
    assert s["after"] == -(-sum(sizes) // (256 * 1024 ** 2)) and abs(s["scan_cost"] - sum(sizes) / 1024 ** 4 * 6.25) < 1e-12
    assert {"Small files", "Skew", "Big files"} <= {i["area"] for i in s["issues"]}
    assert SG.analyse("gs://b/t/a.csv,1048576\ngs://b/t/b.csv,2MB")["total"] == 3 * 1024 ** 2
    assert SG.analyse("-rw-r--r--   3 hdfs hdfs   134217728 2026-11-01 10:00 /data/t/dt=1/p0.orc\ndrwxr-xr-x   - hdfs hdfs 0 2026-11-01 10:00 /data/t/dt=2")["files"] == 1
    assert SG.analyse("     12345  2026-11-01T10:00:00Z  gs://b/t/x.parquet\n    999  2026-11-01T10:00:00Z  gs://b/t/y.parquet\nTOTAL: 2 objects")["total"] == 13344
    with pytest.raises(SG.StorageError):
        SG.analyse("hello")
    w = CI.workflow("dbt build", schema="target/schema.json", contract="contracts/orders.json", setup_cmd="pip install dbt-duckdb")
    y = yaml.safe_load(w["yaml"])
    assert y["permissions"] == {"contents": "read"} and [x.get("name") for x in y["jobs"]["data"]["steps"]][-2:] == ["Data tests", "Compare with the contract"]
    code = w["compare"].replace("\n          ", "\n").strip()
    (tmp_path / "con.json").write_text(json.dumps({"order_id": "bigint", "amount": "decimal(12,2)", "status": "varchar"}))
    run = lambda: subprocess.run([sys.executable, "-I", "-c", code, str(tmp_path / "new.json"), str(tmp_path / "con.json")], capture_output=True, text=True,   # noqa: E731
                                 env={"PATH": os.environ.get("PATH", ""), "GITHUB_STEP_SUMMARY": str(tmp_path / "s.md")})
    (tmp_path / "new.json").write_text(json.dumps([{"name": "order_id", "type": "bigint"}, {"name": "amount", "type": "decimal(12, 2)"}, {"name": "status", "type": "varchar"}, {"name": "x", "type": "int"}]))
    assert run().returncode == 0
    (tmp_path / "new.json").write_text(json.dumps({"columns": {"order_id": "bigint", "amount": "decimal(10,2)"}}))
    out = run()
    assert out.returncode == 1 and "status is in the contract" in out.stdout and "amount: decimal(12,2) -> decimal(10,2)" in out.stdout
    assert "| status | varchar | missing | FAIL |" in (tmp_path / "s.md").read_text()
    assert "Compare" not in CI.workflow("pytest tests/data")["yaml"]
    for bad in (dict(test_cmd=""), dict(test_cmd="x ${{ secrets.K }}"), dict(test_cmd="x", schema="a.json"), dict(test_cmd="x", schema="../a.json", contract="b.json")):
        with pytest.raises(CI.CiError):
            CI.workflow(**bad)


def test_hire_chat_wiring_store_and_guards(dec):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert dec.summary(T)["hired"] is False and "Hire me from AI Employees" in dec.greeting(T)
    with pytest.raises(PermissionError):
        dec.do(T, "add", {"kind": "dag", "text": DAG})
    _hire()
    d = dec.summary(T)
    assert d["hired"] and d["foot"] == dec.FOOT and {n["go"] for n in d["desk"]["needs"]} >= {"pipelines", "settings"}
    chat = dec.current(T)
    assert dec.is_dataeng(chat["id"]) and dec.owns(T, chat["id"]) and "<data_desk>" in dec.block(T)
    s_ = (root / "server/app/agent/santosh.py").read_text()
    assert "_dec.is_dataeng(conversation_id)" in s_ and "adm.admit_families(_dec.FAMILIES)" in s_
    for f_ in ("callconv.py", "convs.py"):
        assert '"dataeng"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/data")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "dedesk.js" in r.text
    html = (root / "server/app/static/console/dedesk.html").read_text()
    for x in ("chatkit.js", "dedesk.css", "dedesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/data')" in (root / "server/app/static/console/v2.js").read_text()
    assert "data_eng: 'dedesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["data_eng"]["live"] is True
    from app.agent.tools import FAMILY_OF, HANDLERS
    from app.agent import admit
    assert FAMILY_OF["data_eng_desk"] in dec.FAMILIES and "data_eng_desk" in HANDLERS and "dataeng" in admit.EXTRA_KEYS
    p1 = dec.do(T, "add", {"kind": "dag", "text": DAG, "inputs": {"window": 60}})
    assert p1["number"] == "P-0001" and p1["brief"]["crit"] == 64 and p1["brief"]["bad"] and p1["title"].startswith("Pipeline: ")
    json.dumps(p1)
    s1 = dec.do(T, "add", {"kind": "schema", "text": OLD, "inputs": {"new": NEW}})
    assert s1["number"] == "S-0001" and s1["brief"]["breaking"] == 6 and any(n["go"] == "contracts/" + s1["id"] for n in dec.summary(T)["desk"]["needs"])
    src, tgt = tables()
    r1 = dec.do(T, "add", {"kind": "recon", "text": src, "inputs": {"target": tgt, "key": "order_id"}})
    assert r1["number"] == "R-0001" and r1["brief"]["missing"] == 2
    h, _ = history()
    j1 = dec.do(T, "add", {"kind": "runs", "text": h, "inputs": {"sla": 60}})
    assert j1["number"] == "J-0001" and j1["brief"]["failing"] == 1
    ls, _ = listing()
    f1 = dec.do(T, "add", {"kind": "storage", "text": ls})
    assert f1["number"] == "F-0001" and f1["brief"]["files"] == 401
    assert dec.do(T, "ci", {})["missing"] is True
    st = dec.do(T, "settings", {"key_cols": "order_id", "window_min": 90, "test_cmd": "dbt build", "schema_path": "target/schema.json", "contract_path": "contracts/orders.json"})
    assert st["key_cols"] == "order_id" and st["window_min"] == 90
    w = dec.do(T, "ci", {})
    assert w["file"] == ".github/workflows/data-checks.yml" and yaml.safe_load(w["yaml"])
    dec.forget(T)
    assert "key order_id" in dec.block(T)
    r2 = dec.do(T, "add", {"kind": "recon", "text": src, "inputs": {"target": tgt}})
    assert r2["result"]["key"] == ["order_id"]
    mk = dec.do(T, "mark", {"id": s1["id"], "status": "fixed"})
    assert mk["status"] == "fixed" and not any(n["go"] == "contracts/" + s1["id"] for n in dec.summary(T)["desk"]["needs"])
    import asyncio
    from app.agent import dataeng_tools as DT
    from app.agent.tools import Ctx
    out = asyncio.run(DT.data_eng_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="dag", text=DAG))
    assert out["number"] == "P-0002" and out["critical"]["minutes"] == 64
    out = asyncio.run(DT.data_eng_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="ci"))
    assert out["file"] == ".github/workflows/data-checks.yml"
    with pytest.raises(PermissionError):
        dec.do(T, "settings", {"test_cmd": "my password is hunter2"})
    assert dec.do(T, "add", {"kind": "dag", "text": DAG + "\n# password = hunter2"})["kind"] == "dag"
    for bad in ({"small_mb": 500}, {"target_mb": 0}, {"schema_path": "../x"}, {"python": "2"}, {"tolerance": -1}):
        with pytest.raises((dec.DeDeskError, PermissionError)):
            dec.do(T, "settings", bad)
    with pytest.raises(dec.DeDeskError):
        dec.do(T, "add", {"kind": "storage", "text": ""})
    with pytest.raises(dec.DeDeskError):
        dec.do(T, "nope", {})
    from app.employee import hire as H
    H.pause(T, "data_eng")
    assert dec.do(T, "get", {"id": p1["id"]})["id"] == p1["id"] and dec.do(T, "ci", {})["yaml"]
    with pytest.raises(PermissionError):
        dec.do(T, "add", {"kind": "dag", "text": DAG})


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def de_server(dec, monkeypatch):
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


def test_desk_in_a_real_browser(dec, de_server):
    base, browser, key = de_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

    def snap(pg, name):
        if shots:
            tag = pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)
            tag.evaluate("el => el.remove()")

    def go(pg, route, sel):
        pg.evaluate(f"location.hash = '{route}'")
        pg.wait_for_selector(sel, timeout=30000)

    def put(pg, form, name, text):
        pg.eval_on_selector(f"form[data-form={form}] [name={name}]", "(el, v) => { el.value = v; el.dispatchEvent(new Event('input', {bubbles: true})); }", text)

    def submit(pg, form, text, sel):
        put(pg, form, "text", text)
        pg.click(f"form[data-form={form}] [type=submit]")
        pg.wait_for_selector(sel, timeout=60000)

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errs.append("console: " + m.text))
    pg.goto(base + "/console/data")
    pg.wait_for_selector(".dek-path", timeout=20000)
    snap(pg, "de-today-empty-1440")
    go(pg, "#/pipelines", "form[data-form=dag]")
    put(pg, "dag", "window", "60")
    submit(pg, "dag", DAG, ".dek-dag svg")
    assert "64 min" in pg.inner_text(".cs-hero") and pg.locator(".dek-dag .nd").count() == 8 and pg.locator(".dek-gantt .hot").count() == 4
    snap(pg, "de-pipelines-1440")
    go(pg, "#/contracts", "form[data-form=contracts], form[data-form=schema]")
    put(pg, "schema", "new", NEW)
    submit(pg, "schema", OLD, "table.dek-t")
    assert "order_status" in pg.inner_text("#dePage") and "Fewer digits" in pg.inner_text("#dePage")
    snap(pg, "de-contracts-1440")
    src, tgt = tables()
    go(pg, "#/reconcile", "form[data-form=recon]")
    put(pg, "recon", "target", tgt)
    put(pg, "recon", "key", "order_id")
    submit(pg, "recon", src, ".dek-keys")
    assert "9999" in pg.inner_text("#dePage") and "PAID" in pg.inner_text("#dePage")
    snap(pg, "de-reconcile-1440")
    h, _ = history()
    go(pg, "#/runs", "form[data-form=runs]")
    put(pg, "runs", "sla", "60")
    put(pg, "runs", "freshness", "24")
    submit(pg, "runs", h, ".dek-spark")
    assert "failing 2x" in pg.inner_text("#dePage")
    snap(pg, "de-runs-1440")
    ls, _ = listing()
    go(pg, "#/storage", "form[data-form=storage]")
    put(pg, "storage", "price_tb", "6.25")
    submit(pg, "storage", ls, "text=After compaction")
    assert "dt=2026-11-01" in pg.inner_text("#dePage")
    snap(pg, "de-storage-1440")
    go(pg, "#/ci", "text=Set the data test command")
    go(pg, "#/settings", "form[data-form=settings]")
    pg.fill("form[data-form=settings] [name=test_cmd]", "dbt build")
    pg.fill("form[data-form=settings] [name=key_cols]", "order_id")
    pg.click("form[data-form=settings] [type=submit]")
    pg.wait_for_selector("#toast:has-text('Saved')", timeout=20000)
    go(pg, "#/ci", "text=data-checks.yml")
    snap(pg, "de-ci-1440")
    go(pg, "#/today", ".dek-list")
    assert "64 min" in pg.inner_text(".cs-hero")
    snap(pg, "de-today-1440")
    for route, sel in (("#/today", ".dek-list"), ("#/pipelines", ".dek-item"), ("#/contracts", ".dek-item"), ("#/reconcile", ".dek-item"), ("#/runs", ".dek-item"),
                       ("#/storage", ".dek-item"), ("#/ci", "text=data-checks.yml"), ("#/settings", "form[data-form=settings]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('body *')].filter(e => !e.closest('pre,textarea,table,svg,.dek-dag') && e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
    for route in ("#/pipelines", "#/contracts", "#/reconcile", "#/runs", "#/storage"):
        go(pg, route, ".dek-item")
        pg.locator(".dek-item").first.click()
        pg.wait_for_selector(".dek-head", timeout=20000)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 8).map(e => e.tagName + '.' + e.className + ':' + Math.round(e.getBoundingClientRect().right) + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
        snap(pg, "de-" + route[2:] + "-390")
    assert not errs, errs
