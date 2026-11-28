"""v0.999.193 GOOGLE DOCS, THE LAST 9: on the same stand-in Docs engine - whole-table delete, row height, cell
borders / padding / vertical alignment; links to a heading / tab / bookmark; moving text with its looks; one part
of the document in its own section (landscape, margins, columns); first-page / even-page headers (Google's API
makes only the main one: said); dropdown options changed / a dropdown removed; replies edited / deleted, a
suggestion withdrawn; named ranges and pictures removed; suggestions read in detail and equations said plainly."""
import pytest

from app.agent.tools import ToolError
from tests.test_drive import d  # noqa: F401  (fixture)
from tests.test_v0999_192_docs_complete import DOC, g, run, styled, tap  # noqa: F401


def calls(g, kind):
    return [c[kind] for c in g.docs.calls if isinstance(c, dict) and kind in c]


def test_tables_delete_height_cells(g):
    run("gdoc_table", doc=DOC, action="insert", rows=[["Item", "Price"], ["Router", "1200"]], where="end")
    run("gdoc_table", doc=DOC, action="row_height", table=1, row="1", height="1.5 cm", keep_together=True)
    rh = calls(g, "updateTableRowStyle")[-1]
    assert rh["rowIndices"] == [0] and rh["fields"] == "minRowHeight,preventOverflow"
    assert round(rh["tableRowStyle"]["minRowHeight"]["magnitude"]) == 43
    run("gdoc_table", doc=DOC, action="cell_style", table=1, border_width="0", border_sides="left,right",
        padding="4 pt", valign="middle")
    cs = calls(g, "updateTableCellStyle")[-1]
    assert "tableStartLocation" in cs and set(cs["fields"].split(",")) == {
        "borderLeft", "borderRight", "paddingTop", "paddingBottom", "paddingLeft", "paddingRight", "contentAlignment"}
    assert cs["tableCellStyle"]["borderLeft"]["width"]["magnitude"] == 0          # Google: width 0 hides a border
    assert cs["tableCellStyle"]["contentAlignment"] == "MIDDLE"
    run("gdoc_table", doc=DOC, action="cell_style", table=1, row=1, column=2, border_color="blue", border_width="2",
        border_style="dashed")
    cs = calls(g, "updateTableCellStyle")[-1]
    assert cs["tableRange"]["tableCellLocation"]["columnIndex"] == 1 and cs["tableCellStyle"]["borderTop"]["dashStyle"] == "DASH"
    with pytest.raises(ToolError, match="valign"):
        run("gdoc_table", doc=DOC, action="cell_style", table=1, valign="sideways")
    out = run("gdoc_table", doc=DOC, action="delete", table=1)
    assert out["table_deleted"] == 1 and "[T" not in g.docs.text("doc1")
    run("gdoc_table", doc=DOC, action="insert", rows=[["Note"], ["x" * 400]], where="end")
    res = run("gdoc_table", doc=DOC, action="delete", table=1)
    assert res["status"] == "needs_approval" and "[T" in g.docs.text("doc1")
    tap(g)
    assert "[T" not in g.docs.text("doc1")


def test_links_inside_the_document(g):
    run("gdoc_edit", doc=DOC, action="link_inside", find="Pay in 30 days", to_heading="Prices")
    assert all(s.get("link") == {"heading": {"id": "h.prices", "tabId": "t.0"}} for s in styled(g, "doc1", "Pay in"))
    run("gdoc_edit", doc=DOC, action="link_inside", find="Router", to_bookmark="id.abc123")
    assert styled(g, "doc1", "Router")[0]["link"] == {"bookmark": {"id": "id.abc123", "tabId": "t.0"}}
    with pytest.raises(ToolError, match="cannot make or list bookmarks"):
        run("gdoc_edit", doc=DOC, action="link_inside", find="Router")


def test_move_keeps_words_and_looks(g):
    run("gdoc_edit", doc=DOC, action="style", find="Pay in", bold=True)
    run("gdoc_edit", doc=DOC, action="move", heading="Terms", where="before:Prices")
    paras = [p for p, _ in g.docs.paras("doc1")]
    assert paras.index("Terms") < paras.index("Prices") and paras.count("Terms") == 1
    assert paras.index("Pay in 30 days.") == paras.index("Terms") + 1
    assert dict(g.docs.paras("doc1"))["Terms"]["namedStyleType"] == "HEADING_1"   # its heading look moved too
    assert all(s.get("bold") for s in styled(g, "doc1", "Pay in"))
    run("gdoc_edit", doc=DOC, action="move", find="with care", where="end")
    assert g.docs.paras("doc1")[-1][0] == "with care" and "😀 ." in g.docs.text("doc1")
    run("gdoc_table", doc=DOC, action="insert", rows=[["A"], ["B"]], where="after:Router costs")
    with pytest.raises(ToolError, match="cannot copy tables"):
        run("gdoc_edit", doc=DOC, action="move", heading="Prices", where="start")
    with pytest.raises(ToolError, match="inside the part"):
        run("gdoc_edit", doc=DOC, action="move", heading="Terms", where="before:Pay in")


def test_one_part_in_its_own_section(g):
    out = run("gdoc_layout", doc=DOC, part_heading="Prices", orientation="landscape", margins="1 cm")
    assert "flipPageOrientation" in out["changed_for_that_part"] and "Section breaks" in out["notes"][0]
    toks = g.docs.docs["doc1"]["tabs"][0]["body"].toks
    sbs = [t for t in toks if t.k == "sb"]
    assert len(sbs) == 2 and all(t.obj["sectionType"] == "NEXT_PAGE" for t in sbs)
    assert sbs[0].obj.get("flipPageOrientation") is True and "flipPageOrientation" not in sbs[1].obj
    info = run("gdoc_read", doc=DOC, what="info")
    assert len(info["sections"]) == 3 and info["sections"][1]["landscape"]
    run("gdoc_layout", doc=DOC, section=3, columns=2)
    assert len(g.docs.docs["doc1"]["tabs"][0]["body"].toks[-1:]) == 1
    assert [t for t in g.docs.docs["doc1"]["tabs"][0]["body"].toks if t.k == "sb"][1].obj["columnProperties"]
    with pytest.raises(ToolError, match="section 1 to 3"):
        run("gdoc_layout", doc=DOC, section=9, columns=2)


def test_first_and_even_page_headers(g):
    out = run("gdoc_layout", doc=DOC, header="FNW", header_first="Cover page")
    st = g.docs.docs["doc1"]["tabs"][0]["style"]
    assert st["useFirstPageHeaderFooter"] is True and "header" in out["changed"]
    assert "can make only the main header" in out["notes"][0]          # said, not faked
    # once she starts the first-page header in Docs, Hoola fills it
    from tests.fakedocs import Seg
    tab = g.docs.docs["doc1"]["tabs"][0]
    tab["headers"]["kix.first"] = Seg("\n")
    st["firstPageHeaderId"] = "kix.first"
    out = run("gdoc_layout", doc=DOC, header_first="Cover page")
    assert "first-page header" in out["changed"]
    assert "".join(t.ch for t in tab["headers"]["kix.first"].toks).startswith("Cover page")


def test_dropdowns_edit_and_remove(g):
    run("gdoc_edit", doc=DOC, action="dropdown", after="Prices", options=["Draft", "Sent", "Paid"], selected="Sent")
    chip = run("gdoc_read", doc=DOC, what="info")["dropdown_chips"][0]
    out = run("gdoc_edit", doc=DOC, action="dropdown_edit", dropdown=chip["id"], options=["Draft", "Paid", "Overdue"],
              replace_with="Draft", title="Payment")
    up = calls(g, "updateDropdownDefinitionProperties")[-1]
    names = [o["displayValue"] for o in up["dropdownDefinitionProperties"]["options"]]
    assert names == ["Draft", "Paid", "Overdue"] and up["fields"] == "title,options"
    assert list(up["selectedOptionIdReplacements"].values()) == [up["dropdownDefinitionProperties"]["options"][0]["optionId"]]
    assert "Sent" in out["note"]
    run("gdoc_edit", doc=DOC, action="dropdown_remove", dropdown=chip["id"])
    assert run("gdoc_read", doc=DOC, what="info")["dropdown_chips"] == []
    assert not g.docs.docs["doc1"]["tabs"][0]["ddefs"]                 # its last chip gone -> the definition too


def test_replies_withdraw_names_pictures(g):
    run("gdoc_comments", doc=DOC, action="add", find="30 days", text="45?")
    tap(g)
    c = run("gdoc_comments", doc=DOC)["comments"][0]
    run("gdoc_comments", doc=DOC, action="reply", comment=c["id"], text="Let me check")
    tap(g)
    r = run("gdoc_comments", doc=DOC)["comments"][0]["replies"][0]
    run("gdoc_comments", doc=DOC, action="edit_reply", comment=c["id"], post=r["id"], text="Checked: 45 is fine")
    assert run("gdoc_comments", doc=DOC)["comments"][0]["replies"][0]["says"] == "Checked: 45 is fine"
    res = run("gdoc_comments", doc=DOC, action="delete_reply", comment=c["id"], post=r["id"])
    assert res["status"] == "needs_approval" and g.cards[-1][1].title == "Delete this reply?"
    tap(g)
    assert run("gdoc_comments", doc=DOC)["comments"][0]["replies"] == []
    run("gdoc_write", doc=DOC, markdown="A line she may not want.", suggest=True)
    sid = run("gdoc_comments", doc=DOC, action="suggestions")["suggestions"][0]["id"]
    run("gdoc_comments", doc=DOC, action="withdraw", suggestion=sid)
    assert "A line she may not want." not in g.docs.text("doc1")
    run("gdoc_edit", doc=DOC, action="named_range", find="Pay in 30 days", name="terms")
    out = run("gdoc_edit", doc=DOC, action="delete_named_range", name="terms")
    assert "text it covered stays" in out["note"] and "Pay in 30 days" in g.docs.text("doc1")
    tab = g.docs.docs["doc1"]["tabs"][0]
    tab.setdefault("pos", {})["kix.float1"] = {"objectId": "kix.float1", "positionedObjectProperties": {
        "embeddedObject": {"title": "Stamp"}}}
    assert run("gdoc_read", doc=DOC, what="info")["floating_pictures"][0]["title"] == "Stamp"
    run("gdoc_edit", doc=DOC, action="delete_picture", picture="kix.float1")
    assert not tab["pos"]


def test_suggestions_in_detail_and_equations(g):
    run("gdoc_edit", doc=DOC, action="style", find="Router costs", bold=True, suggest=True)
    run("gdoc_edit", doc=DOC, action="delete", find=" with care", suggest=True)
    sugs = {s["id"]: s for s in run("gdoc_comments", doc=DOC, action="suggestions")["suggestions"]}
    assert "bold on for 'Router costs'" in sugs["suggest.look1"]["looks"]
    assert sugs["suggest.del1"]["removes"] == " with care"
    text = run("gdoc_read", doc=DOC)["text"]
    assert "[- with care-]" in text and "(has a suggested change)" in text
    from tests.fakedocs import Tok
    toks = g.docs.docs["doc1"]["tabs"][0]["body"].toks
    toks.insert(1, Tok("o", obj={"equation": {}}))
    assert "Google's API does not give its content" in run("gdoc_read", doc=DOC)["text"]
