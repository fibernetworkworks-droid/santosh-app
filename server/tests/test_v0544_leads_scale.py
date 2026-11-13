"""v0.544.0 P4 VENDOR LANE + SCALE - tests with ZERO network: the vendor speaks the ONE documented contract
through an httpx.MockTransport fake (the research R6 test shape), the fan-out enrich walk runs against fake
site passes with the in-flight bound PROVEN, and the store backend answers honestly. Everything else - the
gates, the priced-before-run refusal, the provenance law on vendor rows, the identity ladder, the bill's
honest-cost line, the tool, the API, the card guards - runs FOR REAL.

NOT VERIFIED, said plainly: no live vendor has ever answered this code; the fake is Hoola's side of the
documented contract only."""
import asyncio
import json

import httpx
import pytest

from tests.test_bazar import bz  # noqa: F401  (the env fixture: fresh DB, dry-run WhatsApp)
from tests.test_api import client  # noqa: F401

from app import leadscap
from app.leads import rules as R
from app.leads import scale as SC
from app.leads import service as S
from app.leads import vendor as V
from app.leads.models import ensure_tables

PG = __import__("os").environ.get("HOOLA_TEST_PG", "")


# ================================================================ the vendor world (the documented contract, faked)
def vrow(name="Acme Traders", phone="+91 98765 43210", src="https://vendor.example/records/acme", **kw):
    d = {"name": name, "phone": phone, "website": "https://acme.example", "email": "sales@acme.example",
         "address": "12 MG Road", "city": "Pune", "category": "traders", "source_url": src}
    d.update(kw)
    return d


def mock_world(rows=None, status=200, extra=None, calls=None, key="sekrit-key-123"):
    """The vendor's documented contract, answered by a MockTransport. `calls` collects (method, path, auth,
    body) so the tests can prove ONE call per run, the Bearer header, and that the key never leaks."""
    calls = calls if calls is not None else []

    def handler(req: httpx.Request) -> httpx.Response:
        calls.append({"method": req.method, "path": req.url.path,
                      "auth": req.headers.get("authorization", ""),
                      "body": json.loads(req.content.decode() or "{}")})
        if status >= 400:
            return httpx.Response(status, text="vendor said no")
        body = {"results": (rows if rows is not None else [])}
        body.update(extra or {})
        return httpx.Response(200, json=body)

    V._transport = httpx.MockTransport(handler)
    return calls


@pytest.fixture
def open_vendor(env):
    """The config gate open: she has named the vendor, set its key, price, cap and terms ack (restored)."""
    st = env["settings"]
    fields = ("leads_vendor_name", "leads_vendor_base_url", "leads_vendor_api_key",
              "leads_vendor_price_per_row_inr", "leads_vendor_run_cap_inr", "leads_vendor_terms_ack")
    keep = {k: getattr(st, k) for k in fields}
    st.leads_vendor_name = "acme-leads"
    st.leads_vendor_base_url = "https://api.acme.example"
    st.leads_vendor_api_key = "sekrit-key-123"
    st.leads_vendor_price_per_row_inr = 0.5
    st.leads_vendor_run_cap_inr = 2000.0
    st.leads_vendor_terms_ack = "acme-leads"
    yield st
    for k, v in keep.items():
        setattr(st, k, v)
    V._transport = None


def run_(c):
    return asyncio.run(c)


# ================================================================ the contract + the gate (R6 order)
def test_vendor_contract_documented():
    c = V.contract()
    assert c["request"]["path"] == "/leads/search" and c["request"]["method"] == "POST"
    assert "Bearer" in c["auth"] and "never" in c["auth"]
    assert set(c["row_required"]) == {"name", "source_url"}          # the provenance law is IN the contract
    assert "never reverse-engineered" in c["written_to"]             # SACH BOLO, said where a session looks


def test_gate_order_unconfigured_then_price_then_terms_then_cap(env):
    st = env["settings"]
    ok, why, kind = V.check("t1", 100)
    assert not ok and kind == "config" and "LEADS_VENDOR_NAME" in why and "12.4" in why
    st.leads_vendor_name, st.leads_vendor_base_url, st.leads_vendor_api_key = "acme", "https://a.example", "k"
    ok, why, kind = V.check("t1", 100)
    assert not ok and kind == "config" and "LEADS_VENDOR_PRICE_PER_ROW_INR" in why
    st.leads_vendor_price_per_row_inr = 0.5
    ok, why, kind = V.check("t1", 100)
    assert not ok and kind == "config" and "LEADS_VENDOR_TERMS_ACK" in why and "terms" in why
    st.leads_vendor_terms_ack = "acme"
    ok, why, kind = V.check("t1", 20_000)          # 20,000 x 0.5 = Rs 10,000 > Rs 2,000 cap
    assert not ok and kind == "cap" and "LEADS_VENDOR_RUN_CAP_INR" in why and "10,000" in why
    assert V.check("t1", 100) == (True, "", "ok")  # 100 x 0.5 = Rs 50 fits


def test_config_snapshot_never_carries_the_key(env):
    st = env["settings"]
    snap = V.config_snapshot()
    assert snap["key_set"] is False and "sekrit" not in json.dumps(snap)
    st.leads_vendor_api_key = "sekrit-key-123"
    snap = V.config_snapshot()
    assert snap["key_set"] is True and "sekrit-key-123" not in json.dumps(snap)   # boolean, never the key


def test_plan_card_refuses_vendor_ask_unconfigured(env):
    p = S.plan("t1", "vendor leads", ["VENDOR"], "Pune")
    assert p["ok"] is False and p["refused_lanes"] == ["VENDOR"]
    assert "LEADS_VENDOR_NAME" in json.dumps(p["why"], ensure_ascii=False)
    assert p["vendor"]["key_set"] is False                       # absent from the card until she configures


def test_plan_card_prices_the_vendor_run_when_configured(env, open_vendor):
    p2 = S.plan("t1", "vendor leads", ["VENDOR"], "Pune", planned_rows=100)
    assert p2["ok"] is True and p2["vendor"]["estimate_inr"] == 50.0
    assert p2["vendor"]["price_per_row_inr"] == 0.5 and "BEFORE" in p2["vendor"]["priced"]


# ================================================================ run_vendor: priced before, provenance always
def test_run_vendor_unconfigured_raises_before_any_run_row_or_call(env):
    ensure_tables()
    calls: list = []
    mock_world(rows=[vrow()], calls=calls)
    with pytest.raises(S.LeadsError) as e:
        run_(S.run_vendor("t1", "vendor leads", "contractors", "Pune", 100))
    assert "LEADS_VENDOR_NAME" in str(e.value)
    assert S.runs("t1") == [] and calls == []      # nothing ran: no run row, no call, no spend


def test_run_vendor_priced_before_the_run_cap_refusal_is_a_refused_card(open_vendor):
    out = run_(S.run_vendor("t1", "vendor leads", "contractors", "Pune", 20_000))
    assert out["ok"] is False and out["run"]["status"] == "REFUSED"
    assert "10,000" in out["run"]["error"] and "LEADS_VENDOR_RUN_CAP_INR" in out["run"]["error"]
    assert "2,000" in out["run"]["error"]


def test_run_vendor_happy_path_provenance_dedup_and_estimate_bill(open_vendor):
    ensure_tables()
    calls: list = []
    rows = [vrow(), vrow(name="Bharat Hardware", phone="9876500002",
                         src="https://vendor.example/records/bharat"),
            vrow(phone="+91 98765 43210", src="https://vendor.example/records/acme-again")]  # same phone -> dup
    mock_world(rows=rows, calls=calls)
    out = run_(S.run_vendor("t1", "Pune traders", "traders", "Pune", 100))
    assert out["ok"] is True and out["run"]["status"] == "DONE"
    assert len(calls) == 1 and calls[0]["path"] == "/leads/search"          # ONE call, never retried
    assert calls[0]["auth"] == "Bearer sekrit-key-123"
    assert calls[0]["body"] == {"query": "traders", "city": "Pune", "max_rows": 100}
    r = out["run"]
    assert (r["found"], r["kept"], r["duped"], r["refused"]) == (3, 2, 1, 0)
    got = {x["name"]: x for x in S.rows("t1")["rows"]}
    assert got["Acme Traders"]["source_lane"] == "VENDOR"
    assert got["Acme Traders"]["source_url"] == "https://vendor.example/records/acme"
    assert got["Acme Traders"]["parser_version"] == "v0.691.0-vd1"
    assert got["Acme Traders"]["phone"] == "919876543210"                   # the E.164 law applies to vendor rows
    bill = r["bill"]
    assert bill["lane"] == "VENDOR" and bill["vendor"] == "acme-leads"
    assert bill["cost_reported_by_vendor"] is False
    assert bill["inr"] == 1.5 and bill["estimate_inr_before"] == 50.0       # 3 delivered x Rs 0.5, not the ask
    assert "ESTIMATE" in bill["note"]
    assert leadscap.usage("t1")["rows_kept"] == 2                           # the day ledger counted the kept rows


def test_vendor_row_without_its_own_source_url_is_refused_never_stored(open_vendor):
    rows = [vrow(), vrow(name="No Source Traders", src="")]
    mock_world(rows=rows)
    out = run_(S.run_vendor("t1", "vendor leads", "traders", "Pune", 100))
    assert (out["run"]["found"], out["run"]["refused"]) == (1, 1)
    assert all(x["name"] != "No Source Traders" for x in S.rows("t1")["rows"])
    r2 = vrow(name="Bogus Src", src="not-a-url")
    mock_world(rows=[r2])
    out2 = run_(S.run_vendor("t2", "vendor leads", "traders", "Pune", 100))
    assert out2["run"]["refused"] == 1 and out2["run"]["found"] == 0


def test_vendor_ids_ride_the_identity_ladder(open_vendor):
    rows = [vrow(place_id="ChIJN1t_tDeuEmsRUsoyG82frLA4", phone="")]
    mock_world(rows=rows)
    out = run_(S.run_vendor("t1", "vendor leads", "traders", "Pune", 100))
    assert out["run"]["kept"] == 1
    got = S.rows("t1")["rows"][0]
    assert got["key_type"] == "place_id" and got["key_value"] == "ChIJN1t_tDeuEmsRUsoyG82frLA4"


def test_vendor_401_aborts_the_run_and_never_leaks_the_key(open_vendor):
    mock_world(status=401)
    out = run_(S.run_vendor("t1", "vendor leads", "traders", "Pune", 100))
    assert out["ok"] is False and out["run"]["status"] == "ABORTED"
    assert "401" in out["run"]["error"] and "LEADS_VENDOR_API_KEY" in out["run"]["error"]
    assert "sekrit-key-123" not in out["run"]["error"]                       # the key never rides an error
    assert "sekrit-key-123" not in json.dumps(out["run"]["bill"])


def test_vendor_500_aborts_one_call_only_never_pay_twice(open_vendor):
    calls: list = []
    mock_world(status=500, calls=calls)
    out = run_(S.run_vendor("t1", "vendor leads", "traders", "Pune", 100))
    assert out["run"]["status"] == "ABORTED" and "500" in out["run"]["error"]
    assert len(calls) == 1                              # a retried create may have succeeded - never repeated


def test_vendor_reported_cost_wins_and_says_so(open_vendor):
    mock_world(rows=[vrow(), vrow(name="Bharat Hardware", phone="9876500002")], extra={"cost_inr": 12.5})
    out = run_(S.run_vendor("t1", "vendor leads", "traders", "Pune", 100))
    bill = out["run"]["bill"]
    assert bill["cost_reported_by_vendor"] is True and bill["inr"] == 12.5
    assert "khud ka" in bill["note"]                    # the bill says the number is the vendor's own


def test_per_run_row_cap_refuses_the_raw_ask_before_any_call(open_vendor, monkeypatch):
    monkeypatch.setattr(open_vendor, "leads_vendor_price_per_row_inr", 0.001)   # vendor est tiny: Rs 50
    calls: list = []
    mock_world(rows=[vrow()], calls=calls)
    out = run_(S.run_vendor("t1", "vendor leads", "traders", "Pune", 50_000))
    assert out["ok"] is False and out["run"]["status"] == "REFUSED"     # the receipt card, like every cap
    assert "5,000" in out["run"]["error"] and calls == []               # the ROW cap refused the RAW ask


def test_leads_run_tool_vendor_action(env, open_vendor):
    from app.agent.leads_tools import LEADS_HANDLERS

    class _C:
        tenant_id, conversation_id, actor = "t1", "c1", "owner"

    calls: list = []
    mock_world(rows=[vrow()], calls=calls)
    out = run_(LEADS_HANDLERS["leads_run"](_C(), action="vendor", ask="vendor leads",
                                           query="traders", city="Pune", max_rows=50))
    assert out["ok"] is True and out["run"]["status"] == "DONE"
    assert calls[0]["body"]["max_rows"] == 50
    with pytest.raises(Exception) as e:
        run_(LEADS_HANDLERS["leads_run"](_C(), action="vendor", ask="x", query=""))
    assert "Query" in str(e.value)


def test_vendor_through_the_api(env, open_vendor, monkeypatch):
    from app.config import get_settings
    with client(monkeypatch, env, api_key="secret") as c:
        st = get_settings()                     # the client rebuilt the cache - open the gate on THIS object
        st.leads_vendor_name = "acme-leads"
        st.leads_vendor_base_url = "https://api.acme.example"
        st.leads_vendor_api_key = "sekrit-key-123"
        st.leads_vendor_price_per_row_inr = 0.5
        st.leads_vendor_run_cap_inr = 2000.0
        st.leads_vendor_terms_ack = "acme-leads"
        mock_world(rows=[vrow()])               # the recorded vendor world rides the transport seam
        h = {"Authorization": "Bearer secret"}
        r = c.post("/api/leads/runs/vendor", headers=h, json={"ask": "vendor", "query": "traders", "city": "Pune"})
        assert r.status_code == 200 and r.json()["run"]["status"] == "DONE"
        assert r.json()["run"]["bill"]["lane"] == "VENDOR"


def test_vendor_api_unconfigured_is_a_400_with_the_config_named(env, monkeypatch):
    with client(monkeypatch, env, api_key="secret") as c:
        h = {"Authorization": "Bearer secret"}
        r = c.post("/api/leads/runs/vendor", headers=h, json={"ask": "vendor", "query": "traders"})
        assert r.status_code == 400 and "LEADS_VENDOR_NAME" in r.json()["detail"]


# ================================================================ SCALE: the store backend says what is true
def test_store_backend_honest_on_sqlite(env):
    b = SC.store_backend()
    assert b["engine"] == "sqlite" and b["country_scale"] is False
    assert "postgresql" in b["note"]                    # the note names what country-scale needs


def test_leads_status_carries_the_backend(env):
    from app.agent.leads_tools import LEADS_HANDLERS

    class _C:
        tenant_id, conversation_id, actor = "t1", "c1", "owner"

    out = run_(LEADS_HANDLERS["leads_status"](_C()))
    assert out["store_backend"]["engine"] in ("sqlite", "postgresql")


@pytest.mark.skipif(not PG, reason="HOOLA_TEST_PG not set")
def test_store_backend_and_leads_roundtrip_on_postgres(env):
    b = SC.store_backend()
    assert b["engine"] == "postgresql" and b["country_scale"] is True
    out = S.run_her_data("t_pg", "pg roundtrip", [{"name": "PG Traders", "phone": "9876511111",
                                                   "address": "MG Road"}], "her-data")
    assert out["ok"] is True and out["run"]["kept"] == 1
    assert S.rows("t_pg")["total"] == 1
    assert leadscap.usage("t_pg")["rows_kept"] == 1     # the cap ledger works on the PG dialect too


# ================================================================ SCALE: the fan-out enrich walk (the graph)
def test_fanout_bounded_in_flight_and_complete():
    cur = {"n": 0, "max": 0}

    async def compute(row):
        cur["n"] += 1
        cur["max"] = max(cur["max"], cur["n"])
        await asyncio.sleep(0.005)
        cur["n"] -= 1
        return {"row": row}

    out = asyncio.run(SC.enrich_fanout(list(range(37)), compute, max_in_flight=3))
    assert out["chunks"] == 4                                   # the static fan-out: 4 chunk edges
    assert len(out["results"]) == 37                            # the JOIN BARRIER: every row answered
    assert cur["max"] <= 3                                      # the shared Semaphore held the bound
    assert out["seconds"] >= 0.0


def test_fanout_error_rows_ride_through_and_none_is_dropped():
    async def compute(row):
        if row == 5:
            return {"kind": "error", "error": "boom"}
        if row % 7 == 0:
            return None                                         # a row with no website: nothing to apply
        return {"kind": "ok"}

    out = asyncio.run(SC.enrich_fanout(list(range(20)), compute, max_in_flight=4))
    kinds = [r["kind"] for r in out["results"]]
    assert kinds.count("error") == 1 and "boom" in out["results"][kinds.index("error")]["error"]
    assert len(out["results"]) == 17                            # 20 - 1 error - 3 None (0, 7, 14)


def test_fanout_empty_is_a_honest_empty():
    out = asyncio.run(SC.enrich_fanout([], lambda r: None))
    assert out["results"] == [] and out["chunks"] == 0


# ---- the enrich fixtures (the same recorded sites as v0542, so the two modes read the same world)
HOME = """<html><head><title>Medplus Pharmacy - Pune</title></head><body>
<nav><a href="/contact-us">Contact</a></nav>
<p>Write to <a href="mailto:Info@MedPlus.in">us</a> or sales@medplus.in</p></body></html>"""
DEAD_SITE, CHALLENGE, EMPTY_SITE = "https://dead.in", "https://blocked.in", "https://empty.in"


class _Page:
    def __init__(self, url, html, status=200):
        self.url, self.html_content, self.status = url, html, status


def fake_enrich_world(monkeypatch):
    from app.leads import enrich as E
    pages = {"https://a.in": HOME, "https://a.in/contact-us": HOME,
             DEAD_SITE: None, CHALLENGE: ('<html><head><title>Just a moment...</title></head>'
                                          '<body><script>window._pxAppId="PX1";</script></body></html>', 403),
             EMPTY_SITE: "<html><body><p>no contact here</p></body></html>"}

    def fake_get(url, tenant_id, **k):
        hit = pages.get(url)
        if hit is None:
            raise ConnectionError(f"site dead: {url}")
        html, status = hit if isinstance(hit, tuple) else (hit, 200)
        return _Page(url, html, status)

    monkeypatch.setattr(E, "_get", fake_get)
    monkeypatch.setattr(E, "_robots_ok", lambda u: True)
    monkeypatch.setattr(E, "HOST_MIN_INTERVAL", 0.0)
    monkeypatch.setattr(E, "_resolve_dns", lambda d: d == "medplus.in")
    monkeypatch.setattr(E, "_resolve_mx", lambda d: d == "medplus.in")


def _seed(tenant):
    """Four rows, one per outcome: an enrichable site, a dead site (own-domain email -> galat), a blocked
    site, and a site with no email at all."""
    S.add_row(tenant, {"name": "Alive Traders", "phone": "9100000001", "website": "https://a.in",
                       "address": "a street"}, "HER_DATA", "her-file.csv")
    S.add_row(tenant, {"name": "Dead Traders", "phone": "9100000002", "website": DEAD_SITE,
                       "email": "rahul@dead.in", "address": "b street"}, "HER_DATA", "her-file.csv")
    S.add_row(tenant, {"name": "Blocked Traders", "phone": "9100000003", "website": CHALLENGE,
                       "address": "c street"}, "HER_DATA", "her-file.csv")
    S.add_row(tenant, {"name": "Quiet Traders", "phone": "9100000004", "website": EMPTY_SITE,
                       "address": "d street"}, "HER_DATA", "her-file.csv")


def _by_name(tenant):
    return {x["name"]: x for x in S.rows(tenant)["rows"]}


def test_enrich_serial_and_fanout_agree_card_names_the_mode(env, monkeypatch):
    fake_enrich_world(monkeypatch)
    _seed("t_serial")
    _seed("t_fan")
    a = run_(S.enrich("t_serial", use_model=False))
    assert a["mode"] == "serial" and a["max_in_flight"] == 1
    b = run_(S.enrich("t_fan", use_model=False, fanout=True))
    assert b["mode"] == "graph_fanout" and b["max_in_flight"] >= 2 and b["chunks"] >= 1
    for k in ("enriched", "dead_site", "blocked", "no_email", "picks"):
        assert a[k] == b[k], f"{k} drifted between the modes: {a[k]} != {b[k]}"
    for name, row in _by_name("t_serial").items():
        other = _by_name("t_fan")[name]
        assert row["email"] == other["email"] and row["email_grade"] == other["email_grade"]
        assert row["enrich_note"] == other["enrich_note"]
    assert _by_name("t_fan")["Dead Traders"]["email_grade"] == "galat"      # the dead-site law held on the walk
    assert _by_name("t_fan")["Alive Traders"]["email"] in ("info@medplus.in", "sales@medplus.in")
    assert _by_name("t_fan")["Quiet Traders"]["email"] == ""
    card = b["run"]["plan"]
    assert card["mode"] == "graph_fanout" and card["max_in_flight"] >= 2    # the plan card names the shape


def test_enrich_fanout_cap_still_refuses_at_plan_time(env, monkeypatch):
    fake_enrich_world(monkeypatch)
    _seed("t1")
    monkeypatch.setattr(env["settings"], "leads_enrich_rows_per_run", 2)
    with pytest.raises(S.LeadsError) as e:
        run_(S.enrich("t1", use_model=False, fanout=True))
    assert "2 rows per pass" in str(e.value)                                # the cap is mode-blind


def test_leads_enrich_tool_carries_fanout(env, monkeypatch):
    from app.agent.leads_tools import LEADS_HANDLERS

    class _C:
        tenant_id, conversation_id, actor = "t1", "c1", "owner"

    fake_enrich_world(monkeypatch)
    _seed("t1")
    out = run_(LEADS_HANDLERS["leads_enrich"](_C(), use_model=False, fanout=True))
    assert out["ok"] is True and out["mode"] == "graph_fanout"


def test_enrich_fanout_through_the_api(env, monkeypatch):
    fake_enrich_world(monkeypatch)
    S.add_row("default", {"name": "Alive Traders", "place_id": "PID_FAN", "website": "https://a.in"},
              "OFFICIAL_API", "https://maps.google.com/?cid=FAN")
    with client(monkeypatch, env, api_key="secret") as c:
        h = {"Authorization": "Bearer secret"}
        r = c.post("/api/leads/enrich", headers=h, json={"use_model": False, "fanout": True})
        assert r.status_code == 200 and r.json()["mode"] == "graph_fanout"


# ================================================================ the surface: registry, lanes, card set v5
def test_registry_stays_562_and_the_tool_schemas_carry_p4(env):
    from app.agent.leads_tools import LEADS_TOOLS, LEADS_HANDLERS
    from app.agent.tools import TOOLS
    assert len(TOOLS) == 630                                    # +1 hoola_pc_batch (v0.885); +1 app_engine (v0.824); +1 seekh_video (v0.713 SEEKH MANCH); the registry pin, the lane rode leads_run
    for t in LEADS_TOOLS:
        assert t["name"] in LEADS_HANDLERS
    run_tool = next(t for t in LEADS_TOOLS if t["name"] == "leads_run")
    assert "vendor" in run_tool["input_schema"]["properties"]["action"]["enum"]
    enrich_tool = next(t for t in LEADS_TOOLS if t["name"] == "leads_enrich")
    assert "fanout" in enrich_tool["input_schema"]["properties"]
    assert "action=vendor" in run_tool["description"] and "fanout=true" in enrich_tool["description"]


def test_ladder_complete_and_unknown_lane_still_refused_by_name(env):
    assert set(R.LANE_BUILT) == set(R.LANES) and R.LANE_ARRIVES == {}
    assert R.LANE_BUILT["VENDOR"] == "P4"
    p = S.plan("t1", "ask", ["BOGUS_LANE"], "x")
    assert p["ok"] is False and "BOGUS_LANE" in p["refused_lanes"]
    assert any("koi lane hi nahi hai" in w for w in p["why"])


def test_card_set_v6_all_guards_on(env):
    from app.quality.lead_asks import ASKS, LEADS_SET_V
    from app.quality.leadscard import free_card
    assert LEADS_SET_V == 6
    card = free_card()
    g = card["guards"]
    for k in ("vendor_built", "vendor_gate_holds", "vendor_price_named", "vendor_cap_named",
              "vendor_provenance_required", "vendor_cost_honest", "enrich_fanout_built",
              "store_backend_named", "ladder_complete", "lane_refused_by_name", "rule_text_amended"):
        assert g.get(k) is True, f"guard {k} is off: {g.get(k)}"
    assert card["set"] == 6 and card["guards_ok"] == len(g)   # v0.684.0: the outreach walls joined
    ids = {a["id"] for a in ASKS}
    assert {"tool_vendor", "rule_vendor_off", "tool_outreach_log", "rule_handoff_confirm"} <= ids


def test_asks_ok_tools_are_real_and_vendor_rule_scores(env):
    from app.quality.lead_asks import ASKS
    from app.quality.leadscard import _score_rule
    for a in ASKS:
        if a["kind"] == "tool":
            assert set(a["ok"]) <= {"leads_run", "leads_status", "leads_list", "leads_export",
                                    "leads_forget", "leads_enrich"}
    row = _score_rule({"guard": "vendor_off"}, "Vendor abhi configure nahi hai - pehle naam, key, price aur "
                                              "terms set kijiye, phir run", [])
    assert row["right"] is True
    bad = _score_rule({"guard": "vendor_off"}, "Theek hai, abhi vendor ko bhej deta hoon, kar dunga", [])
    assert bad["right"] is False
