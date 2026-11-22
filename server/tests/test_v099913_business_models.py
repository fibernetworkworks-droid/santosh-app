"""B8 BUSINESS MODELS (gap 10 of docs/research/lovable/03_backend_vs_hoola.md): a website plan for an ISP (or any business
App Sahayak already models) starts its data from Hoola's tested model - plans, subscribers, devices, tickets, bills,
payments - instead of only the lists the model happened to write from the plan's words."""
import json

from fastapi.testclient import TestClient

from tests.test_v0407_ek_dimaag import SCHOOL_LOGIC, SCHOOL_SPEC
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

ISP_WORDS = "Build the ISP portal for my fiber broadband company - customers see their plan, bills and complaints"


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.122"


def test_her_words_pick_the_business_model():
    from app.site import basemodel as BM
    assert BM.match(ISP_WORDS) == "isp_ops"
    assert BM.match("hamari FTTH company ka portal") == "isp_ops"
    assert BM.match("CRM for my sales team") == "crm"
    assert BM.match("a bakery website with our cakes") == ""
    assert BM.match("crisp new design") == ""                  # whole words only: 'crisp' is not 'isp'
    assert BM.match("") == ""


def test_the_isp_model_has_what_a_portal_needs():
    from app.site import basemodel as BM
    from app.site import webapp as W
    ls = BM.lists("isp_ops")
    keys = [c["key"] for c in ls]
    for k in ("plan_package", "subscriber", "customer", "ont", "ticket", "work_order", "invoice", "payment"):
        assert k in keys, k
    assert keys[:2] == ["plan_package", "subscriber"]          # the business's own tables first
    assert len(ls) <= BM.MAX_LISTS
    ok_types = {"text", "long_text", "number", "phone", "email", "date", "choice", "yes_no", "photo", "location", "ref",
                "file", "scan"}
    for c in ls:
        for f in c["fields"]:
            assert f["type"] in ok_types, (c["key"], f)
            assert not BM.SECRET.search(f["key"]), (c["key"], f["key"])
            if f["type"] == "ref":
                assert f["to"] in keys, (c["key"], f)           # a link always points inside the model
            if f["type"] == "choice":
                assert f["options"]
    sub = next(c for c in ls if c["key"] == "subscriber")
    assert {"key": "plan", "type": "ref", "to": "plan_package"} in sub["fields"]
    assert W.MAX_COLLECTIONS                                     # the site itself stays capped where lists are applied


def test_missing_names_only_the_business_tables():
    from app.site import basemodel as BM
    drafted = [{"key": "plans", "label": "Internet plans"}, {"key": "subscriber", "label": "Customers"},
               {"key": "routers", "label": "ONT"}]
    got = BM.missing("isp_ops", drafted)
    assert "Internet plan" not in got and "Subscriber" not in got and "ONT / router" not in got
    assert {"OLT", "PON port", "Fiber route"} <= set(got)
    assert "Invoice" not in " ".join(got)                       # bills are not the ISP's own module: never nagged about
    assert BM.missing("", drafted) == []


def _env(site_env, monkeypatch, words_check):
    from app.appmaker import ai as AAI
    from app.site import ai as AI
    from app.site import architect as AR
    seen = []

    def ask(system, prompt, max_tokens=6000, kind="build"):
        if system.startswith(AR.ARCH_SYSTEM[:40]):
            assert words_check in prompt
            return json.loads(json.dumps(SCHOOL_SPEC))
        return site_env(system, prompt, max_tokens, kind)

    def logic(system, prompt, max_tokens=7000):
        seen.append(json.loads(prompt))
        return json.loads(json.dumps(SCHOOL_LOGIC))
    monkeypatch.setattr(AI, "ask_json", ask)
    monkeypatch.setattr(AAI, "ask_json", logic)
    return seen


def test_an_isp_plan_drafts_its_data_from_the_isp_model(site_env, monkeypatch):
    from app.main import app
    seen = _env(site_env, monkeypatch, "ISP portal")
    card = TestClient(app).post("/api/site-architect", json={"words": ISP_WORDS}).json()
    assert seen, "the data draft was asked"
    base = seen[-1]["starting_model"]
    assert base["business"] == "ISP / FTTH operations"
    assert [c["key"] for c in base["lists"]][:2] == ["plan_package", "subscriber"]
    data = next(m for m in card["modules"] if m["key"] == "data")
    assert data["lines"][0] == "Started from Hoola's ISP / FTTH operations model"
    assert data["model"]["key"] == "isp_ops"
    # the fake draft kept none of the ISP tables: the card names them, and still lets her build
    assert "Subscriber" in data["missing"] and any(x.startswith("Not in this plan from that model:") for x in data["lines"])
    assert card["data_ready"]


def test_a_plan_with_no_known_business_gets_no_starting_model(site_env, monkeypatch):
    from app.main import app
    seen = _env(site_env, monkeypatch, "school")
    card = TestClient(app).post("/api/site-architect",
                                json={"words": "hamare school ka portal - admission, fees, chhutti ki arzi, notices"}).json()
    assert seen and "starting_model" not in seen[-1]
    data = next(m for m in card["modules"] if m["key"] == "data")
    assert data["model"] == {} and data["missing"] == []
    assert not any(x.startswith("Started from") for x in data["lines"])


def test_the_logic_author_is_told_how_to_read_the_model():
    from app.appmaker.logic import service as LS
    assert '"starting_model"' in LS.AUTHOR_SYSTEM and "tested data model" in LS.AUTHOR_SYSTEM
