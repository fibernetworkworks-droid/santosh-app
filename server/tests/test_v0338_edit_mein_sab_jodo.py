"""v0.338 EDIT MEIN SAB JODO (owner: "IN EDIT MODE ADD ALL ATTACHMENT FUNCTIONS IMAGE, VIDEO, FILES ETC"): in Edit mode
she adds a photo, a video (her file or a YouTube link), an audio clip or a file to download, below anything she taps -
her own hands, no AI. Files are accepted only when their bytes match their kind and within size limits; pages carry
placeholders the builder turns into the right address for each page depth; an added piece goes as one with "Hatao";
and photos in the edit preview can be picked again (they lost their edit number inside <picture> since v0.295)."""
import io
import json
import re
import threading
import functools
import http.server
import socketserver

import pytest

from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 2000
PDF = b"%PDF-1.4\n" + b"x" * 3000 + b"\n%%EOF"
MP3 = b"ID3\x04\x00" + b"\x00" * 1500


def _png() -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (900, 600), (200, 120, 60)).save(b, "PNG")
    return b.getvalue()


def test_files_must_be_what_they_say(tmp_path):
    from app.site import media as M
    v = M.add(tmp_path, MP4, "Shop tour.MP4", "Dukaan ka video")
    assert v["kind"] == "video" and v["name"] == "dukaan-ka-video" and (tmp_path / "media" / "dukaan-ka-video.mp4").exists()
    assert M.add(tmp_path, MP4, "x.mp4", "Dukaan ka video")["name"] == "dukaan-ka-video-2"       # never overwrites
    assert M.add(tmp_path, PDF, "Menu.pdf")["kind"] == "file" and M.add(tmp_path, MP3, "bhajan.mp3")["kind"] == "audio"
    for data, name, why in ((b"MZ\x90\x00" + b"\x00" * 500, "menu.pdf", "andar kuch aur"),     # a program renamed .pdf
                            (b"PK\x03\x04junk", "price.xlsx", "andar kuch aur"),
                            (PDF, "virus.exe", "Yeh file nahi lagti"),
                            (b"", "a.pdf", "khaali"),
                            (b"%PDF-" + b"x" * (21 * 1024 * 1024), "big.pdf", "20.0 MB tak")):
        with pytest.raises(M.MediaError) as e:
            M.add(tmp_path, data, name)
        assert why in str(e.value), (name, str(e.value))
    assert [i["kind"] for i in M.manifest(tmp_path)] == ["video", "video", "file", "audio"]


def _site(S):
    v = S.new(T, "Sharma Sweets mithai dukaan ki website", name="Sharma Sweets", answers={"phone": "9876543210"})
    S.approve_plan(T, v["id"], pages=["contact"])
    S.choose_look(T, v["id"], 0)
    assert S._load(v["id"]).status == "ready"
    S.edit_mode(T, v["id"])
    return v["id"]


def _e_of(S, sid, key, tag="p"):
    html = S._sections(S._load(sid))[key]["html"]
    m = re.search(rf'<{tag}\b[^>]*data-e="(\d+)"', html)
    assert m, (key, html[:300])
    return m.group(1)


def test_she_adds_every_kind_and_the_site_shows_it(site_env):
    from app.site import service as S
    sid = _site(S)
    keys = list(S._sections(S._load(sid)))
    home = next(k for k in keys if k.startswith("home__") and k != "home__hero")
    contact = next(k for k in keys if k.startswith("contact__"))
    vid = S.add_media(T, sid, MP4, "tour.mp4", "Dukaan ka video")["name"]
    pdf = S.add_media(T, sid, PDF, "Menu.pdf", "Mithai menu")["name"]
    song = S.add_media(T, sid, MP3, "jingle.mp3", "Jingle")["name"]
    photo = S.add_photo(T, sid, _png(), "", "Kaju katli thali")["name"]
    ins = lambda key, spec: S.edit_element(T, sid, key, _e_of(S, sid, key), "insert", json.dumps(spec))   # noqa: E731
    assert "video jodi" in ins(home, {"kind": "video", "name": vid, "caption": "Hamari <dukaan>"})["say"]
    ins(home, {"kind": "file", "name": pdf, "caption": "Menu download"})
    ins(home, {"kind": "audio", "name": song})
    ins(home, {"kind": "youtube", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "caption": "Tyohar special"})
    ins(home, {"kind": "photo", "name": photo, "caption": "Thali"})
    ins(contact, {"kind": "video", "name": vid})                              # a page one level deep
    for bad, why in (({"kind": "youtube", "url": "https://evil.example/x"}, "YouTube link nahi"),
                     ({"kind": "video", "name": pdf}, "file nahi mili"),        # a PDF is not a video
                     ({"kind": "photo", "name": "nope"}, "photo is website mein nahi"),
                     ({"kind": "exe"}, "chuniye")):
        with pytest.raises(S.SiteError) as e:
            ins(home, bad)
        assert why in str(e.value)
    r = S._load(sid)
    live = S._assemble_live(r)
    page = (live / "index.html").read_text()
    assert f'src="assets/media/{vid}.mp4"' in page and "controls" in page and "Hamari &lt;dukaan&gt;" in page
    assert f'href="assets/files/{pdf}.pdf"' in page and "download" in page and "Menu download (PDF, 3 KB)" in page
    assert f'src="assets/media/{song}.mp3"' in page and 'data-hs-yt="dQw4w9WgXcQ"' in page
    assert f"assets/img/{photo}-" in page and "<figcaption>Thali</figcaption>" in page
    assert (live / "assets" / "media" / f"{vid}.mp4").read_bytes() == MP4 and (live / "assets" / "files" / f"{pdf}.pdf").exists()
    deep = (live / "contact" / "index.html").read_text()
    assert f'src="../assets/media/{vid}.mp4"' in deep                     # the right address one level down
    assert "data-e=" not in page                                           # the live site never carries edit numbers
    from app.site import checks as C
    assert C.link_scan(live) == []
    # remove the added video in one go (its figure + caption), then Undo brings it back
    html = S._sections(S._load(sid))[home]["html"]
    ve = re.search(rf'<video[^>]*data-e="(\d+)"[^>]*data-hoola-media="{vid}"|<video[^>]*data-hoola-media="{vid}"[^>]*data-e="(\d+)"', html)
    S.edit_element(T, sid, home, ve.group(1) or ve.group(2), "remove")
    after = S._sections(S._load(sid))[home]["html"]
    assert f'data-hoola-media="{vid}"' not in after and "Hamari" not in after and f'data-hoola-file="{pdf}"' in after
    S.undo_edit(T, sid)
    assert f'data-hoola-media="{vid}"' in S._sections(S._load(sid))[home]["html"]


def test_photos_can_be_picked_in_the_edit_preview(site_env):
    from app.site import service as S
    sid = _site(S)
    photo = S.add_photo(T, sid, _png(), "", "Dukaan")["name"]
    home = next(k for k in S._sections(S._load(sid)) if k.startswith("home__") and k != "home__hero")
    S.edit_element(T, sid, home, _e_of(S, sid, home), "insert", json.dumps({"kind": "photo", "name": photo}))
    edit = (S._assemble_edit(S._load(sid)) / "index.html").read_text()
    assert re.search(rf'<img [^>]*data-e="\d+" data-hoola-img="{photo}"', edit)     # inside <picture>, still pickable
    live = (S._assemble_live(S._load(sid)) / "index.html").read_text()
    assert "data-e=" not in live


def test_the_edit_toolbar_offers_add_in_a_real_browser(site_env):
    sync_api = pytest.importorskip("playwright.sync_api")
    import os
    from app.site import service as S
    sid = _site(S)
    photo = S.add_photo(T, sid, _png(), "", "Dukaan")["name"]
    home = next(k for k in S._sections(S._load(sid)) if k.startswith("home__") and k != "home__hero")
    S.edit_element(T, sid, home, _e_of(S, sid, home), "insert", json.dumps({"kind": "photo", "name": photo}))
    out = S._assemble_edit(S._load(sid))
    from app.site import build as B
    (out / "assets" / "hoola-edit.js").write_bytes((B.ASSETS / "hoola-edit.js").read_bytes())
    page = (out / "index.html").read_text().replace("</body>", '<script src="assets/hoola-edit.js"></script></body>')
    (out / "index.html").write_text(page)
    H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(out))
    H.log_message = lambda *a: None
    srv = socketserver.TCPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with sync_api.sync_playwright() as p:
            b = p.chromium.launch(**({"executable_path": os.environ["HOOLA_CHROMIUM"]} if os.environ.get("HOOLA_CHROMIUM") else {}))
            pg = b.new_page()
            pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/")
            pg.evaluate("window.__msgs = []; window.addEventListener('message', e => window.__msgs.push(e.data))")
            pg.click(f'img[data-hoola-img="{photo}"]')
            labels = pg.eval_on_selector_all("#hoola-ebar button", "bs => bs.map(b => b.textContent)")
            assert labels == ["Photo badlo", "+ Jodo", "Hatao"]
            pg.click("#hoola-ebar button:has-text('+ Jodo')")
            pg.wait_for_function("window.__msgs.some(m => m.t === 'add')")
            msg = pg.evaluate("window.__msgs.find(m => m.t === 'add')")
            assert msg["k"] == home and msg["e"]
            pg.click(f'#{S.sec_id("home", "hero")} h1')                       # words: Link? no; AI, + Jodo, Hatao
            labels = pg.eval_on_selector_all("#hoola-ebar button", "bs => bs.map(b => b.textContent)")
            assert "+ Jodo" in labels and "AI se badlo" in labels
            b.close()
    finally:
        srv.shutdown()


def test_version():
    from pathlib import Path
    from app.main import APP_VERSION
    assert APP_VERSION == "0.338.0"
    assert "0.338.0+378" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
