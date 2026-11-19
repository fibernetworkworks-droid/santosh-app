"""v0.999.32 WEBSITE WIRING (owner: "NOW GO THROUGH -- EVERY WEBSITE BUILDING FLOW -- CHECK EVERY THING IS WIRED PROPERLY
OR NOT"): Build mode, Plan mode, ask-first, templates, the chat agent and the old three looks were walked end to end
through the real routes, and the prototype screen in a real browser. Three things were not wired:
1. the status line Hoola sends to the chat and the phone still said "Say 'Yes' and I will make 3 looks" with the
   prototype on, and said NOTHING when the prototype was ready (an empty phone push);
2. the website card in the main console chat and on the phone had no prototype state at all (blank card, no way to it)
   and their yes button said "make 3 looks";
3. on a phone-width screen the Web Studio chat was 440 px wide on a 390 px screen (a later rule overrode the phone rule
   since v0.667), cutting the typing box and the send button."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0999_24_prototype import ProtoAI
from tests.test_v121_site import T, site_env  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.32"


@pytest.fixture
def proto(site_env, monkeypatch):
    from app.config import get_settings
    from app.site import ai as AI
    monkeypatch.setenv("STUDIO_PROTOTYPE", "true")
    get_settings.cache_clear()
    fake = ProtoAI(site_env)
    monkeypatch.setattr(AI, "ask_json", fake)
    yield fake
    get_settings.cache_clear()


def _board(sid):
    from app.site import service as S
    v = S.view(S._load(sid))
    return S._say(v)


def test_the_status_line_follows_the_prototype(proto):
    from app.main import app
    from app.site import service as S
    v = S.new(T, "mithai dukaan ki website, online order WhatsApp par. Phone 98765 43210", "", name="Sharma Sweets")
    planned = _board(v["id"])
    assert "prototype of every page" in planned and "3 looks" not in planned
    TestClient(app).post(f"/api/sites/{v['id']}/plan", json={})
    ready = _board(v["id"])
    assert ready.startswith("The prototype is ready:") and "Build the real website" in ready
    assert f"{len(S.get(T, v['id'])['prototype']['pages'])} pages" in ready


def test_the_switch_off_keeps_the_three_looks_line(site_env):
    from app.site import service as S
    v = S.new(T, "mithai dukaan ki website, online order WhatsApp par. Phone 98765 43210", "", name="Sharma Sweets")
    assert "Say 'Yes' and I will make 3 looks." in _board(v["id"])


def test_the_console_chat_card_has_a_prototype_state():
    js = (ROOT / "app" / "static" / "console" / "build.js").read_text()
    assert "s === 'prototype'" in js and "protoBody" in js and "/console/web#/site/" in js
    assert "Check it in Web Studio" in js and "planYes(v)" in js


def test_the_phone_site_card_has_a_prototype_state():
    dart = (REPO / "lib" / "ui" / "site_screen.dart").read_text()
    assert "class SitePrototypeOpen" in dart and "'prototype': 'Prototype: your check'" in dart
    assert "/console/web#/site/" in dart and "if (st == 'prototype')" in dart
    assert "Yes, make 3 looks" not in dart and "Making 3 looks, they will show here." not in dart


def test_the_studio_chat_fits_a_phone():
    css = (ROOT / "app" / "static" / "console" / "webstudio.css").read_text()
    assert ".chat{width:440px;background:var(--bg)}" not in css
    assert "@media (min-width:1001px){.chat{width:440px}}" in css
    assert "@media (max-width:760px){" in css and ".chat{width:auto;" in css
