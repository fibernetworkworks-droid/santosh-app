"""v0.280 DIRECT MODE, how Lovable does it: with SITES_DIRECT_IP her domain points straight at Hoola's server (A @ + A www,
DNS only) and a `_hoola` TXT proves it is hers; the worker walks Verifying -> Setting up -> Live; the edge (Caddy on-demand
TLS) may only ask for a certificate once her records point here; one address is primary and the other 301-redirects; an
orange-cloud A record becomes DNS only; a domain bought through Hoola on Newtika's Cloudflare account gets its records at
once (only adds, nothing of hers changed)."""
from urllib.parse import urlparse

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.db import Event, session
from tests.test_v122_hosting import HER_TOKEN, HOOLA_TOKEN, _ready_site, host_env  # noqa: F401  (fixture)

T = "default"
IP = "139.59.10.30"


def _events(kind):
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.kind == kind).order_by(Event.id)).all()]


def _direct(host_env, world):
    """SITES_DIRECT_IP on + a DNS world the test controls (name, type) -> [answers]."""
    from app.config import get_settings
    from app.site import dns as D
    mp = host_env["monkeypatch"]
    mp.setenv("SITES_DIRECT_IP", IP)
    get_settings.cache_clear()
    mp.setattr(D, "lookup", lambda name, type_="A": {r: list(world.get((name, type_), [])) for r in ("cf", "google", "quad9")})


def _tick():
    """One worker pass with the 60 s gap between checks taken away."""
    from app.site import hosting as H
    from app.site.hosting_models import SiteHost
    with session() as s:
        s.execute(update(SiteHost).values(last_check=None))
    return H.watch()


def _hosts(site_id):
    from app.site.hosting_models import SiteHost
    with session() as s:
        return {x.hostname: (x.status, x.ssl_status, x.role, x.problem) for x in
                s.scalars(select(SiteHost).where(SiteHost.site_id == site_id, SiteHost.status != "removed")).all()}


def test_direct_domain_verifying_setting_up_live(host_env):
    from app.main import app
    from app.site import hosting as H
    world = {}
    _direct(host_env, world)
    assert H.direct_on()
    c = TestClient(app)
    g, _ = _ready_site()
    card = c.post(f"/api/sites/{g['id']}/domain", json={"domain": "https://www.mithaighar.in/"}).json()
    assert card["mode"] == "direct" and card["primary"] == "mithaighar.in"         # Lovable's default: root is main
    token = H.verify_token(T, "mithaighar.in")
    assert token.startswith("hoola_verify=") and token == H.verify_token(T, "mithaighar.in") != H.verify_token("other", "mithaighar.in")
    assert {(x["type"], x["name"], x["value"]) for x in card["records"]} == {
        ("A", "mithaighar.in", IP), ("A", "www.mithaighar.in", IP), ("TXT", "_hoola.mithaighar.in", token)}
    assert card["plan"]["provider"] == "manual" and any("'_hoola'" in s for s in card["plan"]["manual_steps"])
    # records not there yet: Verifying, with the exact missing record; the edge may not ask for a certificate
    _tick()
    h = _hosts(g["id"])
    assert h["mithaighar.in"][:3] == ("pending", "dns", "main") and h["www.mithaighar.in"][2] == "redirect"
    assert f"A -> {IP}" in h["mithaighar.in"][3]
    st = c.get(f"/api/sites/{g['id']}/hosting").json()
    assert st["direct"] and {x["host"]: x["stage"] for x in st["hosts"]}["mithaighar.in"] == "Verifying"
    shown = {x["host"]: x for x in st["hosts"]}["mithaighar.in"]["records"]
    assert {(x["type"], x["name"], x["value"]) for x in shown} == {
        ("A", "mithaighar.in", IP), ("A", "www.mithaighar.in", IP), ("TXT", "_hoola.mithaighar.in", token)}
    # she launches before DNS is done: the free address works at once, her domain waits
    lc = c.post(f"/api/sites/{g['id']}/launch-request", json={}).json()
    assert set(lc["hosts"]) == {"mithaighar.in", "www.mithaighar.in", "sharma-sweets.hoolasites.in"}
    assert c.post(f"/api/sites/{g['id']}/launch", json={"hash": lc["hash"]}).status_code == 200
    assert c.get("/api/hosting/ask?domain=sharma-sweets.hoolasites.in").status_code == 200
    assert c.get("/api/hosting/ask?domain=mithaighar.in").status_code == 404        # not pointing here yet
    # her A records + the TXT appear worldwide -> Setting up; the edge may now make the certificate
    world[("mithaighar.in", "A")] = [IP]
    world[("www.mithaighar.in", "A")] = [IP]
    world[("_hoola.mithaighar.in", "TXT")] = [token]
    fetched = []
    host_env["monkeypatch"].setattr(H, "_fetch_ok", lambda host: fetched.append(host) or False)
    _tick()
    assert _hosts(g["id"])["mithaighar.in"][:2] == ("pending", "ssl")
    assert c.get("/api/hosting/ask?domain=mithaighar.in").status_code == 200
    assert {x["host"]: x["stage"] for x in H.status(T, g["id"])["hosts"]}["mithaighar.in"] == "Setting up"
    # the first https visit works -> Live + one note to her
    host_env["monkeypatch"].setattr(H, "_fetch_ok", lambda host: True)
    _tick()
    assert _hosts(g["id"])["mithaighar.in"][:2] == ("active", "active")
    assert any(e.get("url") == "https://mithaighar.in/" for e in _events("site_live"))
    # root is main: the site is served there, www 301s to it, the free address keeps working
    home = c.get("/", headers={"host": "mithaighar.in"})
    assert home.status_code == 200 and 'rel="canonical" href="https://mithaighar.in/"' in home.text
    r = c.get("/contact/", headers={"host": "www.mithaighar.in"}, follow_redirects=False)
    assert r.status_code == 301 and r.headers["location"] == "https://mithaighar.in/contact/"
    assert c.get("/", headers={"host": "sharma-sweets.hoolasites.in"}).status_code == 200
    assert "www.mithaighar.in" not in H.uptime_targets() and "mithaighar.in" in H.uptime_targets()


def test_someone_elses_txt_or_another_ip_never_verifies(host_env):
    from app.site import hosting as H
    world = {}
    _direct(host_env, world)
    g, _ = _ready_site()
    H.connect_domain(T, g["id"], "mithaighar.in")
    world[("mithaighar.in", "A")] = [IP]
    world[("www.mithaighar.in", "A")] = [IP]
    world[("_hoola.mithaighar.in", "TXT")] = [H.verify_token("someone-else", "mithaighar.in")]
    _tick()
    h = _hosts(g["id"])["mithaighar.in"]
    assert h[1] == "dns" and "_hoola.mithaighar.in" in h[3]
    world[("_hoola.mithaighar.in", "TXT")] = [H.verify_token(T, "mithaighar.in")]
    world[("mithaighar.in", "A")] = ["104.21.3.4"]                               # still behind Cloudflare's proxy
    _tick()
    h = _hosts(g["id"])["mithaighar.in"]
    assert h[1] == "dns" and "orange cloud" in h[3] and IP in h[3]


def test_primary_switch_to_www(host_env):
    from app.main import app
    from app.site import hosting as H
    world = {}
    _direct(host_env, world)
    c = TestClient(app)
    g, _ = _ready_site()
    H.connect_domain(T, g["id"], "mithaighar.in", primary="www")
    assert _hosts(g["id"])["www.mithaighar.in"][2] == "main"
    lc = H.launch_request(T, g["id"])
    H.launch(T, g["id"], lc["hash"])
    out = c.post(f"/api/sites/{g['id']}/primary", json={"host": "mithaighar.in"}).json()
    assert out["primary"] == "mithaighar.in"
    h = _hosts(g["id"])
    assert h["mithaighar.in"][2] == "main" and h["www.mithaighar.in"][2] == "redirect"
    home = c.get("/", headers={"host": "mithaighar.in"})
    assert home.status_code == 200 and 'href="https://mithaighar.in/"' in home.text
    assert c.get("/", headers={"host": "www.mithaighar.in"}, follow_redirects=False).headers["location"] == "https://mithaighar.in/"
    assert c.get("/", headers={"host": "sharma-sweets.hoolasites.in"}).status_code == 200
    assert c.post(f"/api/sites/{g['id']}/primary", json={"host": "evil.example"}).status_code == 400


def test_her_cloudflare_orange_cloud_becomes_dns_only(host_env):
    from app.site import dns as D
    from app.site import hosting as H
    cloud = host_env["cloud"]
    cloud.records["zHER"][0].update(content=IP, proxied=True)                       # A @ -> us, but orange cloud
    D.set_key(T, "cloudflare", HER_TOKEN)
    from app.config import get_settings
    host_env["monkeypatch"].setenv("SITES_DIRECT_IP", IP)
    get_settings.cache_clear()
    g, _ = _ready_site()
    card = H.connect_domain(T, g["id"], "sharmasweets.in")
    pl = card["plan"]
    assert pl["provider"] == "cloudflare" and "orange cloud" in card["say"]
    ops = {(c_["op"], c_["type"], c_["name"]) for c_ in pl["changes"]}
    assert ("update", "A", "sharmasweets.in") in ops and ("add", "A", "www.sharmasweets.in") in ops
    assert ("add", "TXT", "_hoola.sharmasweets.in") in ops
    assert any("orange cloud" in r for r in pl["risks"])
    H.dns_apply(T, pl["id"], pl["hash"])                                             # her tap
    recs = {(r["type"], r["name"]): r for r in cloud.records["zHER"]}
    assert recs[("A", "sharmasweets.in")]["proxied"] is False and recs[("A", "www.sharmasweets.in")]["proxied"] is False
    assert recs[("TXT", "_hoola.sharmasweets.in")]["content"] == H.verify_token(T, "sharmasweets.in")
    assert ("MX", "sharmasweets.in") in recs                                          # her email untouched


def test_domain_bought_on_newtika_account_gets_records_at_once(host_env):
    from app.config import get_settings
    from app.site import cf, dns as D, hosting as H
    from app.site.domains import SiteDomain, _join_site
    cloud = host_env["cloud"]
    base = cloud.handler

    def handler(req):                                       # Newtika's account holds the zone of the domain she bought
        u = urlparse(str(req.url))
        if u.path.endswith("/zones") and req.headers.get("authorization", "") == f"Bearer {HOOLA_TOKEN}":
            return httpx.Response(200, json={"success": True, "errors": [], "result": [
                {"id": "zNEW", "name": "mithaighar.com", "status": "active", "name_servers": ["x.ns.cloudflare.com"]}]})
        return base(req)
    t = httpx.MockTransport(handler)
    cf.set_transport(t)
    D.set_transport(t)
    mp = host_env["monkeypatch"]
    mp.setenv("SITES_DIRECT_IP", IP)
    mp.setenv("SITES_RESELL", "true")
    mp.setenv("SITES_REG_CF_TOKEN", HOOLA_TOKEN)
    mp.setenv("SITES_REG_CF_ACCOUNT", "a" * 32)
    get_settings.cache_clear()
    g, _ = _ready_site()
    with session() as s:
        o = SiteDomain(tenant_id=T, site_id=g["id"], domain="mithaighar.com", registrar="cloudflare", account="hoola",
                       status="registered")
        s.add(o)
        s.flush()
        s.expunge(o)
    say = _join_site(T, o)
    assert "laga diye" in say
    recs = {(r["type"], r["name"]): r for r in cloud.records["zNEW"]}
    assert recs[("A", "mithaighar.com")]["content"] == IP and recs[("A", "mithaighar.com")]["proxied"] is False
    assert recs[("TXT", "_hoola.mithaighar.com")]["content"] == H.verify_token(T, "mithaighar.com")
    # a domain bought on HER own account (not Newtika's) never gets this shortcut
    with session() as s:
        s.add(SiteDomain(tenant_id=T, site_id=g["id"], domain="other.com", registrar="cloudflare", account="own",
                         status="registered"))
    assert D.where_is(T, "other.com")["provider"] == "manual"


def test_saas_still_wins_and_nothing_without_a_route(host_env):
    from app.config import get_settings
    from app.site import hosting as H
    g, _ = _ready_site()
    assert not H.direct_on()
    import pytest
    with pytest.raises(H.HostError) as e:
        H.connect_domain(T, g["id"], "mithaighar.in")
    assert "SITES_DIRECT_IP" in str(e.value)
    mp = host_env["monkeypatch"]
    mp.setenv("SITES_DIRECT_IP", IP)
    mp.setenv("SITES_CF_TOKEN", HOOLA_TOKEN)
    mp.setenv("SITES_CF_ZONE_ID", "zHOOLA")
    mp.setenv("SITES_ORIGIN", "origin.hoolasites.in")
    get_settings.cache_clear()
    assert H.saas_on() and not H.direct_on()
    get_settings.cache_clear()


def test_version():
    from pathlib import Path
    from app.main import APP_VERSION
    assert APP_VERSION == "0.312.0"
    assert "0.312.0+351" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
