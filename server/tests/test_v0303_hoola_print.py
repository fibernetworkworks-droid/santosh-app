"""v0.303.0 HOOLA PRINT: PDFs made the way Claude makes them (designed HTML printed by Chromium).

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
        m = re.search(re.escape(head) + r"[ .…]*?(\d+)\s", toc)
        assert m, head
        real = next(i + 1 for i, p in enumerate(pages) if i > 1 and head in p)
        assert int(m.group(1)) == real, (head, m.group(1), real)
    assert {"Inter", "Source Serif"} <= set(r["qa"]["fonts"])      # humanist: Inter heads + Source Serif body
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
