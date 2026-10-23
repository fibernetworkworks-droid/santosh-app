"""IT Helpdesk Sahayak: playbooks + priority / SLA rules, step-by-step runner, her Haan (only by tap) on system changes, secrets
scrubbed, asset register + repeat detector, technician escalation draft, known issue (outage) linking, phishing check with the
CERT-In 6-hour clock, worker tick (SLA alerts, CERT-In reminders, morning note), tools (staff / customer actors) and API."""
import asyncio
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.helpdesk.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"


@pytest.fixture
def hd(env, monkeypatch):
    from app.helpdesk import service as S
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    S.EVENTS = events
    return S


def kinds(S):
    return [k for k, _ in S.EVENTS]


def test_rules_and_playbooks():
    from app.helpdesk import playbooks as P
    from app.helpdesk import rules as R
    assert P.detect("accounts wale PC par printer nahi chal raha, paper jam")[0] == "printer"
    assert P.detect("Tally bahut slow hai")[0] == "tally"
    assert P.detect("sab ka wifi band hai")[0] == "network"
    assert P.detect("password bhool gayi, account lock ho gaya")[0] == "account"
    assert P.detect("ajeeb mail aaya, link par click kar diya")[0] == "security"
    for cid, p in P.PLAYBOOKS.items():
        assert p["steps"] and p["escalate_when"] and p["tell"], cid
        assert [s for s in p["steps"] if s.get("careful")] == [s for s in p["steps"] if s.get("careful")], cid
        for s in p["steps"]:
            assert s.get("change", "") in ("", *P.CHANGE_LABEL), (cid, s["id"])
    assert R.priority("all", "high") == "P1" and R.priority("one", "normal") == "P4" and R.priority("several", "normal") == "P3"
    assert R.priority("one", "low", security=True) == "P2" and R.priority("one", "low", money_or_data=True) == "P1"
    assert R.impact_of("poore office ka net band") == "all" and R.urgency_of("client baitha hai, jaldi") == "high"
    assert R.sla_for("P2") == {"respond_h": 1, "resolve_h": 8} and R.sla_for("P2", {"P2": {"resolve_h": 6}})["resolve_h"] == 6
    assert R.cert_in("company", "phishing", {"clicked": True})["applies"] is True
    assert R.cert_in("proprietor", "malware")["applies"] is True
    assert R.cert_in("individual", "malware")["applies"] is False
    assert R.cert_in("company", "phishing", {})["applies"] is None
    assert "12 Oct 2027" in R.os_note("Windows 10 Pro 22H2", date(2026, 10, 23)) and R.os_note("Windows 11", date(2026, 10, 23)) == ""
    assert "koi security update nahi" in R.os_note("Windows 7", date(2026, 10, 23))
    ph = R.phish_check("URGENT: aapka account 24 ghante mein block ho jayega. KYC update karein: http://sbi-kyc-update.in/login "
                       "aur OTP batayein. Attached: KYC_form.html", sender="alerts@sbi-secure-mail.com")
    ids = {f["id"] for f in ph["flags"]}
    assert ph["verdict"] == "likely_phish" and {"lookalike_sbi", "urgency", "bait", "asks_secret", "bad_attachment"} <= ids
    ok = R.phish_check("Meeting kal 11 baje hai, agenda attached.", sender="ramesh@gmail.com")
    assert ok["verdict"] == "unclear" and not ok["flags"]
    real = R.phish_check("Your statement is ready https://www.onlinesbi.sbi/", sender="noreply@sbi.co.in")
    assert not any(f["id"].startswith("lookalike") for f in real["flags"])
    assert R.dpdp(True, date(2026, 10, 23))["live"] is False and R.dpdp(True, date(2027, 6, 1))["live"] is True


def test_steps_and_her_haan_on_settings(hd):
    S = hd
    S.save_settings(T, office_name="Ingle Traders", entity="proprietor")
    S.save_asset(T, name="Accounts PC", kind="pc", user="Ramesh", os="Windows 10 Pro")
    pr = S.save_asset(T, name="Reception printer", kind="printer", brand="HP", model="LaserJet 1020", serial="VNB3K12345")["asset"]
    out = S.new_ticket(T, "Ramesh ke PC se print nahi ho raha", person="Ramesh", asset=pr["tag"], actor="owner")
    tk = out["ticket"]
    assert tk["number"] == "HD-0001" and tk["category"] == "printer" and tk["asset"]["tag"] == pr["tag"]
    assert tk["priority"] == "P4" and tk["current"]["id"] == "power_paper" and "Step 1/" in out["say"]
    assert kinds(S)[-1] == "helpdesk_ticket"
    tid = tk["id"]
    for _ in range(4):                                    # power, cable, restart, queue: no luck
        r = S.step(T, tid, "not_fixed", actor="owner")
    assert r["ticket"]["status"] == "waiting_haan" and r["ticket"]["current"]["id"] == "default_printer"
    ch = r["ticket"]["change"]
    assert ch and ch["status"] == "waiting" and ch["kind"] == "setting" and "haan" in r["say"].lower()
    assert "helpdesk_change" in kinds(S)
    # staff can't do a system change before her Haan; the tool path can't approve
    with pytest.raises(S.HelpdeskError):
        S.step(T, tid, "fixed", actor="staff:x")
    with pytest.raises(S.HelpdeskError):
        S.decide_change(T, ch["id"], True, ch["hash"])                      # no by_tap
    with pytest.raises(S.HelpdeskError):
        S.decide_change(T, ch["id"], True, "wrong", by_tap=True)
    d = S.decide_change(T, ch["id"], True, ch["hash"], by_tap=True)
    assert d["change"]["status"] == "approved" and "Settings > Printers" in d["say"]
    assert S.get_ticket(T, tid)["status"] == "working"
    again = S.decide_change(T, ch["id"], False, ch["hash"], by_tap=True)
    assert again["change"]["status"] == "approved"                           # decided once
    done = S.step(T, tid, "fixed", note="default printer galat tha", actor="staff:x")
    assert done["resolved"] and S.get_ticket(T, tid)["fixed_by"] == "default_printer"
    assert S.changes(T)[0]["status"] == "done"
    # a rejected change is skipped, the next step comes
    t2 = S.new_ticket(T, "printer phir se nahi chal raha", asset=pr["tag"])["ticket"]["id"]
    assert S.get_ticket(T, t2)["current"]["id"] == "default_printer"         # what fixed it here comes first now
    c2 = S.get_ticket(T, t2)["change"]
    no = S.decide_change(T, c2["id"], False, c2["hash"], reason="abhi nahi", by_tap=True)
    assert no["change"]["status"] == "rejected" and S.get_ticket(T, t2)["current"]["id"] == "power_paper"
    assert S.known(T, "printer")[0]["step"] == "default_printer"
    # owner herself doing the change step counts as her decision
    t3 = S.new_ticket(T, "laptop bahut slow hai")["ticket"]["id"]
    v = S.get_ticket(T, t3)
    for st in v["steps"]:
        if st["change"]:
            break
        S.step(T, t3, "not_fixed")
    r = S.step(T, t3, "fixed", actor="owner")
    assert r["resolved"] and "Owner ne khud kiya" in r["ticket"]["steps"][-1]["note"] + "".join(x["note"] for x in r["ticket"]["steps"])


def test_secrets_scrubbed_and_account(hd):
    S = hd
    out = S.new_ticket(T, "Gmail login nahi ho raha, password is Ramesh@1234 aur account lock ho gaya")
    tk = out["ticket"]
    assert "Ramesh@1234" not in tk["text"] and "[hataya]" in tk["text"] and "badal dijiye" in out["say"]
    assert tk["category"] == "account" and "Password / OTP Hoola ko kabhi mat" in out["say"]
    r = S.step(T, tk["id"], "not_fixed", note="otp 482913 aaya tha")
    assert "482913" not in str(S.get_ticket(T, tk["id"])["log"]) and "482913" not in str(r["ticket"]["steps"])


def test_assets_repeat_escalate(hd):
    S = hd
    S.save_settings(T, office_name="Ingle Traders")
    S.save_vendor(T, "Sai Computers", kind="amc", phone="+91 98220 12345", email="sai@example.com", covers=["pc", "printer"],
                  amc_until="2027-03-31", sla_hours=4)
    a = S.save_asset(T, name="Billing PC", kind="pc", brand="Dell", model="Vostro 3681", serial="7XK9P2", user="Sunita", os="Windows 10",
                     bought="2019-06-01", warranty_until="2022-06-01", vendor="Sai")["asset"]
    assert a["vendor"] == "Sai Computers" and a["tag"] == "A-001"
    assert any("Windows 10" in x for x in a["advice"]) and any("saal purana" in x for x in a["advice"])
    with pytest.raises(S.HelpdeskError):
        S.save_vendor(T, "Bad", phone="12345")
    ids = []
    for i in range(3):
        r = S.new_ticket(T, "Sunita ka PC chalu nahi ho raha, blue screen", person="Sunita")
        ids.append(r["ticket"]["id"])
        assert r["ticket"]["asset"]["tag"] == "A-001"                         # her one PC picked by person + kind
    assert "90 din mein 2 baar" in r["say"]
    av = S.asset_view(T, "A-001")
    assert av["repeat"]["count_90d"] == 3 and any("AMC" not in x and "baar" in x for x in av["advice"]) and len(av["tickets"]) == 3
    e = S.escalate(T, ids[-1])
    esc = e["escalation"]
    assert esc["vendor"]["name"] == "Sai Computers" and "7XK9P2" in esc["text"] and "Ingle Traders" in esc["text"]
    assert esc["wa_link"].startswith("https://wa.me/919822012345") and esc["mailto"].startswith("mailto:sai@example.com")
    assert e["ticket"]["status"] == "waiting_tech" and kinds(S)[-1] == "helpdesk_escalate"
    tu = S.tech_update(T, ids[-1], "SSD lagaya", True, 3200)
    assert tu["ticket"]["status"] == "resolved" and tu["ticket"]["cost"] == 3200
    # steps exhausted -> escalation by itself (no vendor for the ISP: maps link)
    n = S.new_ticket(T, "internet nahi chal raha")["ticket"]["id"]
    for _ in range(12):
        v = S.get_ticket(T, n)
        if v["status"] == "waiting_tech":
            break
        if v["change"] and v["change"]["status"] == "waiting":
            out = S.decide_change(T, v["change"]["id"], False, v["change"]["hash"], by_tap=True)
            continue
        out = S.step(T, n, "not_fixed")
    assert S.get_ticket(T, n)["status"] == "waiting_tech" and "upay khatam" in out["say"]
    assert S.get_ticket(T, n)["escalation"]["links"]
    sync = S.sync_pcs(T)
    assert sync["added"] == []


def test_known_issue_links_outage(hd):
    S = hd
    a = S.new_ticket(T, "net band hai", person="Ramesh")["ticket"]
    b = S.new_ticket(T, "mere system par bhi internet nahi", person="Sunita")
    assert b["ticket"]["parent_id"] == a["id"] and a["number"] in b["say"] and b["ticket"]["impact"] == "several"
    assert b["ticket"]["priority"] in ("P3", "P2")
    c = S.new_ticket(T, "printer jam", person="Sunita")["ticket"]
    assert c["parent_id"] == ""
    r = S.step(T, a["id"], "fixed", note="router restart")
    assert b["ticket"]["number"] in r["say"] and S.get_ticket(T, b["ticket"]["id"])["status"] == "resolved"
    assert S.set_status(T, b["ticket"]["id"], "reopen")["ticket"]["status"] == "working"


def test_phishing_cert_in_clock_and_tick(hd, monkeypatch):
    S = hd
    S.save_settings(T, office_name="Ingle Traders", entity="company", contact_name="Meghana", contact_email="it@example.com")
    r = S.report_phish(T, "Dear customer, your HDFC account will be blocked within 24 hours. Verify: http://hdfc-netbank-verify.co/kyc "
                          "and share OTP.", sender="support@hdfc-alerts.co", person="Ramesh", clicked=True, entered_password=True)
    inc = r["incident"]
    assert inc["analysis"]["verdict"] == "likely_phish" and r["cert_in"]["applies"] is True and inc["report_due"]
    assert "incident@cert-in.org.in" in r["cert_in_draft"] and "Ingle Traders" in r["cert_in_draft"]
    assert any("password badaliye" in x for x in r["actions"]) and any("net hataiye" in x for x in r["actions"])
    tk = r["ticket"]
    assert tk["security"] and tk["priority"] in ("P1", "P2") and tk["category"] == "security" and tk["current"]["id"] == "disconnect"
    assert S.EVENTS[-1][0] == "helpdesk_alert"
    n0 = datetime.now(timezone.utc)
    S.EVENTS.clear()
    out = S.tick(n0 + timedelta(hours=4, minutes=30))
    assert out["cert_in"] == 1 and any("bache" in p.get("say", "") for _, p in S.EVENTS)
    out = S.tick(n0 + timedelta(hours=6, minutes=5))
    assert out["cert_in"] >= 1 and any("6 ghante poore" in p.get("say", "") for _, p in S.EVENTS)
    S.EVENTS.clear()
    assert S.tick(n0 + timedelta(hours=7))["cert_in"] == 0                   # said once
    monkeypatch.setattr(S, "clock", lambda: n0 + timedelta(hours=7))
    rep = S.cert_in_reported(T, inc["id"], "CERTIn-2026-1234")
    assert rep["incident"]["status"] == "reported" and "6 ghante ke baad" in rep["say"]
    # money gone -> P1 + 1930 first; just a mail received -> no clock
    m = S.report_phish(T, "Your parcel is held at customs, pay Rs 49 fee: bit.ly/xyz", sender="+91 90000 00000", money=True)
    assert m["ticket"]["priority"] == "P1" and "1930" in m["actions"][0]
    q = S.report_phish(T, "You won a lottery prize! Claim now", sender="lucky@winner.biz")
    assert q["incident"]["report_due"] == "" and q["cert_in"]["applies"] is None
    S.save_settings(T, entity="individual")
    h = S.report_phish(T, "virus aa gaya", kind="malware")
    assert h["cert_in"]["applies"] is False and h["incident"]["report_due"] == ""
    assert len(S.incidents(T)) == 4


def test_sla_alerts_and_morning(hd, monkeypatch):
    S = hd
    S.save_settings(T, morning_time="09:30", sla={"P1": {"respond_h": 0.25, "resolve_h": 2}})
    t = S.new_ticket(T, "poore office ka net band, client baitha hai")["ticket"]
    assert t["priority"] == "P1"
    n0 = datetime.now(timezone.utc)
    S.EVENTS.clear()
    S.tick(n0 + timedelta(minutes=30))
    assert any("jawab nahi diya" in p.get("say", "") for _, p in S.EVENTS)
    S.EVENTS.clear()
    S.tick(n0 + timedelta(hours=3))
    says = [p.get("say", "") for k, p in S.EVENTS if k == "helpdesk_alert"]
    assert any("samay nikal gaya" in x for x in says) and not any("jawab nahi diya" in x for x in says)
    monkeypatch.setattr(S, "clock", lambda: n0 + timedelta(hours=3))
    d = S.day(T)
    assert d["late"] and "der se" in d["say"]
    # morning note once a day
    from app.life import tz_of
    loc = datetime(2030, 1, 7, 10, 0, tzinfo=tz_of(T))
    S.EVENTS.clear()
    S.tick(loc)
    S.tick(loc + timedelta(minutes=5))
    assert [k for k, _ in S.EVENTS].count("helpdesk_day") == 1
    assert S.send_morning(T)["text"].startswith("IT:")
    assert S.register_file(T)["file"]["name"].endswith(".xlsx")


def test_tools_and_api(hd):
    S = hd
    from app.agent import helpdesk_tools as H
    from app.agent.tools import Ctx, ToolError
    assert {t["name"] for t in H.HELPDESK_TOOLS} == set(H.HELPDESK_HANDLERS) == set(H.HELPDESK_LABELS)
    enum = H.HELPDESK_TOOLS[0]["input_schema"]["properties"]["action"]["enum"]
    assert not any(x in enum for x in ("approve", "decide"))                 # the tool can only make the card
    ctx = conv_ctx()
    run = lambda c, tool, **a: asyncio.run(H.HELPDESK_HANDLERS[tool](c, **a))      # noqa: E731
    staff = Ctx(T, ctx.conversation_id, actor="staff:tm_1")
    r = run(staff, "helpdesk", action="new", text="scanner se scan nahi ho raha", person="Asha")
    assert r["ticket"]["category"] == "scanner" and r["ticket"]["raised_by"]
    with pytest.raises(ToolError):
        run(staff, "helpdesk", action="settings", entity="company")
    with pytest.raises(ToolError):
        run(Ctx(T, ctx.conversation_id, actor="customer:wa:9198"), "helpdesk", action="new", text="printer")
    ch = run(ctx, "helpdesk", action="change", ticket=r["ticket"]["number"], what="Router ka DNS 1.1.1.1 karna", kind="network")
    assert ch["needs_tap"] and ch["change"]["status"] == "waiting"
    assert run(ctx, "helpdesk_dekho", what="day")["waiting_haan"]
    assert run(ctx, "helpdesk_dekho", what="playbook", category="tally")["steps"]
    assert run(ctx, "helpdesk_dekho", what="rules")["cert_in"]["hours"] == 6
    with pytest.raises(ToolError):
        run(ctx, "helpdesk", action="change_done", change=ch["change"]["id"], ok=True)           # not approved yet
    from app.helpdesk.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: T))
    with TestClient(app) as cl:
        o = cl.get("/api/helpdesk").json()
        assert o["tickets"] and o["playbooks"] and o["changes"]
        cid, h = ch["change"]["id"], ch["change"]["hash"]
        assert cl.post(f"/api/helpdesk/changes/{cid}/decide", json={}).status_code == 400
        assert cl.post(f"/api/helpdesk/changes/{cid}/decide", json={"yes": True, "hash": "x"}).status_code == 400
        assert cl.post(f"/api/helpdesk/changes/{cid}/decide", json={"yes": True, "hash": h}).json()["change"]["status"] == "approved"
        d = cl.post(f"/api/helpdesk/changes/{cid}/done", json={"ok": True})
        assert d.status_code == 200 and S.get_ticket(T, r["ticket"]["id"])["status"] == "resolved"
        nt = cl.post("/api/helpdesk/tickets", json={"text": "Excel file nahi khul rahi"}).json()
        assert nt["ticket"]["category"] == "office_apps"
        tid = nt["ticket"]["id"]
        assert cl.post(f"/api/helpdesk/tickets/{tid}/step", json={"result": "not_fixed"}).status_code == 200
        assert cl.patch(f"/api/helpdesk/tickets/{tid}", json={"error": "file is corrupt", "urgency": "high"}).json()["ticket"]["priority"] == "P3"
        assert cl.post("/api/helpdesk/assets", json={"name": "Tally server", "kind": "server", "bought": "2021-04-01"}).status_code == 200
        assert cl.post("/api/helpdesk/assets", json={"kind": "pc"}).status_code == 400
        assert len(cl.get("/api/helpdesk/assets").json()["assets"]) == 1
        assert cl.post("/api/helpdesk/vendors", json={"name": "Jio Fiber", "kind": "isp", "phone": "1800 896 9999"}).status_code == 400
        assert cl.post("/api/helpdesk/vendors", json={"name": "Jio Fiber", "kind": "isp", "email": "care@jio.example"}).status_code == 200
        p = cl.post("/api/helpdesk/phish", json={"text": "Win iPhone, click http://192.168.4.5/win", "clicked": True}).json()
        assert any(f["id"] == "ip_link" for f in p["incident"]["analysis"]["flags"])
        assert cl.post(f"/api/helpdesk/incidents/{p['incident']['id']}/reported", json={"ref": "x"}).status_code == 200
        assert cl.get("/api/helpdesk/tickets/HD-9999").status_code == 400
        assert cl.put("/api/helpdesk/settings", json={"entity": "alien"}).status_code == 400
        assert cl.post(f"/api/helpdesk/tickets/{tid}/escalate", json={}).json()["ticket"]["status"] == "waiting_tech"
        assert cl.post("/api/helpdesk/register").status_code == 200
