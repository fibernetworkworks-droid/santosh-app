"""v0.997 KHULA PITARA (owner, her BSNL Goa job: "WHY REPLY LIKE THIS FIND THE EXACT ROOT CAUSE ... WE WANT EVERYTHING
LIKE CLAUDE"). Root causes found in the code: (1) a RAR she attached was never opened - the file reader had no archive
support and the Python sandbox cannot run unrar - so Hoola wrote the email from other mails and guessed the months, the
totals and her GST number; (2) every file_read result was cut to 6,000 characters before the model saw it; (3) the email
body was markdown but markdown=false, so ** and | table pipes went out raw (and tables were never drawn); (4) the plan
card cut notes mid-word, listed a file it had only tried to read as "made", and listed every step twice."""
import asyncio
import io
import zipfile
from pathlib import Path

import pytest

FILES = Path(__file__).parent / "files"
ROOT = Path(__file__).resolve().parents[2]


def _pdf(text: str) -> bytes:
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 720, text)
    c.save()
    return buf.getvalue()


def _zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for n, b in files.items():
            z.writestr(n, b)
    return buf.getvalue()


def test_rar4_and_rar5_open_on_the_server():
    from app import archive
    for f, want in (("rar4_sample.rar", {"stest1.txt", "stest2.txt"}),
                    ("rar5_sample.rar", {"somedir/stest1.txt", "stest1.txt", "somedir/stest2.txt", "stest2.txt"})):
        r = archive.open_archive(f, (FILES / f).read_bytes())
        assert r["ok"] and {n for n, _ in r["files"]} == want, (f, r["note"])


def test_an_attached_archive_becomes_her_files_and_the_model_is_told(env):
    from app import chatfiles
    inv = _pdf("Invoice FNWINV032026 June 2026 Net payable 46,388.76")
    data = _zip({"BSNL/June.pdf": inv, "BSNL/copy/June.pdf": inv, "BSNL/July.pdf": _pdf("Invoice INVFNWGOA0602026 52,464.32")})
    out = chatfiles.store("t1", "BSNLGOAPAYMENTISSUE.zip", data)
    arc = out["archive"]
    assert arc["ok"] and len(arc["inside"]) == 3
    assert sum(1 for i in arc["inside"] if i.get("same_as")) == 1          # the duplicate copy is named as one
    ctx = chatfiles.context("t1", [out["file_id"]])
    assert "Opened: 3 file(s) inside" in ctx and all(i["file_id"] in ctx for i in arc["inside"])


def test_file_read_on_an_archive_reads_every_invoice(env):
    from app import chatfiles
    from app.agent import file_tools
    data = _zip({"June.pdf": _pdf("Net payable 46,388.76"), "July.pdf": _pdf("Net payable 52,464.32")})
    fid = chatfiles.store("t1", "pay.zip", data)["file_id"]
    r = file_tools._read("t1", fid)
    assert r["opened"] and r["count"] == 2
    text = " ".join(f.get("text", "") for f in r["files"])
    assert "46,388.76" in text and "52,464.32" in text


def test_an_archive_that_cannot_be_opened_is_said_never_filled_in(env):
    from app import chatfiles
    from app.agent import file_tools
    bad = b"Rar!\x1a\x07\x00" + b"\x00" * 64                        # a RAR header with nothing behind it
    out = chatfiles.store("t1", "broken.rar", bad)
    assert out["archive"]["ok"] is False
    assert "NOT OPENED - nothing inside this archive was read" in chatfiles.context("t1", [out["file_id"]])
    r = file_tools._read("t1", out["file_id"])
    assert r["opened"] is False and "Never take amounts" in r["rule"]


def test_no_path_escapes_and_programs_are_not_opened():
    from app import archive
    r = archive.open_archive("x.zip", _zip({"../../etc/evil.txt": b"hi", "a/b/c.txt": b"ok", "run.exe": b"MZ\x90\x00" + b"\x00" * 200}))
    names = {n for n, _ in r["files"]}
    assert names == {"etc/evil.txt", "a/b/c.txt"}
    assert any(s["name"] == "run.exe" for s in r["skipped"])


def test_too_many_files_stops_at_the_wall():
    from app import archive
    r = archive.open_archive("many.zip", _zip({f"f{i}.txt": b"x" for i in range(archive.MAX_MEMBERS + 5)}))
    assert len(r["files"]) == archive.MAX_MEMBERS and "Only the first" in r["note"]


def test_file_read_is_not_cut_at_6000():
    from app.agent import santosh
    assert santosh.RESULT_LIMIT["file_read"] >= 40000


def test_a_markdown_email_never_goes_out_with_raw_stars_or_pipes():
    from app.mailbox import mime
    body = "Dear Sir,\n\n**1. Summary**\n\n| Month | Invoice | Amount |\n|---|---|---|\n| June | FNWINV032026 | 46,388.76 |\n\n---\nThanks"
    assert mime.looks_md(body) and not mime.looks_md("Dear Sir, please release the payment.")
    html = mime.md_to_html(body)
    assert "<table" in html and "<td" in html and "<b>1. Summary</b>" in html and "<hr>" in html and "|" not in html
    plain = mime.md_to_plain(body)
    assert "**" not in plain and "|" not in plain and "---" not in plain and "FNWINV032026" in plain


def test_both_send_paths_treat_a_markdown_body_as_markdown():
    s = (ROOT / "server/app/mailbox/service.py").read_text()
    assert s.count("mime.looks_md(d.body)") == 2
    e = (ROOT / "server/app/agent/email_tools.py").read_text()
    assert "markdown=bool(markdown) or mime.looks_md(text)" in e


def test_the_email_card_shows_the_email_as_it_will_look():
    js = (ROOT / "server/app/static/console/v2.js").read_text()
    assert '<div class="mailprev textmd" aria-label="Email body">${md(p.body || \'\')}</div>' in js
    assert "data-mail-edit" in js


def test_plan_card_notes_end_on_a_word_and_made_is_only_what_was_made():
    from app.agent import goal
    note = ("All facts extracted: agreement details, GST timeline, BSNL contacts, payment history (0 for Goa, all for "
            "Nashik/Amravati). RAR's BSNLJUNE2026.pdf could not be unpacked in sandbox, so exact invoice amounts are "
            "not known yet and need her copy")
    c = goal.cut(note, 200)
    assert len(c) <= 200 and c.endswith("…") and not c.endswith("amo…")
    steps = [{"n": 1, "text": "Open the RAR", "state": "done", "note": "RAR is RAR4 with BSNLJUNE2026.pdf inside; could not unpack"},
             {"n": 2, "text": "Make the report", "state": "done", "note": "Report saved as Goa_dues.pdf"}]
    rep = goal.build_report(steps, "done", made=["eml_a0e9e9c180a1", "https://example.com/x"])
    assert "BSNLJUNE2026.pdf" not in rep["bana"] and "eml_a0e9e9c180a1" not in rep["bana"]
    assert "Goa_dues.pdf" in rep["bana"] and "https://example.com/x" in rep["bana"]


def test_the_plan_card_does_not_list_every_step_twice():
    js = (ROOT / "server/app/static/console/v2.js").read_text()
    assert "goalReport(p.report, steps.length > 0)" in js and "if (withSteps) r = {...r, hua: []};" in js
    d = (ROOT / "lib/ui/chat/hoola_cards_all.dart").read_text()
    assert "if (!stepsShown && _list('hua').isNotEmpty)" in d


def test_the_rules_are_in_both_prompts():
    from app.agent import core_prompt, prompts
    assert "never fill its figures" in core_prompt.CORE and "[blank] for her to fill" in core_prompt.CORE
    assert "never filled in from other mails or memory" in Path(prompts.__file__).read_text()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.999.63"
    assert "0.999.63+1061" in (ROOT / "pubspec.yaml").read_text()
