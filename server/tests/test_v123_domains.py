"""v0.123 Domains: ideas + live price in rupees (first year AND renewal) from Cloudflare Registrar / Porkbun, buying only
on her tap with the card's hash (fingerprint kind 'domain'), price change -> new card, monthly ceiling, .in KYC reminders,
renewal reminders, Porkbun DNS applied on her tap, tools never buy. Fake registrars over httpx.MockTransport."""
import json
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import Event, session
from tests.test_life import conv_ctx
from tests.test_v121_site import FakeAI

T = "default"
CF_TOKEN = "her-registrar-token-0123456789abcdef"
CF_ACCOUNT = "0123456789abcdef0123456789abcdef"
PB_KEY = "pk1_0123456789abcdef0123456789abcdef"
PB_SECRET = "sk1_0123456789abcdef0123456789abcdef"


def _events(kind):
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.kind == kind).order_by(Event.id)).all()]


class FakeRegistrars:
    def __init__(self):
        self.cf_price = {"sharmasweetsakot.com": 10.44, "sharmasweetsonline.com": 10.44}
        self.cf_taken = {"sharmasweets.com"}
        self.cf_state = "in_progress"
        self.pb_price = {"sharmasweets.in": 7.83, "sharmasweets.shop": 2.0}
        self.pb_records = {"sharmasweets.in": [{"id": "1", "name": "sharmasweets.in", "type": "A", "content": "198.51.100.7",
                                                "ttl": "600", "prio": "0"}]}
        self.created, self.registered = [], []
        self.n = 100

    def handler(self, req: httpx.Request) -> httpx.Response:
        u = urlparse(str(req.url))
        body = json.loads(req.content or b"{}") if req.content else {}
        if u.hostname == "api.porkbun.com":
            return self.porkbun(u.path.replace("/api/json/v3", ""), body)
        tok = req.headers.get("authorization", "").removeprefix("Bearer ")
        path = u.path.replace("/client/v4", "")

        def ok(result, code=200):
            return httpx.Response(code, json={"success": True, "errors": [], "result": result})
        if tok != CF_TOKEN:
            return httpx.Response(403, json={"success": False, "errors": [{"code": 9109, "message": "Invalid access token"}]})
        if path == "/user/tokens/verify":
            return ok({"status": "active"})
        if path == "/zones":
            return ok([])
        if path == f"/accounts/{CF_ACCOUNT}/registrar/domain-check":
            out = []
            for d in body["domains"]:
                if d.endswith((".in", ".shop")):
                    out.append({"name": d, "registrable": False, "reason": "extension_not_supported_via_api"})
                elif d in self.cf_taken:
                    out.append({"name": d, "registrable": False, "reason": "domain_unavailable"})
                else:
                    p = self.cf_price.get(d, 10.44)
                    out.append({"name": d, "registrable": True, "tier": "standard",
                                "pricing": {"currency": "USD", "registration_cost": f"{p:.2f}", "renewal_cost": f"{p:.2f}"}})
            return ok({"domains": out})
        if path == f"/accounts/{CF_ACCOUNT}/registrar/registrations" and req.method == "POST":
            self.registered.append(body)
            return ok({"domain_name": body["domain_name"], "state": "in_progress"}, 202)
        m = re.match(rf"^/accounts/{CF_ACCOUNT}/registrar/registrations/([\w.-]+)/registration-status$", path)
        if m:
            return ok({"domain_name": m.group(1), "state": self.cf_state})
        return httpx.Response(404, json={"success": False, "errors": [{"code": 7003, "message": f"no route {path}"}]})

    def porkbun(self, path, body):
        if body.get("apikey") != PB_KEY or body.get("secretapikey") != PB_SECRET:
            return httpx.Response(400, json={"status": "ERROR", "message": "Invalid API key."})
        if path == "/ping":
            return httpx.Response(200, json={"status": "SUCCESS", "yourIp": "203.0.113.1"})
        m = re.match(r"^/domain/checkDomain/([\w.-]+)$", path)
        if m:
            d = m.group(1)
            p = self.pb_price.get(d)
            return httpx.Response(200, json={"status": "SUCCESS", "response": {
                "avail": "yes" if p else "no", "type": "registration", "price": f"{p or 0:.2f}", "regularPrice": f"{(p or 0) + 1:.2f}",
                "premium": "no", "additional": {"renewal": {"type": "renewal", "price": f"{(p or 0) + 1.17:.2f}"}}}})
        m = re.match(r"^/domain/create/([\w.-]+)$", path)
        if m:
            self.created.append((m.group(1), body))
            assert body["agreeToTerms"] == "yes" and isinstance(body["cost"], int)
            return httpx.Response(200, json={"status": "SUCCESS", "domain": m.group(1), "cost": body["cost"], "orderId": 77})
        m = re.match(r"^/dns/retrieve/([\w.-]+)$", path)
        if m:
            if m.group(1) not in self.pb_records:
                return httpx.Response(400, json={"status": "ERROR", "message": "Invalid domain."})
            return httpx.Response(200, json={"status": "SUCCESS", "records": self.pb_records[m.group(1)]})
        m = re.match(r"^/dns/create/([\w.-]+)$", path)
        if m:
            self.n += 1
            name = (body["name"] + "." if body["name"] else "") + m.group(1)
            self.pb_records.setdefault(m.group(1), []).append({"id": str(self.n), "name": name, "type": body["type"],
                                                               "content": body["content"], "ttl": "600", "prio": body.get("prio", "0")})
            return httpx.Response(200, json={"status": "SUCCESS", "id": self.n})
        m = re.match(r"^/dns/delete/([\w.-]+)/(\w+)$", path)
        if m:
            self.pb_records[m.group(1)] = [r for r in self.pb_records[m.group(1)] if r["id"] != m.group(2)]
            return httpx.Response(200, json={"status": "SUCCESS"})
        m = re.match(r"^/dns/edit/([\w.-]+)/(\w+)$", path)
        if m:
            for r in self.pb_records[m.group(1)]:
                if r["id"] == m.group(2):
                    r.update({"type": body["type"], "content": body["content"]})
            return httpx.Response(200, json={"status": "SUCCESS"})
        return httpx.Response(404, json={"status": "ERROR", "message": path})


@pytest.fixture
def dom_env(env, monkeypatch, tmp_path):
    from app.config import get_settings
    from app.site import ai as AI
    from app.site import cf, dns, domains
    monkeypatch.setenv("SITE_DIR", str(tmp_path / "sites"))
    monkeypatch.setenv("SITE_WORKER", "false")
    monkeypatch.setenv("PORKBUN_GAP_S", "0")
    get_settings.cache_clear()
    monkeypatch.setattr(AI, "ask_json", FakeAI())
    fake = FakeRegistrars()
    t = httpx.MockTransport(fake.handler)
    cf.set_transport(t)
    dns.set_transport(t)
    domains.set_transport(t)
    yield fake
    cf.set_transport(None)
    dns.set_transport(None)
    domains.set_transport(None)
    get_settings.cache_clear()


def _site():
    from app.site import service as S
    ctx = conv_ctx()
    v = S.new(T, "mithai dukaan ki website", ctx.conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210", "address": "Main Road, Akot", "city": "Akot"})
    return v, ctx


def test_ideas_and_prices_need_her_account_and_show_renewal(dom_env):
    from app.site import dns as D
    from app.site import domains as DM
    v, _ = _site()
    with pytest.raises(DM.DomainError):
        DM.check(T, ["sharmasweets.in"])                      # no registrar account joined yet
    with pytest.raises(D.DnsError):
        D.set_key(T, "porkbun", PB_KEY, "short")               # secret needed
    D.set_key(T, "cf_registrar", CF_TOKEN, CF_ACCOUNT)
    D.set_key(T, "porkbun", PB_KEY, PB_SECRET)
    assert {k["provider"] for k in D.keys(T)} == {"cf_registrar", "porkbun"}
    assert not any(PB_SECRET in json.dumps(k) or CF_TOKEN in json.dumps(k) for k in D.keys(T))
    res = {r["domain"]: r for r in DM.check(T, ["sharmasweets.in", "sharmasweets.com", "sharmasweetsakot.com", "sharmasweets.shop"])}
    assert res["sharmasweets.in"]["registrar"] == "porkbun" and res["sharmasweets.in"]["available"] and res["sharmasweets.in"]["kyc"]
    assert res["sharmasweets.in"]["renew_inr"] > res["sharmasweets.in"]["inr"] > 0
    assert not res["sharmasweets.com"]["available"]
    assert res["sharmasweetsakot.com"]["registrar"] == "cloudflare" and res["sharmasweetsakot.com"]["available"]
    assert res["sharmasweets.shop"]["registrar"] == "porkbun"   # Cloudflare can't sell it -> Porkbun
    ideas = DM.suggest(T, v["id"])
    names = [x["domain"] for x in ideas["ideas"]]
    assert names and names[0] == "sharmasweets.in" and "sharmasweets.com" not in names
    assert "₹" in ideas["say"] and "saal" in ideas["say"]
    assert DM.ideas("SBI Sweets") == [] and DM.ideas("Jio Mobile Point") == []    # look-alike names refused


def test_buy_only_on_her_tap_kyc_and_reminders(dom_env):
    from app.main import app
    from app.site import dns as D
    from app.site import domains as DM
    from app import approvekey as ak
    c = TestClient(app)
    v, ctx = _site()
    D.set_key(T, "porkbun", PB_KEY, PB_SECRET)
    card = c.post("/api/sites-domains/request", json={"site": v["id"], "domain": "sharmasweets.in"}).json()
    assert card["kind"] == "domain" and card["hash"] and "NIXI" in " ".join(card["lines"]) and "wapas nahi" in " ".join(card["lines"])
    assert _events("site_domain")[-1]["push"] and _events("site_domain")[-1]["kind"] == "domain"
    assert not dom_env.created                                 # nothing bought by the card
    digest, show = ak.card_digest("domain", card["id"], T)
    assert show["amount"] == card["amount"] and digest
    assert c.post(f"/api/sites-domains/{card['id']}/buy", json={"hash": "wrong"}).status_code == 400
    assert not dom_env.created
    r = c.post(f"/api/sites-domains/{card['id']}/buy", json={"hash": card["hash"]}).json()
    assert r["ok"] and dom_env.created[0][0] == "sharmasweets.in" and dom_env.created[0][1]["cost"] == 783
    row = DM.domains(T)[0]
    assert row["status"] == "kyc" and row["account"] == "own"
    assert c.post(f"/api/sites-domains/{card['id']}/buy", json={"hash": card["hash"]}).status_code == 400   # not twice
    DM.tick()
    DM.tick()
    kyc = [e for e in _events("site_domain") if e.get("kind") == "domain_reminder"]
    assert len(kyc) == 1 and "KYC" in kyc[0]["say"]                         # once a day
    assert DM.kyc_done(T, "sharmasweets.in")["ok"] and DM.domains(T)[0]["status"] == "registered"
    with session() as s:                                                    # 20 days to go -> the 30-day reminder, once
        o = s.scalars(select(DM.SiteDomain)).first()
        o.expires_at = datetime.now(timezone.utc) + timedelta(days=20)
    DM.tick()
    DM.tick()
    ren = [e for e in _events("site_domain") if e.get("kind") == "domain_reminder" and "renew" in e["say"]]
    assert len(ren) == 1 and ("20 din" in ren[0]["say"] or "19 din" in ren[0]["say"])


def test_cloudflare_registration_polls_price_change_and_ceiling(dom_env, monkeypatch):
    from app.config import get_settings
    from app.site import dns as D
    from app.site import domains as DM
    v, _ = _site()
    D.set_key(T, "cf_registrar", CF_TOKEN, CF_ACCOUNT)
    card = DM.buy_request(T, v["id"], "sharmasweetsakot.com", auto_renew=True)
    dom_env.cf_price["sharmasweetsakot.com"] = 12.0              # price moved before her tap
    with pytest.raises(DM.DomainError, match="daam badal"):
        DM.buy(T, card["id"], card["hash"])
    assert not dom_env.registered
    fresh = [e for e in _events("site_domain") if e.get("kind") == "domain"][-1]
    assert fresh["id"] != card["id"] and "12" in str(fresh["usd"])
    r = DM.buy(T, fresh["id"], fresh["hash"])
    assert r["state"] == "in_progress" and dom_env.registered[0] == {"domain_name": "sharmasweetsakot.com", "auto_renew": True}
    assert [d for d in DM.domains(T) if d["domain"] == "sharmasweetsakot.com" and d["status"] == "registering"]
    dom_env.cf_state = "succeeded"
    DM.tick()
    assert [d for d in DM.domains(T) if d["domain"] == "sharmasweetsakot.com" and d["status"] == "registered"]
    monkeypatch.setenv("SITES_DOMAIN_MONTH_INR", "1500")         # this month already ~1,056 spent
    get_settings.cache_clear()
    with pytest.raises(DM.DomainError, match="seema"):
        DM.buy_request(T, v["id"], "sharmasweetsonline.com")
    with pytest.raises(DM.DomainError):
        DM.buy_request(T, v["id"], "sharmasweets.com")           # taken


def test_porkbun_dns_plan_applied_only_on_tap_and_tools(dom_env):
    from app.agent.tools import Ctx, ToolError, dispatch
    from app.site import dns as D
    import asyncio
    v, ctx = _site()
    D.set_key(T, "porkbun", PB_KEY, PB_SECRET)
    assert D.where_is(T, "sharmasweets.in")["provider"] == "porkbun"
    p = D.make_plan(T, v["id"], "sharmasweets.in", D.email_records("sharmasweets.in", "zoho", "owner@sharmasweets.in"), "email")
    assert p["provider"] == "porkbun" and p["todo"] >= 3
    assert len(dom_env.pb_records["sharmasweets.in"]) == 1      # nothing changed by the plan
    out = D.apply(T, p["id"], p["hash"])
    assert out["ok"] and any(r["type"] == "MX" for r in dom_env.pb_records["sharmasweets.in"])
    D.undo(T, p["id"])
    assert len(dom_env.pb_records["sharmasweets.in"]) == 1
    staff = Ctx(tenant_id=T, conversation_id=ctx.conversation_id, actor="staff:x")
    with pytest.raises(ToolError):
        asyncio.run(dispatch("website", {"action": "domain_buy", "site": v["id"], "domain": "sharmasweets.in"}, staff))
    owner = Ctx(tenant_id=T, conversation_id=ctx.conversation_id, actor="owner")
    got = asyncio.run(dispatch("website", {"action": "domain_buy", "site": v["id"], "domain": "sharmasweets.in"}, owner))
    assert got["card"] and "fingerprint" in got["say"] and not dom_env.created            # the tool never buys
    ideas = asyncio.run(dispatch("website", {"action": "domain_ideas", "site": v["id"]}, owner))
    assert ideas["ideas"]


def test_newtika_account_names_the_customer_or_says_newtika(dom_env, monkeypatch):
    from app.config import get_settings
    from app.site import domains as DM
    monkeypatch.setenv("SITES_RESELL", "true")
    monkeypatch.setenv("SITES_REG_CF_TOKEN", CF_TOKEN)
    monkeypatch.setenv("SITES_REG_CF_ACCOUNT", CF_ACCOUNT)
    monkeypatch.setenv("SITES_PORKBUN_KEY", PB_KEY)
    monkeypatch.setenv("SITES_PORKBUN_SECRET", PB_SECRET)
    get_settings.cache_clear()
    v, _ = _site()
    with pytest.raises(DM.DomainError, match="email"):          # customer named as owner needs her details
        DM.buy_request(T, v["id"], "sharmasweetsakot.com")
    card = DM.buy_request(T, v["id"], "sharmasweetsakot.com",
                          registrant={"email": "ramesh@sharmasweets.in", "owner": "Ramesh Sharma", "pin": "444101"})
    line = " ".join(card["lines"])
    assert "Registry mein malik: Sharma Sweets" in line
    DM.buy(T, card["id"], card["hash"])
    reg = dom_env.registered[0]["contacts"]["registrant"]
    assert reg["email"] == "ramesh@sharmasweets.in" and reg["phone"] == "+91.9876543210"
    assert reg["postal_info"]["address"]["state"] == "Maharashtra" and reg["postal_info"]["address"]["country_code"] == "IN"
    pb = DM.buy_request(T, v["id"], "sharmasweets.in")           # Porkbun: API can't name her -> said plainly
    assert "malik: Newtika" in " ".join(pb["lines"])
    assert DM.domains(T)[0]["account"] == "hoola"
