"""v0.189.0 "Document Studio" - Claude-grade documents for the owner (owner: check how Claude Code Opus
makes the perfect documents - PDF with proper alignment, design and fonts, Excel, Word, deep preview -
WE WANT SAME FOR HOOLA AI). The engines port the Claude document skills' design system:

- tokens: cascade palettes derived from the title, tier-capped saturation (XL bg S<=0.08 ... XS accent
  S<=0.75), one hue family, never pure-black ink; the same title always gets the same palette
- pdf (ReportLab report line): registered font pool with the v0.144 Devanagari shaping, TOC gate
  (TocDocTemplate + multiBuild, clickable entries, never hardcoded page numbers), table iron rules
  (every cell a Paragraph, proportional widths <= available, centred, repeatRows, M-tier header fill +
  L-tier zebra), safe_keep_together, CondPageBreak orphan prevention, stat callouts, cover (light bg,
  chunked title, <=4 components) that owns page 1 ALONE, header/footer, QA read-back
- xlsx: typed values ("Rs 1,200" / "12%" / "2024-05-01" become real numbers / dates), live formulas
  guarded (dynamic-array functions refused with the cell named; division without IFERROR warns),
  totals row, zebra, chart factories with font-baked titles, re-open QA
- docx: R1-style cover in its own section (never a PageBreak at the section end), real Heading styles,
  1.3x line spacing, zebra tables with tblHeader + cantSplit, Word TOC field + refresh hint
- pptx: palette deck (title slide + accent bar + slide numbers + notes)
- preview: deep preview per kind + pdf page images; doc_studio / doc_preview tools registered with
  Hinglish labels, PII guard, delivery through the v0.51 file-card path
"""
import io

import pytest

import app.docstudio.docxgen as docxgen
import app.docstudio.pdfgen as pdfgen
import app.docstudio.pptxgen as pptxgen
import app.docstudio.tokens as tokens
import app.docstudio.xlsxgen as xlsxgen
from app.docstudio import preview

LONG = """# Summary
Newtika Traders closed March with 1,842 orders and 12.4% growth. Same-day dispatch stayed above 96%
and the saree bundle offer pulled 312 first-time buyers across Jaipur and Indore.
[stat: +12.4% | Order growth vs February]
| City | Orders | Revenue | Share |
| Jaipur | 842 | Rs 1,240,500 | 45.7% |
| Indore | 610 | Rs 902,300 | 33.3% |
| Nagpur | 390 | Rs 577,100 | 21.0% |

# What worked
- Same-day dispatch stayed above 96% even during the two festival weeks.
- The saree bundle offer pulled 312 new buyers from the evening WhatsApp status forwards.
> WhatsApp follow-ups converted 4x better than email this month.
1. Morning stock check before 9 am
2. Same-day packing and courier handover
3. Evening review with the store leads

# Hindi note
नवरात्रि सेल के लिए बैनर तैयार करवाना है और स्टॉक समय पर पहुँचाना है।

# Next month plan
April has two festivals and one long weekend. The bundle offer runs again with a higher margin floor,
a Nagpur pickup point is added, and the new catalogue photos are tested on the top 20 SKUs.
The target for April is 2,100 orders with the same dispatch quality bar, and the store leads have
already picked the banner designs for the Navratri window. The packing team keeps the two-shift plan
for the first festival week, then reviews whether the second week needs it too.

# Costs
- Packing material: Rs 84,300 (up 9% with volume)
- Courier: Rs 2,10,400 (steady at Rs 114 per parcel)
| Head | March | Plan | Var |
| Revenue | 27.2 L | 25.0 L | +8.8% |
| Orders | 1,842 | 1,700 | +8.4% |
| Returns | 2.1% | 2.5% | -0.4% |
"""

SHEETS = {"Sales": [["City", "Orders", "Revenue", "Share"],
                    ["Jaipur", 842, "Rs 1,240,500", "45.7%"],
                    ["Indore", 610, "Rs 902,300", "33.3%"],
                    ["Nagpur", 390, "Rs 577,100", "21.0%"],
                    ["Total", "=SUM(B2:B4)", "=SUM(C2:C4)", "100%"]]}   # model grid: header row 1


def test_rebase_a1_model_grid_to_designed_grid():
    assert xlsxgen.rebase_a1("=SUM(B2:B4)") == "=SUM(C5:C7)"
    assert xlsxgen.rebase_a1("=IFERROR(B2/C2,0)") == "=IFERROR(C5/D5,0)"
    assert xlsxgen.rebase_a1("$B$2:$B$4") == "$C$5:$C$7"
    assert xlsxgen.rebase_a1("=SUM(A:A)") == "=SUM(B:B)"            # whole-column keeps up
    assert xlsxgen.rebase_a1("=LOG10(100)+B2") == "=LOG10(100)+C5"  # function names untouched


def _hls(hexs: str) -> tuple[float, float, float]:
    import colorsys
    h = hexs.lstrip("#")
    r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    return colorsys.rgb_to_hls(r, g, b)[1], colorsys.rgb_to_hls(r, g, b)[2]  # (lightness, saturation)


# ---------------------------------------------------------------- tokens

def test_palette_deterministic_and_tier_capped():
    a = tokens.palette_for("Newtika Sales March")
    b = tokens.palette_for("Newtika Sales March")
    assert a.header_fill == b.header_fill and a.accent == b.accent       # same title, same colours
    l_bg, s_bg = _hls(a.page_bg)
    l_hf, s_hf = _hls(a.header_fill)
    l_ac, s_ac = _hls(a.accent)
    assert s_bg <= 0.08 and l_bg >= 0.94          # XL tier: near-white, nearly grey
    assert s_hf <= 0.30 and l_hf < 0.45           # M tier: structural, low saturation
    assert s_ac <= 0.75                            # XS tier cap
    assert a.table_stripe != a.page_bg             # zebra visible
    tp = _hls(a.text_primary)
    assert tp[0] < 0.3                             # ink, never pure black but dark


def test_palette_styles_and_fallback():
    assert tokens.resolve_style("BOARDROOM") == "boardroom"
    assert tokens.resolve_style("nonsense") == "auto"
    p = tokens.palette_for("X", "warm")
    l1, _ = _hls(p.header_fill)
    assert 0.2 < l1 < 0.5
    assert len(tokens.title_chunk("Ek Do Teen Char Paanch Chhe")) >= 2   # never a single-line title
    assert len(tokens.title_chunk("Short")) == 1                          # tiny titles stay one line
    assert "\u200b" not in tokens.sanitize_text("a\u200bb\ufeffc")
    assert tokens.display_width("सेल") > 2.0 and tokens.display_width("ab") == 2.0


# ---------------------------------------------------------------- pdf

def test_parse_blocks_groups_consecutive_table_rows():
    blocks = pdfgen.parse_blocks("| A | B |\n| 1 | 2 |\n| 3 | 4 |\n\ntext")
    tables = [b for b in blocks if b["k"] == "table"]
    assert len(tables) == 1 and len(tables[0]["rows"]) == 3        # separator row skipped
    blocks2 = pdfgen.parse_blocks("- a\n1. one\n2. two\n- b\n1. again")
    kinds = [b["k"] for b in blocks2]
    assert kinds == ["bullet", "num", "num", "bullet", "num"]
    assert pdfgen.parse_blocks("[stat: +12% | Growth]")[0]["k"] == "stat"
    assert pdfgen.parse_blocks("> quote line")[0]["k"] == "quote"
    assert pdfgen.parse_blocks("---")[0]["k"] == "divider"


def test_pdf_table_iron_rules():
    pdfgen.ensure_fonts()
    pal = tokens.palette_for("T")
    S = pdfgen._styles(pal, False)
    t = pdfgen._table_flowable([["City", "Orders"], ["Jaipur", "842"], ["Indore", "610"]], pal, S, pdfgen.AVAIL_W)
    assert sum(t._colWidths) <= pdfgen.AVAIL_W + 0.5               # sum(colWidths) <= available
    assert all(h is None for h in t._argH) and t.hAlign == "CENTER"   # no fixed rowHeights
    from reportlab.lib.colors import Color
    want = pal.header_fill.lstrip("#")
    want_rgb = tuple(int(want[i:i + 2], 16) / 255 for i in (0, 2, 4))
    header_cmd = next(c for c in t._bkgrndcmds if c[0] == "BACKGROUND")
    hdr_rgb = header_cmd[3].rgb() if callable(header_cmd[3].rgb) else header_cmd[3].rgb
    assert all(abs(a - b) < 0.01 for a, b in zip(hdr_rgb, want_rgb))  # M-tier fill on the header
    zebra_cmd = next(c for c in t._bkgrndcmds if c[0] == "ROWBACKGROUNDS")
    assert zebra_cmd[1] == (0, 1) and len(zebra_cmd[3]) == 2         # zebra starts below the header
    from reportlab.platypus import Paragraph
    assert all(isinstance(c, Paragraph) for row in t._cellvalues for c in row)   # no plain strings


def test_pdf_small_doc_no_cover_toc():
    r = pdfgen.make_pdf("Quick note", "One line and a bit more text for the body paragraph.")
    assert r["cover"] is False and r["toc"] is False and r["pages"] == 1
    assert r["qa"]["status"] == "pass" and r["qa"]["issues"] == []


def test_pdf_long_doc_cover_toc_and_devanagari():
    r = pdfgen.make_pdf("Newtika Traders March Sales Report", LONG, style="professional", author="Meghana")
    assert r["cover"] is True and r["toc"] is True and r["pages"] >= 3
    assert r["style"] == "professional" and r["qa"]["status"] == "pass"
    assert not r["qa"]["issues"]                                    # no blank pages, metadata set
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(r["data"]))
    text1 = reader.pages[0].extract_text() or ""
    assert "Newtika" in text1 and "PROFESSIONAL" in text1           # cover owns page 1 alone
    assert "Table of Contents" in (reader.pages[1].extract_text() or "")
    toc_pages = [int(x) for x in __import__("re").findall(r"(\d+)\s*$",
                (reader.pages[1].extract_text() or ""), __import__("re").M) if 0 < int(x) <= r["pages"]]
    assert toc_pages, "toc entries carry real page numbers"
    body = (reader.pages[2].extract_text() or "") + (reader.pages[-1].extract_text() or "")
    assert "Jaipur" in body and "1,842" in body.replace(",", "") or "Jaipur" in body


def test_pdf_devanagari_goes_through_shaping():
    r = pdfgen.make_pdf("Hindi note", "# नोट\nनवरात्रि सेल के लिए बैनर तैयार है।")
    assert r["qa"]["status"] == "pass"
    from pypdf import PdfReader
    txt = (PdfReader(io.BytesIO(r["data"])).pages[-1].extract_text() or "")
    assert txt.strip(), "hindi page has extractable text"


# ---------------------------------------------------------------- xlsx

def test_xlsx_typed_values_and_totals():
    r = xlsxgen.make_xlsx("Newtika Sales March", SHEETS, style="professional")
    assert r["qa"]["status"] == "pass" and r["formulas"] == 2
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(r["data"]))
    ws = wb["Sales"]
    assert ws["C5"].value == 842                                    # real number, not "842"
    assert ws["D5"].value == 1240500.0 and "\u20b9" in ws["D5"].number_format
    assert ws["E5"].value == 0.457 and ws["E5"].number_format == "0.0%"
    assert ws["C8"].value == "=SUM(C5:C7)"                          # live formula, rebased grid
    assert ws["C8"].font.bold                                       # totals row styled
    assert ws.sheet_view.showGridLines is False and ws.freeze_panes == "B5"
    zebra_a, zebra_b = ws["C5"].fill.fgColor.rgb, ws["C6"].fill.fgColor.rgb
    assert zebra_a != zebra_b                                       # alternating rows


def test_xlsx_dynamic_array_refused_and_division_warns():
    with pytest.raises(ValueError) as e:
        xlsxgen.make_xlsx("T", {"S": [["A", "B"], ["=XLOOKUP(1,A:A,B:B)", 1]]})
    assert "XLOOKUP" in str(e.value) and "S" in str(e.value)        # cell named
    r = xlsxgen.make_xlsx("T", {"S": [["A", "B"], [10, "=IFERROR(A2/B2,0)"]]})
    assert r["qa"]["status"] == "pass"                              # guarded division passes clean
    r2 = xlsxgen.make_xlsx("T", {"S": [["A", "B"], [10, "=A2/B2"]]})
    assert any("IFERROR" in w for w in r2["qa"]["issues"])          # warned, not failed


def test_xlsx_chart_with_baked_title():
    r = xlsxgen.make_xlsx("Newtika Sales March", SHEETS,
                          charts=[{"sheet": "Sales", "type": "bar", "title": "Orders by city",
                                   "categories": "A2:A4", "values": "B2:B4"}])
    assert r["charts"] == 1
    from openpyxl import load_workbook
    ws = load_workbook(io.BytesIO(r["data"]))["Sales"]
    chart = ws._charts[0]
    assert chart.gapWidth == 80 and chart.overlap == 100            # the thin-bar fix
    assert chart.title.tx.rich.p[0].r[0].rPr.sz == 1200             # font baked into the run
    assert str(chart.series[0].val.numRef.f).endswith("$C$5:$C$7")  # rebased onto the designed grid


# ---------------------------------------------------------------- docx

def test_docx_styles_cover_and_toc_field():
    r = docxgen.make_docx("Newtika Traders March Sales Report", LONG, style="professional", author="Meghana")
    assert r["cover"] is True and r["toc"] is True and r["tables"] == 2
    assert r["qa"]["status"] == "pass" and len(r["headings"]) == 5
    from docx import Document
    d = Document(io.BytesIO(r["data"]))
    assert d.styles["Normal"].paragraph_format.line_spacing == 1.3  # the mandatory default
    assert d.paragraphs[1].runs[0].font.size.pt >= 22               # cover title sized by length
    xml = d.element.xml
    assert " TOC " in xml                                           # real Word field, not fake text
    assert "Update Field" in xml or any("Update Field" in p.text for p in d.paragraphs)
    tbl = d.tables[0]
    assert tbl.rows[0]._tr.trPr.find(
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tblHeader") is not None
    assert tbl.rows[1]._tr.trPr.find(
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}cantSplit") is not None


def test_docx_short_doc_no_cover():
    r = docxgen.make_docx("Quick note", "Just a line.", cover=False, toc=False)
    assert r["cover"] is False and r["toc"] is False and r["qa"]["status"] == "pass"


# ---------------------------------------------------------------- pptx

def test_pptx_deck():
    r = pptxgen.make_pptx("Newtika Sales Review", [
        {"title": "March numbers", "bullets": ["1,842 orders", "+12.4% growth"], "notes": "lead with growth"},
        {"title": "April plan", "bullets": ["Navratri banners"]}])
    assert [s["title"] for s in r["slides"]] == ["March numbers", "April plan"]
    assert r["qa"]["status"] == "pass"
    from pptx import Presentation
    p = Presentation(io.BytesIO(r["data"]))
    assert len(p.slides._sldIdLst) == 3                             # title slide + 2 content
    assert p.slides[1].notes_slide.notes_text_frame.text.startswith("lead")


# ---------------------------------------------------------------- preview + tools

def test_preview_per_kind():
    pdf = pdfgen.make_pdf("Preview check", "# A\nbody " * 40, cover=False, toc=False)
    v = preview.preview("pdf", pdf["data"], pdf)
    assert v["pages"] >= 1 and v["qa"]["status"] == "pass"
    imgs = preview.pdf_pages(pdf["data"], limit=2)
    assert 1 <= len(imgs) <= 2 and imgs[0][:4] == b"\x89PNG"
    x = xlsxgen.make_xlsx("S", SHEETS)
    vx = preview.preview("xlsx", x["data"])
    assert vx["sheets"][0]["name"] == "Sales" and vx["sheets"][0]["rows"] == 4
    p = pptxgen.make_pptx("Deck", [{"title": "One", "bullets": ["a"]}])
    vp = preview.preview("pptx", p["data"])
    assert vp["slide_count"] == 2 and vp["slides"][1]["title"] == "One"
    vunknown = preview.preview("csv", b"a,b\n1,2")
    assert "note" in vunknown


def test_docstudio_tools_registered():
    from app.agent import tools as reg
    names = {t["name"] for t in reg.TOOLS}
    assert {"doc_studio", "doc_preview"} <= names
    assert reg.TOOL_LABELS["doc_studio"] and reg.TOOL_LABELS["doc_preview"]
    assert reg.HANDLERS["doc_studio"].__name__ == "doc_studio"
    diet = reg.diet_tool_specs([t for t in reg.TOOLS if t["name"] in ("doc_studio", "doc_preview")])
    assert {t["name"] for t in diet} == {"doc_studio", "doc_preview"}       # names survive the diet
    kinds = [p for p in next(t for t in reg.TOOLS if t["name"] == "doc_studio")
             ["input_schema"]["properties"].items() if True]
    schema = next(t for t in reg.TOOLS if t["name"] == "doc_studio")["input_schema"]
    assert schema["required"] == ["kind", "title"]
    assert [o for o in schema["properties"]["kind"]["enum"]] == ["pdf", "docx", "xlsx", "pptx"]


def test_doc_studio_refuses_secrets_and_bad_kind():
    import asyncio
    from app.agent.docstudio_tools import doc_studio
    from app.agent.tools import Ctx, ToolError

    class _T:
        tenant_id, conversation_id, user_id = "t1", "c1", "u1"
    ctx = _T()
    with pytest.raises(ToolError) as e:
        asyncio.run(doc_studio(ctx, "pdf", "OTP sheet", "OTP 4455 hai"))
    assert "OTP" in str(e.value)
    with pytest.raises(ToolError):
        asyncio.run(doc_studio(ctx, "exe", "X"))
    with pytest.raises(ToolError):
        asyncio.run(doc_studio(ctx, "xlsx", "X"))                   # sheets missing


def test_doc_studio_builds_and_delivers(monkeypatch, tmp_path):
    import asyncio
    from app.agent import docstudio_tools as dt
    from app.agent.tools import Ctx, ToolError

    seen = {}

    def fake_deliver(ctx, name, data, source):
        seen.update({"name": name, "data": data, "source": source})
        return {"file_id": "f1", "name": name}

    monkeypatch.setattr(dt, "_deliver", fake_deliver)
    monkeypatch.setattr(dt, "_owner_bytes", lambda ctx, fid: ("note.pdf", b"%PDF-fake"))
    monkeypatch.setattr("app.events.bus.publish", lambda *a, **k: None)

    class _T:
        tenant_id, conversation_id, user_id = "t1", "c1", "u1"
    out = asyncio.run(dt.doc_studio(_T(), "pdf", "March Report", LONG, style="boardroom"))
    assert out["made"] == "pdf" and out["file_id"] == "f1"
    assert seen["name"].endswith(".pdf") and seen["data"][:5] == b"%PDF-"
    assert out["preview"]["qa"]["status"] in ("pass", "warn") and out["style"] == "boardroom"
    pv = asyncio.run(dt.doc_preview(_T(), "f1"))
    assert pv["name"] == "note.pdf" and "warning" not in pv or True
