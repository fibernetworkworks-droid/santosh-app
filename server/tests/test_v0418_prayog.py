"""Prayogshala L0 + L1: the 3D practical lab. Every catalogue lab passes the Lab Scene Language checker and its own NCERT
check (the kernel's simulated reading vs the textbook formula, 1 %); every kernel's JavaScript twin gives the SAME numbers
as the Python one (the phone runs the JS); the checker refuses anything that is not data; routes, tool and wiring."""
import asyncio
import copy
import json
import math
import shutil
import subprocess
from pathlib import Path

import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.prayog import catalog, kernels as KN, lsl
from app.prayog import service as S
from tests.test_life import conv_ctx

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static" / "prayog"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(not NODE, reason="node is not installed")


def _labs():
    return [b() for b in catalog.BUILDERS]


# ------------------------------------------------------------------------------------------- the catalogue
def test_catalogue_has_22_physics_labs_all_checked():
    labs = _labs()
    assert len(labs) == 22 and len({l["id"] for l in labs}) == 22
    for lab in labs:
        lsl.check(lab)
        r = lsl.run_check(lab)
        assert r["ok"], (lab["id"], r)
        assert r["error"] <= 0.01
    # v0.781 the catalogue grew past the first 22 through lab packs (app/prayog/labs/*.py): every builder of every pack
    # must open - nothing silently left out (this pin said 22 for ever and went red the day the first pack landed)
    every = {b()["id"] for b in S._all_builders()}
    S.labs.cache_clear()
    assert set(S.labs()) == every, sorted(every - set(S.labs()))[:20]


def test_ncert_checks_compare_against_independent_formulas():
    """Spot checks with the numbers written out by hand, not through the lab file."""
    p = KN.params_for("pendulum", {"L": 1.0, "theta0": 0.05})
    assert KN.Pendulum.measure(p)["T"] == pytest.approx(2 * math.pi * math.sqrt(1 / 9.8), rel=1e-3)
    p = KN.params_for("resonance", {"f": 512, "Tc": 20})
    m = KN.Resonance.measure(p)
    assert 2 * 512 * (m["l2"] - m["l1"]) == pytest.approx(343.2, rel=2e-3)
    p = KN.params_for("prism", {"n": 1.5})
    dm = KN.Prism.measure(p)["dm"]
    assert math.sin((math.radians(60) + dm) / 2) / math.sin(math.radians(30)) == pytest.approx(1.5, rel=1e-3)
    p = KN.params_for("mirror", {"R": 0.3, "u": 0.45})
    assert KN.Mirror.measure(p)["v"] == pytest.approx(0.225, rel=1e-3)          # 1/v + 1/u = 1/f, f = 15 cm
    assert KN.Mirror.measure(p)["m"] == pytest.approx(-0.5, rel=1e-3)
    p = KN.params_for("lens", {"u": 0.6})
    assert KN.Lens.measure(p)["v"] == pytest.approx(0.3, rel=0.01)                # thin lens f = 20 cm
    p = KN.params_for("slab", {"t": 0.06, "n": 1.33})
    assert KN.Slab.measure(p)["app"] == pytest.approx(0.06 / 1.33, rel=1e-4)


def test_circuit_solver_obeys_kirchhoff_and_the_bridge():
    net = {"nodes": 2, "els": [{"id": "E", "kind": "V", "a": 1, "b": 0, "value": 6.0},
                               {"id": "R1", "kind": "R", "a": 1, "b": 2, "value": 2.0},
                               {"id": "R2", "kind": "R", "a": 2, "b": 0, "value": 4.0}]}
    cfg = {"net": net}
    s = KN.Circuit.init({}, cfg)
    v = KN.Circuit.view(s, {}, cfg)
    assert v["I_R1"] == pytest.approx(1.0) and v["V_R2"] == pytest.approx(4.0) and v["I_E"] == pytest.approx(1.0)
    lab = catalog.meter_bridge()
    for rk, sx in ((3.0, 7.0), (10.0, 5.0)):
        p = KN.params_for("circuit", {**lab["params"], "Rk": rk, "Sx": sx})
        l = KN.Circuit.measure(p, {**lab["cfg"], "measure": {"mode": "null", "param": "lj", "var": "I_G"}})["lj"]
        assert rk * (1 - l) / l == pytest.approx(sx, rel=1e-6)                    # S = R (100 - l) / l


def test_learner_table_results_come_from_code():
    p = KN.params_for("pendulum", {})
    rows = [{"L": 1.0, "T": 2.0071}, {"L": 0.5, "T": 1.4192}]
    assert KN.calc("pendulum_g", rows, p) == pytest.approx(9.8, rel=2e-3)
    assert KN.calc("res_v", [{"h": 0.4908}, {"h": 0.1556}], KN.params_for("resonance", {})) == pytest.approx(343.2, rel=1e-3)
    pot = KN.params_for("circuit", {"Rb": 10.0})
    assert KN.calc("pot_r", [{"k2": 0, "l": 0.375}, {"k2": 1, "l": 0.341}], pot) == pytest.approx(10 * (0.375 - 0.341) / 0.341)
    assert KN.calc("ohm_R", [{"V": "", "I": 1}], {}) == 0.0                         # a blank cell is skipped, never a crash


# ------------------------------------------------------------------------------------------- JS twin
_TWIN = r"""
const H = require(process.argv[2]);
// v0.781 every kernel pack (static/prayog/packs/*.js) registers into the same HoolaKernels, exactly as the page loads it
const fs = require('fs'), path = require('path'), dir = path.join(path.dirname(process.argv[2]), 'packs');
for (const f of fs.readdirSync(dir).filter(n => n.endsWith('.js')).sort())
  new Function('require', fs.readFileSync(path.join(dir, f), 'utf8')).call({ HoolaKernels: H }, require);
const fx = JSON.parse(require('fs').readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(fx.map(f => {
  if (f.calc) return { calc: H.CALCS[f.calc].fn(f.rows, H.paramsFor(f.kernel, f.params)) };
  const k = H.K[f.kernel], p = H.paramsFor(f.kernel, f.params), cfg = f.cfg || {};
  const s = k.init(p, cfg); for (let i = 0; i < f.steps; i++) k.step(s, p, f.dt, cfg);
  const out = { view: k.view(s, p, cfg) };
  if (!f.skip_measure) out.measure = k.measure(p, cfg);
  return out;
})));
"""


def _close(a, b, path=""):
    if isinstance(a, bool) or isinstance(b, bool):
        assert bool(a) == bool(b), path
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        assert abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b)), (path, a, b)
    elif isinstance(a, dict):
        for k in a:
            assert k in b, (path, k)
            _close(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list):
        assert len(a) == len(b), (path, len(a), len(b))
        for i, (x, y) in enumerate(zip(a, b)):
            _close(x, y, f"{path}[{i}]")


def _fixtures():
    fx = []
    from app.prayog import service as _S
    for lab in [b() for b in _S._all_builders()]:     # every lab of every pack, at its own settings, as the phone runs it
        base = dict(lab.get("params") or {})
        fx.append({"kernel": lab["kernel"], "params": base, "cfg": lab.get("cfg") or {}, "steps": 25, "dt": 0.04,
                   "skip_measure": lab["kernel"] == "circuit" and not (lab.get("cfg") or {}).get("measure")})
        chk = lab["check"]
        if lab["kernel"] == "circuit" and chk.get("measure"):
            fx.append({"kernel": "circuit", "params": {**base, **(chk.get("params") or {})},
                       "cfg": {**lab["cfg"], "measure": chk["measure"]}, "steps": 3, "dt": 0.05})
    fx.append({"kernel": "induction", "params": {"v": -1.2}, "steps": 40, "dt": 0.02})
    fx.append({"kernel": "mirror", "params": {"convex": 1.0, "u": 0.3}, "steps": 1, "dt": 0.1})
    fx.append({"kernel": "lens", "params": {"u": 0.12}, "steps": 1, "dt": 0.1})              # virtual image
    fx.append({"kernel": "prism", "params": {"i": 0.3}, "steps": 1, "dt": 0.1})              # total internal reflection
    fx.append({"kernel": "gauge", "params": {"kind": 1.0, "L": 0.00137, "ze": 0.00002}, "steps": 1, "dt": 0.1})
    core = {"pendulum_g": "pendulum", "spring_k_static": "spring", "spring_k_shm": "spring", "incline_mu": "incline",
            "stokes_eta": "stokes", "cooling_k": "cooling", "boyle_pv": "boyle", "mix_c": "mixtures", "res_v": "resonance",
            "sono_mu": "sonometer", "mirror_f": "mirror", "lens_f": "lens", "prism_n": "prism", "slab_n": "slab",
            "induct_ratio": "induction", "gauge_mean": "gauge"}
    for name in ("ohm_R", "bridge_S", "pot_r", "diode_knee", "rc_tau"):
        core[name] = "circuit"
    for name, spec in KN.CALCS.items():
        if name not in core:                          # a pack's calc: fed through the kernel of a lab that names it
            k = next((lab["kernel"] for lab in [b() for b in _S._all_builders()] if name in json.dumps(lab)), None)
            if not k:
                continue
            core[name] = k
        rows = [{k: 0.3 + 0.1 * i + 0.01 * j for j, k in enumerate(spec["needs"])} for i in range(3)]
        if name == "pot_r":
            rows = [{"k2": 0, "l": 0.4}, {"k2": 1, "l": 0.35}]
        fx.append({"calc": name, "kernel": core[name],
                   "params": {"Rb": 10.0} if name == "pot_r" else {}, "rows": rows})
    return fx


def _python(f):
    if f.get("calc"):
        return {"calc": KN.calc(f["calc"], f["rows"], KN.params_for(f["kernel"], f["params"]))}
    K = KN.KERNELS[f["kernel"]]
    p = KN.params_for(f["kernel"], f["params"])
    cfg = f.get("cfg") or {}
    s = K.init(p, cfg)
    for _ in range(f["steps"]):
        K.step(s, p, f["dt"], cfg)
    out = {"view": K.view(s, p, cfg)}
    if not f.get("skip_measure"):
        out["measure"] = K.measure(p, cfg)
    return out


@needs_node
def test_javascript_twin_gives_the_same_numbers(tmp_path):
    script = tmp_path / "twin.js"
    script.write_text(_TWIN)
    fx = _fixtures()
    run = subprocess.run([NODE, str(script), str(STATIC / "kernels.js")], input=json.dumps(fx), capture_output=True,
                         text=True, timeout=180)
    assert run.returncode == 0, run.stderr
    js = json.loads(run.stdout)
    assert len(js) == len(fx)
    for f, j in zip(fx, js):
        _close(_python(f), j, f.get("calc") or f["kernel"])


def test_both_twins_know_the_same_kernels_and_calcs():
    import re
    src = (STATIC / "kernels.js").read_text()
    packs = "\n".join(p.read_text() for p in sorted((STATIC / "packs").glob("*.js")))   # v0.781 the packs' own twins
    for name in KN.KERNELS:
        assert f"K.{name} = " in src or re.search(rf"\b{re.escape(name)}\b", packs), name
    for name in KN.CALCS:
        assert f"    {name}: {{" in src or re.search(rf"\b{re.escape(name)}\b", packs), name


@needs_node
def test_runtime_files_parse():
    for f in ("kernels.js", "lab3d.js", "sw.js"):
        r = subprocess.run([NODE, "--check", str(STATIC / f)], capture_output=True, text=True)
        assert r.returncode == 0, (f, r.stderr)


# ------------------------------------------------------------------------------------------- the checker refuses
def _bad(mutate, word):
    lab = copy.deepcopy(catalog.pendulum())
    mutate(lab)
    with pytest.raises(lsl.LabError) as e:
        lsl.check(lab)
    assert word in str(e.value), str(e.value)


def test_checker_refuses_anything_that_is_not_data():
    _bad(lambda l: l.update(script="alert(1)"), "unknown key")
    _bad(lambda l: l["bodies"][0].update(onload="x()"), "unknown key")
    _bad(lambda l: l["bodies"].append({"id": "h", "kind": "html", "text": "<b>"}), "kind")
    _bad(lambda l: l.update(kernel="rocket"), "unknown kernel")
    _bad(lambda l: l["bodies"][4].update(bind={"x": "made_up"}), "is not a kernel var")
    _bad(lambda l: l["knobs"][0].update(param="nope"), "is not a kernel param")
    _bad(lambda l: l["knobs"][0].update(value=999), "value between")
    _bad(lambda l: l.update(sources=[]), "source")
    _bad(lambda l: l.pop("check"), "NCERT formula")
    _bad(lambda l: l["bodies"][4].update(pos=[0, 1e9, 0]), "out of range")
    _bad(lambda l: l["bodies"][4].update(pos=[0, float("nan"), 0]), "needs a number")
    _bad(lambda l: l["bodies"].extend({"id": f"s{i}", "kind": "spring", "a": [0, 0, 0], "b": [0, 1, 0]} for i in range(30)), "triangles")
    _bad(lambda l: l["table"].update(calc="spring_k_shm", columns=[{"id": "x", "label": "x", "from": "manual"}]), "columns")
    _bad(lambda l: l["table"]["columns"][0].update({"from": "inst:nope"}), "from")
    _bad(lambda l: l["tour"][0].update(say="x" * 400), "say")
    _bad(lambda l: l["questions"][0].update(answer=9), "answer")
    _bad(lambda l: l["bodies"].append({"id": "r", "kind": "rope", "a": "ghost", "b": [0, 0, 0]}), "listed earlier")
    _bad(lambda l: l["tour"].append({"say": "x", "set": {"L": 9999}}), "out of the knob's range")


def test_checker_refuses_a_broken_circuit():
    lab = copy.deepcopy(catalog.ohm())
    lab["cfg"]["net"]["els"][2]["a"] = 99
    with pytest.raises(lsl.LabError, match="node"):
        lsl.check(lab)
    lab = copy.deepcopy(catalog.ohm())
    lab["cfg"]["net"]["els"].append({"id": "E", "kind": "R", "a": 1, "b": 2, "value": 1})
    with pytest.raises(lsl.LabError, match="unique"):
        lsl.check(lab)


def test_a_lab_that_fails_its_ncert_check_is_left_out(monkeypatch):
    def broken():
        lab = catalog.pendulum()
        lab["id"] = "broken-pendulum"
        lab["check"]["textbook"] = "spring_T"            # the wrong formula: 2 s vs 0.63 s
        return lab
    S.labs.cache_clear()
    n = len(S.labs())
    monkeypatch.setattr(catalog, "BUILDERS", catalog.BUILDERS + (broken,))
    S.labs.cache_clear()
    try:
        assert "broken-pendulum" not in S.labs() and len(S.labs()) == n
    finally:
        S.labs.cache_clear()


HINGLISH = ("kijiye", "dekhiye", "nahi", "chahiye", "mein ", " hai", "aur ", "raftaar", "guna", "chhupa", "taapmaan",
            "pratirodh", "kiranen", "Chalao", "Andaaza", "Shoonya", "Siddhant", "dhoondh")


def test_everything_the_learner_sees_is_english():
    """Owner, 1 Nov 2026: "FIRST MAKE ENTIRE THING IN ENGLISH"."""
    def walk(v, where):
        if isinstance(v, str):
            low = f" {v} "
            for w in HINGLISH:                           # whole words only: 'var hair' in code is not ' hai'
                pat = r"(?<![A-Za-z])" + re.escape(w.strip()) + r"(?![A-Za-z])"
                assert not re.search(pat, low), (where, w, v)
        elif isinstance(v, dict):
            for k, x in v.items():
                walk(x, f"{where}.{k}")
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(x, f"{where}[{i}]")
    for lab in _labs():
        assert lab["lang"] == "en-IN"
        walk(lab, lab["id"])
    for f in ("lab3d.js", "index.html", "lab.html", "studio/studio.js"):
        walk((STATIC / f).read_text(), f)
    for f in sorted((STATIC / "exp").glob("*.js")):
        walk(f.read_text(), f.name)
    walk((ROOT.parent / "lib" / "ui" / "prayog_screen.dart").read_text(), "prayog_screen.dart")
    walk(S.NOTE, "NOTE")


def test_every_string_is_plain_text():
    def walk(v):
        if isinstance(v, str):
            assert "<script" not in v.lower() and "javascript:" not in v.lower(), v
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    for lab in _labs():
        walk(lab)
    src = (STATIC / "lab3d.js").read_text()
    assert ".innerHTML = '" not in src.replace(".innerHTML = '';", "")      # only clearing, never writing text as HTML
    assert "eval(" not in src and "new Function" not in src


# ------------------------------------------------------------------------------------------- routes, tool, wiring
def _client():
    from app.prayog.api import make_router
    app = FastAPI()
    app.include_router(make_router())
    return TestClient(app)


def test_routes_are_public_read_only():
    c = _client()
    d = c.get("/api/prayog/labs", params={"variants": False}).json()
    assert len(d["labs"]) == min(100, len(S.labs())) and "simulation" in d["note"]   # every set-up, paged at 100
    assert "convex-lens" in {r["id"] for r in c.get("/api/prayog/labs", params={"q": "lens", "variants": False}).json()["labs"]}
    lab = c.get("/api/prayog/labs/simple-pendulum").json()["lab"]
    assert lab["kernel"] == "pendulum" and lab["check"]["textbook"] == "pendulum_T"
    assert c.get("/api/prayog/labs/nahi-hai").status_code == 404
    r = c.get("/api/prayog/three.js")
    assert r.status_code == 200 and "THREE" in r.text[:2000] and "javascript" in r.headers["content-type"]
    assert c.get("/prayog", follow_redirects=False).headers["location"] == "/static/prayog/index.html"
    assert c.post("/api/prayog/labs").status_code == 405


def test_main_app_serves_the_labs_without_a_key(env):
    from app.main import app
    c = TestClient(app)
    assert c.get("/api/prayog/labs").status_code == 200
    assert c.get("/static/prayog/lab.html").status_code == 200
    assert "lab3d.js" in c.get("/static/prayog/lab.html").text


def test_prayog_tool(env):
    from app.agent import tools as T
    from app.agent.prayog_tools import prayog

    assert "prayog" in T.HANDLERS and T.FAMILY_OF["prayog"] == "prayog"
    ctx = conv_ctx()
    r = asyncio.run(prayog(ctx, "find", q="pendulum"))
    assert r["labs"][0]["id"] == "simple-pendulum" and r["labs"][0]["url"].endswith("/static/prayog/lab.html?id=simple-pendulum")
    assert asyncio.run(prayog(ctx, "find", q="convex lens kaise"))["labs"][0]["id"] == "convex-lens"   # loose match
    card = asyncio.run(prayog(ctx, "open", id="meter-bridge"))
    assert card["url"] and card["steps"] and "Unknown wire" not in " ".join(card["knobs"])                 # hidden knobs stay hidden
    chk = asyncio.run(prayog(ctx, "check", id="resonance-tube"))
    assert chk["ok"] and chk["error_percent"] < 1
    with pytest.raises(T.ToolError):
        asyncio.run(prayog(ctx, "open", id="nope"))
    assert asyncio.run(prayog(ctx, "all"))["count"] >= 22        # set-ups + every variant


def test_wiring():
    from app.agent import admit, prompts
    from app.employee import roles
    from app import voice

    assert "prayog" in admit._match("mujhe dikhao pendulum kaise kaam karta hai")
    assert "prayog" in admit._match("ek practical dikhao")
    assert "prayog" in roles.READ
    assert "prayog" in roles.DUTIES["tutoring"]["tools"]
    assert "prayog" in voice.VOICE_TOOL_NAMES and "prayog" in voice.VOICE_VIA_KAAM
    assert "PRACTICAL LAB (Prayogshala)" in prompts.__dict__.get("SYSTEM", "") or "Prayogshala" in Path(prompts.__file__).read_text()
    html = (ROOT / "app" / "static" / "console" / "v2.html").read_text()
    js = (ROOT / "app" / "static" / "console" / "v2.js").read_text()
    assert 'id="labframe"' in html and "['lab','Lab']" in js and "/static/prayog/index.html" in js
    dart = (ROOT.parent / "lib" / "ui" / "prayog_screen.dart").read_text()
    assert "/api/prayog/labs" in dart and "/static/prayog/lab.html" in dart
    assert "PrayogScreen(app: app)" in (ROOT.parent / "lib" / "ui" / "profile_screen.dart").read_text()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.850.0"


# ------------------------------------------------------------------------------------------- the realistic studio
def test_every_lab_has_a_studio_module():
    have = {f.stem for f in (STATIC / "exp").glob("*.js")}
    assert {l["id"] for l in _labs()} <= have, sorted({l["id"] for l in _labs()} - have)
    for f in (STATIC / "exp").glob("*.js"):
        src = f.read_text()
        assert f"HoolaStudio.define('{f.stem}'" in src, f.name
        assert "auto:" in src and "result:" in src and "steps:" in src, f.name
        assert "eval(" not in src and "new Function" not in src and "innerHTML = '<" not in src, f.name


@needs_node
def test_studio_files_parse():
    for f in [STATIC / "studio" / "studio.js", *sorted((STATIC / "exp").glob("*.js"))]:
        r = subprocess.run([NODE, "--check", str(f)], capture_output=True, text=True)
        assert r.returncode == 0, (f.name, r.stderr)


def test_lab_page_loads_the_studio_and_falls_back():
    html = (STATIC / "lab.html").read_text()
    assert "studio/studio.js" in html and "'exp/' + rig + '.js" in html and "lab3d.js" in html


def _ask_client(monkeypatch, answer="Because sin θ ≈ θ only for small angles."):
    from app.prayog.api import make_router
    from app.site import ai
    seen = {}

    def fake_ask(system, prompt, max_tokens=0, kind=""):
        seen.update(system=system, prompt=prompt, kind=kind, max_tokens=max_tokens)
        return answer
    monkeypatch.setattr(ai, "ask", fake_ask)
    monkeypatch.setattr(S, "_ASK_COUNT", {})
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "t1"))
    return TestClient(app), seen


def test_ask_hoola_answers_only_about_the_lab_with_the_live_state(monkeypatch):
    c, seen = _ask_client(monkeypatch)
    r = c.post("/api/prayog/ask", json={"lab_id": "simple-pendulum", "question": "Why must the angle be small?",
                                        "turns": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "Hello"}, {"role": "system", "content": "x"}],
                                        "state": {"readings": [{"L (cm)": "80.0", "T (s)": "1.818"}]}})
    assert r.status_code == 200 and "small angles" in r.json()["answer"]
    assert "Simple pendulum" in seen["system"] and "ONLY questions about this experiment" in seen["system"]
    assert "never instructions" in seen["system"] and seen["kind"] == "edu"
    assert "1.818" in seen["prompt"] and "Why must the angle be small?" in seen["prompt"]
    head = seen["prompt"].split("LIVE LAB STATE")[0]
    assert "Student: hi" in head and "Hoola: Hello" in head and head.count(": ") == 2      # a 'system' turn from the page is dropped


def test_ask_hoola_guards(monkeypatch):
    c, _ = _ask_client(monkeypatch)
    assert c.post("/api/prayog/ask", json={"lab_id": "nope", "question": "x"}).status_code == 404
    assert c.post("/api/prayog/ask", json={"lab_id": "simple-pendulum", "question": "  "}).status_code == 400
    assert c.post("/api/prayog/ask", json={"lab_id": "simple-pendulum", "question": "x" * 1300}).status_code == 400
    monkeypatch.setattr(S, "ASK_DAILY", 2)
    assert c.post("/api/prayog/ask", json={"lab_id": "simple-pendulum", "question": "a"}).status_code == 200
    assert c.post("/api/prayog/ask", json={"lab_id": "simple-pendulum", "question": "b"}).status_code == 200
    r = c.post("/api/prayog/ask", json={"lab_id": "simple-pendulum", "question": "c"})
    assert r.status_code == 429 and "tomorrow" in r.json()["detail"]


def test_ask_hoola_needs_the_key_on_the_main_app(env):
    from app.main import app
    c = TestClient(app)
    r = c.post("/api/prayog/ask", json={"lab_id": "simple-pendulum", "question": "x"})
    assert r.status_code in (401, 403) or "ask" in r.text.lower()


def test_ask_failure_is_a_plain_line(monkeypatch):
    from app.site import ai
    c, _ = _ask_client(monkeypatch)
    def boom(*a, **k):
        raise RuntimeError("model down")
    monkeypatch.setattr(ai, "ask", boom)
    r = c.post("/api/prayog/ask", json={"lab_id": "simple-pendulum", "question": "x"})
    assert r.status_code == 503 and "model down" not in r.text
