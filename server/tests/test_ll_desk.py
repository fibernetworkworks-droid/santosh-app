"""LOW LATENCY DESK: the Backend Systems Engineer (Low Latency)'s own section, built like the finance desks - its own chat (kind
'lowlat') with the desk block + the latency tool in view; latency percentiles from samples / HdrHistogram / wrk2 with how far each can
be trusted, runs compared with a bootstrap interval, coordinated omission corrected; a request path's budget sampled (fan-out, hedging);
hot-path code read; struct layout + false sharing; perf profiles + counters; host tuning; the CI workflow is valid YAML and its compare
step really fails a slower head; walked in a browser."""
from __future__ import annotations

import os
import random
import subprocess
import sys

import pytest
import yaml
from fastapi.testclient import TestClient

T = "default"


def _samples(seed, n, scale=1.0, tail=0):
    r = random.Random(seed)
    v = [r.lognormvariate(3.0, 0.35) * scale for _ in range(n)] + [r.uniform(900, 1300) * scale for _ in range(tail)]
    return "\n".join(f"{x:.2f}" for x in v)


TWO = "## before\n" + _samples(1, 6000) + "\n## after\n" + _samples(2, 6000, 1.35)
SAME = "## a\n" + _samples(3, 6000) + "\n## b\n" + _samples(4, 6000)
WRK2 = """Running 30s test @ http://127.0.0.1:8080
  Latency Distribution (HdrHistogram - Recorded Latency)
 50.000%    1.23ms
 75.000%    1.80ms
 90.000%    2.50ms
 99.000%    9.10ms
 99.900%   20.00ms
 99.990%   30.00ms
100.000%   35.00ms
Requests/sec:   1000.00
"""
WRK = """Running 10s test @ http://x
  Latency Distribution
     50%  410.00us
     75%  520.00us
     90%  900.00us
     99%    4.20ms
  12000 requests in 10.00s
Requests/sec:   1200.00
"""
BUDGET = """stage, gateway, 0.3ms, 1.2ms
stage, auth, 0.5ms, 4ms
fanout, search shards, 20, 2ms, 15ms
stage, database, 1ms, 12ms, 2
target, p99, 30ms
"""
CODE = """#include <mutex>
void run(std::vector<int>& out, int sock) {
  std::mutex m;
  for (int i = 0; i < n; ++i) {
    auto* p = new Order(i);
    out.push_back(i);
    std::cout << i << std::endl;
    send(sock, buf, len, 0);
  }
  // new Foo() in a comment
  const char* s = "malloc( in a string";
  usleep(100);
}
"""
STRUCTS = """struct Order { char side; double price; int qty; char sym[8]; bool live; };
struct Ring {
  std::atomic<size_t> head;
  std::atomic<size_t> tail;
  Order slots[4];
};
#[repr(C)]
struct Tick { a: u8, b: u64, c: u16 }
"""
PERF = """# Children      Self  Command  Shared Object      Symbol
    45.00%     2.00%  srv      srv                [.] handle
    30.00%    18.00%  srv      libc.so.6          [.] malloc
    20.00%    12.00%  srv      [kernel.kallsyms]  [k] native_queued_spin_lock_slowpath
    10.00%    10.00%  srv      libc.so.6          [.] __memmove_avx_unaligned_erms
     8.00%     8.00%  srv      srv                [.] parse_json
"""
STAT = """ Performance counter stats for './srv':
     1,000.00 msec task-clock
        5,400      context-switches
           12      cpu-migrations
       20,000      page-faults
  3,000,000,000      cycles
  2,100,000,000      instructions
    100,000,000      cache-references
     20,000,000      cache-misses
       1.002 seconds time elapsed
"""
HOST = """BOOT_IMAGE=/vmlinuz-6.8 root=/dev/nvme0n1p2 ro quiet
vm.swappiness = 60
kernel.numa_balancing = 1
net.core.somaxconn = 128
net.ipv4.tcp_slow_start_after_idle = 1
always [madvise] never
/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor:powersave
CPU(s): 16
Thread(s) per core: 2
Adaptive RX: on  TX: on
rx-usecs: 50
current_clocksource: hpet
"""


@pytest.fixture
def llc(env):
    from app import lowlatchat as C
    C._OF.clear()
    C._BLOCK.clear()
    return C


def _hire():
    from app.employee import hire
    hire.hire(T, "lowlatency_eng", trust="seekh")


# ---------------------------------------------------------------- the engine (pure code)
def test_latency_percentiles_compare_and_omission():
    from app.lldesk import latency as L
    one = L.analyse(_samples(9, 5000, tail=40))
    s = one["runs"][0]
    assert s["count"] == 5040 and s["q"]["50"] < s["q"]["99"] < s["q"]["99.9"] <= s["q"]["100"]
    vals = sorted(float(x) for x in _samples(9, 5000, tail=40).split())
    assert s["q"]["99"] == vals[int(0.99 * 5040 + 0.999999) - 1]          # nearest rank
    assert s["reliable"]["99"] == "ok" and s["reliable"]["99.9"] == "few" and s["reliable"]["99.99"] == "none"
    assert any("p99.9 and above rest on fewer than 10 samples" in i["text"] for i in one["issues"])
    two = L.analyse(TWO)
    c = two["compare"][0]
    assert c["verdict"] == "slower" and c["ci99"][0] > 0.1 and 0.25 < c["q"]["99"]["change"] < 0.45 and "slower, beyond the noise" in two["verdict"]
    same = L.analyse(SAME)
    assert same["compare"][0]["verdict"] == "same" and same["compare"][0]["ci99"][0] < 0 < same["compare"][0]["ci99"][1]
    w2 = L.analyse(WRK2)
    assert w2["runs"][0]["tool"] == "wrk2" and w2["runs"][0]["q"]["99"] == 9100 and w2["runs"][0]["q"]["100"] == 35000
    w = L.analyse(WRK)
    assert w["runs"][0]["tool"] == "wrk" and w["runs"][0]["q"]["50"] == 410 and any("coordinated omission" in i["text"] for i in w["issues"])
    pts = L.analyse("p50: 120us\np99: 3.1ms\np99.9 = 9ms\nmax 20ms", target_us=2000, target_q=99)
    assert pts["runs"][0]["q"]["99"] == 3100 and pts["runs"][0]["target"]["ok"] is False and pts["counts"]["bad"] == 1
    co = L.analyse("\n".join(["10"] * 900 + ["5000"] * 5), interval_us=100)
    assert co["corrected"]["added"] == 5 * 49 and co["corrected"]["q"]["99"] > 1000 and co["runs"][0]["q"]["99"] == 10
    assert any("never measured" in i["text"] for i in co["issues"])
    r = random.Random(5)
    bi = [r.gauss(20, 2) for _ in range(3000)] + [r.gauss(200, 15) for _ in range(800)]
    assert len(L.analyse("\n".join(f"{x:.2f}" for x in bi))["runs"][0]["modes"]) == 2
    assert L.analyse("1ms\n2 ms\n500us\n3000ns")["runs"][0]["q"]["100"] == 2000
    for bad in ("hello", "## a\n1\n## b\nnothing here"):
        with pytest.raises(L.LatencyError):
            L.analyse(bad)
    with pytest.raises(L.LatencyError):
        L.analyse("1\n2\n3", unit="parsecs")


def test_budget_layout_code_profile_tuning_ci(tmp_path):
    from app.lldesk import budget as B, ci as C, hotpath as H, layout as Y, profile as P, tuning as U
    b = B.budget(BUDGET)
    names = {s["name"]: s for s in b["stages"]}
    assert b["target"]["us"] == 30000 and b["target"]["ok"] is False and b["q"]["50"] < b["q"]["99"] < b["sum_p99"]
    assert max(b["stages"], key=lambda s: s["gain"])["name"] == "search shards" and abs(names["search shards"]["slow_chance"] - (1 - 0.99 ** 20)) < 1e-9
    assert b == B.budget(BUDGET)                                             # the same seed, the same answer
    assert any(w["what"].startswith("'search shards' to 10") and w["change"] < 0 for w in b["what_if"])
    assert any("hedge 'auth'" in w["what"] for w in b["what_if"]) and any("biggest win" in i["text"] for i in b["issues"])
    for bad in ("", "stage, x, 5ms, 1ms", "stage, x, 1ms, 2ms\nstage, x, 1ms, 2ms", "fly, x, 1, 2"):
        with pytest.raises(B.BudgetError):
            B.budget(bad)
    h = H.check(CODE)
    ids = {f["id"]: f for f in h["findings"]}
    assert h["lang"] == "cpp" and {"lock", "alloc", "endl", "log", "sleep", "vecgrow", "syscall"} <= set(ids)
    assert ids["alloc"]["line"] == 5 and ids["alloc"]["loop"] and not ids["sleep"]["loop"] and sum(1 for f in h["findings"] if f["id"] == "alloc") == 1
    assert H.check("fn main() { for x in 0..9 {\n let s = x.to_string();\n println!(\"{}\", s);\n} }")["lang"] == "rust"
    g = H.check("package main\nfunc h(xs []int) {\n for _, x := range xs {\n  b := make([]byte, 8)\n  defer f()\n }\n}")
    assert g["lang"] == "go" and {"galloc", "gdefer"} <= {f["id"] for f in g["findings"]}
    j = H.check("public class A { void f() { for (int i=0;i<n;i++) { list.add(new Item(i)); } synchronized(this) {} } }")
    assert j["lang"] == "java" and {"jalloc", "jsync"} <= {f["id"] for f in j["findings"]}
    assert H.check("int x = 1;", "cpp")["findings"] == []
    y = Y.analyse(STRUCTS)
    o, ring, tick = y["structs"]
    assert (o["size"], o["padding"], o["best"]["size"]) == (32, 10, 24) and [r["offset"] for r in o["rows"]] == [0, 8, 16, 20, 28]
    assert ring["size"] == 16 + 4 * 32 and any("head, tail share cache line 0" in i["text"] for i in y["issues"])
    assert (tick["size"], tick["best"]["size"]) == (24, 16)
    assert Y.analyse("struct W { long a; char b; };", abi="llp64")["structs"][0]["size"] == 8
    assert Y.analyse("struct P { char a; int b; } __attribute__((packed));")["structs"][0]["size"] == 5
    assert Y.analyse("struct A { alignas(64) std::atomic<int> a; alignas(64) std::atomic<int> b; };")["structs"][0]["size"] == 128
    with pytest.raises(Y.LayoutError):
        Y.analyse("struct X { Mystery m; };")
    p = P.analyse(PERF)
    assert p["kind"] == "perf report" and p["top"][0]["sym"] == "malloc" and [c["key"] for c in p["cats"]][:2] == ["alloc", "lock"]
    f = P.analyse("main;handle;malloc 50\nmain;handle;parse 30\nmain;handle;futex_wait 20\n")
    assert f["kind"] == "folded stacks" and f["samples"] == 100 and abs(f["cats"][0]["share"] - 50) < 1e-9
    s = P.analyse(STAT)
    assert abs(s["stat"]["ipc"] - 0.7) < 1e-9 and any("instructions per cycle" in i["text"] for i in s["issues"])
    with pytest.raises(P.ProfileError):
        P.analyse("hello there")
    u = U.check(HOST)
    t = " ".join(i["text"] for i in u["issues"])
    assert u["counts"]["bad"] == 1 and "hpet" in t and "No CPUs are set apart" in t and "powersave" in t and "swappiness is 60" in t
    assert "Adaptive RX" in t and "rx-usecs is 50" in t and any("isolcpus=managed_irq,domain,2-15" in i["fix"] for i in u["issues"])
    good = U.check("BOOT_IMAGE=/v root=/dev/x ro isolcpus=managed_irq,domain,2-7 nohz_full=2-7 rcu_nocbs=2-7 intel_idle.max_cstate=1 processor.max_cstate=1 skew_tick=1 nmi_watchdog=0\n"
                   "always madvise [never]\nperformance\n")
    assert good["counts"]["warn"] == 0 and good["counts"]["bad"] == 0 and good["isolated"] == list(range(2, 8))
    with pytest.raises(U.TuneError):
        U.check("nothing useful")
    w = C.workflow("./bench --out bench.txt", "make -j", tolerance=10)
    yy = yaml.safe_load(w["yaml"])
    steps = yy["jobs"]["latency"]["steps"]
    assert yy["permissions"] == {"contents": "read"} and "taskset -c 1 ./bench" in steps[3]["run"] and "rm " not in w["yaml"]
    for bad in (dict(bench_cmd=""), dict(bench_cmd="x ${{ secrets.T }}"), dict(bench_cmd="a\nb"), dict(bench_cmd="x", out_file="../x"),
                dict(bench_cmd="x", tolerance=0), dict(bench_cmd="x", unit="ks")):
        with pytest.raises(C.CiError):
            C.workflow(**bad)
    # the compare step: a head 30% slower fails, the same code passes
    (tmp_path / "results").mkdir()
    for i in (1, 2, 3):
        (tmp_path / "results" / f"base-{i}.txt").write_text(_samples(i, 2000))
        (tmp_path / "results" / f"head-{i}.txt").write_text(_samples(i + 10, 2000, 1.3))
    summ = tmp_path / "summary.md"
    r = subprocess.run([sys.executable, "-I", "-c", w["compare"].replace("\n          ", "\n").strip()], cwd=tmp_path,
                       env={"GITHUB_STEP_SUMMARY": str(summ), "PATH": os.environ.get("PATH", "")}, capture_output=True, text=True)
    assert r.returncode == 1 and "slower than the base" in r.stdout and "| head | 3 |" in summ.read_text()
    for i in (1, 2, 3):
        (tmp_path / "results" / f"head-{i}.txt").write_text(_samples(i + 20, 2000))
    r = subprocess.run([sys.executable, "-I", "-c", w["compare"].replace("\n          ", "\n").strip()], cwd=tmp_path,
                       env={"GITHUB_STEP_SUMMARY": str(summ), "PATH": os.environ.get("PATH", "")}, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_hire_chat_wiring_store_and_guards(llc):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert llc.summary(T)["hired"] is False and "Hire me from AI Employees" in llc.greeting(T)
    with pytest.raises(PermissionError):
        llc.do(T, "add", {"kind": "latency", "text": "1\n2\n3"})
    _hire()
    d = llc.summary(T)
    assert d["hired"] and "runs nothing on your machines" in d["foot"] and {n["go"] for n in d["desk"]["needs"]} >= {"latency", "settings"}
    chat = llc.current(T)
    assert llc.is_lowlat(chat["id"]) and llc.owns(T, chat["id"]) and "<lowlat_desk>" in llc.block(T)
    s_ = (root / "server/app/agent/santosh.py").read_text()
    assert "_llc.is_lowlat(conversation_id)" in s_ and "adm.admit_families(_llc.FAMILIES)" in s_
    for f_ in ("callconv.py", "convs.py"):
        assert '"lowlat"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/latency")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "lldesk.js" in r.text
    html = (root / "server/app/static/console/lldesk.html").read_text()
    for x in ("chatkit.js", "lldesk.css", "lldesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/latency')" in (root / "server/app/static/console/v2.js").read_text()
    assert "lowlatency_eng: 'lldesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["lowlatency_eng"]["live"] is True
    from app.agent.tools import FAMILY_OF, HANDLERS
    assert FAMILY_OF["latency_desk"] in llc.FAMILIES and "latency_desk" in HANDLERS
    lt = llc.do(T, "add", {"kind": "latency", "text": TWO})
    assert lt["number"] == "L-0001" and lt["brief"]["bad"] and lt["brief"]["verdict"] == "slower" and lt["title"] == "Latency: before vs after"
    assert any(n["go"] == "latency/" + lt["id"] for n in llc.summary(T)["desk"]["needs"])
    assert llc.summary(T)["desk"]["latency"]["verdict"] == "slower"
    bd = llc.do(T, "add", {"kind": "budget", "text": BUDGET})
    assert bd["number"] == "B-0001" and bd["brief"]["target_ok"] is False and llc.summary(T)["desk"]["budget"]["target_ok"] is False
    hc = llc.do(T, "add", {"kind": "code", "text": CODE})
    assert hc["number"] == "H-0001" and hc["brief"]["lang"] == "C / C++"
    ly = llc.do(T, "add", {"kind": "layout", "text": STRUCTS})
    assert ly["number"] == "S-0001" and ly["brief"]["sharing"] == 1 and ly["title"] == "Layout: Order, Ring, Tick"
    pr = llc.do(T, "add", {"kind": "profile", "text": PERF})
    assert pr["number"] == "P-0001" and pr["brief"]["cat"] == "Allocation and GC"
    tu = llc.do(T, "add", {"kind": "tuning", "text": HOST})
    assert tu["number"] == "T-0001" and tu["brief"]["bad"] and llc.summary(T)["desk"]["tuning"]["issues"] >= 8
    assert llc.do(T, "ci", {})["missing"] is True
    st = llc.do(T, "settings", {"target_us": "2000", "target_q": "99.9", "bench_cmd": "./bench --out bench.txt", "tolerance": "5", "runs": "5", "pin_cpu": "0"})
    assert st["target_us"] == 2000 and st["runs"] == 5 and st["pin_cpu"] is False
    w = llc.do(T, "ci", {})
    assert "p99.9" in w["yaml"] and "seq 1 5" in w["yaml"] and "taskset" not in w["yaml"] and yaml.safe_load(w["yaml"])
    lt2 = llc.do(T, "add", {"kind": "latency", "text": _samples(1, 3000)})
    assert lt2["result"]["target"] == {"q": 99.9, "us": 2000}
    llc.forget(T)
    assert "./bench --out bench.txt" in llc.block(T) and "p99.9 under 2 ms" in llc.block(T)
    mk = llc.do(T, "mark", {"id": lt["id"], "status": "fixed"})
    assert mk["status"] == "fixed" and not any(n["go"] == "latency/" + lt["id"] for n in llc.summary(T)["desk"]["needs"])
    # the tool
    import asyncio
    from app.agent import lowlat_tools as LT
    from app.agent.tools import Ctx
    out = asyncio.run(LT.latency_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="latency", text=TWO))
    assert out["compare"][0]["verdict"] == "slower" and out["runs"][0]["count"] == 6000
    out = asyncio.run(LT.latency_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="layout", text=STRUCTS))
    assert out["structs"][0]["best"]["size"] == 24
    out = asyncio.run(LT.latency_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="ci"))
    assert out["file"] == ".github/workflows/latency.yml"
    # guards
    with pytest.raises(PermissionError):
        llc.do(T, "settings", {"bench_cmd": "my password is hunter2"})
    assert llc.do(T, "add", {"kind": "code", "text": "// password = hunter2\nint main() { for(;;) { malloc(8); } }"})["kind"] == "code"
    for bad in ({"unit": "years"}, {"abi": "ilp32"}, {"line": "48"}, {"tolerance": "500"}, {"bench_cmd": "x ${{ github.token }}"}):
        with pytest.raises(llc.LlDeskError):
            llc.do(T, "settings", bad)
    with pytest.raises(llc.LlDeskError):
        llc.do(T, "add", {"kind": "latency", "text": ""})
    with pytest.raises(llc.LlDeskError):
        llc.do(T, "add", {"kind": "layout", "text": "struct X { Mystery m; };"})
    with pytest.raises(llc.LlDeskError):
        llc.do(T, "nope", {})
    from app.employee import hire as H
    H.pause(T, "lowlatency_eng")
    assert llc.do(T, "get", {"id": lt["id"]})["id"] == lt["id"] and llc.do(T, "ci", {})["yaml"]
    with pytest.raises(PermissionError):
        llc.do(T, "add", {"kind": "latency", "text": "1\n2\n3"})


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def ll_server(llc, monkeypatch):
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


def test_desk_in_a_real_browser(llc, ll_server):
    base, browser, key = ll_server
    shots = os.environ.get("HOOLA_SHOTS")
    errs = []

    def snap(pg, name):
        if shots:
            pg.add_style_tag(content="html,body,#sd,.sd-body,.sd-desk{height:auto!important;max-height:none!important;overflow:visible!important}")
            pg.screenshot(path=f"{shots}/{name}.png", full_page=True)

    def go(pg, route, sel):
        pg.evaluate(f"location.hash = '{route}'")
        pg.wait_for_selector(sel, timeout=30000)

    def submit(pg, form, text, sel):
        pg.eval_on_selector(f"form[data-form={form}] [name=text]", "(el, v) => { el.value = v; el.dispatchEvent(new Event('input', {bubbles: true})); }", text)
        pg.click(f"form[data-form={form}] [type=submit]")
        pg.wait_for_selector(sel, timeout=60000)

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errs.append("console: " + m.text))
    pg.goto(base + "/console/latency")
    pg.wait_for_selector(".llk-starts", timeout=20000)
    snap(pg, "ll-today-empty-1440")
    go(pg, "#/latency", "form[data-form=latency]")
    submit(pg, "latency", "## one\n" + _samples(9, 5000, tail=40), ".llk-hist")
    assert pg.locator(".llk-hist rect.b").count() > 5 and "p99.9" in pg.inner_text(".llk-pq")
    snap(pg, "ll-latency-1440")
    go(pg, "#/latency", "form[data-form=latency]")
    submit(pg, "latency", TWO, ".llk-curve")
    assert "Slower" in pg.inner_text("#llPage") and pg.locator(".llk-curve path").count() == 2
    snap(pg, "ll-compare-1440")
    go(pg, "#/budget", "form[data-form=budget]")
    submit(pg, "budget", BUDGET, ".llk-stages")
    assert pg.locator(".llk-st").count() == 4 and pg.locator(".llk-st.top").count() == 1 and "search shards" in pg.inner_text(".llk-st.top")
    snap(pg, "ll-budget-1440")
    go(pg, "#/code", ".llk-seg")
    submit(pg, "code", CODE, ".llk-src")
    assert "std::endl" in pg.inner_text("#llPage")
    snap(pg, "ll-code-1440")
    go(pg, "#/code", ".llk-seg")
    pg.click("[data-sub=layout]")
    pg.wait_for_selector("form[data-form=layout]", timeout=10000)
    submit(pg, "layout", STRUCTS, ".llk-mem")
    assert pg.locator(".llk-mem").count() == 3 and pg.locator(".llk-cells i.pad").count() >= 3 and "false sharing" in pg.inner_text("#llPage")
    snap(pg, "ll-layout-1440")
    go(pg, "#/profile", "form[data-form=profile]")
    submit(pg, "profile", PERF + "\n" + STAT, ".mk-bars")
    assert "Allocation and GC" in pg.inner_text("#llPage") and "Instructions per cycle" in pg.inner_text(".cs-hero")
    snap(pg, "ll-profile-1440")
    go(pg, "#/tuning", "form[data-form=tuning]")
    submit(pg, "tuning", HOST, ".llk-chips")
    assert "hpet" in pg.inner_text("#llPage") and "CPU isolation" in pg.inner_text("#llPage")
    snap(pg, "ll-tuning-1440")
    go(pg, "#/ci", "text=Set the command")
    go(pg, "#/settings", "form[data-form=settings]")
    pg.fill("form[data-form=settings] [name=bench_cmd]", "./bench --out bench.txt")
    pg.fill("form[data-form=settings] [name=target_us]", "2000")
    pg.click("form[data-form=settings] [type=submit]")
    pg.wait_for_selector("#toast:has-text('Saved')", timeout=20000)
    go(pg, "#/ci", "text=latency.yml")
    assert "./bench --out bench.txt" in pg.inner_text("#llPage")
    snap(pg, "ll-ci-1440")
    go(pg, "#/today", ".llk-list")
    assert "p99" in pg.inner_text(".cs-hero").lower()
    snap(pg, "ll-today-1440")
    pg.evaluate("document.documentElement.dataset.theme = 'dark'")
    snap(pg, "ll-today-dark-1440")
    pg.evaluate("document.documentElement.dataset.theme = 'light'")
    for route, sel in (("#/today", ".llk-list"), ("#/latency", ".llk-item"), ("#/budget", ".llk-item"), ("#/code", ".llk-item"),
                       ("#/profile", ".llk-item"), ("#/tuning", ".llk-item"), ("#/ci", "text=latency.yml"), ("#/settings", "form[data-form=settings]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('#llPage *')].filter(e => !e.closest('pre,textarea,table,svg,.llk-hist,.cs-chart') && e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
    for route in ("#/budget", "#/code"):
        go(pg, route, ".llk-item")
        pg.locator(".llk-item").first.click()
        pg.wait_for_selector(".llk-head", timeout=20000)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        assert w[0] <= w[1] + 1, (route, w)
        snap(pg, "ll-" + route[2:] + "-390")
    assert not errs, errs
