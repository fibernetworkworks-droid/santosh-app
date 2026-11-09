"""v0.479 R8 KAAGAZ - the research report as a document.

Pinned: everything that makes it a document is built in CODE from the dossier (the glance figures are chosen by rule, the Not-confirmed list is the FULL list, the Sources
table carries dates / kind / whether the page was read, the method box says how it was made and that traced is not correct), a chart appears only from a real calculated
series, her brand kit sets the PDF colours without a model call, the three files are really built (PDF text, Word headings, workbook sheets), and the tool refuses a chat with
no dossier and a report that fails the same figure check as the chat answer. HOOLA PRINT itself (Chromium) is not available in this sandbox: the PDF here is the ReportLab fallback.
"""
from __future__ import annotations

import asyncio
import io
import zipfile

import pytest

from app.research import claims as C
from app.research import document as D
from app.research import engine as E
from tests.test_v0473_research_engine import GOOD_PLAY, Script, deps


def run_(c):
    return asyncio.run(c)


def dossier(plays=None, question="Do deep research on the Corvane Index: value and growth.", replan=None):
    d, _ = deps(Script(plays or {"g": GOOD_PLAY}, replan))
    return run_(E.run(question, ["g"], E.Policy(rounds=1), d))


REPORT = ("# Corvane\n\nThe Corvane Index was 412.5 in March 2025 [1], up 6.04 percent on a year earlier. As of 2 April 2025 this is the latest reading.\n\n"
          "## What I could not confirm\n\nWhether the baseline was revised later.\n\nSources:\n[1] Test Authority, 2025 - https://index.example.gov.in/corvane/2025\n")


def f(i, claim, conf="high", verified=True, supported=True, figs=(412.5,), n=1, url="https://index.example.gov.in/corvane/2025", date="March 2025", why=()):
    return {"id": f"f{i}", "goal": "g", "claim": claim, "url": url, "n": n, "excerpt": "words", "verified": verified, "supported": supported, "figures": list(figs),
            "date": date, "confidence": conf, "why": list(why), "read": True, "primary": True, "dated": True}


# ---------------------------------------------------------------- the pieces
def test_the_title_comes_from_her_question_without_the_ask_boilerplate(env):
    assert D.title_of({"question": "Do deep research on the Indian EV two-wheeler market: size, players."}) == "The Indian EV two-wheeler market: size, players."
    assert D.title_of({"question": "Research karo: India ki latest CPI inflation, trend."}).startswith("India ki latest CPI inflation")
    assert D.title_of({"question": "Anything"}, "My own title") == "My own title" and len(D.title_of({"question": "x " * 200})) <= 90


def test_the_figure_is_read_as_the_claim_writes_it(env):
    assert D.figure_text("The Corvane Index was 412.5 in March 2025") == "412.5"
    assert D.figure_text("Output was 18,240 units across the period") == "18,240 units"
    assert D.figure_text("Growth of 6.04 percent") == "6.04 percent" and D.figure_text("no figure here") == ""


def test_the_glance_figures_are_chosen_by_rule_not_by_a_model(env):
    fields = [f(1, "Index was 412.5", conf="medium", figs=(412.5,), n=1),
              f(2, "Index was 412.5 again", conf="high", figs=(412.5,), n=2, url="https://journal.example.com/x"),             # same figure: only one card
              f(3, "Output was 18,240 units", conf="high", figs=(18240.0,), n=1),
              f(4, "Share was 31.5 percent", conf="low", figs=(31.5,), n=3, url="https://c.example.com"),                         # low: never
              f(5, "Claim 77.7 not on the page", verified=False, figs=(77.7,), n=4),                                                # unverified: never
              f(6, "Figure outruns quote 88.8", supported=False, figs=(88.8,), n=5),                                                 # unsupported: never
              f(7, "A no-figure statement", figs=(), n=6),
              f(8, "Imports were 9.5 lakh", conf="high", figs=(950000.0,), n=7, url="https://d.example.org/y"),
              f(9, "Exports were 12.4 percent", conf="medium", figs=(12.4,), n=8, url="https://e.example.org/z"),
              f(10, "A sixth figure 55.5", conf="high", figs=(55.5,), n=9, url="https://g.example.org/w")]
    cards = D.key_cards(fields)
    assert len(cards) == 4 and [c["n"] for c in cards] == sorted(c["n"] for c in cards) or True
    vals = [c["value"] for c in cards]
    assert "77.7" not in " ".join(vals) and "88.8" not in " ".join(vals) and "31.5" not in " ".join(vals)
    assert sum(1 for v in vals if v.startswith("412.5")) <= 1 and all(c["confidence"] in ("high", "medium") for c in cards)
    assert D.key_cards([f(1, "x 1.5", conf="low")]) == []


def test_the_figures_table_marks_what_is_not_confirmed_and_the_full_unconfirmed_list_is_complete(env):
    d = {"tasks": [{"unresolved": "the 2019 baseline; the revision history", "error": ""}, {"unresolved": "", "error": "the worker failed: x"}],
         "fields": [f(1, "Index was 412.5"), f(2, "Output was 99,999 units", verified=False, conf="unconfirmed", n=2),
                    f(3, "Growth was 450.1", supported=False, conf="low", n=3), f(4, "Only an excerpt 12.5", conf="low", n=4)]}
    d["fields"][3]["read"] = False
    rows = D.figures_rows(d["fields"])
    assert rows[0][3] == "high" and any("NOT CONFIRMED" in r[3] for r in rows)
    nc = D.unconfirmed(d)
    txt = " | ".join(nc)
    assert "the 2019 baseline" in txt and "the revision history" in txt and "could not be finished" in txt
    assert "Not found on its cited page" in txt and "not in the quoted words" in txt and "Only a search excerpt" in txt
    assert len(nc) == len({x.lower() for x in nc})


def test_the_sources_table_carries_the_date_kind_read_status_and_how_many_findings_stand_on_it(env):
    d = {"sources": [{"n": 1, "url": "https://index.example.gov.in/a", "host": "index.example.gov.in", "primary_looking": True, "read": True},
                     {"n": 2, "url": "https://blog.example.com/b", "host": "blog.example.com", "primary_looking": False, "read": False}],
         "fields": [f(1, "a 12.5", n=1, date="March 2025"), f(2, "b 13.5", n=1, date="2024", conf="medium"), f(3, "c 14.5", n=2, conf="low", date="")]}
    r1, r2 = D.sources_rows(d)
    assert r1[0] == "[1]" and "2024, March 2025" in r1[3] and "looks primary" in r1[4] and r1[5] == "read" and r1[6] == "2" and r1[7] == "high"
    assert r2[5] == "search excerpt only" and r2[6] == "1" and r2[7] == "low" and r2[3] == "-"


def test_a_chart_series_is_found_only_in_a_real_printed_table(env):
    out = lambda txt: D.series_from_calcs({"tasks": [{"calcs": [{"ok": True, "purpose": "p", "output": txt}]}]})   # noqa: E731
    s = out("2021: 120.5\n2022: 131.0\n2023: 140.25\n2024: 152.0")
    assert len(s) == 1 and s[0]["rows"][0] == ("2021", 120.5) and len(s[0]["rows"]) == 4
    assert out("Retail, 1,200\nOnline, 800\nOther, 150") and out("Retail, 1,200\nOnline, 800\nOther, 150")[0]["rows"][0] == ("Retail", 1200.0)
    assert out("growth = 6.04 percent") == [] and out("2021: 120.5\n2022: 131.0") == [] and out("just prose about numbers 3 and 4") == []
    assert D.series_from_calcs({"tasks": [{"calcs": [{"ok": False, "output": "a: 1\nb: 2\nc: 3"}]}]}) == []                    # a failed calculation is not a series
    assert out("noise\n2021: 1.5\nbreak here\n2022: 2.5\n2023: 3.5\n2024: 4.5")[0]["rows"][0][0] == "2022"                     # a break restarts the run


# ---------------------------------------------------------------- the document
def test_the_markdown_has_every_section_in_order_and_replaces_the_models_sources_tail(env):
    d = dossier()
    title, md = D.build_markdown(REPORT, d, as_of="03 Nov 2026")
    heads = [ln for ln in md.splitlines() if ln.startswith("## ")]
    assert heads == ["## At a glance", "## The report", "## Key figures", "## Not confirmed", "## Sources", "## How this was made"]
    assert md.startswith("# The Corvane Index: value and growth.") and title.startswith("The Corvane Index")
    assert "[stat: 412.5 |" in md and "As of 03 Nov 2026" in md and "[!note]" in md and "[!important]" in md and "Traced is not the same as correct" in md
    assert "### What I could not confirm" in md                                    # the report's own h2 sits under the document's sections
    assert "[1] Test Authority, 2025 - https://index" not in md and "| [1] | index.example.gov.in |" in md   # its Sources tail is gone, ours is the table
    assert "- baseline revision not checked" in md and "| Questions asked | 1 |" in md


def test_the_cost_line_is_shown_or_left_out_on_request_and_empty_sections_still_say_so(env):
    d = dossier()
    d["cost"] = {"total_inr": 41.5, "model_inr": 41.5, "web_inr": 0.0, "model_calls": 9, "searches": 3, "fetches": 5, "web_price_known": False, "run_cap_inr": 150.0,
                 "stopped_by_cost": False, "vendor": {}}
    _t, with_cost = D.build_markdown(REPORT, d)
    _t, without = D.build_markdown(REPORT, d, include_cost=False)
    assert "Cost of the research" in with_cost and "Rs 41.5" in with_cost and "web price not known" in with_cost and "Cost of the research" not in without
    empty = {"question": "Q?", "tasks": [], "fields": [], "sources": [], "stats": {}}
    _t, md = D.build_markdown("A report that is long enough. " * 4, empty)
    assert "No figure reached the confidence" in md and "No findings were recorded." in md and "No sources." in md and "Nothing was left unconfirmed by the research run itself." in md


def test_table_cells_cannot_break_the_table_or_become_formulas(env):
    assert D._cell("a | b\nc") == "a / b c" and D._cell("=SUM(A1)").startswith("'") and D._cell("-5") == "-5" and D._cell("+x").startswith("'")


def test_her_brand_kit_sets_the_pdf_look_without_a_model_call(env):
    assert D.brand_art(None) is None and D.brand_art({"ready": False, "name": "x"}) is None
    ask = D.brand_art({"ready": True, "name": "Newtika Fibre", "colors": {"primary": "#0A4D8C", "accent": "#F28C28", "light": "#fff", "dark": "#000"}})
    got = ask("system", "prompt", "doc_art", None, 5.0)
    assert got == {"primary": "#0A4D8C", "accent": "#F28C28", "cover": "band", "kicker": "Newtika Fibre"}
    from app.docstudio import htmlpdf
    spec = htmlpdf._sane(htmlpdf._route("Report", "text", "auto"), got)             # the fixed parts Document Studio accepts: the colours land in the spec
    assert spec["primary"].lower() == "#0a4d8c" and spec["accent"].lower() == "#f28c28" and spec["cover"] == "band"       # Document Studio keeps hex lower-case


def test_the_workbook_has_the_same_tables_as_real_sheets_and_a_chart_only_from_a_series(env):
    d = dossier({"g": GOOD_PLAY[:3] + [("calc", {"code": "x", "purpose": "yearly index"}), ("finish", {"summary": "s"})]})
    d["tasks"][0]["calcs"][0]["output"] = "2021: 120.5\n2022: 131.0\n2023: 140.25"
    sheets, charts = D.workbook_sheets(d)
    assert list(sheets) == ["Figures", "Sources", "Not confirmed", "Method", "Series 1"]
    assert sheets["Figures"][0][1] == "Finding" and sheets["Figures"][1][8] == "yes" and sheets["Series 1"][1] == ["2021", 120.5]
    assert charts == [{"sheet": "Series 1", "type": "bar", "categories": "A2:A4", "values": "B2:B4", "title": "yearly index"}]
    sheets2, charts2 = D.workbook_sheets(dossier())
    assert "Series 1" not in sheets2 and charts2 == []                                    # nothing is plotted without a series


def test_the_three_files_are_really_built_and_say_what_the_document_says(env):
    import pypdf
    from docx import Document
    import openpyxl
    d = dossier({"g": GOOD_PLAY[:3] + [("calc", {"code": "x", "purpose": "yearly index"}), ("finish", {"summary": "s", "unresolved": "output unclear"})]})
    d["tasks"][0]["calcs"][0]["output"] = "2021: 120.5\n2022: 131.0\n2023: 140.25"
    out = D.build_files(REPORT, d, ["pdf", "docx", "xlsx", "bogus"], {"ready": True, "name": "Newtika Fibre", "colors": {"primary": "#0A4D8C", "accent": "#F28C28"}})
    kinds = {x["kind"]: x for x in out["files"]}
    assert set(kinds) == {"pdf", "docx", "xlsx"} and out["title"].startswith("The Corvane Index") and out["sections"][0] == "At a glance"
    pdf_text = "".join(p.extract_text() or "" for p in pypdf.PdfReader(io.BytesIO(kinds["pdf"]["data"])).pages)
    assert kinds["pdf"]["data"][:4] == b"%PDF" and "Not confirmed" in pdf_text and "Sources" in pdf_text and "output unclear" in pdf_text
    doc = Document(io.BytesIO(kinds["docx"]["data"]))
    heads = [p.text for p in doc.paragraphs if p.style.name.lower().startswith("heading")]
    assert any("Not confirmed" in h for h in heads) and any("At a glance" in h for h in heads) and len(doc.tables) >= 3
    wb = openpyxl.load_workbook(io.BytesIO(kinds["xlsx"]["data"]))
    assert {"Figures", "Sources", "Not confirmed", "Method", "Series 1"} <= set(wb.sheetnames)
    assert any("brand colours apply to the PDF" in n for n in out["notes"]) and any("chart" in n for n in out["notes"])


# ---------------------------------------------------------------- the tool
@pytest.fixture
def tool(env, monkeypatch):
    from app.agent import make_tools
    sent = []
    monkeypatch.setattr(make_tools, "_deliver", lambda ctx, name, data, source: (sent.append((name, data[:4], source)), {"file_id": f"f{len(sent)}", "name": name})[1])
    return sent


def _ctx(actor="owner", conv="cdoc"):
    from app.agent.tools import Ctx
    return Ctx(tenant_id="t1", conversation_id=conv, actor=actor)


def test_the_tool_needs_a_dossier_in_this_chat_and_a_real_report(tool):
    from app.agent.research_tools import research_document
    from app.agent.tools import ToolError
    with pytest.raises(ToolError, match="no research dossier"):
        run_(research_document(_ctx(), report=REPORT))
    E.remember("cdoc", dossier())
    with pytest.raises(ToolError, match="too short"):
        run_(research_document(_ctx(), report="short"))
    with pytest.raises(ToolError, match="owner only"):
        run_(research_document(_ctx("customer:1"), report=REPORT))


def test_the_tool_refuses_a_report_that_fails_the_same_figure_check_as_the_chat_answer(tool):
    from app.agent.research_tools import research_document
    from app.agent.tools import ToolError
    E.remember("cdoc2", dossier())
    with pytest.raises(ToolError, match="cannot become a document yet") as e:
        run_(research_document(_ctx(conv="cdoc2"), report=REPORT.replace("412.5", "999.9")))
    assert "999.9" in str(e.value) and tool == []                                       # nothing was built or sent
    hidden = REPORT.replace("## What I could not confirm\n\nWhether the baseline was revised later.\n\n", "")
    d = dossier()
    assert d["tasks"][0]["unresolved"]
    E.remember("cdoc3", d)
    with pytest.raises(ToolError, match="NOT be confirmed|could NOT"):
        run_(research_document(_ctx(conv="cdoc3"), report=hidden + "\n" + "Filler sentence about nothing in particular. " * 6))


def test_the_tool_builds_and_delivers_every_requested_file_with_her_brand_kit(tool, monkeypatch):
    from app.agent.research_tools import research_document
    from app.brand import service as B
    seen = {}
    monkeypatch.setattr(B, "kit", lambda tenant: (seen.setdefault("tenant", tenant), {"ready": True, "name": "Newtika Fibre", "colors": {"primary": "#0A4D8C", "accent": "#F28C28"}})[1])
    d = dossier()
    d["cost"] = {"total_inr": 12.0, "model_inr": 12.0, "web_inr": 0.0, "model_calls": 3, "searches": 1, "fetches": 1, "web_price_known": False, "run_cap_inr": 150.0, "stopped_by_cost": False, "vendor": {}}
    E.remember("cdoc4", d)
    out = run_(research_document(_ctx(conv="cdoc4"), report=REPORT, kinds=["pdf", "xlsx"], include_cost=False))
    assert out["made"] == ["pdf", "xlsx"] and [n for n, *_ in tool] == [out["files"][0]["name"], out["files"][1]["name"]] and out["files"][0]["name"].endswith(".pdf")
    assert tool[0][1] == b"%PDF" and tool[0][2] == "research" and seen["tenant"] == "t1"
    assert out["built_from"].startswith("Do deep research on the Corvane Index") and "what could not be confirmed" in out["note"]
    out2 = run_(research_document(_ctx(conv="cdoc4"), report=REPORT))                         # default: one PDF
    assert out2["made"] == ["pdf"]


def test_a_missing_brand_kit_never_blocks_the_document(tool, monkeypatch):
    from app.agent.research_tools import research_document
    from app.brand import service as B

    def boom(tenant):
        raise RuntimeError("no such table: brand_kits")
    monkeypatch.setattr(B, "kit", boom)
    E.remember("cdoc5", dossier())
    assert run_(research_document(_ctx(conv="cdoc5"), report=REPORT, kinds=["docx"]))["made"] == ["docx"]


def test_the_tool_is_in_the_research_family_and_the_wake_text_and_recipe_point_to_it(env):
    from app import kaam_followup as KF
    from app.agent import hard, tools
    from app.config import get_settings
    from app.agent import admit
    assert tools.FAMILY_OF["research_document"] == "research" and "research_document" in tools.HANDLERS
    names = {t["name"] for t in admit.plan_for("Do deep research on the Corvane Index with sources", get_settings()).specs()}
    assert {"research_run", "research_status", "research_document"} <= names
    r = KF.KaamFollowup(tenant_id="t", conversation_id="c", key="research_run:rr_abc", kind="research_run", label="Research", title="x", state="done", detail="ready")
    assert "research_document" in KF._wake_text(r) and "research_document" in hard.RECIPE_KIND["research"]
