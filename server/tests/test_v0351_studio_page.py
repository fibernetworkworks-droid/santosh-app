"""v0.351 HOOLA STUDIO PAGE: /studio on the Hoola website shows the real Create Studio screens, the menus of the other pages
link to it, and the samples wall reads the owner's showcase through a public, showcase-only endpoint."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SITE = Path(__file__).resolve().parents[1] / "app" / "static" / "site"


@pytest.fixture
def web(env):
    from app import main
    with TestClient(main.app) as c:
        yield c


def test_page_and_real_screens(web):
    html = web.get("/studio").text
    assert "<title>Hoola Create Studio</title>" in html
    for sid in ("oneline", "director", "tools", "samples", "price", "languages", "made", "questions", "get"):
        assert f'id="{sid}"' in html, sid
    js = (SITE / "studio.js").read_text()
    shots = set(re.findall(r"/static/site/studio/([a-z]+)\.webp", html)) | {t for t in re.findall(r"\['([a-z]+)', '[A-Z]", js)
                                                                           if (SITE / "studio" / f"{t}.webp").exists()}
    assert {"home", "director", "dubbing", "video", "image", "music", "voice", "editor"} <= shots
    for s in shots:
        r = web.get(f"/static/site/studio/{s}.webp")
        assert r.status_code == 200 and r.content[:4] == b"RIFF" and len(r.content) < 120_000, s
    assert "prefers-reduced-motion" in js and "IntersectionObserver" in js and "eval(" not in js
    assert "__LOGO__" not in html


def test_menus_link_to_studio(web):
    for path in ("/", "/employee", "/network"):
        assert '<a href="/studio">Studio</a>' in web.get(path).text, path


def test_public_showcase_is_showcase_only(web, monkeypatch):
    from app.studio import showcase
    r = web.get("/api/site/showcase")
    assert r.status_code == 200 and r.json() == {"slots": {}}
    assert web.get("/api/site/showcase/film0/pic").status_code == 404         # not made yet
    assert web.get("/api/site/showcase/../../etc/pic").status_code == 404
    assert web.get("/api/site/showcase/nope/pic").status_code == 404           # only the showcase slots
    assert web.get("/api/site/showcase/film0/exe").status_code == 404
    monkeypatch.setattr(showcase, "manifest", lambda: {"film0": {"pic": True, "clip": False}})
    assert web.get("/api/site/showcase").json()["slots"]["film0"]["pic"] is True
