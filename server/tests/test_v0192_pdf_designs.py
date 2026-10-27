"""v0.192.0 "Design Router" - one CR design per user topic (owner: PDF is generated in only one
design -- we want it generated in 1 CR design based on user topic). The router (docstudio/designs.py)
detects the topic from title + content keywords (English, Hinglish, Devanagari) and picks a FULL
design: hue anchor + per-title jitter, one of 6 cover architectures (band / rail / plate / sunrise /
minimal / classic), a topic font pairing from the registered pool, grid or clean tables, H1 rule
weight, page-number style. 12 families x jitter x covers x pairings = a crore of distinct looks,
deterministic per title. v0.189 named styles keep byte-identical legacy output (classic cover,
FreeSerif, grid, hue from STYLES) so the old suite stays untouched and green.
"""
import io

import pytest

from app.docstudio import designs, pdfgen, tokens
from pypdf import PdfReader

LONG = """# Summary
Newtika Traders closed March with 1,842 orders and 12.4% growth. Same-day dispatch stayed above 96%.
[stat: +12.4% | Order growth vs February]
| City | Orders | Revenue | Share |
| Jaipur | 842 | Rs 1,240,500 | 45.7% |
| Indore | 610 | Rs 902,300 | 33.3% |

# What worked
- Same-day dispatch stayed above 96% even during the two festival weeks.
> WhatsApp follow-ups converted 4x better than email this month.

# Next month plan
April has two festivals and one long weekend. The bundle offer runs again with a higher margin floor,
a Nagpur pickup point is added, and the new catalogue photos are tested on the top 20 SKUs.

# Costs
- Packing material: Rs 84,300 (up 9% with volume)
| Head | March | Plan | Var |
| Revenue | 27.2 L | 25.0 L | +8.8% |
"""


# ---------------------------------------------------------------- detection

def test_detect_topic_english_titles():
    cases = [("Q3 Invoice and GST Summary", "", "finance"),
             ("Sprint 24 API Release Notes", "the server deploy fixed a bug", "technology"),
             ("Class 8 Exam Schedule", "school syllabus for students", "education"),
             ("Patient Discharge Summary", "hospital treatment and medicine", "health"),
             ("Shop Rent Agreement", "contract clause and notice period", "legal"),
             ("Diwali Sale Campaign", "instagram offer poster", "marketing"),
             ("Farm Mandi Report", "crop harvest and fertilizer prices", "agriculture"),
             ("Ward Cleaning Yojana", "panchayat scheme for citizens", "government"),
             ("Goa Trip Itinerary", "hotel booking and flight times", "travel"),
             ("Shaadi Invitation Card", "wedding puja and dinner invite", "festive")]
    for t, body, want in cases:
        fam, info = designs.detect_topic(t, body)
        assert fam == want, f"{t}: got {fam}, wanted {want} (hits={info['hits']})"


def test_detect_topic_hinglish_and_devanagari_and_fallback():
    fam, info = designs.detect_topic("Mandi Bhav", "fasal aur kisan ka byaj udhaar")
    assert fam == "agriculture" and info["hits"]
    fam, _ = designs.detect_topic("नवरात्रि बैनर योजना", "सेल के लिए पोस्टर तैयार करवाना है")
    assert fam in ("marketing", "festive")          # Devanagari hits counted (weight 4)
    fam, info = designs.detect_topic("Weekly Notes", "a few plain lines about the day")
    assert fam == "general" and info["scores"].get("general", 0) == 0   # no signal -> general
    fam2, _ = designs.detect_topic("Team Huddle", "attendance and leave plan for the staff")
    assert fam2 == "people"


def test_title_signal_beats_body_noise():
    # title keyword (weight 5) outranks repeated body hits (capped 2/keyword): the real bug this
    # fixed - "Shop Rent Agreement" + an offer-heavy body must stay LEGAL, not marketing
    fam, _ = designs.detect_topic("Shop Rent Agreement", "the bundle offer pulled buyers. "
                                  "The offer runs again. One more offer line here.")
    assert fam == "legal"
    fam2, _ = designs.detect_topic("School Annual Day Plan", "one stray revenue word")
    assert fam2 == "education"


def test_plural_titles_match_keywords():
    # "March Sales Report" must reach a family via the plural of "sale" (s? in the pattern)
    fam, info = designs.detect_topic("March Sales Report", "")
    assert fam == "marketing" and "sale" in info["hits"]
    fam2, _ = designs.detect_topic("Vendor Invoices Pending", "")
    assert fam2 == "finance"


# ---------------------------------------------------------------- resolve_design

def test_resolve_design_deterministic_per_title():
    a = designs.resolve_design("Q3 Invoice and GST Summary", LONG, None)
    b = designs.resolve_design("Q3 Invoice and GST Summary", LONG, None)
    assert a["hue"] == b["hue"] and a["cover"] == b["cover"] and a["family"] == b["family"]
    assert a["detected"] is True and a["family"] == "finance" and a["cover"] == "band"


def test_resolve_design_distinct_families_get_distinct_designs():
    finance = designs.resolve_design("Q3 Invoice and GST Summary", "", None)
    tech = designs.resolve_design("Sprint 24 API Release Notes", "", None)
    legal = designs.resolve_design("Shop Rent Agreement", "", None)
    edu = designs.resolve_design("Class 8 Exam Schedule", "", None)
    assert finance["cover"] == "band" and tech["cover"] == "rail"
    assert legal["cover"] == "minimal" and edu["cover"] == "plate"
    assert len({finance["family"], tech["family"], legal["family"], edu["family"]}) == 4
    # hue anchors far apart, jitter never leaves the family behind
    assert abs(finance["hue"] - 168) <= 10.5 and abs(tech["hue"] - 234) <= 10.5


def test_resolve_design_legacy_styles_byte_compatible():
    for name, hue in (("professional", 215.0), ("boardroom", 222.0), ("warm", 26.0),
                      ("elegant", 282.0), ("forest", 150.0)):
        s = designs.resolve_design("Any Title", LONG, name)
        assert s["hue"] == hue and s["cover"] == "classic" and s["table"] == "grid"
        assert s["style_name"] == name and s["detected"] is False
        p_old = tokens.palette_for("Any Title", name)
        p_new = tokens.Palette(s["hue"], s["style_name"])
        assert p_old.accent == p_new.accent and p_old.header_fill == p_new.header_fill
    assert tokens.resolve_style("nonsense") == "auto"      # unknown still falls back


def test_resolve_design_explicit_topic_style_forces_family():
    s = designs.resolve_design("Anything", "", "technology")
    assert s["family"] == "technology" and s["cover"] == "rail" and s["detected"] is False


# ---------------------------------------------------------------- pdf builds

def test_make_pdf_returns_design_and_routes_by_topic():
    r = pdfgen.make_pdf("Q3 Invoice and GST Summary", LONG, cover=True)
    assert r["design"]["topic"] == "finance" and r["design"]["cover"] == "band"
    assert r["design"]["detected"] is True and r["qa"]["status"] == "pass"
    assert not r["qa"]["issues"]


def test_make_pdf_all_six_covers_render_and_pass_qa():
    cases = [("Q3 Invoice and GST Summary", "band"), ("Sprint 24 API Release Notes", "rail"),
             ("Class 8 Exam Schedule", "plate"), ("Diwali Sale Campaign Plan", "sunrise"),
             ("Shop Rent Agreement", "minimal"), ("Quarterly Operations Note", None)]
    for t, want in cases:
        kw = {"style": "professional"} if want is None else {}   # professional -> classic
        want = want or "classic"
        r = pdfgen.make_pdf(t, LONG, cover=True, **kw)
        assert r["design"]["cover"] == want, f"{t}: {r['design']['cover']} != {want}"
        assert r["cover"] is True and r["pages"] >= 3 and not r["qa"]["issues"]
        txt = (PdfReader(io.BytesIO(r["data"])).pages[0].extract_text() or "")
        assert t.split()[0] in txt                              # title chunked onto the cover


def test_topic_font_pairings_resolve_to_registered_fonts():
    pdfgen.ensure_fonts()
    from reportlab.pdfbase import pdfmetrics
    pairs = [("Q3 Invoice and GST Summary", LONG), ("Sprint 24 API Release Notes", LONG),
             ("Class 8 Exam Schedule", LONG), ("Shop Rent Agreement", LONG)]
    for t, body in pairs:
        r = pdfgen.make_pdf(t, body, cover=True)
        head, body_f = r["design"]["fonts"]["head"], r["design"]["fonts"]["body"]
        pdfmetrics.getFont(head) and pdfmetrics.getFont(f"{head}-Bold")     # registered, not phantom
        pdfmetrics.getFont(body_f)
        assert head != "Helvetica"                                          # never the fallback default


def test_font_pool_falls_back_when_families_are_absent(monkeypatch):
    # a corrupt TTF (like this sandbox's Tinos-Regular.ttf) drops THAT family, never the build:
    # _register_family returns False for a bad file, and chains fall through to the next candidate
    pdfgen.ensure_fonts()
    assert pdfgen._register_family("BrokenTinos", "english",
                                   {"regular": "Tinos-Regular.ttf", "bold": "Tinos-Bold.ttf"}) is False
    monkeypatch.setitem(pdfgen._FONT_STATE, "pool", {"FreeSerif"})   # pretend only the floor exists
    F = pdfgen._resolve_pair(designs.FAMILIES["technology"]["fonts"])
    assert F["head"] == "FreeSerif" and F["body"] == "FreeSerif"     # floor catches every chain
    from reportlab.pdfbase import pdfmetrics
    pdfmetrics.getFont(F["head_b"])                                  # resolved names are real fonts


def test_clean_table_keeps_iron_rules():
    pdfgen.ensure_fonts()
    pal = tokens.Palette(234, "technology")
    S = pdfgen._styles(pal, False)
    t = pdfgen._table_flowable([["City", "Orders"], ["Jaipur", "842"], ["Indore", "610"]],
                               pal, S, pdfgen.AVAIL_W, "clean")
    assert sum(t._colWidths) <= pdfgen.AVAIL_W + 0.5 and t.hAlign == "CENTER"
    assert all(h is None for h in t._argH) and t.repeatRows == 1
    from reportlab.platypus import Paragraph
    assert all(isinstance(c, Paragraph) for row in t._cellvalues for c in row)
    kinds = {c[0] for c in t._bkgrndcmds} | {c[0] for c in t._linecmds}
    assert "BACKGROUND" in kinds and "ROWBACKGROUNDS" in kinds        # header fill + zebra kept
    grid = [c for c in t._linecmds if c[0] == "GRID"]
    assert not grid                                                   # clean = no vertical grid


def test_devanagari_still_shapes_through_any_design():
    r = pdfgen.make_pdf("नवरात्रि सेल प्लान", "# नोट\nनवरात्रि सेल के लिए बैनर तैयार है।", cover=True)
    assert r["qa"]["status"] == "pass" and not r["qa"]["issues"]
    txt = (PdfReader(io.BytesIO(r["data"])).pages[-1].extract_text() or "")
    assert txt.strip()


# ---------------------------------------------------------------- tool surface

def test_doc_studio_schema_and_result_carry_the_design(monkeypatch):
    from app.agent import tools as reg
    schema = next(t for t in reg.TOOLS if t["name"] == "doc_studio")["input_schema"]
    style_enum = schema["properties"]["style"]["enum"]
    assert {"auto", "professional", "finance", "technology", "festive"} <= set(style_enum)
    assert len(style_enum) == 17
    import asyncio
    from app.agent import docstudio_tools as dt

    class _T:
        tenant_id, conversation_id, user_id = "t1", "c1", "u1"
    seen = {}
    monkeypatch.setattr(dt, "_deliver",
                        lambda ctx, name, data, source: seen.update(
                            {"name": name, "data": data}) or {"file_id": "f1", "name": name})
    monkeypatch.setattr(dt, "_owner_bytes", lambda ctx, fid: ("n.pdf", b"%PDF-x"))
    monkeypatch.setattr("app.events.bus.publish", lambda *a, **k: None)
    out = asyncio.run(dt.doc_studio(_T(), "pdf", "Q3 Invoice and GST Summary", LONG))
    assert out["made"] == "pdf" and out["design"]["topic"] == "finance"
    assert "Design matched to the topic" in out["note"]
    assert seen["data"][:5] == b"%PDF-"
