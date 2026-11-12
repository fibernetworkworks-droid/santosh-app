"""v0.834 BAHI A2 - the monthly credit loop: 2B pull, match + reasons, her decisions, IMS apply on her confirm. No network."""
import json

import httpx
import pytest

G = "27ADCPI1932N1ZH"
S1, S2 = "29AABCU9603R1ZX", "07AAACR5055K1Z3"


def _2b():
    def inv(n, dt, tx, ig=0, cg=0, sg=0, **k):
        return {"inum": n, "typ": "R", "dt": dt, "val": tx + ig + cg + sg, "pos": "27", "rev": "N", "itcavl": "Y",
                "items": [{"txval": tx, "igst": ig, "cgst": cg, "sgst": sg}], **k}
    return {"data": {"docdata": {"b2b": [
        {"ctin": S1, "trdnm": "ACME LTD", "supprd": "102026", "inv": [inv("INV-001", "05-10-2026", 1000, 180), inv("INV-002", "06-10-2026", 2000, 360),
                                                                      inv("INV-003", "07-10-2026", 500, 90), inv("INV-001", "05-10-2026", 1000, 180)]},
        {"ctin": S2, "trdnm": "RAJ CO", "supprd": "102026", "inv": [inv("R-9", "08-10-2026", 400, 72, itcavl="N", rsn="POS")]}]}}}


@pytest.fixture
def a2(env, monkeypatch):
    for k, v in {"WHITEBOOKS_EMAIL": "o@example.com", "WHITEBOOKS_GST_CLIENT_ID": "GSTS" + "x" * 36, "WHITEBOOKS_GST_CLIENT_SECRET": "s" * 40}.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.bahi import connect, itc, wb
    from app.bahi.models import AccDoc, AccGstConn, ensure_tables
    from app.db import session
    monkeypatch.setattr(itc, "_sleep", lambda s: None)
    ensure_tables()
    with session() as s:
        s.add(AccGstConn(tenant_id="t1", gstin=G, state_cd="27", gst_username="u", txn="TXN", status="connected", enabled_until="2999-01-01T00:00:00+00:00"))
        def doc(n, ctin, ig, d="2026-10-05"):
            s.add(AccDoc(tenant_id="t1", gstin=G, period=d[:7], direction="in", number=n, doc_date=d, party_name="ACME", party_gstin=ctin,
                         igst=ig, source="office", source_ref=n))
        doc("INV-001", S1, 180)            # matches exactly
        doc("INV-002", S1, 300)            # tax differs (2B says 360)
        doc("OLD-77", S1, 90, "2026-09-20")  # same tax as INV-003 under another number
        doc("BILL-5", S2, 50)              # bought, never reached 2B
        s.commit()
    seen = []

    def plug(fn):
        def h(req):
            seen.append(req)
            return fn(req)
        monkeypatch.setattr(wb, "TRANSPORT", httpx.MockTransport(h))

    def routes(req):
        p = req.url.path
        ok = lambda **k: httpx.Response(200, json={"status_cd": "1", "status_desc": "ok", **k})   # noqa: E731
        if p.endswith("/gstr2b/all"):
            return ok(**_2b())
        if p.endswith("/ims/save"):
            return ok(header={"int_tran_id": "IT-1"})
        if p.endswith("/ims/status"):
            return ok(data={"status": "processed"})
        if p.endswith("/gstr2b/gen2b"):
            return ok(header={"int_tran_id": "IT-2"})
        return httpx.Response(404)
    plug(routes)
    yield itc, seen, plug
    get_settings.cache_clear()


def test_pull_parses_2b_and_proposes_each_row_with_a_reason(a2):
    itc, seen, _ = a2
    r = itc.pull("t1", G, "2026-10")
    assert r["invoices"] == 5 and seen[0].url.params["rtnprd"] == "102026" and seen[0].headers["txn"] == "TXN"
    p = itc.propose("t1", G, "2026-10")
    by = {(x["number"], x["proposal"]): x for x in p["rows"]}
    assert by[("INV-001", "accept")]["confidence"] == 0.99
    assert ("INV-002", "pending") in by and "differs by Rs 60" in by[("INV-002", "pending")]["reason"]
    assert "OLD-77" in by[("INV-003", "pending")]["reason"] and "numbering" in by[("INV-003", "pending")]["reason"]
    dup = [x for x in p["rows"] if x["proposal"] == "reject"]
    assert len(dup) == 1 and "twice" in dup[0]["reason"]
    assert by[("R-9", "none")]["reason"].startswith("GSTN already marks")
    m = p["missing_in_2b"]
    assert [x["number"] for x in m] == ["BILL-5"] and "wa.me" in m[0]["nudge"]["wa_link"] and "BILL-5" in m[0]["nudge"]["text"]
    # a non-duplicate is never proposed for reject
    assert all(x["proposal"] != "reject" or "twice" in x["reason"] for x in p["rows"])


def test_nothing_reaches_the_portal_without_confirm_and_the_exact_plan(a2):
    itc, seen, _ = a2
    itc.pull("t1", G, "2026-10")
    p = itc.propose("t1", G, "2026-10")
    ids = {x["number"]: x["id"] for x in p["rows"] if x["proposal"] in ("accept", "pending")}
    itc.decide("t1", G, "2026-10", {ids["INV-001"]: "accept", ids["INV-002"]: "pending"})
    pv = itc.preview("t1", G, "2026-10")
    assert pv["will_send"] == 2 and pv["counts"] == {"accept": 1, "reject": 0, "pending": 1}
    n_before = len(seen)
    with pytest.raises(itc.ItcError):
        itc.apply("t1", G, "2026-10", pv["plan_hash"], False)
    with pytest.raises(itc.ItcError):
        itc.apply("t1", G, "2026-10", "wrong", True)
    assert len(seen) == n_before and not [r for r in seen if r.url.path.endswith("/ims/save")]
    itc.decide("t1", G, "2026-10", {ids["INV-001"]: "reject"})       # list changed after the preview
    with pytest.raises(itc.ItcError):
        itc.apply("t1", G, "2026-10", pv["plan_hash"], True)
    pv = itc.preview("t1", G, "2026-10")
    out = itc.apply("t1", G, "2026-10", pv["plan_hash"], True)
    assert out["sent"] == 2 and out["int_tran_id"] == "IT-1" and "processed" in out["portal_status"] and out["recompute"] == "asked"
    save = [r for r in seen if r.url.path.endswith("/ims/save")][0]
    assert save.method == "PUT" and save.headers["gstin"] == G and save.headers["ret_period"] == "102026"
    body = json.loads(save.content)
    assert body["reqtyp"] == "SAVE" and body["rtin"] == G
    one = {x["inum"]: x for x in body["invdata"]["b2b"]}
    assert one["INV-001"]["action"] == "R" and one["INV-002"]["action"] == "P" and one["INV-002"]["idt"] == "06-10-2026" and one["INV-002"]["iamt"] == 360
    with pytest.raises(itc.ItcError):                                  # already sent: nothing waiting
        itc.apply("t1", G, "2026-10", pv["plan_hash"], True)


def test_repull_keeps_her_decisions_and_other_tenants_are_walled(a2):
    itc, seen, _ = a2
    itc.pull("t1", G, "2026-10")
    p = itc.propose("t1", G, "2026-10")
    rid = next(x["id"] for x in p["rows"] if x["number"] == "INV-002")
    itc.decide("t1", G, "2026-10", {rid: "accept"})
    assert itc.pull("t1", G, "2026-10")["decisions_kept"] == 1
    assert itc.decide("other", G, "2026-10", {rid: "reject"})["updated"] == 0
    assert [x["decided"] for x in itc.propose("t1", G, "2026-10")["rows"] if x["number"] == "INV-002"] == ["accept"]


def test_needs_a_live_connection_and_says_when_2b_is_not_ready(a2):
    itc, seen, plug = a2
    with pytest.raises(itc.ItcError) as e:
        itc.pull("nobody", G, "2026-10")
    assert "OTP" in str(e.value)
    plug(lambda req: httpx.Response(200, json={"status_cd": "1", "data": {"docdata": {}}}))
    with pytest.raises(itc.ItcError) as e:
        itc.pull("t1", G, "2026-10")
    assert "14th" in str(e.value)
    with pytest.raises(itc.ItcError):
        itc.propose("t1", G, "2026-09")


def test_routes_console_and_the_check_are_wired():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "app"
    api = (root / "bahi/api.py").read_text()
    for route in ("/api/bahi/itc/pull", "/api/bahi/itc/proposals", "/api/bahi/itc/decide", "/api/bahi/itc/preview", "/api/bahi/itc/apply"):
        assert route in api
    js = (root / "static/console/bahi.js").read_text()
    assert "itcapply" in js and "confirm: true" in js and "Credit (ITC)" in js
    chk = (root / "bahi/wbcheck.py").read_text()
    assert "gstr2b_all" in chk and "ims_invoices" in chk and "ims_save" not in chk
