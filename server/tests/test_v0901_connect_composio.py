"""v0.901 CONNECT: her phone's Connect page shows only Composio apps, in ten plain groups worked out on the server."""
from pathlib import Path

from tests.test_v0276_composio import ACCOUNTS, _link, cz  # noqa: F401  (the fake Composio + its fixture)

ROOT = Path(__file__).resolve().parents[2]


def test_group_of_pins_popular_apps_and_reads_composio_categories():
    from app.bazar import composio as c
    assert c.group_of("slack") == "mail" and c.group_of("razorpay") == "money" and c.group_of("notion") == "projects"
    assert c.group_of("acme", ["CRM"]) == "crm"
    assert c.group_of("acme", ["Email Marketing"]) == "marketing"        # the specific word wins over "email"
    assert c.group_of("acme", ["Customer Support"]) == "crm"
    assert c.group_of("acme", ["Scheduling & Booking"]) == "calendar"
    assert c.group_of("acme", ["Developer Tools"]) == "dev"
    assert c.group_of("acme", ["Something else"]) == "more" and c.group_of("acme", []) == "more"
    assert [g for g, _ in c.GROUPS][-1] == "more" and len(c.GROUPS) == 11


def test_home_in_one_call_with_groups_tops_and_her_apps(cz):  # noqa: F811
    h = cz["svc"].composio_home("default")
    assert h["configured"] is True and h["total"] == 5 and h["connected"] == 0 and h["mine"] == []
    groups = {g["id"]: g for g in h["groups"]}
    assert set(groups) == {"mail", "crm", "data", "projects"}
    assert groups["crm"]["count"] == 2                                   # zendesk + pipedrive
    # an app Newtika has not switched on (pipedrive: OAuth with no login) is never a group's top pick
    assert [a["toolkit"] for a in groups["crm"]["top"]] == ["zendesk"]
    assert groups["crm"]["top"][0]["status"] == "needs_key" and groups["crm"]["top"][0]["group_name"] == "Sales & CRM"
    assert {a["toolkit"] for a in h["featured"]} == {"notion", "slack"}
    _link(cz)
    h = cz["svc"].composio_home("default")
    assert h["connected"] == 1 and h["mine"][0]["toolkit"] == "slack" and h["mine"][0]["status"] == "ready"
    assert "slack" not in {a["toolkit"] for a in h["featured"]}
    assert {g["id"]: g for g in h["groups"]}["mail"]["connected"] == 1


def test_list_by_group_sort_and_search_groups(cz):  # noqa: F811
    svc = cz["svc"]
    assert [a["toolkit"] for a in svc.composio_apps("default", group="crm")["apps"]] == ["zendesk", "pipedrive"]
    assert [a["toolkit"] for a in svc.composio_apps("default", group="crm", sort="az")["apps"]] == ["pipedrive", "zendesk"]
    assert svc.composio_apps("default", sort="connected")["apps"] == []
    _link(cz)
    assert [a["toolkit"] for a in svc.composio_apps("default", sort="connected")["apps"]] == ["slack"]
    res = svc.composio_apps("default", q="s")
    assert all("group" in a and "group_name" in a for a in res["apps"])
    assert {g["id"] for g in res["groups"]} <= {"mail", "crm", "data", "projects", "more"}


def test_home_route_and_not_configured(env, monkeypatch):
    from app.bazar import service
    monkeypatch.delenv("COMPOSIO_API_KEY", raising=False)
    from app.config import get_settings
    get_settings.cache_clear()
    assert service.composio_home("default") == {"configured": False, "total": 0, "connected": 0, "mine": [],
                                                "featured": [], "groups": []}
    get_settings.cache_clear()
    src = (ROOT / "server/app/bazar/api/composio.py").read_text()
    assert '"/api/composio/home"' in src and "group, sort" in src


def test_phone_connect_page_is_composio_only():
    dart = (ROOT / "lib/ui/shell/hoola_connect.dart").read_text()
    assert "composioHome()" in dart and "ConnectGroupPage" in dart and "Built-in tools" in dart
    assert "bazarCatalog" not in dart and "linkApp(" not in dart        # the old plugin list is not on this page
    assert "Never paste a key in the chat" in dart
    tabs = (ROOT / "lib/ui/shell/hoola_tabs.dart").read_text()
    assert "class HoolaConnect " not in tabs and "connectSections" not in tabs
    api = (ROOT / "lib/api.dart").read_text()
    assert "'/api/composio/home'" in api and "'group': group" in api


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION.startswith("0.902.0")
    assert "version: 0.902.0+901" in (ROOT / "pubspec.yaml").read_text()
