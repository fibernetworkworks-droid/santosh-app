"""SECURITY ENGINEER DESK: the Security Engineer's own section, built like the finance desks - its own chat (kind 'seceng') with
the desk block and the security tool in view; scanner reports triaged (SARIF / Trivy / Grype / Semgrep / ZAP / CSV merged, the
CVSS-style severity mapping, upgrades that close most, new / fixed against a baseline, due dates pinned to the fix-time rules);
headers and cookies checked; a certificate chain made here and checked (expiry, names, order, a weak key); JWTs decoded with
their signatures never stored; risky code found in a diff's added lines only, secrets stored cut; keys refused; the CI security
gate really fails; walked in a browser."""
from __future__ import annotations

import base64
import datetime as dt
import json
import os
import subprocess
import sys

import pytest
import yaml
from fastapi.testclient import TestClient

T = "default"

TRIVY = {"Results": [{"Target": "package-lock.json", "Vulnerabilities": [
    {"VulnerabilityID": "CVE-2024-0001", "PkgName": "lodash", "InstalledVersion": "4.17.20", "FixedVersion": "4.17.21", "Severity": "HIGH", "Title": "Prototype pollution"},
    {"VulnerabilityID": "CVE-2024-0002", "PkgName": "lodash", "InstalledVersion": "4.17.20", "FixedVersion": "4.17.19, 4.17.22", "Severity": "CRITICAL", "Title": "Command injection"},
    {"VulnerabilityID": "CVE-2023-0003", "PkgName": "minimist", "InstalledVersion": "1.2.5", "FixedVersion": "1.2.6", "Severity": "MEDIUM", "Title": "x"}]},
    {"Target": "Dockerfile", "Misconfigurations": [{"ID": "DS002", "Severity": "HIGH", "Title": "Image user should not be root", "Status": "FAIL"},
                                                  {"ID": "DS001", "Severity": "LOW", "Title": "ok", "Status": "PASS"}]}]}
GRYPE = {"matches": [{"vulnerability": {"id": "CVE-2024-0001", "severity": "Medium", "fix": {"versions": ["4.17.21"]}}, "artifact": {"name": "lodash", "version": "4.17.20", "locations": [{"path": "/app/package-lock.json"}]}}]}
SARIF = {"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "CodeQL", "rules": [{"id": "py/sql-injection", "properties": {"security-severity": "8.8", "tags": ["security", "external/cwe/cwe-089"]}},
                                                                                        {"id": "py/clear-text-logging", "properties": {"security-severity": "5.0"}}]}},
                                       "results": [{"ruleId": "py/sql-injection", "message": {"text": "SQL built from user input"}, "locations": [{"physicalLocation": {"artifactLocation": {"uri": "app/db.py"}, "region": {"startLine": 42}}}]},
                                                   {"ruleId": "py/clear-text-logging", "message": {"text": "Logged password"}, "locations": [{"physicalLocation": {"artifactLocation": {"uri": "app/log.py"}, "region": {"startLine": 7}}}]}]}]}
BASE = {"Results": [{"Target": "package-lock.json", "Vulnerabilities": [
    {"VulnerabilityID": "CVE-2023-0003", "PkgName": "minimist", "InstalledVersion": "1.2.5", "FixedVersion": "1.2.6", "Severity": "MEDIUM"},
    {"VulnerabilityID": "CVE-2022-9999", "PkgName": "axios", "InstalledVersion": "0.21.0", "FixedVersion": "0.21.1", "Severity": "HIGH"}]}]}
REPORT = "## trivy\n" + json.dumps(TRIVY) + "\n## grype\n" + json.dumps(GRYPE) + "\n## codeql\n" + json.dumps(SARIF)
HEADERS = """HTTP/1.1 301 Moved Permanently
Location: https://shop.example.com/

HTTP/2 200
server: nginx/1.18.0
x-powered-by: Express
strict-transport-security: max-age=300
content-security-policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.example.com
access-control-allow-origin: *
access-control-allow-credentials: true
set-cookie: sessionid=abc123; Path=/
set-cookie: __Host-csrf=x; Secure; Path=/; Domain=shop.example.com; SameSite=Strict
set-cookie: theme=dark; Secure; SameSite=Lax
"""
GOOD_HEADERS = """HTTP/2 200
strict-transport-security: max-age=63072000; includeSubDomains; preload
content-security-policy: default-src 'self'; script-src 'nonce-abc' 'strict-dynamic'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'
x-content-type-options: nosniff
referrer-policy: strict-origin-when-cross-origin
permissions-policy: camera=()
set-cookie: __Host-sid=abc; Secure; HttpOnly; Path=/; SameSite=Lax
"""
DIFF = """diff --git a/app/api.py b/app/api.py
--- a/app/api.py
+++ b/app/api.py
@@ -1,4 +1,10 @@
 import os
-cur.execute("SELECT 1")
+data = pickle.loads(body)
+cur.execute(f"SELECT * FROM users WHERE id={uid}")
+requests.get(url, verify=False)
+API_KEY = "sk_live_abcdefghijk123"
+password = "changeme"
+x = model.eval()
+token = str(random.random())
 print("ok")
diff --git a/web/app.js b/web/app.js
--- a/web/app.js
+++ b/web/app.js
@@ -5,0 +6,2 @@
+el.innerHTML = userText;
+const h = crypto.createHash('md5');
"""


def _certs(days_left=20, weak=False, names=("shop.example.com", "*.example.com"), leaf_life=90):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec, rsa
    from cryptography.hazmat.primitives.serialization import Encoding
    from cryptography.x509.oid import NameOID
    now = dt.datetime(2026, 11, 28, tzinfo=dt.timezone.utc)
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test Issuing CA")])
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name).public_key(ca_key.public_key()).serial_number(1)
          .not_valid_before(now - dt.timedelta(days=400)).not_valid_after(now + dt.timedelta(days=3000))
          .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True).sign(ca_key, hashes.SHA256()))
    lk = rsa.generate_private_key(public_exponent=65537, key_size=1024 if weak else 2048)
    leaf = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, names[0])])).issuer_name(ca_name)
            .public_key(lk.public_key()).serial_number(2).not_valid_before(now + dt.timedelta(days=days_left - leaf_life)).not_valid_after(now + dt.timedelta(days=days_left))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName(n) for n in names]), critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True).sign(ca_key, hashes.SHA256()))
    return leaf.public_bytes(Encoding.PEM).decode(), ca.public_bytes(Encoding.PEM).decode()


def _jwt(h, p, sig="c2lnbmF0dXJlLXRoYXQtaXMtc2VjcmV0"):
    e = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")   # noqa: E731
    return f"{e(h)}.{e(p)}.{sig}"


NOW = dt.datetime(2026, 11, 28, tzinfo=dt.timezone.utc).timestamp()
TOKENS = "\n".join([
    _jwt({"alg": "none", "typ": "JWT"}, {"sub": "1", "iat": NOW - 60}, ""),
    _jwt({"alg": "HS256", "jku": "https://evil.example/keys", "kid": "../../keys/a"}, {"sub": "2", "iat": NOW, "exp": NOW + 7 * 86400, "email": "a@b.c", "password": "x"}),
    _jwt({"alg": "RS256", "kid": "k1"}, {"sub": "3", "iss": "https://id.example", "aud": "api", "iat": NOW - 600, "exp": NOW + 3000})])


@pytest.fixture
def sec(env):
    from app import secchat as C
    C._OF.clear()
    C._BLOCK.clear()
    return C


def _hire():
    from app.employee import hire
    hire.hire(T, "security_eng", trust="seekh")


# ---------------------------------------------------------------- the engine (pure code)
def test_findings():
    from app.secdesk import findings as F
    r = F.analyse(REPORT, scan_date="2026-11-28")
    rows = {f["rule"]: f for f in r["rows"]}
    # the same CVE on the same package from Trivy and Grype is one finding, at the worse severity, with both tools
    assert r["raw"] == 7 and r["findings"] == 6 and r["merged"] == 1
    assert rows["CVE-2024-0001"]["sev"] == "high" and set(rows["CVE-2024-0001"]["tools"]) == {"Trivy", "Grype"}
    # SARIF security-severity mapped the CVSS way: 8.8 high, 5.0 medium; a PASS misconfiguration is not a finding
    assert rows["py/sql-injection"]["sev"] == "high" and rows["py/sql-injection"]["where"] == "app/db.py:42" and rows["py/clear-text-logging"]["sev"] == "medium"
    assert "DS001" not in rows and rows["DS002"]["sev"] == "high"
    assert r["counts_sev"] == {"critical": 1, "high": 3, "medium": 2, "low": 0, "info": 0}
    # one upgrade closes both lodash findings: to the highest version any of them needs
    up = r["upgrades"][0]
    assert up["pkg"] == "lodash" and up["to"] == "4.17.22" and up["closes"] == 2 and up["worst"] == "critical"
    # due dates = scan date + her days
    assert rows["CVE-2024-0002"]["due"] == "2026-12-05" and rows["CVE-2024-0001"]["due"] == "2026-12-28"
    r2 = F.analyse(json.dumps(TRIVY) + "\n## baseline\n" + json.dumps(BASE), {"critical": 3}, "2026-11-28")
    st = {f["rule"]: f["status"] for f in r2["rows"]}
    assert st["CVE-2023-0003"] == "open" and st["CVE-2024-0001"] == "new" and [f["rule"] for f in r2["fixed"]] == ["CVE-2022-9999"]
    assert r2["new"] == 3 and "due" not in next(f for f in r2["rows"] if f["rule"] == "CVE-2023-0003")
    assert next(f for f in r2["rows"] if f["rule"] == "CVE-2024-0002")["due"] == "2026-12-01"
    assert any(i["area"] == "New serious" for i in r2["issues"])
    sem = {"results": [{"check_id": "python.lang.eval", "path": "a.py", "start": {"line": 3}, "extra": {"severity": "ERROR", "message": "eval", "metadata": {"cwe": ["CWE-95"]}}}]}
    zap = {"site": [{"@name": "https://x", "alerts": [{"pluginid": "10038", "name": "CSP not set", "riskcode": "2", "cweid": "693", "instances": [{"uri": "https://x/"}, {"uri": "https://x/a"}]}]}]}
    r3 = F.analyse("## s\n" + json.dumps(sem) + "\n## z\n" + json.dumps(zap) + "\n## c\nid,severity,file,line\nX-1,Critical,src/a.go,9\n")
    assert r3["kinds"] == ["Semgrep", "ZAP", "CSV"] and r3["counts_sev"]["critical"] == 1 and r3["counts_sev"]["high"] == 1 and r3["counts_sev"]["medium"] == 1
    assert next(f for f in r3["rows"] if f["tool"] == "ZAP")["cwe"] == "CWE-693"
    with pytest.raises(F.FindingsError):
        F.analyse('{"nothing": 1}')


def test_headers_and_certs():
    from app.secdesk import certs as CE, headers as H
    r = H.analyse(HEADERS, "https://shop.example.com")
    a = [i["area"] for i in r["issues"]]
    assert "HSTS" in a and "CSP scripts" in a and "Framing" in a and "CORS" in a and a.count("Version shown") == 1
    ck = {c["name"]: c for c in r["cookies"]}
    assert ck["sessionid"]["session"] and set(ck["sessionid"]["flags"]) == {"no Secure", "no HttpOnly", "no SameSite"}
    assert "__Host- rules broken" in ck["__Host-csrf"]["flags"] and not ck["theme"]["flags"]
    assert r["hops"][0]["status"] == 301 and r["status"] == 200 and r["counts"]["bad"] >= 2
    g = H.analyse(GOOD_HEADERS, "https://shop.example.com")
    assert g["passed"] == g["total"] and g["counts"]["bad"] == 0 and g["counts"]["warn"] == 0 and not g["cookies"][0]["flags"]
    with pytest.raises(H.HeadersError):
        H.analyse("")
    leaf, ca = _certs(days_left=20)
    c = CE.analyse(leaf + ca, "shop.example.com, api.example.com, a.b.example.com, other.org", warn_days=30, today="2026-11-28")
    assert c["count"] == 2 and c["chain_ok"] and c["leaf_days"] == 20 and c["certs"][0]["key"] == "RSA 2048" and c["certs"][1]["role"] == "root"
    assert [x["ok"] for x in c["cover"]] == [True, True, False, False]
    assert any(i["area"] == "Expires soon" for i in c["issues"]) and sum(1 for i in c["issues"] if i["area"] == "Name") == 2
    bad = CE.analyse(ca + leaf, today="2026-11-28")
    assert any(i["area"] == "Order" for i in bad["issues"]) and not bad["chain_ok"]
    weak, _ = _certs(days_left=-3, weak=True, leaf_life=500)
    w = CE.analyse(weak, today="2026-11-28")
    wa = [i["area"] for i in w["issues"]]
    assert "Expired" in wa and "Weak key" in wa and "Too long" in wa and "Intermediates" in wa
    with pytest.raises(CE.CertError):
        CE.analyse("-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----")


def test_tokens_code_ci(tmp_path):
    from app.secdesk import ci as CI, code as C, tokens as TO
    r = TO.analyse(TOKENS, max_hours=24, now="2026-11-28T00:00:00", expect_alg="RS256")
    f = {t["n"]: t["flags"] for t in r["rows"]}
    assert "alg none" in f[1] and "no expiry" in f[1]
    assert {"unexpected alg", "jku", "odd kid", "long life", "sensitive claims"} <= set(f[2])
    assert f[3] == [] and r["rows"][2]["life_h"] == 1.0
    assert any(i["area"] == "Algorithm" and i["sev"] == "bad" for i in r["issues"])
    stored = TO.strip(TOKENS)
    assert "c2lnbmF0dXJl" not in stored and stored.count("<signature removed>") == 3
    with pytest.raises(TO.TokenError):
        TO.analyse("not a token")
    c = C.analyse(DIFF)
    rules = {(h["file"], h["rule"], h["line"]) for h in c["hits"]}
    assert ("app/api.py", "pickle", 2) in rules and ("app/api.py", "sql-concat", 3) in rules and ("app/api.py", "tls-off-py", 4) in rules
    assert ("app/api.py", "hardcoded-secret", 5) in rules and ("app/api.py", "weak-random", 8) in rules
    assert ("web/app.js", "inner-html", 6) in rules and ("web/app.js", "weak-hash", 7) in rules
    # a removed line, a placeholder password and model.eval() are not hits; a secret is shown cut
    assert not any(h["rule"] == "eval" for h in c["hits"]) and sum(1 for h in c["hits"] if h["rule"] == "hardcoded-secret") == 1
    assert c["diff"] and c["lines"] == 9 and "sk_live_abcdefghijk123" not in json.dumps(c) and "abcdefghijk" not in C.redact(DIFF)
    files = C.analyse("## a.go\nhttp.Transport{TLSClientConfig: &tls.Config{InsecureSkipVerify: true}}\nexec.Command(\"sh\", \"-c\", x)\n## b.java\nObjectInputStream in = new ObjectInputStream(s);")
    assert {h["rule"] for h in files["hits"]} == {"tls-off-go", "go-shell", "java-deser"} and not files["diff"]
    with pytest.raises(C.CodeError):
        C.analyse("   ")
    w = CI.workflow("medium", branches="main, release/*")
    y = yaml.safe_load(w["yaml"])
    assert w["file"] == ".github/workflows/security-gate.yml" and y.get("on", y.get(True))["pull_request"]["branches"] == ["main", "release/*"] and y["permissions"] == {"contents": "read"}
    (tmp_path / "g.py").write_text(y["jobs"]["gate"]["steps"][1]["run"])
    run = lambda name: subprocess.run([sys.executable, "g.py", name], cwd=tmp_path, capture_output=True, text=True, env={**os.environ, "GITHUB_STEP_SUMMARY": str(tmp_path / "sum.md")})   # noqa: E731
    (tmp_path / "bad.diff").write_text(DIFF)
    (tmp_path / "ok.diff").write_text("+++ b/a.py\n@@ -1 +1 @@\n+print('hello')\n")
    p = run("bad.diff")
    assert p.returncode == 1 and "file=app/api.py,line=2" in p.stdout and "CWE-502" in p.stdout and "Security gate" in (tmp_path / "sum.md").read_text()
    # the gate finds exactly what the desk finds
    assert p.stdout.count("::error") == sum(1 for h in c["hits"] if h["sev"] in ("high", "medium"))
    assert run("ok.diff").returncode == 0
    for bad in ({"fail_level": "critical"}, {"runner": "a b"}, {"branches": "ma in"}):
        with pytest.raises(CI.CiError):
            CI.workflow(**bad)


def test_hire_chat_wiring_store_and_guards(sec):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    assert sec.summary(T)["hired"] is False and "Hire me from AI Employees" in sec.greeting(T)
    with pytest.raises(PermissionError):
        sec.do(T, "add", {"kind": "headers", "text": HEADERS})
    _hire()
    d = sec.summary(T)
    assert d["hired"] and d["foot"] == sec.FOOT and {n["go"] for n in d["desk"]["needs"]} >= {"findings", "settings"}
    chat = sec.current(T)
    assert sec.is_security(chat["id"]) and sec.owns(T, chat["id"]) and "<security_desk>" in sec.block(T)
    s_ = (root / "server/app/agent/santosh.py").read_text()
    assert "_sec.is_security(conversation_id)" in s_ and "adm.admit_families(_sec.FAMILIES)" in s_
    for f_ in ("callconv.py", "convs.py"):
        assert '"seceng"' in (root / "server/app" / f_).read_text()
    from app.main import APP_VERSION, app
    r = TestClient(app).get("/console/security")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "secdesk.js" in r.text
    html = (root / "server/app/static/console/secdesk.html").read_text()
    for x in ("chatkit.js", "secdesk.css", "secdesk.js"):
        assert f"/static/console/{x}?v={APP_VERSION}" in html, x
    assert "location.assign('/console/security')" in (root / "server/app/static/console/v2.js").read_text()
    assert "security_eng: 'secdesk'" in (root / "server/app/static/console/employees.js").read_text()
    from app.employee import hire
    assert hire.CATALOG["security_eng"]["live"] is True
    from app.agent import admit
    from app.agent.tools import FAMILY_OF, HANDLERS
    assert FAMILY_OF["security_desk"] in sec.FAMILIES and "security_desk" in HANDLERS and "seceng" in admit.EXTRA_KEYS
    f1 = sec.do(T, "add", {"kind": "findings", "text": REPORT, "inputs": {"scan_date": "2026-11-28"}})
    assert f1["number"] == "F-0001" and f1["brief"]["critical"] == 1 and f1["brief"]["bad"] and f1["title"].startswith("Findings: ")
    json.dumps(f1)
    assert any(n["go"] == "findings/" + f1["id"] for n in sec.summary(T)["desk"]["needs"])
    h1 = sec.do(T, "add", {"kind": "headers", "text": HEADERS, "inputs": {"url": "https://shop.example.com"}})
    assert h1["number"] == "H-0001" and h1["brief"]["cookies"] == 3
    leaf, ca = _certs()
    c1 = sec.do(T, "add", {"kind": "certs", "text": leaf + ca, "inputs": {"today": "2026-11-28", "hosts": "shop.example.com"}})
    assert c1["number"] == "C-0001" and c1["brief"]["days"] == 20
    t1 = sec.do(T, "add", {"kind": "tokens", "text": TOKENS})
    assert t1["number"] == "T-0001" and t1["brief"]["flagged"] >= 2 and "c2lnbmF0dXJl" not in t1["text"]
    k1 = sec.do(T, "add", {"kind": "code", "text": DIFF})
    assert k1["number"] == "R-0001" and k1["brief"]["high"] >= 4 and "abcdefghijk" not in k1["text"]
    w = sec.do(T, "ci", {})
    assert w["file"] == ".github/workflows/security-gate.yml" and yaml.safe_load(w["yaml"])
    st = sec.do(T, "settings", {"sla_critical": 3, "hosts": "shop.example.com, *.example.com", "fail_level": "medium", "expect_alg": "RS256"})
    assert st["sla_critical"] == 3 and st["fail_level"] == "medium" and "Fail" not in str(st)
    sec.forget(T)
    assert "critical 3" in sec.block(T) and "gate fails at medium" in sec.block(T)
    assert "at medium or above" in sec.do(T, "ci", {})["yaml"]
    f2 = sec.do(T, "add", {"kind": "findings", "text": REPORT, "inputs": {"scan_date": "2026-11-28"}})
    assert next(f for f in f2["result"]["rows"] if f["rule"] == "CVE-2024-0002")["due"] == "2026-12-01"
    mk = sec.do(T, "mark", {"id": f1["id"], "status": "fixed"})
    assert mk["status"] == "fixed" and not any(n["go"] == "findings/" + f1["id"] for n in sec.summary(T)["desk"]["needs"])
    import asyncio
    from app.agent import seceng_tools as ST
    from app.agent.tools import Ctx, ToolError
    out = asyncio.run(ST.security_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="headers", text=GOOD_HEADERS))
    assert out["number"] == "H-0002" and all(c["ok"] for c in out["checks"])
    out = asyncio.run(ST.security_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="ci"))
    assert out["file"] == ".github/workflows/security-gate.yml"
    with pytest.raises(PermissionError):
        sec.do(T, "settings", {"hosts": "my password is hunter2"})
    with pytest.raises(PermissionError):
        sec.do(T, "add", {"kind": "code", "text": DIFF + "+aws_secret_access_key = abc\n"})
    with pytest.raises(PermissionError):
        sec.do(T, "add", {"kind": "certs", "text": leaf + "-----BEGIN RSA PRIVATE KEY-----\nxx"})
    with pytest.raises(ToolError):
        asyncio.run(ST.security_desk(Ctx(tenant_id=T, conversation_id=chat["id"]), action="code", text="key = AKIAABCDEFGHIJKLMNOP"))
    for bad in ({"fail_level": "critical"}, {"expect_alg": "RSA"}, {"sla_critical": 400}, {"sla_high": 2}, {"hosts": "bad host!"}, {"token_hours": 0}):
        with pytest.raises((sec.SecDeskError, PermissionError)):
            sec.do(T, "settings", bad)
    with pytest.raises(sec.SecDeskError):
        sec.do(T, "add", {"kind": "tokens", "text": ""})
    with pytest.raises(sec.SecDeskError):
        sec.do(T, "nope", {})
    from app.employee import hire as H
    H.pause(T, "security_eng")
    assert sec.do(T, "get", {"id": f1["id"]})["id"] == f1["id"] and sec.do(T, "ci", {})["yaml"]
    with pytest.raises(PermissionError):
        sec.do(T, "add", {"kind": "headers", "text": HEADERS})


# ---------------------------------------------------------------- the browser walk
@pytest.fixture
def sec_server(sec, monkeypatch):
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


def test_desk_in_a_real_browser(sec, sec_server):
    base, browser, key = sec_server
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
    pg.goto(base + "/console/security")
    pg.wait_for_selector(".sek-path", timeout=20000)
    snap(pg, "sec-today-empty-1440")
    go(pg, "#/findings", "form[data-form=findings]")
    put(pg, "findings", "scan_date", "2026-11-28")
    submit(pg, "findings", json.dumps(TRIVY) + "\n## grype\n" + json.dumps(GRYPE) + "\n## codeql\n" + json.dumps(SARIF) + "\n## baseline\n" + json.dumps(BASE), "table.sek-t")
    t = pg.inner_text("#secPage")
    assert "4.17.22" in t and "CVE-2022-9999" in t and "py/sql-injection" in t
    snap(pg, "sec-findings-1440")
    go(pg, "#/headers", "form[data-form=headers]")
    put(pg, "headers", "url", "https://shop.example.com")
    submit(pg, "headers", HEADERS, "table.sek-sc")
    assert "__Host- rules broken" in pg.inner_text("#secPage") and pg.locator(".sek-x").count() >= 2
    snap(pg, "sec-headers-1440")
    leaf, ca = _certs()
    go(pg, "#/certificates", "form[data-form=certs]")
    put(pg, "certs", "hosts", "shop.example.com, other.org")
    submit(pg, "certs", leaf + ca, ".sek-chain")
    assert "Test Issuing CA" in pg.inner_text("#secPage") and "other.org is not covered" in pg.inner_text("#secPage")
    snap(pg, "sec-certificates-1440")
    go(pg, "#/tokens", "form[data-form=tokens]")
    put(pg, "tokens", "expect_alg", "RS256")
    submit(pg, "tokens", TOKENS, "table.sek-t")
    assert "alg none" in pg.inner_text("#secPage") and "c2lnbmF0dXJl" not in pg.content()
    snap(pg, "sec-tokens-1440")
    go(pg, "#/code", "form[data-form=code]")
    submit(pg, "code", DIFF, "table.sek-t")
    assert "CWE-502" in pg.inner_text("#secPage") and "abcdefghijk" not in pg.content()
    snap(pg, "sec-code-1440")
    go(pg, "#/settings", "form[data-form=settings]")
    pg.fill("form[data-form=settings] [name=hosts]", "shop.example.com")
    pg.select_option("form[data-form=settings] [name=fail_level]", "medium")
    pg.click("form[data-form=settings] [type=submit]")
    pg.wait_for_selector("#toast:has-text('Saved')", timeout=20000)
    go(pg, "#/ci", "text=security-gate.yml")
    assert "at medium or above" in pg.inner_text("#secPage")
    snap(pg, "sec-ci-1440")
    go(pg, "#/today", ".sek-list")
    snap(pg, "sec-today-1440")
    for route, sel in (("#/today", ".sek-list"), ("#/findings", ".sek-item"), ("#/headers", ".sek-item"), ("#/certificates", ".sek-item"), ("#/tokens", ".sek-item"),
                       ("#/code", ".sek-item"), ("#/ci", "text=security-gate.yml"), ("#/settings", "form[data-form=settings]")):
        pg.set_viewport_size({"width": 390, "height": 860})
        go(pg, route, sel)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('body *')].filter(e => !e.closest('pre,textarea,table,svg') && e.getBoundingClientRect().right > innerWidth + 1).slice(0, 6).map(e => e.tagName + '.' + e.className + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
    for route in ("#/findings", "#/headers", "#/certificates", "#/tokens", "#/code"):
        go(pg, route, ".sek-item")
        pg.locator(".sek-item").first.click()
        pg.wait_for_selector(".sek-head", timeout=20000)
        w = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        wide = pg.evaluate("[...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 8).map(e => e.tagName + '.' + e.className + ':' + Math.round(e.getBoundingClientRect().right) + ':' + (e.textContent || '').slice(0, 40))")
        assert w[0] <= w[1] + 1, (route, w, wide)
        snap(pg, "sec-" + route[2:] + "-390")
    assert not errs, errs
