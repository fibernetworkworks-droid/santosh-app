"""v0.439 LONG CARD (long-task report item 0b): the set is valid, the end-state reader reads real files, the scorer
tells finished / false done / false stuck / stopped-by-a-cap apart, pass^k is strict, a real run_turn is judged on
what it left behind, the card cleans up, and the live server's goal sweeps never touch the card's tenants."""
import asyncio

import pytest

import app.agent.santosh as santosh
from app.quality import long_asks, longcard as LC


def run(coro):
    return asyncio.run(coro)


# ---------------- the set

def test_the_set_is_valid_and_has_25_asks_with_three_needs_her():
    assert LC.check_set() == []
    assert len(long_asks.ASKS) == 25
    assert sum(1 for a in long_asks.ASKS if a.get("needs_her")) == 3
    assert long_asks.SET_V == "long-1"


def test_check_set_catches_broken_asks():
    bad = [{"id": "x", "text": "t", "checks": [{"file": "exe"}]},
           {"id": "x", "text": "", "checks": []},
           {"id": "y", "text": "t", "checks": [{"reply": True, "words": ["a"], "min": 3}]},
           {"id": "z", "text": "t", "needs_her": True, "checks": [{"reply": True}]},
           {"id": "w", "text": "t", "checks": [{"reply": True, "file": "pdf"}]}]
    out = "\n".join(LC.check_set(bad))
    for frag in ("unknown file kind exe", "id twice", "no text", "no checks", "min 3 > 1", "needs-her", "exactly one"):
        assert frag in out


# ---------------- reading real files

def _pdf(path, lines, link=None, pages=2):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(path), pagesize=A4)
    for p in range(pages):
        y = 800
        for ln in lines:
            c.drawString(50, y, ln)
            y -= 20
        if link and p == 0:
            c.linkURL(link, (50, 500, 300, 520))
        c.showPage()
    c.save()


def test_read_file_pdf_xlsx_docx_pptx(tmp_path):
    p = tmp_path / "r.pdf"
    _pdf(p, ["Ola Electric 30%", "Ather 15%", "TVS 20%"], link="https://example.com/a", pages=3)
    r = LC.read_file(str(p), "pdf")
    assert r["ok"] and r["pages"] == 3 and "Ather" in r["text"] and "https://example.com/a" in r["links"]

    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["city", "rent", "link"])
    for c in ("Mumbai", "Pune", "Bengaluru"):
        ws.append([c, 30000, f"https://x.in/{c}"])
    x = tmp_path / "r.xlsx"
    wb.save(x)
    r = LC.read_file(str(x), "xlsx")
    assert r["ok"] and r["rows"] == 3 and len(r["links"]) == 3          # header row not counted

    import docx
    d = docx.Document()
    d.add_paragraph("PAN card and Aadhaar for a proprietor")
    t = d.add_table(rows=1, cols=1)
    t.rows[0].cells[0].text = "Partnership deed"
    w = tmp_path / "r.docx"
    d.save(w)
    r = LC.read_file(str(w), "docx")
    assert r["ok"] and "Partnership deed" in r["text"]

    from pptx import Presentation
    pr = Presentation()
    for i in range(6):
        s = pr.slides.add_slide(pr.slide_layouts[1])
        s.shapes.title.text = f"Chai Adda slide {i}"
    pp = tmp_path / "r.pptx"
    pr.save(pp)
    r = LC.read_file(str(pp), "pptx")
    assert r["ok"] and r["slides"] == 6 and "Chai Adda" in r["text"]

    assert LC.read_file(str(tmp_path / "missing.pdf"), "pdf")["ok"] is False
    junk = tmp_path / "junk.pdf"
    junk.write_bytes(b"not a pdf at all")
    assert LC.read_file(str(junk), "pdf")["ok"] is False                 # a file she cannot open is not a file


# ---------------- judging + scoring (pure)

def _ev(**kw):
    base = {"files": [], "artifacts": [], "lists": {}, "reminders": [], "routines": [], "memory": [],
            "replies": [], "tools": [], "tools_ok": []}
    base.update(kw)
    return base


def test_judge_file_checks_pages_rows_words_and_links(tmp_path):
    ask = long_asks.by_id("ev_pdf")
    p = tmp_path / "ev.pdf"
    _pdf(p, ["Ola", "Ather", "TVS"], pages=1)                         # 1 page < 2
    ev = _ev(files=[{"name": "ev.pdf", "kind": "pdf", "path": str(p), "size": 1}])
    rows = LC.judge(ask, ev)
    assert rows[0]["ok"] is False and "1 pages < 2" in rows[0]["why"]
    _pdf(p, ["Ola", "Ather", "TVS"], pages=3)
    assert LC.judge(ask, ev)[0]["ok"] is True
    _pdf(p, ["Ola only"], pages=3)
    assert "words 1/3" in LC.judge(ask, ev)[0]["why"]
    assert "no pdf file delivered" in LC.judge(ask, _ev())[0]["why"]

    news = long_asks.by_id("rbi_news_pdf")
    _pdf(p, ["repo rate 5.5", "inflation 3%", "https://rbi.org.in/x", "https://a.com/y"], pages=1)
    assert "2 links < 3" in LC.judge(news, ev)[0]["why"]


def test_judge_lists_reminders_routines_memory_reply_tools_and_pages():
    rows = LC.judge(long_asks.by_id("diwali_list"),
                    _ev(lists={"diwali": list("abcdefg")}, reminders=["mithai", "safai"]))
    assert [r["ok"] for r in rows] == [True, False]                    # 7 items ok, 2 < 3 reminders
    rows = LC.judge(long_asks.by_id("remember_and_list"),
                    _ev(memory=["Naam Meghana, Akola"], lists={"ghoomna list": list("abcde")}))
    assert all(r["ok"] for r in rows)                                  # list name matched inside a longer name
    assert LC.judge(long_asks.by_id("market_routine"),
                    _ev(routines=["Monday market"], replies=["Nifty 25,100 par band hua"]))[0]["ok"]
    three = long_asks.by_id("three_facts")
    assert LC.judge(three, _ev(replies=["Akola 31°C, USD 88.4, Sensex 82,100"]))[0]["ok"]
    assert LC.judge(three, _ev(replies=["Akola garam hai, dollar mehnga, Sensex upar"]))[0]["why"] == "too few numbers"
    phones = long_asks.by_id("phones_compare")
    assert not LC.judge(phones, _ev(replies=["iPhone, Samsung, Pixel - Pixel lijiye"]))[0]["ok"]   # no table
    assert LC.judge(phones, _ev(replies=["| Phone | Price |\n| iPhone | 79k |\n| Galaxy | 75k |\n| Pixel | 70k |"]))[0]["ok"]
    cpi = long_asks.by_id("cpi_mospi")
    assert LC.judge(cpi, _ev(tools=["mospi"], tools_ok=[]))[0]["ok"] is False      # it ran but failed = not used
    assert LC.judge(cpi, _ev(tools=["mospi"], tools_ok=["mospi"]))[0]["ok"] is True
    page = long_asks.by_id("bakery_page")
    assert not LC.judge(page, _ev(artifacts=[{"title": "Meetha Ghar", "status": "building", "text": "Meetha Ghar Akola"}]))[0]["ok"]
    assert LC.judge(page, _ev(artifacts=[{"title": "Meetha Ghar", "status": "ready", "text": "Meetha Ghar, Akola"}]))[0]["ok"]


def test_asked_her_needs_a_question_and_nothing_made():
    ask = long_asks.by_id("ask_cab")
    assert LC.judge(ask, _ev(replies=["Kis time pickup chahiye aur kahan se?"]))[0]["ok"]
    assert LC.judge(ask, _ev(replies=["Ho gaya."]), waiting_on_her=True)[0]["ok"]            # a waiting card counts
    assert LC.judge(ask, _ev(replies=["Done."]), goal={"status": "blocked", "hold": ""})[0]["ok"]
    assert not LC.judge(ask, _ev(replies=["Cab book ho gayi, 8 baje aayegi."]))[0]["ok"]       # invented
    made = _ev(replies=["Kaunsa time?"], files=[{"name": "x.pdf", "kind": "pdf", "path": "", "size": 1}])
    assert "made 1" in LC.judge(ask, made)[0]["why"]


def test_score_run_tells_the_four_outcomes_apart():
    ask = long_asks.by_id("ev_pdf")
    ok, bad = [{"check": "file", "ok": True, "why": ""}], [{"check": "file", "ok": False, "why": ""}]
    v = LC.score_run(ask, ok, {"status": "done"}, "done", False, False)
    assert v["passed"] and v["claimed_done"] and not v["false_done"]
    v = LC.score_run(ask, bad, {"status": "done"}, "done", False, False)
    assert v["false_done"] and not v["passed"]                          # "ho gaya" with no file
    v = LC.score_run(ask, bad, None, "done", False, False)
    assert v["false_done"]                                              # no goal: the turn's own claim counts
    v = LC.score_run(ask, bad, {"status": "blocked", "hold": ""}, "partial", False, False)
    assert v["false_stuck"] and not v["cap_stopped"]                    # asked her for nothing
    v = LC.score_run(long_asks.by_id("ask_cab"), bad, {"status": "blocked", "hold": ""}, "", False, False)
    assert not v["false_stuck"]                                         # needs-her ask: stopping is right
    v = LC.score_run(ask, bad, {"status": "blocked", "hold": "limit"}, "partial", False, False)
    assert v["cap_stopped"] and not v["false_stuck"]
    assert LC.score_run(ask, bad, {"status": "working"}, "", True, False)["cap_stopped"]       # card clock
    assert LC.score_run(ask, bad, None, "stopped", False, True)["cap_stopped"]                 # turn timeout


def test_summarise_pass_hat_k_is_strict_and_rupees_per_finished():
    runs = []
    for i, (aid, ok, inr) in enumerate([("a", True, 50), ("a", True, 50), ("a", True, 50),
                                        ("b", True, 80), ("b", False, 80), ("b", True, 80)]):
        runs.append({"id": aid, "k": i % 3 + 1, "passed": ok, "false_done": not ok, "false_stuck": False,
                     "cap_stopped": False, "inr": inr, "minutes": 5})
    s = LC.summarise(runs, 3)
    assert s["finished_pct"] == 83 and s["false_done_pct"] == 17
    assert s["pass_at_k_pct"] == 100 and s["pass_hat_k_pct"] == 50     # b failed once -> not reliable
    assert s["inr_total"] == 390 and s["inr_per_finished"] == 78.0
    lines = "\n".join(LC.lines({"set": "long-1", "version": "x", "status": "done", "summary": s,
                                "runs": [dict(r, checks=[{"check": "file", "ok": False, "why": "no pdf"}],
                                              goal_status="done", outcome="done", error="") for r in runs]}))
    assert "pass^3 50%" in lines and "FALSE DONE" in lines and "no pdf" in lines


# ---------------- the end state read from the database + a real run_turn

def test_evidence_reads_files_lists_reminders_replies_and_steps(env, tmp_path):
    from app.db import Event, ListItem, Message, PcFile, Reminder, Routine, now, session
    tenant = LC.PREFIX + "t1"
    conv = LC._new_conv(tenant)
    f = tmp_path / "plan.xlsx"
    from openpyxl import Workbook
    wb = Workbook()
    wb.active.append(["day"])
    wb.active.append([1])
    wb.save(f)
    with session() as s:
        s.add(PcFile(id="file_lc1", tenant_id=tenant, device_id="", direction="to_phone", name="plan.xlsx",
                     size=f.stat().st_size, sha256="x", stored_path=str(f)))
        s.add(ListItem(tenant_id=tenant, list_name="Diwali", text="diye"))
        s.add(Reminder(tenant_id=tenant, conversation_id=conv, text="mithai", due_at=now()))
        s.add(Routine(tenant_id=tenant, conversation_id=conv, title="market", instruction="x", next_run=now()))
        s.add(Message(conversation_id=conv, role="assistant", content="Excel bana diya", display="Excel bana diya"))
        s.add(Event(conversation_id=conv, kind="step", payload={"id": "s1", "tool": "doc_studio", "state": "done"}))
        s.add(Event(conversation_id=conv, kind="step", payload={"id": "s2", "tool": "mospi", "state": "error"}))
    ev = LC.evidence(tenant, conv)
    assert ev["files"][0]["kind"] == "xlsx" and ev["lists"] == {"diwali": ["diye"]}
    assert ev["reminders"] == ["mithai"] and ev["routines"] == ["market"]
    assert ev["replies"] == ["Excel bana diya"]
    assert ev["tools"] == ["doc_studio", "mospi"] and ev["tools_ok"] == ["doc_studio"]
    LC._cleanup(tenant)                                                  # nothing the card made fires later
    ev2 = LC.evidence(tenant, conv)
    assert ev2["reminders"] == [] and ev2["routines"] == []


def _brain_says(text):
    async def fake_brain(brain, system, history, settings, tools=None, live=None, max_tokens=None):
        return [{"type": "text", "text": text}], "end_turn"
    return fake_brain


def test_run_one_judges_a_real_turn_on_what_it_left_behind(env, monkeypatch):
    monkeypatch.setattr(santosh, "_call_brain", _brain_says("Pickup kis time aur kis jagah se chahiye?"))
    r = run(LC.run_one(long_asks.by_id("ask_cab"), 1, "t", max_min=2))
    assert r["passed"] is True and r["tenant"].startswith(LC.PREFIX) and r["error"] == ""
    assert r["checks"][0]["check"] == "asked_her"

    monkeypatch.setattr(santosh, "_call_brain", _brain_says("Electric scooter ki report yeh rahi: Ola, Ather, TVS."))
    r = run(LC.run_one(long_asks.by_id("ev_pdf"), 1, "t", max_min=2))
    assert r["passed"] is False and "no pdf file delivered" in r["checks"][0]["why"]


# ---------------- the live server never runs the card's jobs a second time

@pytest.mark.parametrize("sweep", ["recover_tick", "resume_tick"])
def test_goal_sweeps_skip_card_tenants(env, monkeypatch, sweep):
    from datetime import timedelta

    from app.agent import goal as G
    from app.db import now, session
    assert G.CARD_PREFIX == LC.PREFIX
    tenant = LC.PREFIX + "sweep"
    conv = LC._new_conv(tenant)
    view = G.set_goal(tenant, conv, "card job", ["a", "b"])
    with session() as s:
        r = s.get(G.GoalRun, view["id"])
        r.updated_at = now() - timedelta(minutes=30)
        if sweep == "resume_tick":
            r.paused_at = now() - timedelta(minutes=5)
    scheduled = []
    monkeypatch.setattr(G, "_schedule", lambda *a, **k: scheduled.append(a) or True)
    assert getattr(G, sweep)() == 0 and scheduled == []
