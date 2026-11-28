"""ML DESK: the Machine Learning Engineer's own section, built like the finance desks - its own chat (kind 'mleng') with the desk block
and the ml tool in view; training runs read from logs (CSV, Keras, Hugging Face lines: best epoch, overfitting, early stopping);
training tables profiled (ID columns, constants, duplicates, a leaking column); drift between two samples (PSI, and the
Kolmogorov-Smirnov statistic pinned to scipy); regression and forecast errors pinned to numpy; GPU sizing by hand (KV cache,
bandwidth, LoRA compute); the CI check really fails a pull request whose score drops; walked in a browser."""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys

import pytest
import yaml
from fastapi.testclient import TestClient

T = "default"

import random
def run_csv(n=30, turn=12):
    rows = ["epoch,loss,val_loss,val_accuracy,lr"]
    for e in range(1, n + 1):
        tr = 2.0 * math.exp(-e / 8) + 0.05
        va = 2.1 * math.exp(-e / 8) + 0.25 + (0.02 * (e - turn) if e > turn else 0)
        rows.append(f"{e},{tr:.5f},{va:.5f},{min(.99, .5 + e * .015):.4f},{0.001 if e < 20 else 0.0001}")
    return "\n".join(rows)
def data_csv(n=2000, seed=1):
    R = random.Random(seed); rows = ["customer_id,age,income,city,plan,refund_issued,const,churned,split"]
    for i in range(n):
        ch = 1 if R.random() < .2 else 0
        inc = "" if R.random() < .3 else str(round(R.gauss(50000, 15000)))
        rows.append(f"{1000 + i},{R.randint(18, 80)},{inc},{R.choice(['Pune','Lagos','Berlin','Lima'])},{R.choice('abc')},{ch},x,{ch},{'test' if i % 5 == 0 else 'train'}")
    rows += rows[1:4]
    return "\n".join(rows)
def drift_pair(seed=2):
    R = random.Random(seed); a = ["age,income,city"]; b = ["age,income,city"]
    ra, rb = [], []
    for _ in range(1500):
        x = R.gauss(40, 10); ra.append(x); a.append(f"{x:.2f},{R.gauss(50000, 9000):.0f},{R.choice(['Pune','Lagos','Berlin'])}")
    for _ in range(1200):
        x = R.gauss(46, 10); rb.append(x); b.append(f"{x:.2f},{R.gauss(50000, 9000):.0f},{R.choice(['Pune','Lagos','Berlin','Accra'])}")
    return "\n".join(a), "\n".join(b), ra, rb
def reg_csv(seed=4, days=60):
    R = random.Random(seed); rows = ["date,store,actual,predicted,p10,p90"]; Y = []; P = []
    for d in range(days):
        for s in "AB":
            base = (100 if s == "A" else 300) + 20 * math.sin(d / 7 * 2 * math.pi)
            y = base + R.gauss(0, 8); p = base + R.gauss(0, 6) + (5 if s == "B" else 0)
            rows.append(f"2026-03-{(d % 28) + 1:02d},{s},{y:.2f},{p:.2f},{p - 12:.2f},{p + 12:.2f}"); Y.append(y); P.append(p)
    return "\n".join(rows), Y, P
SZ = "model 8B bf16 layers=32 kv_heads=8 head_dim=128\nserve context=8192 batch=16\ngpu h100 x1\ntrain lora rank=16 hidden=4096 on 500M tokens"


@pytest.fixture
def mlc(env):
    from app import mlchat as C
    C._OF.clear()
    C._BLOCK.clear()
    return C


def _hire():
    from app.employee import hire
    hire.hire(T, "ml_eng", trust="seekh")


# ---------------------------------------------------------------- the engine (pure code)
def test_training_runs():
    from app.mldesk import run as RN
    r = RN.analyse(run_csv())
    assert r["points"] == 30 and r["best"]["at"] == 21 and r["since_best"] == 9 and r["early_stop"] == 26
    assert r["train"] == "loss" and r["val"] == "val_loss" and r["lr"] == "lr" and "val_accuracy" in r["metrics"]
    assert any("rose" in i["text"] for i in r["issues"]) and any("early stopping" in i["text"] for i in r["issues"])
    keras = "\n".join(f"Epoch {e}/5\n100/100 - 2s - loss: {1 / e:.4f} - val_loss: {1.1 / e + (0.3 if e == 5 else 0):.4f}" for e in range(1, 6))
    k = RN.analyse(keras)
    assert k["points"] == 5 and k["best"]["at"] == 4
    hf = "\n".join("{'loss': %.3f, 'epoch': %d.0}\n{'eval_loss': %.3f, 'epoch': %d.0}" % (2 / e, e, 2.2 / e, e) for e in range(1, 4))
    assert RN.analyse(hf)["points"] >= 3
    boom = RN.analyse("epoch,loss\n1,0.9\n2,0.8\n3,5.2\n4,nan")
    assert any(i["sev"] == "bad" for i in boom["issues"])
    for bad in ("", "hello there\nno numbers here"):
        with pytest.raises(RN.RunError):
            RN.analyse(bad)


def test_data_profile_and_drift():
    import numpy as np
    from scipy import stats
    from app.mldesk import data as DA, drift as DR, table as TB
    d = DA.profile(data_csv(), "churned", "split")
    by = {c["name"]: c for c in d["cols"]}
    assert d["rows"] == 2003 and d["duplicates"] == 3 and by["customer_id"]["id"] and by["churned"]["target"]
    texts = {i["fn"]: (i["sev"], i["text"]) for i in d["issues"] if i.get("fn")}
    assert texts["refund_issued"][0] == "bad" and texts["const"][0] == "warn" and texts["customer_id"][0] == "warn"
    inc = [float(x.split(",")[2]) for x in data_csv().split("\n")[1:] if x.split(",")[2]]
    assert abs(by["income"]["mean"] - np.mean(inc)) < 1e-6 and abs(by["income"]["missing"] - (2003 - len(inc)) / 2003) < 1e-12
    assert d["target"]["type"] == "classes" and set(d["split"]["counts"]) == {"train", "test"}
    a, b, ra, rb = drift_pair()
    f = DR.compare(a, b)
    col = {c["name"]: c for c in f["columns"]}
    ref = stats.ks_2samp(ra, rb)
    assert abs(col["age"]["ks"] - ref.statistic) < 1e-12 and col["age"]["state"] == "bad" and col["income"]["state"] == "ok"
    en = math.sqrt(len(ra) * len(rb) / (len(ra) + len(rb)))
    assert abs(col["age"]["p"] - stats.kstwobign.sf(en * ref.statistic)) < 1e-12
    assert col["city"]["state"] == "bad" and any(x.get("new") and x["value"] == "Accra" for x in col["city"]["bins"])
    p, bins = TB.psi(ra, ra[:700])
    assert p < 0.1 and abs(sum(x["ref"] for x in bins) - 1) < 1e-9
    with pytest.raises(TB.TableError):
        DR.compare(a, "")


def test_regression_and_sizing(tmp_path):
    import numpy as np
    from app.mldesk import ci as CI, regress as RG, sizing as SZM
    t, Y, P = reg_csv()
    g = RG.evaluate(t, group="store", season=7)
    rows = [x.split(",") for x in t.split("\n")[1:]]
    y, p = np.array([float(r[2]) for r in rows]), np.array([float(r[3]) for r in rows])
    e = p - y
    assert abs(g["mae"] - np.abs(e).mean()) < 1e-9 and abs(g["rmse"] - math.sqrt((e ** 2).mean())) < 1e-9
    assert abs(g["r2"] - (1 - (e ** 2).sum() / ((y - y.mean()) ** 2).sum())) < 1e-9 and abs(g["bias"] - e.mean()) < 1e-9
    assert abs(g["wape"] - np.abs(e).sum() / np.abs(y).sum() * 100) < 1e-9 and g["n"] == 120
    assert {x["group"] for x in g["groups"]} == {"A", "B"} and g["interval"]["n"] == 120 and g["mase"] < 1
    s = SZM.analyse(SZ)
    kv_tok = 2 * 32 * 8 * 128 * 2
    assert s["weights_gb"] == 16.0 and abs(s["serve"]["kv_gb"] - kv_tok * 8192 * 16 / 1e9) < 1e-9 and s["serve"]["fits"]
    assert abs(s["kv_per_token_mb"] - kv_tok / 1e6) < 1e-9 and abs(s["decode_tok_s"] - s["bw"] / 16) < 1e-9
    assert s["train"]["mode"] == "lora" and s["train"]["flops"] == 4 * 8e9 * 5e8
    big = SZM.analyse("model 70B fp16 layers=80 kv_heads=8 head_dim=128\nserve context=32768 batch=8\ngpu a100-80gb x1")
    assert big["serve"]["fits"] is False and big["serve"]["gpus_needed"] >= 2
    with pytest.raises(SZM.SizingError):
        SZM.analyse("make it fast")
    w = CI.workflow("python eval.py --out eval/metrics.json", max_drop=1, max_rise=10)
    assert yaml.safe_load(w["yaml"])["permissions"] == {"contents": "read"}
    code = w["compare"].replace("\n          ", "\n").strip()
    (tmp_path / "base.json").write_text(json.dumps({"accuracy": 0.91, "rmse": 10.0}))
    run = lambda: subprocess.run([sys.executable, "-I", "-c", code, str(tmp_path / "head.json"), str(tmp_path / "base.json")], capture_output=True, text=True,   # noqa: E731
                                 env={"PATH": os.environ.get("PATH", ""), "GITHUB_STEP_SUMMARY": str(tmp_path / "s.md")})
    (tmp_path / "head.json").write_text(json.dumps({"accuracy": 0.905, "rmse": 10.5}))
    assert run().returncode == 0
    (tmp_path / "head.json").write_text(json.dumps({"accuracy": 0.88, "rmse": 12.0}))
    out = run()
    assert out.returncode == 1 and "accuracy: 0.91 -> 0.88" in out.stdout and "rmse: 10 -> 12" in out.stdout
    for bad in (dict(eval_cmd=""), dict(eval_cmd="x ${{ secrets.K }}"), dict(eval_cmd="x", metrics="../m.json")):
        with pytest.raises(CI.CiError):
            CI.workflow(**bad)


def test_hire_chat_wiring_store_and_guards(mlc):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert mlc.summary(T)["hired"] is False and "Hire me from AI Employees" in mlc.greeting(T)
    with pytest.raises(PermissionError):
        mlc.do(T, "add", {"kind": "sizing", "text": SZ})
    _hire()
    d = mlc.summary(T)
    assert d["hired"] and d["foot"] == mlc.FOOT and {n["go"] for n in d["desk"]["needs"]} >= {"training", "settings"}
    chat = mlc.current(T)
    assert mlc.is_mleng(chat["id"]) and mlc.owns(T, chat["id"]) and "<ml_desk>" in mlc.block(T)
    s_ = (root / "server/app/agent/santosh.py").read_text()
    assert "is_mleng(conversation_id)" in s_ and "_mlc.FAMILIES" in s_
    for f_ in ("callconv.py", "convs.py"):
        assert '"mleng"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/ml")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "mldesk.js" in r.text
    html = (root / "server/app/static/console/mldesk.html").read_text()
    for x in ("chatkit.js", "mldesk.css", "mldesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/ml')" in (root / "server/app/static/console/v2.js").read_text()
    assert "ml_eng: 'mldesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["ml_eng"]["live"] is True
    from app.agent.tools import FAMILY_OF, HANDLERS
    assert FAMILY_OF["ml_desk"] in mlc.FAMILIES and "ml_desk" in HANDLERS
    r1 = mlc.do(T, "add", {"kind": "run", "text": run_csv()})
    assert r1["number"] == "R-0001" and r1["brief"]["best_at"] == 21 and r1["title"].startswith("Training: ")
    json.dumps(r1)
    d1 = mlc.do(T, "add", {"kind": "data", "text": data_csv(), "inputs": {"target": "churned", "split": "split"}})
    assert d1["number"] == "D-0001" and d1["brief"]["bad"] and any(n["go"] == "data/" + d1["id"] for n in mlc.summary(T)["desk"]["needs"])
    a, b, _, _ = drift_pair()
    f1 = mlc.do(T, "add", {"kind": "drift", "text": a, "inputs": {"current": b}})
    assert f1["number"] == "F-0001" and f1["brief"]["moved"] == 2
    t, _, _ = reg_csv()
    e1 = mlc.do(T, "add", {"kind": "regress", "text": t, "inputs": {"group": "store", "season": 7}})
    assert e1["number"] == "E-0001" and e1["brief"]["n"] == 120
    z1 = mlc.do(T, "add", {"kind": "sizing", "text": SZ})
    assert z1["number"] == "Z-0001" and z1["brief"]["fits"] is True
    assert mlc.do(T, "ci", {})["missing"] is True
    st = mlc.do(T, "settings", {"target": "churned", "patience": 3, "eval_cmd": "python eval.py --out eval/metrics.json", "max_drop": 2})
    assert st["target"] == "churned" and st["patience"] == 3
    w = mlc.do(T, "ci", {})
    assert w["file"] == ".github/workflows/model-check.yml" and yaml.safe_load(w["yaml"])
    mlc.forget(T)
    assert "churned" in mlc.block(T)
    mk = mlc.do(T, "mark", {"id": d1["id"], "status": "fixed"})
    assert mk["status"] == "fixed" and not any(n["go"] == "data/" + d1["id"] for n in mlc.summary(T)["desk"]["needs"])
    import asyncio
    from app.agent import ml_tools as MT
    from app.agent.tools import Ctx
    out = asyncio.run(MT.ml_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="sizing", text=SZ))
    assert out["number"] == "Z-0002"
    out = asyncio.run(MT.ml_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="ci"))
    assert out["file"] == ".github/workflows/model-check.yml"
    with pytest.raises(PermissionError):
        mlc.do(T, "settings", {"eval_cmd": "my password is hunter2"})
    assert mlc.do(T, "add", {"kind": "run", "text": run_csv() + "\n# password = hunter2"})["kind"] == "run"
    for bad in ({"psi_warn": 0}, {"gpu_util": 2}, {"metrics_path": "../x"}, {"max_drop": -1}, {"python": "2"}):
        with pytest.raises((mlc.MlDeskError, PermissionError)):
            mlc.do(T, "settings", bad)
    with pytest.raises(mlc.MlDeskError):
        mlc.do(T, "add", {"kind": "sizing", "text": ""})
    with pytest.raises(mlc.MlDeskError):
        mlc.do(T, "nope", {})
    from app.employee import hire as H
    H.pause(T, "ml_eng")
    assert mlc.do(T, "get", {"id": r1["id"]})["id"] == r1["id"] and mlc.do(T, "ci", {})["yaml"]
    with pytest.raises(PermissionError):
        mlc.do(T, "add", {"kind": "sizing", "text": SZ})


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def ml_server(mlc, monkeypatch):
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


def test_desk_in_a_real_browser(mlc, ml_server):
    base, browser, key = ml_server
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
    pg.goto(base + "/console/ml")
    pg.wait_for_selector(".mlk-path", timeout=20000)
    snap(pg, "ml-today-empty-1440")
    go(pg, "#/training", "form[data-form=run]")
    submit(pg, "run", run_csv(), ".mlk-chart svg")
    assert "0.5821" in pg.inner_text(".cs-hero") and pg.locator(".mlk-chart polyline").count() >= 3
    snap(pg, "ml-training-1440")
    go(pg, "#/data", "form[data-form=data]")
    put(pg, "data", "target", "churned")
    put(pg, "data", "split", "split")
    submit(pg, "data", data_csv(), "table.mlk-t")
    assert "refund_issued" in pg.inner_text("#mlPage") and "Train against test" in pg.inner_text("#mlPage")
    snap(pg, "ml-data-1440")
    a, b, _, _ = drift_pair()
    go(pg, "#/drift", "form[data-form=drift]")
    put(pg, "drift", "current", b)
    submit(pg, "drift", a, ".mlk-pair")
    assert "Accra" in pg.inner_text("#mlPage")
    snap(pg, "ml-drift-1440")
    t, _, _ = reg_csv()
    go(pg, "#/errors", "form[data-form=regress]")
    put(pg, "regress", "group", "store")
    put(pg, "regress", "season", "7")
    submit(pg, "regress", t, ".mlk-scatter svg")
    assert "MASE" in pg.inner_text(".cs-hero") and pg.locator(".mlk-scatter circle").count() == 120
    snap(pg, "ml-errors-1440")
    go(pg, "#/sizing", "form[data-form=sizing]")
    submit(pg, "sizing", SZ, ".mlk-mem")
    assert "16.0 GB" in pg.inner_text(".cs-hero") and "LORA" in pg.inner_text("#mlPage")
    snap(pg, "ml-sizing-1440")
    go(pg, "#/ci", "text=Set the evaluation command")
    go(pg, "#/settings", "form[data-form=settings]")
    pg.fill("form[data-form=settings] [name=eval_cmd]", "python eval.py --out eval/metrics.json")
    pg.fill("form[data-form=settings] [name=target]", "churned")
    pg.click("form[data-form=settings] [type=submit]")
    pg.wait_for_selector("#toast:has-text('Saved')", timeout=20000)
    go(pg, "#/ci", "text=model-check.yml")
    snap(pg, "ml-ci-1440")
    go(pg, "#/today", ".mlk-list")
    assert "0.5821" in pg.inner_text(".cs-hero")
    snap(pg, "ml-today-1440")
    for route, sel in (("#/today", ".mlk-list"), ("#/training", ".mlk-item"), ("#/data", ".mlk-item"), ("#/drift", ".mlk-item"), ("#/errors", ".mlk-item"),
                       ("#/sizing", ".mlk-item"), ("#/ci", "text=model-check.yml"), ("#/settings", "form[data-form=settings]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('#mlPage *')].filter(e => !e.closest('pre,textarea,table,svg') && e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
    for route in ("#/training", "#/data", "#/drift", "#/errors", "#/sizing"):
        go(pg, route, ".mlk-item")
        pg.locator(".mlk-item").first.click()
        pg.wait_for_selector(".mlk-head", timeout=20000)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 8).map(e => e.tagName + '.' + e.className + ':' + Math.round(e.getBoundingClientRect().right) + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
        snap(pg, "ml-" + route[2:] + "-390")
    assert not errs, errs
