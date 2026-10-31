"""v0.313.0 HOOLA PRINT: PDFs made the way Claude makes them (designed HTML printed by Chromium).

Pure parts (parser, colours, art-direction guard rails, HTML) always run; the print tests run where Chromium can print
(the VPS, this sandbox) and skip elsewhere.
"""
import asyncio
import io
import os
import re
from pathlib import Path

import pytest

SANDBOX_CHROME = "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"


@pytest.fixture()
def chrome(env, monkeypatch):
    if not os.environ.get("HOOLA_CHROMIUM") and Path(SANDBOX_CHROME).exists():
        monkeypatch.setenv("HOOLA_CHROMIUM", SANDBOX_CHROME)
    from app.config import get_settings
    get_settings.cache_clear() if hasattr(get_settings, "cache_clear") else None
    from app.docstudio import htmlpdf
    htmlpdf._AVAILABLE.clear()
    if not htmlpdf.available():
        pytest.skip("Chromium cannot print here")
    return htmlpdf


LONG = """# Executive Summary
Sharma Traders closed FY 2025-26 with revenue of **Rs 4.2 crore**, up 18% on last year.
[stat: Rs 4.2 Cr | Revenue FY26]
[stat: 18% | Growth]
[stat: 51 days | Receivables]
## Key numbers
- Net profit Rs 38 lakh
- Two new distributors
# Quarterly Revenue
| Quarter | Revenue (Rs lakh) | Profit |
|---|---|---|
| Q1 | 92 | 8 |
| Q2 | 98 | 9 |
| Total | 190 | 17 |
# Cash Flow
Operating cash flow stayed positive in all four quarters, and the packing machine was paid from a term loan.
> [!WARNING] Two customers make up 31% of sales.
# Risks
1. Customer concentration.
2. Steel prices.
# Recommendations
Diversify customers and keep 60 days of working capital.
""" + "\n".join(f"# Annex {i}\n" + ("Working capital detail for the year with notes on every distributor. " * 30)
                for i in range(1, 5))


def _text_pages(data: bytes) -> list[str]:
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(io.BytesIO(data))
    out = [doc[i].get_textpage().get_text_range() for i in range(len(doc))]
    doc.close()
    return out


# ---------------------------------------------------------------- pure
def test_parse_groups_stats_lists_callouts_code_and_tables():
    from app.docstudio.htmlpdf import parse
    b = parse("# A\n[stat: 1 | x]\n[stat: 2 | y]\n- one\n- two\n  - sub\n> [!WARNING] careful\n> more\n"
              "```\nls -la\n```\n| a | b |\n|---|---|\n| 1 | 2 |\n[[pagebreak]]\n3. third\n")
    kinds = [x["k"] for x in b]
    assert kinds == ["h1", "stats", "ul", "callout", "code", "table", "pagebreak", "ol"]
    assert b[1]["items"] == [("1", "x"), ("2", "y")]
    assert b[2]["items"][2] == (1, "sub")
    assert b[3]["kind"] == "warning" and b[3]["t"] == "careful\nmore"
    assert b[4]["t"] == "ls -la"
    assert b[5]["rows"] == [["a", "b"], ["1", "2"]]
    assert b[7]["start"] == 3


def test_inline_escapes_html_and_only_links_http():
    from app.docstudio.htmlpdf import _inline
    out = _inline("<script>x</script> **b** *i* `c<d>` [ok](https://a.in) [bad](javascript:alert(1))")
    assert "<script>" not in out and "&lt;script&gt;" in out
    assert "<b>b</b>" in out and "<i>i</i>" in out and "<code>c&lt;d&gt;</code>" in out
    assert '<a href="https://a.in">ok</a>' in out and "javascript:" not in out.split("bad")[0][-30:]
    assert 'href="javascript' not in out


def test_numeric_columns_and_total_row():
    from app.docstudio.htmlpdf import _table, numeric_columns
    rows = [["Item", "Qty", "Amount"], ["Chair", "10", "₹65,000"], ["GST 18%", "", "₹11,700"],
            ["**Total**", "", "**₹76,700**"]]
    assert numeric_columns(rows) == [False, True, True]
    html = _table(rows, keep=True)
    assert "<th class=n>Amount</th>" in html and "<tr class=tot>" in html
    assert "<td class=n>₹76,700</td>" in html          # the bold markers drop inside the (already bold) total row


def test_palette_always_readable_even_from_light_picks():
    from app.docstudio.htmlpdf import contrast, palette
    P = palette("#f5e663", "#ffe0f0")                   # a careless model pick: pale yellow + pale pink
    assert contrast(P["primary"], "#ffffff") >= 7.0     # white cover text reads on the primary
    assert contrast(P["accent"], "#ffffff") >= 4.5      # accent text reads on white
    assert contrast(P["ink"], "#ffffff") >= 12


def test_art_pick_is_kept_inside_the_fixed_parts():
    from app.docstudio.htmlpdf import _route, _sane
    base = _route("Annual report", "profit loss revenue", "auto")
    got = _sane(base, {"cover": "gradient", "type": "comic-sans", "primary": "red;}body{display:none",
                       "accent": "#0E9F6E", "tags": ["a", "b", "c", "d", "e"], "kicker": "x" * 200,
                       "table": "lines", "evil": "<script>"})
    assert got["cover"] == "gradient" and got["table"] == "lines"
    assert got["type"] == base["type"]                  # unknown value ignored
    assert got["primary"] == base["primary"]            # CSS injection refused
    assert got["accent"] == "#0e9f6e"
    assert len(got["tags"]) == 4 and len(got["kicker"]) <= 48 and "evil" not in got


def test_art_direct_uses_opus_pick_and_falls_back_to_router(env):
    from app.docstudio import htmlpdf
    asked = []

    def opus(system, prompt, kind, images, timeout):
        asked.append(kind)
        assert "OUTLINE" in prompt and kind == "doc_art"
        return {"cover": "swiss", "type": "sans", "primary": "#16181d", "accent": "#c2410c", "kicker": "BUSINESS PLAN"}
    os.environ["DOC_ART"] = "true"
    try:
        from app.config import get_settings
        get_settings.cache_clear() if hasattr(get_settings, "cache_clear") else None
        spec = htmlpdf.art_direct("Varasa business plan", "# Problem\n# Product", "auto", ask=opus)
        assert spec["source"] == "opus" and spec["cover"] == "swiss" and spec["kicker"] == "BUSINESS PLAN"

        def broken(*a):
            raise TimeoutError("slow")
        spec2 = htmlpdf.art_direct("Varasa business plan", "# Problem", "auto", ask=broken)
        assert spec2["source"] == "router" and spec2["cover"] in htmlpdf.COVERS
        n = len(asked)
        spec3 = htmlpdf.art_direct("Varasa business plan", "x", "legal", ask=opus)   # a forced style never asks
        assert len(asked) == n and spec3["family"] == "legal" and spec3["source"] == "router"
    finally:
        os.environ["DOC_ART"] = "false"


def test_kicker_from_document_type():
    from app.docstudio.htmlpdf import doc_kicker
    assert doc_kicker("Quotation for Office Chairs", "Finance", "finance") == "QUOTATION"
    assert doc_kicker("OmniStream delivery plan", "Technology", "technology") == "DELIVERY PLAN"
    assert doc_kicker("मासिक बिक्री रिपोर्ट", "Finance", "finance") == ""     # no English label on a Hindi title
    assert doc_kicker("Hello", "Classic", "general") == ""


def test_headings_keep_the_writers_own_numbers():
    from app.docstudio.htmlpdf import headings, parse
    assert [h["no"] for h in headings(parse("# Intro\n# Plan\n## Step"), True)] == ["01", "02", ""]
    assert [h["no"] for h in headings(parse("# 1. Intro\n# 2. Plan"), True)] == ["", ""]


def test_doc_kinds_ride_the_opus_path(env):
    from app.site import ai as AI
    assert AI._opus_kind("doc_art") and AI._opus_kind("doc_critique")
    assert AI.model_for("doc_art") == "claude-opus-5-5"
    assert AI.EFFORT["doc_art"] == "medium"


# ---------------------------------------------------------------- printed
def test_long_report_cover_contents_real_page_numbers(chrome):
    r = chrome.make_pdf("Sharma Traders Annual Financial Report FY 2025-26", LONG,
                        author="Sharma Traders", prepared_for="SBI Nagpur")
    assert r["cover"] and r["toc"] and r["design"]["engine"] == "chromium"
    pages = _text_pages(r["data"])
    assert len(pages) == r["pages"] >= 4
    assert "Page 1 of" not in pages[0]                  # the cover is printed alone: no footer on it
    flat = re.sub(r"\s+", "", pages[0])            # letter-spaced kicker extracts as 'R E P O R T'
    assert "REPORT" in flat and "Preparedfor:SBINagpur" in flat and "INSIDE" in flat
    assert f"Page 2 of {len(pages)}" in pages[1]        # numbering counts the cover
    assert not any("HQX" in p for p in pages)           # pass-1 markers never reach her file
    toc = pages[1]
    for head in ("Quarterly Revenue", "Recommendations", "Annex 4"):
        m = re.search(re.escape(head) + r"[ .…]*?(\d+)(?:\s|$)", toc)
        assert m, head
        real = next(i + 1 for i, p in enumerate(pages) if i > 1 and head in p)
        assert int(m.group(1)) == real, (head, m.group(1), real)
    assert {"Inter", "Source Serif 4"} <= set(r["qa"]["fonts"])    # humanist: Inter heads + Source Serif body (as drawn)
    assert not any("fonts not loaded" in i for i in r["qa"]["issues"])
    from pypdf import PdfReader
    meta = PdfReader(io.BytesIO(r["data"])).metadata
    assert meta["/Title"].startswith("Sharma Traders") and "Hoola Print" in meta["/Creator"]
    assert meta["/Author"] == "Sharma Traders"
    assert r["qa"]["status"] in ("pass", "warn") and "fill" in r["qa"]


def test_short_quotation_is_one_page_with_letterhead(chrome):
    text = ("Dear Sir,\n\n| Item | Qty | Amount |\n|---|---|---|\n| Chair | 10 | ₹65,000 |\n"
            "| Total | | ₹76,700 |\n\nValid for 15 days.")
    r = chrome.make_pdf("Quotation for Office Chairs", text)
    assert r["pages"] == 1 and not r["cover"] and not r["toc"] and r["design"]["cover"] == "letterhead"
    page = _text_pages(r["data"])[0]
    assert "QUOTATION" in page and "₹76,700" in page and "Page 1 of 1" in page


def test_hindi_prints_with_noto_and_no_english_kicker(chrome):
    text = "# सारांश\nइस महीने बिक्री **12%** बढ़ी।\n| महीना | बिक्री |\n| सितंबर | ₹8,00,000 |\n" * 3
    r = chrome.make_pdf("मासिक बिक्री रिपोर्ट", text)
    assert "Noto Sans Devanagari" in r["qa"]["fonts"]
    assert "FINANCE" not in _text_pages(r["data"])[0]


def test_review_can_change_the_look_once(chrome):
    seen = {}

    def reviewer(system, prompt, kind, images, timeout):
        seen["kind"], seen["imgs"] = kind, len(images)
        assert all(i[:8] == b"\x89PNG\r\n\x1a\n" for i in images)
        return {"score": 6, "issues": ["cover too quiet for a launch plan"], "change": {"cover": "gradient"}}
    art = lambda *a: {"cover": "minimal", "type": "sans", "primary": "#0b2a4a", "accent": "#0e9f6e"}  # noqa: E731
    r = chrome.make_pdf("OmniStream launch plan", LONG, art=art, reviewer=reviewer)
    assert seen["kind"] == "doc_critique" and seen["imgs"] >= 2
    assert r["design"]["cover"] == "gradient" and r["qa"]["review"]["changed"] == {"cover": "gradient"}

    calm = lambda *a: {"score": 9, "issues": [], "change": {"cover": "swiss"}}   # noqa: E731
    r2 = chrome.make_pdf("OmniStream launch plan", LONG, art=art, reviewer=calm)
    assert r2["design"]["cover"] == "minimal"           # a good score keeps the look


def test_doc_studio_uses_print_and_falls_back_to_reportlab(chrome, monkeypatch):
    from app.agent import docstudio_tools as T
    r = T.make_pdf("Annual report", LONG, {"style": "auto", "subject": "", "cover": "auto", "toc": "auto"},
                   "Sharma Traders", "SBI")
    assert r["design"]["engine"] == "chromium"
    monkeypatch.setattr(chrome, "make_pdf", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("chromium crashed")))
    r2 = T.make_pdf("Annual report", LONG, {"style": "auto", "subject": "", "cover": "auto", "toc": "auto"})
    assert r2["data"][:5] == b"%PDF-" and r2["design"].get("engine") is None     # ReportLab answered
    monkeypatch.setenv("DOC_ENGINE", "reportlab")
    from app.config import get_settings
    get_settings.cache_clear() if hasattr(get_settings, "cache_clear") else None
    r3 = T.make_pdf("Annual report", "# A\ntext", {"style": "auto", "subject": "", "cover": "auto", "toc": "auto"})
    assert r3["design"].get("engine") is None


def test_doc_studio_tool_delivers_a_printed_pdf(chrome, monkeypatch):
    from app.agent import docstudio_tools as T
    from app.agent.tools import Ctx
    got = {}

    def deliver(ctx, name, data, src):
        got["name"], got["data"] = name, data
        return {"file_id": "f1", "name": name}
    monkeypatch.setattr(T, "_deliver", deliver)
    out = asyncio.run(T.doc_studio(Ctx(tenant_id="t1", conversation_id="c1"), kind="pdf",
                                   title="Quotation for Office Chairs", text="| Item | Amount |\n| Chair | ₹6,500 |",
                                   author="Mehta Furniture", prepared_for="Newtika"))
    assert out["made"] == "pdf" and got["data"][:5] == b"%PDF-" and got["name"].endswith(".pdf")
    assert out["design"]["engine"] == "chromium" and "Design matched" in out["note"]


# ---------------------------------------------------------------- v0.313.0 THE PAGE SYSTEM (measured, not eyeballed)
ALL_PARTS = """# Executive Summary
Revenue of **Rs 4.2 crore**, up 18% on last year, because raw material costs fell in the second half of the year.
[stat: Rs 4.2 Cr | Revenue]
[stat: 18% | Growth]
## Key numbers
- Net profit Rs 38 lakh, the best year since the business started and well above the plan for the year
  - Nagpur distributor pays in 30 days
### What drove it
Festive demand.
# Quarterly Revenue
| Quarter | Revenue | Profit |
|---|---|---|
| Q1 | 92 | 8 |
| Total | 190 | 17 |
Q3 and Q4 carried the year.
# Cash Flow
Operating cash flow stayed positive.
> [!WARNING] Two customers make up 31% of sales.

> A quote from the auditor.
```
ssh root@vps
```
# Risks
1. Concentration.
"""

MEASURE = r"""() => {
 const mm = v => v / (96 / 25.4);
 const first = el => { const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT,
     {acceptNode: n => n.textContent.trim() && !n.parentElement.closest('.no,.mk') ? 1 : 3});
   const n = w.nextNode(); if (!n) return null; const r = document.createRange();
   const i = n.textContent.search(/\S/); r.setStart(n, i); r.setEnd(n, i + 1); return r.getClientRects()[0]; };
 const col = document.querySelector('.body').getBoundingClientRect();
 const out = [];
 document.querySelectorAll('.body > *, .body li, .body td:first-child, .body .stat, .body .callout p, .toc .row').forEach(el => {
   const b = el.getBoundingClientRect(); const t = first(el);
   const no = el.querySelector(':scope > .no, :scope .t > .no');
   out.push({k: el.tagName.toLowerCase() + '.' + (el.className || ''), textL: t ? mm(t.left - col.left) : null,
             top: mm(b.top), bot: mm(b.bottom), boxL: mm(b.left - col.left), boxR: mm(b.right - col.left),
             noL: no ? mm(no.getBoundingClientRect().left) : null});
 }); return {rows: out, colW: mm(col.width), colL: mm(col.left)}; }"""


def _measure(H, table="dark", headings="numbered"):
    import pathlib
    spec = H._sane(H._route("Report", ALL_PARTS, "auto"), {"table": table, "headings": headings})
    P = H.palette(spec["primary"], spec["accent"])
    blocks = H.parse(ALL_PARTS)
    heads = H.headings(blocks, True)
    html = H._doc(H._css(spec, P), H.body_html(blocks, spec, heads, toc_pages={h["id"]: 3 for h in heads},
                                                markers=False), "t")
    with H.Printer() as pr:
        f = pathlib.Path(pr._tmp.name) / "m.html"
        f.write_text(html)
        pg = pr._browser.new_context().new_page()     # a measuring page WITH script (the print page has none)
        pg.set_viewport_size({"width": round(194 * 96 / 25.4), "height": 1400})   # A4 minus the 8 mm page margins
        pg.emulate_media(media="print")
        pg.goto(f.as_uri())
        pg.evaluate("document.fonts.ready")
        return pg.evaluate(MEASURE)


@pytest.mark.parametrize("table", ["dark", "lines"])
def test_two_text_edges_only(chrome, table):
    m = _measure(chrome, table=table)
    IN = chrome.GRID["inset"]
    edges = {round(r["textL"], 1) for r in m["rows"] if r["textL"] is not None and not r["k"].startswith("div.stat")}
    allowed = {0.0, IN, 2 * IN}
    assert all(any(abs(e - a) <= 0.3 for a in allowed) for e in edges), edges
    for k in ("h1.", "h2.", "h3.", "p.", "a.row r1"):
        assert all(abs(r["textL"]) <= 0.3 for r in m["rows"] if r["k"].startswith(k) and r["textL"] is not None
                   and r["boxL"] == 0), k                    # headings, paragraphs, contents titles on the text edge
    first_cell = [r["textL"] for r in m["rows"] if r["k"].startswith("td.")]
    assert all(abs(x - (0 if table == "lines" else IN)) <= 0.3 for x in first_cell)
    for r in m["rows"]:                                       # every block spans the full column
        if r["k"].split(".")[0] in ("table", "pre") or r["k"].startswith(("div.callout", "div.stats")):
            assert abs(r["boxL"]) <= 0.3 and abs(r["boxR"] - m["colW"]) <= 0.3, r


def test_numbers_hang_inside_the_printable_strip(chrome):
    m = _measure(chrome)
    nos = [r["noL"] for r in m["rows"] if r["noL"] is not None]
    assert nos and all(n >= 0 for n in nos)                   # never pushed into the clipped page margin
    assert all(n < m["colL"] for n in nos)                    # ... and still left of the text edge (hanging)


def test_vertical_rhythm(chrome):
    rows = [r for r in _measure(chrome)["rows"] if not r["k"].startswith(("li", "td", "div.stat.", "p.", "a."))
            or r["k"] == "p."]
    top = [r for r in rows if r["boxL"] == 0]
    after_head = []
    for a, b in zip(top, top[1:]):
        if a["k"].startswith(("h1", "h2", "h3")):
            after_head.append((a["k"][:2], round(b["top"] - a["bot"], 1)))
    by = {}
    for h, g in after_head:
        by.setdefault(h, set()).add(g)
    assert all(len(v) == 1 for v in by.values()), by          # a heading sits the same distance from whatever follows
    gaps = {}
    for a, b, c in zip(top, top[1:], top[2:]):
        if b["k"].startswith(("div.callout", "div.stats", "pre", "blockquote")) and a["k"] == "p." and c["k"] in ("p.", "pre."):
            gaps[b["k"]] = (round(b["top"] - a["bot"], 1), round(c["top"] - b["bot"], 1))
    assert all(abs(x - y) <= 0.3 for x, y in gaps.values()), gaps   # same space above and below a box


def test_cover_is_full_bleed_and_bands_sit_12mm_from_the_edge(chrome):
    import pypdfium2 as pdfium
    r = chrome.make_pdf("Annual report", LONG, art=lambda *a: {"cover": "gradient", "primary": "#0b2a4a",
                                                                 "accent": "#0e8f6a"})
    doc = pdfium.PdfDocument(io.BytesIO(r["data"]))
    im = doc[0].render(scale=0.4).to_pil().convert("RGB")
    w, h = im.size
    assert all(sum(im.getpixel(p)) < 600 for p in ((1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2)))
    page = doc[2]
    H_mm = page.get_height() * 25.4 / 72
    tp = page.get_textpage()
    txt = tp.get_text_range()
    i = txt.index("Page 3 of")
    _l, b, _r, t = tp.get_charbox(i)
    assert 9 <= b * 25.4 / 72 <= 15                          # footer baseline 9-15 mm above the paper's bottom edge
    _l, b, _r, t = tp.get_charbox(txt.index("Annual report"))   # the running header carries the title
    assert 9 <= H_mm - t * 25.4 / 72 <= 15                   # header 9-15 mm below the top edge


# ---------------------------------------------------------------- v0.313 review round: faults found by stress inputs
def test_link_cannot_grow_an_attribute():
    from app.docstudio.htmlpdf import _inline
    out = _inline('[x](https://a.in/"onfocus="alert(1)"autofocus=")')
    assert '"onfocus' not in out and "&quot;onfocus" in out
    assert re.fullmatch(r'<a href="[^"]*">x</a>.*', out)       # exactly one attribute, quote-free


def test_print_page_runs_no_script_and_reaches_no_network(chrome, tmp_path):
    seen = []
    html = ("<!doctype html><p id=x>static</p><img src='https://example.com/leak.png'>"
            "<script>document.getElementById('x').textContent='SCRIPT RAN'</script>")
    with chrome.Printer() as pr:
        pr._ctx.on("requestfailed", lambda r: seen.append(r.url))
        data = pr.pdf(html)
    text = _text_pages(data)[0]
    assert "static" in text and "SCRIPT RAN" not in text
    assert any("example.com" in u for u in seen)               # the outside request was refused


def test_long_tokens_wrap_inside_the_column_and_words_stay_whole(chrome):
    url = "https://www.example.com/this/is/a/really/long/path/that/never/breaks/naturally/at/all?query=1234567890"
    text = (f"# Links\nSee {url} and Supercalifragilisticexpialidociousandevenlongerthanthatwordhere.\n"
            "| Sr | Name | City | State | GSTIN | Phone | Orders | Value | Status |\n"
            "| 1 | Sharma Traders Private Limited | Nagpur | Maharashtra | 27AAACS1234F1Z5 | +91 98220 12345 | 120 | "
            "₹12,40,000 | Active |\n| 2 | Rao & Sons | Hyderabad | Telangana | 36AAACR1111L1Z9 | +91 90000 11111 | 8 | "
            "₹45,000 | Active |")
    r = chrome.make_pdf("Wrap test", text, cover=False)
    import pypdfium2 as pdfium
    page = pdfium.PdfDocument(io.BytesIO(r["data"]))[0]
    tp = page.get_textpage()
    right = max(tp.get_charbox(i)[2] for i in range(tp.count_chars())
                if tp.get_text_range(i, 1).strip()) * 25.4 / 72  # line breaks have boxes too - ink only
    assert right <= 192.8, right                                # nothing past the text column (18 mm from the edge)
    flat = tp.get_text_range()
    for word in ("Maharashtra", "Hyderabad", "Telangana", "27AAACS1234F1Z5"):
        assert word in flat, word                               # no word cut in the middle by the table
    assert "<wbr>" not in flat and "\x01" not in flat


def test_parser_and_number_column_edge_cases():
    from app.docstudio.htmlpdf import numeric_columns, parse, stat_rows
    assert [b["k"] for b in parse("2025. was a good year.\n12. Twelfth step")] == ["p", "ol"]
    assert [len(r) for r in stat_rows(list(range(5)))] == [3, 2]
    assert [len(r) for r in stat_rows(list(range(8)))] == [4, 4]
    assert [len(r) for r in stat_rows(list(range(9)))] == [3, 3, 3]
    assert len(parse("[stat: 1 | a]\n[stat: 2 | b]\n[stat: 3 | c]\n[stat: 4 | d]\n[stat: 5 | e]")) == 1
    rows = [["Name", "Value"], ["A", "—"], ["B", "-"], ["C", "₹10"], ["D", "n/a"]]
    assert numeric_columns(rows) == [False, True]               # placeholders don't vote


def test_header_footer_carry_latin_only():
    from app.docstudio.htmlpdf import band_safe
    assert band_safe("मासिक बिक्री रिपोर्ट") == ""
    assert band_safe("Price ₹500 · Q3 — “final”") == "Price Rs 500 · Q3 — “final”"


def test_chromium_no_is_asked_again_after_ten_minutes(monkeypatch):
    from app.docstudio import htmlpdf as H
    calls = []

    class Boom:
        def __enter__(self):
            calls.append(1)
            raise H.PrintError("no chromium")

        def __exit__(self, *a):
            return False
    monkeypatch.setattr(H, "Printer", Boom)
    H._AVAILABLE.clear()
    assert H.available() is False and H.available() is False and len(calls) == 1
    H._AVAILABLE["at"] -= 601
    assert H.available() is False and len(calls) == 2
    H._AVAILABLE.clear()


# ---------------------------------------------------------------- v0.313 world-class round (research -> deployed)
def test_prose_lines_stay_within_90_characters(chrome):
    para = ("Operating cash flow stayed positive in all four quarters of the year, and the largest single outflow was "
            "the new packing machine bought in the third quarter, paid partly from an SBI term loan. ") * 6
    r = chrome.make_pdf("Line length", "# Cash\n" + para, cover=False)
    lines = [ln for ln in _text_pages(r["data"])[0].split("\r\n") if len(ln) > 50 and "Page" not in ln]
    assert lines and max(len(ln) for ln in lines) <= 90, max(len(ln) for ln in lines)   # Butterick: 45-90


def test_pdf_has_bookmarks_tags_language_and_shows_its_title(chrome):
    from pypdf import PdfReader
    r = chrome.make_pdf("Annual report", LONG)
    R = PdfReader(io.BytesIO(r["data"]))
    root = R.trailer["/Root"]
    titles = [o.title for o in R.outline if not isinstance(o, list)]
    assert "Quarterly Revenue" in titles and "Annex 4" in titles   # heading words only - no glued '02'
    assert "/StructTreeRoot" in root and root["/MarkInfo"]["/Marked"]
    assert root["/Lang"] == "en" and root["/ViewerPreferences"]["/DisplayDocTitle"]
    assert root["/PageMode"] == "/UseOutlines"


def test_hindi_document_speaks_hindi(chrome):
    from pypdf import PdfReader
    text = "# सारांश\nइस महीने बिक्री बढ़ी।\n> [!KEY] नए ग्राहक 40 जुड़े।\n" * 10
    r = chrome.make_pdf("मासिक बिक्री रिपोर्ट", text, cover=True, toc=True)
    assert PdfReader(io.BytesIO(r["data"])).trailer["/Root"]["/Lang"] == "hi"
    pages = _text_pages(r["data"])
    flat = re.sub(r"\s+", "", "".join(pages))
    for word in ("विषय", "मुख्यबातें", "पृष्ठ"):
        assert word in flat, word                           # Hoola's own labels in Hindi, footer included
    assert re.search(r"2/\d", flat)                         # 'पृष्ठ 2 / 4' (the text layer repeats some letters)
    assert "Contents" not in flat and "Page 2" not in flat


def test_typographic_punctuation_never_touches_code_or_links():
    from app.docstudio.htmlpdf import typo
    assert typo('He said "FY 2025-26 was good" -- it\'s true...') == "He said \u201cFY 2025\u201326 was good\u201d \u2014 it\u2019s true\u2026"
    assert typo("Delivery in 10-12 days, 20-30% off - see") == "Delivery in 10\u201312 days, 20\u201330% off \u2013 see"
    assert typo('`a-b "c"` and https://x.in/a-b?q="1"') == '`a-b "c"` and https://x.in/a-b?q="1"'
    assert typo("GSTIN 27AAACS1234F1Z5, phone 98220-12345") == "GSTIN 27AAACS1234F1Z5, phone 98220-12345"


def test_chart_syntax_takes_its_table_caption_and_source():
    from app.docstudio.htmlpdf import parse
    b = parse("[chart: bar | Revenue by quarter]\n| Q | Revenue |\n| Q1 | 92 |\n| Q2 | 98 |\nSource: Tally\n"
              "Table 2: Costs\n| Head | Amount |\n| Rent | 22 |\n[chart: pie | Share | table]\n| C | V |\n| A | 1 |\n"
              "[chart: line | nothing under me]\nplain text")
    k = [x["k"] for x in b]
    assert k == ["chart", "table", "chart", "table", "p"], k
    assert b[0]["rows"][1] == ["Q1", "92"] and b[0]["source"] == "Tally" and b[0]["t"] == "Revenue by quarter"
    assert b[1]["caption"] == "Costs"                            # a caption written ABOVE its table
    assert b[2]["kind"] == "donut" and b[3].get("from_chart")    # '| table' keeps the table under the chart


def test_chart_svg_draws_every_kind_with_indian_numbers():
    from app.docstudio.htmlpdf import chart_svg, indian, palette
    P = palette("#123a5c", "#0f8a6a")
    rows = [["Quarter", "Revenue", "Profit"], ["Q1", "₹92,00,000", "₹8,00,000"], ["Q2", "₹1,20,00,000", "₹9,00,000"],
            ["Total", "₹2,12,00,000", "₹17,00,000"]]
    for kind in ("bar", "hbar", "line", "donut"):
        svg = chart_svg(kind, rows, P, {}, "Revenue")
        assert svg.startswith("<svg") and "role='img'" in svg and "<title>Revenue</title>" in svg, kind
        assert "Total" not in svg.split("<desc>")[1].split("</desc>")[0]      # the total row is not a bar
    assert "₹1.2 Cr" in chart_svg("bar", rows, P, {}, "R")
    assert indian(1240000, "₹") == "₹12.4 L" and indian(45600) == "46k" and indian(4560) == "4.6k" and indian(18, "%") == "18%"
    assert chart_svg("bar", [["Name", "City"], ["A", "Pune"]], P, {}, "x") == ""    # nothing numeric -> no chart
    long_labels = [["Head", "Amount"]] + [[f"Expense head number {i}", str(i * 10)] for i in range(1, 6)]
    assert "<rect x='" in chart_svg("bar", long_labels, P, {}, "x")     # long labels switch to sideways bars


def test_footnotes_and_key_takeaways_print(chrome):
    text = ("# Summary\n> [!KEY] Revenue grew 18%.\nBest year since 2019[^a]. Costs fell[^b].\n"
            "[^a]: FY 2019-20 was the previous high.\n[^b]: Steel fell 9%.\n"
            "[chart: bar | Revenue]\n| Q | Revenue |\n| Q1 | 92 |\n| Q2 | 98 |\nSource: Tally")
    r = chrome.make_pdf("Annual review", text, cover=False)
    flat = _text_pages(r["data"])[0]
    assert "KEY TAKEAWAYS" in flat.upper() and "Notes" in flat and "Figure 1" in flat and "Source: Tally" in flat
    assert "[^a]" not in flat and "previous high" in flat


def test_kicker_case_keeps_short_capitals():
    from app.docstudio.htmlpdf import kicker_case
    assert kicker_case("ANNUAL REVIEW · FY 2025-26") == "Annual Review · FY 2025-26"
    assert kicker_case("GST NOTICE") == "GST Notice"
