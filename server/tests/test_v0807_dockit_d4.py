"""v0.807 HOOLA DOCUMENT KIT D4 (docs/DOCUMENT_KIT_PLAN.md): searchable scans, PDF -> Word / Excel / PowerPoint,
PDF/A and web page -> PDF, through the pdf_kit tool on real files."""
import asyncio
import http.server
import io
import os
import threading
from types import SimpleNamespace

import pytest

from app.agent import pdfkit_tools as T
from app.agent import toolsearch, tools
from app.dockit import archive, convert, fromdoc, ocrlayer
from app.dockit.core import DocError
from app.quality import pdfcard as F

needs_ocr = pytest.mark.skipif(not ocrlayer.ready(), reason="tesseract not installed")


def run(c):
    return asyncio.run(c)


@pytest.fixture
def env(monkeypatch):
    files = {"scan": ("Bill scan.pdf", F.scanned_text_pdf()), "tbl": ("Quote.pdf", F.table_pdf()),
             "bad": ("Wrong total.pdf", F.table_pdf("4,999.00")), "r": ("Report.pdf", F.text_pdf(3)),
             "font": ("Archive.pdf", F.embedded_font_pdf())}
    out = []
    monkeypatch.setattr(T, "_get", lambda ctx, fid: files[fid])

    def put(ctx, name, data):
        out.append((name, data))
        return {"file_id": f"o{len(out)}", "name": name}
    monkeypatch.setattr(T, "_put", put)
    return SimpleNamespace(ctx=SimpleNamespace(tenant_id="t1", conversation_id="c1", actor="owner"), out=out)


def test_schema_and_not_yet():
    spec = next(t for t in tools.TOOLS if t["name"] == "pdf_kit")
    for a in T.D4 + ("web_to_pdf",):
        assert a in spec["input_schema"]["properties"]["action"]["enum"]
    assert toolsearch.schema_ok(spec)
    assert "OCR" not in T.NOT_YET and "Aadhaar eSign" in T.NOT_YET


def test_indian_numbers():
    assert fromdoc.number("1,23,456.50") == 123456.5 and fromdoc.number("₹ 1,200") == 1200
    assert fromdoc.number("(450)") == -450 and fromdoc.number("12.5%") == 0.125 and fromdoc.number("Rs. 99") == 99
    assert fromdoc.number("2024-11-01") is None and fromdoc.number("Atta") is None and fromdoc.number("") is None


@needs_ocr
def test_ocr_through_the_tool(env):
    r = run(T.pdf_kit(env.ctx, action="ocr", file_id="scan", language="hindi"))
    assert r["pages_read"] == [1] and "hin" in r["languages"] and "Sharma" in convert.page_texts(env.out[-1][1])[0]
    t = run(T.pdf_kit(env.ctx, action="ocr", file_id="r"))
    assert t["changed"] is False and "force=true" in t["say"]


def test_excel_word_powerpoint(env):
    x = run(T.pdf_kit(env.ctx, action="to_excel", file_id="tbl"))
    assert x["name"].endswith(".xlsx") and x["tables"] == 1 and x["numbers"] >= 4 and not x["notes"]
    bad = run(T.pdf_kit(env.ctx, action="to_excel", file_id="bad"))
    assert any("add up to 4650.5" in n for n in bad["notes"])
    w = run(T.pdf_kit(env.ctx, action="to_word", file_id="tbl"))
    assert w["name"].endswith(".docx") and w["tables"] == 1 and w["headings"] >= 1 and "approximate" in w["notes"][0]
    p = run(T.pdf_kit(env.ctx, action="to_powerpoint", file_id="r"))
    assert p["name"].endswith(".pptx") and p["slides"] == 3


def test_pdfa_is_never_called_compliant_without_validation(env, monkeypatch):
    monkeypatch.setattr(archive.shutil, "which", lambda name: None)
    r = run(T.pdf_kit(env.ctx, action="pdfa", file_id="font"))
    assert r["validated"] is False and r["compliant"] is None and "NOT validated" in r["say"]
    with pytest.raises(T.ToolError, match="mode=pages"):
        run(T.pdf_kit(env.ctx, action="pdfa", file_id="r", pdfa_mode="keep"))


def test_used_fonts_only():
    assert archive.font_problems(F.embedded_font_pdf()) == []
    assert "Helvetica" in archive.font_problems(F.text_pdf(1))


def test_web_to_pdf_refuses_private_addresses(env):
    for u in ("http://127.0.0.1/x", "http://localhost:8077/", "file:///etc/passwd", "http://169.254.169.254/"):
        with pytest.raises(T.ToolError):
            run(T.pdf_kit(env.ctx, action="web_to_pdf", url=u))


def _chromium_ok() -> bool:
    try:
        from playwright.sync_api import sync_playwright
        kw = {"headless": True, "args": ["--no-sandbox"]}
        if os.environ.get("HOOLA_CHROMIUM"):
            kw["executable_path"] = os.environ["HOOLA_CHROMIUM"]
        with sync_playwright() as pw:
            pw.chromium.launch(**kw).close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _chromium_ok(), reason="Chromium not launchable here")
def test_web_to_pdf_prints_a_real_page_and_blocks_its_private_requests(monkeypatch):
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = (b"<html><head><title>Hoola test page</title></head><body><h1>Rate card 2026</h1>"
                    b"<img src='http://10.0.0.5/secret.png'></body></html>")
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass
    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    from app.agent import scrape_tools
    real = scrape_tools._guard_url
    seen = []

    def guard(u):                                     # the test page itself is local; its private image is not allowed
        seen.append(u)
        if u.startswith(f"http://127.0.0.1:{srv.server_port}"):
            return u
        return real(u)
    monkeypatch.setattr(scrape_tools, "_guard_url", guard)
    try:
        pdf, title = archive.url_to_pdf(f"http://127.0.0.1:{srv.server_port}/", timeout_s=20)
    finally:
        srv.shutdown()
    assert title == "Hoola test page" and "Rate card 2026" in convert.page_texts(pdf)[0]
    assert any("10.0.0.5" in u for u in seen)          # the private image was checked (and refused by the real guard)


@needs_ocr
def test_redaction_text_layer_never_brings_the_secret_back():
    from app.dockit import secure
    pdf = F.id_pdf()
    f = secure.find(pdf, list(secure.DEFAULT_PRESETS))
    r = secure.redact(pdf, f["hits"], presets=list(secure.DEFAULT_PRESETS))
    t = " ".join(convert.page_texts(r["bytes"]))
    assert r["text_layer_pages"] == [1] and "Name" in t and "ABCPE1234F" not in t and "98765" not in t


def test_ocr_refuses_plainly_without_the_reader(monkeypatch):
    monkeypatch.setattr(ocrlayer, "ready", lambda: False)
    with pytest.raises(DocError, match="not installed"):
        ocrlayer.searchable(F.scanned_text_pdf())
