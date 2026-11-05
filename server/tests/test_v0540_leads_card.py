"""v0.540.0 LEADS card - the free card runs offline in CI: are the five tools registered AND reachable from her
words, and do the walls REALLY stand (fired for real, not read from a comment): the cap refuses a 50,000-row ask
with the number named, an unbuilt lane is refused by name with its phase, the export refuses unprovenanced rows,
the hand-off copies consent=False, and the service module contains no sending machinery at all."""
import json

import pytest

from tests.test_bazar import bz  # noqa: F401  (the env fixture: fresh DB, dry-run WhatsApp)

from app.quality import leadscard as LC
from app.quality.lead_asks import ASKS, LEADS_SET_V


def test_asks_shape():
    ids = [a["id"] for a in ASKS]
    assert len(ids) == len(set(ids))
    for a in ASKS:
        assert a["kind"] in ("tool", "rule")
        if a["kind"] == "tool":
            assert a.get("ok"), a["id"]
        else:
            assert a.get("guard"), a["id"]
    tool_asks = [a for a in ASKS if a["kind"] == "tool"]
    for t in ("leads_run", "leads_status", "leads_list", "leads_export", "leads_forget"):
        assert any(t in a["ok"] for a in tool_asks), f"{t} is never the right tool for any ask"


def test_free_card_all_guards_on(env):
    card = LC.free_card()
    assert card["kind"] == "free" and card["set"] == LEADS_SET_V
    assert card["asks"] == len(ASKS)
    assert card["registered"] == 5, card["not_registered"]
    assert card["reachable"] == 5, card["unreachable"]
    assert card["right_in_view"] == card["tool_asks"], [r for r in card["rows"] if not r["in_view"]]
    assert card["tool_asks"] == sum(1 for a in ASKS if a["kind"] == "tool")
    off = {k: v for k, v in card["guards"].items() if not v}
    assert off == {}, off


def test_guards_fired_for_real(env):
    from app import leadscap
    from app.leads import service as S
    g = LC.guards_in_code()
    # the cap refusal is not a string match on a comment - the cap really fired on a 50,000-row ask
    with pytest.raises(leadscap.LeadsCapped) as e:
        leadscap.check_run("__leadscard__", 50_000)
    assert "5,000" in str(e.value)
    p = S.plan("__leadscard__", "Nagpur contractors", ["SCRAPE"], "Nagpur")
    assert p["ok"] is False and p["refused_lanes"] == ["SCRAPE"]
    assert g["provenance_gate"] and g["cap_refuses"] and g["lane_refused_by_name"]
    assert g["consent_false_handoff"] and g["engine_never_sends"] and g["outreach_is_ledger"]
    assert g["forget_exists"] and g["opt_out_default_export"]
    assert g["tools_carry_never_send"] and g["store_boundary_written"]


def test_export_refuses_unprovenanced_rows(env):
    from app.db import session
    from app.leads.models import LeadContact
    from app.leads import service as S
    with session() as s:                       # a row that skipped the gate (as a buggy lane never could)
        s.add(LeadContact(tenant_id="tX", key_type="kgmid", key_value="k1", name="Ghost",
                          source_lane="", source_url=""))
    with pytest.raises(S.LeadsError, match="provenance"):
        S.export_csv("tX")


def test_live_scoring_rules(env):
    r = LC._score_rule({"guard": "cap_refuses"}, "Yeh 50,000 rows ka cap 5,000 hai - plan chhota kijiye, refuse.", [])
    assert r["right"] is True
    r = LC._score_rule({"guard": "cap_refuses"}, "Theek hai, chala raha hoon.", [])
    assert r["right"] is False and r["misses"]
    r = LC._score_rule({"guard": "lane_off"}, "Scrape lane abhi OFF hai - woh P3 mein aayega, aapki haan chahiye.", [])
    assert r["right"] is True
    r = LC._score_rule({"guard": "never_sends"}, "Sabko bhej diya!", [])
    assert r["right"] is False and r["misses"]
    r = LC._score_rule({"guard": "official_first"},
                       "Pehle aapka apna data, phir official lanes (IndiaMART, Places) - scrape P3 mein, aapki haan se.", [])
    assert r["right"] is True


def test_card_save_and_lines(env, tmp_path, monkeypatch):
    monkeypatch.setenv("QUALITY_DIR", str(tmp_path))
    card = LC.free_card()
    saved = LC.save(card, "test")
    assert saved["file"].startswith("leadscard-free-")
    rows = LC.saved()
    assert rows and rows[0]["file"] == saved["file"]
    text = LC.lines(LC.free_card())
    assert text and "Leads card" in text[0] and "guards" in text[0]
    assert not [ln for ln in text if "guard off" in ln or "NOT REGISTERED" in ln]


def test_json_serialisable(env):
    card = LC.free_card()
    json.dumps(card, ensure_ascii=False)      # the saved card must never fail on a Hinglish refusal string
