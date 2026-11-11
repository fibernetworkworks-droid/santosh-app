"""v0.479.0 HOOLA SMART HOME - ghar ka control, Home Assistant ke official REST API se (W1 of the Platforms plan).

What this suite pins:
(1) REGISTRY: the 5 home_* tools in the agent's table + handlers + Hinglish labels; the family router
    admits them on "ghar ki light band karo" and keeps them off "hello".
(2) THE HOME GATE: home_control default OFF - home_on / home_off refuse with the bake-then-flip line
    (PC se alag switch), home_link reports the gate state honestly, reads stay gate-free.
(3) PRIVACY: the HA token lives in env only; no tool result ever carries it - home_link shows a masked
    preview; without env every read/control answers with the setup guide, never an error crash.
(4) THE FROZEN-BRIEF GUARDS: fridge / washing machine / geyser READ-ONLY (refused by name, even as a
    switch.* entity); AC temperature clamped 20-28 (24 goes, 19 and 32 do not, HVAC mode respected);
    media volume clamped at 90 %; non-controllable domains (sensor/camera/vacuum) refused.
(5) LOCKS CONFIRM-ONLY, NEVER AUTONOMOUS: without confirm=true refused; in a routine turn (actor=
    "routine") refused even WITH confirm=true; a confirmed owner lock/unlock passes and is audited.
(6) THE REST CLIENT: states / state_one / switch against a fake HA (httpx.MockTransport) - domain-native
    services (cover open/close, scene turn_on, button press), the settle re-read, honest failure lines.
(7) AUDIT: every attempt (success or refusal) lands in home_audit; recent_audit reads it back.
(8) VERSION: APP_VERSION 0.479.0, pubspec 0.542.0+565.
"""
import asyncio

import httpx
import pytest

from app import home
from app.agent import admit, tools as agent_tools
from app.agent.home_tools import HOME_HANDLERS, HOME_LABELS, HOME_TOOLS

T = "default"
CONV = "conv_home"


@pytest.fixture()
def hm(env, monkeypatch):
    """Home link ON via env + settings cache cleared; gate OFF (default) unless a test flips it."""
    monkeypatch.setenv("HOME_ASSISTANT_URL", "http://ha.test:8123")
    monkeypatch.setenv("HOME_ASSISTANT_TOKEN", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9-testtoken-value")
    monkeypatch.setenv("HOME_CONTROL", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    yield monkeypatch
    get_settings.cache_clear()


def _ctx(actor="owner"):
    return type("C", (), {"tenant_id": T, "conversation_id": CONV, "actor": actor, "place": ""})()


class FakeHA:
    """A tiny Home Assistant: entity states flip when the right service is called."""

    def __init__(self):
        self.states = {
            "light.hall": {"state": "on", "attributes": {"friendly_name": "Hall Light", "brightness": 200}},
            "light.bedi": {"state": "off", "attributes": {"friendly_name": "Bedroom Light"}},
            "switch.fridge_plug": {"state": "on", "attributes": {"friendly_name": "Fridge Plug"}},
            "switch.geyser_bathroom": {"state": "off", "attributes": {"friendly_name": "Geyser Bathroom"}},
            "fan.hall": {"state": "off", "attributes": {"friendly_name": "Hall Fan"}},
            "cover.hall_window": {"state": "closed", "attributes": {"friendly_name": "Hall Curtain"}},
            "media_player.tv": {"state": "playing", "attributes": {"friendly_name": "TV", "volume_level": 0.4}},
            "climate.ac_hall": {"state": "off", "attributes": {"friendly_name": "Hall AC"}},
            "scene.movie_night": {"state": "scening", "attributes": {"friendly_name": "Movie Night"}},
            "button.restart_hub": {"state": "unknown", "attributes": {"friendly_name": "Restart Hub"}},
            "lock.main_door": {"state": "locked", "attributes": {"friendly_name": "Main Door"}},
            "sensor.hall_temp": {"state": "27.4", "attributes": {"friendly_name": "Hall Temp", "unit_of_measurement": "°C"}},
            "camera.gate": {"state": "idle", "attributes": {"friendly_name": "Gate Camera"}},
        }
        self.calls: list[str] = []

    def handler(self, req: httpx.Request) -> httpx.Response:
        path = req.url.path
        if path == "/api/":
            return httpx.Response(200, json={"message": "API running."})
        if path == "/api/states" and req.method == "GET":
            return httpx.Response(200, json=[{"entity_id": k, "state": v["state"], "attributes": v["attributes"]}
                                             for k, v in self.states.items()])
        if path.startswith("/api/states/") and req.method == "GET":
            eid = path.rsplit("/", 1)[1]
            if eid in self.states:
                return httpx.Response(200, json={"entity_id": eid, "state": self.states[eid]["state"],
                                                 "attributes": self.states[eid]["attributes"]})
            return httpx.Response(404, json={"message": "Entity not found."})
        if path.startswith("/api/services/") and req.method == "POST":
            svc = path.rsplit("/api/services/", 1)[1]
            body = req.read() and __import__("json").loads(req.content or b"{}")
            eid = (body or {}).get("entity_id", "")
            dom = eid.split(".", 1)[0] if eid in self.states else ""
            self.calls.append(f"{svc} {eid} {body if body else ''}")
            if dom == "light" and svc == "light/turn_on":
                self.states[eid]["state"] = "on"
                if (body or {}).get("brightness"):
                    self.states[eid]["attributes"]["brightness"] = body["brightness"]
                return httpx.Response(200, json=[])
            if dom == "light" and svc == "light/turn_off":
                self.states[eid]["state"] = "off"
                return httpx.Response(200, json=[])
            if dom in ("fan", "switch", "media_player", "input_boolean", "humidifier") and \
                    svc.endswith("turn_on"):
                self.states[eid]["state"] = "on"
                if svc == "media_player/turn_on" or "volume_level" in (body or {}):
                    pass
                if "volume_level" in (body or {}):
                    self.states[eid]["attributes"]["volume_level"] = body["volume_level"]
                return httpx.Response(200, json=[])
            if dom in ("fan", "switch", "media_player") and svc.endswith("turn_off"):
                self.states[eid]["state"] = "off"
                return httpx.Response(200, json=[])
            if dom == "cover" and svc == "cover/open_cover":
                self.states[eid]["state"] = "open"
                return httpx.Response(200, json=[])
            if dom == "cover" and svc == "cover/close_cover":
                self.states[eid]["state"] = "closed"
                return httpx.Response(200, json=[])
            if dom == "climate" and svc == "climate/set_temperature":
                self.states[eid]["attributes"]["temperature"] = body.get("temperature")
                self.states[eid]["state"] = "cool"
                return httpx.Response(200, json=[])
            if dom == "climate" and svc == "climate/set_hvac_mode":
                self.states[eid]["state"] = body.get("hvac_mode", "off")
                return httpx.Response(200, json=[])
            if dom in ("scene", "script") and svc.endswith("turn_on"):
                return httpx.Response(200, json=[])
            if dom == "button" and svc == "button/press":
                return httpx.Response(200, json=[])
            if dom == "lock" and svc in ("lock/lock", "lock/unlock"):
                self.states[eid]["state"] = "locked" if svc == "lock/lock" else "unlocked"
                return httpx.Response(200, json=[])
            return httpx.Response(400, json={"message": f"bad service {svc}"})
        return httpx.Response(404, json={"message": "not found"})


@pytest.fixture()
def fakeha(hm, monkeypatch):
    ha = FakeHA()
    real_client = httpx.AsyncClient
    monkeypatch.setattr(home.httpx, "AsyncClient",
                        lambda **k: real_client(transport=httpx.MockTransport(ha.handler), **k))
    return ha


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


# ---------------------------------------------------------------- (1) registry

def test_five_tools_registered():
    names = {t["name"] for t in agent_tools.TOOLS}
    for n in ("home_link", "home_devices", "home_on", "home_off", "home_state"):
        assert n in names
        assert n in agent_tools.HANDLERS
        assert n in agent_tools.TOOL_LABELS          # the Hinglish label
    assert set(HOME_HANDLERS) == {n for n in ("home_link", "home_devices", "home_on", "home_off", "home_state")}
    assert len(HOME_TOOLS) == 5


def test_family_router_admits_home_words():
    hit = admit.route("ghar ki light band kar do")
    assert "home" in hit, hit
    miss = admit.route("hello kaise ho")
    assert "home" not in miss, miss


def test_voice_declares_home_tools_v0491():
    """v0.479 kept Ghar voice-less (test_voice_never_declares_home_tools); v0.491 EQUAL POWER declares all five on a
    call. The real-world guard is unchanged: the HOME_CONTROL gate below still refuses controls when it is off, and
    the persona carries the Ghar safety line (AC 20-28, speaker <=90, geyser / fridge / washer never)."""
    from app import voice
    for n in ("home_link", "home_devices", "home_on", "home_off", "home_state"):
        assert n in voice.VOICE_TOOL_NAMES
        assert not voice.via_kaam(n), f"{n} must stay directly callable on a call"
    assert "geyser / fridge / washer never" in voice.PERSONA


# ---------------------------------------------------------------- (2) the HOME gate

def test_gate_off_refuses_controls(hm):
    monkey = hm
    monkey.setenv("HOME_CONTROL", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    with pytest.raises(Exception) as e:
        _run(HOME_HANDLERS["home_on"](_ctx(), entity="light.hall"))
    assert "home_control" in str(e.value).lower() or "HOME_CONTROL=1" in str(e.value)
    with pytest.raises(Exception):
        _run(HOME_HANDLERS["home_off"](_ctx(), entity="light.hall"))
    # the audit row for the gate refusal exists
    out = home.recent_audit(T, 5)
    assert any("gate off" in (r.get("detail") or "") for r in out["entries"])


def test_gate_off_leaves_reads_open(hm):
    monkey = hm
    monkey.setenv("HOME_CONTROL", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    st = _run(HOME_HANDLERS["home_link"](_ctx()))
    assert st["gate_on"] is False and st["linked"] is True
    assert "HOME_CONTROL=1" in st["say"]


def test_link_without_env_gives_the_guide(env):
    from app.config import get_settings
    get_settings.cache_clear()
    st = _run(HOME_HANDLERS["home_link"](_ctx()))
    assert st["linked"] is False and "Long-lived access tokens" in st["how"]
    with pytest.raises(Exception):
        _run(HOME_HANDLERS["home_devices"](_ctx()))


# ---------------------------------------------------------------- (3) privacy

def test_token_never_returns_to_model(fakeha):
    from app.config import get_settings
    tok = get_settings().home_assistant_token
    assert tok
    st = home.link_status()
    blob = __import__("json").dumps(st)
    assert tok not in blob
    assert st["linked"] is True and "…" in st["token_masked"]
    out = _run(HOME_HANDLERS["home_link"](_ctx()))
    assert tok not in __import__("json").dumps(out)
    dev = _run(HOME_HANDLERS["home_devices"](_ctx(), q="hall"))
    assert tok not in __import__("json").dumps(dev)


# ---------------------------------------------------------------- (4) reads + guards

def test_devices_lists_and_filters(fakeha):
    dev = _run(HOME_HANDLERS["home_devices"](_ctx(), q="hall"))
    ids = {d["entity_id"] for d in dev["devices"]}
    assert "light.hall" in ids and "sensor.hall_temp" in ids
    assert dev["devices"][0].get("controllable") is not None
    dev2 = _run(HOME_HANDLERS["home_devices"](_ctx(), domain="climate"))
    assert {d["entity_id"] for d in dev2["devices"]} == {"climate.ac_hall"}


def test_state_one_by_name(fakeha):
    st = _run(HOME_HANDLERS["home_state"](_ctx(), entity="hall temp"))
    assert st["ok"] is True and st["entity_id"] == "sensor.hall_temp" and st["state"] == "27.4"
    st2 = _run(HOME_HANDLERS["home_state"](_ctx(), entity="light.hall"))
    assert st2["state"] == "on" and st2["name"] == "Hall Light"


def test_fridge_geyser_readonly(fakeha):
    for eid in ("switch.fridge_plug", "switch.geyser_bathroom"):
        with pytest.raises(Exception) as e:
            _run(HOME_HANDLERS["home_off"](_ctx(), entity=eid))
        msg = str(e.value)
        assert "haath nahi lagata" in msg, eid
        out = home.recent_audit(T, 10)
        assert any(r["entity"] == eid and r["action"] == "refused" for r in out["entries"]), eid


def test_uncontrollable_domains_refused(fakeha):
    for eid in ("sensor.hall_temp", "camera.gate"):
        with pytest.raises(Exception) as e:
            _run(HOME_HANDLERS["home_on"](_ctx(), entity=eid))
        assert "switch main nahi chalata" in str(e.value)


def test_ac_temperature_clamped(fakeha):
    ok = _run(HOME_HANDLERS["home_on"](_ctx(), entity="climate.ac_hall", extra={"temperature": 24}))
    assert ok["ok"] is True and ok["say"]
    assert any("climate/set_temperature" in c for c in fakeha.calls)
    for bad in (19, 32):
        with pytest.raises(Exception) as e:
            _run(HOME_HANDLERS["home_on"](_ctx(), entity="climate.ac_hall", extra={"temperature": bad}))
        assert "20" in str(e.value) and "28" in str(e.value)


def test_media_volume_clamped(fakeha):
    _run(HOME_HANDLERS["home_on"](_ctx(), entity="media_player.tv", extra={"volume_level": 1.0}))
    vol = [c for c in fakeha.calls if "volume_level" in c][-1]
    assert "0.9" in vol, vol                      # 1.0 -> clamped to 0.9 (speaker <= 90 %)


# ---------------------------------------------------------------- (5) locks

def test_lock_needs_confirm(fakeha):
    with pytest.raises(Exception) as e:
        _run(HOME_HANDLERS["home_off"](_ctx(), entity="lock.main_door"))   # off = unlock
    assert "confirm" in str(e.value).lower()


def test_lock_never_in_routine(fakeha):
    with pytest.raises(Exception) as e:
        _run(HOME_HANDLERS["home_on"](_ctx(actor="routine"), entity="lock.main_door", confirm=True))
    assert "routine" in str(e.value).lower()
    assert fakeha.states["lock.main_door"]["state"] == "locked"


def test_lock_with_confirm_owner_passes(fakeha):
    ok = _run(HOME_HANDLERS["home_off"](_ctx(), entity="lock.main_door", confirm=True))
    assert ok["ok"] is True and fakeha.states["lock.main_door"]["state"] == "unlocked"
    out = home.recent_audit(T, 10)
    assert any(r["entity"] == "lock.main_door" and r["action"] == "unlock" and r["ok"] for r in out["entries"])


# ---------------------------------------------------------------- (6) controls end to end

def test_light_on_off_and_settle(fakeha):
    on = _run(HOME_HANDLERS["home_on"](_ctx(), entity="light.bedi"))
    assert on["ok"] is True and on["state"] == "on" and "Bedroom Light" in on["say"]
    off = _run(HOME_HANDLERS["home_off"](_ctx(), entity="light.bedi"))
    assert off["ok"] is True and off["state"] == "off" and "band kar di" in off["say"]
    assert any("light/turn_on" in c for c in fakeha.calls) and any("light/turn_off" in c for c in fakeha.calls)


def test_brightness_scene_button_cover(fakeha):
    b = _run(HOME_HANDLERS["home_on"](_ctx(), entity="light.hall", extra={"brightness": 120}))
    assert b["ok"] is True
    assert any("brightness" in c and "120" in c for c in fakeha.calls)
    sc = _run(HOME_HANDLERS["home_on"](_ctx(), entity="scene.movie_night"))
    assert sc["ok"] is True and any("scene/turn_on" in c for c in fakeha.calls)
    bu = _run(HOME_HANDLERS["home_on"](_ctx(), entity="button.restart_hub"))
    assert bu["ok"] is True and any("button/press" in c for c in fakeha.calls)
    cov = _run(HOME_HANDLERS["home_on"](_ctx(), entity="cover.hall_window"))
    assert cov["ok"] is True and fakeha.states["cover.hall_window"]["state"] == "open"
    cov2 = _run(HOME_HANDLERS["home_off"](_ctx(), entity="cover.hall_window"))
    assert cov2["ok"] is True and fakeha.states["cover.hall_window"]["state"] == "closed"


def test_by_name_resolution(fakeha):
    ok = _run(HOME_HANDLERS["home_off"](_ctx(), entity="hall fan"))
    assert ok["ok"] is True and ok["entity_id"] == "fan.hall"


def test_unknown_device_honest(fakeha):
    with pytest.raises(Exception) as e:
        _run(HOME_HANDLERS["home_on"](_ctx(), entity="light.nahi_hai_ye"))
    assert "nahi mila" in str(e.value)


def test_ha_down_honest(hm, monkeypatch):
    def boom(req):
        raise httpx.ConnectError("nope")
    real_client = httpx.AsyncClient
    monkeypatch.setattr(home.httpx, "AsyncClient", lambda **k: real_client(transport=httpx.MockTransport(boom), **k))
    with pytest.raises(Exception) as e:
        _run(HOME_HANDLERS["home_devices"](_ctx()))
    assert "pahunch" in str(e.value)


# ---------------------------------------------------------------- (7) audit trail

def test_audit_trail_readback(fakeha):
    _run(HOME_HANDLERS["home_on"](_ctx(), entity="light.bedi"))
    with pytest.raises(Exception):
        _run(HOME_HANDLERS["home_off"](_ctx(), entity="switch.geyser_bathroom"))
    out = home.recent_audit(T, 20)
    acts = [(r["entity"], r["action"], r["ok"]) for r in out["entries"]]
    assert ("light.bedi", "on", True) in acts
    assert ("switch.geyser_bathroom", "refused", False) in acts
    assert all("token" not in (r.get("detail") or "").lower() or "tokens" in (r.get("detail") or "").lower()
               for r in out["entries"])      # no secret material in the trail


# ---------------------------------------------------------------- (8) version

def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.789.0"


def test_pubspec_version():
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[2]
    assert "0.789.0+788" in (root / "pubspec.yaml").read_text()
