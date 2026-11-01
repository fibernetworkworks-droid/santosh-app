"""v0.396 CONNECT — the screen where an enterprise system is really joined.

The suite could do everything except reach a customer system, because there was nowhere to put a credential.
These tests pin the two things that matter about that door: the key cannot leak back out, and `verify` tells
her what her system actually answered instead of a green tick.
"""
from __future__ import annotations

import json

import pytest

from app.enterprise import dialect, run as RUN
from .entfake import fake_call

SECRET = "sk-live-THIS-MUST-NEVER-COME-BACK-9f3c"


# ---------------------------------------------------------------- the credential cannot get back out
def test_the_key_is_sealed_and_no_route_or_listing_returns_it(env):
    out = RUN.set_endpoint("t1", "erp", "sap", "https://erp.example.com/sap/opu/odata/sap/SRV", SECRET,
                           env="test")
    blob = json.dumps(out, default=str)
    assert SECRET not in blob
    assert "…" in out["auth"] or "…" in blob          # only the masked form comes back
    listed = json.dumps(RUN.endpoints("t1", "erp"), default=str)
    assert SECRET not in listed
    # and not in the database column either
    from sqlalchemy import select
    from app.db import session
    from app.enterprise.models import EntEndpoint
    with session() as s:
        row = s.scalars(select(EntEndpoint).where(EntEndpoint.tenant_id == "t1")).first()
        assert SECRET not in (row.auth_enc or ""), "stored in the clear"
        assert SECRET not in (row.auth_masked or "")


def test_the_masked_form_keeps_too_little_to_reconstruct(env):
    RUN.set_endpoint("t1", "erp", "sap", "https://e.example.com/odata", SECRET)
    m = RUN.endpoints("t1", "erp")[0]["auth"]
    assert len(m) < len(SECRET)
    assert SECRET[3:-3] not in m


def test_an_address_must_be_https(env):
    with pytest.raises(RUN.RunError):
        RUN.set_endpoint("t1", "erp", "sap", "http://erp.example.com/odata", SECRET)


def test_a_system_this_job_does_not_use_is_refused(env):
    with pytest.raises(RUN.RunError):
        RUN.set_endpoint("t1", "erp", "salesforce", "https://x.my.salesforce.com", SECRET)
    # and the right one for that job is fine
    RUN.set_endpoint("t1", "crm_arch", "salesforce", "https://x.my.salesforce.com", SECRET)


def test_production_is_never_inferred_from_the_address(env):
    """A URL that looks live is not consent. `env` is declared, and defaults to test."""
    RUN.set_endpoint("t1", "erp", "sap", "https://prod-erp.example.com/odata", SECRET)
    assert RUN.endpoints("t1", "erp")[0]["env"] == "test"
    with pytest.raises(RUN.RunError):
        RUN.set_endpoint("t1", "erp", "sap", "https://e.example.com/odata", SECRET, env="live")


def test_forgetting_removes_the_way_in_and_keeps_her_work(env, monkeypatch):
    calls = []
    monkeypatch.setattr(RUN.dialect, "Call", fake_call(calls, lambda m, p, b: (201, {"ok": 1})))
    monkeypatch.setattr(RUN, "_odata_call", lambda *a, **k: (200, {}))
    RUN.set_endpoint("t1", "erp", "sap", "https://e.example.com/odata", SECRET)
    r = RUN.plan_write("t1", "erp", "sap", "Vendors", "create", [{"id": "V1"}], key_field="id")
    RUN.dry_run("t1", r["run"]); RUN.approve("t1", r["run"]); RUN.execute("t1", r["run"])
    RUN.forget_endpoint("t1", "erp", "sap")
    assert RUN.endpoints("t1", "erp") == []
    assert RUN.status("t1", r["run"])["hue"] == 1          # the run is still there
    with pytest.raises(RUN.RunError):
        RUN.forget_endpoint("t1", "erp", "sap")            # and saying so twice is honest


# ---------------------------------------------------------------- verify: what the system ANSWERED
class Res:
    def __init__(self, code=200, body=None, headers=None):
        self.status_code, self._b, self.headers, self.text = code, body, headers or {}, ""

    def json(self):
        if self._b is None:
            raise ValueError
        return self._b


def probe(monkeypatch, script):
    """Drive the real dialect.Call against a scripted HTTP server."""
    class C:
        def __init__(self, *a, **k):
            self.seen = []

        def request(self, method, url, json=None, params=None, headers=None):
            self.seen.append((method, url, dict(headers or {})))
            return script(method, url, dict(headers or {}))

        def close(self):
            pass
    monkeypatch.setattr(dialect, "Call", _call_with(C))


def _call_with(client_cls):
    orig = dialect.Call

    class Patched(orig):                    # type: ignore[misc,valid-type]
        def __init__(self, ep, timeout=60):
            self.ep = ep
            self.system = getattr(ep, "system", "")
            self.d = dialect.of(self.system)
            self._token = None
            self._idem_support = "unknown"
            self._c = client_cls()
    return Patched


def test_verify_writes_nothing(env, monkeypatch):
    """It is the first call that ever reaches a customer tenant, so it must only ever read."""
    seen = []

    def script(method, url, headers):
        seen.append(method)
        if headers.get("X-CSRF-Token") == "Fetch":
            return Res(200, {}, {"x-csrf-token": "T"})
        return Res(200, {"d": []})
    probe(monkeypatch, script)
    RUN.set_endpoint("t1", "erp", "sap", "https://e.example.com/odata", SECRET)
    out = RUN.verify("t1", "erp", "sap")
    assert out["theek"] is True
    assert set(seen) == {"GET"}, f"verify must never write, saw {seen}"


def test_a_wrong_key_is_told_apart_from_a_missing_permission(env, monkeypatch):
    """401 and 403 are different problems and need different fixes, so they are never one 'failed'."""
    probe(monkeypatch, lambda m, u, h: Res(401, {"error": "invalid_token"}))
    RUN.set_endpoint("t1", "erp", "sap", "https://e.example.com/odata", SECRET)
    bad = RUN.verify("t1", "erp", "sap")
    assert bad["theek"] is False and "401" in json.dumps(bad)
    assert "Key dobara" in bad["aage"]

    def forbidden(m, u, h):
        if h.get("X-CSRF-Token") == "Fetch":
            return Res(200, {}, {"x-csrf-token": "T"})
        return Res(403, {"error": "no permission"})
    probe(monkeypatch, forbidden)
    out = RUN.verify("t1", "erp", "sap")
    cred = [j for j in out["jaanch"] if j["kya"] == "credential"][0]
    assert cred["theek"] is True and "permission" in cred["kaha"]


def test_a_wrong_address_says_so_instead_of_blaming_the_key(env, monkeypatch):
    probe(monkeypatch, lambda m, u, h: Res(404, {"error": "not found"}))
    RUN.set_endpoint("t1", "erp", "sap", "https://e.example.com/wrong", SECRET)
    out = RUN.verify("t1", "erp", "sap")
    assert out["theek"] is False
    assert "API address" in out["aage"]


def test_a_dead_host_is_an_answer_not_a_crash(env, monkeypatch):
    def boom(m, u, h):
        raise OSError("Connection refused")
    probe(monkeypatch, boom)
    RUN.set_endpoint("t1", "erp", "sap", "https://nowhere.example.com/odata", SECRET)
    out = RUN.verify("t1", "erp", "sap")
    assert out["theek"] is False
    assert "firewall" in out["aage"].lower() or "Firewall" in out["aage"]


def test_verify_reports_the_write_prerequisites_per_system(env, monkeypatch):
    """A read that works does not mean a write will. SAP needs a CSRF token and an ETag; Windchill needs a
    nonce and a check-out. verify says which of those it could actually get."""
    def sap(m, u, h):
        if h.get("X-CSRF-Token") == "Fetch":
            return Res(200, {}, {"x-csrf-token": "T"})
        return Res(200, {"d": []})
    probe(monkeypatch, sap)
    RUN.set_endpoint("t1", "erp", "sap", "https://e.example.com/odata", SECRET)
    out = RUN.verify("t1", "erp", "sap")
    names = " ".join(j["kya"] for j in out["jaanch"])
    assert "CSRF" in names and "If-Match" in names and "Idempotent" in names
    assert "Reserve" not in names                        # not a SAP concept

    def wc(m, u, h):
        if u.endswith("PTC/GetCSRFToken()"):
            return Res(200, {"NonceKey": "CSRF_NONCE", "NonceValue": "N"})
        return Res(200, {"value": []})
    probe(monkeypatch, wc)
    RUN.set_endpoint("t1", "plm", "windchill", "https://w.example.com/Windchill/servlet/odata", SECRET)
    out2 = RUN.verify("t1", "plm", "windchill")
    names2 = " ".join(j["kya"] for j in out2["jaanch"])
    assert "Reserve" in names2
    assert "If-Match" not in names2                      # PTC documents no ETag


def test_a_csrf_token_that_cannot_be_fetched_fails_the_check(env, monkeypatch):
    """Better said now than discovered at her first write, which SAP would 403."""
    probe(monkeypatch, lambda m, u, h: Res(200, {"d": []}, {}))   # answers, but issues no token
    RUN.set_endpoint("t1", "erp", "sap", "https://e.example.com/odata", SECRET)
    out = RUN.verify("t1", "erp", "sap")
    assert out["theek"] is False
    csrf = [j for j in out["jaanch"] if "CSRF" in j["kya"]][0]
    assert csrf["theek"] is False


def test_a_good_check_is_recorded_and_a_bad_one_is_not(env, monkeypatch):
    probe(monkeypatch, lambda m, u, h: Res(500, {"error": "boom"}))
    RUN.set_endpoint("t1", "crm_arch", "salesforce", "https://x.my.salesforce.com", SECRET)
    RUN.verify("t1", "crm_arch", "salesforce")
    assert RUN.endpoints("t1", "crm_arch")[0]["verified"] is False
    probe(monkeypatch, lambda m, u, h: Res(200, {"sobjects": []}))
    out = RUN.verify("t1", "crm_arch", "salesforce")
    assert out["theek"] is True
    assert RUN.endpoints("t1", "crm_arch")[0]["verified"] is True


def test_verify_on_a_system_that_is_not_joined_says_so(env):
    with pytest.raises(RUN.RunError) as e:
        RUN.verify("t1", "erp", "sap")
    assert "juda" in str(e.value)


def test_production_says_the_extra_word_is_still_needed(env, monkeypatch):
    def ok(m, u, h):
        if h.get("X-CSRF-Token") == "Fetch":
            return Res(200, {}, {"x-csrf-token": "T"})
        return Res(200, {"d": []})
    probe(monkeypatch, ok)
    RUN.set_endpoint("t1", "erp", "sap", "https://e.example.com/odata", SECRET, env="production")
    out = RUN.verify("t1", "erp", "sap")
    assert out["theek"] is True
    assert "production" in out["aage"]        # a working connection is not permission to write


# ---------------------------------------------------------------- the door exists in the app, not in chat
def test_the_chat_tool_still_refuses_to_take_a_credential():
    """The whole reason this screen exists. A key typed into a conversation is in the history, in the model's
    context and in any export of either, so the tool points her at the app instead."""
    from app.agent.enterprise_tools import ENTERPRISE_TOOLS
    erp = [t for t in ENTERPRISE_TOOLS if t["name"] == "erp"][0]
    assert "credential is typed in the APP, never here" in erp["description"]
    assert "endpoint" in erp["input_schema"]["properties"]["action"]["enum"]


def test_the_routes_exist_and_only_the_app_can_set_a_key():
    from app.main import app
    paths = {(sorted(getattr(r, "methods", []) or ["?"])[0], getattr(r, "path", "")) for r in app.routes}
    assert ("POST", "/api/enterprise/{role}/endpoint") in paths
    assert ("POST", "/api/enterprise/{role}/endpoint/{system}/verify") in paths
    assert ("DELETE", "/api/enterprise/{role}/endpoint/{system}") in paths
    assert ("GET", "/api/enterprise/{role}/endpoint") in paths
    # there is no route that hands a credential back
    assert not any(p.endswith("/secret") or p.endswith("/auth") for _m, p in paths)


def test_the_console_screen_never_keeps_the_key_on_the_page():
    js = open("app/static/console/enterprise.js").read()
    assert "type=\"password\"" in js
    assert "value = ''" in js                 # cleared after sending
    assert "esc(" in js                       # every server value escaped
    # the key is only ever sent, never read back into the form
    assert "value=\"${esc(live ? live.base_url : '')}\"" in js
    assert "live.auth" in js and "live.key" not in js
