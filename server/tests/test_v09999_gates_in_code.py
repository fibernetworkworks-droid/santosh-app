"""B7 GATES IN CODE (owner: "GO B7" on docs/research/lovable/03_backend_vs_hoola.md, gap 8).

Before: two gates lived in the prompt, not in code. Her own chat agent (actor owner) could build an architect plan and put a
logic draft live just by calling the tool after she said haan in words, and Hoola Cloud's `confirm_public` (open a list with
personal data to the whole internet) was a flag the MODEL set inside the change. Now the chat tool can only put the card back
in front of her; the build, the logic and the public list happen only from her tap (the console / Studio / phone routes)."""
import ast
import json

import pytest
from fastapi.testclient import TestClient

from tests.test_v0305_web_apps import app_site  # noqa: F401  (fixture)
from tests.test_v0407_ek_dimaag import WORKFLOW, arch_env  # noqa: F401  (fixture)
from tests.test_v0814_app_engine import _tool, ae_env  # noqa: F401  (fixture + helper)
from tests.test_v0827_hoola_cloud import ORDERS, _app
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.124"


ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


def _ctx(actor="owner"):
    from app.agent.tools import Ctx
    return Ctx(tenant_id=T, conversation_id="", actor=actor)


# ---------------------------------------------------------------- 1. the architect plan: her tap, not her words
def test_chat_agent_never_builds_a_plan_the_card_comes_back(arch_env, monkeypatch):
    from app.agent import site_tools as ST
    from app.events import bus
    from app.main import app
    from app.site import architect as AR
    seen = []
    real = bus.publish
    monkeypatch.setattr(bus, "publish", lambda conv, kind, payload: seen.append(kind) or real(conv, kind, payload))
    out = ST._act(_ctx(), "architect", {"brief": "school ka portal, fees aur chhutti"})
    seen.clear()
    got = ST._act(_ctx(), "architect_ok", {"spec": out["number"], "hash": out["hash"], "modules": ["pages", "data"]})
    assert got["status"] == "waiting for her tap" and "tap" in got["say"]
    assert "site_spec" in seen                                              # the card with its button is back in her chat
    assert AR.card(T, out["number"])["status"] != "built"                   # nothing was built from her words
    with pytest.raises(Exception):
        ST._act(_ctx("staff:x"), "architect_ok", {"spec": out["number"], "hash": out["hash"]})
    # her tap = the route the console / Web Studio / phone button calls, with the hash of the card she saw
    c = TestClient(app)
    assert c.post(f"/api/site-architect/{out['id']}/approve", json={"hash": "wrong"}).status_code == 409
    done = c.post(f"/api/site-architect/{out['id']}/approve", json={"hash": out["hash"]}).json()
    assert done["number"].startswith("S-")
    again = ST._act(_ctx(), "architect_ok", {"spec": out["number"]})       # a built plan: said, nothing re-published
    assert again["status"] == "built"


# ---------------------------------------------------------------- 2. logic on a website: her Apply, not her words
def test_chat_agent_never_puts_logic_live(app_site, monkeypatch):
    from app.agent import site_tools as ST
    from app.agent.tools import ToolError
    from app.appmaker import ai as AAI
    from app.main import app
    sid = app_site
    c = TestClient(app)
    with pytest.raises(ToolError):                                          # no draft yet: said, nothing made up
        ST._act(_ctx(), "logic_ok", {"site": sid, "hash": "x"})
    monkeypatch.setattr(AAI, "ask_json", lambda system, prompt, max_tokens=7000: json.loads(json.dumps(WORKFLOW)))
    c.post(f"/api/sites/{sid}/link-app")
    d = ST._act(_ctx(), "logic", {"site": sid, "instruction": "order ready karne se pehle manager approve kare"})
    h = d["hash"]
    before = c.get(f"/api/sites/{sid}/logic").json()
    got = ST._act(_ctx(), "logic_ok", {"site": sid, "hash": h})
    assert got["status"] == "waiting for her tap" and got["hash"] == h and "Apply" in got["say"]
    after = c.get(f"/api/sites/{sid}/logic").json()
    assert after.get("rev") == before.get("rev") and after["draft"]["hash"] == h   # still waiting, nothing live
    ok = c.post(f"/api/sites/{sid}/logic/apply", json={"hash": h}).json()  # her 'Apply this logic' button
    assert ok["rev"] >= 1


# ---------------------------------------------------------------- 3. Hoola Cloud: the model can never open a list to the internet
def test_model_cannot_confirm_public_the_card_waits_for_her(ae_env):
    from app.appengine import cloud as CL
    from app.appengine import service as AE
    from app.main import app
    aid, r = _app([ORDERS])
    msg = ""
    try:
        _tool(action="cloud_change", app=aid, changes=[{"op": "rules", "list": "orders", "read": "public", "confirm_public": True}])
    except Exception as e:                                                  # noqa: BLE001
        msg = str(e)
    assert "Let anyone read this" in msg and "phone" in msg
    r = AE._load(T, aid)
    lst = next(x for x in CL.schema(r)["lists"] if x["key"] == "orders")
    assert lst["rules"]["read"] == "own" and not lst.get("public_ack")       # nothing changed
    card = CL.pending_public(r)
    assert card["list"] == "orders" and "phone" in card["fields"]
    assert all("confirm_public" not in ch for ch in card["changes"])         # the model's yes is not carried
    assert CL.overview(r)["pending_public"]["list"] == "orders"
    # the gate is in apply_changes too, not only in the tool
    with pytest.raises(CL.CloudError):
        CL.apply_changes(r, [{"op": "rules", "list": "orders", "read": "public", "confirm_public": True}], "hoola", from_model=True)
    # her tap in the Studio's Cloud tab
    c = TestClient(app)
    assert c.post(f"/api/appengine/{aid}/cloud/changes", json={"public_ok": True}).status_code == 403
    ok = c.post(f"/api/appengine/{aid}/cloud/changes", json={"public_ok": True, "confirm": True}).json()
    r = AE._load(T, aid)
    lst = next(x for x in CL.schema(r)["lists"] if x["key"] == "orders")
    assert ok["version"] and lst["rules"]["read"] == "public" and lst["public_ack"] is True
    assert CL.pending_public(r) is None
    assert CL.migrations(r)[-1]["by"] == "her (let anyone read)"


def test_not_now_clears_only_the_public_card(ae_env):
    from app.appengine import cloud as CL
    from app.appengine import service as AE
    from app.main import app
    aid, r = _app([ORDERS])
    CL.queue_pending(r, [{"op": "drop_field", "list": "orders", "field": "qty"}])
    with pytest.raises(Exception):
        _tool(action="cloud_change", app=aid, changes=[{"op": "rules", "list": "orders", "read": "public"}])
    c = TestClient(app)
    assert c.post(f"/api/appengine/{aid}/cloud/pending/clear", json={"which": "public"}).json()["ok"]
    r = AE._load(T, aid)
    assert CL.pending_public(r) is None and CL.pending(r)                   # the data-loss card is still there
    assert c.post(f"/api/appengine/{aid}/cloud/changes", json={"public_ok": True, "confirm": True}).status_code == 409


# ---------------------------------------------------------------- 4. the tool layer never reaches a her-tap door
def test_no_agent_module_calls_a_her_tap_function():
    taps = {"logic_apply", "public_run", "destructive_run"}
    seen_apply = []
    for f in sorted((ROOT / "app" / "agent").glob("*.py")):
        tree = ast.parse(f.read_text())
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            fn = n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
            assert fn not in taps, f"{f.name} calls {fn} - that is her tap only"
            if fn == "approve" and isinstance(n.func, ast.Attribute) and getattr(n.func.value, "id", "") == "AR":
                pytest.fail(f"{f.name} calls the architect's approve - that is her tap only")
            if fn == "apply_changes":
                kw = {k.arg: k.value for k in n.keywords}
                assert isinstance(kw.get("from_model"), ast.Constant) and kw["from_model"].value is True, f.name
                seen_apply.append(f.name)
    assert seen_apply == ["appengine_tools.py"]


def test_studio_cloud_tab_draws_the_public_card():
    js = (ROOT / "app" / "static" / "console" / "appengine.js").read_text()
    for k in ("pending_public", "Yes, anyone may read this", "pub-yes", "pub-no", "public_ok: true", "which: 'public'"):
        assert k in js, k
    tools = (ROOT / "app" / "agent" / "appengine_tools.py").read_text()
    assert "confirm_public: true" not in tools                              # the model is no longer told to set it
    site = (ROOT / "app" / "agent" / "site_tools.py").read_text()
    assert "ONLY after she clearly said haan" not in site
