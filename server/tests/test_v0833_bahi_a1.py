"""v0.833 BAHI A1 - connect her GSTIN (OTP walk) + supplier checks. No network: WhiteBooks / API Setu are MockTransports."""
import json

import httpx
import pytest

G = "27ADCPI1932N1ZH"
OTP = "123456"


@pytest.fixture
def a1(env, monkeypatch):
    for k, v in {"WHITEBOOKS_EMAIL": "o@example.com", "WHITEBOOKS_GST_CLIENT_ID": "GSTS" + "x" * 36, "WHITEBOOKS_GST_CLIENT_SECRET": "s" * 40}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.bahi import connect, wb
    seen = []

    def plug(fn):
        def h(req):
            seen.append(req)
            return fn(req)
        monkeypatch.setattr(wb, "TRANSPORT", httpx.MockTransport(h))
    yield connect, wb, plug, seen
    get_settings.cache_clear()


def _ok(**data):
    return httpx.Response(200, json={"status_cd": "1", "status_desc": "ok", **data})


def _walk(req):
    p = req.url.path
    if p.endswith("/authentication/otprequest"):
        return _ok(header={"txn": "TXN-1"})
    if p.endswith("/authentication/authtoken"):
        return _ok(header={"txn": "TXN-2"})
    if p.endswith("/authentication/refreshtoken"):
        return _ok(header={"txn": "TXN-3"})
    return httpx.Response(404)


def test_connect_walk_never_stores_or_returns_otp_or_txn(a1):
    connect, wb, plug, seen = a1
    plug(_walk)
    r = connect.start("t1", G.lower(), " GST.user ")
    assert r["status"] == "otp_sent" and "TXN" not in json.dumps(r)
    assert seen[0].headers["gst_username"] == "GST.user" and seen[0].headers["state_cd"] == "27"
    v = connect.verify("t1", G, OTP)
    assert v["status"] == "connected" and v["enabled_until"] and "txn" not in v
    assert [x for x in seen if "authtoken" in x.url.path][0].url.params["otp"] == OTP
    from app.bahi.models import AccGstConn
    from app.db import session
    with session() as s:
        row = s.query(AccGstConn).one()
        assert row.txn == "TXN-2" and OTP not in json.dumps([row.txn, row.gst_username])
    assert connect.refresh("t1", G)["status"] == "connected"
    assert connect.status("t1")[0]["status"] == "connected"
    assert connect.status("other") == []
    d = connect.disconnect("t1", G)
    assert d["status"] == "new" and "Manage API Access" in d["message"]


def test_bad_inputs_refuse_before_any_call(a1):
    connect, wb, plug, seen = a1
    plug(_walk)
    for args in (("t1", "27ADCPI1932N1ZX", "u"), ("t1", G, "")):
        with pytest.raises(connect.ConnectError):
            connect.start(*args)
    with pytest.raises(connect.ConnectError):
        connect.verify("t1", G, "12")
    with pytest.raises(connect.ConnectError):
        connect.verify("t1", G, OTP)           # no OTP was requested
    assert seen == []


def test_wrong_otp_and_failed_refresh_say_so(a1):
    connect, wb, plug, seen = a1
    plug(_walk)
    connect.start("t1", G, "u")
    plug(lambda req: httpx.Response(200, json={"status_cd": "0", "error": {"message": "OTP is invalid", "error_cd": "AUTH4033"}}))
    with pytest.raises(connect.ConnectError) as e:
        connect.verify("t1", G, OTP)
    assert "OTP" in str(e.value) and connect.status("t1")[0]["status"] == "otp_sent"
    plug(_walk)
    connect.verify("t1", G, OTP)
    plug(lambda req: httpx.Response(200, json={"status_cd": "0", "error": {"message": "session expired"}}))
    with pytest.raises(connect.ConnectError) as e:
        connect.refresh("t1", G)
    assert "new OTP" in str(e.value) and connect.status("t1")[0]["status"] == "lapsed"


def test_supplier_check_prefers_api_setu_then_whitebooks_and_says_what_it_could_not_find(a1, monkeypatch):
    connect, wb, plug, seen = a1
    from app.bahi import apisetu

    def h(req):
        p = req.url.path
        if p.endswith("/public/search"):
            return _ok(data={"sts": "Cancelled", "lgnm": "WB NAME"})
        if p.endswith("/public/rettrack"):
            if req.url.params["fy"].startswith("2026") and False:
                return _ok(data=[])
            return _ok(data={"EFiledlist": [{"ret_prd": "102026", "rtntype": "GSTR1", "dof": "11-11-2026", "status": "Filed"}]})
        return httpx.Response(404)
    plug(h)
    r = connect.supplier_check("t1", G)
    assert r["source"] == "WhiteBooks (GSTN)" and r["status"] == "cancelled" and r["filing"]["returns"][0]["form"] == "GSTR1"
    # API Setu answers first when configured
    monkeypatch.setenv("APISETU_CLIENT_ID", "com.x")
    monkeypatch.setenv("APISETU_API_KEY", "k" * 20)
    from app.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setattr(apisetu, "_transport", httpx.MockTransport(lambda req: httpx.Response(200, json={
        "gstin": G, "legalName": "SETU NAME", "status": "Active", "registrationDate": "24/03/2019"})))
    r = connect.supplier_check("t1", G)
    assert r["source"] == "API Setu (GSTN)" and r["status"] == "active" and r["legal_name"] == "SETU NAME"
    # filing track refused in both years -> said plainly, never invented
    plug(lambda req: _ok(data={}) if req.url.path.endswith("/public/search") else httpx.Response(200, json={"status_cd": "0", "error": {"message": "no"}}))
    r = connect.supplier_check("t1", G)
    assert r["filing"] is None and any("cannot say whether this supplier filed" in n for n in r["notes"])


def test_unknown_when_no_source_answers(a1, monkeypatch):
    connect, wb, plug, seen = a1
    for k in ("WHITEBOOKS_GST_CLIENT_ID", "WHITEBOOKS_GST_CLIENT_SECRET"):
        monkeypatch.setenv(k, "")
    from app.config import get_settings
    get_settings.cache_clear()
    r = connect.supplier_check("t1", G)
    assert r["status"] == "unknown" and any("unknown, not 'fine'" in n for n in r["notes"])


def test_routes_and_desk_are_wired():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "app"
    api = (root / "bahi/api.py").read_text()
    for route in ("/api/bahi/connect/start", "/api/bahi/connect/verify", "/api/bahi/connect/refresh", "/api/bahi/connect/disconnect", "/api/bahi/supplier-check"):
        assert route in api
    js = (root / "static/console/bahi.js").read_text()
    assert "cstart" in js and "cverify" in js and "supcheck" in js and "autocomplete=\"one-time-code\"" in js
    assert "password" not in js.lower().split("connectform")[1][:1500].replace("never asked for", "")
