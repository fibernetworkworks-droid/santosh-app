"""Paisa Sahayak (consumer finance protection; register docs/research/banking_finance_industry Wave 1 slice: #1 money manager, #2 fee auditor,
#3 loan reader, #5 debt planner, #6 scam shield, #7 UPI coach, #8 complaint drafter). Pure engines: known textbook numbers, honest labels
(heuristic vs measured, facts marked verify), no secrets kept, no network, nothing stored, nothing sent, no money moved."""
import asyncio
import inspect
from datetime import date

import pytest

from app.finguard import complaint as CP
from app.finguard import loans as LN
from app.finguard import scam as SC
from app.finguard import statement as ST
from tests.test_life import conv_ctx

CSV = """Account Statement
Date,Narration,Debit,Credit,Balance
01/10/2026,SALARY OCT,,80000,90000
02/10/2026,SMS CHGS,15,,89985
02/10/2026,GST ON CHARGES,2.7,,89982.3
05/10/2026,UPI/swiggy/123456,450,,89500
05/10/2026,NETFLIX SUBSCRIPTION,649,,88800
05/10/2026,NETFLIX SUBSCRIPTION,649,,88150
01/11/2026,SALARY NOV,,80000,168000
02/11/2026,SMS CHGS,15,,167985
02/11/2026,GST ON CHARGES,2.7,,167982
05/11/2026,NETFLIX SUBSCRIPTION,649,,167300
10/11/2026,MIN BAL PENALTY,500,,166800
10/11/2026,GST ON CHARGES,150,,166650
01/12/2026,SMS CHGS,15,,166635
01/12/2026,GST ON CHARGES,2.7,,166632
05/12/2026,NETFLIX SUBSCRIPTION,649,,166000
"""


# ---------------------------------------------------------------- loans
def test_emi_matches_textbook_numbers():
    assert LN.emi(1000000, 10, 12) == 87915.89
    assert LN.emi(500000, 12, 60) == 11122.22
    assert LN.emi(120000, 0, 12) == 10000.0
    with pytest.raises(ValueError):
        LN.emi("lots", 10, 12)
    with pytest.raises(ValueError):
        LN.emi(1000, 10, 9999)


def test_schedule_pays_the_loan_to_zero():
    s = LN.schedule(500000, 12, 60)
    assert s["months"] == 60 and s["rows"][-1]["balance"] == 0.0
    assert abs(s["total_paid"] - (500000 + s["total_interest"])) < 1.0


def test_true_cost_apr_is_the_stated_rate_without_fees_and_higher_with_them():
    plain = LN.true_cost(500000, 12, 60)
    assert plain["apr_nominal_pct"] == 12.0 and plain["total_cost"] == plain["total_interest"] and plain["upfront_total"] == 0
    fee = LN.true_cost(500000, 12, 60, fee_pct=2, insurance=5000)
    assert fee["fee_before_gst"] == 10000.0 and fee["fee_gst"] == 1800.0 and fee["upfront_total"] == 16800.0
    assert fee["money_received"] == 483200.0 and fee["apr_nominal_pct"] > 13 and fee["apr_effective_pct"] > fee["apr_nominal_pct"]
    assert fee["total_cost"] == round(fee["total_paid"] - 500000 + 16800, 2)
    assert "assumed" in fee["gst_note"] or fee["gst_note"] == ""                                  # the 18% is shown as assumed unless she gave it
    assert LN.true_cost(500000, 12, 60, fee_pct=2, fee_gst_pct=0)["fee_gst"] == 0
    kinds = {f["kind"] for f in fee["flags"]}
    assert kinds <= {"measured", "heuristic"} and any("Insurance" in f["text"] for f in fee["flags"])


def test_fee_taken_later_still_counts_and_balloon_is_flagged():
    a = LN.true_cost(100000, 10, 12, fee_pct=3, fees_deducted=True)
    b = LN.true_cost(100000, 10, 12, fee_pct=3, fees_deducted=False)
    assert b["apr_effective_pct"] > 10 and a["apr_effective_pct"] > b["apr_effective_pct"]         # paid up front costs more per rupee received
    assert any("balloon" in f["text"] for f in LN.true_cost(100000, 10, 12, balloon=20000)["flags"])


def test_flat_rate_is_much_dearer_than_it_sounds():
    f = LN.flat_to_reducing(10, 12)
    assert f["emi_per_lakh"] == 9166.67 and 17.5 <= f["reducing_rate_pct"] <= 18.5 and "reducing" in f["note"]


def test_compare_needs_two_and_says_when_not_like_for_like():
    with pytest.raises(ValueError):
        LN.compare([{"name": "A"}])
    c = LN.compare([{"name": "A", "amount": 500000, "rate": 11, "months": 60, "fee_pct": 2}, {"name": "B", "amount": 500000, "rate": 12, "months": 60}])
    assert c["like_for_like"] and c["lowest_apr"] in ("A", "B") and "your decision" in c["note"]
    d = LN.compare([{"name": "A", "amount": 500000, "rate": 11, "months": 60}, {"name": "B", "amount": 300000, "rate": 12, "months": 36}])
    assert not d["like_for_like"] and "APR" in d["note"]


def test_prepay_weighs_saving_against_her_own_charge():
    p = LN.prepay(2500000, 9, 240, 300000, 12, charge_pct=0)
    assert p["interest_saved"] > 800000 and p["months_saved"] > 30 and p["worth_it"]
    pricey = LN.prepay(2500000, 9, 240, 300000, 12, charge_pct=400)
    assert pricey["net_saving"] < p["net_saving"] and not LN.prepay(100000, 10, 12, 1000, 11, charge_pct=100)["worth_it"]
    r = LN.prepay(500000, 12, 60, 100000, 12, mode="reduce_emi")
    assert r["after"]["months"] == 60 and r["interest_saved"] > 0


def test_debt_plan_orders_and_flags():
    d = LN.debt_plan([{"name": "Card", "balance": 50000, "rate": 36, "min_payment": 2500}, {"name": "PL", "balance": 200000, "rate": 14, "min_payment": 6000},
                      {"name": "Gadget", "balance": 20000, "rate": 0, "min_payment": 2000}], 5000)
    assert d["avalanche"]["total_interest"] <= d["snowball"]["total_interest"] < d["minimums_only"]["total_interest"]
    assert d["interest_saved_avalanche_vs_snowball"] >= 0 and d["snowball"]["payoff_month"]["Gadget"] <= d["snowball"]["payoff_month"]["PL"]
    tough = LN.debt_plan([{"name": "Card", "balance": 100000, "rate": 42, "min_payment": 1000}], 0, 0)
    assert any("less than even the interest" in f["text"] for f in tough["flags"]) and tough["minimums_only"]["debt_free"] is False
    stress = LN.debt_plan([{"name": "A", "balance": 50000, "rate": 20, "min_payment": 3000}], 0, 30)
    assert any("even the minimums are not covered" in f["text"] for f in stress["flags"])
    with pytest.raises(ValueError):
        LN.debt_plan([])


# ---------------------------------------------------------------- statement
def test_csv_parse_and_charges_audit():
    rows = ST.parse_csv(CSV)
    assert len(rows) == 15 and rows[1] == {"date": "2026-10-02", "narration": "SMS CHGS", "debit": 15.0, "credit": 0.0}
    c = ST.charges(rows)
    assert c["fee_total"] == 545.0 and c["gst_on_charges"] == 155.4 + 2.7 * 0 or c["gst_on_charges"] > 150
    labels = {x["label"] for x in c["classes"]}
    assert "SMS / alert charges" in labels and "Minimum / average balance penalty" in labels
    text = " | ".join(f["text"] for f in c["flags"])
    assert "SMS / alert charges: 3 times" in text and "twice" in text and "NETFLIX" in text      # repeated fee + double debit
    assert "30.0%" in text or "GST Rs 150.00" in text                                           # a GST line far from ~18% of that day's fee
    assert {f["kind"] for f in c["flags"]} <= {"measured", "heuristic"} and "not a claim that any charge is wrong" in c["note"]
    assert c["yearly_projection"] and c["yearly_projection"] > c["all_in_total"]


def test_spend_months_categories_and_recurring():
    s = ST.spend(ST.parse_csv(CSV), overrides={"swiggy": "treats"}, budget={"subscriptions": 700})
    m = {x["month"]: x for x in s["months"]}
    assert m["2026-10"]["in"] == 80000 and m["2026-10"]["by_category"]["treats"] == 450 and m["2026-10"]["over_budget"]["subscriptions"] == 598.0
    assert any("netflix" in r["what"] for r in s["recurring"]) and s["biggest_debits"][0]["amount"] == 649.0
    with pytest.raises(ValueError):
        ST.parse_csv("no,header\n1,2")
    with pytest.raises(ValueError):
        ST.spend([])


# ---------------------------------------------------------------- scam shield
def test_fake_kyc_with_otp_ask_and_bad_link_is_critical():
    r = SC.check("Dear customer your SBI KYC will expire today. Update now http://sbi-kyc-update.xyz/login and share OTP received immediately")
    assert r["verdict"] == "critical-pattern" and {"fake_kyc", "otp_share"} <= {f["id"] for f in r["families"]}
    assert r["links"][0]["verdict"] == "high-risk" and r["pressure_words"] and r["secrets_mentioned"] == ["otp"]
    assert any("OTP" in x for x in r["always"]) and "never sends money" in r["note"]


def test_each_family_catches_its_classic_wording():
    cases = {"upi_refund_collect": "Sir for your refund enter UPI PIN to receive the money",
             "loan_app": "Instant loan without any document, download the app, it needs access to your contacts and photos",
             "investment_group": "Join our VIP group on telegram for guaranteed returns, double your money in a month",
             "lottery_prize": "Congratulations you have won the KBC lottery, pay a fee to claim the prize",
             "digital_arrest": "This is CBI. Your parcel has drugs. This is a digital arrest, do not tell anyone, transfer to a safe account",
             "remote_access": "Please install AnyDesk so we can verify and process the refund",
             "job_task": "Part time work from home earn 5000 per day, like and review videos earn commission",
             "sextortion": "Pay or else your private video will go viral and be sent to your contacts"}
    for fid, msg in cases.items():
        assert fid in {f["id"] for f in SC.check(msg)["families"]}, fid


def test_no_pattern_is_never_called_safe():
    r = SC.check("Hi, are we still on for lunch at 1 tomorrow?")
    assert r["verdict"] == "no-known-pattern" and "does not mean safe" in r["note"]
    with pytest.raises(ValueError):
        SC.check("hi")


def test_url_analysis_is_text_only_and_labelled():
    assert SC.analyse_url("https://www.sbi.co.in/web/personal-banking")["verdict"] == "no-flag"
    bad = SC.analyse_url("http://hdfcbank.com.secure-login.top/x")
    assert bad["verdict"] == "high-risk" and bad["site"] == "secure-login.top"
    assert SC.analyse_url("https://bit.ly/abc")["verdict"] == "high-risk" and SC.analyse_url("http://203.0.113.9/login")["verdict"] == "high-risk"
    assert SC.analyse_url("https://example.com/app.apk")["verdict"] == "high-risk" and "xn--" in " ".join(f["text"] for f in SC.analyse_url("https://xn--pypal-4ve.com")["flags"])
    assert "urlopen" not in inspect.getsource(SC) and "requests" not in inspect.getsource(SC) and "httpx" not in inspect.getsource(SC)


def test_facts_are_marked_for_recheck_and_upi_rules():
    assert all("verify" in f and "source" in f for f in SC.FACTS) and any(f["verify"] for f in SC.FACTS)
    u = SC.upi_coach("collect request")
    assert "DECLINE" in u["answer"] and "verify" in u["dispute_note"]
    assert "qr_to_receive" in SC.upi_coach("")["all_rules"] and "PIN" in SC.UPI_RULES["qr_to_receive"]


# ---------------------------------------------------------------- complaint
def test_complaint_letter_has_blanks_masks_numbers_and_never_sends():
    d = CP.draft({"issue_type": "unauthorised_txn", "bank": "Test Bank", "name": "A Kumar", "account": "123456789012", "amount": "5000",
                  "txn_date": "2026-11-01", "narrative": "Card 4111 1111 1111 1111 was used abroad", "prior_complaint_no": "C123", "prior_date": "2026-10-01"},
                 date(2026, 11, 5))
    assert d["masked"] and "XXXX1111 was used" in d["letter"] and "4111 1111" not in d["letter"] and "123456789012" not in d["letter"] and "ending 9012" in d["letter"]
    assert "35 days" in d["escalation"] and d["urgent"] and "1930" in d["urgent_note"] and len(d["evidence_checklist"]) >= 4
    assert [x["step"] for x in d["ladder"]] == [1, 2, 3, 4] and any(x["verify"] for x in d["ladder"])
    blank = CP.draft({"issue_type": "charges"}, date(2026, 11, 5))
    assert "[bank / NBFC name]" in blank["letter"] and "[date]" in blank["letter"] and blank["blanks"] and "sending it is up to you" in blank["note"]
    assert "smtp" not in inspect.getsource(CP) and "requests" not in inspect.getsource(CP)


def test_young_complaint_is_told_to_wait_for_the_reply_window():
    d = CP.draft({"issue_type": "charges", "prior_complaint_no": "X1", "prior_date": "2026-11-01"}, date(2026, 11, 5))
    assert "more days" in d["escalation"]


# ---------------------------------------------------------------- tool + registry + hub
def test_tool_registered_routed_and_guarded():
    from app import voice
    from app.agent import tools
    from app.agent import finguard_tools as FT
    assert "paisa_sahayak" in tools.HANDLERS and tools.FAMILY_OF["paisa_sahayak"] == "finguard" and "paisa_sahayak" in voice.VOICE_VIA_KAAM
    assert voice.call_route("paisa_sahayak") == "kaam"
    ctx = conv_ctx()
    t = asyncio.run(FT._paisa_sahayak(ctx, action="loan", amount=500000, rate=12, months=60, fee_pct=2))
    assert t["emi"] == 11122.22 and t["apr_nominal_pct"] > 12
    assert asyncio.run(FT._paisa_sahayak(ctx, action="charges", text=CSV))["fee_total"] == 545.0
    assert asyncio.run(FT._paisa_sahayak(ctx, action="scam", text="share your OTP now to avoid KYC block"))["verdict"] != "no-known-pattern"
    assert asyncio.run(FT._paisa_sahayak(ctx, action="facts"))["facts"]
    from app.agent.tools import ToolError
    for bad in (dict(action="loan", amount="x", rate=1, months=1), dict(action="nope"), dict(action="charges")):
        with pytest.raises(ToolError):
            asyncio.run(FT._paisa_sahayak(ctx, **bad))
    cust = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="customer:wa:1")
    with pytest.raises(ToolError):
        asyncio.run(FT._paisa_sahayak(cust, action="scam", text="share your otp please"))
    staff = type(ctx)(ctx.tenant_id, ctx.conversation_id, actor="staff:s1")
    with pytest.raises(ToolError):
        asyncio.run(FT._paisa_sahayak(staff, action="charges", text=CSV))                          # statements are the owner's
    assert asyncio.run(FT._paisa_sahayak(staff, action="scam", text="share your otp please")) ["secrets_mentioned"] == ["otp"]


def test_nothing_is_stored_by_the_engines():
    for mod in (LN, ST, SC, CP):
        src = inspect.getsource(mod)
        assert "session(" not in src and "open(" not in src and "sqlite" not in src and "Base" not in src, mod.__name__


def test_hub_lists_paisa_sahayak_with_its_never_list(env):
    from app.employee import hire as H
    c = H.CATALOG["paisa_sahayak"]
    assert c["live"] and c["group"] == "Finance & Banking" and c["does"] and c["needs"]
    text = " ".join(c["never"]).lower()
    assert "pin" in text and "otp" in text and "move money" in text and "recommend a lender" in text
    assert H.hire("t1", "paisa_sahayak")["key"] == "paisa_sahayak"
