"""NOC Sahayak (ISP network engineer): alarm parsing (OLT logs / syslog / SNMP trap text / NMS CSV), correlation to the REAL
fault (feeder cut, splitter branch, area power, one customer, OLT down, uplink flap, Rx degradation), plain words + customer
message, tickets with SLA / ETA / MTTR, changes on live equipment only on her tap (hash), the HMAC collector (push, jobs,
results; a fake collector on her network), tick (SLA, ETA, big outage, collector offline, morning), tools + API."""
import asyncio
import base64
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.ispnoc.models  # noqa: F401  (tables for the env fixture's init_db)
from tests.test_life import conv_ctx

T = "default"
IST = timezone(timedelta(hours=5, minutes=30))


@pytest.fixture
def noc(env, monkeypatch):
    from app.ispnoc import service as S
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    S.EVENTS = events
    S._SEEN_SIGS.clear()
    S._LAST_ANALYSE.clear()
    return S


def ts(minutes_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).astimezone(IST).strftime("%Y-%m-%d %H:%M:%S")


def network_csv() -> bytes:
    rows = ["customer,mobile,mac,olt,pon,onu,splitter,route,address,password"]
    for i in range(1, 9):                       # PON 0/1: 8 customers on splitter SPL-A
        rows.append(f"Ramesh {i},98220{10000 + i},AA:BB:CC:00:01:{i:02X},OLT-AKOT,0/1,{i},SPL-A,Akot-Ward5 route,Ward 5 Akot,secret{i}")
    for i in range(1, 7):                       # PON 0/2: 3 on SPL-B, 3 on SPL-C
        rows.append(f"Sita {i},97660{20000 + i},AA:BB:CC:00:02:{i:02X},OLT-AKOT,0/2,{i},{'SPL-B' if i <= 3 else 'SPL-C'},Market road,Market Akot,x")
    for i in range(1, 5):                       # PON 0/3: 4 customers
        rows.append(f"Asha {i},93700{30000 + i},AA:BB:CC:00:03:{i:02X},OLT-AKOT,0/3,{i},SPL-D,Station road,Station Akot,x")
    return ("\n".join(rows) + "\n").encode()


def setup_net(S):
    S.save_settings(T, isp_name="Fiber Network Works", model="franchise", upstream="BSNL", optics="epon_px20+",
                    teams={"field_fibre": [{"name": "Sandeep", "phone": "+91 98500 11122"}], "bsnl": [{"name": "SDE Akot", "phone": "9422012345"}]},
                    bsnl_sla_hours=8)
    S.save_site(T, "Akot POP", address="Khanapur Ves, Akot", lat=21.096, lng=77.058, power="UPS 2 ghante")
    S.save_olt(T, "OLT-AKOT", make="syrotech", tech="epon", ip="10.10.1.2", site="Akot POP", pon_ports=4, uplinks="ge0/9", upstream="BSNL")
    S.save_splitter(T, "SPL-B", olt="OLT-AKOT", pon="0/2", ratio=4, location="Market chowk pole 12", lat=21.1, lng=77.06)
    r = S.import_inventory(T, network_csv(), "network.csv")
    assert r["kind"] == "onts" and r["saved"] == 18 and r["ignored_columns"] == ["password"]
    assert "password" in r["say"].lower()
    return r


def test_rules_parse_optics_commands():
    from app.ispnoc import rules as R
    n = datetime(2026, 10, 23, 12, 0, tzinfo=IST)
    e = R.parse_line("2026-10-23 10:15:01 OLT-AKOT EPON0/1:12 ONU LOS alarm", IST, n)
    assert (e["host"], e["pon"], e["onu"], e["kind"]) == ("OLT-AKOT", "0/1", "12", "los")
    assert R.parse_line("<134>Oct 23 10:15:02 OLT-AKOT %ONU-4: EPON0/1:13 dying gasp", IST, n)["kind"] == "dying_gasp"
    assert R.parse_line("2026-10-23 10:20:00 gpon-onu_1/1/3:12 LOSi raised", IST, n)["pon"] == "1/1/3"
    hw = R.parse_line("FrameID: 0, SlotID: 1, PortID: 3, ONT ID: 12, ONT LOS", IST, n)
    assert (hw["pon"], hw["onu"], hw["kind"]) == ("0/1/3", "12", "los")
    assert R.parse_line("23-10-2026 10:21 PON 2 ONU 7 online", IST, n)["kind"] == "online"
    assert R.parse_line("2026-10-23 10:22:00 OLT-AKOT interface ge0/9 link down", IST, n)["kind"] == "uplink_down"
    assert R.parse_line("2026-10-23 10:23:00 OLT-AKOT ge0/9 link up", IST, n)["kind"] == "uplink_up"
    assert R.parse_line("2026-10-23 10:24:00 OLT-AKOT PON 0/4 LOS", IST, n)["kind"] == "pon_los"
    assert R.parse_line("2026-10-23 10:25:00 OLT-AKOT EPON0/2:3 rx power -29.4 dBm", IST, n)["rx"] == -29.4
    assert R.parse_line("2026-10-23 10:26:00 OLT-AKOT EPON0/2:3 LOS cleared", IST, n)["kind"] == "online"
    assert R.parse_line("trap 1.3.6.1.6.3.1.1.5.3 from 10.10.1.2 ifIndex 25", IST, n)["kind"] == "uplink_down"
    assert R.parse_line("ONU SYTC1234ABCD offline", IST, n)["sn"] == "SYTC1234ABCD"
    assert R.parse_line("hello world", IST, n) is None
    csvt = R.parse_text("Time,Device,PON,ONU,Alarm\n2026-10-23 10:00:00,OLT-AKOT,0/1,3,LOS\n2026-10-23 10:01:00,OLT-AKOT,0/1,4,Dying Gasp\n", IST, n)
    assert csvt["format"] == "csv" and [x["kind"] for x in csvt["events"]] == ["los", "dying_gasp"]
    assert R.rx_band(-20, "gpon_b+") == "good" and R.rx_band(-26, "gpon_b+") == "weak" and R.rx_band(-28.5, "gpon_b+") == "bad"
    assert R.rx_band(-6, "gpon_b+") == "high" and R.rx_band(-25.5, "epon_px20") == "bad"
    b = R.budget("gpon_b+", km=5, splits=[8, 4])
    assert b["loss_db"] == round(5 * 0.35 + 10.5 + 7.3 + 4 * 0.5 + 4 * 0.1, 2) and b["margin_db"] > 0
    hc = R.commands_for("huawei", "reboot_ont", "gpon", "0/1/3", "12")
    assert hc["verified"] and "ont reset 3 12" in hc["commands"]
    sc = R.commands_for("syrotech", "pon_reset", "epon", "0/2")
    assert not sc["verified"] and "no shutdown" in sc["rollback"][2]
    assert R.command_problems(["show onu info", "onu reboot 3"]) == []
    assert R.command_problems(["erase startup-config", "username admin password x"]) and R.command_problems(["copy tftp flash"])
    assert R.scrub("telnet password is admin@123") == "telnet password is [hataya]" and not R.has_secret("Key Road Akot")
    base = datetime(2026, 10, 23, 10, 0, tzinfo=IST)
    assert R.parse_when("2 ghante", base, IST) == base + timedelta(hours=2)
    assert R.parse_when("shaam 6 baje", base, IST).hour == 18 and R.parse_when("kal 11 baje", base, IST).day == 24


def test_feeder_cut_ticket_message_resolve(noc):
    S = noc
    setup_net(S)
    lines = [f"{ts(30 - i * 0.2)} OLT-AKOT EPON0/1:{i} ONU LOS alarm" for i in range(1, 9)]
    lines.append(f"{ts(29)} OLT-AKOT EPON0/2:5 rx power -18.2 dBm")
    r = S.ingest(T, "\n".join(lines))
    assert r["read"] == 9 and len(r["new"]) == 1
    f = r["new"][0]
    assert f["kind"] == "feeder_cut" and f["number"] == "F-0001" and f["n_affected"] == 8 and f["n_total"] == 8
    assert f["confidence"] >= 0.8 and f["confidence_label"] == "pakka jaisa"
    assert "8 / 8" in " ".join(f["reasons"]) and "Akot-Ward5 route" in f["explain"] and f["team"] == "field_fibre"
    assert f["location"]["site"] == "Akot POP" and f["location"]["maps"].startswith("https://www.google.com/maps")
    assert "[samay]" in f["customer_msg"] and "Fiber Network Works" in f["customer_msg"]
    assert f["affected"][0]["phone"].count("X") == 4                       # masked in views
    assert S.EVENTS[-1][0] == "ispnoc_fault"
    assert S.ingest(T, "\n".join(lines))["duplicates"] == 9                 # same paste twice = nothing new
    tk = S.open_ticket(T, "F-0001", eta="2 ghante", note="splicer le jaana")
    t = tk["ticket"]
    assert t["number"] == "N-0001" and t["assignee"] == "Sandeep" and t["wa_link"].startswith("https://wa.me/919850011122")
    assert t["sla_hours"] == 4 and "Ramesh 1" in t["text"] and "Akot POP" in t["text"] and "ETA" in t["text"]
    assert "password" in t["text"].lower() and "Sandeep" in tk["say"]
    assert S.open_ticket(T, "F-0001")["ticket"]["number"] == "N-0001"        # one open ticket per team
    m = S.customer_message(T, "F-0001")
    assert m["count"] == 8 and m["phones"][0] == "9822010001" and "[samay]" not in m["text"] and not m["blanks"]
    up = "\n".join(f"{ts(5)} OLT-AKOT EPON0/1:{i} ONU online" for i in range(1, 9))
    r2 = S.ingest(T, up)
    assert [x["number"] for x in r2["resolved"]] == ["F-0001"] and "Theek hua" in r2["say"]
    tkv = S.tickets(T, "fixed")[0]
    assert tkv["status"] == "fixed" and tkv["mttr_hours"] is not None and tkv["mttr_hours"] < 1
    assert "chalu hai" in S.customer_message(T, "F-0001")["text"]
    rep = S.report(T, 30)
    assert rep["faults"] == 1 and rep["teams"][0]["sla_pct"] == 100 and rep["availability_pct"] < 100


def test_power_splitter_single_and_rx(noc):
    S = noc
    setup_net(S)
    # PON 0/2: splitter SPL-B (ONU 1-3) goes dark with LOS; SPL-C fine. PON 0/1: dying gasp x4 (area power). PON 0/3: one LOS.
    lines = [f"{ts(20)} OLT-AKOT EPON0/2:{i} ONU LOS" for i in (1, 2, 3)]
    lines += [f"{ts(19)} OLT-AKOT EPON0/2:{i} ONU online" for i in (4, 5, 6)]
    lines += [f"{ts(18)} OLT-AKOT EPON0/1:{i} dying gasp" for i in (1, 2, 3, 4)]
    lines += [f"{ts(17)} OLT-AKOT EPON0/3:2 ONU LOS"]
    lines += [f"{ts(16)} OLT-AKOT EPON0/3:{i} ONU online" for i in (1, 3, 4)]
    r = S.ingest(T, "\n".join(lines))
    kinds = {f["kind"]: f for f in r["new"]}
    assert set(kinds) == {"splitter_branch", "area_power", "drop_fibre"}, kinds.keys()
    sp = kinds["splitter_branch"]
    assert sp["target"] == "SPL-B" and sp["n_affected"] == 3 and sp["location"]["splitter_location"] == "Market chowk pole 12"
    ap = kinds["area_power"]
    assert ap["team"] == "electricity" and "bijli" in ap["explain"] and "dying gasp" in " ".join(ap["reasons"])
    df = kinds["drop_fibre"]
    assert df["n_affected"] == 1 and "Asha 2" in df["explain"] and "Asha 2" in df["target"]
    # customer power for one ONT; flapping ONT
    S.ingest(T, f"{ts(10)} OLT-AKOT EPON0/2:4 dying gasp")
    flap = "\n".join(f"{ts(m)} OLT-AKOT EPON0/2:6 deregister\n{ts(m - 1)} OLT-AKOT EPON0/2:6 online" for m in (40, 30, 20))
    r3 = S.ingest(T, flap)
    assert any(f["kind"] == "flap" for f in r3["new"])
    assert any(f["kind"] == "customer_power" for f in S.faults(T))
    # Rx: ONT 0/2:5 normally -18, now -28.1 (EPON PX20+: below -27 bad)
    S.ingest(T, f"{ts(9)} OLT-AKOT EPON0/2:5 rx power -18.0 dBm\n{ts(8)} OLT-AKOT EPON0/2:5 rx power -28.1 dBm")
    rx = [f for f in S.faults(T) if f["kind"] == "rx_bad"]
    assert rx and "-28.1" in " ".join(rx[0]["reasons"]) and "10.1 dB gira" in " ".join(rx[0]["reasons"])
    assert S.optics_check("epon_px20+", 3, [4, 8], rx=-27.5)["gap_db"] > 0
    net = S.network(T)
    assert net["onts"] == 18 and net["olts"][0]["down"] >= 4


def test_olt_down_uplink_flap_pon_degrade(noc):
    S = noc
    setup_net(S)
    S.ingest(T, "\n".join(f"{ts(50)} OLT-AKOT EPON0/1:{i} ONU LOS" for i in range(1, 9)))
    assert S.faults(T)[0]["kind"] == "feeder_cut"
    r = S.ingest(T, f"{ts(45)} OLT-AKOT ping timeout node down\n" + "\n".join(f"{ts(45)} OLT-AKOT EPON0/2:{i} ONU LOS" for i in range(1, 7)))
    od = [f for f in r["new"] if f["kind"] == "olt_down"]
    assert od and od[0]["n_affected"] == 18 and "OLT ka khud ka alarm" in " ".join(od[0]["reasons"])
    assert [f["kind"] for f in S.faults(T)] == ["olt_down"]                 # PON fault folded into the OLT one
    assert S.faults(T, "dismissed")[0]["kind"] == "feeder_cut"
    # SNO note: 18/18 customers > 4 h (pretend time passed)
    real = S.clock
    S.clock = lambda: real() + timedelta(hours=5)
    try:
        v = S.fault_view(T, od[0]["id"])
        assert any("Significant Network Outage" in x for x in v["notes"]) and any("BSNL" in x for x in v["notes"])
    finally:
        S.clock = real
    S.ingest(T, f"{ts(3)} OLT-AKOT node is up recovered\n" + "\n".join(f"{ts(2)} OLT-AKOT EPON0/{p}:{i} online" for p, n in ((1, 8), (2, 6), (3, 4)) for i in range(1, n + 1)))
    assert not S.faults(T)
    # uplink flapping 3x in 30 min (BSNL upstream on a franchise -> BSNL team, her BSNL SLA hours)
    up = "\n".join(f"{ts(m)} OLT-AKOT interface ge0/9 link down\n{ts(m - 1)} OLT-AKOT interface ge0/9 link up" for m in (25, 18, 10))
    fl = [f for f in S.ingest(T, up)["new"] if f["kind"] == "uplink_flap"]
    assert fl and fl[0]["team"] == "bsnl" and fl[0]["sla_hours"] == 8
    tk = S.open_ticket(T, fl[0]["number"], ext_ref="BSNL-DKT-7781")
    assert tk["ticket"]["team"] == "bsnl" and tk["ticket"]["sla_hours"] == 8 and tk["ticket"]["assignee"] == "SDE Akot"
    # whole PON 0/3 loses ~4 dB together = feeder / OLT port, not 4 separate customers
    base_rx = "\n".join(f"{ts(60)} OLT-AKOT EPON0/3:{i} rx power -17.{i} dBm\n{ts(59)} OLT-AKOT EPON0/3:{i} rx power -17.{i} dBm" for i in range(1, 5))
    now_rx = "\n".join(f"{ts(1)} OLT-AKOT EPON0/3:{i} rx power -21.{i} dBm" for i in range(1, 5))
    S.ingest(T, base_rx)
    pd = [f for f in S.ingest(T, now_rx)["new"] if f["kind"] == "pon_degrade"]
    assert pd and pd[0]["n_affected"] == 4 and "4.0 dB" in " ".join(pd[0]["reasons"])


def test_changes_only_on_her_tap(noc):
    S = noc
    setup_net(S)
    ch = S.request_change(T, "reboot_ont", "OLT-AKOT", "0/2", "6", reason="flap")
    c = ch["change"]
    assert ch["needs_tap"] and c["status"] == "waiting" and c["n_affected"] == 1 and not c["verified"] and c["warn"]
    assert c["commands"] and "onu reboot 6" in " ".join(c["commands"]) and S.EVENTS[-1][0] == "ispnoc_change"
    pr = S.request_change(T, "pon_reset", "OLT-AKOT", "0/1")["change"]
    assert pr["n_affected"] == 8 and "SAARE" in pr["risk"] and pr["rollback"]
    with pytest.raises(S.NocError):
        S.decide_change(T, c["id"], True, c["hash"])                       # no tap = no change
    with pytest.raises(S.NocError):
        S.decide_change(T, c["id"], True, "wrong", by_tap=True)
    with pytest.raises(S.NocError):
        S.request_change(T, "custom", "OLT-AKOT", commands=["erase startup-config"])
    with pytest.raises(S.NocError):
        S.request_change(T, "custom", "OLT-AKOT", commands=["username admin password abc123"])
    e = S.edit_change(T, c["id"], ["interface epon 0/2", "onu reboot 6", "exit"])["change"]
    assert e["hash"] != c["hash"]
    with pytest.raises(S.NocError):
        S.decide_change(T, c["id"], True, c["hash"], by_tap=True)          # old card after an edit
    d = S.decide_change(T, c["id"], True, e["hash"], by_tap=True)
    assert d["change"]["status"] == "approved" and d["change"]["via"] == "manual" and "Telnet" in d["change"]["steps"]
    again = S.decide_change(T, c["id"], False, e["hash"], by_tap=True)
    assert again["change"]["status"] == "approved"                          # decided once
    with pytest.raises(S.NocError):
        S.change_done(T, c["id"], True, actor="staff:x")
    assert S.change_done(T, c["id"], True, "ok")["change"]["status"] == "done"
    no = S.decide_change(T, pr["id"], False, pr["hash"], reason="raat ko karenge", by_tap=True)
    assert no["change"]["status"] == "rejected"


def test_collector_hmac_push_jobs(noc):
    S = noc
    setup_net(S)
    from app.ispnoc import collector as C
    from app.ispnoc.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: T))
    with TestClient(app) as cl:
        made = cl.post("/api/ispnoc/collectors", json={"name": "Akot POP box", "site": "Akot POP"}).json()
        cid, secret = made["collector"]["id"], made["secret"]
        assert len(secret) > 30 and secret not in json.dumps(cl.get("/api/ispnoc/collectors").json())
        assert cl.patch(f"/api/ispnoc/collectors/{cid}", json={"olts": ["OLT-AKOT"], "changes_ok": True}).status_code == 200

        def transport(method, path, body, hdrs):
            r = cl.request(method, path, content=body if method != "GET" else None, headers=hdrs)
            return r.status_code, (r.json() if r.content else {})

        cfg = {"server": "http://test", "collector_id": cid, "allow_changes": True,
               "olts": [{"name": "OLT-AKOT", "ip": "10.10.1.2", "ssh": "noc@10.10.1.2", "read_commands": ["show onu info", "reboot olt"]}]}
        fake = C.Collector(cfg, secret, transport)
        ran_cmds = []
        fake.ssh = lambda o, lines, timeout=60: (ran_cmds.append(list(lines)) or "show output\n0/1:1 online rx -19.2 dBm")
        for i in range(1, 9):
            fake.add("OLT-AKOT", f"{ts(15)} OLT-AKOT EPON0/1:{i} ONU LOS")
        res = fake.push_once()
        assert res["ok"] and res["read"] >= 8 and res["new"] == ["F-0001"]
        assert ran_cmds == [["show onu info"]]                                 # 'reboot olt' is not read-only: never pulled
        assert S.collectors(T)[0]["online"]
        # wrong secret / replay / no headers
        body = b'{"batches": []}'
        h = C.headers("wrong", cid, "POST", "/api/ispnoc/collector/push", body)
        assert cl.post("/api/ispnoc/collector/push", content=body, headers=h).status_code == 401
        h = C.headers(secret, cid, "POST", "/api/ispnoc/collector/push", body)
        assert cl.post("/api/ispnoc/collector/push", content=body, headers=h).status_code == 200
        assert cl.post("/api/ispnoc/collector/push", content=body, headers=h).status_code == 401      # replay
        assert cl.post("/api/ispnoc/collector/push", json={}).status_code == 401
        # an approved change goes to the collector; nothing runs before her tap
        assert fake.jobs_once() == 0
        ch = S.request_change(T, "reboot_ont", "OLT-AKOT", "0/1", "3")["change"]
        assert fake.jobs_once() == 0
        d = cl.post(f"/api/ispnoc/changes/{ch['id']}/decide", json={"yes": True, "hash": ch["hash"]}).json()
        assert d["change"]["status"] == "queued" and d["change"]["via"] == "collector"
        ran_cmds.clear()
        assert fake.jobs_once() == 1 and ran_cmds == [ch["commands"]]
        assert S.changes(T)[0]["status"] == "done" and "show output" in S.changes(T)[0]["output"]
        # a tampered job is refused by the collector itself
        job = {"id": "x", "hash": "h", "commands": ["onu reboot 3"], "sig": C.job_sig(secret, "x", "h", ["onu reboot 3"])}
        assert C.verify_job(secret, job) == ""
        assert C.verify_job(secret, {**job, "commands": ["erase flash"]}) == "bad job signature"
        bad = {"id": "y", "hash": "h", "commands": ["write erase"], "sig": C.job_sig(secret, "y", "h", ["write erase"])}
        assert C.verify_job(secret, bad).startswith("forbidden")
        assert "HOOLA_COLLECTOR_SECRET" in cl.get("/api/ispnoc/collector-script").text


def test_tick_alerts_and_morning(noc, monkeypatch):
    S = noc
    setup_net(S)
    S.save_settings(T, morning_time="09:00", sla={"feeder_cut": 1})
    S.ingest(T, "\n".join(f"{ts(10)} OLT-AKOT EPON0/1:{i} ONU LOS" for i in range(1, 9)))
    S.open_ticket(T, "F-0001", eta="30 min")
    col = S.create_collector(T, "Box")
    with S.session() as s:
        c = s.get(S.IspnocCollector, col["collector"]["id"])
        c.last_seen = S.now() - timedelta(minutes=30)
    n0 = datetime.now(timezone.utc)
    S.EVENTS.clear()
    out = S.tick(n0 + timedelta(hours=5))
    says = " ".join(p.get("say", "") for k, p in S.EVENTS if k == "ispnoc_alert")
    assert out["sla"] == 1 and out["eta"] == 1 and out["collectors"] == 1 and out["sno"] >= 1
    assert "SLA" in says and "ETA" in says and "chup" in says and "4 ghante" in says
    S.EVENTS.clear()
    again = S.tick(n0 + timedelta(hours=5, minutes=1))
    assert again["sla"] == again["eta"] == again["collectors"] == 0            # said once
    from app.life import tz_of
    loc = datetime(2030, 1, 7, 9, 30, tzinfo=tz_of(T))
    monkeypatch.setattr(S, "clock", lambda: loc)
    S.EVENTS.clear()
    S.tick(loc)
    S.tick(loc + timedelta(minutes=5))
    assert [k for k, _ in S.EVENTS].count("ispnoc_day") == 1
    assert S.send_morning(T)["text"].startswith("NOC:")


def test_tools_and_api(noc):
    from app.agent import ispnoc_tools as N
    from app.agent.tools import Ctx, ToolError
    assert {t["name"] for t in N.ISPNOC_TOOLS} == set(N.ISPNOC_HANDLERS) == set(N.ISPNOC_LABELS)
    enum = N.NOC_TOOLS[0]["input_schema"]["properties"]["action"]["enum"]
    assert not any(x in enum for x in ("approve", "decide", "collector"))   # the tool can only make the card
    ctx = conv_ctx()
    run = lambda c, tool, **a: asyncio.run(N.NOC_HANDLERS[tool](c, **a))      # noqa: E731
    staff = Ctx(T, ctx.conversation_id, actor="staff:tm_1")
    with pytest.raises(ToolError):
        run(staff, "noc", action="settings", isp_name="X")
    with pytest.raises(ToolError):
        run(Ctx(T, ctx.conversation_id, actor="customer:wa:9198"), "noc", action="alarms", text="LOS")
    with pytest.raises(ToolError):
        run(ctx, "noc", action="note", fault="F-0001", text="olt password is admin123")
    run(ctx, "noc", action="olt", name="OLT-NASHIK", make="vsol", tech="gpon", ip="10.20.0.2")
    run(ctx, "noc", action="ont", olt="OLT-NASHIK", pon="0/1", onu="1", customer="Kiran", phone="9822033344")
    run(ctx, "noc", action="ont", olt="OLT-NASHIK", pon="0/1", onu="2", customer="Meena")
    run(ctx, "noc", action="ont", olt="OLT-NASHIK", pon="0/1", onu="3", customer="Gita")
    r = run(staff, "noc", action="alarms", text=f"{ts(5)} OLT-NASHIK GPON0/1:1 LOSi\n{ts(4)} OLT-NASHIK GPON0/1:2 dying gasp")
    assert r["read"] == 2 and r["new"]
    day = run(ctx, "noc_dekho", what="day")
    assert day["faults"] and all("X" in a["phone"] for f in day["faults"] for a in f["affected"] if a["phone"])
    los = next(f for f in day["faults"] if f["kind"] == "drop_fibre")
    t = run(staff, "noc", action="ticket", fault=los["number"], team="field_fibre", assignee="Raju", phone="9850099988")
    assert t["ticket"]["assignee"] == "Raju"
    msg = run(ctx, "noc", action="message", fault=los["number"])
    assert "phones" not in msg and msg["count"] == 1
    ch = run(ctx, "noc", action="change", action_kind="reboot_ont", olt="OLT-NASHIK", pon="0/1", onu="1")
    assert ch["needs_tap"] and ch["change"]["status"] == "waiting"
    assert run(ctx, "noc_dekho", what="changes", status="waiting")["changes"]
    assert run(ctx, "noc_dekho", what="rules")["facts"]["trai_qos_2024"]
    assert run(ctx, "noc_dekho", what="customer", q="kiran")["onts"][0]["phone"] == "98XXXX3344"
    assert run(ctx, "noc_dekho", what="optics", **{"class": "gpon_b+", "km": 4, "splits": [8, 8]})["margin_db"] > 0
    from app.ispnoc.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: T))
    with TestClient(app) as cl:
        o = cl.get("/api/ispnoc").json()
        assert o["faults"] and o["network"]["olts"] and o["sources"]
        cid, h = ch["change"]["id"], ch["change"]["hash"]
        assert cl.post(f"/api/ispnoc/changes/{cid}/decide", json={}).status_code == 400
        assert cl.post(f"/api/ispnoc/changes/{cid}/decide", json={"yes": True, "hash": "x"}).status_code == 400
        assert cl.post(f"/api/ispnoc/changes/{cid}/decide", json={"yes": True, "hash": h}).json()["change"]["status"] == "approved"
        fid = los["id"]
        full = cl.get(f"/api/ispnoc/faults/{fid}").json()
        assert full["affected"][0]["phone"] == "9822033344"                # her own app sees the full number
        assert cl.get(f"/api/ispnoc/faults/{fid}/message").json()["phones"] == ["9822033344"]
        tid = t["ticket"]["id"]
        assert cl.patch(f"/api/ispnoc/tickets/{tid}", json={"status": "on_site", "eta": "1 ghanta"}).json()["ticket"]["status"] == "on_site"
        assert cl.patch(f"/api/ispnoc/tickets/{tid}", json={"status": "flying"}).status_code == 400
        assert cl.post(f"/api/ispnoc/faults/{fid}/resolve", json={"note": "patch cord badla"}).json()["fault"]["status"] == "resolved"
        imp = cl.post("/api/ispnoc/import", json={"name": "olts.csv", "data_b64": base64.b64encode(b"name,make,ip,tech\nOLT-PUNE,cdata,10.30.0.2,gpon\n").decode()})
        assert imp.json()["kind"] == "olts" and imp.json()["saved"] == 1
        assert cl.post("/api/ispnoc/olts", json={"name": "OLT-X", "make": "nokia-alien"}).status_code == 400
        assert cl.put("/api/ispnoc/settings", json={"model": "alien"}).status_code == 400
        assert cl.put("/api/ispnoc/settings", json={"snmp_community": "public"}).status_code == 400
        a = cl.post("/api/ispnoc/alarms", json={"data_b64": base64.b64encode(f"{ts(2)} OLT-PUNE GPON0/1:9 LOS".encode()).decode(), "olt": "OLT-PUNE"})
        assert a.status_code == 200 and a.json()["read"] == 1
        assert cl.post("/api/ispnoc/alarms", json={"text": "x LOS", "olt": "NOPE"}).status_code == 400
        assert cl.get("/api/ispnoc/report?days=7").json()["days"] == 7
        assert cl.post("/api/ispnoc/optics", json={"class": "gpon_c+", "km": 10, "splits": [32]}).json()["band"] in ("good", "weak")
