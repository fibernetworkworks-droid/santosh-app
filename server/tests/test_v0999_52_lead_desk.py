"""v0.999.52 LEAD DESK - the Lead Generation employee's own section (the Accounts desk's twin): its chat (kind 'leads', out of
her Hoola chats, a CSV / Excel can be attached) beside the desk's pages (Today, Find leads, Leads + one lead, Lists, Quality &
settings); stages, follow-ups, notes, a timeline, saved searches, quality checks; hand-offs to the campaign desk and the
Telecaller only after two taps; message drafts with a WhatsApp link she sends herself; nothing is ever sent from here."""
import asyncio
import os
import threading
import time
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"
T = "default"
ROWS = [{"name": "Shree Dental Clinic", "phone": "9822041234", "city": "Pune", "category": "Dentist"},
        {"name": "Smile Care", "phone": "", "website": "smilecare.example", "city": "Pune", "category": "Dentist",
         "address": "Karve Road"},
        {"name": "Patil Hardware", "phone": "9422011234", "city": "Akola", "category": "Hardware"},
        {"name": "Shree Dental Clinic", "phone": "9822049999", "city": "Pune", "category": "Dentist"}]


@pytest.fixture
def ld(env):
    from app.employee import hire
    from app.leads import service as S
    hire.hire(T, "leads", trust="seekh")
    out = S.run_her_data(T, "my old list", ROWS, "dentists-old.csv")
    assert out["ok"], out
    got = S.rows(T)["rows"]
    yield {r["name"] + "|" + r["phone"]: r["id"] for r in got}


def _id(ids, name, phone=""):
    return next(v for k, v in ids.items() if k.startswith(name + "|") and (not phone or k.endswith(phone)))


def test_the_leads_chat_is_its_own_and_knows_the_desk(ld):
    from app.main import app
    from app import leadschat, convs
    with TestClient(app) as c:
        r = c.get("/api/leads/chat").json()
        assert r["id"]
        home = c.post("/api/conversations").json()["id"]
        lid = c.post("/api/leads/chat/new").json()["id"]        # the untouched first chat is reused
        assert lid == r["id"]
        ids = [x["id"] for x in c.get("/api/conversations").json()["conversations"]]
        assert home in ids and lid not in ids                   # never in her Hoola chat list
        assert leadschat.is_leads(lid) and not leadschat.is_leads(home)
        assert c.get(f"/api/leads/chat/{lid}/ok").json()["ok"] and c.get(f"/api/leads/chat/{home}/ok").status_code == 404
        convs.mark(T, lid, "message")
        assert convs.current(T) != lid
        s = c.get("/api/leads/desk/summary").json()
        assert s["hired"] and s["counts"]["all"] == 4 and s["no_phone"] == 1
    b = leadschat.block(T)
    assert "<lead_desk>" in b and "Leads kept: 4" in b and "never invent a business" in b
    assert "can NOT send anything" in b and "leads_desk action=draft" in b and "import_file" in b
    assert "attach your own list" in leadschat.greeting(T)


def test_a_call_from_the_leads_chat_is_a_leads_turn(ld):
    from app import callconv, leadschat
    from app.db import Conversation, session
    lid = leadschat.current(T)["id"]
    with session() as s:
        c = Conversation(tenant_id=T, kind="call", origin_conv=lid)
        s.add(c)
        s.flush()
        call = c.id
    assert callconv.origin_of(call) == lid and leadschat.is_leads(call)


def test_stages_follow_ups_notes_and_the_timeline(ld):
    from app.leads import pipeline as PL
    a, p = _id(ld, "Shree Dental Clinic", "1234"), _id(ld, "Patil Hardware")
    assert PL.counts(T) == {"all": 4, "new": 4, "contacted": 0, "interested": 0, "not_interested": 0, "won": 0, "opted_out": 0}
    assert PL.set_stage(T, [a], "contacted")["changed"] == 1
    PL.set_stage(T, [p], "interested")
    c = PL.counts(T)
    assert (c["new"], c["contacted"], c["interested"]) == (2, 1, 1)
    assert [r["id"] for r in PL.leads(T, stage="interested")["rows"]] == [p]
    assert len(PL.leads(T, stage="new")["rows"]) == 2
    PL.set_follow(T, [a], (date.today() - timedelta(days=1)).isoformat(), "call after Diwali")
    PL.add_note(T, a, "Busy until the festival")
    due = PL.leads(T, due=True)["rows"]
    assert [r["id"] for r in due] == [a] and due[0]["follow_note"] == "call after Diwali"
    assert PL.today(T)["due"][0]["id"] == a
    tl = PL.lead(T, a)["timeline"]
    kinds = [e["kind"] for e in tl]
    assert {"found", "stage", "follow", "note"} <= set(kinds)
    assert any("dentists-old.csv" not in e["text"] and e["kind"] == "found" for e in tl)
    PL.set_stage(T, [a], "won")                                  # a won lead needs no follow-up
    assert PL.lead(T, a)["lead"]["follow_on"] is None
    with pytest.raises(PL.DeskError):
        PL.set_stage(T, [a], "bought")


def test_an_opted_out_business_is_never_drafted_or_handed_over(ld):
    from app.leads import pipeline as PL
    from app.leads import service as S
    a, p = _id(ld, "Shree Dental Clinic", "1234"), _id(ld, "Patil Hardware")
    d = PL.draft(T, p, "Namaste, can I share our price list?")
    assert d["whatsapp_link"].startswith("https://wa.me/919422011234?text=Namaste") and "send" in d["note"]
    S.set_opt_out(T, a, True)
    with pytest.raises(PL.DeskError):
        PL.draft(T, a, "hello")
    with pytest.raises(PL.DeskError):
        PL.set_follow(T, [a], date.today().isoformat())
    assert PL.set_stage(T, [a], "contacted")["skipped_opted_out"] == 1
    assert PL.lead(T, a)["lead"]["stage"] == "opted_out"
    card = PL.to_telecaller(T, [a, p])
    assert card["confirm_required"] and card["rows"] == 1 and card["opt_out_excluded"] == 1
    from app.telecall import service as TC
    assert TC.leads(T) == []                                     # the first tap adds nobody
    done = PL.to_telecaller(T, [a, p], confirm=True)
    assert done["added"] == 1 and [x["phone"][-4:] for x in TC.leads(T)] == ["1234"]


def test_campaign_hand_off_of_the_ticked_rows_is_two_taps(ld):
    from app.main import app
    a, s = _id(ld, "Shree Dental Clinic", "1234"), _id(ld, "Smile Care")
    with TestClient(app) as c:
        card = c.post("/api/leads/campaign-list", json={"ids": [a, s]}).json()
        assert card["confirm_required"] and card["rows"] == 1 and card["rows_without_phone"] == 1
        assert c.get("/api/leads/desk/lists").json()["lists"] == []
        done = c.post("/api/leads/campaign-list", json={"ids": [a, s], "confirm": True, "name": "Pune dentists"}).json()
        assert done["confirmed"] and done["rows"] == 1
        lists = c.get("/api/leads/desk/lists").json()
        assert [x["name"] for x in lists["lists"]] == ["Pune dentists"] and lists["lists"][0]["rows"] == 1
        tl = c.get(f"/api/leads/desk/leads/{a}").json()["timeline"]
        assert any("campaign list" in e["text"] for e in tl)


def test_quality_finds_twins_missing_phones_and_old_leads(ld):
    from app.leads import pipeline as PL
    from app.leads.models import LeadContact
    from app.db import session
    from datetime import datetime, timezone
    q = PL.quality(T)
    assert q["maybe_same_count"] == 1 and len(q["maybe_same"][0]["leads"]) == 2
    assert q["no_phone_count"] == 1 and q["no_phone"][0]["name"] == "Smile Care"
    with session() as s:
        c = s.get(LeadContact, _id(ld, "Patil Hardware"))
        c.fetched_at = datetime.now(timezone.utc) - timedelta(days=120)
    assert PL.quality(T)["untouched_count"] == 1


def test_saved_searches_never_run_a_paid_route_by_themselves(ld, monkeypatch):
    from app.leads import pipeline as PL
    from app.leads import service as S
    with pytest.raises(PL.DeskError):
        PL.save_search(T, "Pune dentists", "OFFICIAL_API", {"kinds": ["dentist"], "near": "Pune"}, weekly=True)
    PL.save_search(T, "Pune dentists", "OFFICIAL_API", {"kinds": ["dentist"], "near": "Pune"}, weekly=False)
    w = PL.save_search(T, "Nagpur steel", "REGISTRY", {"search_term": "steel suppliers", "city": "Nagpur"}, weekly=True)
    calls = []

    async def fake_im(tenant, ask, term, city="", cities=None, biztype="", place="", max_rows=200):
        calls.append(("im", term, city))
        return {"ok": True, "run": {"kept": 3}}

    async def fake_pl(*a, **k):
        calls.append(("places",))
        return {"ok": True, "run": {"kept": 0}}
    monkeypatch.setattr(S, "run_indiamart", fake_im)
    monkeypatch.setattr(S, "run_places", fake_pl)
    assert asyncio.run(PL.weekly_tick()) == 1
    assert calls == [("im", "steel suppliers", "Nagpur")]          # the paid Google search never ran by itself
    assert asyncio.run(PL.weekly_tick()) == 0                       # and not twice in a week
    sv = {x["id"]: x for x in PL.saved(T)}
    assert sv[w["id"]]["runs"] == 1 and sv[w["id"]]["last_kept"] == 3


def test_her_file_attached_in_the_chat_goes_into_the_store(ld):
    from app import chatfiles
    from app.agent.leadsdesk_tools import leads_desk
    from app.agent.tools import Ctx
    csv = "Firm,Mobile No,Town\nOm Medicals,9011022334,Pune\nOm Medicals,9011022334,Pune\nRaj Traders,,Akola\n"
    m = chatfiles.store(T, "chemists.csv", csv.encode(), "text/csv")
    r = asyncio.run(leads_desk(Ctx(T, "c1"), action="import_file", file_id=m["file_id"]))
    assert r["ok"] and r["columns_used"]["name"] == "Firm" and r["columns_used"]["phone"] == "Mobile No"
    assert r["run"]["kept"] == 2 and r["run"]["duped"] == 1
    from app.leads import service as S
    assert {x["name"] for x in S.rows(T, q="Om")["rows"]} == {"Om Medicals"}


def test_the_tool_guards(ld, env):
    from app.agent.leadsdesk_tools import leads_desk
    from app.agent.tools import Ctx, ToolError
    run = lambda ctx=None, **a: asyncio.run(leads_desk(ctx or Ctx(T, "c1"), **a))   # noqa: E731
    r = run(action="read", what="leads", stage="new")
    assert r["total"] == 4 and all("phone" not in x for x in r["leads"])   # the masked number only
    a = r["leads"][0]["id"]
    assert run(action="stage", lead_ids=[a], stage="contacted")["changed"] == 1
    assert run(action="read", what="lead", lead_id=a)["timeline"][0]["by"] == "hoola"
    with pytest.raises(ToolError):
        run(Ctx(T, "c1", actor="customer:x"), action="stage", lead_ids=[a], stage="won")
    from app.employee import hire
    hire.leave(T, "leads")
    with pytest.raises(ToolError):
        run(action="read")


def test_turn_hooks_and_admission():
    src = (ROOT / "server/app/agent/santosh.py").read_text()
    assert "_ldc.is_leads(conversation_id)" in src and "_ldc.block" in src and "adm.admit_families(_ldc.FAMILIES)" in src
    from app import leadschat
    from app.agent import admit
    assert set(leadschat.FAMILIES) <= set(admit.FAMILY_OF.values())
    assert admit.FAMILY_OF["leads_desk"] == "leadsdesk"
    assert '"leads"' in (ROOT / "server/app/callconv.py").read_text() and '"leads"' in (ROOT / "server/app/convs.py").read_text()
    assert "lead_desk_jobs" in (ROOT / "server/app/worker.py").read_text()


def test_page_and_wiring():
    from app.main import app, APP_VERSION
    c = TestClient(app)
    r = c.get("/console/leads")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers and "leadsdesk.js" in r.text
    html = (CON / "leadsdesk.html").read_text()
    for f in ("chatkit.js", "quality.js", "md.js", "mark.js", "stream.js", "seodesk.css", "leadsdesk.css", "leadsdesk.js"):
        assert f"/static/console/{f}?v={APP_VERSION}" in html, f
    js = (CON / "leadsdesk.js").read_text()
    for need in ("/api/leads/chat", "/api/leads/desk", "HoolaChat.mount", "plus: true", "quality: true", "/files`", "files,",
                 "hoola.leads.side", "dragover", "paste", "/api/leads/campaign-list", "/api/leads/desk/telecaller", "confirm: true"):
        assert need in js, need
    for tab in ("today", "find", "leads", "lists", "quality"):
        assert f"['{tab}'," in js
    assert "location.assign('/console/leads')" in (CON / "v2.js").read_text()


def test_phone_calls_the_lead_generation_employee():
    es = (ROOT / "lib/ui/employees_screen.dart").read_text()
    assert "callLeadsDesk" in es and "app.api!.leadsChat()" in es
    he = (ROOT / "lib/ui/shell/hoola_employees.dart").read_text()
    assert "callLeadsDesk(context, staff.app)" in he and "'/console/leads'" in he and "Call Lead Generation" in he
    assert "leadsChat()" in (ROOT / "lib/api.dart").read_text()


# ---------------------------------------------------------------- the page in a real browser
@pytest.fixture
def ld_server(ld, monkeypatch):
    sync_api = pytest.importorskip("playwright.sync_api")
    from tests.test_v161_console_e2e import _free_port
    from tests.test_v161_stream import KEY
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    import uvicorn
    from app import main
    port = _free_port()
    srv = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(1200):
        if srv.started:
            break
        time.sleep(0.05)
    assert srv.started
    try:
        pw = sync_api.sync_playwright().start()
        try:
            browser = pw.chromium.launch(**({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
        except Exception as e:
            pw.stop()
            pytest.skip(f"no Chromium for Playwright here: {str(e)[:80]}")
        yield f"http://127.0.0.1:{port}", browser, KEY, ld
        browser.close()
        pw.stop()
    finally:
        srv.should_exit = True
        th.join(timeout=10)


def test_lead_desk_in_a_real_browser(ld_server, tmp_path):
    base, browser, key, ids = ld_server
    shots = os.environ.get("CONSOLE_SHOTS")
    errors = []
    f = tmp_path / "chemists.csv"
    f.write_text("Name,Mobile\nOm Medicals,9011022334\n")
    a = _id(ids, "Shree Dental Clinic", "1234")
    for scheme, width in (("light", 1440), ("dark", 1440), ("light", 390)):
        ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(base + "/console/leads")
        pg.wait_for_selector("#sdTabs [data-tab='today']", timeout=20000)
        try:
            pg.wait_for_function("() => document.querySelector('#sdThread').innerText.includes('attach your own list')", timeout=20000)
        except Exception:
            raise AssertionError(f"chat empty: errors={errors} page={pg.inner_text('body')[:600]!r}")
        pg.wait_for_function("() => document.querySelector('#ldPage').innerText.includes('leads kept')", timeout=20000)
        pg.evaluate("document.querySelector('#sdChat').__keep = 1")
        for tab, want in (("find", "IndiaMART sellers"), ("leads", "Shree Dental Clinic"), ("lists", "Lists by stage"),
                          ("quality", "Maybe the same business twice"), ("today", "leads kept")):
            pg.click(f"#sdTabs [data-tab='{tab}']")
            pg.wait_for_function("(w) => document.querySelector('#ldPage').innerText.includes(w)", arg=want, timeout=10000)
            assert pg.evaluate("document.querySelector('#sdChat').__keep") == 1     # the chat stayed while the page changed
        assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "sideways scroll"
        if width == 1440 and scheme == "light":
            pg.click("#sdTabs [data-tab='leads']")
            pg.wait_for_selector(f"[data-sel='{a}']")
            pg.check(f"[data-sel='{a}']")
            pg.wait_for_selector("[data-act='bulkstage']")
            pg.select_option("#ldBulkStage", "interested")
            pg.click("[data-act='bulkstage']")
            pg.wait_for_function("() => document.querySelector('#ldPage').innerText.includes('Interested 1')", timeout=10000)
            pg.goto(base + f"/console/leads#/lead/{a}")
            pg.wait_for_function("() => document.querySelector('#ldPage').innerText.includes('What happened')", timeout=10000)
            pg.fill("#ldNoteText", "Wants a demo on Thursday")
            pg.click("#ldNote button[type=submit]")
            pg.wait_for_function("() => document.querySelector('#ldPage').innerText.includes('Wants a demo on Thursday')", timeout=10000)
            pg.click(f"[data-tele='{a}']")                               # tap 1: the card, nothing added yet
            pg.wait_for_selector("[data-confirm='tele']")
            assert "Tap 1 of 2" in pg.inner_text("#ldHand")
            pg.click("[data-act='cancelhand']")
            pg.set_input_files("#adPick", str(f))                        # + in the chat: her list is uploaded to this chat
            pg.wait_for_function("() => { const x = document.querySelector('#adFiles .ac-file'); return x && !x.classList.contains('up') && !x.classList.contains('bad'); }", timeout=15000)
            assert "chemists.csv" in pg.inner_text("#adFiles")
            pg.click("#adFiles .ac-file button")
            assert pg.evaluate("document.querySelector('#adFiles').hidden")
            pg.click("#sdSwap")
            assert pg.evaluate("document.querySelector('#sdBody').classList.contains('right')")
            pg.click("#sdSwap")
        if shots:
            Path(shots).mkdir(parents=True, exist_ok=True)
            for tab in ("today", "find", "leads", "lists", "quality"):
                pg.goto(base + f"/console/leads#/{tab}")
                time.sleep(0.8)
                pg.screenshot(path=f"{shots}/leadsdesk_{tab}_{scheme}_{width}.png", full_page=False)
        ctx.close()
    assert not errors, errors
