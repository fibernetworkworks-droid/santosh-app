"""v0.794 HOOLA DOCUMENT KIT D0 + D1 (docs/DOCUMENT_KIT_PLAN.md): the dockit engine, the pdf_kit tool, the proof card
and the engine check - on real PDFs made in code (no mocks of the PDF work itself)."""
import asyncio
import io
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pikepdf
import pytest

from app.agent import admit, tools
from app.agent import pdfkit_tools as T
from app.dockit import check, convert, core, health, optimize, organize
from app.dockit.core import DocError
from app.quality import pdfcard as F

ROOT = Path(__file__).resolve().parent.parent


def run(c):
    return asyncio.run(c)


def pages_of(b: bytes) -> int:
    with pikepdf.open(io.BytesIO(b)) as p:
        return len(p.pages)


# ------------------------------------------------------------------------------------------ the engine
def test_page_grammar_every_way_she_writes_it():
    assert core.pages("1-3,5", 10) == [0, 1, 2, 4]
    assert core.pages("8-", 10) == [7, 8, 9]
    assert core.pages("-3", 10) == [0, 1, 2]
    assert core.pages("odd", 5) == [0, 2, 4] and core.pages("even", 5) == [1, 3]
    assert core.pages("last-2", 10) == [8, 9] and core.pages("first, last", 10) == [0, 9]
    assert core.pages("all-but-last", 4) == [0, 1, 2]
    assert core.pages("3-1", 5) == [2, 1, 0]
    assert core.pages("2 se 4", 9) == [1, 2, 3]
    assert core.pages([2, 4], 5) == [1, 3]
    assert core.pages("1,1", 3, allow_repeat=True) == [0, 0]
    with pytest.raises(DocError):
        core.pages("abc", 5)
    with pytest.raises(DocError):
        core.pages("20-30", 5)


def test_the_whole_proof_card_passes_here():
    rep = F.card()
    bad = [r for r in rep["rows"] if r["state"] == "FAIL"]
    assert not bad, bad
    assert rep["ran"] >= 23


def test_locked_pdf_never_opened_and_never_asks_in_chat():
    with pytest.raises(DocError) as e:
        organize.extract(F.locked_pdf(), "1")
    assert "password" in str(e.value) and "never asks" in str(e.value)


def test_limits_refused_before_any_work(monkeypatch):
    monkeypatch.setattr(core, "MAX_PAGES", 5)
    with pytest.raises(DocError, match="limit is 5"):
        organize.extract(F.text_pdf(8), "1")
    with pytest.raises(DocError, match="at least 2"):
        organize.merge([("a.pdf", F.text_pdf(1))])
    with pytest.raises(DocError):
        optimize.compress(F.text_pdf(1), target_kb=5)


def test_compress_never_grows_and_never_breaks_pages():
    src = F.text_pdf(3)
    r = optimize.compress(src, "extreme")
    assert r["after"] <= r["before"] and pages_of(r["bytes"]) == 3
    unchanged = optimize.compress(src, target_kb=10_000)
    assert unchanged["bytes"] is src and unchanged["met"]


def test_split_by_size_says_when_one_page_is_over():
    parts = organize.split(F.photo_pdf(2), "size", max_kb=20)
    assert all(p.get("over") for p in parts) and sum(len(p["pages"]) for p in parts) == 2


def test_repair_falls_back_to_pictures_only_when_needed():
    r = optimize.repair(F.broken_pdf())
    assert "kept" in r["method"]
    with pytest.raises(DocError):
        optimize.repair(b"%PDF-1.4 garbage garbage")


def test_photo_metadata_never_travels():
    from PIL import Image
    im = Image.new("RGB", (300, 200), (10, 120, 200))
    exif = Image.Exif()
    exif[0x010F] = "SecretPhoneMaker"
    b = io.BytesIO()
    im.save(b, "JPEG", exif=exif)
    pdf = convert.images_to_pdf([("x.jpg", b.getvalue())])
    assert b"SecretPhoneMaker" not in pdf


def test_check_refuses_a_bad_output():
    with pytest.raises(DocError, match="nothing was delivered"):
        check.pdf_out(b"%PDF-1.4 not really")
    with pytest.raises(DocError, match="pages"):
        check.pdf_out(F.text_pdf(2), expect_pages=3)
    assert "opens, 2 pages" in check.pdf_out(F.text_pdf(2), expect_pages=2)


def test_engine_check_reports_every_engine_truthfully():
    rep = health.check()
    names = {r["engine"] for r in rep["engines"]}
    assert {"pikepdf", "pypdfium2", "reportlab", "pillow", "libreoffice", "ocrmypdf", "ghostscript"} <= names
    assert rep["core_ok"] is True
    assert all(r["state"] in ("LIVE", "MISSING", "BROKEN") for r in rep["engines"])
    gs = next(r for r in rep["engines"] if r["engine"] == "ghostscript")
    assert "NOT used" in gs["detail"]                     # owner decision D2, said on every check


# ------------------------------------------------------------------------------------------ the tool
@pytest.fixture
def tool_env(monkeypatch):
    files = {"a": ("Bill A.pdf", F.text_pdf(3, "A")), "b": ("Bill B.pdf", F.text_pdf(2, "B")),
             "big": ("Photos.pdf", F.photo_pdf(3)), "twelve": ("Report.pdf", F.text_pdf(12)),
             "jpg": ("shop.jpg", F.noisy_photo(800, 600)), "jpg2": ("board.jpg", F.noisy_photo(600, 800, 2)),
             "lock": ("Statement.pdf", F.locked_pdf()), "doc": ("Quote.docx", F.word_file())}
    out = []

    def get(ctx, fid):
        if fid not in files:
            raise T.ToolError("not found")
        return files[fid]

    def put(ctx, name, data):
        out.append((name, data))
        return {"file_id": f"o{len(out)}", "name": name}
    monkeypatch.setattr(T, "_get", get)
    monkeypatch.setattr(T, "_put", put)
    return SimpleNamespace(ctx=SimpleNamespace(tenant_id="t1", conversation_id="c1", actor="owner"), out=out)


def test_registered_and_reachable_from_real_asks():
    assert "pdf_kit" in {t["name"] for t in tools.TOOLS} and tools.HANDLERS["pdf_kit"] is T.pdf_kit
    assert tools.FAMILY_OF["pdf_kit"] == "pdf_kit" and "pdf_tools" in tools.HANDLERS     # the old tool stays
    for ask in ("in teeno pdf ko jod do", "ye photos ko pdf bana do", "pdf ko 200 kb ka karo", "word ko pdf mein badlo",
                "pdf ke page 3 hata do", "split this pdf into separate pages", "pdf to jpg kar do", "compress pdf please",
                "is pdf ka size kam karo", "repair pdf jo khul nahi rahi"):
        assert "pdf_kit" in _in_view(ask), ask
    assert "pdf_kit" not in _in_view("make a pdf report on sales")      # making a PDF = doc_studio


def _in_view(ask: str) -> set[str]:
    from app.config import get_settings
    return {t["name"] for t in admit.plan_for(ask, get_settings()).specs()}


def test_label_and_prompt():
    from app.agent.labels_en import LABELS_EN
    assert LABELS_EN["pdf_kit"] == "Working on the PDF"
    p = (ROOT / "app" / "agent" / "prompts.py").read_text()
    assert "PDFs: pdf_kit = WORK ON HER PDF" in p and "= pdf_kit." in p


def test_reachable_on_a_call():
    from app import voice
    assert voice.registered("pdf_kit") and voice.call_route("pdf_kit")


def test_guide_and_not_yet_are_honest(tool_env):
    g = run(T.pdf_kit(tool_env.ctx, action="guide"))
    assert "NOT YET" in g["guide"] and "compare" in g["not_yet"] and g["engines"]["pikepdf"]
    with pytest.raises(T.ToolError, match="cannot 'compare' yet"):
        run(T.pdf_kit(tool_env.ctx, action="compare", file_id="a"))


def test_tool_merge_split_remove_extract(tool_env):
    m = run(T.pdf_kit(tool_env.ctx, action="merge", file_ids=["a", "b", "jpg"]))
    assert m["pages"] == 6 and m["merged"] == 3 and "checked" in m["checked"]
    s = run(T.pdf_kit(tool_env.ctx, action="split", file_id="twelve", mode="every", every=5))
    assert s["count"] == 3 and [p["pages"] for p in s["parts"]] == ["1-5", "6-10", "11-12"]
    r = run(T.pdf_kit(tool_env.ctx, action="remove", file_id="twelve", pages="1,2"))
    assert r["pages"] == 10
    e = run(T.pdf_kit(tool_env.ctx, action="extract", file_id="twelve", pages="last"))
    assert e["pages"] == 1 and pages_of(tool_env.out[-1][1]) == 1


def test_many_results_arrive_as_one_zip(tool_env):
    s = run(T.pdf_kit(tool_env.ctx, action="split", file_id="twelve", mode="each"))
    assert s["count"] == 12 and s["zip"]["name"].endswith(".zip")
    name, blob = tool_env.out[-1]
    assert len(zipfile.ZipFile(io.BytesIO(blob)).namelist()) == 12 and len(tool_env.out) == 1


def test_tool_compress_to_target_and_honest_note(tool_env):
    r = run(T.pdf_kit(tool_env.ctx, action="compress", file_id="big", target_kb=200))
    assert r["after_kb"] <= 200 and r["target_met"] and r["pages"] == 3
    t = run(T.pdf_kit(tool_env.ctx, action="compress", file_id="a", target_kb=5000))
    assert t["changed"] is False and "already" in t["say"]


def test_tool_photos_and_word_to_pdf(tool_env):
    r = run(T.pdf_kit(tool_env.ctx, action="to_pdf", file_ids=["jpg", "jpg2"], page_size="a4", margin="small"))
    assert len(r["made"]) == 1 and r["made"][0]["pages"] == 2
    sep = run(T.pdf_kit(tool_env.ctx, action="to_pdf", file_ids=["jpg", "jpg2"], separate=True))
    assert len(sep["made"]) == 2
    if convert.office_ready():
        w = run(T.pdf_kit(tool_env.ctx, action="to_pdf", file_ids=["doc"]))
        assert w["made"][0]["pages"] >= 1


def test_tool_pictures_text_info(tool_env):
    i = run(T.pdf_kit(tool_env.ctx, action="to_images", file_id="a", pages="1-2", format="png", dpi=72))
    assert i["count"] == 2
    x = run(T.pdf_kit(tool_env.ctx, action="extract_images", file_id="big"))
    assert x["count"] == 3
    none = run(T.pdf_kit(tool_env.ctx, action="extract_images", file_id="a"))
    assert none["count"] == 0 and "to_images" in none["say"]
    t = run(T.pdf_kit(tool_env.ctx, action="to_text", file_id="big"))
    assert t["no_text_pages"] == [1, 2, 3] and "file_read" in t["note"]
    info = run(T.pdf_kit(tool_env.ctx, action="info", file_ids=["a", "big", "jpg"]))
    kinds = [f.get("kind") or f.get("error") for f in info["files"]]
    assert kinds[0] == "text" and kinds[1].startswith("scanned") and kinds[2] == "not a PDF"


def test_tool_refuses_cleanly(tool_env):
    with pytest.raises(T.ToolError, match="password"):
        run(T.pdf_kit(tool_env.ctx, action="extract", file_id="lock", pages="1"))
    with pytest.raises(T.ToolError, match="is not a PDF.*to_pdf"):
        run(T.pdf_kit(tool_env.ctx, action="rotate", file_id="jpg"))
    with pytest.raises(T.ToolError, match="Which PDF"):
        run(T.pdf_kit(tool_env.ctx, action="rotate"))
    with pytest.raises(T.ToolError):
        run(T.pdf_kit(tool_env.ctx, action="merge", file_ids=["a", "nope"]))
    assert not tool_env.out                               # nothing half-delivered


def test_originals_are_never_changed(tool_env):
    before = tool_env.ctx and T._get(tool_env.ctx, "twelve")[1]
    run(T.pdf_kit(tool_env.ctx, action="rotate", file_id="twelve", degrees=90))
    assert T._get(tool_env.ctx, "twelve")[1] == before


def test_setup_script_and_vps_jobs():
    sh = (ROOT / "deploy" / "setup_docs.sh").read_text()
    assert "pdfplumber" in sh and "libreoffice-core" in sh and "python -m app.dockit check" in sh
    assert "ghostscript" not in sh.split("NOT")[0].lower().replace("ghostscript is", "")   # never apt-installed
    ops = (ROOT.parent / ".github" / "workflows" / "vps-ops.yml").read_text()
    for job in ("docs_setup)", "docs_check)", "pdf_card)", "- docs_setup", "- pdf_card"):
        assert job in ops, job
    assert "pdfplumber" in (ROOT / "requirements.txt").read_text()
