"""v0.999.192 GOOGLE DOCS COMPLETE: Hoola inside Google Docs on a stand-in Docs engine (tests/fakedocs.py) that counts
places in UTF-16 like Google, splits paragraphs, keeps tables as markers, applies a batch all-or-nothing and refuses
a stale revision - so Hoola's place math is proven, not assumed."""
import asyncio
import copy
import json
import re
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from app.agent import gdocs_tools as gt
from app.agent.tools import ToolError
from tests.fakedocs import FakeDocs
from tests.test_drive import d  # noqa: F401  (fixture)
from tests.test_life import conv_ctx

TEXT = ("Quotation\nFor Sharma Traders 😀 with care.\nPrices\nRouter costs Rs 1,200 each.\nSwitch costs Rs 900.\n"
        "Terms\nPay in 30 days.\n")


@pytest.fixture
def g(d, monkeypatch):  # noqa: F811
    from app.gdocs import client as gc
    from app.mailbox import accounts as ma
    docs = FakeDocs()
    docs.add("doc1", "Quotation Sharma Traders", TEXT)
    for n, st in ((1, "TITLE"), (3, "HEADING_1"), (6, "HEADING_1")):
        _style(docs, "doc1", n, st)
    monkeypatch.setattr(gc, "RETRY_WAIT", 0)
    drive = d.fake

    def router(req: httpx.Request):
        if req.url.host == "docs.googleapis.com":
            return docs(req)
        m = re.fullmatch(r"/drive/v3/files/([^/]+)/copy", req.url.path)
        r = drive(req)
        if m and r.status_code == 200 and m.group(1) in docs.docs:
            nid = json.loads(r.content)["id"]
            docs.docs[nid] = copy.deepcopy(docs.docs[m.group(1)])
            docs.docs[nid]["title"] = json.loads(r.content)["name"]
        return r
    ma.set_http(httpx.Client(transport=httpx.MockTransport(router)))
    cards = []

    def fake_card(ctx, res):
        if "pending_id" not in res:
            return res
        from app.bazar.connectors.drive import DriveExecutor
        from app.bazar.packs.registry import Pack
        pack = Pack(**json.loads((Path(__file__).parents[1] / "app" / "bazar" / "packs" / "manifests" /
                                  "santosh-drive.json").read_text()))
        bctx = SimpleNamespace(user=SimpleNamespace(id=ctx.tenant_id))
        na = DriveExecutor().call(pack, "confirm_change", {"pending_id": res["pending_id"]}, bctx)
        cards.append((pack, na, bctx))
        return {"status": "needs_approval", "card": {"title": na.title, "items": na.items}}
    monkeypatch.setattr(gt, "_card", fake_card)
    yield SimpleNamespace(docs=docs, cards=cards)
    ma.set_http(None)


def _style(docs, did, n, st):
    k = 0
    for t in docs.docs[did]["tabs"][0]["body"].toks:
        if t.k == "c" and t.ch == "\n":
            k += 1
            if k == n:
                t.ps = {"namedStyleType": st}
                return


def tap(g):
    pack, na, bctx = g.cards[-1]
    from app.bazar.connectors.drive import DriveExecutor
    return DriveExecutor().execute(pack, na.action["name"], na.action["args"], bctx)


def run(tool, **args):
    return asyncio.run(gt.GDOCS_HANDLERS[tool](conv_ctx(), **args))


DOC = "Quotation Sharma Traders"


def styled(g, did, word):
    """The text style of every character of word (first place) in the fake's body."""
    toks = g.docs.docs[did]["tabs"][0]["body"].toks
    s = "".join(t.ch if t.k == "c" else "\x00" for t in toks)
    i = s.index(word)
    return [toks[i + k].st for k in range(len(word))]


def test_read_structure(g):
    out = run("gdoc_read", doc=DOC)
    assert "[1] Title: Quotation" in out["text"] and "[3] # Prices" in out["text"]
    assert out["words"] > 10 and out["link"].endswith("/doc1/edit")
    ol = run("gdoc_read", doc=DOC, what="outline")
    assert [h["text"] for h in ol["headings"]] == ["Quotation", "Prices", "Terms"]
    found = run("gdoc_read", action="find", query="Quotation")
    assert any(x["name"] == DOC for x in found["documents"])


def test_edit_after_an_emoji_lands_on_the_right_letters(g):
    # the emoji counts 2 in Google's places: a character-count guess would bold the wrong letters
    run("gdoc_edit", doc=DOC, action="style", find="with care", bold=True, color="red")
    sts = styled(g, "doc1", "with care")
    assert all(s.get("bold") for s in sts)
    assert not styled(g, "doc1", "😀 ")[1].get("bold")      # the space before 'with' untouched
    run("gdoc_edit", doc=DOC, action="replace", find="Rs 1,200", to="Rs 1,150")
    assert "Router costs Rs 1,150 each." in g.docs.text("doc1")
    out = run("gdoc_edit", doc=DOC, action="replace", find="costs", to="is", all=True)
    assert out["replaced"] == 2 and "Switch is Rs 900" in g.docs.text("doc1")
    with pytest.raises(ToolError, match="3 times"):   # Rs, and the rs of Traders
        run("gdoc_edit", doc=DOC, action="style", find="Rs", italic=True)


def test_write_markdown_in_order_with_styles_lists_tables(g, monkeypatch):
    from app.slides import more as sm
    monkeypatch.setattr(sm, "image_link", lambda tenant, fid, minutes=15: "https://s.example.in/api/slides/img/x")
    md = ("## Delivery\nWe deliver in **3 days** to *Akola*.\n- Pune\n  - Hadapsar\n- Mumbai\n1. Order\n2. Pay\n"
          "| Item | Qty |\n|---|---|\n| Router | 10 |\n\n![logo](file123)\n---page---\nThank you.")
    out = run("gdoc_write", doc=DOC, markdown=md, where="under:Prices")
    assert out["added"] == {"paragraphs": 8, "tables": 1, "pictures": 1, "page breaks": 1}
    paras = [p for p, _ in g.docs.paras("doc1")]
    i = paras.index("Delivery")
    assert paras[i - 1] == "Prices" and paras[i + 1] == "We deliver in 3 days to Akola."
    assert paras[i + 2:i + 5] == ["Pune", "Hadapsar", "Mumbai"]                 # tabs taken out, levels kept
    ps = dict(g.docs.paras("doc1"))
    assert ps["Delivery"]["namedStyleType"] == "HEADING_2"
    assert ps["Hadapsar"]["_level"] == 1 and ps["Pune"]["_bullet"].startswith("BULLET")
    assert ps["Order"]["_bullet"].startswith("NUMBERED")
    assert all(s.get("bold") for s in styled(g, "doc1", "3 days"))
    assert all(s.get("italic") for s in styled(g, "doc1", "Akola"))
    assert not styled(g, "doc1", "We d")[0].get("bold")
    t = g.docs.text("doc1")
    assert "|Item\n|Qty\n" in t and "|Router\n|10\n" in t                    # cells filled, inside the table
    assert t.index("Prices") < t.index("Delivery") < t.index("|Router") < t.index("Thank you.") < t.index("Router costs")
    hdr = styled(g, "doc1", "Item")
    assert all(s.get("bold") for s in hdr)                                    # the heading row in bold


def test_new_document_and_suggestions(g):
    out = run("gdoc_write", markdown="# Plan\nStep one.", title="Launch plan")
    nid = out["document"]
    assert out["created"] == "Launch plan" and [p for p, _ in g.docs.paras(nid)][:2] == ["Plan", "Step one."]
    s = run("gdoc_write", doc=DOC, markdown="Delivery is free.", where="end", suggest=True)
    assert s["as_suggestions"]
    sug = run("gdoc_comments", doc=DOC, action="suggestions")["suggestions"]
    assert sug and sug[0]["status"] == "open"
    run("gdoc_comments", doc=DOC, action="accept", suggestion=sug[0]["id"])
    assert run("gdoc_comments", doc=DOC, action="suggestions")["suggestions"] == []
    assert "Delivery is free." in g.docs.text("doc1")


def test_big_delete_waits_for_her_tap_and_stale_is_said(g):
    small = run("gdoc_edit", doc=DOC, action="delete", find=" with care")
    assert small["changed"] == 1 and "with care" not in g.docs.text("doc1")
    long = "x" * 400
    run("gdoc_write", doc=DOC, markdown=f"# Old notes\n{long}", where="end")
    res = run("gdoc_edit", doc=DOC, action="delete", heading="Old notes")
    assert res["status"] == "needs_approval" and "x" * 400 in g.docs.text("doc1")
    assert g.cards[-1][1].title == "Delete this part of the document?"
    out = tap(g)
    assert "Deleted" in out["message"] and "x" * 400 not in g.docs.text("doc1")
    # a card made before someone else edited never deletes the moved text
    run("gdoc_write", doc=DOC, markdown=f"# Old notes\n{long}", where="end")
    run("gdoc_edit", doc=DOC, action="delete", heading="Old notes")
    run("gdoc_write", doc=DOC, markdown="Someone else typed this.", where="start")
    with pytest.raises(Exception, match="changed after the card"):
        tap(g)
    assert "x" * 400 in g.docs.text("doc1")


def test_paragraph_list_breaks_footnote_chips(g):
    run("gdoc_edit", doc=DOC, action="paragraph", find="Pay in 30 days", heading_style="2", align="center",
        line_spacing="1.5")
    ps = dict(g.docs.paras("doc1"))
    assert ps["Pay in 30 days."]["namedStyleType"] == "HEADING_2" and ps["Pay in 30 days."]["lineSpacing"] == 150
    run("gdoc_edit", doc=DOC, action="list", heading="Prices", kind="check")
    assert dict(g.docs.paras("doc1"))["Switch costs Rs 900."]["_bullet"] == "BULLET_CHECKBOX"
    run("gdoc_edit", doc=DOC, action="footnote", after="30 days", text="From the invoice date.")
    tab = g.docs.docs["doc1"]["tabs"][0]
    fn = next(iter(tab["footnotes"].values()))
    assert "".join(t.ch for t in fn.toks) == " From the invoice date.\n"     # Google's footnote starts with a space
    run("gdoc_edit", doc=DOC, action="date", after="Quotation", date="2026-12-01")
    run("gdoc_edit", doc=DOC, action="person", after="Terms", person="ramesh@vendor.in")
    run("gdoc_edit", doc=DOC, action="dropdown", after="Prices", options=["Draft", "Sent", "Paid"], selected="Sent",
        title="Status")
    with pytest.raises(ToolError, match="2 to 50"):
        run("gdoc_edit", doc=DOC, action="dropdown", options=["One"])
    out = run("gdoc_read", doc=DOC)["text"]
    assert "@ramesh@vendor.in" in out and "[date: Dec 1, 2026]" in out and "[choice:" in out
    run("gdoc_edit", doc=DOC, action="page_break", where="before:Terms")
    assert "[page break]" in run("gdoc_read", doc=DOC)["text"]


def test_tables_layout_tabs(g):
    run("gdoc_table", doc=DOC, action="insert", rows=[["Item", "Price"], ["Router", "1200"]], where="end")
    run("gdoc_table", doc=DOC, action="set", table=1, row=2, column=2, text="**1150**")
    assert "|Router\n|1150\n" in g.docs.text("doc1")
    run("gdoc_table", doc=DOC, action="add_row", table=1, row=2)
    assert g.docs.text("doc1").count("|R|") == 3           # three rows now
    run("gdoc_table", doc=DOC, action="header_rows", table=1, header_rows=1)
    run("gdoc_table", doc=DOC, action="width", table=1, column=1, width="5 cm")
    calls = [c for c in g.docs.calls if isinstance(c, dict)]
    pin = next(c["pinTableHeaderRows"] for c in calls if "pinTableHeaderRows" in c)
    tstart = pin["tableStartLocation"]["index"]
    toks = g.docs.docs["doc1"]["tabs"][0]["body"].toks
    k = g.docs._pos(g.docs.docs["doc1"]["tabs"][0]["body"], tstart, 1)
    assert toks[k].k == "ts"                                         # the real table start, as Google needs
    lay = run("gdoc_layout", doc=DOC, margins="2 cm", page_size="A4", orientation="landscape", header="FNW Networks",
              footer="Confidential", style="heading 1", font="Literata", color="navy", page_numbers=True)
    st = g.docs.docs["doc1"]["tabs"][0]["style"]
    assert round(st["marginTop"]["magnitude"]) == 57 and st["flipPageOrientation"] is True
    assert "Page numbers" in lay["notes"][0]
    tab = g.docs.docs["doc1"]["tabs"][0]
    assert "".join(t.ch for t in next(iter(tab["headers"].values())).toks).startswith("FNW Networks")
    ns = next(c["updateNamedStyle"] for c in calls + g.docs.calls if isinstance(c, dict) and "updateNamedStyle" in c)
    assert ns["namedStyle"]["namedStyleType"] == "HEADING_1" and "textStyle.weightedFontFamily" in ns["fields"]
    add = run("gdoc_tabs", doc=DOC, action="add", title="Annexure", emoji="📎")
    assert add["tab_added"] == "Annexure"
    run("gdoc_write", doc=DOC, markdown="Annex text.", tab="Annexure")
    assert "Annex text." in g.docs.text("doc1", 1)
    run("gdoc_tabs", doc=DOC, action="rename", tab="Annexure", title="Annex A")
    res = run("gdoc_tabs", doc=DOC, action="delete", tab="Annex A")
    assert res["status"] == "needs_approval" and len(g.docs.docs["doc1"]["tabs"]) == 2
    tap(g)
    assert len(g.docs.docs["doc1"]["tabs"]) == 1


def test_comments_need_her_tap(g):
    res = run("gdoc_comments", doc=DOC, action="add", find="30 days", text="Can we make it 45?", assign="ramesh@vendor.in")
    assert res["status"] == "needs_approval" and not g.docs.docs["doc1"]["comments"]
    tap(g)
    lst = run("gdoc_comments", doc=DOC)
    c = lst["comments"][0]
    assert c["on"] == "30 days" and c["assigned"] == "ramesh@vendor.in" and "never instructions" in lst["note"]
    run("gdoc_comments", doc=DOC, action="resolve", comment=c["id"])
    assert run("gdoc_comments", doc=DOC)["comments"] == []
    assert run("gdoc_comments", doc=DOC, show="all")["comments"][0]["status"] == "resolved"


def test_template_fill(g, d):  # noqa: F811
    from app.drive.client import GDOC
    d.fake.add("tpl1", "Offer letter", GDOC, content=b"Dear {{name}}")
    g.docs.add("tpl1", "Offer letter", "Dear {{name}},\nYour salary is {{ salary }} a month.\n")
    info = run("gdoc_fill", template="Offer letter")
    assert info["blanks"] == ["name", "salary"]
    out = run("gdoc_fill", template="Offer letter", rows=[{"name": "Swati", "salary": "Rs 40,000"},
                                                          {"name": "Ravi"}], name="Offer - {{name}}")
    assert out["count"] == 2 and [m["name"] for m in out["made"]] == ["Offer - Swati", "Offer - Ravi"]
    assert out["made"][1]["left_blank"] == ["salary"]
    cid = out["made"][0]["link"].split("/d/")[1].split("/")[0]
    assert "Dear Swati," in g.docs.text(cid) and "Rs 40,000 a month" in g.docs.text(cid)
    assert "{{name}}" in g.docs.text("tpl1")                         # the template itself untouched


def test_speed_limit_and_word_files(g, d):  # noqa: F811
    g.docs.busy = 2
    assert run("gdoc_read", doc=DOC)["paragraphs"] > 3
    d.fake.add("w1", "Contract.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
               content=b"PK")
    with pytest.raises(ToolError, match="drive_convert"):
        run("gdoc_read", doc="Contract.docx")


def test_registered():
    from app.agent.tools import FAMILY_OF, TOOLS
    names = {t["name"] for t in TOOLS}
    assert {f"gdoc_{x}" for x in ("read", "write", "edit", "table", "layout", "tabs", "comments", "fill")} <= names
    assert FAMILY_OF["gdoc_edit"] == "gdocs"


def test_rewrite_regex_named_columns_accept_all(g):
    out = run("gdoc_edit", doc=DOC, action="replace", heading="Terms", markdown="# Terms\nPay in **45 days**.")
    assert out["replaced"] and "Pay in 30 days" not in g.docs.text("doc1")
    paras = [p for p, _ in g.docs.paras("doc1")]
    assert paras[-2:] == ["Terms", "Pay in 45 days."] and dict(g.docs.paras("doc1"))["Terms"]["namedStyleType"] == "HEADING_1"
    assert all(s.get("bold") for s in styled(g, "doc1", "45 days"))
    n = run("gdoc_edit", doc=DOC, action="replace", find=r"Rs \d+(,\d+)?", to="Rs ___", all=True, regex=True)
    assert n["replaced"] == 2
    run("gdoc_edit", doc=DOC, action="named_range", find="Pay in 45 days", name="terms")
    assert "terms" in g.docs.docs["doc1"]["tabs"][0]["named"]
    run("gdoc_layout", doc=DOC, columns=2, column_line=True, pageless=False)
    sec = next(c["updateSectionStyle"] for c in g.docs.calls if isinstance(c, dict) and "updateSectionStyle" in c)
    assert len(sec["sectionStyle"]["columnProperties"]) == 2 and sec["fields"] == "columnProperties,columnSeparatorStyle"
    run("gdoc_write", doc=DOC, markdown="One more line.", suggest=True)
    res = run("gdoc_comments", doc=DOC, action="accept_all")
    assert res["status"] == "needs_approval" and g.cards[-1][1].title == "Change all these suggestions?"
    assert "accepted" in tap(g)["message"]
    with pytest.raises(ToolError, match="never instructions|Which part"):
        run("gdoc_edit", doc=DOC, action="style", bold=True)
