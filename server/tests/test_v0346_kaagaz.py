"""v0.346 KAAGAZ (App Sahayak Phase 12): a PDF document field (prescription, ID proof, bill, resume) on both platforms:
the system file picker (no permission), the outbox upload, and a server that keeps only plain PDFs (10 MB, opens, not
encrypted, no scripts / launch actions / attachments / XFA - in the bytes AND in the PDF's own structure), serves them only
as downloads to the sender / staff / the owner, and never lets a PDF sit in a photo field."""
import io
import json
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from tests.test_v0314_app_backend import _built
from tests.test_v0319_app_features import _jpeg, _member
from tests.test_v128_appdesign import T
from tests.test_v132_android import droid_env  # noqa: F401  (fixture)

FIX = Path(__file__).resolve().parents[1] / "app/appmaker/android/fixture/spec.json"


def _pdf(js=False, attach=False, pw=""):
    w = PdfWriter()
    w.add_blank_page(200, 200)
    if js:
        w.add_js("app.alert('x');")
    if attach:
        w.add_attachment("x.exe", b"MZ")
    if pw:
        w.encrypt(pw)
    b = io.BytesIO()
    w.write(b)
    return b.getvalue()


def test_pdf_upload_checks_and_serving(droid_env):
    from app.appmaker import backend as BE
    from app.main import app
    c = TestClient(app)
    aid, conv, key, _be = _built(droid_env)
    api = f"/api/app-api/{key}"
    ha, hb = _member(c, api, "asha@example.com"), _member(c, api, "ravi@example.com")
    pdf = _pdf()
    up = c.post(f"{api}/files", content=pdf, headers={**ha, "Content-Type": "application/pdf"}).json()
    assert up["kind"] == "pdf" and up["pages"] == 1 and up["id"].startswith("f_")
    got = c.get(f"{api}/files/{up['id']}", headers=ha)
    assert got.status_code == 200 and got.content == pdf                       # kept byte for byte
    assert got.headers["content-type"] == "application/pdf" and got.headers["content-security-policy"] == "sandbox"
    assert got.headers["content-disposition"].startswith("attachment")         # never opened inside a page
    assert c.get(f"{api}/files/{up['id']}", headers=hb).status_code == 404    # another customer: nothing
    assert c.get(f"/api/apps/{aid}/files/{up['id']}").headers["content-type"] == "application/pdf"   # she sees it
    # refused: scripts, attachments, a password, broken, too big
    for bad, code in ((_pdf(js=True), 415), (_pdf(attach=True), 415), (_pdf(pw="x"), 415), (b"%PDF-1.4 broken", 415),
                      (b"%PDF-" + b"0" * (10 * 1024 * 1024), 413)):
        assert c.post(f"{api}/files", content=bad, headers=ha).status_code == code
    # a JavaScript action hidden in a compressed object stream is still caught by the structure check
    import pypdf.generic as G
    w = PdfWriter()
    w.add_blank_page(200, 200)
    w._root_object[G.NameObject("/OpenAction")] = G.DictionaryObject({G.NameObject("/S"): G.NameObject("/JavaScript"),
                                                                     G.NameObject("/JS"): G.TextStringObject("x")})
    w.compress_identical_objects()
    b = io.BytesIO()
    w.write(b)
    assert BE._pdf_risky(__import__("pypdf").PdfReader(io.BytesIO(b.getvalue())))
    # a file field takes the PDF; a photo field refuses it
    c.post(f"/api/apps/{aid}/data_change", json={"ops": {"add": [{"coll": "orders", "key": "rx", "label": "Prescription", "type": "file"}]}})
    pid = c.get(f"/api/app-content/{key}").json()["lists"]["products"][0]["id"]
    base = {"name": "Asha", "phone": "9876543210", "cart": [{"id": pid, "qty": 1}]}
    row = c.post(f"{api}/c/orders", json={**base, "rx": up["id"]}, headers=ha).json()
    assert row["rx"] == up["id"]
    c.post(f"/api/apps/{aid}/data_change", json={"ops": {"add": [{"coll": "orders", "key": "pic", "label": "Photo", "type": "photo"}]}})
    assert c.post(f"{api}/c/orders", json={**base, "pic": up["id"]}, headers=ha).status_code == 400
    img = c.post(f"{api}/files", content=_jpeg(), headers={**ha, "Content-Type": "image/jpeg"}).json()
    assert c.post(f"{api}/c/orders", json={**base, "rx": img["id"]}, headers=ha).status_code == 200   # a photo of the paper is fine


def test_complex_lists_take_documents_as_pdf():
    from app.appmaker import backend as BE
    assert BE.DOC_NAME.search("prescription") and BE.DOC_NAME.search("kyc_proof") and not BE.DOC_NAME.search("profile_photo")


def test_kits_and_generators():
    from app.appmaker.android import gen as AG
    from app.appmaker.android import prompts as AP
    from app.appmaker.ios import prompts as IP
    be = {"collections": [{"key": "requests", "label": "Requests", "rules": {"create": "member"},
                           "fields": [{"key": "rx", "label": "Prescription", "type": "file"}]}]}
    assert 'FileField("Prescription", "rx")' in AG.fallback_screen({"id": "book", "label": "Book"}, ["book"], [], be)
    assert "@Composable FileField(label: String, key: String)" in AP.kit_sheet() and "[file]" in AP.backend_line(be)
    assert "FileRow" in IP.KIT_SHEET
    root = Path(__file__).resolve().parents[1] / "app/appmaker"
    pro = (root / "android/template/app/src/main/java/hoola/kit/Pro.kt").read_text()
    assert "ActivityResultContracts.OpenDocument()" in pro and 'arrayOf("application/pdf")' in pro and "READ_EXTERNAL_STORAGE" not in pro
    assert '"application/pdf"' in (root / "android/template/app/src/main/java/hoola/kit/Backend.kt").read_text()
    sw = (root / "ios/template/Sources/Kit/Pro.swift").read_text()
    assert ".fileImporter(isPresented: $open, allowedContentTypes: [.pdf])" in sw and "startAccessingSecurityScopedResource" in sw
    assert 'case "file":' in (root / "ios/template/Sources/Kit/Accounts.swift").read_text()
    assert "pdf ok" in (root / "android/template/app/src/main/java/hoola/kit/E2e.kt").read_text()
    assert "pdf ok" in (root / "ios/template/Sources/Kit/E2e.swift").read_text()
