"""DISTRIBUTED DESK: the Distributed Systems Engineer's own section, built like the finance desks - its own chat (kind 'distsys')
with the desk block + the distributed tool in view; retry policies (jitter spreads the herd, deadlines cut tries) and call chains
(retries multiply, timeouts that do not nest); quorums and zones; a linearizability checker checked against brute force; the
fault-injection simulator (quorum without read repair breaks, the same run with read repair holds, last-writer-wins under clock
skew breaks, async failover loses acknowledged writes); TLA+ starters, the TLC output reader and the CI workflow; walked in a
browser."""
from __future__ import annotations

import itertools
import os
import random

import pytest
import yaml
from fastapi.testclient import TestClient

from tests import dist_samples as D

T = "default"


@pytest.fixture
def dsc(env):
    from app import distchat as C
    C._OF.clear()
    C._BLOCK.clear()
    return C


def _hire():
    from app.employee import hire
    hire.hire(T, "distsys_eng", trust="seekh")


# ---------------------------------------------------------------- the engine (pure code)
def test_retries_chains_quorums():
    from app.distdesk import quorum, retry
    peaks = {j: retry.analyse({"attempts": 4, "base_ms": 200, "timeout_ms": 1000, "jitter": j}, 1.0, 1000)["retry_peak"] for j in retry.JITTERS}
    assert peaks["none"] == 1000 and peaks["full"] < 150 and peaks["decorrelated"] < peaks["none"]
    r = retry.analyse({"attempts": 5, "base_ms": 100, "multiplier": 2, "cap_ms": 5000, "timeout_ms": 1000, "jitter": "none"})
    assert r["waits_worst"] == [100, 200, 400, 800] and r["worst_ms"] == 6500 and r["load_factor"] == 5
    assert r["issues"][0]["sev"] == "bad" and "No jitter" in r["issues"][0]["say"]
    assert retry.analyse({"attempts": 5, "deadline_ms": 3000})["deadline_cut"] == 2
    with pytest.raises(retry.RetryError):
        retry.analyse({"attempts": 50})
    c = retry.chain([{"name": "gateway", "attempts": 3, "timeout_ms": 2000}, {"name": "orders", "attempts": 3, "timeout_ms": 1000},
                     {"name": "db", "attempts": 2, "timeout_ms": 500}])
    assert c["amplification"] == 18 and sum("gives up" in i["say"] for i in c["issues"]) == 2
    q = quorum.analyse(3, 1, 1)
    assert not q["overlap"] and q["issues"][0]["sev"] == "bad"
    assert quorum.analyse(5, 3, 3)["overlap"] and quorum.analyse(4, mode="consensus")["tolerates"] == 1
    z = quorum.analyse(5, mode="consensus", zones=[{"name": "a", "replicas": 3}, {"name": "b", "replicas": 1}, {"name": "c", "replicas": 1}])
    assert [x["writes"] for x in z["zones"]] == [False, True, True] and "Losing a" in z["issues"][0]["say"]
    ok = quorum.analyse(5, mode="consensus", zones=[{"name": "a", "replicas": 2}, {"name": "b", "replicas": 2}, {"name": "c", "replicas": 1}])
    assert all(x["writes"] for x in ok["zones"]) and not ok["issues"]
    with pytest.raises(quorum.QuorumError):
        quorum.analyse(3, zones=[{"name": "a", "replicas": 2}])


def test_linearizability_checker_matches_brute_force():
    from app.distdesk import linear as L

    def brute(ops):
        must = [o for o in ops if not o["info"]]
        opt = [o for o in ops if o["info"]]
        inf = float("inf")
        for k in range(len(opt) + 1):
            for sub in itertools.combinations(opt, k):
                for perm in itertools.permutations(must + list(sub)):
                    if any((perm[j]["ret"] if perm[j]["ret"] is not None else inf) < perm[i]["call"]
                           for i in range(len(perm)) for j in range(i + 1, len(perm))):
                        continue
                    st, good = None, True
                    for o in perm:
                        good, st = L._step(st, o)
                        if not good:
                            break
                    if good:
                        return True
        return False
    seen = {True: 0, False: 0}
    for trial in range(500):
        rnd = random.Random(trial)
        lines, openp, val = [], {}, 1
        for _ in range(rnd.randint(4, 11)):
            p = rnd.randrange(3)
            if p in openp:
                f, v = openp.pop(p)
                lines.append(f"{p} {rnd.choice(['ok', 'ok', 'info'])} write {v}" if f == "write" else f"{p} ok read {rnd.choice(['nil', 1, 2, 3])}")
            elif rnd.random() < 0.5:
                openp[p] = ("write", val)
                lines.append(f"{p} invoke write {val}")
                val += 1
            else:
                openp[p] = ("read", None)
                lines.append(f"{p} invoke read")
        ops = L.ops_of(L.parse("\n".join(lines)))
        if len(ops) > 6:
            continue
        a = L.check_key(ops)["result"] == "ok"
        assert a == brute(ops), "\n".join(lines)
        seen[a] += 1
    assert seen[True] > 20 and seen[False] > 20
    bad = L.check(D.HISTORY_BAD)
    assert not bad["linearizable"] and "Process 1's read 1" in bad["verdict"] and bad["timeline"][-1]["bad"]
    j = L.check(D.HISTORY_JSON)
    assert j["linearizable"] and j["info_ops"] == 1 and {k["key"] for k in j["keys"]} == {None, "x"}
    edn = '{:type :invoke, :f :write, :value 3, :process 0}\n{:type :ok, :f :write, :value 3, :process 0}\n{:type :invoke, :f :read, :value nil, :process 1}\n{:type :ok, :f :read, :value 4, :process 1}'
    assert not L.check(edn)["linearizable"]
    with pytest.raises(L.HistoryError):
        L.check("0 ok read 1")


def test_simulator_and_specs():
    from app.distdesk import sim, tla
    res = {k: sim.run(v) for k, v in sim.PRESETS.items()}
    assert res["leader"]["check"]["result"] == "ok"
    assert res["quorum"]["check"]["result"] == "fail" and res["quorum_repair"]["check"]["result"] == "ok"      # read repair fixes the same run
    assert res["quorum_partition"]["check"]["result"] == "ok" and res["quorum_partition"]["counts"]["fail"] > 0
    assert res["lww_skew"]["check"]["result"] == "fail"
    af = res["async_failover"]
    assert af["check"]["result"] == "fail" and af["lost_writes"] and af["failover"][0]["from"] == 0
    assert sim.run(sim.PRESETS["quorum"])["history"] == res["quorum"]["history"]                             # same seed, same run
    with pytest.raises(sim.SimError):
        sim.run({"protocol": "gossip"})
    for k in tla.TEMPLATES:
        bugged, fixed = tla.template(k, False), tla.template(k, True)
        assert bugged["tla"] == fixed["tla"] and f"{fixed['switch']} = TRUE" in fixed["cfg"] and f"{fixed['switch']} = FALSE" in bugged["cfg"]
        assert f"MODULE {fixed['module']}" in fixed["tla"] and fixed["tla"].rstrip().endswith("=" * 77)
    f = tla.read_output(D.TLC_FAIL)
    assert (f["result"], f["invariant"], f["distinct"], f["depth"], len(f["trace"])) == ("invariant", "NoStaleWrite", 9, 5, 5)
    assert f["trace"][1]["action"] == "Acquire" and f["trace"][-1]["changed"] == ["writes"] and f["trace"][-1]["vars"]["writes"] == "<<2, 1>>"
    p = tla.read_output(D.TLC_PASS)
    assert p["result"] == "pass" and p["distinct"] == 288 and p["generated"] == 1204
    assert not tla.read_output("hello")["ok"]
    wf = tla.workflow("specs", "v1.8.0", "main")
    y = yaml.safe_load(wf["yaml"])
    assert y[True]["push"]["paths"] == ["specs/**"] and "releases/download/v1.8.0/tla2tools.jar" in wf["yaml"]
    with pytest.raises(ValueError):
        tla.workflow("../etc")


def test_hire_chat_wiring_store_and_guards(dsc):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert dsc.summary(T)["hired"] is False and "Hire me from AI Employees" in dsc.greeting(T)
    with pytest.raises(PermissionError):
        dsc.do(T, "add", {"kind": "retry", "inputs": {}})
    _hire()
    d = dsc.summary(T)
    assert d["hired"] and "never runs anything on your systems" in d["foot"] and {n["go"] for n in d["desk"]["needs"]} >= {"retries", "settings"}
    chat = dsc.current(T)
    assert dsc.is_distsys(chat["id"]) and dsc.owns(T, chat["id"]) and "<distributed_desk>" in dsc.block(T)
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_dsc.is_distsys(conversation_id)" in src and "adm.admit_families(_dsc.FAMILIES)" in src
    for f_ in ("callconv.py", "convs.py"):
        assert '"distsys"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/distributed")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "dsdesk.js" in r.text
    html = (root / "server/app/static/console/dsdesk.html").read_text()
    for x in ("chatkit.js", "dsdesk.css", "dsdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/distributed')" in (root / "server/app/static/console/v2.js").read_text()
    assert "distsys_eng: 'dsdesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["distsys_eng"]["live"] is True
    from app.agent.tools import FAMILY_OF, HANDLERS
    assert FAMILY_OF["dist_desk"] in dsc.FAMILIES and "dist_desk" in HANDLERS
    rt = dsc.do(T, "add", {"kind": "retry", "inputs": {"attempts": 5, "jitter": "none"}})
    assert rt["number"] == "R-0001" and rt["brief"]["bad"] and any(n["go"] == "retries/" + rt["id"] for n in dsc.summary(T)["desk"]["needs"])
    ch = dsc.do(T, "add", {"kind": "chain", "inputs": {"hops": [{"name": "a", "attempts": 3, "timeout_ms": 100}, {"name": "b", "attempts": 3, "timeout_ms": 100}]}})
    assert ch["brief"]["amplification"] == 9
    sm = dsc.do(T, "add", {"kind": "sim", "inputs": {"preset": "quorum"}})
    assert sm["number"] == "J-0001" and sm["brief"]["result"] == "fail" and "invoke" in sm["text"]
    h = dsc.do(T, "add", {"kind": "history", "text": sm["text"]})
    assert h["brief"]["result"] == "fail" and h["brief"]["ops"] == sm["brief"]["ops"]
    ok = dsc.do(T, "add", {"kind": "history", "text": D.HISTORY_JSON})
    assert ok["status"] == "fixed"
    tl = dsc.do(T, "add", {"kind": "tlc", "text": D.TLC_FAIL})
    assert tl["title"] == "TLC: NoStaleWrite violated" and any("NoStaleWrite violated" in n["say"] for n in dsc.summary(T)["desk"]["needs"])
    assert dsc.do(T, "spec", {"key": "fencing", "fixed": False})["cfg"].count("Fencing = FALSE") == 1
    s = dsc.do(T, "settings", {"system": "payments", "specs_dir": "tla", "fail_rate": "50"})
    assert s["specs_dir"] == "tla" and s["fail_rate"] == 0.5
    assert "paths: ['tla/**']" in dsc.do(T, "workflow", {})["yaml"]
    dsc.forget(T)
    assert "payments" in dsc.block(T)
    # guards
    with pytest.raises(PermissionError):
        dsc.do(T, "settings", {"system": "my password is hunter2"})
    assert dsc.do(T, "add", {"kind": "tlc", "text": "TLC2 password: hunter2 Model checking completed. No error has been found."})["kind"] == "tlc"
    with pytest.raises(dsc.DsDeskError):
        dsc.do(T, "settings", {"specs_dir": "../etc"})
    with pytest.raises(dsc.DsDeskError):
        dsc.do(T, "add", {"kind": "quorum", "inputs": {"n": 0}})
    with pytest.raises(dsc.DsDeskError):
        dsc.do(T, "add", {"kind": "history", "text": "nonsense"})
    with pytest.raises(dsc.DsDeskError):
        dsc.do(T, "nope", {})
    from app.employee import hire as H
    H.pause(T, "distsys_eng")
    assert dsc.do(T, "get", {"id": rt["id"]})["id"] == rt["id"]
    with pytest.raises(PermissionError):
        dsc.do(T, "add", {"kind": "retry", "inputs": {}})


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def ds_server(dsc, monkeypatch):
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


def test_desk_in_a_real_browser(dsc, ds_server):
    base, browser, key = ds_server
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
    pg.goto(base + "/console/distributed")
    pg.wait_for_selector(".dsk-starts", timeout=20000)
    go(pg, "#/retries", "form[data-form=retry]")
    pg.select_option("form[data-form=retry] [name=jitter]", "none")
    pg.fill("form[data-form=retry] [name=attempts]", "5")
    pg.click("form[data-form=retry] [type=submit]")
    pg.wait_for_selector(".dsk-herd", timeout=30000)
    assert "No jitter" in pg.inner_text("#dsPage")
    snap(pg, "ds-retry-1440")
    go(pg, "#/retries", "form[data-form=chain]")
    pg.fill("form[data-form=chain] [name=hops]", "gateway, 3, 2000\norders, 3, 1000\ndb, 2, 500")
    pg.click("form[data-form=chain] [type=submit]")
    pg.wait_for_selector(".dsk-chain", timeout=30000)
    assert "18 requests" in pg.inner_text("#dsPage")
    go(pg, "#/quorums", "form[data-form=quorum]")
    pg.select_option("form[data-form=quorum] [name=mode]", "consensus")
    pg.fill("form[data-form=quorum] [name=n]", "5")
    pg.fill("form[data-form=quorum] [name=zones]", "zone-a, 3\nzone-b, 1\nzone-c, 1")
    pg.click("form[data-form=quorum] [type=submit]")
    pg.wait_for_selector(".dsk-zones", timeout=30000)
    assert "writes stop" in pg.inner_text(".dsk-zones")
    snap(pg, "ds-quorum-1440")
    go(pg, "#/histories", "form[data-form=sim]")
    pg.select_option("form[data-form=sim] [name=preset]", "async_failover")
    pg.click("form[data-form=sim] [type=submit]")
    pg.wait_for_selector(".dsk-tl", timeout=30000)
    assert "Not linearizable" in pg.inner_text(".dsk-sum") and "lost in the failover" in pg.inner_text(".dsk-sum") and pg.locator(".dsk-tl g.bad").count() == 1
    snap(pg, "ds-sim-1440")
    go(pg, "#/histories", "form[data-form=history]")
    pg.fill("form[data-form=history] [name=text]", D.HISTORY_BAD)
    pg.click("form[data-form=history] [type=submit]")
    pg.wait_for_selector(".dsk-tl", timeout=30000)
    assert "Process 1's read 1" in pg.inner_text(".dsk-sum")
    go(pg, "#/specs", ".dsk-kinds")
    pg.click("[data-spec=fencing]")
    pg.wait_for_selector("text=FencedLeader.cfg", timeout=20000)
    assert "Fencing = FALSE" in pg.inner_text(".dsk-files")
    pg.click("[data-fixed='1']")
    pg.wait_for_selector(".dsk-files >> text=Fencing = TRUE", timeout=20000)
    pg.click("[data-wf]")
    pg.wait_for_selector("text=.github/workflows/tla-check.yml", timeout=20000)
    snap(pg, "ds-specs-1440")
    pg.fill("form[data-form=tlc] [name=text]", D.TLC_FAIL)
    pg.click("form[data-form=tlc] [type=submit]")
    pg.wait_for_selector(".dsk-trace", timeout=30000)
    assert pg.locator(".dsk-vars div.ch").count() >= 4
    snap(pg, "ds-tlc-1440")
    go(pg, "#/settings", "form[data-form=settings]")
    pg.fill("form[data-form=settings] [name=system]", "payments")
    pg.click("form[data-form=settings] [type=submit]")
    pg.wait_for_selector("#toast:has-text('Saved')", timeout=20000)
    assert "payments" in pg.inner_text("#dsSite")
    go(pg, "#/today", ".dsk-list")
    snap(pg, "ds-today-1440")
    for route, sel in (("#/today", ".dsk-list"), ("#/retries", ".dsk-item"), ("#/quorums", ".dsk-item"), ("#/histories", ".dsk-item"),
                       ("#/specs", ".dsk-item"), ("#/settings", "form[data-form=settings]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('#dsPage *')].filter(e => !e.closest('pre,textarea,table,.dsk-tl') && e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
    go(pg, "#/histories", ".dsk-item")
    pg.click(".dsk-item")
    pg.wait_for_selector(".dsk-tl", timeout=20000)
    w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
    assert w[0] <= w[1] + 1, w
    snap(pg, "ds-history-390")
    assert not errs, errs
