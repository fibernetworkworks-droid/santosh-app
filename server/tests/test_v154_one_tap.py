"""v0.154 one-tap MCP: npm / PyPI directory servers run on the MCP runner box (here: the real runner in-process, with a
local fake stdio server instead of Docker) and join Hoola like a hosted server, through Hoola's real MCP client."""
import hashlib
import json
import socket
import sys
import threading
import time
from pathlib import Path

import pytest

from tests.test_bazar import bz  # noqa: F401  (fixture)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "mcp_runner"))
import runner as R  # noqa: E402

FAKE = str(HERE / "mcp_fake_stdio.py")


def test_runner_spec_rules_and_locked_container():
    good = {"kind": "npm", "package": "@brave/brave-search-mcp-server", "token_sha256": "a" * 64,
            "env": {"BRAVE_API_KEY": "k"}}
    assert R.clean_spec(good)["package"] == "@brave/brave-search-mcp-server"
    for bad in ({"kind": "npm", "package": "../x"}, {"kind": "npm", "package": "x", "env": {"LD_PRELOAD": "/x"}},
                {"kind": "npm", "package": "x", "env": {"PATH": "/x"}}, {"kind": "npm", "package": "x; rm -rf /"},
                {"kind": "docker", "package": "evil/image"}, {"kind": "cmd", "package": "x"},
                {"kind": "pypi", "package": "x", "args": ["$(id)"]}):
        with pytest.raises(ValueError):
            R.clean_spec({"token_sha256": "a" * 64, **bad})
    cmd = R.command("b" * 24, R.clean_spec(good))
    joined = " ".join(cmd)
    for flag in ("--read-only", "--cap-drop ALL", "no-new-privileges", "--pids-limit", "--memory", "--user 10001:10001",
                 "--network hoola-mcp", "npm_config_ignore_scripts=true", "npx -y @brave/brave-search-mcp-server"):
        assert flag in joined, flag
    assert "-v /" not in joined and "--privileged" not in joined and "docker.sock" not in joined
    py = R.command("c" * 24, R.clean_spec({**good, "kind": "pypi", "package": "mcp-server-fetch"}))
    assert py[-2:] == ["uvx", "mcp-server-fetch"] or "uvx" in py
    assert R.mask("token=abcdefghijklmnop1234", {"env": {}}) == "token=[key hataya]"


@pytest.fixture
def run_box(bz, monkeypatch):  # noqa: F811
    monkeypatch.setenv("HOOLA_RUNNER_ALLOW_CMD", "1")
    for k in ("NO_PROXY", "no_proxy"):                                  # the test runner is on this machine
        monkeypatch.setenv(k, "127.0.0.1,localhost," + __import__("os").environ.get(k, ""))
    monkeypatch.setattr(R, "SECRET", "test-secret")
    R.SPECS.clear()
    R.LIVE.clear()
    srv = R.serve(0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    from app.bazar import custom_mcp, runner as hr, service
    from app.bazar.agent.toolbox import default_executors
    from app.config import get_settings
    st = get_settings()
    monkeypatch.setattr(st, "mcp_runner_url", base)
    monkeypatch.setattr(st, "mcp_runner_secret", "test-secret")
    monkeypatch.setattr(custom_mcp, "check_url", lambda u: u)          # the test runner is on localhost / http
    real = socket.getaddrinfo
    monkeypatch.setattr(custom_mcp.socket, "getaddrinfo", lambda h, *a, **k: real(h, *a, **k) if str(h)[:1].isdigit()
                        else [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))])
    service.set_executors(default_executors())
    hr._ENSURED.clear()
    verdicts = {}
    monkeypatch.setattr(R, "check", lambda kind, pkg, version="": verdicts.get(pkg, {"verdict": "ok", "reasons": [],
                                                                                     "facts": {}}))
    yield {"base": base, "verdicts": verdicts, "svc": service, "conv": bz["conv"]}
    for inst in list(R.LIVE.values()):
        inst.stop()
    srv.shutdown()


def _pick(d, with_env: bool):
    for s in d.servers():
        if s[d.PKG] and s[d.PKG][0] == "npm" and not d.blocked(s) and not d.local_pc(s) and not s[d.MCP_URL] and not d.risky(s) \
                and bool(s[d.ENV]) == with_env and (not with_env or len(s[d.ENV]) == 1):
            return s
    raise AssertionError("no entry")


def test_one_tap_runs_a_package_end_to_end(run_box, monkeypatch):
    from app.bazar import directory as d, runner as hr
    from app.bazar.db import RunnerSpec, session_factory
    svc = run_box["svc"]
    s = _pick(d, with_env=True)
    need = s[d.ENV][0]
    monkeypatch.setenv("HOOLA_RUNNER_FAKE_CMD", json.dumps([sys.executable, FAKE, need]))
    pub = d.public(s)
    assert pub["one_tap"] is True and pub["runs_on"] == "hoola" and pub["keys"] == [need]
    # 1. the listing says which key it needs: asked first (in the app, never chat)
    r = svc.mcp_add("default", "", ref=s[d.NAME])               # the chat tool's path: just the ref
    assert r["status"] == "needs_keys" and r["keys"][0]["name"] == need and "chat mein kabhi" in r["say"]
    # 2. with the key: started on the runner, tools listed, a normal MCP server row
    r = svc.mcp_one_tap("default", s[d.NAME], {need: "secret-value-123"})
    assert r["status"] == "ready" and set(r["tools"]) == {"get_forecast", "delete_city"}, r
    assert r["url"].startswith(run_box["base"] + "/mcp/") and r["name"] == s[d.TITLE]
    with session_factory() as ss:
        spec = ss.get(RunnerSpec, r["pack_id"])
        assert spec and spec.package == s[d.PKG][1] and "secret-value-123" not in spec.env_enc
    # 3. the avatar uses it: a read runs, a delete waits for her tap
    out = svc.run("default", run_box["conv"], r["pack_id"], "get_forecast", {"city": "Akola"})
    assert "Akola: 31C sunny" in json.dumps(out)
    w = svc.run("default", run_box["conv"], r["pack_id"], "delete_city", {"city": "Akola"})
    assert w.get("needs_approval") is True
    # 4. the runner restarts (it keeps nothing on disk): Hoola registers it again by itself
    for inst in list(R.LIVE.values()):
        inst.stop()
    R.SPECS.clear()
    R.LIVE.clear()
    hr._ENSURED.clear()
    from app.bazar.connectors.mcp_remote import McpExecutor
    McpExecutor._cache.clear()
    out = svc.run("default", run_box["conv"], r["pack_id"], "get_forecast", {"city": "Pune"})
    assert "Pune: 31C sunny" in json.dumps(out)
    # 5. removed = its container stops and the spec is gone
    assert svc.mcp_remove("default", r["pack_id"])
    assert not R.SPECS
    with session_factory() as ss:
        assert ss.get(RunnerSpec, r["pack_id"]) is None


def test_key_names_from_the_servers_own_error(run_box, monkeypatch):
    from app.bazar import directory as d
    s = _pick(d, with_env=False)
    monkeypatch.setenv("HOOLA_RUNNER_FAKE_CMD", json.dumps([sys.executable, FAKE, "ACME_API_KEY"]))
    r = run_box["svc"].mcp_one_tap("default", s[d.NAME])
    assert r["status"] == "needs_keys" and r["keys"] == [{"name": "ACME_API_KEY", "kind": "secret"}]
    r = run_box["svc"].mcp_one_tap("default", s[d.NAME], {"ACME_API_KEY": "zz-1"})
    assert r["status"] == "ready"


def test_safety_verdicts(run_box, monkeypatch):
    from app.bazar import directory as d
    s = _pick(d, with_env=False)
    monkeypatch.setenv("HOOLA_RUNNER_FAKE_CMD", json.dumps([sys.executable, FAKE, "X_TOKEN"]))
    run_box["verdicts"][s[d.PKG][1]] = {"verdict": "block", "reasons": ["OSV.dev lists this package as MALICIOUS"]}
    r = run_box["svc"].mcp_one_tap("default", s[d.NAME], {"X_TOKEN": "t"})
    assert r["status"] == "blocked" and "MALICIOUS" in r["say"] and not R.SPECS
    from app.bazar.db import PackageCheck, session_factory
    with session_factory() as ss:                                      # a fresh verdict, not the cached one
        ss.query(PackageCheck).delete()
        ss.commit()
    run_box["verdicts"][s[d.PKG][1]] = {"verdict": "caution", "reasons": ["2 known security problem(s) on OSV.dev"]}
    r = run_box["svc"].mcp_one_tap("default", s[d.NAME], {"X_TOKEN": "t"})
    assert r["status"] == "caution" and "known security" in r["say"]
    r = run_box["svc"].mcp_one_tap("default", s[d.NAME], {"X_TOKEN": "t"}, accept_caution=True)
    assert r["status"] == "ready"
    rows = run_box["svc"].mcp_list("default")
    assert rows and rows[0]["caution"] is True


def test_not_for_the_runner(run_box):
    from app.bazar import directory as d
    from app.bazar.connectors.base import ToolError
    pc = next(s for s in d.servers() if s[d.PKG] and d.local_pc(s) and not d.blocked(s) and not s[d.MCP_URL])
    assert d.public(pc)["runs_on"] == "pc" and d.public(pc)["one_tap"] is False
    assert run_box["svc"].mcp_one_tap("default", pc[d.NAME])["status"] == "pc_only"
    scraper = next(s for s in d.servers() if d.blocked(s) == "scraper")
    with pytest.raises(ToolError, match="scrapes"):
        run_box["svc"].mcp_one_tap("default", scraper[d.NAME])
    apify = next(s for s in d.servers() if s[d.SRC] == "apify" and s[d.MCP_URL] and not d.blocked(s))
    r = run_box["svc"].mcp_one_tap("default", apify[d.NAME])
    assert r["status"] == "needs_keys" and r["keys"][0]["name"] == "APIFY_TOKEN" and "credit" in r["say"]


def test_without_a_runner_it_says_so(bz, monkeypatch):  # noqa: F811
    from app.bazar import directory as d, service
    from app.bazar.connectors.base import ToolError
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "mcp_runner_url", "")
    s = _pick(d, with_env=False)
    assert d.public(s)["one_tap"] is False and d.public(s)["connect"] == "local"
    with pytest.raises(ToolError, match="MCP runner"):
        service.mcp_one_tap("default", s[d.NAME])


def test_runner_refuses_unsigned_and_wrong_tokens(run_box):
    import httpx
    base = run_box["base"]
    httpx = httpx.Client(trust_env=False)
    assert httpx.post(base + "/v1/instances", json={"iid": "a" * 24}).status_code == 401
    ts = str(int(time.time()) - 900)
    body = json.dumps({"iid": "a" * 24}).encode()
    old = httpx.post(base + "/v1/instances", content=body,
                     headers={"X-Hoola-Time": ts, "X-Hoola-Sign": R.sign("POST", "/v1/instances", ts, body)})
    assert old.status_code == 401                                        # replayed / old signature
    assert httpx.post(base + "/mcp/" + "d" * 24, json={}, headers={"Authorization": "Bearer x"}).status_code == 404
    R.SPECS["e" * 24] = {"token_sha256": hashlib.sha256(b"right").hexdigest(), "kind": "npm", "package": "x",
                         "version": "", "env": {}, "args": []}
    assert httpx.post(base + "/mcp/" + "e" * 24, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                      headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert httpx.get(base + "/v1/health").json()["ok"] is True
