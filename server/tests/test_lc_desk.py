"""COMPILER DESK: the Compiler Construction Engineer's own section, built like the finance desks - its own chat (kind 'langlab')
with the desk block + the language tool in view; Hoola's own parser generator (checks: undefined names, left recursion, loops that
match nothing, choices that can never win; clear errors with a pointer); her interpreter run ONLY in the locked sandbox (clean
errors vs crashes vs endless loops, no server files); golden tests she approves; fuzzing; a model change kept only when no more
tests fail, else a proposal; versions; the zip that runs anywhere; GLOBAL: names in any script, vowel signs included; walked in a
browser."""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import time
import zipfile

import pytest
from fastapi.testclient import TestClient

T = "default"


@pytest.fixture
def lc(env, monkeypatch):
    from app import lcchat as C
    C._OF.clear()
    C._BLOCK.clear()
    return C


def _hire():
    from app.employee import hire
    hire.hire(T, "compiler_eng", trust="seekh")


def _wait(S, lid, secs=60):
    for _ in range(int(secs * 10)):
        L = S.get(T, lid)
        if L["status"] not in ("designing", "improving"):
            return L
        time.sleep(0.1)
    raise AssertionError("still working")


def _calc():
    from app.langlab import service as S
    n, w, g, i, tests = S.STARTERS[0]
    return S, S.create(T, n, w, g, i, "", tests)


# ---------------------------------------------------------------- the engine
def test_grammar_engine_checks_errors_and_any_script():
    from app.langlab import hoola_lang as H
    from app.langlab import service as S
    bad = S.check_grammar('e : e "+" NUMBER | NUMBER ; NUMBER : /\\d+/ ; x : y ;')
    says = " | ".join(x["say"] for x in bad["errors"])
    assert not bad["ok"] and "'y' is used in x but never defined" in says
    lr = S.check_grammar('e : e "+" NUMBER | NUMBER ; NUMBER : /\\d+/ ;')
    assert "left-recursive" in lr["errors"][0]["say"] and "(op item)*" in lr["errors"][0]["say"]
    loop = S.check_grammar('p : ("a"?)* ;')
    assert "loop for ever" in loop["errors"][0]["say"]
    sh = S.check_grammar('a : "=" | "==" ; ')
    assert sh["ok"] and 'can never match' in sh["warnings"][0]["say"]
    assert "rule" in S.check_grammar('a : "x" ; b : "y" ;')["warnings"][0]["say"]
    assert "matches nothing" in S.check_grammar('A : /x*/ ; a : A ;')["errors"][0]["say"]
    assert "not a valid regular expression" in S.check_grammar('A : /(/ ; a : A ;')["errors"][0]["say"]
    g = H.load('%ignore /\\s+/\nprogram : ("let" NAME "=" NUMBER ";")* ;\nNAME : /[^\\W\\d]\\w*/ ;\nNUMBER : /\\d+/ ;')
    for name in ("दाम", "سَلام", "ค่า", "naïve", "имя"):      # vowel signs / harakat / Thai marks / accents / Cyrillic
        assert H.sexp(g.parse(f"let {name} = 1;")) == f"(program {name} 1)", name
    with pytest.raises(H.ParseError) as e:
        g.parse("let let = 2;")                                   # a fixed word is never a NAME
    assert e.value.line == 1 and e.value.col == 5 and "NAME" in e.value.expected and e.value.pointer.endswith("    ^")
    with pytest.raises(H.ParseError) as e:
        g.parse("let x = 1;\nlet y = ;")
    assert (e.value.line, e.value.col) == (2, 9) and "NUMBER" in str(e.value)
    with pytest.raises(H.ParseError):
        H.load('%ignore /\\s+/\na : "let" ;').parse("letter")      # a word matches as a whole word
    assert H.norm_sexp("( a  b\n (c \"d e\") )") == '(a b (c "d e"))'
    import random
    rnd = random.Random(2)
    for _ in range(15):
        g.parse(g.sample(rnd))


def test_hire_chat_block_and_wiring(lc):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert lc.summary(T)["hired"] is False and "Hire me from AI Employees" in lc.greeting(T)
    with pytest.raises(PermissionError):
        lc.do(T, "blank", {"name": "x"})
    _hire()
    d = lc.summary(T)
    assert d["hired"] and "locked sandbox" in d["foot"]
    assert {n["go"] for n in d["desk"]["needs"]} >= {"new"} and len(d["desk"]["starters"]) >= 5
    chat = lc.current(T)
    assert lc.is_lang(chat["id"]) and lc.owns(T, chat["id"])
    assert "<compiler_desk>" in lc.block(T)
    src = (root / "server/app/agent/santosh.py").read_text()
    assert "_lcc.is_lang(conversation_id)" in src and "adm.admit_families(_lcc.FAMILIES)" in src
    for f_ in ("callconv.py", "convs.py"):
        assert '"langlab"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/compiler")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "lcdesk.js" in r.text
    html = (root / "server/app/static/console/lcdesk.html").read_text()
    for x in ("chatkit.js", "lcdesk.css", "lcdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/compiler')" in (root / "server/app/static/console/v2.js").read_text()
    assert "compiler_eng: 'lcdesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["compiler_eng"]["live"] is True
    from app.agent.tools import FAMILY_OF, HANDLERS
    assert FAMILY_OF["lang_lab"] in lc.FAMILIES and "lang_lab" in HANDLERS


def test_sandbox_tests_golden_fuzz_and_zip(lc, tmp_path):
    _hire()
    S, L = _calc()
    assert (L["passed"], L["failed"], L["total"]) == (7, 0, 7), L["last_run"]
    r = S.run_program(T, L["id"], "let a = 3; print a * a + 1;")
    assert r["ok"] and r["ran"] and r["outcome"] == "ok" and r["output"].strip() == "10"
    r = S.run_program(T, L["id"], "print 1 +;")
    assert not r["ok"] and r["error"]["line"] == 1 and "NUMBER" in r["error"]["message"]
    # her interpreter: a clean error, a crash, an endless loop, and the walls of the sandbox are told apart
    crash = ("def run(tree):\n    for st in tree.children:\n        if st.children and getattr(st.children[0], 'text', '') == 'boom':\n"
             "            raise LangError('boom is not allowed', st)\n        if len(st.children) == 1 and getattr(st.children[0], 'text', '') == 'loop':\n"
             "            while True: pass\n        if len(st.children) == 1 and getattr(st.children[0], 'text', '') == 'peek':\n"
             f"            print(open({str(os.path.abspath('app/config.py'))!r}).read()[:20])\n        print(1 / 0)\n")
    L = S.save(T, L["id"], interpreter=crash)
    assert L["version"] == 2
    for prog, want in (("print boom;", "error"), ("print 1;", "crash"), ("print loop;", "timeout"), ("print peek;", "crash")):
        r = S.run_program(T, L["id"], prog)
        assert r["outcome"] == want, (prog, r)
    assert "Sandbox" in S.run_program(T, L["id"], "print peek;")["message"]       # the server's own files stay closed
    L = S.restore(T, L["id"], 1)
    assert L["version"] == 3 and L["passed"] == 7
    # golden approval: a test with no expectation needs her yes, then passes
    L = S.test_save(T, L["id"], {"name": "Big", "src": "print 6 * 7;", "kind": "output", "expect": ""})
    new = [x for x in L["last_run"]["results"] if x["status"] == "new"]
    assert len(new) == 1 and L["last_run"]["new"] == 1
    L = S.test_accept(T, L["id"], new[0]["id"])
    assert L["passed"] == 8 and next(t for t in L["tests"] if t["name"] == "Big")["expect"].strip() == "42"
    L = S.test_save(T, L["id"], {"name": "Tree", "src": "print 1 + 2;", "kind": "tree", "expect": "(program (statement (expr 1 + 2)))"})
    assert L["passed"] == 9 and L["failed"] == 0
    f = S.fuzz(T, L["id"])
    assert f["made"] >= 10 and f["unreadable"] == 0 and f["crashes"] == 0 and f["ok"] and f["kb_per_s"] > 0
    name, data = S.export_zip(T, L["id"])
    z = zipfile.ZipFile(io.BytesIO(data))
    files = {n.split("/", 1)[1] for n in z.namelist()}
    assert {"hoola_lang.py", "grammar.hg", "interpreter.py", "cli.py", "run_tests.py", "tests.json", "SPEC.md", "README.md",
            "editor/package.json", "railroad/program.svg"} <= files
    z.extractall(tmp_path)
    d = tmp_path / name[:-4]
    (d / "p.calculator").write_text("let x = 4; print x * 2;", encoding="utf-8")
    out = subprocess.run([sys.executable, "cli.py", "p.calculator"], cwd=d, capture_output=True, text=True, timeout=60)
    assert out.returncode == 0 and out.stdout.strip() == "8", out.stderr
    out = subprocess.run([sys.executable, "run_tests.py"], cwd=d, capture_output=True, text=True, timeout=60)
    assert out.returncode == 0 and "9 passed, 0 failed" in out.stdout, out.stdout + out.stderr
    tm = json.loads(z.read(f"{name[:-4]}/editor/syntaxes/calculator.tmLanguage.json"))
    assert any(p["name"] == "keyword.control" and "let" in p["match"] for p in tm["patterns"])
    md = S.spec_md(S.get(T, L["id"]))
    assert "## Grammar" in md and "railroad/expr.svg" in md and "`let`" in md
    assert "<svg" in S.railroads(T, L["id"])[0]["svg"]


def test_design_improve_proposal_and_guards(lc, monkeypatch):
    from app.langlab import ai
    from app.langlab import service as S
    _hire()
    good = {"name": "Greeter", "purpose": "Say hello", "ext": "hi", "start": "program",
            "grammar": '%ignore /\\s+/\nprogram : ("hello" NAME ";")* ;\nNAME : /[^\\W\\d]\\w*/ ;',
            "interpreter": "def run(tree):\n    for t in tree.toks('NAME'):\n        print('Hello, ' + t.text)\n",
            "tests": [{"name": "One", "src": "hello Asha;", "kind": "output", "expect": "Hello, Asha"},
                      {"name": "Bad", "src": "hello ;", "kind": "error", "expect": ""}]}
    answers = [json.dumps({**good, "grammar": 'program : program "x" | "x" ;'}), "```json\n" + json.dumps(good) + "\n```"]
    calls = []

    def fake(system, prompt, max_tokens=12000, job="langlab"):
        calls.append(prompt)
        return answers.pop(0)
    monkeypatch.setattr(ai, "ask", fake)
    L = lc.do(T, "design", {"words": "a tiny greeting language", "examples": "hello Asha;"})
    assert L["status"] in ("designing", "ready")          # the fake model answers at once
    L = _wait(S, L["id"])
    assert L["status"] == "ready" and L["name"] == "Greeter" and (L["passed"], L["total"]) == (2, 2)
    assert "left-recursive" in calls[1]                       # the checks went back to the model for one fix round
    # a change that makes more tests fail is held as a proposal; her tap applies it
    worse = {**good, "interpreter": "def run(tree):\n    print('nope')\n", "summary": "Shorter greetings"}
    monkeypatch.setattr(ai, "ask", lambda *a, **k: json.dumps(worse))
    L2 = S.improve(T, L["id"], "shorter greetings", wait=True)
    assert L2["kept"] is False and L2["proposal"]["failed"] == 1 and L2["version"] == L["version"]
    assert any("waits for you" in n["say"] for n in lc.summary(T)["desk"]["needs"])
    L3 = lc.do(T, "proposal", {"id": L["id"], "use": True})
    assert L3["version"] == L["version"] + 1 and not L3["proposal"] and L3["failed"] == 1
    better = {**good, "summary": "Back to Hello"}
    monkeypatch.setattr(ai, "ask", lambda *a, **k: json.dumps(better))
    L4 = S.improve(T, L["id"], "", wait=True)                 # empty words = make the failing tests pass
    assert L4["kept"] is True and L4["failed"] == 0
    # guards
    with pytest.raises(PermissionError):
        lc.do(T, "settings", {"target": "my password is hunter2"})
    with pytest.raises(lc.LcDeskError):
        lc.do(T, "settings", {"limit_s": 99})
    with pytest.raises(lc.LcDeskError):
        lc.do(T, "nope", {})
    assert lc.do(T, "settings", {"target": "compiler"})["target"] == "compiler" and "compile it" in (lc.forget(T) or lc.block(T))
    from app.employee import hire
    hire.pause(T, "compiler_eng")
    assert lc.do(T, "parse", {"id": L["id"], "src": "hello Ravi;"})["ok"]        # reads still work while paused
    with pytest.raises(PermissionError):
        lc.do(T, "blank", {"name": "x"})


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def lc_server(lc, monkeypatch):
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


def test_desk_in_a_real_browser(lc, lc_server):
    base, browser, key = lc_server
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
    pg.goto(base + "/console/compiler")
    pg.wait_for_selector("text=Needs you", timeout=20000)
    snap(pg, "lc-today-empty-1440")
    # start from the ready example -> the language opens on its playground
    pg.click("[data-starter='0']")
    pg.wait_for_selector("form[data-form=play]", timeout=60000)
    pid = pg.evaluate("location.hash.split('/')[2]")
    pg.fill("form[data-form=play] [name=src]", "let x = 2 + 3 * 4;\nprint x;")
    pg.wait_for_selector(".lc-tree", timeout=20000)
    pg.click("form[data-form=play] [type=submit]")
    pg.wait_for_selector("pre.lc-pre.out:has-text('14')", timeout=60000)
    snap(pg, "lc-play-1440")
    pg.fill("form[data-form=play] [name=src]", "print 1 +;")
    pg.wait_for_selector(".lc-err", timeout=20000)
    assert "column 10" in pg.inner_text(".lc-err")
    # grammar: checks + railroad diagrams
    go(pg, f"#/langs/{pid}/grammar", ".lc-rr svg")
    assert "No problems found" in pg.inner_text("#lcPage")
    snap(pg, "lc-grammar-1440")
    # tests: add one with no expectation, keep its answer
    go(pg, f"#/langs/{pid}/tests", ".lc-sum")
    pg.click("[data-edit='new']")
    pg.fill("form[data-form=test] [name=name]", "Answer")
    pg.fill("form[data-form=test] [name=src]", "print 6 * 7;")
    pg.click("form[data-form=test] [type=submit]")
    pg.wait_for_selector("#toast:has-text('Saved and run')", timeout=60000)
    pg.click("details.lc-test:has-text('Answer') summary")
    pg.click("[data-accept]")
    pg.wait_for_selector("#toast:has-text('Kept as the expected answer')", timeout=60000)
    assert "8 pass" in pg.inner_text(".lc-sum")
    snap(pg, "lc-tests-1440")
    go(pg, f"#/langs/{pid}/check", "[data-fuzz]")
    pg.click("[data-fuzz]")
    pg.wait_for_selector("text=Reading speed", timeout=60000)
    snap(pg, "lc-check-1440")
    go(pg, f"#/langs/{pid}/release", "pre.lc-spec")
    snap(pg, "lc-release-1440")
    go(pg, f"#/langs/{pid}/versions", "text=Versions")
    go(pg, f"#/langs/{pid}/code", "form[data-form=code]")
    snap(pg, "lc-code-1440")
    go(pg, "#/new", "form[data-form=design]")
    snap(pg, "lc-new-1440")
    go(pg, "#/today", ".lc-card")
    snap(pg, "lc-today-1440")
    for route, sel in (("#/today", ".lc-card"), ("#/new", "form[data-form=design]"), ("#/langs", ".lc-card"),
                       (f"#/langs/{pid}/play", "form[data-form=play]"), (f"#/langs/{pid}/grammar", ".lc-rr svg"),
                       (f"#/langs/{pid}/tests", ".lc-sum"), (f"#/langs/{pid}/release", ".lc-files"), ("#/settings", "form[data-form=settings]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('#lcPage *')].filter(e => !e.closest('.lc-svg,pre,textarea') && e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
        if route.endswith("/tests"):
            snap(pg, "lc-tests-390")
        if route.endswith("/play"):
            snap(pg, "lc-play-390")
    snap(pg, "lc-settings-390")
    assert not errs, errs
