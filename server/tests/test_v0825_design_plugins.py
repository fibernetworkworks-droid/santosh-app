"""D8a HOOLA DESIGN PLUGIN RUNTIME (docs/HOOLA_DESIGN_PLAN.md section 8, D8a): install + validation, the approval bound
to ONE code hash (a code change asks again), switch on / off, the plugin's own storage, tenant walls, the fetch proxy
(https only, granted hosts only, the house SSRF guard before AND after connecting, no redirect to another host, size
cap, never her token), the sandboxed runner page and its own CSP.

No real network anywhere: the resolver and the proxy's one HTTP seam (`plugins._http`) are monkeypatched.

Browser half: server/tests/web/design_plugins_test.js against a REAL server this file starts on a free port - three
squares in one undo step, a plugin without `edit` refused, a malicious plugin that gets nothing (no token, no cookie,
no network, no top navigation), an endless loop killed while the editor stays responsive, a panel plugin's panel."""
import base64
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

HERE = Path(__file__).resolve().parent
SERVER = HERE.parent
DESIGN = SERVER / "app" / "static" / "console" / "design"
JS_TEST = HERE / "web" / "design_plugins_test.js"
NODE = shutil.which("node")
SANDBOX_CHROME = "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"
needs_node = pytest.mark.skipif(not NODE, reason="node is not installed")
H = {"Authorization": "Bearer kd"}
CODE = "const p = await hoola.page();\nawait hoola.create('RECT', p.id, {x: 0, y: 0});\n"


@pytest.fixture()
def design_env(env, tmp_path, monkeypatch):
    monkeypatch.setenv("API_KEY", "kd")
    monkeypatch.setenv("DESIGN_DIR", str(tmp_path / "design"))
    from app.config import get_settings
    from app.design import plugins
    get_settings.cache_clear()
    plugins.FETCHES.reset()
    yield monkeypatch
    get_settings.cache_clear()
    plugins.FETCHES.reset()


def client():
    from app.main import app
    return TestClient(app)


def other_tenant():
    from app import accounts
    from app.db import User, session
    with session() as s:
        u = User(email="other@example.com", name="Other Person")
        s.add(u)
        s.flush()
        uid = u.id
    return {"Authorization": f"Bearer {accounts.issue_session(uid)}"}


def man(**kw):
    m = {"id": "three-squares", "name": "Three squares", "version": "1.0.0", "description": "Makes squares.",
         "permissions": ["read", "edit"], "ui": False, "menu": [{"label": "Make", "command": "make"}]}
    m.update(kw)
    return m


def install(c, headers=H, code=CODE, **kw):
    r = c.post("/api/design/plugins", headers=headers, json={"manifest": man(**kw), "code": code})
    assert r.status_code == 200, r.text
    return r.json()["plugin"]


def approve(c, pid, perms, sha, headers=H):
    return c.post(f"/api/design/plugins/{pid}/grant", headers=headers, json={"permissions": perms, "code_sha": sha})


# ================================================================================ install + validation
def test_install_validates_the_manifest_and_the_code(design_env):
    c = client()
    bad = [man(id="X"), man(id="a"), man(name=""), man(permissions=["read", "camera"]), man(permissions=["net:10.0.0.1"]),
           man(permissions=["net:https://api.example.com"]), man(permissions=["net:*.example.com"]), man(ui="yes"),
           man(menu=[{"label": "A", "command": "go"}, {"label": "B", "command": "go"}]), man(menu=[{"label": "A", "command": "no spaces"}]),
           man(permissions=["net:h%d.example.com" % i for i in range(11)]), man(description="x" * 501)]
    for m in bad:
        r = c.post("/api/design/plugins", headers=H, json={"manifest": m, "code": CODE})
        assert r.status_code == 422, (m, r.text)
    assert c.post("/api/design/plugins", headers=H, json={"manifest": man(), "code": ""}).status_code == 422
    assert c.post("/api/design/plugins", headers=H, json={"manifest": man(), "code": "x" * (200 * 1024 + 1)}).status_code in (413, 422)
    assert c.post("/api/design/plugins", json={"manifest": man(), "code": CODE}).status_code == 401
    p = install(c, permissions=["read", "edit", "net:API.Example.com", "read"])
    assert p["code_sha"] == hashlib.sha256(CODE.encode()).hexdigest()
    assert p["manifest"]["permissions"] == ["read", "edit", "net:api.example.com"]         # cleaned, lower-cased, no duplicates
    assert p["approved"] is False and p["needs_review"] is True and p["enabled"] is True and p["granted"] == []
    listed = c.get("/api/design/plugins", headers=H).json()["plugins"]
    assert [x["id"] for x in listed] == ["three-squares"] and "code" not in listed[0]
    one = c.get("/api/design/plugins/three-squares", headers=H).json()["plugin"]
    assert one["code"] == CODE
    assert install(c, menu=[])["manifest"]["menu"] == [{"label": "Run", "command": "run"}]      # no menu = one "Run"


def test_the_approval_is_bound_to_the_code_hash(design_env):
    c = client()
    p = install(c)
    r = c.get("/api/design/plugins/three-squares/run", headers=H)
    assert r.status_code == 409 and "approved" in r.json()["detail"]
    assert approve(c, "three-squares", ["read"], "0" * 64).status_code == 409                 # not the code she looked at
    assert approve(c, "three-squares", ["read", "export"], p["code_sha"]).status_code == 422  # it did not ask for export
    assert approve(c, "three-squares", ["read"], "short").status_code == 422
    got = approve(c, "three-squares", ["read"], p["code_sha"]).json()["plugin"]               # a subset is fine
    assert got["approved"] is True and got["granted"] == ["read"]
    run = c.get("/api/design/plugins/three-squares/run", headers=H).json()
    assert run["code"] == CODE and run["permissions"] == ["read"]
    # the same code again keeps the approval; new code drops it until she looks again
    assert install(c)["approved"] is True
    p2 = install(c, code=CODE + "// changed\n")
    assert p2["approved"] is False and p2["stale_grant"] is True and p2["granted"] == []
    r = c.get("/api/design/plugins/three-squares/run", headers=H)
    assert r.status_code == 409
    assert approve(c, "three-squares", ["read", "edit"], p["code_sha"]).status_code == 409    # the OLD hash no longer fits
    assert approve(c, "three-squares", ["read", "edit"], p2["code_sha"]).status_code == 200
    assert c.get("/api/design/plugins/three-squares/run", headers=H).json()["permissions"] == ["read", "edit"]


def test_switch_off_and_remove(design_env):
    c = client()
    p = install(c)
    approve(c, "three-squares", ["read", "edit"], p["code_sha"])
    assert c.patch("/api/design/plugins/three-squares", headers=H, json={"enabled": "no"}).status_code == 422
    assert c.patch("/api/design/plugins/three-squares", headers=H, json={"enabled": False}).json()["plugin"]["enabled"] is False
    r = c.get("/api/design/plugins/three-squares/run", headers=H)
    assert r.status_code == 409 and "switched off" in r.json()["detail"]
    c.patch("/api/design/plugins/three-squares", headers=H, json={"enabled": True})
    assert c.get("/api/design/plugins/three-squares/run", headers=H).status_code == 200
    assert c.delete("/api/design/plugins/three-squares", headers=H).json() == {"ok": True}
    assert c.get("/api/design/plugins/three-squares", headers=H).status_code == 404
    assert c.delete("/api/design/plugins/three-squares", headers=H).status_code == 404


def test_storage_needs_its_grant_and_has_a_cap(design_env):
    c = client()
    p = install(c, permissions=["read", "storage"])
    assert c.get("/api/design/plugins/three-squares/storage", headers=H).status_code == 409      # not approved yet
    approve(c, "three-squares", ["read"], p["code_sha"])
    assert c.get("/api/design/plugins/three-squares/storage", headers=H).status_code == 403      # storage not granted
    approve(c, "three-squares", ["read", "storage"], p["code_sha"])
    assert c.get("/api/design/plugins/three-squares/storage", headers=H).json() == {"data": {}}
    assert c.put("/api/design/plugins/three-squares/storage", headers=H, json={"data": {"theme": "dark", "n": 3}}).status_code == 200
    assert c.get("/api/design/plugins/three-squares/storage", headers=H).json() == {"data": {"theme": "dark", "n": 3}}
    assert c.put("/api/design/plugins/three-squares/storage", headers=H, json={"data": {"big": "x" * (256 * 1024)}}).status_code == 413
    assert c.put("/api/design/plugins/three-squares/storage", headers=H, json={"data": [1, 2]}).status_code == 422
    assert c.get("/api/design/plugins/three-squares/storage", headers=H).json()["data"]["n"] == 3     # the refused write changed nothing


def test_tenant_walls(design_env):
    c = client()
    p = install(c, permissions=["read", "storage", "net:api.example.com"])
    approve(c, "three-squares", ["read", "storage", "net:api.example.com"], p["code_sha"])
    o = other_tenant()
    assert c.get("/api/design/plugins", headers=o).json() == {"plugins": []}
    for method, path, body in (("get", "", None), ("get", "/run", None), ("get", "/storage", None), ("delete", "", None),
                               ("patch", "", {"enabled": False}), ("post", "/grant", {"permissions": ["read"], "code_sha": p["code_sha"]}),
                               ("put", "/storage", {"data": {}}), ("post", "/fetch", {"url": "https://api.example.com/"})):
        kw = {"headers": o}
        if body is not None:
            kw["json"] = body
        r = getattr(c, method)("/api/design/plugins/three-squares" + path, **kw)
        assert r.status_code == 404, (method, path, r.status_code, r.text)
    # her twin with the same id is HER own row, untouched by the other account
    install(c, headers=o, code="hoola.notify('mine')")
    assert c.get("/api/design/plugins/three-squares", headers=H).json()["plugin"]["code"] == CODE


# ================================================================================ the fetch proxy
def _resolver(monkeypatch, table):
    real = socket.getaddrinfo

    def fake(host, *a, **kw):
        if host in table:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443)) for ip in table[host]]
        raise socket.gaierror("no such host in this test")
    monkeypatch.setattr(socket, "getaddrinfo", fake)
    return real


def _net(c, perms=("net:api.example.com",)):
    p = install(c, permissions=["read", *perms])
    assert approve(c, "three-squares", ["read", *perms], p["code_sha"]).status_code == 200


def test_fetch_proxy_happy_path_and_what_it_never_sends(design_env):
    from app.design import plugins
    c = client()
    _net(c)
    _resolver(design_env, {"api.example.com": ["93.184.216.34"]})
    seen = []

    async def fake_http(method, url, headers, body, timeout, cap):
        seen.append({"method": method, "url": url, "headers": dict(headers), "body": body, "timeout": timeout, "cap": cap})
        if url.endswith("/png"):
            return {"status": 200, "headers": {"content-type": "image/png"}, "content": b"\x89PNG\r\n", "too_big": False, "peer": "93.184.216.34"}
        return {"status": 200, "headers": {"content-type": "application/json; charset=utf-8"}, "content": b'{"ok":1}', "too_big": False, "peer": "93.184.216.34"}
    design_env.setattr(plugins, "_http", fake_http)
    r = c.post("/api/design/plugins/three-squares/fetch", headers={**H, "Cookie": "session=hers"},
               json={"url": "https://api.example.com/v1/x?q=1", "method": "POST", "body": '{"a":1}',
                     "headers": {"Content-Type": "application/json", "X-Api-Key": "plugin-own", "Cookie": "c=1",
                                 "X-Forwarded-For": "10.0.0.1", "Host": "evil", "Authorization": "Bearer plugin-own"}})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out == {"status": 200, "ok": True, "url": "https://api.example.com/v1/x?q=1", "contentType": "application/json; charset=utf-8",
                   "encoding": "text", "body": '{"ok":1}'}
    sent = seen[0]
    assert sent["method"] == "POST" and sent["body"] == b'{"a":1}' and sent["cap"] == 2 * 1024 * 1024 and sent["timeout"] <= 10
    assert sent["headers"] == {"content-type": "application/json", "x-api-key": "plugin-own", "authorization": "Bearer plugin-own"}
    assert "kd" not in json.dumps(sent["headers"]) and "hers" not in json.dumps(sent["headers"])   # never her key, never her cookie
    png = c.post("/api/design/plugins/three-squares/fetch", headers=H, json={"url": "https://api.example.com/png"}).json()
    assert png["encoding"] == "base64" and base64.b64decode(png["body"]) == b"\x89PNG\r\n"


def test_fetch_proxy_refusals(design_env):
    from app.design import plugins
    c = client()
    _net(c)
    _resolver(design_env, {"api.example.com": ["93.184.216.34"], "inside.example.com": ["10.1.2.3"]})
    calls = []

    async def fake_http(method, url, headers, body, timeout, cap):
        calls.append(url)
        return {"status": 200, "headers": {"content-type": "text/plain"}, "content": b"hi", "too_big": False, "peer": "93.184.216.34"}
    design_env.setattr(plugins, "_http", fake_http)
    f = lambda body: c.post("/api/design/plugins/three-squares/fetch", headers=H, json=body)   # noqa: E731
    assert f({"url": "http://api.example.com/"}).status_code == 403                       # https only
    assert f({"url": "https://other.example.com/"}).status_code == 403                     # not a granted host
    assert f({"url": "https://api.example.com:8443/"}).status_code == 403                  # only the normal port
    assert f({"url": "https://user:pw@api.example.com/"}).status_code == 403               # no credentials in the address
    assert f({"url": "https://93.184.216.34/"}).status_code == 403                         # a number is not a granted host
    assert f({"url": "https://api.example.com/", "method": "DELETE"}).status_code == 422
    assert f({"url": "https://api.example.com/", "method": "POST", "body": "x" * (256 * 1024 + 1)}).status_code == 413
    assert calls == []                                                                      # none of those reached the network
    assert f({"url": "https://api.example.com/"}).status_code == 200
    # the granted host resolving into a private network (or metadata) is refused by the house guard
    _net(c, perms=("net:inside.example.com",))
    assert f({"url": "https://inside.example.com/"}).status_code == 403
    _resolver(design_env, {"inside.example.com": ["169.254.169.254"]})
    assert f({"url": "https://inside.example.com/"}).status_code == 403
    _resolver(design_env, {"inside.example.com": ["127.0.0.1"]})
    assert f({"url": "https://inside.example.com/"}).status_code == 403
    assert calls == ["https://api.example.com/"]
    # a plugin with no host at all
    p = install(c, permissions=["read"])
    approve(c, "three-squares", ["read"], p["code_sha"])
    assert f({"url": "https://api.example.com/"}).status_code == 403


def test_fetch_proxy_rebinding_redirects_and_size(design_env):
    from app.design import plugins
    c = client()
    _net(c)
    _resolver(design_env, {"api.example.com": ["93.184.216.34"]})
    answers = []

    async def fake_http(method, url, headers, body, timeout, cap):
        return answers.pop(0)(url)
    design_env.setattr(plugins, "_http", fake_http)
    f = lambda: c.post("/api/design/plugins/three-squares/fetch", headers=H, json={"url": "https://api.example.com/a"})   # noqa: E731
    ok = lambda url: {"status": 200, "headers": {"content-type": "text/plain"}, "content": b"done", "too_big": False, "peer": "93.184.216.34"}   # noqa: E731
    # DNS said public, the connection landed somewhere private: refused after connecting
    answers[:] = [lambda url: {"status": 200, "headers": {}, "content": b"secret", "too_big": False, "peer": "127.0.0.1"}]
    r = f()
    assert r.status_code == 403 and "private" in r.json()["detail"]
    # a redirect to another host
    answers[:] = [lambda url: {"status": 302, "headers": {"location": "https://evil.example.net/x"}, "content": b"", "too_big": False, "peer": "93.184.216.34"}]
    assert f().status_code == 403
    # a redirect down to http on the same host
    answers[:] = [lambda url: {"status": 301, "headers": {"location": "http://api.example.com/b"}, "content": b"", "too_big": False, "peer": "93.184.216.34"}]
    assert f().status_code == 403
    # a redirect on the same host is followed (re-guarded)
    hops = []
    answers[:] = [lambda url: (hops.append(url), {"status": 302, "headers": {"location": "/b"}, "content": b"", "too_big": False, "peer": "93.184.216.34"})[1],
                  lambda url: (hops.append(url), ok(url))[1]]
    r = f()
    assert r.status_code == 200 and r.json()["body"] == "done" and r.json()["url"] == "https://api.example.com/b"
    assert hops == ["https://api.example.com/a", "https://api.example.com/b"]
    # round in circles
    loop = lambda url: {"status": 302, "headers": {"location": "/a"}, "content": b"", "too_big": False, "peer": "93.184.216.34"}   # noqa: E731
    answers[:] = [loop] * 4
    assert f().status_code == 403
    # over the size cap
    answers[:] = [lambda url: {"status": 200, "headers": {"content-type": "text/plain"}, "content": b"x" * 10, "too_big": True, "peer": "93.184.216.34"}]
    assert f().status_code == 413


def test_fetch_rate_limit(design_env):
    from app.design import plugins
    c = client()
    _net(c)
    _resolver(design_env, {"api.example.com": ["93.184.216.34"]})

    async def fake_http(method, url, headers, body, timeout, cap):
        return {"status": 204, "headers": {}, "content": b"", "too_big": False, "peer": None}
    design_env.setattr(plugins, "_http", fake_http)
    design_env.setattr(plugins, "FETCHES", plugins._Window(3))
    codes = [c.post("/api/design/plugins/three-squares/fetch", headers=H, json={"url": "https://api.example.com/"}).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]


def test_the_real_http_seam_refuses_a_private_peer(design_env):
    """The seam itself (no monkeypatch) reads the address it connected to; httpx's mock transport has none -> None."""
    from app.design import plugins
    assert plugins._peer_ok(None) is True and plugins._peer_ok("93.184.216.34") is True
    for ip in ("127.0.0.1", "10.0.0.1", "192.168.1.1", "169.254.169.254", "::1", "fd00::1", "not-an-ip"):
        assert plugins._peer_ok(ip) is False, ip


# ================================================================================ the runner page
def test_the_runner_page_and_its_own_csp(design_env):
    c = client()
    r = c.get("/api/design/plugin-frame")                                   # no sign-in: an iframe can not send her key
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    csp = r.headers["content-security-policy"]
    script = re.search(r"<script>(.*)</script>", r.text, re.S).group(1)
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    assert f"script-src 'sha256-{digest}'" in csp
    assert script == (DESIGN / "plugin-runner.js").read_text("utf-8")
    for need in ("default-src 'none'", "connect-src 'none'", "img-src data: blob:", "worker-src blob:", "frame-ancestors 'self'",
                 "form-action 'none'", "base-uri 'none'", "object-src 'none'"):
        assert need in csp, need
    assert "unsafe-eval" not in csp and "'unsafe-inline'" not in csp.split("script-src")[1].split(";")[0]
    assert "X-Frame-Options" not in r.headers and r.headers["x-content-type-options"] == "nosniff"
    assert r.text.count("<script") == 1
    from app import main
    assert "unsafe-eval" not in main._CONSOLE_CSP and "frame-src 'self'" in main._CONSOLE_CSP      # the console's CSP as it was


def test_the_client_files(design_env):
    html = (DESIGN / "design.html").read_text()
    order = [html.index(f"design/{n}") for n in ("hd-ui.js", "hd-bridge-web.js", "hd-plugins.js", "hd-app.js")]
    assert order == sorted(order)
    assert "design-plugins.css" in html
    stamp = re.search(r"hd-app\.js\?v=([\d.]+)", html).group(1)
    assert f"hd-plugins.js?v={stamp}" in html and f"design-plugins.css?v={stamp}" in html
    js = (DESIGN / "hd-plugins.js").read_text()
    assert "fr.setAttribute('sandbox', 'allow-scripts')" in js
    code = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    code = re.sub(r"(^|\s)//[^\n]*", r"\1", code)
    assert re.findall(r"setAttribute\('sandbox', '([^']*)'\)", code) == ["allow-scripts"]
    for flag in ("allow-same-origin", "allow-top-navigation", "allow-popups", "allow-forms", "allow-modals"):
        assert flag not in code, flag
    runner = (DESIGN / "plugin-runner.js").read_text()
    assert "new Worker" in runner and "eval(" not in runner and "new Function" not in runner


@needs_node
def test_the_client_files_parse():
    for path in (DESIGN / "hd-plugins.js", DESIGN / "plugin-runner.js", JS_TEST):
        run = subprocess.run([NODE, "--check", str(path)], capture_output=True, text=True, timeout=60)
        assert run.returncode == 0, run.stderr[-2000:]


# ================================================================================ the browser walk
def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@needs_node
def test_plugins_in_a_real_browser(tmp_path):
    port, key = _free_port(), "plugins-test-key"
    env = os.environ.copy()
    env.update({"DATABASE_URL": f"sqlite:///{tmp_path}/plugins.db", "API_KEY": key, "WA_DRY_RUN": "true", "ANTHROPIC_API_KEY": "test",
                "SEMANTIC_OFF": "1", "MEMORY_AUTO": "false", "HOOLA_ENRICH": "false", "VIDEO_EDIT_WORKER": "false",
                "OPERATOR_WORKER": "false", "DESIGN_PAGE": "true", "PYTHONPATH": str(SERVER)})
    env.pop("DESIGN_DIR", None)
    log = open(tmp_path / "server.log", "w")
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level", "warning"],
                              cwd=tmp_path, env=env, stdout=log, stderr=subprocess.STDOUT)
    run = None
    try:
        base, up = f"http://127.0.0.1:{port}", False
        for _ in range(240):
            if server.poll() is not None:
                break
            try:
                with urllib.request.urlopen(base + "/console/design", timeout=2) as r:
                    up = r.status == 200
                    break
            except Exception:                            # noqa: BLE001 - not listening yet
                time.sleep(0.5)
        if not up:
            log.flush()
            pytest.fail("the server did not start: " + (tmp_path / "server.log").read_text()[-1500:])
        jenv = os.environ.copy()
        jenv.update({"HD_BASE": base, "HD_KEY": key})
        if jenv.get("HOOLA_CHROMIUM"):
            jenv["CHROMIUM_EXECUTABLE"] = jenv["HOOLA_CHROMIUM"]
        run = subprocess.run([NODE, str(JS_TEST)], capture_output=True, text=True, timeout=600, env=jenv)
        if run.returncode == 77 and not jenv.get("HOOLA_CHROMIUM") and Path(SANDBOX_CHROME).exists():
            jenv["HOOLA_CHROMIUM"] = SANDBOX_CHROME
            run = subprocess.run([NODE, str(JS_TEST)], capture_output=True, text=True, timeout=600, env=jenv)
    finally:
        server.terminate()
        try:
            server.wait(timeout=20)
        except subprocess.TimeoutExpired:
            server.kill()
        log.close()
    if run.returncode == 77:
        pytest.skip((run.stdout.strip().splitlines() or ["no browser here"])[-1])
    assert run.returncode == 0, (run.stdout[-2500:] + "\n" + run.stderr[-4000:] + "\n--- server ---\n" + (tmp_path / "server.log").read_text()[-1500:])
    report = json.loads(run.stdout.strip().splitlines()[-1])
    assert report["ok"] is True and report["checks"] >= 30, report
