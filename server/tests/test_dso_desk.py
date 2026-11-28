"""DEVSECOPS ENGINEER DESK: the DevSecOps Engineer's own section, built like the finance desks - its own chat (kind 'devsecops') with
the desk block and the DevSecOps tool in view; GitHub Actions workflows read (unpinned actions, script injection, pull_request_target
running the PR's code, permissions, workflow-wide secrets, self-hosted runners on PRs, curl | bash); SBOMs (CycloneDX and SPDX,
licence families, deny / allow lists with wildcards, gaps, several versions); manifests (unpinned, git sources, extra index, lookalike
names, install scripts); repository guard rails (an unprotected branch, reviews, force pushes, push protection); fix times pinned to
their arithmetic; keys refused; the CI pipeline guard really fails (and passes itself); walked in a browser."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest
import yaml
from fastapi.testclient import TestClient

T = "default"

WF = """## .github/workflows/pr.yml
name: pr
on: pull_request_target
env:
  NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - uses: some-org/setup-tool@v2
      - uses: good-org/action@0123456789abcdef0123456789abcdef01234567
      - run: echo "${{ github.event.pull_request.title }}"
      - run: curl -sSL https://get.example.com/install.sh | bash
## .github/workflows/ok.yml
name: ok
on: [push, pull_request]
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false
      - uses: my-org/helper@v1
      - run: make test
## .github/workflows/self.yml
name: self
on: pull_request
permissions: write-all
jobs:
  a:
    runs-on: [self-hosted, linux]
    timeout-minutes: 5
    steps:
      - run: echo hi
"""
CDX = {"bomFormat": "CycloneDX", "specVersion": "1.5", "components": [
    {"name": "lodash", "version": "4.17.21", "purl": "pkg:npm/lodash@4.17.21", "licenses": [{"license": {"id": "MIT"}}], "supplier": {"name": "OpenJS"}},
    {"name": "lodash", "version": "4.17.15", "purl": "pkg:npm/lodash@4.17.15", "licenses": [{"license": {"id": "MIT"}}]},
    {"name": "readline-x", "version": "2.0.0", "purl": "pkg:npm/readline-x@2.0.0", "licenses": [{"license": {"id": "GPL-3.0-only"}}]},
    {"name": "mongo-thing", "version": "1.0.0", "purl": "pkg:npm/mongo-thing@1.0.0", "licenses": [{"license": {"id": "AGPL-3.0-or-later"}}]},
    {"name": "dual", "version": "1.0.0", "purl": "pkg:npm/dual@1.0.0", "licenses": [{"expression": "GPL-2.0-only OR MIT"}]},
    {"name": "mpl-lib", "version": "3.1", "purl": "pkg:npm/mpl-lib@3.1", "licenses": [{"license": {"id": "MPL-2.0"}}]},
    {"name": "mystery", "version": "", "licenses": []}]}
SPDX = {"spdxVersion": "SPDX-2.3", "packages": [
    {"name": "requests", "versionInfo": "2.32.3", "licenseConcluded": "Apache-2.0", "supplier": "Organization: PSF", "externalRefs": [{"referenceType": "purl", "referenceLocator": "pkg:pypi/requests@2.32.3"}]},
    {"name": "chardet", "versionInfo": "5.2.0", "licenseConcluded": "NOASSERTION", "licenseDeclared": "LGPL-2.1-or-later", "externalRefs": [{"referenceType": "purl", "referenceLocator": "pkg:pypi/chardet@5.2.0"}]},
    {"name": "secretlib", "versionInfo": "1.0", "licenseConcluded": "NOASSERTION", "licenseDeclared": "NOASSERTION"}]}
DEPS = """## package.json
{"dependencies": {"react": "^18.2.0", "lodahs": "4.17.21", "express": "4.19.2", "mylib": "github:acme/mylib"}, "devDependencies": {"jest": "^29.7.0"}, "scripts": {"postinstall": "node setup.js"}}
## package-lock.json
{"lockfileVersion": 3, "packages": {"": {}, "node_modules/esbuild": {"version": "0.21.5", "hasInstallScript": true}, "node_modules/react": {"version": "18.3.1"}}}
## requirements.txt
--extra-index-url https://pypi.acme.internal/simple
requests==2.32.3
reqeusts==2.31.0
flask>=2
git+https://github.com/acme/x.git#egg=x
## go.mod
module example.com/app
require (
  github.com/pkg/errors v0.9.1
)
replace github.com/pkg/errors => ../errors
## Cargo.toml
[dependencies]
serde = "1.0"
mycrate = { git = "https://github.com/acme/mycrate" }
"""
REPO = {"full_name": "acme/shop", "visibility": "public", "default_branch": "main", "allow_forking": True,
        "security_and_analysis": {"secret_scanning": {"status": "enabled"}, "secret_scanning_push_protection": {"status": "disabled"}, "dependabot_security_updates": {"status": "enabled"}}}
PROT = {"required_pull_request_reviews": {"required_approving_review_count": 1, "dismiss_stale_reviews": False, "require_code_owner_reviews": True, "require_last_push_approval": False},
        "required_status_checks": {"strict": True, "contexts": ["test"]}, "enforce_admins": {"enabled": False}, "allow_force_pushes": {"enabled": True},
        "allow_deletions": {"enabled": False}, "required_signatures": {"enabled": False}, "required_linear_history": {"enabled": True}, "required_conversation_resolution": {"enabled": False}}
REPO_TXT = "## repo\n" + json.dumps(REPO) + "\n## protection\n" + json.dumps(PROT)
METRICS = """id,severity,opened,closed,team
V-1,critical,2026-11-01,2026-11-03,web
V-2,critical,2026-10-01,2026-10-20,web
V-3,high,2026-09-01,,web
V-4,high,2026-10-01,2026-11-10,data
V-5,high,2026-11-20,,data
V-6,medium,2026-05-01,,data
V-7,low,2026-11-25,,web
"""


@pytest.fixture
def dso(env):
    from app import dsochat as C
    C._OF.clear()
    C._BLOCK.clear()
    return C


def _hire():
    from app.employee import hire
    hire.hire(T, "devsecops_eng", trust="seekh")


# ---------------------------------------------------------------- the engine (pure code)
def test_workflows_and_ci(tmp_path):
    from app.dsodesk import ci as CI, workflows as W
    r = W.analyse(WF, "my-org")
    a = [i["area"] for i in r["issues"]]
    fl = {f["path"]: f["flags"] for f in r["files"]}
    assert "Runs the pull request's code with secrets" in a and "Event text an outsider controls is put into the workflow" in a
    assert "Self-hosted runner on pull requests" in a and "permissions: write-all" in a and "Secrets for every job" in a
    # only the untrusted, tag-pinned action is asked to pin: actions/ and her own org are trusted, the SHA one is pinned
    un = [i["fn"] for i in r["issues"] if i["area"].startswith("A third-party action")]
    assert un == [".github/workflows/pr.yml:12"] and r["unpinned"] == 1 and r["pinned"] == 1
    assert "no permissions" in fl[".github/workflows/pr.yml"] and "no permissions" not in fl[".github/workflows/ok.yml"]
    assert "no timeout" not in fl[".github/workflows/ok.yml"] and "token kept on disk" not in fl[".github/workflows/ok.yml"]
    assert r["counts"]["bad"] == 4
    with pytest.raises(W.WorkflowError):
        W.analyse("name: x\nsteps: []")
    # the guard: it passes itself, fails a bad workflow with the right lines, and trusts her owners
    w = CI.workflow("warn", "my-org")
    y = yaml.safe_load(w["yaml"])
    assert w["file"] == ".github/workflows/pipeline-guard.yml" and y.get("on", y.get(True))["pull_request"]["paths"] == [".github/workflows/**"] and y["permissions"] == {"contents": "read"}
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / "g.py").write_text(y["jobs"]["guard"]["steps"][1]["run"])
    (tmp_path / ".github/workflows/pipeline-guard.yml").write_text(w["yaml"])
    run = lambda *a_: subprocess.run([sys.executable, "g.py", *a_], cwd=tmp_path, capture_output=True, text=True, env={**os.environ, "GITHUB_STEP_SUMMARY": str(tmp_path / "s.md")})   # noqa: E731
    assert run().returncode == 0
    for part in WF.split("## ")[1:]:
        name, body = part.split("\n", 1)
        (tmp_path / name.strip()).write_text(body)
    p = run()
    assert p.returncode == 1 and "pr.yml,line=12" in p.stdout and "prt-checkout" in p.stdout and "self.yml" in p.stdout and "ok.yml" not in p.stdout
    assert "Pipeline guard" in (tmp_path / "s.md").read_text()
    for bad in ({"fail_level": "info"}, {"trusted_owners": "a b"}, {"runner": "x y"}):
        with pytest.raises(CI.CiError):
            CI.workflow(**bad)


def test_sbom_and_deps():
    from app.dsodesk import deps as D, sbom as S
    r = S.analyse(json.dumps(CDX), deny="AGPL-*, SSPL-*")
    by = {(c["name"], c["version"]): c for c in r["rows"]}
    assert r["format"] == "CycloneDX 1.5" and r["components"] == 7
    assert r["families"] == {"permissive": 3, "weak": 1, "strong": 2, "unknown": 1}
    assert "denied licence" in by[("mongo-thing", "1.0.0")]["flags"] and by[("readline-x", "2.0.0")]["family"] == "strong"
    assert by[("dual", "1.0.0")]["family"] == "permissive" and set(by[("mystery", "")]["flags"]) >= {"no licence", "no version", "no purl"}
    assert r["multi"] == [["lodash", ["4.17.15", "4.17.21"]]] or r["multi"] == [("lodash", ["4.17.15", "4.17.21"])]
    a = {i["area"] for i in r["issues"]}
    assert {"Denied licence", "Strong copyleft", "No licence"} <= a
    r2 = S.analyse(json.dumps(SPDX), allow="Apache-2.0, MIT, BSD-*")
    b2 = {c["name"]: c for c in r2["rows"]}
    assert r2["format"] == "SPDX-2.3" and b2["chardet"]["license"] == "LGPL-2.1-or-later" and b2["chardet"]["family"] == "weak"
    assert "not on the allow list" in b2["chardet"]["flags"] and b2["secretlib"]["family"] == "unknown" and not b2["requests"]["flags"]
    with pytest.raises(S.SbomError):
        S.analyse('{"x": 1}')
    d = D.analyse(DEPS)
    f = {(x["eco"], x["name"]): x["flags"] for x in d["rows"]}
    assert f[("npm", "react")] == ["not pinned"] and f[("npm", "express")] == [] and f[("npm", "jest")] == []
    assert f[("npm", "lodahs")] == ["looks like lodash"] and f[("npm", "mylib")] == ["from git or a URL"]
    assert f[("pypi", "reqeusts")] == ["looks like requests"] and f[("pypi", "flask")] == ["not pinned"] and f[("pypi", "requests")] == []
    assert f[("pypi", "(index)")] == ["extra index"] and f[("npm", "esbuild")] == ["runs an install script"]
    assert f[("go", "github.com/pkg/errors")] == [] and any(x["flags"] == ["local replace"] for x in d["rows"] if x["eco"] == "go")
    assert f[("cargo", "mycrate")] == ["from git or a URL"] and f[("cargo", "serde")] == ["range (Cargo.lock pins it)"]
    assert d["lookalike"] == 2 and "Extra package index" in {i["area"] for i in d["issues"]}
    assert D.analyse(DEPS, pin_dev=True)["rows"] and ["not pinned"] == next(x["flags"] for x in D.analyse(DEPS, pin_dev=True)["rows"] if x["name"] == "jest")
    with pytest.raises(D.DepsError):
        D.analyse("")


def test_repo_and_metrics():
    from app.dsodesk import metrics as M, repo as R
    r = R.analyse(REPO_TXT, min_reviews=2, need_checks="test, Pipeline guard")
    ck = {c["name"]: c["ok"] for c in r["checks"]}
    assert r["repo"] == "acme/shop" and r["protected"] is True
    assert ck["Secret scanning"] is True and ck["Push protection"] is False and ck["Reviews"] is False and ck["No force pushes"] is False
    assert ck["Code owners"] is True and ck["Admins included"] is False and ck["Forks"] is None
    a = {i["area"] for i in r["issues"]}
    assert {"No force pushes", "Reviews", "Push protection", "Required check missing"} <= a and r["counts"]["bad"] == 1
    nr = R.analyse('## repo\n' + json.dumps(REPO) + '\n## protection\n{"message": "Branch not protected", "documentation_url": "x"}')
    assert nr["protected"] is False and nr["counts"]["bad"] == 1 and "not protected" in nr["verdict"]
    with pytest.raises(R.RepoError):
        R.analyse('{"x": 1}')
    m = M.analyse(METRICS, {"critical": 7, "high": 30, "medium": 90, "low": 180}, today="2026-11-28")
    per = {p["sev"]: p for p in m["per"]}
    assert m["findings"] == 7 and m["open"] == 4 and m["late"] == 2
    assert per["critical"]["mttr"] == (2 + 19) / 2 and per["critical"]["in_sla"] == 0.5 and per["high"]["open_late"] == 1 and per["high"]["mttr"] == 40
    assert per["medium"]["oldest"] == 211 and m["buckets"] == {"0-7": 1, "8-30": 1, "31-90": 1, "91-180": 0, "180+": 1}
    assert [t["team"] for t in m["teams"]][:2] == ["data", "web"] or m["teams"][0]["late"] >= m["teams"][1]["late"]
    assert m["weeks"][-1]["backlog"] == 4 and m["weeks"][0]["week"] == "2026-04-27"
    with pytest.raises(M.MetricsError):
        M.analyse("id,severity,opened,closed\nx,high,2026-11-02,2026-11-01")


def test_hire_chat_wiring_store_and_guards(dso):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert dso.summary(T)["hired"] is False and "Hire me from AI Employees" in dso.greeting(T)
    with pytest.raises(PermissionError):
        dso.do(T, "add", {"kind": "workflows", "text": WF})
    _hire()
    d = dso.summary(T)
    assert d["hired"] and d["foot"] == dso.FOOT and {n["go"] for n in d["desk"]["needs"]} >= {"workflows", "settings"}
    chat = dso.current(T)
    assert dso.is_devsecops(chat["id"]) and dso.owns(T, chat["id"]) and "<devsecops_desk>" in dso.block(T)
    s_ = (root / "server/app/agent/santosh.py").read_text()
    assert "_dso.is_devsecops(conversation_id)" in s_ and "adm.admit_families(_dso.FAMILIES)" in s_
    for f_ in ("callconv.py", "convs.py"):
        assert '"devsecops"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/devsecops")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "dsodesk.js" in r.text
    html = (root / "server/app/static/console/dsodesk.html").read_text()
    for x in ("chatkit.js", "dsodesk.css", "dsodesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/devsecops')" in (root / "server/app/static/console/v2.js").read_text()
    assert "devsecops_eng: 'dsodesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["devsecops_eng"]["live"] is True
    from app.agent import admit
    from app.agent.tools import FAMILY_OF, HANDLERS
    assert FAMILY_OF["devsecops_desk"] in dso.FAMILIES and "devsecops_desk" in HANDLERS and "devsecops" in admit.EXTRA_KEYS
    w1 = dso.do(T, "add", {"kind": "workflows", "text": WF})
    assert w1["number"] == "W-0001" and w1["brief"]["files"] == 3 and w1["brief"]["bad"] and w1["title"].startswith("Workflows: ")
    json.dumps(w1)
    assert any(n["go"] == "workflows/" + w1["id"] for n in dso.summary(T)["desk"]["needs"])
    s1 = dso.do(T, "add", {"kind": "sbom", "text": json.dumps(CDX)})
    assert s1["number"] == "S-0001" and s1["brief"]["strong"] == 2 and s1["brief"]["bad"]
    d1 = dso.do(T, "add", {"kind": "deps", "text": DEPS})
    assert d1["number"] == "D-0001" and d1["brief"]["lookalike"] == 2
    r1 = dso.do(T, "add", {"kind": "repo", "text": REPO_TXT})
    assert r1["number"] == "R-0001" and r1["brief"]["repo"] == "acme/shop"
    m1 = dso.do(T, "add", {"kind": "metrics", "text": METRICS, "inputs": {"today": "2026-11-28"}})
    assert m1["number"] == "M-0001" and m1["brief"]["late"] == 2
    st = dso.do(T, "settings", {"trusted_owners": "my-org", "deny_licenses": "AGPL-*, GPL-*", "min_reviews": 2, "sla_high": 14, "fail_level": "bad"})
    assert st["trusted_owners"] == "my-org" and st["min_reviews"] == 2 and st["fail_level"] == "bad"
    dso.forget(T)
    assert "trusted action owners my-org" in dso.block(T) and "guard fails on bad" in dso.block(T)
    assert "'my-org/'" in dso.do(T, "ci", {})["yaml"]
    w2 = dso.do(T, "add", {"kind": "workflows", "text": WF})
    assert w2["brief"]["unpinned"] == 1
    s2 = dso.do(T, "add", {"kind": "sbom", "text": json.dumps(CDX)})
    assert sum(1 for c in s2["result"]["rows"] if "denied licence" in c["flags"]) == 2
    m2 = dso.do(T, "add", {"kind": "metrics", "text": METRICS, "inputs": {"today": "2026-11-28"}})
    assert m2["result"]["sla"]["high"] == 14
    mk = dso.do(T, "mark", {"id": w1["id"], "status": "fixed"})
    assert mk["status"] == "fixed" and not any(n["go"] == "workflows/" + w1["id"] for n in dso.summary(T)["desk"]["needs"])
    import asyncio
    from app.agent import devsecops_tools as DT
    from app.agent.tools import Ctx, ToolError
    out = asyncio.run(DT.devsecops_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="repo", text=REPO_TXT))
    assert out["number"] == "R-0002" and out["passed"] < out["total"]
    out = asyncio.run(DT.devsecops_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="ci"))
    assert out["file"] == ".github/workflows/pipeline-guard.yml"
    with pytest.raises(PermissionError):
        dso.do(T, "settings", {"need_checks": "my password is hunter2"})
    with pytest.raises(PermissionError):
        dso.do(T, "add", {"kind": "workflows", "text": WF + "\n# AKIAABCDEFGHIJKLMNOP"})
    with pytest.raises(ToolError):
        asyncio.run(DT.devsecops_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="deps", text="-----BEGIN OPENSSH PRIVATE KEY-----\nxx"))
    for bad in ({"fail_level": "info"}, {"deny_licenses": "GPL 3!"}, {"min_reviews": 9}, {"sla_critical": 100}, {"trusted_owners": "a b"}):
        with pytest.raises((dso.DsoDeskError, PermissionError)):
            dso.do(T, "settings", bad)
    with pytest.raises(dso.DsoDeskError):
        dso.do(T, "add", {"kind": "sbom", "text": ""})
    with pytest.raises(dso.DsoDeskError):
        dso.do(T, "nope", {})
    from app.employee import hire as H
    H.pause(T, "devsecops_eng")
    assert dso.do(T, "get", {"id": w1["id"]})["id"] == w1["id"] and dso.do(T, "ci", {})["yaml"]
    with pytest.raises(PermissionError):
        dso.do(T, "add", {"kind": "sbom", "text": json.dumps(CDX)})


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def dso_server(dso, monkeypatch):
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


def test_desk_in_a_real_browser(dso, dso_server):
    base, browser, key = dso_server
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
    pg.goto(base + "/console/devsecops")
    pg.wait_for_selector(".dok-path", timeout=20000)
    snap(pg, "dso-today-empty-1440")
    go(pg, "#/workflows", "form[data-form=workflows]")
    put(pg, "workflows", "trusted_owners", "my-org")
    submit(pg, "workflows", WF, "table.dok-t")
    t = pg.inner_text("#dsoPage")
    assert "some-org/setup-tool" in t and "runs PR code with secrets" in t and pg.locator(".dok-x").count() >= 1
    snap(pg, "dso-workflows-1440")
    go(pg, "#/sbom", "form[data-form=sbom]")
    submit(pg, "sbom", json.dumps(CDX), "table.dok-t")
    assert "denied licence" in pg.inner_text("#dsoPage") and "Strong copyleft" in pg.inner_text("#dsoPage")
    snap(pg, "dso-sbom-1440")
    go(pg, "#/dependencies", "form[data-form=deps]")
    submit(pg, "deps", DEPS, "table.dok-t")
    assert "looks like lodash" in pg.inner_text("#dsoPage") and "extra index" in pg.inner_text("#dsoPage")
    snap(pg, "dso-dependencies-1440")
    go(pg, "#/repository", "form[data-form=repo]")
    put(pg, "repo", "min_reviews", "2")
    submit(pg, "repo", REPO_TXT, ".dok-head")
    assert "Force pushes are allowed" in pg.inner_text("#dsoPage")
    snap(pg, "dso-repository-1440")
    go(pg, "#/fix-times", "form[data-form=metrics]")
    put(pg, "metrics", "today", "2026-11-28")
    submit(pg, "metrics", METRICS, "table.dok-t")
    assert "Past the fix time" in pg.inner_text("#dsoPage") and pg.locator(".cm-line").count() == 1
    snap(pg, "dso-fix-times-1440")
    go(pg, "#/settings", "form[data-form=settings]")
    pg.fill("form[data-form=settings] [name=trusted_owners]", "my-org")
    pg.select_option("form[data-form=settings] [name=fail_level]", "bad")
    pg.click("form[data-form=settings] [type=submit]")
    pg.wait_for_selector("#toast:has-text('Saved')", timeout=20000)
    go(pg, "#/ci", "text=pipeline-guard.yml")
    assert "serious findings only" in pg.inner_text("#dsoPage")
    snap(pg, "dso-ci-1440")
    go(pg, "#/today", ".dok-list")
    snap(pg, "dso-today-1440")
    for route, sel in (("#/today", ".dok-list"), ("#/workflows", ".dok-item"), ("#/sbom", ".dok-item"), ("#/dependencies", ".dok-item"), ("#/repository", ".dok-item"),
                       ("#/fix-times", ".dok-item"), ("#/ci", "text=pipeline-guard.yml"), ("#/settings", "form[data-form=settings]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('body *')].filter(e => !e.closest('pre,textarea,table,svg') && e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
    for route in ("#/workflows", "#/sbom", "#/dependencies", "#/repository", "#/fix-times"):
        go(pg, route, ".dok-item")
        pg.locator(".dok-item").first.click()
        pg.wait_for_selector(".dok-head", timeout=20000)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 8).map(e => e.tagName + '.' + e.className + ':' + Math.round(e.getBoundingClientRect().right) + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
        snap(pg, "dso-" + route[2:] + "-390")
    assert not errs, errs
