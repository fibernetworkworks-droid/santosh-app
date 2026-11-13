"""v0.877 HOOLA AGENT API - keys, INR wallet, catalogue calls (docs/HOOLA_API_PLAN.md). No network, no model."""
import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient

BASE = "/api/hoola-api/v1"
INR = 1_000_000


@pytest.fixture()
def api(env, monkeypatch):
    monkeypatch.setenv("HOOLA_API_ENABLED", "true")
    monkeypatch.setenv("HOOLA_OPERATOR_TENANT", "default")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.hoolaapi import service as SV
    SV.LIMITER.reset()
    from app.main import app
    return TestClient(app)


def _fake(monkeypatch, fn=None, name="duniya"):
    from app.agent import tools as T
    calls = []

    async def ok(ctx, **kw):
        calls.append((ctx.tenant_id, ctx.actor, kw))
        return {"ok": True, "echo": kw.get("action")}
    monkeypatch.setitem(T.HANDLERS, name, fn or ok)
    return calls


def _key(c, **body):
    r = c.post("/api/hoola-portal/keys", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _fund(c, inr, tenant="default", ref=None):
    r = c.post(f"/api/hoola-admin/wallets/{tenant}/credit", json={"amount_inr": inr, "reason": "test credit",
                                                                    "idempotency_key": ref or ""})
    assert r.status_code == 200, r.text
    return r.json()


def _h(k):
    return {"Authorization": "Bearer " + k["key"]}


def _call(c, k, args=None, name="duniya"):
    return c.post(f"{BASE}/tools/{name}", json={"arguments": args if args is not None else {"action": "status"}}, headers=_h(k))


def test_off_by_default(env):
    from app.config import get_settings
    get_settings.cache_clear()
    from app.main import app
    r = TestClient(app).get(f"{BASE}/tools", headers={"Authorization": "Bearer hk_live_x"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "api_disabled"


def test_key_shown_once_and_only_hash_kept(api):
    k = _key(api, name="my app")
    assert k["key"].startswith("hk_live_") and k["tail"] == k["key"][-4:]
    listed = api.get("/api/hoola-portal/keys").json()["keys"]
    assert len(listed) == 1 and "key" not in listed[0] and k["key"] not in str(listed)
    from app.db import session
    from app.hoolaapi.models import HapiKey
    with session() as s:
        row = s.query(HapiKey).first()
        assert row.key_hash != k["key"] and k["key"] not in str(row.__dict__)
        assert len(row.key_hash) == 64


def test_auth_wrong_missing_and_revoked_key(api, monkeypatch):
    _fake(monkeypatch)
    k = _key(api)
    _fund(api, 10)
    assert api.get(f"{BASE}/tools").status_code == 401
    assert api.get(f"{BASE}/tools", headers={"Authorization": "Bearer hk_live_nope"}).status_code == 401
    assert api.get(f"{BASE}/tools", headers=_h(k)).status_code == 200
    assert api.delete(f"/api/hoola-portal/keys/{k['id']}").status_code == 200
    r = _call(api, k)
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_api_key"


def test_catalogue_is_an_allowlist(api, monkeypatch):
    k = _key(api)
    names = {t["name"] for t in api.get(f"{BASE}/tools", headers=_h(k)).json()["tools"]}
    assert names == {"api_box", "mospi", "duniya", "reach", "scrape_page", "pylab"}
    _fund(api, 10)
    for bad in ("create_campaign", "email_send", "pc_do", "pay_upi", "nothing_here"):
        r = _call(api, k, {}, name=bad)
        assert r.status_code == 404 and r.json()["error"]["code"] == "tool_not_found", bad


def test_catalogue_never_holds_a_sending_or_paying_tool():
    from app.hoolaapi.catalog import CATALOG
    for n in CATALOG:
        assert not any(w in n for w in ("send", "pay", "delete", "campaign", "email", "pc_", "whatsapp", "approve"))


def test_key_can_be_limited_to_some_tools(api, monkeypatch):
    _fake(monkeypatch)
    _fund(api, 10)
    k = _key(api, tools=["duniya"])
    assert {t["name"] for t in api.get(f"{BASE}/tools", headers=_h(k)).json()["tools"]} == {"duniya"}
    r = _call(api, k, {"code": "print(1)"}, name="pylab")
    assert r.status_code == 403 and r.json()["error"]["code"] == "tool_not_allowed"
    assert api.post("/api/hoola-portal/keys", json={"tools": ["email_send"]}).status_code == 400


def test_call_runs_as_the_company_and_is_charged_exactly(api, monkeypatch):
    calls = _fake(monkeypatch)
    k = _key(api)
    assert _fund(api, 10)["balance_micro_inr"] == 10 * INR
    r = _call(api, k)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["result"] == {"ok": True, "echo": "status"} and b["charged_micro_inr"] == 250_000
    assert r.headers["x-hoola-cost-inr"] == "0.250000" and r.headers["x-hoola-request-id"] == b["request_id"]
    assert calls[0][0] == "default" and calls[0][1] == "api:" + k["id"]            # acts as ITS company, as an api actor
    bal = api.get(f"{BASE}/balance", headers=_h(k)).json()
    assert bal["balance_micro_inr"] == 10 * INR - 250_000 and bal["key_spent_today_micro_inr"] == 250_000
    assert api.get("/api/hoola-portal/wallet").json()["invariant"]["ok"] is True
    types = [e["type"] for e in api.get("/api/hoola-portal/ledger").json()["entries"]]
    assert types == ["charge", "adjustment"]


def test_empty_wallet_is_402_and_the_tool_never_runs(api, monkeypatch):
    calls = _fake(monkeypatch)
    k = _key(api)
    r = _call(api, k)
    assert r.status_code == 402 and r.json()["error"]["code"] == "insufficient_balance"
    assert calls == []
    assert api.get("/api/hoola-portal/wallet").json()["balance_micro_inr"] == 0


def test_a_failed_tool_is_refunded_and_logged(api, monkeypatch):
    async def boom(ctx, **kw):
        raise RuntimeError("upstream down")
    _fake(monkeypatch, boom)
    k = _key(api)
    _fund(api, 5)
    r = _call(api, k)
    assert r.status_code == 502 and "not charged" in r.json()["error"]["message"]
    w = api.get("/api/hoola-portal/wallet").json()
    assert w["balance_micro_inr"] == 5 * INR and w["invariant"]["ok"] is True
    types = sorted(e["type"] for e in api.get("/api/hoola-portal/ledger").json()["entries"])
    assert types == ["adjustment", "charge", "refund"]
    u = api.get("/api/hoola-portal/usage").json()
    assert u["by_tool"]["duniya"]["failed"] == 1 and u["charged_micro_inr"] == 0


def test_a_tool_error_dict_is_also_a_failure_with_refund(api, monkeypatch):
    async def soft(ctx, **kw):
        return {"error": "no such place"}
    _fake(monkeypatch, soft)
    k = _key(api)
    _fund(api, 5)
    assert _call(api, k).status_code == 502
    assert api.get("/api/hoola-portal/wallet").json()["balance_micro_inr"] == 5 * INR


def test_ok_false_result_is_a_failure_with_refund(api, monkeypatch):
    async def nothing(ctx, **kw):
        return {"ok": False, "say": "nothing found for that"}
    _fake(monkeypatch, nothing)
    k = _key(api)
    _fund(api, 5)
    r = _call(api, k)
    assert r.status_code == 502 and "nothing found" in r.json()["error"]["message"]
    assert api.get("/api/hoola-portal/wallet").json()["balance_micro_inr"] == 5 * INR


def test_employee_mode_never_holds_an_api_call_for_the_owner(api, monkeypatch):
    """With Employee mode on and 'seekh' trust the gate asks the owner before an in-job action; an API call must not."""
    calls = _fake(monkeypatch, name="api_box")
    from app.db import session
    from app.employee.models import EmployeeAsk, EmployeeProfile
    with session() as s:
        s.merge(EmployeeProfile(tenant_id="default", enabled=True, role="front_desk"))
    k = _key(api)
    _fund(api, 5)
    r = _call(api, k, {"need": "usd to inr"}, name="api_box")
    assert r.status_code == 200, r.text
    assert len(calls) == 1
    with session() as s:
        assert s.query(EmployeeAsk).count() == 0
    assert api.get("/api/hoola-portal/usage").json()["by_tool"]["api_box"]["calls"] == 1


def test_a_waiting_owner_answer_is_never_charged(api, monkeypatch):
    async def held(ctx, **kw):
        return {"status": "waiting_owner", "ask_id": "ea_1"}
    _fake(monkeypatch, held)
    k = _key(api)
    _fund(api, 5)
    assert _call(api, k).status_code == 502
    assert api.get("/api/hoola-portal/wallet").json()["balance_micro_inr"] == 5 * INR


def test_timeout_is_refunded(api, monkeypatch):
    async def slow(ctx, **kw):
        await asyncio.sleep(5)
    _fake(monkeypatch, slow)
    from app.hoolaapi import service as SV
    monkeypatch.setattr(SV, "CALL_TIMEOUT_S", 0.05)
    k = _key(api)
    _fund(api, 5)
    r = _call(api, k)
    assert r.status_code == 504 and r.json()["error"]["code"] == "timeout"
    assert api.get("/api/hoola-portal/wallet").json()["balance_micro_inr"] == 5 * INR


def test_bad_arguments_are_400_and_not_charged(api, monkeypatch):
    calls = _fake(monkeypatch)
    k = _key(api)
    _fund(api, 5)
    r = _call(api, k, {"action": "not-an-action"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "invalid_request" and calls == []
    r = api.post(f"{BASE}/tools/duniya", json={"arguments": ["x"]}, headers=_h(k))
    assert r.status_code == 400
    assert api.get("/api/hoola-portal/wallet").json()["balance_micro_inr"] == 5 * INR


def test_daily_limit_of_a_key(api, monkeypatch):
    _fake(monkeypatch)
    k = _key(api, daily_limit_inr=0.5)                 # two calls of 0.25
    _fund(api, 5)
    assert _call(api, k).status_code == 200 and _call(api, k).status_code == 200
    r = _call(api, k)
    assert r.status_code == 429 and r.json()["error"]["code"] == "daily_limit_reached"
    assert api.get("/api/hoola-portal/wallet").json()["balance_micro_inr"] == 5 * INR - 500_000


def test_rate_limit_is_429_with_retry_after_and_no_charge(api, monkeypatch):
    _fake(monkeypatch)
    k = _key(api, rpm=1)
    _fund(api, 5)
    assert _call(api, k).status_code == 200
    r = _call(api, k)
    assert r.status_code == 429 and r.json()["error"]["code"] == "rate_limited" and int(r.headers["Retry-After"]) >= 1
    assert api.get("/api/hoola-portal/wallet").json()["balance_micro_inr"] == 5 * INR - 250_000


def test_parallel_calls_only_the_affordable_number_succeed(api, monkeypatch):
    async def slowish(ctx, **kw):
        await asyncio.sleep(0.05)
        return {"ok": True}
    _fake(monkeypatch, slowish)
    k = _key(api, rpm=600, rph=50000, concurrent=20)
    _fund(api, 0.75)                                   # exactly three calls of 0.25
    from app.main import app

    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as ac:
            rs = await asyncio.gather(*[ac.post(f"{BASE}/tools/duniya", json={"arguments": {"action": "status"}},
                                                headers=_h(k)) for _ in range(10)])
        return [r.status_code for r in rs]
    codes = asyncio.run(go())
    assert codes.count(200) == 3 and codes.count(402) == 7
    w = api.get("/api/hoola-portal/wallet").json()
    assert w["balance_micro_inr"] == 0 and w["invariant"]["ok"] is True


def test_ledger_is_append_only(api):
    _fund(api, 1)
    from sqlalchemy import text

    from app.db import session
    from app.hoolaapi.models import HapiLedger
    with pytest.raises(Exception):
        with session() as s:
            s.execute(text("update hapi_ledger set amount_micro = 1"))
    with pytest.raises(Exception):
        with session() as s:
            s.execute(text("delete from hapi_ledger"))
    with pytest.raises(RuntimeError):
        with session() as s:
            s.query(HapiLedger).first().note = "edited"
            s.flush()
    with pytest.raises(RuntimeError):
        with session() as s:
            s.delete(s.query(HapiLedger).first())
            s.flush()


def test_same_credit_event_counts_once(api):
    a = _fund(api, 3, ref="pay-1")
    b = _fund(api, 3, ref="pay-1")
    assert a["applied"] is True and b["applied"] is False
    assert api.get("/api/hoola-portal/wallet").json()["balance_micro_inr"] == 3 * INR


def test_admin_is_operator_only_and_needs_a_reason(api, monkeypatch):
    r = api.post("/api/hoola-admin/wallets/default/credit", json={"amount_inr": 5})
    assert r.status_code == 400
    assert api.post("/api/hoola-admin/wallets/default/credit", json={"amount_inr": -5, "reason": "x"}).status_code == 400
    monkeypatch.setenv("HOOLA_OPERATOR_TENANT", "someone-else")
    from app.config import get_settings
    get_settings.cache_clear()
    assert api.post("/api/hoola-admin/wallets/default/credit", json={"amount_inr": 5, "reason": "x"}).status_code == 403
    assert api.get("/api/hoola-admin/overview").status_code == 403


def test_suspended_wallet_stops_every_key(api, monkeypatch):
    _fake(monkeypatch)
    k = _key(api)
    _fund(api, 5)
    assert api.post("/api/hoola-admin/wallets/default/suspend", json={"suspended": True}).status_code == 200
    r = _call(api, k)
    assert r.status_code == 403 and r.json()["error"]["code"] == "account_suspended"
    api.post("/api/hoola-admin/wallets/default/suspend", json={"suspended": False})
    assert _call(api, k).status_code == 200


def test_usage_log_stores_metadata_only(api, monkeypatch):
    _fake(monkeypatch)
    k = _key(api)
    _fund(api, 5)
    _call(api, k, {"action": "status"})
    from app.hoolaapi.models import HapiCall
    cols = {c.name for c in HapiCall.__table__.columns}
    assert not (cols & {"args", "arguments", "result", "output", "body", "prompt"})
    u = api.get(f"{BASE}/usage", headers=_h(k)).json()
    assert u["calls"] == 1 and u["by_tool"]["duniya"]["charged_micro_inr"] == 250_000


def test_price_override_setting_and_bad_override_ignored(monkeypatch):
    from app.config import get_settings
    from app.hoolaapi import catalog as C
    monkeypatch.setenv("HOOLA_API_PRICES", '{"duniya": 1000000, "pylab": -5, "bogus": 1, "reach": "x"}')
    get_settings.cache_clear()
    p = C.prices()
    assert p["duniya"] == 1_000_000 and p["pylab"] == 500_000 and p["reach"] == 1_000_000 and "bogus" not in p
    monkeypatch.setenv("HOOLA_API_PRICES", "not json")
    get_settings.cache_clear()
    assert C.prices()["duniya"] == 250_000


def test_portal_me_and_catalog(api):
    me = api.get("/api/hoola-portal/me").json()
    assert me["enabled"] is True and me["base_url"] == BASE and me["wallet"]["balance_micro_inr"] == 0
    assert len(api.get("/api/hoola-portal/catalog").json()["tools"]) == 6


def test_version():
    from pathlib import Path

    from app.main import APP_VERSION
    assert APP_VERSION == "0.877.0"
    assert "0.877.0+876" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
