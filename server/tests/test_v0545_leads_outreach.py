"""v0.684.0 P5 OUTREACH HANDOFF + PROOF - the plan section 10 finale, tests with ZERO network:

- the campaign hand-off is TWO TAPS: the first returns a CONFIRM CARD and creates nothing (no list, no refs,
  no ledger rows), the second (confirm=true) builds - "her tap, confirm card" said in code;
- the opt-out ledger the campaign desk honours is EXTENDED TO LEADS at SEND time too: a store row she opted out
  after the hand-off never joins the queue (create_campaign re-checks through LeadListRef);
- the send moment WRITES the ledger: worker.send_batches -> note_campaign_sends (campaign_sent), and the email
  desk's send_draft -> note_email_sends (email_sent) through a fake box - the engine still never sends;
- the ledger is READABLE (outreach_log / GET /api/leads/outreach / leads_export action=outreach_log), the
  kind/desk vocabulary is CHECKED (rules.OUTREACH_KINDS / OUTREACH_DESKS), and a forgotten row's events stay;
- the CI LOAD PROOF: 5,000 rows END-TO-END under the caps - one her-data run keeps exactly 5,000 (the cap
  number itself), the day ledger counts them, the export ships all 5,000, the hand-off copies all 5,000 with
  consent False, and a 5,001-row ask is REFUSED at plan time with the cap named - never silently truncated.

NOT VERIFIED, said plainly: the WhatsApp send here is the dry-run client and the email send a fake box - her
first live campaign/e-mail from a leads list confirms the desks' side; the ledger code paths themselves are
the real ones (the same session() and tables the desks use)."""
import asyncio
import json

import pytest

from tests.test_bazar import bz  # noqa: F401  (the env fixture: fresh DB, dry-run WhatsApp)
from tests.test_api import client  # noqa: F401

from app import leadscap
from app.leads import rules as R
from app.leads import service as S
from app.leads.models import LeadListRef, LeadOutreach, ensure_tables


def run_(c):
    return asyncio.run(c)


# ================================================================ the two-tap hand-off (confirm card first)
def test_handoff_first_tap_is_confirm_card_and_creates_nothing(env):
    S.run_her_data("t1", "ask", [{"name": "A", "phone": "9876500001"}, {"name": "B", "phone": "9876500002"}],
                   "f.csv")
    out = S.campaign_list("t1", "Dentists")
    assert out["kind"] == "leads_handoff_confirm" and out["confirm_required"] is True
    assert out["rows"] == 2 and out["rows_without_phone"] == 0 and out["opt_out_excluded"] == 0
    assert "consent=False" in out["consent"] and "confirm=true" in out["confirm"]
    ensure_tables()
    from app.db import LeadList, session
    with session() as s:
        assert s.query(LeadList).count() == 0                    # nothing was built
        assert s.query(LeadOutreach).count() == 0                # nothing was led


def test_handoff_confirm_tap_builds_list_refs_and_ledger(env):
    S.run_her_data("t1", "ask", [{"name": "A", "phone": "9876500001"}, {"name": "B", "phone": "9876500002"}],
                   "f.csv")
    card = S.campaign_list("t1", "Dentists")
    out = S.campaign_list("t1", "Dentists", confirm=True)
    assert out["confirmed"] is True and out["rows"] == 2 and out["list_id"]
    ensure_tables()
    from app.db import Lead, LeadList, session
    with session() as s:
        ll = s.get(LeadList, out["list_id"])
        assert ll is not None and ll.valid == 2 and ll.opted_in == 0 and ll.has_consent_column
        leads = s.query(Lead).filter(Lead.list_id == ll.id).all()
        assert len(leads) == 2 and all(l.opted_in is False for l in leads)
        assert s.query(LeadListRef).filter(LeadListRef.list_id == ll.id).count() == 2
        assert s.query(LeadOutreach).filter(LeadOutreach.kind == "campaign_list",
                                            LeadOutreach.ref == ll.id).count() == 2


def test_handoff_card_names_the_opt_out_rows_it_excludes(env):
    S.run_her_data("t1", "ask", [{"name": "A", "phone": "9876500001"}, {"name": "B", "phone": "9876500002"},
                                 {"name": "C", "phone": "9876500003"}], "f.csv")
    store = S.rows("t1")
    aid = next(r["id"] for r in store["rows"] if r["name"] == "A")
    S.set_opt_out("t1", aid, True)
    card = S.campaign_list("t1", "L")
    assert card["rows"] == 2 and card["opt_out_excluded"] == 1   # the card says who stayed home
    out = S.campaign_list("t1", "L", confirm=True)
    assert out["rows"] == 2 and out["opt_out_excluded"] == 1
    ensure_tables()
    from app.db import Lead, session
    with session() as s:
        phones = {l.phone for l in s.query(Lead).filter(Lead.list_id == out["list_id"]).all()}
        assert phones == {"919876500002", "919876500003"}


def test_record_outreach_rejects_unknown_kind_and_desk(env):
    row = S.add_row("t1", {"name": "A", "phone": "9876500001"}, "HER_DATA", "x.csv")
    with pytest.raises(S.LeadsError, match="kind"):
        S.record_outreach("t1", [row["id"]], "sms_blast", "ref", "campaign")   # no invented kinds
    with pytest.raises(S.LeadsError, match="desk"):
        S.record_outreach("t1", [row["id"]], "email_sent", "ref", "scrapedesk")


def test_outreach_log_readable_filterable_and_survives_forget(env):
    a = S.add_row("t1", {"name": "A", "phone": "9876500001", "email": "a@acme.in"}, "HER_DATA", "x.csv")
    b = S.add_row("t1", {"name": "B", "phone": "9876500002"}, "HER_DATA", "x.csv")
    S.record_outreach("t1", [a["id"]], "email_sent", "eml_1", "email")
    S.record_outreach("t1", [b["id"]], "campaign_sent", "cmp_9", "campaign")
    log = S.outreach_log("t1")
    assert log["kind"] == "leads_outreach_log" and log["count"] == 2
    assert log["by_kind"] == {"email_sent": 1, "campaign_sent": 1}
    by_id = {e["contact_id"]: e for e in log["events"]}
    assert by_id[a["id"]]["name"] == "A" and by_id[a["id"]]["desk"] == "email"
    kinds = S.outreach_log("t1", kind="email_sent")
    assert kinds["count"] == 1 and kinds["events"][0]["kind"] == "email_sent"
    with pytest.raises(S.LeadsError):
        S.outreach_log("t1", kind="sms_blast")
    # the DPO erasure deletes the row, the ledger event stays (the history is not the person)
    S.forget("t1", row_ids=[a["id"]])
    after = S.outreach_log("t1")
    gone = [e for e in after["events"] if e["contact_id"] == a["id"]]
    assert gone and gone[0]["name"] == "(row miti hui)" and gone[0]["key_value"] == ""


# ================================================================ the campaign desk: opt-out at SEND time
def _mk_template():
    from app.db import Template, session
    with session() as s:
        t = Template(tenant_id="t1", name="leads-promo", language="en", category="MARKETING",
                     body="Namaste {{1}}, naya offer hai.", example_values=["ji"], status="APPROVED")
        s.add(t)
        s.flush()
        return t.id


def _mk_conv():
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="t1", title="leads test")
        s.add(c)
        s.flush()
        return c.id


def test_create_campaign_skips_store_rows_opted_out_after_handoff(env):
    from app.campaigns import create_campaign
    from app.db import OutboundMessage, session
    S.run_her_data("t1", "ask", [{"name": "A", "phone": "9876500001"}, {"name": "B", "phone": "9876500002"}],
                   "f.csv")
    out = S.campaign_list("t1", "L", confirm=True)
    store = S.rows("t1")
    aid = next(r["id"] for r in store["rows"] if r["name"] == "A")
    S.set_opt_out("t1", aid, True)                               # opted out AFTER the copy was made
    tid = _mk_template()
    v = create_campaign(tenant_id="t1", conversation_id=_mk_conv(), title="T", lead_list_id=out["list_id"],
                        template_id=tid, param_mapping=[{"source": "static", "value": "ji"}],
                        consent_confirmed=True, auto_send=True, only_opted_in=False)
    assert v["leads_opt_out_skipped"] == 1                       # the card names who did not join
    with session() as s:
        phones = {m.phone for m in s.query(OutboundMessage).filter(OutboundMessage.campaign_id == v["id"]).all()}
        assert phones == {"919876500002"}                        # the opted-out row never queued


def test_create_campaign_refuses_when_every_store_row_opted_out(env):
    from app.campaigns import create_campaign
    S.run_her_data("t1", "ask", [{"name": "A", "phone": "9876500001"}], "f.csv")
    out = S.campaign_list("t1", "L", confirm=True)
    store = S.rows("t1")
    S.set_opt_out("t1", store["rows"][0]["id"], True)
    tid = _mk_template()
    with pytest.raises(Exception, match="opt-out"):
        create_campaign(tenant_id="t1", conversation_id=_mk_conv(), title="T", lead_list_id=out["list_id"],
                        template_id=tid, param_mapping=[{"source": "static", "value": "ji"}],
                        consent_confirmed=True, auto_send=True, only_opted_in=False)


# ================================================================ the send moment writes the ledger
def test_note_campaign_sends_writes_ledger_for_store_copies_only(env):
    from app.db import Lead, session
    S.run_her_data("t1", "ask", [{"name": "A", "phone": "9876500001"}, {"name": "B", "phone": "9876500002"}],
                   "f.csv")
    out = S.campaign_list("t1", "L", confirm=True)
    # a plain imported lead (her own CSV, never a store row) rides the same list
    with session() as s:
        plain = Lead(list_id=out["list_id"], name="Plain", phone="919999999999", opted_in=False)
        s.add(plain)
        s.flush()
        plain_id = plain.id
    assert S.note_campaign_sends("t1", "cmp_1", []) == 0
    n = S.note_campaign_sends("t1", "cmp_1", [out["rows"] and 0 or 0])   # falsy ids: no-op
    assert n == 0
    with session() as s:
        store_copy_ids = [r.lead_row_id for r in s.query(LeadListRef).filter(LeadListRef.list_id == out["list_id"]).all()]
    n = S.note_campaign_sends("t1", "cmp_1", store_copy_ids + [plain_id, 999999])
    assert n == 2                                               # only the store copies land in the ledger
    with session() as s:
        evs = s.query(LeadOutreach).filter(LeadOutreach.kind == "campaign_sent",
                                           LeadOutreach.ref == "cmp_1").all()
        assert len(evs) == 2 and all(e.desk == "campaign" for e in evs)


def test_worker_send_batches_writes_campaign_sent_ledger(env):
    """The real send path: handoff -> campaign -> her confirm_send -> the worker's dry-run sends -> the ledger."""
    from app.campaigns import confirm_send, create_campaign
    from app.db import OutboundMessage, session
    from app import worker
    S.run_her_data("t1", "ask", [{"name": "A", "phone": "9876500001"}, {"name": "B", "phone": "9876500002"},
                                 {"name": "C", "phone": "9876500003"}], "f.csv")
    out = S.campaign_list("t1", "L", confirm=True)
    tid = _mk_template()
    v = create_campaign(tenant_id="t1", conversation_id=_mk_conv(), title="T", lead_list_id=out["list_id"],
                        template_id=tid, param_mapping=[{"source": "static", "value": "ji"}],
                        consent_confirmed=True, auto_send=False, only_opted_in=False)
    confirm_send(v["id"])                                        # HER tap
    run_(worker.send_batches(max_seconds=1.0))
    with session() as s:
        sent = s.query(OutboundMessage).filter(OutboundMessage.campaign_id == v["id"],
                                               OutboundMessage.status == "sent").count()
        queued = s.query(OutboundMessage).filter(OutboundMessage.campaign_id == v["id"]).count()
        ledger = s.query(LeadOutreach).filter(LeadOutreach.kind == "campaign_sent",
                                              LeadOutreach.ref == v["id"]).count()
    assert sent >= 1                                             # the dry-run WhatsApp sends (a few fail by design)
    assert ledger == sent                                        # every real send is on the ledger, nothing else


# ================================================================ the email desk: ledger on send
class _FakeBox:
    key, address, name = "fake", "shop@example.com", "Shop"
    kind = "smtp"

    def send(self, msg, thread_id=None):
        return {"message_id": "<fake@x>"}


def test_email_send_draft_writes_email_sent_ledger(env, monkeypatch):
    import app.mailbox.service as MB
    a = S.add_row("t1", {"name": "A", "phone": "9876500001", "email": "owner@acme.in"}, "HER_DATA", "x.csv")
    b = S.add_row("t1", {"name": "B", "phone": "9876500002", "email": "other@acme.in"}, "HER_DATA", "x.csv")
    from app.db import EmailDraft, session
    conv = _mk_conv()                                    # the draft rides a REAL conversation (notify FKs it)
    with session() as s:
        d = EmailDraft(tenant_id="t1", conversation_id=conv, to_addr="Owner@Acme.in, stranger@nowhere.in",
                       subject="Namaste", body="leads engine se aapki detail mili thi", status="pending")
        s.add(d)
        s.flush()
        did = d.id
    monkeypatch.setattr(MB, "get_box", lambda tenant, account=None: _FakeBox())
    monkeypatch.setattr(MB, "get_undo_seconds", lambda tenant: 0)
    out = MB.send_draft("t1", did)
    assert out["status"] == "sent"
    log = S.outreach_log("t1", kind="email_sent")
    ids = {e["contact_id"] for e in log["events"]}
    assert ids == {a["id"]}                                      # the store row got its ledger row...
    assert all(e["ref"] == did and e["desk"] == "email" for e in log["events"])
    # an unknown address records nothing; a lead whose email never went out is absent
    assert b["id"] not in ids


# ================================================================ the tool + the API
def test_tool_leads_export_confirm_and_outreach_log(env):
    from app.agent.leads_tools import LEADS_HANDLERS

    class _C:
        tenant_id, conversation_id, actor = "t1", "c1", "owner"

    S.run_her_data("t1", "ask", [{"name": "A", "phone": "9876500001"}], "f.csv")
    card = run_(LEADS_HANDLERS["leads_export"](_C(), action="campaign_list", name="L"))
    assert card["confirm_required"] is True
    out = run_(LEADS_HANDLERS["leads_export"](_C(), action="campaign_list", name="L", confirm=True))
    assert out["confirmed"] is True and out["list_id"]
    with pytest.raises(Exception):
        run_(LEADS_HANDLERS["leads_export"](_C(), action="campaign_list", name="L2",
                                            run_id="LR-wrong-run-id-x", confirm=True))
    S.record_outreach("t1", [S.rows("t1")["rows"][0]["id"]], "campaign_list", out["list_id"], "campaign")
    log = run_(LEADS_HANDLERS["leads_export"](_C(), action="outreach_log"))
    # the hand-off already wrote its own campaign_list row; the desk-side record adds the second
    assert log["kind"] == "leads_outreach_log" and log["count"] == 2
    assert set(log["by_kind"]) == {"campaign_list"}
    with pytest.raises(Exception):
        run_(LEADS_HANDLERS["leads_export"](_C(), action="bogus"))


def test_api_campaign_list_two_taps_and_outreach_endpoint(env, monkeypatch):
    with client(monkeypatch, env, api_key="secret") as c:
        h = {"Authorization": "Bearer secret"}
        c.post("/api/leads/runs/her-data", headers=h,
               json={"ask": "f", "rows": [{"name": "A", "phone": "9876500001"}], "source_name": "f.csv"})
        card = c.post("/api/leads/campaign-list", headers=h, json={"name": "API"}).json()
        assert card["confirm_required"] is True and card["rows"] == 1
        out = c.post("/api/leads/campaign-list", headers=h, json={"name": "API", "confirm": True}).json()
        assert out["confirmed"] is True and out["rows"] == 1
        log = c.get("/api/leads/outreach", headers=h).json()
        assert log["kind"] == "leads_outreach_log" and log["count"] == 1
        assert log["events"][0]["kind"] == "campaign_list" and log["events"][0]["desk"] == "campaign"
        kind_log = c.get("/api/leads/outreach", headers=h, params={"kind": "email_sent"}).json()
        assert kind_log["count"] == 0
        bad = c.get("/api/leads/outreach", headers=h, params={"kind": "sms_blast"})
        assert bad.status_code == 400


# ================================================================ the CI LOAD PROOF (plan section 10)
def _load_rows(n: int) -> list[dict]:
    return [{"name": f"Shop {i}", "phone": f"99{i:08d}", "category": "kirana",
             "address": f"{i} Market Road", "city": "Pune"} for i in range(n)]


def test_load_proof_5000_rows_end_to_end_under_caps(env):
    """The plan's CI proof: 5,000 rows END-TO-END under the caps - kept, counted, exported, handed off - and
    the 5,001st refused AT PLAN TIME with the cap named. Zero network; the same tables and code the desks run."""
    t = "loadtest"
    cap = leadscap.caps()["per_run"]
    assert cap == 5000                                           # the proof rides the default cap, not a raised one
    out = S.run_her_data(t, "poore sheher ki dukaanein", _load_rows(5000), "bada.csv", place="Pune")
    assert out["ok"] is True and out["run"]["status"] == "DONE"
    assert out["run"]["kept"] == 5000 and out["run"]["duped"] == 0
    # the day ledger counted every row (a forget() later cannot erase the day's count)
    u = leadscap.usage(t)
    assert u["rows_kept"] == 5000 and u["per_day_left"] == u["per_day"] - 5000
    # the export ships all 5,000, every one with provenance
    ex = S.export_csv(t)
    assert ex["rows"] == 5000 and len(ex["csv"].strip().splitlines()) == 5001
    assert '"HER_DATA"' in ex["csv"] or "HER_DATA" in ex["csv"]
    # the hand-off copies all 5,000 with consent False, on the second tap
    card = S.campaign_list(t, "Badi list")
    assert card["confirm_required"] is True and card["rows"] == 5000
    hand = S.campaign_list(t, "Badi list", confirm=True)
    assert hand["rows"] == 5000 and hand["list_id"]
    ensure_tables()
    from app.db import Lead, LeadList, session
    with session() as s:
        assert s.get(LeadList, hand["list_id"]).valid == 5000
        assert s.query(LeadListRef).filter(LeadListRef.list_id == hand["list_id"]).count() == 5000
        assert s.query(LeadOutreach).filter(LeadOutreach.kind == "campaign_list",
                                            LeadOutreach.ref == hand["list_id"]).count() == 5000
        assert s.query(Lead).filter(Lead.list_id == hand["list_id"]).filter(Lead.opted_in.is_(False)).count() == 5000
    # the ledger reads it back fast enough to be a desk view, not a query job
    log = S.outreach_log(t, limit=1000)
    assert log["count"] == 1000 and log["by_kind"]["campaign_list"] == 1000
    # the caps still stand: row 5,001 is a REFUSED card at plan time, with the cap named
    refused = S.run_her_data(t, "ek aur", _load_rows(5001), "x.csv", place="Pune")
    assert refused["ok"] is False and refused["run"]["status"] == "REFUSED"
    assert "5,000" in refused["plan"]["cap_refusal"]
    # and the day's remaining headroom is what it says (nothing was smuggled past the ledger)
    assert leadscap.usage(t)["rows_kept"] == 5000


# ================================================================ the card (set v6)
def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.858.0"
    from pathlib import Path
    pub = Path(__file__).resolve().parents[2] / "pubspec.yaml"
    assert "0.858.0+857" in pub.read_text()


def test_card_set_v6_outreach_guards(env):
    from app.quality import lead_asks, leadscard
    assert lead_asks.LEADS_SET_V == 6
    c = leadscard.free_card()
    g = c["guards"]
    for k in ("handoff_confirm_card", "opt_out_honoured_at_send", "campaign_sent_ledger", "email_sent_ledger",
              "outreach_ledger_queryable", "consent_false_handoff", "engine_never_sends"):
        assert g.get(k), f"guard off: {k}"
    ids = {a["id"] for a in lead_asks.ASKS}
    assert {"tool_outreach_log", "rule_handoff_confirm"} <= ids
    # the live scorer's new guard, scored on a reply like the model would give
    ok = leadscard._score_rule({"guard": "handoff_confirm"},
                               "Pehle confirm card dikhata hoon - 2 rows, consent False. List confirm=true par banegi.",
                               [])
    assert ok["right"] is True
    bad = leadscard._score_rule({"guard": "handoff_confirm"}, "Theek hai, main sabko turant bhej dunga.", [])
    assert bad["right"] is False
    # the tool schema carries the new action and the confirm flag
    from app.agent.leads_tools import LEADS_TOOLS
    ex = next(t for t in LEADS_TOOLS if t["name"] == "leads_export")
    assert "outreach_log" in ex["input_schema"]["properties"]["action"]["enum"]
    assert "confirm" in ex["input_schema"]["properties"]
