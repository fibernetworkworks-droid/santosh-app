"""v0.122 Website hosting: launch only on her tap (free Hoola address + her domain), serving by hostname, her domain via
Cloudflare for SaaS with a DNS plan applied only on her tap (snapshot, undo, zone-changed guard), worldwide check from 3
resolvers, pending -> active, rollback on her tap, uptime alerts, email DNS (one SPF), guards. Fake Cloudflare + DoH."""
import json
import re
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import Event, session
from tests.test_life import conv_ctx
from tests.test_v121_site import FakeAI

T = "default"
HER_TOKEN = "her-cloudflare-token-0123456789abcdef"
HOOLA_TOKEN = "hoola-saas-token-0123456789abcdef"


def _events(kind):
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.kind == kind).order_by(Event.id)).all()]


class FakeCloud:
    """Cloudflare v4 API (two accounts: hers with her zone, Hoola's with the SaaS zone) + 3 DoH resolvers that see
    what is in her zone."""

    def __init__(self):
        self.zones = {"zHER": {"id": "zHER", "name": "sharmasweets.in", "status": "active",
                               "name_servers": ["ana.ns.cloudflare.com", "bob.ns.cloudflare.com"]}}
        self.records = {"zHER": [
            {"id": "r1", "type": "A", "name": "sharmasweets.in", "content": "203.0.113.9", "proxied": False, "ttl": 1},
            {"id": "r2", "type": "MX", "name": "sharmasweets.in", "content": "mx.zoho.in", "priority": 10, "ttl": 1},
            {"id": "r3", "type": "TXT", "name": "sharmasweets.in", "content": "v=spf1 include:zoho.in ~all", "ttl": 1}]}
        self.custom = {}
        self.n = 10
        self.calls = []

    def handler(self, req: httpx.Request) -> httpx.Response:
        u = urlparse(str(req.url))
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.hostname in ("cloudflare-dns.com", "dns.google", "dns.quad9.net"):
            return self.doh(q)
        tok = req.headers.get("authorization", "").removeprefix("Bearer ")
        path = u.path.replace("/client/v4", "")
        body = json.loads(req.content or b"{}") if req.content else {}
        self.calls.append((req.method, path, tok))

        def ok(result):
            return httpx.Response(200, json={"success": True, "errors": [], "result": result})
        if tok not in (HER_TOKEN, HOOLA_TOKEN):
            return httpx.Response(403, json={"success": False, "errors": [{"code": 9109, "message": "Invalid access token"}]})
        if path == "/user/tokens/verify":
            return ok({"id": "t", "status": "active"})
        if path == "/zones":
            if tok != HER_TOKEN:
                return ok([])
            return ok([z for z in self.zones.values() if z["name"] == q.get("name")] if q.get("name") else list(self.zones.values()))
        m = re.match(r"^/zones/(\w+)/dns_records(?:/(\w+))?$", path)
        if m:
            zid, rid = m.groups()
            recs = self.records.setdefault(zid, [])
            if req.method == "GET":
                return ok([r for r in recs if (not q.get("name") or r["name"] == q["name"]) and (not q.get("type") or r["type"] == q["type"])])
            if req.method == "POST":
                self.n += 1
                rec = {"id": f"r{self.n}", **body}
                recs.append(rec)
                return ok(rec)
            rec = next(r for r in recs if r["id"] == rid)
            if req.method == "PATCH":
                rec.update(body)
                return ok(rec)
            if req.method == "DELETE":
                recs.remove(rec)
                return ok({"id": rid})
        m = re.match(r"^/zones/zHOOLA/custom_hostnames(?:/(\w+))?$", path)
        if m:
            assert tok == HOOLA_TOKEN
            hid = m.group(1)
            if req.method == "POST":
                self.n += 1
                h = {"id": f"ch{self.n}", "hostname": body["hostname"], "status": "pending",
                     "ownership_verification": {"type": "txt", "name": f"_cf-custom-hostname.{body['hostname']}", "value": f"tok-{self.n}"},
                     "ssl": {"status": "pending_validation", "validation_records": []}}
                self.custom[h["id"]] = h
                return ok(h)
            if req.method == "GET" and not hid:
                return ok([h for h in self.custom.values() if h["hostname"] == q.get("hostname")])
            if req.method == "GET":
                return ok(self.custom[hid])
            if req.method == "DELETE":
                self.custom.pop(hid, None)
                return ok({"id": hid})
        return httpx.Response(404, json={"success": False, "errors": [{"code": 7003, "message": f"no route {path}"}]})

    def doh(self, q):
        name, typ = q.get("name", "").rstrip("."), q.get("type", "A")
        num = {"A": 1, "CNAME": 5, "MX": 15, "TXT": 16, "NS": 2}[typ]
        ans = []
        for r in self.records.get("zHER", []):
            if r["name"] == name and r["type"] == typ:
                data = r["content"] if typ != "TXT" else f'"{r["content"]}"'
                ans.append({"name": name, "type": num, "TTL": 300, "data": data + ("." if typ in ("CNAME", "MX") else "")})
        if typ == "NS" and name == "sharmasweets.in":
            ans = [{"name": name, "type": 2, "data": "ana.ns.cloudflare.com."}]
        return httpx.Response(200, json={"Status": 0, "Answer": ans})


@pytest.fixture
def host_env(env, monkeypatch, tmp_path):
    from app.config import get_settings
    from app.site import ai as AI
    from app.site import cf, dns, hosting
    monkeypatch.setenv("SITE_DIR", str(tmp_path / "sites"))
    monkeypatch.setenv("SITE_HOSTED_DIR", str(tmp_path / "hosted"))
    monkeypatch.setenv("SITE_WORKER", "false")
    monkeypatch.setenv("SITE_LIGHTHOUSE", "false")
    monkeypatch.setenv("SITES_BASE_DOMAIN", "hoolasites.in")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://api.hoola.example")
    get_settings.cache_clear()
    fake = FakeAI()
    fake.blank = False
    monkeypatch.setattr(AI, "ask_json", fake)
    cloud = FakeCloud()
    t = httpx.MockTransport(cloud.handler)
    cf.set_transport(t)
    dns.set_transport(t)
    yield {"ai": fake, "cloud": cloud, "monkeypatch": monkeypatch}
    cf.set_transport(None)
    dns.set_transport(None)
    hosting.set_transport(None)
    hosting.host_map(force=True)


def _ready_site(name="Sharma Sweets", brief="mithai dukaan ki website"):
    from app.site import service as S
    ctx = conv_ctx()
    v = S.new(T, brief, ctx.conversation_id, name=name, answers={"phone": "9876543210", "address": "Main Road, Akot"})
    S.approve_plan(T, v["id"], pages=["contact"])
    S.choose_look(T, v["id"], 0)
    g = S.get(T, v["id"])
    assert g["status"] == "ready" and g["checks"]["passed"], g["checks"]
    return g, ctx


def test_free_launch_only_on_her_tap_and_served_by_hostname(host_env):
    from app.main import app
    from app.site import hosting as H
    c = TestClient(app)
    g, _ = _ready_site()
    card = c.post(f"/api/sites/{g['id']}/launch-request", json={}).json()
    assert card["hosts"] == ["sharma-sweets.hoolasites.in"] and not card["blockers"] and card["hash"]
    assert _events("site_launch")[-1]["push"] is True
    # nothing is live before her tap
    assert c.get("/", headers={"host": "sharma-sweets.hoolasites.in"}).status_code != 200 or \
        "generator" not in c.get("/", headers={"host": "sharma-sweets.hoolasites.in"}).text
    assert c.post(f"/api/sites/{g['id']}/launch", json={"hash": "wrong"}).status_code == 400
    r = c.post(f"/api/sites/{g['id']}/launch", json={"hash": card["hash"]})
    assert r.status_code == 200, r.text
    assert r.json()["url"] == "https://sharma-sweets.hoolasites.in/"
    home = c.get("/", headers={"host": "sharma-sweets.hoolasites.in"})
    assert home.status_code == 200 and 'name="generator" content="Hoola"' in home.text
    assert 'rel="canonical" href="https://sharma-sweets.hoolasites.in/"' in home.text and "noindex" not in home.text
    assert "script-src 'self'" in home.headers["content-security-policy"] and "max-age=31536000" in home.headers["strict-transport-security"]
    assert "https://api.hoola.example" in home.headers["content-security-policy"]       # forms post to Hoola
    css = c.get("/assets/site.css", headers={"host": "sharma-sweets.hoolasites.in"})
    assert css.status_code == 200 and "max-age=604800" in css.headers["cache-control"]
    sm = c.get("/sitemap.xml", headers={"host": "sharma-sweets.hoolasites.in"})
    assert "https://sharma-sweets.hoolasites.in/contact/" in sm.text
    assert c.get("/contact", headers={"host": "sharma-sweets.hoolasites.in"}, follow_redirects=False).status_code == 301
    assert c.get("/nope/", headers={"host": "sharma-sweets.hoolasites.in"}).status_code == 404
    assert c.get("/../../etc/passwd", headers={"host": "sharma-sweets.hoolasites.in"}).status_code == 404
    assert c.get("/_headers", headers={"host": "sharma-sweets.hoolasites.in"}).status_code == 404
    # a site's address serves only the site, never Hoola's API
    assert c.get("/api/sites", headers={"host": "sharma-sweets.hoolasites.in"}).status_code == 404
    assert c.get("/api/hosting/ask?domain=sharma-sweets.hoolasites.in").status_code == 200
    assert c.get("/api/hosting/ask?domain=evil.example").status_code == 404
    assert _events("site_live")[-1]["url"] == "https://sharma-sweets.hoolasites.in/"
    st = H.status(T, g["id"])
    assert st["hosts"][0]["status"] == "active" and st["hosts"][0]["live_version"] == 1


def test_blanks_block_launch(host_env):
    from app.site import hosting as H
    host_env["ai"].blank = True
    g, _ = _ready_site("Glow Salon", "salon ki website")
    card = H.launch_request(T, g["id"])
    assert any("[blank]" in b for b in card["blockers"])
    with pytest.raises(H.HostError):
        H.launch(T, g["id"], card["hash"])


def test_her_domain_saas_dns_plan_apply_undo_and_activation(host_env):
    from app.main import app
    from app.site import dns as D
    from app.site import hosting as H
    mp, cloud = host_env["monkeypatch"], host_env["cloud"]
    mp.setenv("SITES_CF_TOKEN", HOOLA_TOKEN)
    mp.setenv("SITES_CF_ZONE_ID", "zHOOLA")
    mp.setenv("SITES_ORIGIN", "origin.hoolasites.in")
    from app.config import get_settings
    get_settings.cache_clear()
    c = TestClient(app)
    g, _ = _ready_site()
    # her Cloudflare token is typed in the app only, verified, sealed
    assert c.put("/api/sites-keys/cloudflare", json={"token": "short"}).status_code == 400
    r = c.put("/api/sites-keys/cloudflare", json={"token": HER_TOKEN})
    assert r.status_code == 200 and HER_TOKEN not in r.text
    from app.site.hosting_models import SiteHostingKey
    with session() as s:
        assert HER_TOKEN not in s.scalars(select(SiteHostingKey)).first().sealed
    card = c.post(f"/api/sites/{g['id']}/domain", json={"domain": "https://www.SharmaSweets.in/"}).json()
    assert card["domain"] == "sharmasweets.in" and card["mode"] == "saas"
    assert {h["hostname"] for h in cloud.custom.values()} == {"www.sharmasweets.in", "sharmasweets.in"}
    plan = card["plan"]
    ops = {(x["op"], x["type"], x["name"]) for x in plan["changes"]}
    assert ("add", "CNAME", "www.sharmasweets.in") in ops
    assert ("update", "CNAME", "sharmasweets.in") in ops                      # old A record -> Hoola, with a risk line
    assert any("pehle A 203.0.113.9" in x for x in plan["risks"])
    assert sum(1 for x in plan["changes"] if x["type"] == "TXT" and x["name"].startswith("_cf-custom-hostname")) == 2
    assert not any(x["type"] == "MX" for x in plan["changes"])                 # mail untouched
    assert _events("site_dns")[-1]["push"] is True
    # her tap with a wrong hash is refused; nothing changed
    assert c.post(f"/api/sites-dns/{plan['id']}/apply", json={"hash": "x"}).status_code == 400
    assert len(cloud.records["zHER"]) == 3
    # zone changed after the plan -> refused, fresh plan needed
    cloud.records["zHER"].append({"id": "rX", "type": "TXT", "name": "sharmasweets.in", "content": "google-site-verification=abc"})
    assert c.post(f"/api/sites-dns/{plan['id']}/apply", json={"hash": plan["hash"]}).status_code == 400
    cloud.records["zHER"].pop()
    r = c.post(f"/api/sites-dns/{plan['id']}/apply", json={"hash": plan["hash"]})
    assert r.status_code == 200, r.text
    apex = [x for x in cloud.records["zHER"] if x["name"] == "sharmasweets.in" and x["type"] == "CNAME"]
    assert apex and apex[0]["content"] == "origin.hoolasites.in" and apex[0]["proxied"] is False
    assert any(x["type"] == "MX" for x in cloud.records["zHER"])
    chk = c.get(f"/api/sites-dns/{plan['id']}/check").json()
    assert chk["done"] is True and all(x["seen"] == 3 for x in chk["checks"])
    # launch: her domain is the main address, the free one serves the same files
    card2 = H.launch_request(T, g["id"])
    assert set(card2["hosts"]) == {"www.sharmasweets.in", "sharmasweets.in", "sharma-sweets.hoolasites.in"}
    out = H.launch(T, g["id"], card2["hash"])
    assert out["url"] == "https://www.sharmasweets.in/" and "DNS / SSL" in out["say"]
    home = c.get("/", headers={"host": "www.sharmasweets.in"})
    assert 'href="https://www.sharmasweets.in/"' in home.text
    assert c.get("/", headers={"host": "sharmasweets.in"}, follow_redirects=False).headers["location"] == "https://www.sharmasweets.in/"
    assert 'href="https://www.sharmasweets.in/"' in c.get("/", headers={"host": "sharma-sweets.hoolasites.in"}).text
    # Cloudflare finishes -> the watcher marks it active and tells her
    for h in cloud.custom.values():
        h["status"], h["ssl"]["status"] = "active", "active"
    H.watch(T)
    st = {h["host"]: h["status"] for h in H.status(T, g["id"])["hosts"]}
    assert st["www.sharmasweets.in"] == "active"
    assert any("www.sharmasweets.in" in e["say"] for e in _events("site_live"))
    # undo puts her zone back exactly
    D.undo(T, plan["id"])
    assert sorted((x["type"], x["name"], x["content"]) for x in cloud.records["zHER"]) == sorted(
        [("A", "sharmasweets.in", "203.0.113.9"), ("MX", "sharmasweets.in", "mx.zoho.in"),
         ("TXT", "sharmasweets.in", "v=spf1 include:zoho.in ~all")])


def test_manual_dns_when_not_on_her_cloudflare_and_guards(host_env):
    from app.site import hosting as H
    mp = host_env["monkeypatch"]
    mp.setenv("SITES_CF_TOKEN", HOOLA_TOKEN)
    mp.setenv("SITES_CF_ZONE_ID", "zHOOLA")
    mp.setenv("SITES_ORIGIN", "origin.hoolasites.in")
    from app.config import get_settings
    get_settings.cache_clear()
    g, _ = _ready_site()
    card = H.connect_domain(T, g["id"], "akotsweets.co.in")
    assert card["plan"]["provider"] == "manual" and card["plan"]["status"] == "manual"
    steps = " ".join(card["plan"]["manual_steps"])
    assert "Host/Name 'www'" in steps and "origin.hoolasites.in" in steps and "password aap khud" in steps
    assert "forwarding" in card["say"]
    with pytest.raises(H.HostError):
        H.connect_domain(T, g["id"], "sbi-offers.in")
    with pytest.raises(Exception):
        H.connect_domain(T, g["id"], "not a domain")


def test_rollback_uptime_takedown_and_email_dns(host_env):
    from app.main import app
    from app.site import dns as D
    from app.site import hosting as H
    from app.site import service as S
    c = TestClient(app)
    g, ctx = _ready_site()
    card = H.launch_request(T, g["id"])
    H.launch(T, g["id"], card["hash"])
    host = "sharma-sweets.hoolasites.in"
    # v2 with a marker, launched
    host_env["ai"].marker = "DIWALI-OFFER"
    host_env["ai"].change = {"say": "ok", "sections": [{"key": "home__hero", "instruction": "Diwali offer"}]}
    S.change(T, g["id"], "hero mein Diwali offer")
    card = H.launch_request(T, g["id"])
    H.launch(T, g["id"], card["hash"])
    assert "DIWALI-OFFER" in c.get("/", headers={"host": host}).text
    # rollback to v1 only with the card's hash
    rb = c.post(f"/api/sites/{g['id']}/rollback-request", json={"version": 1}).json()
    assert c.post(f"/api/sites/{g['id']}/rollback", json={"version": 1, "hash": "nope"}).status_code == 400
    assert c.post(f"/api/sites/{g['id']}/rollback", json={"version": 1, "hash": rb["hash"]}).status_code == 200
    page = c.get("/", headers={"host": host}).text
    assert "DIWALI-OFFER" not in page and "noindex" not in page
    # uptime: two misses -> one alert with a reason; back -> ok note
    H.set_transport(httpx.MockTransport(lambda req: httpx.Response(503, text="down")))
    from app.site.hosting_models import SiteHost
    with session() as s:
        for h in s.scalars(select(SiteHost)).all():
            h.last_check = None
    H.watch(T)
    with session() as s:
        for h in s.scalars(select(SiteHost)).all():
            h.last_check = None
    H.watch(T)
    downs = _events("site_down")
    assert len(downs) == 1 and downs[0]["push"] is True and host in downs[0]["say"]
    H.set_transport(httpx.MockTransport(lambda req: httpx.Response(200, text='<meta name="generator" content="Hoola">')))
    with session() as s:
        for h in s.scalars(select(SiteHost)).all():
            h.last_check = None
    H.watch(T)
    assert _events("site_down")[-1].get("ok") is True
    # email at her domain: SPF merged into ONE record, DMARC added, existing MX kept
    c.put("/api/sites-keys/cloudflare", json={"token": HER_TOKEN})
    p = c.post(f"/api/sites/{g['id']}/email-dns", json={"domain": "sharmasweets.in", "provider": "google",
                                                        "report_to": "owner@sharmasweets.in"}).json()
    spf = [x for x in p["changes"] if x["type"] == "TXT" and x["content"].startswith("v=spf1")]
    assert len(spf) == 1 and spf[0]["op"] == "update" and "include:zoho.in" in spf[0]["content"] and "include:_spf.google.com" in spf[0]["content"]
    assert any(x["name"] == "_dmarc.sharmasweets.in" and x["op"] == "add" and "rua=mailto:owner@sharmasweets.in" in x["content"]
               for x in p["changes"])
    assert any(x["type"] == "MX" and x["content"] == "smtp.google.com" and x["op"] == "add" for x in p["changes"])
    # takedown (owner only via tools)
    import asyncio
    from app.agent.tools import Ctx, ToolError, dispatch
    with pytest.raises(ToolError):
        asyncio.run(dispatch("website", {"action": "takedown", "site": g["id"]}, Ctx(T, ctx.conversation_id, actor="staff:x")))
    out = asyncio.run(dispatch("website", {"action": "takedown", "site": g["id"]}, ctx))
    assert "band" in out["say"]
    assert c.get("/", headers={"host": host}).status_code != 200 or 'content="Hoola"' not in c.get("/", headers={"host": host}).text
    lr = asyncio.run(dispatch("website", {"action": "launch", "site": g["id"]}, ctx))
    assert "Haan, live karo" in lr["say"]
