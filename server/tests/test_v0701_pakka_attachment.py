"""v0.701 PAKKA ATTACHMENT (owner: "GO FIX 1 2 3 + SHEET IMPORT" after the attachment-flow audit).

1. a draft keeps its OWN copy of every attached file: the 24-hour chat-file sweep (frozen PC module, untouched) can
   delete the original and a next-day Bhejo / scheduled send / multi-day bulk still sends it;
2. a Google Sheet attached from Drive goes as a REAL .xlsx (was a PDF named .xlsx with the google-apps mime);
3. the id drive_find gives ("<account>~<id>") attaches (was always "Drive file nahi mili");
+ the size check happens before the download; Sheets import reads an Excel / CSV / Google Sheet straight from Drive.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import PcFile, session
from tests.test_email import FakeBox, _raw, run  # noqa: F401
from tests.test_life import conv_ctx

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
GSHEET = "application/vnd.google-apps.spreadsheet"


@pytest.fixture
def box(env, monkeypatch):
    b = FakeBox()
    b.add("201", _raw(("Ramesh", "ramesh@vendor.in"), "meghana@fnw.in", "Hi", "Namaste"))
    import app.mailbox.accounts as ma
    monkeypatch.setattr(ma, "boxes", lambda tenant: [b] if tenant == "default" else [])
    return b


class Drive:
    key, address = "acc2", "second@gmail.com"

    def __init__(self, files):
        self.files, self.downloads, self.exports = files, [], []

    def get(self, fid):
        if fid not in self.files:
            from app.drive.client import DriveError
            raise DriveError("nahi mili")
        return {"id": fid, **self.files[fid]}

    def download(self, fid):
        self.downloads.append(fid)
        return self.files[fid]["bytes"]

    def export(self, fid, mime):
        self.exports.append((fid, mime))
        return b"PK-real-xlsx" if mime == XLSX else b"%PDF-export"


@pytest.fixture
def drive(monkeypatch):
    import app.drive.service as ds
    d = Drive({"rep1": {"name": "Report.pdf", "mimeType": "application/pdf", "size": "9", "bytes": b"%PDF-rep1"},
               "sh1": {"name": "Stock", "mimeType": GSHEET},
               "big": {"name": "Huge.zip", "mimeType": "application/zip", "size": str(40 * 1024 * 1024), "bytes": b"x"},
               "csv1": {"name": "leads.csv", "mimeType": "text/csv", "size": "30",
                        "bytes": b"name,phone\nRavi,98000\nSita,97000\n"}})
    monkeypatch.setattr(ds, "_client_for", lambda tenant, key: d)
    return d


def _upload(name, data):
    from app.mailbox import service as ms
    return ms.store_bytes("default", name, data, direction="from_phone")


def _send(draft_id):
    from app import main
    with TestClient(main.app) as c:
        return c.post(f"/api/emails/{draft_id}/send").json()


def test_uploaded_file_survives_the_24h_sweep(box):
    f = _upload("Quote.pdf", b"%PDF-quote-bytes")
    out = run("email_draft", {"to": "kunal@x.in", "subject": "Quote", "body": "PDF attached",
                              "attachments": [{"file_id": f.id}]}, conv_ctx())
    assert out["attachments"] == ["Quote.pdf"]
    # the chat-file store deletes the original (what pc.cleanup_files does after 24 h)
    Path(f.stored_path).unlink()
    with session() as s:
        s.delete(s.get(PcFile, f.id))
    assert _send(out["draft_id"])["status"] == "sent"
    att = list(box.sent[0][0].iter_attachments())[0]
    assert att.get_filename() == "Quote.pdf" and att.get_payload(decode=True) == b"%PDF-quote-bytes"


def test_bulk_and_load_files_use_the_kept_copy(box):
    from app.mailbox import service as ms
    f = _upload("List.pdf", b"%PDF-list")
    desc = ms.describe_attachments("default", [{"file_id": f.id}])
    assert len(desc[0]["keep"]) == 64
    Path(f.stored_path).unlink()
    assert ms.load_files("default", desc) == [("List.pdf", "application/pdf", b"%PDF-list")]


def test_missing_upload_is_said_at_draft_time(box):
    from app.mailbox import service as ms
    f = _upload("Gone.pdf", b"%PDF")
    Path(f.stored_path).unlink()
    with pytest.raises(ms.MailError, match="ab server par nahi"):
        ms.describe_attachments("default", [{"file_id": f.id}])


def test_drive_find_ref_attaches(box, drive):
    out = run("email_draft", {"to": "kunal@x.in", "subject": "Report", "body": "Attached",
                              "attachments": [{"drive_file_id": "acc2~rep1"}]}, conv_ctx())
    assert out["attachments"] == ["Report.pdf"]
    assert _send(out["draft_id"])["status"] == "sent"
    att = list(box.sent[0][0].iter_attachments())[0]
    assert att.get_payload(decode=True) == b"%PDF-rep1"
    assert drive.downloads == ["rep1"]          # downloaded once at draft time, the send used the kept copy


def test_google_sheet_goes_as_real_xlsx(box, drive):
    out = run("email_draft", {"to": "kunal@x.in", "subject": "Stock", "body": "Sheet",
                              "attachments": [{"drive_file_id": "acc2~sh1"}]}, conv_ctx())
    assert out["attachments"] == ["Stock.xlsx"]
    assert _send(out["draft_id"])["status"] == "sent"
    att = list(box.sent[0][0].iter_attachments())[0]
    assert att.get_content_type() == XLSX and att.get_payload(decode=True) == b"PK-real-xlsx"
    assert drive.exports == [("sh1", XLSX)]


def test_google_sheet_as_pdf_when_asked(box, drive):
    from app.mailbox import service as ms
    d = ms.describe_attachments("default", [{"drive_file_id": "acc2~sh1", "format": "pdf"}])
    assert d[0]["name"] == "Stock.pdf" and d[0]["mime"] == "application/pdf"


def test_big_drive_file_refused_before_download(box, drive):
    from app.mailbox import service as ms
    with pytest.raises(ms.MailError, match="25 MB"):
        ms.describe_attachments("default", [{"drive_file_id": "acc2~big"}])
    assert drive.downloads == []


def test_kept_copies_are_swept_after_mail_keep_days(box):
    import os
    import time
    from app.mailbox import service as ms
    h = ms._keep("default", b"old-bytes")
    p = ms._keep_root("default") / h
    os.utime(p, (time.time() - 80 * 86400,) * 2)
    ms._keep("default", b"fresh-bytes")
    assert not p.exists() and ms._kept("default", h) is None
    assert ms._kept("default", "../../etc/passwd") is None


def test_sheet_import_from_drive(box, drive):
    from app.sheets import service as ss
    rows, name = ss.import_rows("default", {"drive_file": "acc2~csv1"})
    assert name == "leads.csv" and rows[0] == ["name", "phone"] and len(rows) == 3


def test_sheet_tool_schema_offers_drive_source():
    from app.agent import sheets_tools as st
    tool = next(t for t in st.SHEETS_TOOLS if t["name"] == "sheet_create")
    assert "drive_file" in tool["input_schema"]["properties"]["source"]["properties"]


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.864.0"
