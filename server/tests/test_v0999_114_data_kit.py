"""v0.999.114 ULTIMATE PC PLAN P3 - data without clicking: Hoola PC reads xlsx / csv / docx / pdf as data, writes cells
and tables into a workbook, fills a Word template, and reads every table of a page (both PCs) - real files, real page."""
from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "desktop-linux"))
import datakit as DK  # noqa: E402

from tests.test_v0999_93_ultimate_p1 import _do, _Fake, chrome_page  # noqa: F401,E402


def _agent(tmp_path, monkeypatch):
    monkeypatch.setenv("HOOLA_DATA", str(tmp_path / "data"))
    spec = importlib.util.spec_from_file_location("hoola_agent_p3", ROOT / "desktop-linux" / "agent.py")
    a = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(a)
    a.DOWNLOADS.mkdir(parents=True, exist_ok=True)
    return a


def test_sheets_round_trip(tmp_path, monkeypatch):
    a = _agent(tmp_path, monkeypatch)
    act = a.Actions()
    w = act.do_sheet_write("orders.xlsx", rows=[["Invoice", "Amount"], ["INV-1", 1200.5], ["INV-2", 99]], new=True, sheet="Orders")
    assert w["written"] == 6 and w["sheet"] == "Orders"
    act.do_sheet_write("orders.xlsx", cells={"C1": "Paid", "C2": "yes"}, sheet="Orders")
    r = act.do_data_read("orders.xlsx")
    assert r["kind"] == "sheet" and r["sheets"][0]["rows"][:2] == [["Invoice", "Amount", "Paid"], ["INV-1", 1200.5, "yes"]]
    (a.DOWNLOADS / "x.csv").write_text("name,city\nAna,Madrid\n")
    assert act.do_data_read("x.csv")["sheets"][0]["rows"] == [["name", "city"], ["Ana", "Madrid"]]
    with pytest.raises(a.ActionError, match="cell address"):
        act.do_sheet_write("orders.xlsx", cells={"not a cell": 1})
    with pytest.raises(a.ActionError, match="No such file"):
        act.do_data_read("missing.xlsx")


def test_word_template_is_filled_and_pdf_read(tmp_path, monkeypatch):
    import docx
    a = _agent(tmp_path, monkeypatch)
    act = a.Actions()
    d = docx.Document()
    d.add_paragraph("Dear {{Name}}, your order [Order No] ships on {{ Date }}.")
    t = d.add_table(rows=1, cols=2)
    t.cell(0, 0).text = "Total"
    t.cell(0, 1).text = "{{Total}}"
    d.save(str(a.DOWNLOADS / "letter.docx"))
    r = act.do_doc_fill("letter.docx", values={"name": "Lena Fischer", "Order No": "A-77", "total": "EUR 1,100.25"})
    assert r["filled"] == ["Name", "Order No", "Total"] and r["left_blank"] == ["Date"]
    got = act.do_data_read(Path(r["path"]).name)
    assert "Dear Lena Fischer, your order A-77 ships on {{ Date }}." in got["text"] and got["tables"][0] == [["Total", "EUR 1,100.25"]]
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(a.DOWNLOADS / "inv.pdf"))
    c.drawString(72, 720, "Invoice INV-2026-004 total EUR 1,100.25")
    c.save()
    p = act.do_data_read("inv.pdf")
    assert p["kind"] == "pdf" and "INV-2026-004" in p["text"] and not p["scanned"]
    with pytest.raises(a.ActionError, match="not a file I read as data"):
        (a.DOWNLOADS / "a.exe").write_bytes(b"MZ")
        act.do_data_read("a.exe")


def test_page_tables_on_a_real_page(chrome_page):  # noqa: F811
    act, open_, ref, recs = chrome_page
    open_("invoices")
    t = act.do_page_tables()["tables"]
    from app import practice
    assert t and t[0]["rows"][0] == ["Invoice", "Customer", "Amount", "Status"] and len(t[0]["rows"]) == len(practice.INVOICES) + 1


def test_operator_lines_and_tools():
    from app.pc import operator as O
    hoola = {t["name"] for t in O.HOOLA_TOOLS}
    assert {"data_read", "sheet_write", "doc_fill", "page_tables"} <= hoola
    assert not {"data_read", "sheet_write", "doc_fill", "page_tables"} & {t["name"] for t in O.TOOLS}
    out = _do("page_tables", {}, _Fake({"title": "Invoices", "tables": [{"caption": "", "rows": [["A", "B"], ["1", "2"]]}]}))
    assert "Table 1 - 2 rows:" in out and "1 | 2" in out and "WEBSITE'S data" in out
    out = _do("data_read", {"path": "a.xlsx"}, _Fake({"name": "a.xlsx", "kind": "sheet", "sheets": [{"name": "S", "n_rows": 1, "rows": [["x", 1]]}]}))
    assert "Sheet 'S' - 1 rows:" in out and "x | 1" in out
    out = _do("doc_fill", {"template": "t.docx", "values": {}}, _Fake({"filled": ["Name"], "left_blank": ["Date"], "path": "/data/Downloads/t-filled.docx"}))
    assert "still blank: Date" in out
    assert "older than sheet_write" in _do("sheet_write", {"path": "a.xlsx"}, _Fake(exc=RuntimeError("Unknown action: sheet_write")))


def test_shipping():
    assert "datakit.py" in (ROOT / "desktop-linux" / "Dockerfile").read_text()
    req = (ROOT / "desktop-linux" / "requirements.txt").read_text()
    assert "openpyxl" in req and "python-docx" in req and "pdfplumber" in req
    assert "tables: () =>" in (ROOT / "desktop" / "ext" / "hoola-extension" / "pagekit.js").read_text()
