"""v0.827 API Setu GSTN Tax Payer lookup + its check (vps-ops apisetu_check). No network: httpx.MockTransport."""
import json

import httpx
import pytest

KEY = "ak-SECRET-9f8e7d"
REC = {"gstin": "33AAACC1206D1ZN", "legalName": "SAMPLE TRADERS PRIVATE LIMITED", "constitution": "Private Limited Company",
       "registrationDate": "01/07/2017", "status": "Active", "taxPayerType": "Regular", "centerJurisdiction": "RANGE-III",
       "stateJurisdiction": "Chennai - Ward 4", "cancellationDate": "", "natureBusinessActivities": ["Wholesale Business"]}


@pytest.fixture
def asenv(env, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APISETU_CLIENT_ID", " in.gov.example ")
    monkeypatch.setenv("APISETU_API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.bahi import apisetu
    seen = []

    def plug(fn):
        def h(req):
            seen.append(req)
            return fn(req)
        monkeypatch.setattr(apisetu, "_transport", httpx.MockTransport(h))
    yield apisetu, plug, seen
    get_settings.cache_clear()


def test_lookup_sends_both_headers_and_reads_the_spec_reply(asenv):
    apisetu, plug, seen = asenv
    plug(lambda req: httpx.Response(200, json=REC))
    r = apisetu.taxpayer("33aaacc1206d1zn")
    req = seen[0]
    assert str(req.url) == "https://apisetu.gov.in/gstn/v1/taxpayers/33AAACC1206D1ZN"
    assert req.headers["X-APISETU-CLIENTID"] == "in.gov.example" and req.headers["X-APISETU-APIKEY"] == KEY
    assert r["active"] is True and r["registered_on"] == "2017-07-01" and r["cancelled_on"] == ""
    assert r["legal_name"] == "SAMPLE TRADERS PRIVATE LIMITED" and r["activities"] == ["Wholesale Business"]


def test_bad_gstin_and_missing_keys_refuse_before_any_call(asenv, monkeypatch):
    apisetu, plug, seen = asenv
    plug(lambda req: httpx.Response(200, json=REC))
    with pytest.raises(apisetu.ApiSetuError) as e:
        apisetu.taxpayer("33AAACC1206D1ZX")              # wrong check digit
    assert e.value.code == "bad_gstin"
    monkeypatch.setenv("APISETU_API_KEY", "")
    from app.config import get_settings
    get_settings.cache_clear()
    with pytest.raises(apisetu.ApiSetuError) as e:
        apisetu.taxpayer("33AAACC1206D1ZN")
    assert e.value.code == "not_configured" and "VPS .env" in e.value.message
    assert seen == []


@pytest.mark.parametrize("status,body,code,words", [
    (401, {"error": "invalid_authentication", "errorDescription": "Authentication failed"}, "invalid_authentication", "did not accept the keys"),
    (401, {"error": "invalid_authorization", "errorDescription": "You are not authorized to use this API"}, "invalid_authorization", "subscribe"),
    (404, {"error": "record_not_found", "errorDescription": "No record found for the provided inputs"}, "record_not_found", "no taxpayer"),
    (503, {}, "unavailable", "down or busy"),
])
def test_errors_are_said_plainly(asenv, status, body, code, words):
    apisetu, plug, _ = asenv
    plug(lambda req: httpx.Response(status, json=body))
    with pytest.raises(apisetu.ApiSetuError) as e:
        apisetu.taxpayer("33AAACC1206D1ZN")
    assert e.value.code == code and words in e.value.message and KEY not in e.value.message


def test_check_passes_records_the_shape_and_never_prints_the_key(asenv, capsys):
    apisetu, plug, _ = asenv
    plug(lambda req: httpx.Response(200, json=REC))
    from app.bahi import apisetucheck
    assert apisetucheck.main([]) == 0
    out = capsys.readouterr().out
    assert "PASS" in out and "SAMPLE TRADERS" in out and KEY not in out and "in.gov.example" not in out
    assert f"{len(KEY)} characters" in out
    shape = json.loads(apisetucheck.shape_path().read_text())["shape"]
    assert shape["legalName"] == "str" and shape["natureBusinessActivities"] == ["str"]


def test_check_says_why_it_failed_and_a_404_still_proves_the_keys(asenv, capsys):
    apisetu, plug, _ = asenv
    from app.bahi import apisetucheck
    plug(lambda req: httpx.Response(401, json={"error": "invalid_authorization", "errorDescription": "You are not authorized to use this API"}))
    assert apisetucheck.main([]) == 1
    out = capsys.readouterr().out
    assert "FAIL" in out and "GSTN Tax Payer API" in out
    plug(lambda req: httpx.Response(404, json={"error": "record_not_found"}))
    r = apisetucheck.run("27AAGCB1286QKZL")
    assert r["result"] == "PASS" and r["keys_accepted"] and r["gstin"] == "27AAGCB1286QKZL"


def test_check_skips_without_keys_and_vps_ops_has_the_job(asenv, monkeypatch):
    monkeypatch.setenv("APISETU_CLIENT_ID", "")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.bahi import apisetucheck
    r = apisetucheck.run()
    assert r["result"] == "SKIP" and r["paste"][0]["set"] is False
    from pathlib import Path
    wf = (Path(__file__).resolve().parents[2] / ".github/workflows/vps-ops.yml").read_text()
    assert "- apisetu_check" in wf and "python -m app.bahi.apisetucheck" in wf and "APISETU_API_KEY" in wf


def test_v0828_relay_is_used_and_its_failures_say_what_to_do(asenv, monkeypatch):
    apisetu, plug, seen = asenv
    from app.config import get_settings
    monkeypatch.setenv("DATA_GOV_IN_BASE", "https://hoola-dg.example.workers.dev/")
    get_settings.cache_clear()
    assert apisetu.base() == "https://hoola-dg.example.workers.dev/gstn/v1" and apisetu.via_relay()
    plug(lambda req: httpx.Response(200, json=REC))
    apisetu.taxpayer("33AAACC1206D1ZN")
    assert str(seen[-1].url) == "https://hoola-dg.example.workers.dev/gstn/v1/taxpayers/33AAACC1206D1ZN"
    plug(lambda req: httpx.Response(404, text="Not found"))           # the old worker, before the new code is pasted
    with pytest.raises(apisetu.ApiSetuError) as e:
        apisetu.taxpayer("33AAACC1206D1ZN")
    assert "worker.js" in e.value.message and "does not forward API Setu" in e.value.message
    monkeypatch.setenv("APISETU_GSTN_BASE", "https://apisetu.gov.in/gstn/v1")    # explicit wins
    get_settings.cache_clear()
    assert apisetu.base() == "https://apisetu.gov.in/gstn/v1" and not apisetu.via_relay()

    def slow(req):
        raise httpx.ReadTimeout("timed out", request=req)
    plug(slow)
    with pytest.raises(apisetu.ApiSetuError) as e:
        apisetu.taxpayer("33AAACC1206D1ZN")
    assert e.value.code == "unreachable" and "DATA_GOV_IN_BASE" in e.value.message and KEY not in e.value.message


def test_v0828_the_relay_worker_forwards_only_the_gstin_lookup():
    from pathlib import Path
    js = (Path(__file__).resolve().parents[2] / "deploy/datagov-relay/worker.js").read_text()
    assert "/^\\/gstn\\/v[12]\\/taxpayers\\/[0-9A-Z]{15}$/" in js and "https://apisetu.gov.in" in js
    assert '["X-APISETU-CLIENTID", "X-APISETU-APIKEY"]' in js and 'request.method !== "GET"' in js
    assert '"/resource/"' in js and "api.data.gov.in" in js                        # data.gov.in relay kept


def test_v0828_wb_check_explains_an_unknown_gst_username(capsys, monkeypatch):
    from app.bahi import wbcheck
    monkeypatch.setattr(wbcheck, "run", lambda: {"env": "sandbox", "paste": [], "passed": 4, "failed": 1, "skipped": 0,
                                                 "steps": [{"step": "otp_request", "result": "FAIL",
                                                            "line": "refused: user name does not exists"}]})
    monkeypatch.setattr(wbcheck.wb, "configured", lambda p: True)
    assert wbcheck.main() == 1
    out = capsys.readouterr().out
    assert "does not know the name" in out and "gst_username and the GSTIN it" in out


def test_v0832_a_wrapped_or_gstn_shaped_record_is_read(asenv):
    apisetu, plug, _ = asenv
    plug(lambda req: httpx.Response(200, json={"status": True, "data": REC}))
    assert apisetu.taxpayer("33AAACC1206D1ZN")["legal_name"] == "SAMPLE TRADERS PRIVATE LIMITED"
    native = {"gstin": "33AAACC1206D1ZN", "lgnm": "NATIVE NAME LTD", "sts": "Active", "rgdt": "05/09/2018", "nba": ["Retail Business"]}
    plug(lambda req: httpx.Response(200, json={"result": [native]}))
    r = apisetu.taxpayer("33AAACC1206D1ZN")
    assert r["legal_name"] == "NATIVE NAME LTD" and r["active"] and r["registered_on"] == "2018-09-05"
    assert r["activities"] == ["Retail Business"]


def test_v0832_a_200_without_a_record_names_the_fields_never_the_values(asenv, capsys):
    apisetu, plug, _ = asenv
    plug(lambda req: httpx.Response(200, json={"status": False, "message": "No records found", "data": {"secretish": "VALUE-XYZ"}}))
    with pytest.raises(apisetu.ApiSetuError) as e:
        apisetu.taxpayer("33AAACC1206D1ZN")
    assert e.value.code == "no_record" and "status" in e.value.message and "data.secretish" in e.value.message
    assert "VALUE-XYZ" not in e.value.message and "No records found" in e.value.message
    from app.bahi import apisetucheck
    assert apisetucheck.main([]) == 0
    out = capsys.readouterr().out
    assert "PASS" in out and "the keys work" in out.lower() and "APISETU_TEST_GSTIN" in out
