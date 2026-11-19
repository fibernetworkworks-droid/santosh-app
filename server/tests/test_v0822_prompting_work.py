"""v0.999.34 KAAM KE SECTION (built as 0.999.33) (P6 of docs/HOOLA_PROMPTING_PLAN.md): coding, research, data and sheets, an AI assistant for
her customers, and the everyday ask - anatomy, code-read slots, engine wording, starter recipes, each section's checks,
the Hoola Code hand-off and its ledger hooks. No model runs here."""
from pathlib import Path

import pytest

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

REPO = Path(__file__).resolve().parents[2]
CON = REPO / "server" / "app" / "static" / "console"
KEY = "test-key-kaam-section"
NEW = ("code", "research", "data", "aiapp", "chat")


@pytest.fixture
def pr(env, monkeypatch):
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.prompting import brief as B
    from app.prompting import context as C
    monkeypatch.setattr(C, "known", lambda t: {"name": "", "tagline": "", "colours": [], "tone": "", "language": "",
                                                "about": "", "items": []})
    monkeypatch.setattr(B, "ASK", [lambda s, p: {}])
    yield B
    get_settings.cache_clear()


def test_thirteen_sections():
    from app.prompting import anatomy as A
    from app.prompting import dialect as D
    from app.prompting import ledger as L
    assert A.ORDER == ("web", "image", "script", "app", "video", "music", "marketing", "doc",
                       "code", "research", "data", "aiapp", "chat")
    assert L.SECTIONS == A.ORDER and set(D.RENDER) == set(A.ORDER) == set(D.DIALECT_V)
    for sec in NEW:
        assert 1 <= len(A.required(sec)) <= 4, sec


@pytest.mark.parametrize("text,section", [
    ("fix the bug in server/app/shop.py, total shows Rs 0 with coupon", "code"),
    ("tests failing after the last pull request in my repo", "code"),
    ("research the cheapest courier from Akola to Pune", "research"),
    ("compare jio and airtel plans", "research"),
    ("in sales_oct.xlsx which 5 products made most profit, make a chart", "data"),
    ("a vlookup formula for my sheet", "data"),
    ("make a chatbot for my salon that takes bookings on whatsapp", "aiapp"),
    ("an ai assistant to answer my customers on my website", "aiapp"),
    ("whatsapp message: 20% off till 15 nov", "marketing"),       # P5 and P1 sections are read as before
    ("30 second reel script for coaching", "script"),
    ("diwali sale ka poster banao", "image"),
    ("ek kirana app banao android", "app"),
    ("quotation pdf for ABC Rs 45000", "doc"),
    ("aaj mausam kaisa hai", ""),                                  # the everyday ask is never guessed - she picks it
])
def test_which_section(text, section):
    from app.prompting import brief as B
    assert B.guess_section(text) == section


def test_code_reads_each_section(pr):
    c = pr.code_slots("code", "fix the bug in server/app/shop.py, total shows Rs 0 with coupon, run pytest tests/test_shop.py")
    assert c["kind"] == "Fix a bug" and c["where"] == "server/app/shop.py, tests/test_shop.py"
    assert c["check"] == "pytest tests/test_shop.py" and c["task"].startswith("fix the bug")      # her sentence = the task
    r = pr.code_slots("research", "research the latest courier prices from Akola to Pune, official sources, in a table")
    assert r == {"sources": "Official / government sites first", "form": "A comparison table", "asof": "The latest",
                 "region": "Pune, Akola", "question": "research the latest courier prices from Akola to Pune, official sources, in a table"}
    d = pr.code_slots("data", "in sales_oct.xlsx which products sold most, chart by month")
    assert d["output"] == "A chart" and d["data"] == "sales_oct.xlsx" and "which products" in d["question"]
    assert pr.code_slots("aiapp", "a chatbot that takes bookings on whatsapp") == {"role": "Take bookings", "channel": "My WhatsApp number"}
    assert pr.code_slots("chat", "reply to a customer who says the cake was late")["form"] == "A message I can send"


def test_dialects_say_what_proves_it_and_never_send(pr):
    from app.prompting import dialect as D
    b = pr.apply(pr.understand("t", "fix the bug in server/app/shop.py: cart total shows Rs 0 after a coupon, run pytest"),
                 {"done": "Rs 500 with a 10% coupon shows Rs 450"})
    out = D.render(b)
    assert out["run"]["to"] == "code" and out["run"]["label"] == "Open in Hoola Code" and out["dialect"] == "code-1"
    assert "DONE WHEN: Rs 500 with a 10% coupon shows Rs 450." in out["prompt"] and "WHERE: server/app/shop.py." in out["prompt"]
    assert "step by step" not in out["prompt"].lower() and "you are" not in out["prompt"].lower()
    res = D.render(pr.understand("t", "research the latest courier prices from Akola to Pune, compare in a table"))
    assert res["run"]["text"].startswith("Research this:") and "give its link and date" in res["prompt"]
    dat = D.render(pr.understand("t", "in sales_oct.xlsx total sales by month as a chart, must match Rs 4,82,000"))
    assert "never estimate a number" in dat["prompt"] and "Rs 4,82,000" in dat["prompt"]
    ai = D.render(pr.understand("t", "a chatbot for my salon on whatsapp: open 10 am to 8 pm, haircut Rs 300"))
    assert ai["run"]["text"].startswith("Plan this AI app for my customers (draft it, do not publish)")
    assert "Never invent a price" in ai["prompt"]
    ch = D.render(pr.understand("t", "reply to a customer who says the cake came 40 minutes late", "chat"))
    assert ch["run"]["to"] == "chat" and ch["prompt"].startswith("reply to a customer")


def test_section_checks_say_why(pr):
    def reasons(text, section="", **set_):
        b = pr.understand("t", text, section)
        if set_:
            b = pr.apply(b, set_)
        return " ".join(r["text"] for r in pr.score(b)["reasons"])
    assert "a failing test first" in reasons("fix the crash on the orders page of my app code")
    assert "Too short to act on" in reasons("fix the bug in my code", task="fix it")
    assert "Prices change" in reasons("research courier prices from Akola to Pune")
    assert "Prices change" not in reasons("research the latest courier prices from Akola to Pune")
    assert "'Best' for what" in reasons("research which is best laptop for billing software")
    assert "what the chart compares" in reasons("make a chart from sales_oct.xlsx")
    assert "what the chart compares" not in reasons("make a chart of sales by month from sales_oct.xlsx")
    assert "Give it real facts" in reasons("a chatbot for my salon", knows="our services")
    assert "Give it real facts" not in reasons("a chatbot for my salon", knows="open 10 am to 8 pm, haircut Rs 300")
    assert "hand over to you" in reasons("a chatbot for my salon")


def test_recipes_for_every_work_section(pr):
    from app.prompting import dialect as D
    from app.prompting import recipes as R
    assert R.check() == [] and len(R.RECIPES) >= 60
    for sec in NEW:
        mine = [r for r in R.RECIPES if r["section"] == sec]
        assert len(mine) >= 4, sec
        for r in mine:
            b = R.use(r["id"], {x["key"]: x["eg"] for x in r["blanks"]})["brief"]
            assert D.render(b)["prompt"] and pr.score(b)["score"] >= 70, r["id"]


def test_hoola_code_ledger_hooks(pr):
    from app.db import session
    from app.devsahayak import api as DA
    from app.prompting import dialect as D
    from app.prompting import ledger as L
    b = pr.apply(pr.understand("t1", "fix the bug in server/app/shop.py: cart total shows Rs 0 after a coupon"),
                 {"done": "the total is right"})
    text = D.render(b)["run"]["text"]
    rid = L.hand("t1", text, b)
    DA._pled_code("t1", text, {"id": "dev_task_1"})
    with session() as s:
        r = s.get(L.PromptRun, rid)
        assert r.status == "ready" and " dev_task_1 " in r.refs and r.section == "code" and r.dialect == "code-1"
    DA._pled_code_event("t1", "dev_task_1", "deleted")
    with session() as s:
        assert s.get(L.PromptRun, rid).grade == "dropped"
    DA._pled_code("t1", "a coding job nobody prompted for", None)                 # never raises
    src = (REPO / "server" / "app" / "devsahayak" / "api.py").read_text()
    assert "_pled_code, tenant" in src and '_pled_code_event, tenant, tid, "deleted"' in src


def test_page_wiring():
    js = (CON / "prompting.js").read_text()
    for sec in NEW:
        assert f"{sec}: I(" in js and f"{sec}: '" in js, sec
    assert "'/console/code'" in js and "'?prompt=' + encodeURIComponent" in js


def test_coding_prompt_lands_in_hoola_code(arena_server, monkeypatch):  # noqa: F811
    base, browser, key = arena_server
    from app.config import get_settings
    from app.prompting import brief as B
    from app.prompting import context as C
    monkeypatch.setenv("HOOLA_CODE_PAGE", "true")                # conftest keeps the page off for the older suites
    get_settings.cache_clear()
    monkeypatch.setattr(B, "ASK", [lambda s, p: {}])
    monkeypatch.setattr(C, "known", lambda t: {"name": "", "tagline": "", "colours": [], "tone": "", "language": "",
                                                "about": "", "items": []})
    ctx = browser.new_context(viewport={"width": 1360, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(base + "/console/prompting#/s/code")
    pg.wait_for_selector("#hpText")
    assert pg.locator(".hp-nav").count() == 19
    pg.fill("#hpText", "fix the bug in server/app/shop.py: cart total shows Rs 0 after a coupon, run pytest")
    pg.click("#hpAsk button[type=submit]")
    pg.wait_for_selector("#hpRun")
    assert "Coding" in pg.inner_text(".hp-top h1") and pg.inner_text("#hpRun") == "Open in Hoola Code"
    assert "Hoola Code" in pg.inner_text("#hpMain")
    pg.click("#hpRun")
    pg.wait_for_url("**/console/code**")
    pg.wait_for_selector("#hcdLine")
    assert "cart total shows Rs 0" in pg.input_value("#hcdLine")
    assert "prompt=" not in pg.url                                  # the address is cleaned; nothing was started
    assert not [e for e in errs if "prompting" in e or "code.js" in e], errs
