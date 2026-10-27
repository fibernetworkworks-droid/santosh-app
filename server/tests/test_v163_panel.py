"""v0.163 Side panel for finished work (SIDE_PANEL): "Banaya hua" lists every page / file / picture / video / website /
app Hoola made, her files open safely (only images, video, audio and PDF are viewable; everything else downloads),
Office as PDF, page source + versions + a panel-mode page bridge, and Share only through a Haan card."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.test_v161_stream import KEY

H = {"Authorization": f"Bearer {KEY}"}
PAGE = "<!doctype html><html><head><title>EMI</title></head><body><h1>EMI calculator</h1><script>x()</script></body></html>"


@pytest.fixture
def pn(env, monkeypatch):
    for k, v in (("SIDE_PANEL", "true"), ("API_KEY", KEY), ("PUBLIC_BASE_URL", "https://hoola.example.in"),
                 ("SECRET_KEY", "a-very-long-random-secret-for-tests-0123456789")):
        monkeypatch.setenv(k, v)
    from app.config import get_settings
    get_settings.cache_clear()
    from app import main
    with TestClient(main.app) as c:
        conv = c.post("/api/conversations", headers=H).json()["id"]
        yield c, conv


def _page(conv, versions=2):
    from app.db import Artifact, ArtifactVersion, session
    with session() as s:
        a = Artifact(tenant_id="default", conversation_id=conv, title="EMI calculator", summary="Loan EMI", version=versions,
                     status="ready")
        s.add(a)
        s.flush()
        for v in range(1, versions + 1):
            s.add(ArtifactVersion(artifact_id=a.id, version=v, html=PAGE.replace("EMI calculator", f"EMI calculator v{v}")))
        return a.id


def _file(name, data, direction="to_phone"):
    from app.mailbox import service as ms
    return ms.store_bytes("default", name, data, direction).id


def test_library_lists_everything_hoola_made(pn):
    c, conv = pn
    from app.events import bus
    from app.pc.service import download_path
    aid = _page(conv)
    pdf = _file("bill.pdf", b"%PDF-1.4 test")
    img = _file("poster.png", b"\x89PNG\r\n\x1a\n" + b"0" * 20)
    bus.publish(conv, "artifact", {"id": aid, "title": "EMI calculator", "version": 1, "status": "building"})
    bus.publish(conv, "artifact", {"id": aid, "title": "EMI calculator", "version": 2, "status": "ready", "summary": "Loan EMI"})
    bus.publish(conv, "pc_file", {"file_id": pdf, "name": "bill.pdf", "url": download_path(pdf)})
    bus.publish(conv, "photo_made", {"file_id": img, "name": "poster.png", "prompt": "Diwali poster"})
    bus.publish(conv, "motion", {"id": "mv_1", "title": "Sale reel", "url": "/api/motion/files/mv_1.mp4?exp=1&sig=x"})
    bus.publish(conv, "site_board", {"id": "site_1", "title": "Chai Point site", "status": "building",
                                     "preview": "https://hoola.example.in/api/site-preview/tok123/"})
    bus.publish(conv, "app_board", {"id": "app_1", "title": "Darzi app", "preview": "/api/app-preview/tokA/"})
    bus.publish(conv, "app_board", {"id": "app_2", "title": "Bad", "preview": "https://evil.example/x/"})
    items = c.get("/api/panel/library", headers=H).json()["items"]
    by = {i["type"]: i for i in items}
    assert set(by) >= {"page", "pdf", "image", "video", "website", "app"}
    assert by["page"]["ref"] == aid and by["page"]["version"] == 2 and by["page"]["status"] == "ready"   # latest state, once
    assert len([i for i in items if i["type"] == "page"]) == 1
    assert by["website"]["preview"] == "/api/site-preview/tok123/" and by["image"]["sub"] == "Diwali poster"
    bad = next(i for i in items if i["ref"] == "app_2")
    assert bad["preview"] == ""                                       # only our own preview pages
    assert [i["type"] for i in c.get("/api/panel/library?kind=pages", headers=H).json()["items"]] == ["page"]
    assert {i["ref"] for i in c.get("/api/panel/library?q=diwali", headers=H).json()["items"]} == {img}


def test_files_open_safely(pn):
    c, conv = pn
    png = _file("poster.png", b"\x89PNG\r\n\x1a\n0000")
    html = _file("evil.html", b"<script>parent.localStorage.getItem('hoola.console.token')</script>")
    svg = _file("logo.svg", b"<svg onload='alert(1)'/>")
    r = c.get(f"/api/panel/files/{png}", headers=H)
    assert r.status_code == 200 and r.headers["content-type"] == "image/png" and r.headers["content-disposition"].startswith("inline")
    assert r.headers["x-content-type-options"] == "nosniff"
    for fid in (html, svg):                                          # never rendered next to the console
        r = c.get(f"/api/panel/files/{fid}", headers=H)
        assert r.headers["content-type"] == "application/octet-stream" and r.headers["content-disposition"].startswith("attachment")
        assert "sandbox" in r.headers["content-security-policy"]
    info = c.get(f"/api/panel/files/{html}/info", headers=H).json()
    assert info["inline"] is False and info["text"] is True
    assert "localStorage" in c.get(f"/api/panel/files/{html}/text", headers=H).json()["text"]   # code view = text only
    assert c.get(f"/api/panel/files/{png}?download=1", headers=H).headers["content-disposition"].startswith("attachment")
    assert c.get(f"/api/panel/files/{png}/text", headers=H).status_code == 415
    assert c.get("/api/panel/files/file_nope", headers=H).status_code == 404
    from app.db import PcFile, session
    with session() as s:                                             # another owner's file: not hers
        s.get(PcFile, png).tenant_id = "someone_else"
    assert c.get(f"/api/panel/files/{png}", headers=H).status_code == 404


def test_office_as_pdf(pn, monkeypatch):
    c, conv = pn
    doc = _file("quote.docx", b"PK\x03\x04 fake docx")
    assert c.get(f"/api/panel/files/{doc}/pdf", headers=H).status_code == 404          # no Gotenberg on this server
    from app.net import media
    calls = []
    monkeypatch.setattr(media, "office_to_pdf", lambda name, data: calls.append(name) or b"%PDF-1.7 converted")
    r = c.get(f"/api/panel/files/{doc}/pdf", headers=H)
    assert r.status_code == 200 and r.content.startswith(b"%PDF") and r.headers["content-type"] == "application/pdf"
    c.get(f"/api/panel/files/{doc}/pdf", headers=H)
    assert calls == ["quote.docx"]                                    # cached
    png = _file("a.png", b"\x89PNG")
    assert c.get(f"/api/panel/files/{png}/pdf", headers=H).status_code == 415


def test_page_versions_source_and_panel_bridge(pn):
    c, conv = pn
    aid = _page(conv, versions=3)
    v = c.get(f"/api/panel/pages/{aid}/view?version=2", headers=H).json()
    assert v["version"] == 2 and v["url"].startswith(f"/a/{aid}/2?")              # same-server path
    src = c.get(f"/api/panel/pages/{aid}/source?version=1", headers=H).json()
    assert src["version"] == 1 and "EMI calculator v1" in src["html"]
    assert c.get(f"/api/panel/pages/{aid}/source", headers=H).json()["version"] == 3
    page = c.get(v["url"] + "&panel=1")
    csp = page.headers["content-security-policy"]
    assert page.status_code == 200 and "PANEL=1" in page.text and "hoola:'error'" in page.text
    assert "sandbox" in csp and "allow-same-origin" not in csp                     # opaque origin: no login, no cookies
    assert "PANEL=0" in c.get(v["url"]).text                                       # the phone app / plain link: as before
    assert "frame-src 'self' blob:" in c.get("/console/").headers["content-security-policy"]


def test_share_needs_a_haan_card(pn):
    c, conv = pn
    aid = _page(conv)
    card = c.post("/api/panel/share", json={"kind": "page", "id": aid, "conversation_id": conv}, headers=H).json()
    assert card["status"] == "pending" and card["url"] == ""
    from app.db import Artifact, Event, session
    with session() as s:
        assert s.get(Artifact, aid).share_token == ""                              # nothing public yet
        ev = s.scalars(select(Event).where(Event.conversation_id == conv, Event.kind == "share_ask")).all()
    assert ev and ev[-1].payload["status"] == "pending"
    from app.events import needs_her
    assert needs_her("share_ask", ev[-1].payload)
    done = c.post(f"/api/panel/share/{card['id']}", json={"approve": True}, headers=H).json()
    assert done["status"] == "approved" and done["url"].startswith("https://hoola.example.in/s/")
    with session() as s:
        assert s.get(Artifact, aid).share_token
    assert c.post(f"/api/panel/share/{card['id']}", json={"approve": False}, headers=H).json()["status"] == "approved"
    # a file: only Hoola's own files get a link, and only on her tap
    mine = _file("upload.pdf", b"%PDF", direction="mail")
    assert c.post("/api/panel/share", json={"kind": "file", "id": mine}, headers=H).status_code == 409
    made = _file("report.pdf", b"%PDF")
    card = c.post("/api/panel/share", json={"kind": "file", "id": made}, headers=H).json()
    no = c.post(f"/api/panel/share/{card['id']}", json={"approve": False}, headers=H).json()
    assert no["status"] == "rejected" and no["url"] == ""


def test_switch_off(pn, monkeypatch):
    c, conv = pn
    assert c.get("/api/console/config").json()["panel"] is True
    monkeypatch.setenv("SIDE_PANEL", "false")
    monkeypatch.setenv("CONSOLE_V2", "false")   # v0.170 CONSOLE_V2 (default on) turns the panel on by itself
    from app.config import get_settings
    get_settings.cache_clear()
    assert c.get("/api/console/config").json()["panel"] is False
    for url in ("/api/panel/library", "/api/panel/files/x", "/api/panel/pages/x/view"):
        assert c.get(url, headers=H).status_code == 404
