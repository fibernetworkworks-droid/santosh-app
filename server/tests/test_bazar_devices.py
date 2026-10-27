"""Home devices ("Ghar") in Santosh: IR/HID encoders, chat tools via service.run, phone results, safety limits,
appliance clouds (offline sandbox), alerts and per-tenant isolation."""
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.bazar.connectors import device_hid as hid
from app.bazar.connectors import device_ir as ir
from app.bazar.connectors import device_sandbox
from app.bazar.connectors.base import ToolError
from app.bazar.connectors.device_cloud import HomeConnect, LgThinq, SmartThings, Token


@pytest.fixture
def bz(env, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-0123456789-abcdefghij")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://santosh.example.in")
    monkeypatch.setenv("BAZAR_ENV", "dev")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.bazar import config as bzc, security
    bzc.reset_settings()
    security._vault = None
    from app.bazar import service
    service.set_executors(None)
    device_sandbox.reset()
    from app.db import Conversation, session
    with session() as s:
        c = Conversation(tenant_id="default")
        s.add(c)
        s.flush()
        conv = c.id
    yield {"svc": service, "conv": conv}
    device_sandbox.reset()
    bzc.reset_settings()
    security._vault = None
    service.set_executors(None)


@pytest.fixture
def api(bz):
    from fastapi.testclient import TestClient
    from app import main
    return TestClient(main.app)


def _events(conv, kind):
    from app.db import Event, session
    with session() as s:
        return [e.payload for e in s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind == kind)
                                             .order_by(Event.id)).all()]


def _decode_bits(pattern, start, nbits, one, zero):
    v = 0
    for i in range(nbits):
        space = pattern[start + 2 * i + 1]
        v = (v << 1) | (1 if abs(space - one) < abs(space - zero) else 0)
    return v


# ------------------------------------------------------------------ encoders (pure)
def test_ir_codes_and_limits():
    assert ir.lg_code(ir.AcState(False)) == 0x88C0051
    assert ir.lg_code(ir.AcState(True, "cool", 25, "high")) == 0x8800A4E
    sig = ir.encode("lg_ac", ir.AcState(True, "cool", 24, "auto"))
    assert sig.carrier_hz == 38000 and sig.pattern[:2] == [8500, 4250]
    assert _decode_bits(sig.pattern, 2, 28, 1600, 550) == int(sig.code_hex, 16)
    assert ir.coolix_code(ir.AcState(True, "cool", 24, "auto")) == 0xB2BF40
    assert ir.clamp_temp(16) == (20, True) and ir.clamp_temp(31) == (28, True) and ir.clamp_temp(24) == (24, False)


def test_hid_mapping():
    assert hid.key_op("vol_up", 3) == {"op": "consumer", "usage": 0xE9, "repeat": 3, "label": "VOL_UP"}
    assert hid.key_op("HOME")["usage"] == 0x223
    assert hid.key_op("vol_down", 99)["repeat"] == 30
    assert hid.open_app_ops("youtube")[0]["op"] == "dial_launch"
    with pytest.raises(ValueError):
        hid.key_op("SELF_DESTRUCT")


SET = SimpleNamespace(smartthings_client_id="cid", smartthings_client_secret="sec", home_connect_client_id="hid",
                      home_connect_client_secret="hsec", lg_thinq_client_id="santosh-test", lg_thinq_country="IN",
                      lg_thinq_region="kic")


def test_cloud_clients_against_sandbox():
    device_sandbox.reset()
    saved = []
    st = SmartThings(Token("expired-token", "r1"), transport=device_sandbox.transport(), on_token=saved.append, settings=SET)
    assert {d["name"] for d in st.list_devices()} >= {"Samsung Fridge", "Samsung Washer"} and saved
    lg = LgThinq(Token("pat-abc"), transport=device_sandbox.transport(), settings=SET)
    assert {d["name"]: d["kind"] for d in lg.list_devices()} == {"LG Hall AC": "ac", "LG Fridge": "fridge"}
    hc = HomeConnect(Token("hc"), transport=device_sandbox.transport(), settings=SET)
    with pytest.raises(ToolError):
        hc.set_ac("BOSCH-WAT-1", True)   # read-only


# ------------------------------------------------------------------ chat path (service.run)
def _ac(svc, tenant="default", name="Bedroom AC", brand="Midea", protocol="coolix"):
    from app.bazar import devices
    d = devices.add_device(tenant, "ac", name, "Bedroom", brand)
    devices.ir_confirm(tenant, d["id"], protocol)
    return d


def test_catalog_status_no_device_until_added(bz):
    from app.bazar import devices
    svc, conv = bz["svc"], bz["conv"]
    st = {p["pack_id"]: p["status"] for p in svc.catalog("default")["packs"] if p["executor"] == "device"}
    assert st == {"bluetooth-speaker": "ready", "smart-tv-remote": "no_device", "ac-ir-remote": "no_device",
                  "samsung-smartthings": "no_device", "lg-thinq": "no_device", "bosch-home-connect": "no_device"}
    with pytest.raises(ToolError, match="Ghar"):
        svc.run("default", conv, "ac-ir-remote", "set_ac", {"temp_c": 24})
    d = devices.add_device("default", "ac", "Bedroom AC", brand="LG")
    assert [p["protocol"] for p in d["setup"]["try_protocols"]] == ["lg2_ac", "lg_ac"]
    with pytest.raises(ToolError, match="isn't confirmed"):
        svc.run("default", conv, "ac-ir-remote", "set_ac", {"temp_c": 24})


def test_set_ac_clamps_and_phone_confirm_saves_state(bz, api):
    svc, conv = bz["svc"], bz["conv"]
    _ac(svc)
    out = svc.run("default", conv, "ac-ir-remote", "set_ac", {"temp_c": 16})
    assert "20°C" in out["message"] and "between 20 and 28" in out["message"] and "device_action" not in out
    act = _events(conv, "home_device")[-1]
    assert act["channel"] == "ir" and act["ops"][0]["op"] == "ir" and act["ops"][0]["pattern"]
    assert act["report_to"] == f"/api/bazar/devices/commands/{act['command_id']}/result"
    # phone failed: nothing saved, hint returned
    r = api.post(act["report_to"], json={"ok": False, "error": "no IR emitter"}).json()
    assert r["status"] == "failed" and "IR blaster" in r["hint"]
    devs = {d["name"]: d for d in api.get("/api/bazar/devices").json()["devices"]}
    assert devs["Bedroom AC"]["last_set"]["temp_c"] == 24
    # too hot asked -> 28; phone confirms -> saved
    out = svc.run("default", conv, "ac-ir-remote", "set_ac", {"temp_c": 35})
    assert "28°C" in out["message"]
    act = _events(conv, "home_device")[-1]
    assert api.post(act["report_to"], json={"ok": True}).json()["status"] == "done"
    assert api.post(act["report_to"], json={"ok": False}).json()["status"] == "done"   # reported once
    devs = {d["name"]: d for d in api.get("/api/bazar/devices").json()["devices"]}
    assert devs["Bedroom AC"]["last_set"]["temp_c"] == 28
    # delta is bounded too
    assert "20°C" in svc.run("default", conv, "ac-ir-remote", "set_ac", {"delta": -50})["message"]
    act = _events(conv, "home_device")[-1]
    api.post(act["report_to"], json={"ok": True})
    st = svc.run("default", conv, "ac-ir-remote", "ac_status", {})
    assert st["temp_c"] == 20 and "IR can't read" in st["message"]


def test_unsafe_requests_are_refused(bz):
    svc, conv = bz["svc"], bz["conv"]
    _ac(svc)
    with pytest.raises(ToolError, match="safety"):
        svc.run("default", conv, "ac-ir-remote", "set_ac", {"device": "bathroom geyser", "power": True})
    with pytest.raises(ToolError, match="safety"):
        svc.run("default", conv, "ac-ir-remote", "set_ac", {"device": "fridge", "power": False})
    with pytest.raises(ToolError, match="no tool"):
        svc.run("default", conv, "ac-ir-remote", "start_washer", {})
    assert _events(conv, "home_device") == []


def test_tv_keys_and_speaker_volume_cap(bz):
    from app.bazar import devices
    svc, conv = bz["svc"], bz["conv"]
    devices.add_device("default", "tv", "Hall TV", target={"bt_address": "aa:bb:cc:dd:ee:ff", "ip": "192.168.1.20"})
    out = svc.run("default", conv, "smart-tv-remote", "tv_keys", {"keys": ["VOL_DOWN"], "repeat": 5})
    act = _events(conv, "home_device")[-1]
    assert act["channel"] == "bt_hid" and act["ops"][0]["usage"] == 0xEA and act["ops"][0]["repeat"] == 5
    assert act["target"]["bt_address"] == "AA:BB:CC:DD:EE:FF" and "command" in out["phone"]
    svc.run("default", conv, "smart-tv-remote", "tv_open_app", {"app": "youtube"})
    assert _events(conv, "home_device")[-1]["ops"][0]["op"] == "dial_launch"
    with pytest.raises(ToolError, match="Unknown TV key"):
        svc.run("default", conv, "smart-tv-remote", "tv_keys", {"keys": ["SELF_DESTRUCT"]})
    # speaker works without adding one (phone audio); volume capped at 90
    svc.run("default", conv, "bluetooth-speaker", "volume", {"percent": 100})
    assert _events(conv, "home_device")[-1]["ops"][0] == {"op": "volume_set", "percent": 90, "max_percent": 90}
    devices.add_device("default", "speaker", "JBL", target={"max_percent": 100})
    svc.run("default", conv, "bluetooth-speaker", "volume", {"percent": 95})
    assert _events(conv, "home_device")[-1]["ops"][0]["percent"] == 90
    svc.run("default", conv, "bluetooth-speaker", "media", {"action": "play", "query": "Arijit Singh"})
    assert _events(conv, "home_device")[-1]["ops"] == [{"op": "play_from_search", "query": "Arijit Singh"}]


# ------------------------------------------------------------------ routes
def test_api_ac_onboarding(api):
    d = api.post("/api/bazar/devices", json={"kind": "ac", "name": "Kids room AC", "brand": "LG"}).json()
    assert d["ready"] is False
    t = api.post(f"/api/bazar/devices/{d['id']}/ir-test", json={"protocol": "lg2_ac"}).json()
    assert t["device_action"]["ops"][0]["pattern"][:2] == [3200, 9900]
    assert api.post(f"/api/bazar/devices/{d['id']}/ir-test", json={"protocol": "nope"}).status_code == 400
    ok = api.post(f"/api/bazar/devices/{d['id']}/ir-confirm", json={"protocol": "lg2_ac"}).json()
    assert ok["protocol"] == "lg2_ac" and ok["ready"] is True
    assert api.post("/api/bazar/devices", json={"kind": "tv", "name": "TV", "target": {"ip": "8.8.8.8"}}).status_code == 400
    assert api.post("/api/bazar/devices", json={"kind": "fridge", "name": "F"}).status_code == 422
    assert api.delete(f"/api/bazar/devices/{d['id']}").json() == {"removed": d["id"]}
    assert api.get("/api/bazar/devices").json()["devices"] == []


def test_cloud_link_sync_status_and_alerts(bz, api):
    svc, conv = bz["svc"], bz["conv"]
    start = api.post("/api/bazar/devices/link/smartthings").json()
    assert start["url"].startswith("https://santosh.example.in/bazar/devices/callback/smartthings?code=sandbox")
    state = start["url"].split("state=")[1]
    bad = api.get("/bazar/devices/callback/smartthings", params={"code": "x", "state": state[:-2] + "zz"})
    assert bad.status_code == 400
    page = api.get("/bazar/devices/callback/smartthings", params={"code": "abc", "state": state})
    assert page.status_code == 200 and "Samsung Fridge" in page.text
    assert api.get("/bazar/devices/callback/smartthings", params={"code": "abc", "state": state}).status_code == 400  # single use
    # LG: personal access token entered in the app
    lg = api.post("/api/bazar/devices/link/lg_thinq", json={"token": "my-personal-access-token"}).json()
    assert lg["linked"] == "lg_thinq" and "LG Hall AC" in lg["devices"]
    from app.bazar.db import Connection
    from app.db import session
    with session() as s:
        c = s.scalars(select(Connection).where(Connection.provider == "lg_thinq", Connection.status == "active")).one()
        assert "my-personal-access-token" not in c.token_enc   # encrypted at rest
    links = {x["provider"]: x["linked"] for x in api.get("/api/bazar/devices").json()["links"]}
    assert links == {"smartthings": True, "lg_thinq": True, "home_connect": False}
    st = {p["pack_id"]: p["status"] for p in svc.catalog("default")["packs"] if p["executor"] == "device"}
    assert st["samsung-smartthings"] == "ready" and st["lg-thinq"] == "ready" and st["bosch-home-connect"] == "no_device"
    # status + cloud AC (clamped) through the chat path
    r = svc.run("default", conv, "lg-thinq", "device_status", {"kind": "fridge"})
    assert "Door is OPEN" in r["message"]
    r = svc.run("default", conv, "lg-thinq", "set_ac", {"temp_c": 18})
    assert "20°C" in r["message"]
    assert device_sandbox.STATE["lg_thinq"]["lg-ac-1"]["state"]["temperature"]["targetTemperature"] == 20
    with pytest.raises(ToolError, match="safety"):
        svc.run("default", conv, "samsung-smartthings", "set_ac", {"device": "Samsung Fridge", "power": False})
    assert api.post("/api/bazar/devices/sync").json()["smartthings"]
    first = api.get("/api/bazar/devices/alerts").json()["alerts"]
    assert any(a["kind"] == "fridge_door" and a["device"] == "LG Fridge" for a in first)
    assert not any(a["kind"] == "fridge_door" for a in api.get("/api/bazar/devices/alerts").json()["alerts"])  # once
    assert api.delete("/api/bazar/devices/link/lg_thinq").json() == {"unlinked": True}
    assert "LG Fridge" not in [d["name"] for d in api.get("/api/bazar/devices").json()["devices"]]


def test_alerts_tick_notifies_latest_chat(bz):
    from app.bazar import devices
    devices.link_lg("default", "my-personal-access-token")
    assert devices.alerts_tick() >= 1
    from app.db import Message, session
    with session() as s:
        texts = [m.display for m in s.scalars(select(Message).where(Message.conversation_id == bz["conv"])).all()]
    assert any("LG Fridge door is open" in t for t in texts)
    assert devices.alerts_tick() == 0


def test_owner_isolation(bz, monkeypatch):
    monkeypatch.setenv("API_KEY", "")
    monkeypatch.setenv("EMAIL_ADDRESS", "owner@gmail.com")
    from app.config import get_settings
    get_settings.cache_clear()
    from fastapi.testclient import TestClient
    from app import accounts, main
    from app.db import User, session
    with session() as s:
        s.add_all([User(id="usr_owner", email="owner@gmail.com"), User(id="usr_kunal", email="kunal@gmail.com")])
    owner = {"Authorization": f"Bearer {accounts.issue_session('usr_owner')}"}
    kunal = {"Authorization": f"Bearer {accounts.issue_session('usr_kunal')}"}
    c = TestClient(main.app)
    d = c.post("/api/bazar/devices", json={"kind": "ac", "name": "Owner AC", "brand": "Midea"}, headers=owner).json()
    assert c.post(f"/api/bazar/devices/{d['id']}/ir-confirm", json={"protocol": "coolix"}, headers=owner).status_code == 200
    assert c.get("/api/bazar/devices", headers=kunal).json()["devices"] == []
    assert c.post(f"/api/bazar/devices/{d['id']}/ir-test", json={"protocol": "coolix"}, headers=kunal).status_code == 404
    assert c.post(f"/api/bazar/devices/{d['id']}/ir-confirm", json={"protocol": "lg_ac"}, headers=kunal).status_code == 404
    assert c.delete(f"/api/bazar/devices/{d['id']}", headers=kunal).status_code == 404
    # owner's command can't be reported by someone else
    t = c.post(f"/api/bazar/devices/{d['id']}/ir-test", json={"protocol": "coolix"}, headers=owner).json()
    cid = t["device_action"]["command_id"]
    assert c.post(f"/api/bazar/devices/commands/{cid}/result", json={"ok": True}, headers=kunal).status_code == 404
    assert c.post(f"/api/bazar/devices/commands/{cid}/result", json={"ok": True}, headers=owner).json()["status"] == "done"
    # Kunal's chat can't reach the owner's AC
    kt = accounts.tenant_of_user("usr_kunal")
    with pytest.raises(ToolError, match="Ghar"):
        bz["svc"].run(kt, bz["conv"], "ac-ir-remote", "set_ac", {"temp_c": 24})
