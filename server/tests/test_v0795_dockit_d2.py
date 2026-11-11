"""v0.795 HOOLA DOCUMENT KIT D2 (docs/DOCUMENT_KIT_PLAN.md): stamps + edit through the pdf_kit tool, on real PDFs."""
import asyncio
import io
from types import SimpleNamespace

import pikepdf
import pytest

from app.agent import pdfkit_tools as T
from app.agent import toolsearch
from app.agent import tools
from app.dockit import convert, edit, stamp
from app.dockit.core import DocError
from app.quality import pdfcard as F


def run(c):
    return asyncio.run(c)


@pytest.fixture
def env(monkeypatch):
    files = {"r": ("Report.pdf", F.text_pdf(6)), "logo": ("logo.png", F.logo_png()), "form": ("Form.pdf", F.form_pdf()),
             "risky": ("Risky.pdf", F.risky_pdf()), "pdf2": ("Two.pdf", F.text_pdf(2))}
    out = []
    monkeypatch.setattr(T, "_get", lambda ctx, fid: files[fid] if fid in files else (_ for _ in ()).throw(T.ToolError("not found")))

    def put(ctx, name, data):
        out.append((name, data))
        return {"file_id": f"o{len(out)}", "name": name}
    monkeypatch.setattr(T, "_put", put)
    return SimpleNamespace(ctx=SimpleNamespace(tenant_id="t1", conversation_id="c1", actor="owner"), out=out)


def text(b: bytes, page: str = "1") -> str:
    return convert.page_texts(b, page)[0]


def test_every_d2_action_is_in_the_schema_and_the_schema_is_valid():
    spec = next(t for t in tools.TOOLS if t["name"] == "pdf_kit")
    enum = spec["input_schema"]["properties"]["action"]["enum"]
    for a in T.D2:
        assert a in enum and a in T.ACTIONS
    assert toolsearch.schema_ok(spec)
    assert "watermark" not in T.NOT_YET and "sign" in T.NOT_YET


def test_page_numbers_through_the_tool(env):
    r = run(T.pdf_kit(env.ctx, action="page_numbers", file_id="r", text="Page {n} of {p}", position="top-right",
                      skip_first=1))
    b = env.out[-1][1]
    assert r["pages"] == 6 and "Page" not in text(b, "1") and "Page 1 of 6" in text(b, "2")
    run(T.pdf_kit(env.ctx, action="page_numbers", file_id="r", text="{n}", digits="devanagari", start=5))
    assert "५" in text(env.out[-1][1], "1")
    with pytest.raises(T.ToolError, match=r"\{n\}"):
        run(T.pdf_kit(env.ctx, action="page_numbers", file_id="r", text="no number here"))


def test_watermark_text_logo_and_a_non_picture_refused(env):
    run(T.pdf_kit(env.ctx, action="watermark", file_id="r", text="गोपनीय", opacity=0.2, mosaic=True))
    assert "गोपनीय" in text(env.out[-1][1])
    run(T.pdf_kit(env.ctx, action="watermark", file_id="r", image_file_id="logo", position="bottom-right", rotation=0))
    with pytest.raises(T.ToolError, match="not a picture"):
        run(T.pdf_kit(env.ctx, action="watermark", file_id="r", image_file_id="pdf2"))
    with pytest.raises(T.ToolError, match="watermark text"):
        run(T.pdf_kit(env.ctx, action="watermark", file_id="r"))


def test_header_footer_crop_and_refusal(env):
    run(T.pdf_kit(env.ctx, action="header_footer", file_id="r", header={"right": "{date}"}, footer={"center": "{n}/{p}"}))
    assert "3/6" in text(env.out[-1][1], "3")
    c = run(T.pdf_kit(env.ctx, action="crop", file_id="r", top="10%", bottom="10%"))
    assert c["pages_cropped"] == 6
    with pytest.raises(T.ToolError, match="smaller than half an inch"):
        run(T.pdf_kit(env.ctx, action="crop", file_id="r", left="60%", right="60%"))


def test_add_her_signature_and_the_whiteout_warning(env):
    r = run(T.pdf_kit(env.ctx, action="add", file_id="r", items=[
        {"type": "image", "page": "last", "x": 140, "y": 250, "w": 40, "file_id": "logo"},
        {"type": "text", "page": "last", "x": 140, "y": 270, "text": "Signed 11 Nov 2026", "size": 10},
        {"type": "whiteout", "page": 1, "x": 10, "y": 40, "w": 80, "h": 10}]))
    assert r["added"] == 3 and "HIDES" in r["note"] and "redaction" in r["note"]
    assert "Signed 11 Nov 2026" in text(env.out[-1][1], "6")
    with pytest.raises(T.ToolError, match="type ="):
        run(T.pdf_kit(env.ctx, action="add", file_id="r", items=[{"type": "explode"}]))


def test_highlight_found_and_not_found(env):
    r = run(T.pdf_kit(env.ctx, action="highlight", file_id="r", term="Line 3:"))
    assert r["found"] == 6
    with pytest.raises(T.ToolError, match="not found"):
        run(T.pdf_kit(env.ctx, action="highlight", file_id="r", term="zzzz nothing"))


def test_metadata_bookmarks_flatten(env):
    m = run(T.pdf_kit(env.ctx, action="metadata", file_id="r", title="Quote", author="Hoola"))
    assert m["after"]["title"] == "Quote"
    b = run(T.pdf_kit(env.ctx, action="bookmarks", file_id="r", marks=[{"title": "A", "page": 1}, {"title": "B", "page": 4}]))
    assert b["bookmarks"] == 2
    with pytest.raises(T.ToolError, match="points at page 9"):
        run(T.pdf_kit(env.ctx, action="bookmarks", file_id="r", marks=[{"title": "X", "page": 9}]))
    f = run(T.pdf_kit(env.ctx, action="flatten", file_id="form"))
    assert f["form_fields"] == 2 and "Ramesh" in text(env.out[-1][1])


def test_printing_layouts(env):
    n = run(T.pdf_kit(env.ctx, action="nup", file_id="r", per_sheet=4))
    assert n["pages"] == 2
    bk = run(T.pdf_kit(env.ctx, action="booklet", file_id="r"))
    assert bk["pages"] == 4 and bk["blank_pages_added"] == 2 and "SHORT edge" in bk["print"]
    ft = run(T.pdf_kit(env.ctx, action="fit", file_id="r", sheet="letter"))
    with pikepdf.open(io.BytesIO(env.out[-1][1])) as p:
        assert [round(float(x)) for x in p.pages[0].mediabox] == [0, 0, 612, 792]
    assert ft["pages"] == 6
    g = run(T.pdf_kit(env.ctx, action="grayscale", file_id="r"))
    assert g["pages"] == 6


def test_sanitize_and_attachments(env):
    a = run(T.pdf_kit(env.ctx, action="attachments", file_id="risky"))
    assert a["count"] == 1 and env.out[-1] == ("notes.txt", b"secret attached notes")
    s = run(T.pdf_kit(env.ctx, action="sanitize", file_id="risky"))
    assert any("opening" in x for x in s["removed"]) and any("attached" in x for x in s["removed"])
    none = run(T.pdf_kit(env.ctx, action="attachments", file_id="r"))
    assert none["count"] == 0


def test_text_in_hindi_and_rupee_is_drawn_not_dropped():
    b, _ = edit.add(F.text_pdf(1), [{"type": "text", "page": 1, "x": 20, "y": 20, "text": "कुल ₹1,250 स्वीकृत"}])
    t = text(b)
    assert "कुल" in t and "1,250" in t and ("₹" in t or "Rs" in t)


def test_colour_and_limits():
    assert stamp.color("red") == stamp.color("#d32f2f") and stamp.color("#fff") == (1.0, 1.0, 1.0)
    with pytest.raises(DocError):
        stamp.color("not-a-colour")
    with pytest.raises(DocError):
        stamp.page_numbers(F.text_pdf(1), size=200)
    with pytest.raises(DocError):
        edit.add(F.text_pdf(1), [{"type": "text"}] * 201)


def test_guide_names_every_d2_action():
    g = run(T.pdf_kit(SimpleNamespace(tenant_id="t", conversation_id="c"), action="guide"))["guide"]
    for word in ("page_numbers", "watermark", "header_footer", "crop", "highlight", "booklet", "sanitize", "Bates"):
        assert word in g, word
