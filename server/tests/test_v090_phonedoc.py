"""v0.90 Phone Doctor: her words -> issue, the phone's own check -> findings, fix steps ordered by what the phone says and
what fixed it for others, one step at a time with the right settings screen, verification, escalation to a shop /
operator / official help (CEIR, 1930), a repair job in her own Mobile Dukaan, and the hard lines (IMEI, locks)."""
import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import Event, session
from tests.test_life import conv_ctx

T = "default"
SLOW_PHONE = {"brand": "xiaomi", "model": "Redmi Note 12", "storage_used_pct": 96, "storage_free_gb": 2.1, "uptime_hours": 300,
              "battery_pct": 54, "battery_temp_c": 33.0, "battery_health": "good", "operator": "Jio", "signal_level": 3,
              "auto_time": True, "dnd": False, "ringer": "normal", "ring_volume_pct": 80, "media_volume_pct": 60,
              "security_patch": "2023-01-05", "top_apps": [{"package": "com.instagram.android", "label": "Instagram", "minutes": 190}],
              "password": "1234", "contacts": ["x"]}


def _events(kind):
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.kind == kind).order_by(Event.id)).all()]


def test_detect_and_findings():
    from app.phonedoc.playbooks import ISSUES, SETTING_LABEL, detect, findings
    assert detect("mera phone bahut hang hota hai")[0] == "slow"
    assert detect("battery jaldi khatam ho jati hai")[0] == "battery_drain"
    assert detect("phone chori ho gaya")[0] == "lost_stolen"
    assert detect("OTP nahi aa raha bank ka")[0] == "otp_not_coming"
    assert detect("paise kat gaye, anydesk dala tha")[0] == "hacked_fraud"
    assert detect("kuch ajeeb sa") == ["other"]
    for iid, spec in ISSUES.items():                      # every screen a step opens exists on the phone side
        assert spec["steps"] and spec["escalate"] in ("repair", "operator", "official"), iid
        for st in spec["steps"]:
            assert not st.get("setting") or st["setting"] in SETTING_LABEL, (iid, st["id"])
    f = {x["id"]: x for x in findings(SLOW_PHONE)}
    assert f["storage"]["level"] == "bad" and "slow" in f["storage"]["issues"]
    assert "uptime" in f and "patch" in f and "top_app" in f and "temp" not in f
    hot = {x["id"] for x in findings({"battery_temp_c": 47.5, "thermal_status": 4, "airplane": True, "sim_state": "absent",
                                       "dnd": True, "plugged": "usb", "charging_status": "charging", "current_ma": 150})}
    assert {"temp", "thermal", "airplane", "sim", "dnd", "slow_charge"} <= hot
    assert findings({}) == []


def test_case_end_to_end_ordered_by_phone_check_learns(env):
    from app.phonedoc import service as P
    P.save_snapshot(T, SLOW_PHONE)
    snap, _ = P.latest_snapshot(T)
    assert "password" not in snap and "contacts" not in snap            # only the phone's own state is kept
    r = P.start(T, "phone bahut slow hai, hang hota hai")
    c = r["case"]
    assert r["started"] and c["issue"] == "slow" and c["device"] == "Xiaomi Redmi Note 12"
    ids = [s["id"] for s in c["steps"]]
    assert ids[:2] in (["restart", "storage"], ["storage", "restart"])     # the phone said: full + not restarted for 12 days
    assert ids[-1] == "factory_reset" and c["steps"][-1]["careful"]       # data loss always last
    heavy = next(s for s in c["steps"] if s["id"] == "heavy_app")
    assert heavy["pkg"] == "com.instagram.android" and "Instagram" in heavy["title"]
    assert "Storage 96%" in r["say"] and "Step 1/" in r["say"]
    r = P.step(T, c["id"], result="nahi")
    assert r["case"]["step_no"] == 2 and r["case"]["status"] == "open"
    r = P.step(T, c["id"], result="fixed")
    assert r["resolved"] and r["case"]["fixed_by"] == ids[1]
    # learning: that step now wins once seen enough
    for _ in range(4):
        cid = P.start(T, "phone slow hai")["case"]["id"]
        P.step(T, cid, step_id="update_apps", result="fixed")
    st = {x["step"]: x for x in P.learned("slow")}
    assert st["update_apps"]["fixed"] == 4
    P.save_snapshot(T, {"storage_used_pct": 40, "uptime_hours": 2, "brand": "xiaomi", "model": "Redmi Note 12"})
    order = [s["id"] for s in P.start(T, "phone slow hai")["case"]["steps"]]
    assert order[0] == "update_apps" and order.index("storage") > order.index("heavy_app")   # storage fine now -> later
    assert P.cases(T, "resolved")


def test_steps_run_out_escalate_and_recheck(env):
    from app.phonedoc import service as P
    P.save_snapshot(T, {"airplane": True, "sim_state": "ready", "operator": "Airtel", "brand": "samsung", "model": "A14"})
    c = P.start(T, "network nahi aa raha")["case"]
    assert c["issue"] == "no_network" and c["steps"][0]["id"] == "airplane_toggle"
    P.save_snapshot(T, {"airplane": False, "sim_state": "ready", "operator": "Airtel", "signal_level": 3})
    rc = P.recheck(T, c["id"])
    assert any("Airplane" in g for g in rc["fixed_now"])
    out = None
    for _ in c["steps"]:
        out = P.step(T, c["id"], result="not_fixed")
    assert out["case"]["status"] == "escalated" and out["escalation"]["kind"] == "operator"
    assert any("Airtel" in n for n in out["escalation"]["notes"]) and any("198" in n for n in out["escalation"]["notes"])
    with pytest.raises(P.PhoneDocError):
        P.step(T, "nope", result="fixed")


def test_lost_fraud_lock_imei_lines(env):
    from app.phonedoc import service as P
    r = P.start(T, "mera phone chori ho gaya")
    assert r["case"]["steps"][0]["id"] == "block_sim"                     # urgent order is never reshuffled
    e = P.escalate(T, r["case"]["id"])["escalation"]
    assert e["kind"] == "official" and any("ceir.sancharsaathi.gov.in" in l["url"] for l in e["links"])
    f = P.start(T, "paise kat gaye fraud hua")
    assert f["case"]["steps"][0]["id"] == "money_1930"
    fe = P.escalate(T, f["case"]["id"])["escalation"]
    assert any("1930" in n for n in fe["notes"]) and any("cybercrime.gov.in" in l["url"] for l in fe["links"])
    lk = P.start(T, "pattern bhool gaya, lock tod do")
    assert lk["case"]["issue"] == "forgot_lock" and all("bypass" not in s["how"].lower() for s in lk["case"]["steps"])
    no = P.start(T, "IMEI change karna hai")
    assert no["started"] is False and "kanoonan" in no["say"]


def test_customer_phone_makes_mshop_job(env):
    from app.mshop import service as M
    from app.phonedoc import service as P
    M.save_settings(T, shop_name="Meghana Mobile")
    P.save_snapshot(T, {"storage_used_pct": 99, "brand": "x", "model": "y"})          # HER phone: must not leak into a customer case
    c = P.start(T, "charge nahi hota", for_whom="Suresh", device="Vivo Y21")["case"]
    assert c["findings"] == [] and c["device"] == "Vivo Y21"
    e = P.escalate(T, c["id"], make_job=True, phone="9822012345")
    assert e["case"]["mshop_job"] and any("job M-" in n for n in e["escalation"]["notes"])
    job = M.get_job(T, e["case"]["mshop_job"])
    assert job["customer"]["name"] == "Suresh" and job["faults"][0]["id"] == "charging_port"


def test_tool_events_api(env):
    from app import main, voice
    from app.agent.tools import HANDLERS, TOOLS
    from app.employee import roles
    from app.phonedoc import service as P
    assert any(t["name"] == "phone_doctor" for t in TOOLS) and "phone_doctor" in voice.VOICE_TOOL_NAMES
    assert roles.duty_of("phone_doctor") == "mobile_repair"
    ctx = conv_ctx()
    P.save_snapshot(T, {"battery_temp_c": 46.0, "brand": "oppo", "model": "A78"})
    out = asyncio.run(HANDLERS["phone_doctor"](ctx, action="start", text="phone bahut garam ho raha hai"))
    assert out["case"]["issue"] == "heating" and "46" in out["say"]
    opened = _events("phonedoc_open")
    assert opened == [] or opened[-1]["key"] in ("", "app_info", "apps")      # step 1 (cool down) has no screen
    out = asyncio.run(HANDLERS["phone_doctor"](ctx, action="step", case=out["case"]["id"], result="not_fixed"))
    assert out["case"]["step_no"] == 2
    asyncio.run(HANDLERS["phone_doctor"](ctx, action="open", setting="battery_usage"))
    assert _events("phonedoc_open")[-1]["key"] == "battery_usage"
    with TestClient(main.app) as cl:
        assert "phone_doctor" in cl.get("/healthz").json()["features"]
        assert len(cl.get("/api/phonedoc/issues").json()["issues"]) >= 20
        assert cl.post("/api/phonedoc/check", json={"snapshot": {"dnd": True, "ringer": "silent"}}).json()["findings"]
        c = cl.post("/api/phonedoc/cases", json={"text": "call aati hai par ring nahi bajti"}).json()
        assert c["case"]["issue"] == "calls_not_ringing" and c["case"]["steps"][0]["id"] in ("dnd_off", "ring_volume")
        cid = c["case"]["id"]
        assert cl.post(f"/api/phonedoc/cases/{cid}/step", json={"result": "fixed"}).json()["resolved"]
        assert cl.get(f"/api/phonedoc/cases/{cid}").json()["status"] == "resolved"
        assert cl.get("/api/phonedoc/cases").json()["cases"]
        assert cl.post("/api/phonedoc/cases/nope/step", json={"result": "fixed"}).status_code == 400
        assert cl.post(f"/api/phonedoc/cases/{cid}/bogus", json={}).status_code == 404
