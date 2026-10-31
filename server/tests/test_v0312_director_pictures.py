"""v0.312 Director pictures: after Haan the opening pictures are painted in the background; when they failed the reason
went ONLY to the chat and the Director sat on Pictures with nothing showing. Now: "Painting N opening pictures…" while
it runs, the reason ON the film (plain words, only painted pictures charged), Try again for the missing ones, and Skip =
the shots are made from the words (prefs.pics_skip)."""
from __future__ import annotations

import asyncio
import io
from pathlib import Path

from .test_v0262_every_model import _project, _studio

ROOT = Path(__file__).resolve().parents[2]


def _jpg() -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (200, 120, 60)).save(buf, "JPEG")
    return buf.getvalue()


def _setup(tmp_path, monkeypatch, painter):
    from app.studio import service as ss
    st = _studio(tmp_path, monkeypatch)
    _project(st)
    st.painter = painter
    seen = []
    monkeypatch.setattr(ss, "_changed", lambda t, p: seen.append(sorted(ss._painting.get(ss._key(t, p), ()))))
    monkeypatch.setattr(ss, "_publish", lambda *a, **k: None)
    monkeypatch.setattr(ss, "_note", lambda *a, **k: None)
    return ss, st, seen, [x["id"] for x in st.load("p1")["shots"]]


def test_all_failed_lands_on_the_film_in_plain_words(tmp_path, monkeypatch):
    def broken(prompt, aspect, refs):
        raise RuntimeError("400 INVALID_ARGUMENT API key not valid. Please pass a valid API key.")
    ss, st, seen, ids = _setup(tmp_path, monkeypatch, broken)
    asyncio.run(ss._do_keyframes("default", st, "p1", ids))
    p = st.load("p1")
    assert p["pics_error"].startswith("2 of 2 opening pictures could not be made: the picture service refused the Gemini key")
    assert "Only the pictures that were made are charged" in p["pics_error"]
    assert sorted(ids) in seen                                         # shown while painting
    assert float(p.get("spent_usd") or 0) == 0                         # nothing painted = nothing charged
    assert ss.view("default", p)["pics_error"] == p["pics_error"]


def test_some_failed_charges_only_the_painted_ones(tmp_path, monkeypatch):
    calls = []

    def half(prompt, aspect, refs):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        return _jpg()
    ss, st, _, ids = _setup(tmp_path, monkeypatch, half)
    asyncio.run(ss._do_keyframes("default", st, "p1", ids))
    p = st.load("p1")
    assert p["pics_error"].startswith("1 of 2 opening pictures could not be made:") and "out of quota" in p["pics_error"]
    assert sum(1 for x in p["shots"] if x.get("keyframe")) == 1
    assert abs(float(p.get("spent_usd") or 0) - ss.KEYFRAME_USD) < 1e-9


def test_success_clears_the_old_error(tmp_path, monkeypatch):
    ss, st, _, ids = _setup(tmp_path, monkeypatch, lambda prompt, aspect, refs: _jpg())
    p = st.load("p1")
    p["pics_error"] = "old"
    st.save(p)
    asyncio.run(ss._do_keyframes("default", st, "p1", ids))
    p = st.load("p1")
    assert p["pics_error"] == "" and all(x.get("keyframe") for x in p["shots"])


def test_skip_makes_the_shots_from_the_words(tmp_path, monkeypatch):
    ss, st, _, _ = _setup(tmp_path, monkeypatch, lambda prompt, aspect, refs: _jpg())
    assert ss.quote(st, st.load("p1"), "final")["paint_ids"]           # pictures on the card by default
    assert ss._clean_prefs({"pics_skip": True})["pics_skip"] is True
    p = st.load("p1")
    p["prefs"] = {"pics_skip": True}
    st.save(p)
    q = ss.quote(st, st.load("p1"), "final")
    assert q["paint_ids"] == [] and q["keyframes"] == 0                 # no pictures, none charged


def test_page():
    js = (ROOT / "server" / "app" / "static" / "console" / "studio.js").read_text()
    for k in ("|| (shots.length > 0 && !!p.prefs?.pics_skip)", "data-picsretry", "data-picsskip", "p.pics_error",
              "!p.prefs?.pics_skip ?", "!p.prefs?.cast_skip ?", "{pics_skip: true}"):
        assert k in js, k
    main = (ROOT / "server" / "app" / "main.py").read_text()
    assert "pics_skip: bool | None = None" in main
