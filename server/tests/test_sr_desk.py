"""SRE DESK: the Site Reliability Engineer's own section, built like the finance desks - its own chat (kind 'sre') with the desk
block + the SRE tool in view; SLOs and error budgets (the numbers of the nines), the multiwindow burn-rate alerts of the Google SRE
workbook (which fire on a real outage and not on a blip) and the Prometheus rules for them (valid YAML, her metric names); alert
rules checked for noise; alert history counted in her time zone; incident timelines read into times and a blameless postmortem
(blanks never filled in); latency percentiles and histogram quantiles with their bounds; capacity trends; M/M/c queues; system
availability from its parts; walked in a browser."""
from __future__ import annotations

import math
import os
import random

import pytest
import yaml
from fastapi.testclient import TestClient

T = "default"

RULES = """groups:
  - name: api
    rules:
      - alert: HighCPU
        expr: node_cpu_seconds_total > 100
        labels: {severity: critical}
      - alert: ApiErrors
        expr: sum(rate(http_errors_total[30s])) / sum(rate(http_requests_total[30s])) > 0.01
        for: 5m
        labels: {severity: page}
        annotations: {summary: "API errors", runbook_url: "https://runbooks.example/api"}
      - alert: Good
        expr: sum(rate(http_errors_total[5m])) / sum(rate(http_requests_total[5m])) > 0.05
        for: 10m
        labels: {severity: page}
        annotations: {summary: "Errors", runbook_url: "https://runbooks.example/errors"}
      - record: job:errors:rate5m
        expr: sum(rate(http_errors_total[5m]))
"""

INCIDENT = """2026-11-27 09:58 deploy v2.3 went out to prod
10:02 first errors in checkout, SEV2
10:14 alert fired: CheckoutErrorBudgetBurnFast
10:21 on it, investigating
10:35 rolled back to v2.2, errors dropped
10:50 resolved, all clear
10:52 TODO add a canary step before full rollout
10:53 it was the reviewer's fault for skipping review
"""


def series(outage=(600, 660), bad_base=2, bad_out=200, minutes=24 * 60):
    lines = ["time,good,total"]
    t0 = 1_800_000_000
    for i in range(minutes):
        bad = bad_out if outage and outage[0] <= i < outage[1] else bad_base
        lines.append(f"{t0 + i * 60},{1000 - bad},1000")
    return "\n".join(lines)


def noise_csv(seed=3):
    r = random.Random(seed)
    lines = ["alertname,startsAt,endsAt,severity,acked"]
    t = 1_800_000_000
    for i in range(300):
        n = r.choice(["DiskFull", "Flappy", "Flappy", "Flappy", "ApiErrors"])
        s = t + i * 3000
        e = s + (120 if n == "Flappy" else 1800)
        lines.append(f"{n},{s},{e},page,{'' if n == 'DiskFull' else 'yes'}")
    return "\n".join(lines)


@pytest.fixture
def src(env):
    from app import srechat as C
    C._OF.clear()
    C._BLOCK.clear()
    return C


def _hire():
    from app.employee import hire
    hire.hire(T, "sre", trust="seekh")


# ---------------------------------------------------------------- the engine (pure code)
def test_slo_budget_burn_and_rules():
    from app.sredesk import slo
    b = slo.budget(99.9, 30)
    assert round(b["allowed_minutes"], 1) == 43.2 and b["allowed"] == "43.2 min"
    n = {r["target"]: r for r in slo.nines_table()}
    assert n[0.999]["year"] == "8.8 h" and n[0.9999]["month30"] == "4.3 min"
    u = slo.budget(99.9, 30, 999_000, 1_000_000, 10)
    assert u["used"] == 1.0 and u["burn_rate"] == 3.0 and u["issues"][0]["sev"] == "bad"
    half = slo.budget(0.999, 30, 999_500, 1_000_000, 15)
    assert half["used"] == 0.5 and half["burn_rate"] == 1.0 and not half["issues"]
    a = {x["name"]: x for x in slo.alerts_for(30)}
    assert (a["fast"]["burn"], a["fast"]["long_h"], round(a["fast"]["short_h"] * 60)) == (14.4, 1.0, 5)
    assert (a["slow"]["burn"], a["drift"]["burn"], a["drift"]["long_h"]) == (6.0, 1.0, 72.0)
    assert slo.alerts_for(28)[0]["burn"] == pytest.approx(13.44)
    # a real outage pages; the same day without it pages nothing; a blip shorter than 5 min does not page
    hit = slo.burn(series(), 99.9, 30)
    assert {f["alert"] for f in hit["fired"] if f["severity"] == "page"} == {"fast", "slow"}
    calm = slo.burn(series(outage=None, bad_base=0), 99.9, 30)
    assert not calm["fired"] and "No burn-rate alert" in calm["verdict"]
    blip = slo.burn(series(outage=(600, 602), bad_base=0, bad_out=120), 99.9, 30)
    assert not [f for f in blip["fired"] if f["alert"] == "fast"]
    # counters (only rising) are turned into steps
    cum, g, n_ = ["t,good,total"], 0, 0
    for i in range(600):
        n_ += 1000
        g += 1000 - (200 if 300 <= i < 360 else 0)
        cum.append(f"{1_800_000_000 + i * 60},{g},{n_}")
    c = slo.burn("\n".join(cum), 99.9, 30)
    assert c["counters"] and any(f["alert"] == "fast" for f in c["fired"])
    with pytest.raises(slo.SloError):
        slo.burn("t,good,total\n1,5,3\n2,5,6", 99.9)
    rl = slo.rules("checkout", 99.9, 30, "http_requests_errors_total", "http_requests_total", '{job="api"}')
    doc = yaml.safe_load(rl["yaml"])["groups"][0]["rules"]
    recs = [x for x in doc if "record" in x]
    alerts = [x for x in doc if "alert" in x]
    assert {x["record"].rsplit("rate", 1)[1] for x in recs} == {"5m", "30m", "1h", "6h", "3d"}
    assert len(alerts) == 3 and all(x["labels"]["slo"] == "checkout" and x["annotations"]["runbook_url"] for x in alerts)
    assert "> (14.4 * 0.001)" in alerts[0]["expr"] and '{job="api"}' in recs[0]["expr"]
    with pytest.raises(slo.SloError):
        slo.rules("x", 99.9, 30, "bad metric!", "t_total")
    with pytest.raises(slo.SloError):
        slo.rules("x", 99.9, 30, "a_total", "t_total", '{job="api"} or vector(1)')


def test_latency_capacity_queue_availability():
    from app.sredesk import avail, capacity, latency
    vals = list(range(1, 1001))
    r = latency.analyse("\n".join(map(str, vals)), 500)
    assert r["percentiles"]["p50"] == pytest.approx(500.5) and r["percentiles"]["p99"] == pytest.approx(990.01)
    assert r["under_threshold"] == 0.5 and r["apdex"] == pytest.approx(0.75)
    log = "\n".join(f"GET /x 200 {v}ms" for v in vals[:20]) + "\n" + "\n".join(f"GET /y 200 {v / 1000}s" for v in vals[20:40])
    assert latency.analyse(log, 30)["count"] == 40
    csv = "path,duration_seconds\n" + "\n".join(f"/a,{v / 1000}" for v in vals[:50])
    assert latency.analyse(csv, 25)["under_threshold"] == 0.5
    b = latency.buckets('h_bucket{le="0.05"} 100\nh_bucket{le="0.1"} 400\nh_bucket{le="0.25"} 900\nh_bucket{le="0.5"} 980\n'
                        'h_bucket{le="+Inf"} 1000', 250)
    assert b["quantiles"]["p50"]["ms"] == pytest.approx(130.0) and b["quantiles"]["p50"]["between_ms"] == [100.0, 250.0]
    assert b["under_threshold"] == 0.9 and b["estimated"] is False and b["quantiles"]["p99"]["between_ms"][1] is None
    est = latency.buckets('h_bucket{le="0.1"} 50\nh_bucket{le="0.5"} 100\nh_bucket{le="+Inf"} 100', 300)
    assert est["estimated"] and est["under_threshold"] == pytest.approx(0.75)
    assert latency.buckets('a{le="0.1"} 10\na{le="0.2"} 5\na{le="+Inf"} 20')["issues"][0]["sev"] == "bad"
    # capacity: a clean line hits the limit on the day the arithmetic says
    rows = "\n".join(f"2026-01-{d:02d}, {40 + d}" for d in range(1, 21))
    f = capacity.forecast(rows, 100, 80)
    assert f["slope_per_day"] == pytest.approx(1.0) and f["r2"] == pytest.approx(1.0)
    assert f["hits_headroom"] == "2026-02-09" and f["hits_limit"] == "2026-03-01"
    assert capacity.forecast("2026-01-01, 50\n2026-01-02, 50\n2026-01-03, 50", 100)["hits_limit"] is None
    # M/M/1: wait = rho / (mu - lambda)
    q = capacity.queue(50, 10, 1)
    assert q["utilisation"] == 0.5 and q["wait_ms"] == pytest.approx(10.0) and q["response_ms"] == pytest.approx(20.0)
    q2 = capacity.queue(90, 20, 2)
    assert q2["one_down_utilisation"] > 1 and any("no N+1" in i["text"] for i in q2["issues"])
    assert capacity.queue(200, 10, 1)["min_servers"] == 3
    # availability: series multiplies, 1-of-2 is 1 - (1-a)^2, the costliest part is named
    tree = {"name": "shop", "all": [{"name": "lb", "availability": 99.99}, {"name": "app", "any": [{"name": "a1", "availability": 99.5},
            {"name": "a2", "availability": 99.5}]}, {"name": "db", "availability": 99.9}]}
    a = avail.analyse(tree, 99.95)
    assert a["availability"] == pytest.approx(0.9999 * (1 - 0.005 ** 2) * 0.999) and a["weakest"] == "db"
    assert a["issues"][0]["sev"] == "bad"
    k2 = avail.analyse({"name": "x", "any": [{"name": str(i), "availability": 90} for i in range(3)], "need": 2})
    assert k2["availability"] == pytest.approx(3 * 0.9 ** 2 * 0.1 + 0.9 ** 3)
    assert avail.replicas_needed(99, 99.99)["replicas"] == 2
    with pytest.raises(avail.AvailError):
        avail.analyse({"name": "x", "all": [{"name": "y"}]})
    assert not math.isnan(a["downtime_month_min"])


def test_alert_rules_noise_and_incidents():
    from app.sredesk import alerts, incident
    lt = alerts.lint(RULES, 30)
    by = {r["name"]: [i["text"] for i in r["issues"]] for r in lt["rules"]}
    assert lt["alerts"] == 3 and lt["records"] == 1
    assert any("No `for`" in x for x in by["HighCPU"]) and any("counter" in x for x in by["HighCPU"]) and any("cause" in x for x in by["HighCPU"])
    assert sum("under 4 scrapes" in x for x in by["ApiErrors"]) == 1
    assert not [x for x in by["Good"] if "No " in x or "counter" in x]
    with pytest.raises(alerts.AlertError):
        alerts.lint("groups: [\n", 30)
    nz = alerts.noise(noise_csv(), "Asia/Kolkata")
    top = nz["table"][0]
    assert top["name"] == "Flappy" and top["median_min"] == 2.0 and any("under 5 minutes" in a for a in top["advice"])
    disk = next(t for t in nz["table"] if t["name"] == "DiskFull")
    assert disk["acked_share"] == 0 and any("Never acknowledged" in a for a in disk["advice"])
    assert nz["issues"][0]["sev"] == "bad" and sum(nz["by_hour"]) == 300
    # the same history read in another zone moves the hours
    assert alerts.noise(noise_csv(), "America/New_York")["by_hour"] != nz["by_hour"]
    with pytest.raises(alerts.AlertError):
        alerts.noise(noise_csv(), "Mars/Base")
    t = incident.timeline(INCIDENT, "Asia/Kolkata")
    assert t["said"] == {"detect": "16 min", "ack": "7 min", "mitigate": "37 min", "resolve": "52 min", "impact": "37 min"}
    assert t["severity"] == "SEV2" and len(t["followups"]) == 1 and len(t["blame"]) == 1
    assert t["marks"]["start"].startswith("2026-11-27T09:58") and t["marks"]["start"].endswith("+05:30")
    pm = incident.postmortem(t, "Checkout errors", "checkout")
    assert "blameless" in pm and "## Root cause\n_(to write: only you know this)_" in pm and "| Time to detect | 16 min |" in pm
    assert "TODO add a canary step" in pm and "Reword before sharing" in pm
    assert pm.count("(Impact started)") == 1
    night = incident.timeline("23:50 errors started\n23:58 paged\n00:20 rolled back\n00:40 resolved", "UTC", "2026-11-27")
    assert night["said"]["resolve"] == "50 min" and night["marks"]["resolve"].startswith("2026-11-28")
    with pytest.raises(incident.IncidentError):
        incident.timeline("no times here", "UTC")


def test_hire_chat_wiring_store_and_guards(src):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert src.summary(T)["hired"] is False and "Hire me from AI Employees" in src.greeting(T)
    with pytest.raises(PermissionError):
        src.do(T, "add", {"kind": "slo", "inputs": {}})
    _hire()
    d = src.summary(T)
    assert d["hired"] and "never changes anything on your systems" in d["foot"] and {n["go"] for n in d["desk"]["needs"]} >= {"slos", "settings"}
    chat = src.current(T)
    assert src.is_sre(chat["id"]) and src.owns(T, chat["id"]) and "<sre_desk>" in src.block(T)
    s_ = (root / "server/app/agent/santosh.py").read_text()
    assert "_src.is_sre(conversation_id)" in s_ and "adm.admit_families(_src.FAMILIES)" in s_
    for f_ in ("callconv.py", "convs.py"):
        assert '"sre")' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/sre")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "srdesk.js" in r.text
    html = (root / "server/app/static/console/srdesk.html").read_text()
    for x in ("chatkit.js", "srdesk.css", "srdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/sre')" in (root / "server/app/static/console/v2.js").read_text()
    assert "sre: 'srdesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["sre"]["live"] is True
    from app.agent.tools import FAMILY_OF, HANDLERS
    assert FAMILY_OF["sre_desk"] in src.FAMILIES and "sre_desk" in HANDLERS
    s = src.do(T, "add", {"kind": "slo", "inputs": {"target": 99.9, "good": 999000, "total": 1000000, "elapsed_days": 10}})
    assert s["number"] == "S-0001" and s["brief"]["bad"] and any(n["go"] == "slos/" + s["id"] for n in src.summary(T)["desk"]["needs"])
    assert src.summary(T)["desk"]["budget"]["used"] == 1.0
    b = src.do(T, "add", {"kind": "burn", "text": series()})
    assert b["number"] == "B-0001" and b["brief"]["fired"] >= 2 and b["brief"]["bad"]
    lt = src.do(T, "add", {"kind": "rules", "text": RULES})
    assert lt["brief"]["problems"] >= 1
    nz = src.do(T, "add", {"kind": "noise", "text": noise_csv()})
    assert src.summary(T)["desk"]["pages_week"] == nz["brief"]["per_week"]
    inc = src.do(T, "add", {"kind": "incident", "text": INCIDENT, "inputs": {"tz": "Asia/Kolkata", "impact": "4% of checkouts failed"}})
    assert inc["status"] == "fixed" and "4% of checkouts failed" in inc["result"]["postmortem"]
    assert src.summary(T)["desk"]["incidents"]["median"]["resolve"] == "52 min"
    pm = src.do(T, "postmortem", {"id": inc["id"], "root_cause": "The deploy had no canary."})
    assert "The deploy had no canary." in pm["markdown"]
    with pytest.raises(src.SrDeskError):
        src.do(T, "rules", {})
    st = src.do(T, "settings", {"service": "checkout", "tz": "Europe/London", "bad_metric": "http_requests_errors_total",
                                "total_metric": "http_requests_total", "target": "99.95"})
    assert st["target"] == pytest.approx(0.9995) and st["tz"] == "Europe/London"
    assert "slo-checkout" in src.do(T, "rules", {})["yaml"]
    src.forget(T)
    assert "checkout" in src.block(T) and "Europe/London" in src.block(T)
    for kind, inputs in (("latency", {}), ("capacity", {"limit": 100}), ("queue", {"rps": 50, "service_ms": 10, "servers": 1}),
                         ("avail", {"tree": {"name": "a", "all": [{"name": "b", "availability": 99.9}]}})):
        x = src.do(T, "add", {"kind": kind, "text": "\n".join(f"2026-01-{d:02d}, {40 + d}" for d in range(1, 21)) if kind == "capacity" else
                              "\n".join(str(v) for v in range(1, 200)), "inputs": inputs})
        assert x["kind"] == kind
    # guards
    with pytest.raises(PermissionError):
        src.do(T, "settings", {"service": "my password is hunter2"})
    assert src.do(T, "add", {"kind": "incident", "text": "10:00 password: hunter2 in a log\n10:05 resolved"})["kind"] == "incident"
    with pytest.raises(src.SrDeskError):
        src.do(T, "settings", {"tz": "Nowhere/Land"})
    with pytest.raises(src.SrDeskError):
        src.do(T, "settings", {"selector": '{job="a"} or vector(1)'})
    with pytest.raises(src.SrDeskError):
        src.do(T, "add", {"kind": "slo", "inputs": {"target": 120}})
    with pytest.raises(src.SrDeskError):
        src.do(T, "add", {"kind": "rules", "text": ""})
    with pytest.raises(src.SrDeskError):
        src.do(T, "nope", {})
    from app.employee import hire as H
    H.pause(T, "sre")
    assert src.do(T, "get", {"id": s["id"]})["id"] == s["id"]
    with pytest.raises(PermissionError):
        src.do(T, "add", {"kind": "slo", "inputs": {}})


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def sr_server(src, monkeypatch):
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


def test_desk_in_a_real_browser(src, sr_server):
    base, browser, key = sr_server
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
    pg.goto(base + "/console/sre")
    pg.wait_for_selector(".srk-starts", timeout=20000)
    snap(pg, "sr-today-empty-1440")
    go(pg, "#/settings", "form[data-form=settings]")
    pg.fill("form[data-form=settings] [name=service]", "checkout")
    pg.fill("form[data-form=settings] [name=tz]", "Asia/Kolkata")
    pg.fill("form[data-form=settings] [name=bad_metric]", "http_requests_errors_total")
    pg.fill("form[data-form=settings] [name=total_metric]", "http_requests_total")
    pg.click("form[data-form=settings] [type=submit]")
    pg.wait_for_selector("#toast:has-text('Saved')", timeout=20000)
    assert "checkout" in pg.inner_text("#srSite")
    go(pg, "#/slos", "form[data-form=slo]")
    pg.fill("form[data-form=slo] [name=good]", "999000")
    pg.fill("form[data-form=slo] [name=total]", "1000000")
    pg.fill("form[data-form=slo] [name=elapsed_days]", "10")
    pg.click("form[data-form=slo] [type=submit]")
    pg.wait_for_selector(".srk-meter", timeout=30000)
    assert "budget is spent" in pg.inner_text("#srPage")
    snap(pg, "sr-slo-1440")
    go(pg, "#/slos", "form[data-form=burn]")
    pg.fill("form[data-form=burn] [name=text]", series())
    pg.click("form[data-form=burn] [type=submit]")
    pg.wait_for_selector(".srk-fired", timeout=30000)
    assert pg.locator(".srk-chart line.th").count() == 2
    snap(pg, "sr-burn-1440")
    go(pg, "#/slos", "[data-rules]")
    pg.click("[data-rules]")
    pg.wait_for_selector("text=slo-checkout.rules.yml", timeout=20000)
    assert "ErrorBudgetBurnFast" in pg.inner_text("#srPage")
    go(pg, "#/alerts", "form[data-form=rules]")
    pg.fill("form[data-form=rules] [name=text]", RULES)
    pg.click("form[data-form=rules] [type=submit]")
    pg.wait_for_selector(".srk-rule", timeout=30000)
    assert pg.locator(".srk-rule").count() == 2
    pg.click(".srk-rule summary")
    snap(pg, "sr-rules-1440")
    go(pg, "#/alerts", "form[data-form=noise]")
    pg.fill("form[data-form=noise] [name=text]", noise_csv())
    pg.click("form[data-form=noise] [type=submit]")
    pg.wait_for_selector(".srk-hours", timeout=30000)
    assert pg.locator(".srk-hr").count() == 24 and "Flappy" in pg.inner_text("#srPage")
    snap(pg, "sr-noise-1440")
    go(pg, "#/incidents", "form[data-form=incident]")
    pg.fill("form[data-form=incident] [name=text]", INCIDENT)
    pg.fill("form[data-form=incident] [name=impact]", "4% of checkouts failed")
    pg.click("form[data-form=incident] [type=submit]")
    pg.wait_for_selector(".srk-tl", timeout=30000)
    assert pg.locator(".srk-tl li.mk").count() == 5 and "52 min" in pg.inner_text(".cs-hero")
    assert "4% of checkouts failed" in pg.inner_text("#srPage")
    snap(pg, "sr-incident-1440")
    go(pg, "#/capacity", ".srk-seg")
    pg.fill("form[data-form=latency] [name=text]", "\n".join(str(v) for v in range(1, 1001)))
    pg.fill("form[data-form=latency] [name=threshold_ms]", "500")
    pg.click("form[data-form=latency] [type=submit]")
    pg.wait_for_selector("text=Apdex", timeout=30000)
    assert "0.75" in pg.inner_text(".cs-hero")
    go(pg, "#/capacity", ".srk-seg")
    pg.click("[data-cap=avail]")
    pg.wait_for_selector("form[data-form=avail]", timeout=10000)
    pg.fill("form[data-form=avail] [name=tree]", "shop: all\n  load balancer, 99.99\n  app: any\n    app 1, 99.5\n    app 2, 99.5\n  database, 99.9")
    pg.click("form[data-form=avail] [type=submit]")
    pg.wait_for_selector("text=Where the downtime comes from", timeout=30000)
    assert "database" in pg.inner_text(".cs-hero")
    snap(pg, "sr-avail-1440")
    go(pg, "#/capacity", ".srk-seg")
    pg.click("[data-cap=queue]")
    pg.fill("form[data-form=queue] [name=rps]", "90")
    pg.fill("form[data-form=queue] [name=service_ms]", "20")
    pg.click("form[data-form=queue] [type=submit]")
    pg.wait_for_selector("text=Response time as it gets busier", timeout=30000)
    go(pg, "#/today", ".srk-list")
    assert "left" in pg.inner_text(".cs-hero")
    snap(pg, "sr-today-1440")
    for route, sel in (("#/today", ".srk-list"), ("#/slos", ".srk-item"), ("#/alerts", ".srk-item"), ("#/incidents", ".srk-item"),
                       ("#/capacity", ".srk-item"), ("#/settings", "form[data-form=settings]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('#srPage *')].filter(e => !e.closest('pre,textarea,table,svg') && e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
    go(pg, "#/incidents", ".srk-item")
    pg.click(".srk-item")
    pg.wait_for_selector(".srk-tl", timeout=20000)
    w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
    assert w[0] <= w[1] + 1, w
    snap(pg, "sr-incident-390")
    assert not errs, errs
