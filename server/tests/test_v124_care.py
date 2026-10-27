"""v0.124 Website care + agency + GitHub export: page views counted by the hosting server (no IP / cookie), uptime samples,
care report with tips (built-not-live, facts changed), one monthly care note, staff only on sites given to them, client
summary, GitHub export only on her tap (private repo, blobs -> tree -> commit -> ref, noindex removed, README)."""
import asyncio
import base64
import json
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.test_v122_hosting import T, _events, _ready_site, host_env  # noqa: F401  (fixture)

GH_TOKEN = "github_pat_0123456789abcdef0123456789abcdef"
HOST = "sharma-sweets.hoolasites.in"


class FakeGitHub:
    def __init__(self):
        self.repos, self.blobs, self.trees, self.commits, self.refs = {}, {}, {}, {}, {}
        self.n = 0
        self.calls = []

    def sha(self):
        self.n += 1
        return f"{self.n:040x}"

    def handler(self, req: httpx.Request) -> httpx.Response:
        u = urlparse(str(req.url))
        if u.hostname != "api.github.com":
            return None
        if req.headers.get("authorization") != f"Bearer {GH_TOKEN}":
            return httpx.Response(401, json={"message": "Bad credentials"})
        body = json.loads(req.content or b"{}") if req.content else {}
        p = u.path
        self.calls.append((req.method, p))
        if p == "/user":
            return httpx.Response(200, json={"login": "meghana"})
        if p == "/user/repos" and req.method == "POST":
            self.repos[body["name"]] = {"name": body["name"], "private": body["private"], "default_branch": "main"}
            if body.get("auto_init"):
                c = self.sha()
                self.commits[c] = {"tree": None, "parents": []}
                self.refs[(body["name"], "main")] = c
            return httpx.Response(201, json=self.repos[body["name"]])
        m = re.match(r"^/repos/meghana/([\w.-]+)(/.*)?$", p)
        if not m:
            return httpx.Response(404, json={"message": "Not Found"})
        repo, rest = m.group(1), m.group(2) or ""
        if repo not in self.repos:
            return httpx.Response(404, json={"message": "Not Found"})
        if rest == "":
            return httpx.Response(200, json=self.repos[repo])
        if rest == "/git/blobs":
            s = self.sha()
            raw = base64.b64decode(body["content"]) if body.get("encoding") == "base64" else body["content"].encode()
            self.blobs[s] = raw
            return httpx.Response(201, json={"sha": s})
        if rest == "/git/trees":
            s = self.sha()
            self.trees[s] = body["tree"]
            return httpx.Response(201, json={"sha": s})
        if rest == "/git/commits":
            s = self.sha()
            self.commits[s] = {"tree": body["tree"], "parents": body["parents"], "message": body["message"]}
            return httpx.Response(201, json={"sha": s})
        m2 = re.match(r"^/git/refs?/heads/(\w+)$", rest)
        if m2 and req.method == "GET":
            sha = self.refs.get((repo, m2.group(1)))
            return httpx.Response(200, json={"object": {"sha": sha}}) if sha else httpx.Response(404, json={"message": "Not Found"})
        if m2 and req.method == "PATCH":
            assert self.commits[body["sha"]]["parents"] == [self.refs[(repo, m2.group(1))]]
            self.refs[(repo, m2.group(1))] = body["sha"]
            return httpx.Response(200, json={"object": {"sha": body["sha"]}})
        if rest == "/git/refs" and req.method == "POST":
            self.refs[(repo, body["ref"].split("/")[-1])] = body["sha"]
            return httpx.Response(201, json={})
        return httpx.Response(404, json={"message": f"no route {rest}"})


@pytest.fixture
def care_env(host_env):
    from app.site import cf, dns, github
    gh = FakeGitHub()
    cloud = host_env["cloud"]

    def both(req):
        r = gh.handler(req)
        return r if r is not None else cloud.handler(req)
    t = httpx.MockTransport(both)
    cf.set_transport(t)
    dns.set_transport(t)
    github.set_transport(t)
    yield {**host_env, "gh": gh}
    github.set_transport(None)


def _launched(c):
    g, ctx = _ready_site()
    card = c.post(f"/api/sites/{g['id']}/launch-request", json={}).json()
    assert c.post(f"/api/sites/{g['id']}/launch", json={"hash": card["hash"]}).status_code == 200
    return g, ctx


def test_views_uptime_report_and_monthly_note(care_env, monkeypatch):
    from app.main import app
    from app.site import care, hosting as H, service as S
    from app.site.hosting_models import SiteHost
    from app.db import session
    from sqlalchemy import select
    c = TestClient(app)
    g, ctx = _launched(c)
    for _ in range(3):
        assert c.get("/", headers={"host": HOST}).status_code == 200
    c.get("/contact/", headers={"host": HOST})
    c.get("/assets/site.css", headers={"host": HOST})                 # assets are not visits
    c.get("/old-page/", headers={"host": HOST})                        # 404 counted as a missing page
    care.count_check(g["id"], T, True)
    care.count_check(g["id"], T, False)
    c.post(f"/api/site-forms/{g['id']}", json={"name": "Ravi", "phone": "9822012345", "message": "kaju katli 2 kg"})
    rep = c.get(f"/api/sites/{g['id']}/care?days=30").json()
    assert rep["views"] == 4 and rep["missing_hits"] == 1 and rep["leads"] == 1 and rep["conversion_pct"] == 25.0
    assert dict(rep["top_pages"])["/"] == 3 and rep["uptime_pct"] == 50.0
    assert any("nahi khuli" in t for t in rep["tips"])
    with session() as s:                                               # nothing about the visitor is stored
        from app.site.care import SiteCareDay
        row = s.scalars(select(SiteCareDay)).first()
        assert set(json.loads(row.pages)) <= {"/", "/contact/"} and not hasattr(row, "ip_hash")
    # a newer version built but not live + her phone changed in her profile -> tips
    with session() as s:
        from app.site.models import Site
        s.get(Site, g["id"]).version += 1
    real = S.gather_facts
    monkeypatch.setattr(S, "gather_facts", lambda t, b="": {**real(t, b), "phone": "9000000001"})
    tips = care.report(T, g["id"])["tips"]
    assert any("live v1" in t or "live v" in t for t in tips) and any("9000000001" in t for t in tips)
    # monthly note: once, only on the 1st after 9 am IST
    ist = timezone(timedelta(hours=5, minutes=30))
    assert care.monthly(datetime(2026, 11, 2, 10, tzinfo=ist)) == 0
    assert care.monthly(datetime(2026, 11, 1, 8, tzinfo=ist)) == 0
    assert care.monthly(datetime(2026, 11, 1, 10, tzinfo=ist)) == 1
    assert care.monthly(datetime(2026, 11, 1, 11, tzinfo=ist)) == 0
    note = _events("site_care")[-1]
    assert note["month"] == "2026-10" and note["push"] and "visit" in note["say"]


def test_agency_staff_only_on_their_sites_and_client_summary(care_env):
    from app.agent.tools import Ctx, ToolError, dispatch
    from app.site import care
    from app.site import service as S
    g, ctx = _ready_site()
    other = S.new(T, "dental clinic ki website", ctx.conversation_id, name="Smile Dental", answers={"phone": "9876500000"})
    owner = Ctx(T, ctx.conversation_id, actor="owner")
    staff = Ctx(T, ctx.conversation_id, actor="staff:asha")
    with pytest.raises(ToolError):
        asyncio.run(dispatch("website", {"action": "assign", "site": g["id"], "staff": "asha"}, staff))   # owner only
    asyncio.run(dispatch("website", {"action": "assign", "site": g["id"], "client": "Sharma ji", "staff": "asha"}, owner))
    asyncio.run(dispatch("website", {"action": "assign", "site": other["id"], "client": "Dr Patil"}, owner))
    assert care.staff_ok(T, g["id"], "staff:asha") and not care.staff_ok(T, other["id"], "staff:asha")
    from app.agent.site_tools import _act        # past the employee gate (staff with the web_work duty)
    with pytest.raises(ToolError, match="assign"):
        _act(staff, "change", {"site": other["id"], "instruction": "rang halka"})
    assert _act(staff, "care", {"site": g["id"]})["views"] == 0
    cl = {x["client"]: x for x in care.clients(T)}
    assert set(cl) == {"Sharma ji", "Dr Patil"} and cl["Sharma ji"]["sites"][0]["staff"] == "asha"
    rep = asyncio.run(dispatch("website", {"action": "client_report", "client": "dr patil"}, owner))
    assert "Smile Dental" in rep["text"]


def test_github_export_only_on_her_tap(care_env):
    from app.main import app
    from app.site import dns as D
    from app.site import github as GH
    c = TestClient(app)
    g, ctx = _ready_site()
    gh = care_env["gh"]
    with pytest.raises(GH.GithubError):
        GH.request(T, g["id"])                                                  # no token yet
    assert c.put("/api/sites-keys/github", json={"token": "short"}).status_code == 400
    r = c.put("/api/sites-keys/github", json={"token": GH_TOKEN}).json()
    assert r["label"] == "@meghana" and GH_TOKEN not in json.dumps(c.get("/api/sites-keys").json())
    card = c.post(f"/api/sites/{g['id']}/github-request", json={}).json()
    assert card["repo"] == "meghana/sharma-sweets-website" and card["private"] and _events("site_github")[-1]["push"]
    assert not gh.repos                                                          # the card changes nothing
    assert c.post(f"/api/sites-github/{card['id']}/push", json={"hash": "x"}).status_code == 400
    out = c.post(f"/api/sites-github/{card['id']}/push", json={"hash": card["hash"]}).json()
    assert out["url"] == "https://github.com/meghana/sharma-sweets-website"
    assert gh.repos["sharma-sweets-website"]["private"] is True
    head = gh.refs[("sharma-sweets-website", "main")]
    tree = {t["path"]: gh.blobs[t["sha"]] for t in gh.trees[gh.commits[head]["tree"]]}
    assert "index.html" in tree and "README.md" in tree and "contact/index.html" in tree
    assert b'content="noindex"' not in tree["index.html"] and tree["robots.txt"].startswith(b"User-agent: *\nAllow")
    assert c.post(f"/api/sites-github/{card['id']}/push", json={"hash": card["hash"]}).status_code == 400   # once
    assert GH.exports(T, g["id"])[0]["status"] == "done"
