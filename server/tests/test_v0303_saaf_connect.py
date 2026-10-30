"""v0.303 SAAF CONNECT: the Connect tab and bazar_find show only what really works (Composio apps + working plugins)."""
import pytest


@pytest.fixture
def clean(env, monkeypatch):
    monkeypatch.setenv("CONNECT_CLEAN", "true")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-0123456789-abcdefghij")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.bazar import config as bzc, security, service
    bzc.reset_settings()
    security._vault = None
    service.set_executors(None)
    yield service
    get_settings.cache_clear()
    bzc.reset_settings()
    service.set_executors(None)


def test_catalogue_keeps_only_working_plugins(clean):
    cat = clean.catalog("default")
    st = {p["status"] for p in cat["packs"]}
    ex = {p["executor"] for p in cat["packs"]}
    assert cat["clean"] is True
    assert not st & {"demo", "no_shop_yet", "not_configured", "core", "unavailable"}
    assert "handoff" not in ex
    assert {"upi", "ride", "native", "reader"} <= ex                 # working plugins stay
    assert 120 <= cat["total"] <= 220                                 # was 694
    names = {p["name"] for p in cat["packs"]}
    assert "UMANG" not in names and "DigiLocker" not in names        # website-only handoffs gone


def test_connections_hide_providers_not_set_up(clean):
    st = {a["name"]: a["status"] for a in clean.connections("default")}
    assert "not_configured" not in st.values()


def test_find_never_offers_demo_bills_handoffs_or_the_directory(clean):
    r = clean.find("default", "bijli bill msedcl bharna hai")
    assert all(p["status"] != "demo" for p in r["packs"])
    assert "mcp_directory" not in r and "featured_connectors" not in r
    r = clean.find("default", "passport apply")
    assert all(p["pack_id"] != "passport-seva" for p in r["packs"])
    assert clean.mcp_directory("github")["servers"] == []


def test_switch_off_brings_everything_back(clean, monkeypatch):
    monkeypatch.setenv("CONNECT_CLEAN", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    assert clean.catalog("default")["total"] == 694
