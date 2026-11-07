"""v0.311 Director cast: after Haan the character picture is painted in the background; when it failed the reason
went ONLY to the chat and the Director sat on Cast with nothing showing. Now: "Painting <name>…" while it runs, the
reason ON the film (plain words, nothing charged), Try again refilled, and Skip = no fixed characters."""
from __future__ import annotations

import asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _st(env, tmp_path, monkeypatch, painter):
    from app.studio import service as ss
    from app.studio import studio as stmod
    st = stmod.Studio(tmp_path / "st")
    st.create("film", aspect="16:9", style="ad", language="Hindi", brief="chai")
    st.painter = painter
    seen = []
    monkeypatch.setattr(ss, "_changed", lambda t, p: seen.append(sorted(ss._casting.get(ss._key(t, p), ()))))
    monkeypatch.setattr(ss, "_publish", lambda *a, **k: None)
    monkeypatch.setattr(ss, "_note", lambda *a, **k: None)
    return ss, st, seen


ASK = {"name": "Riya", "description": "28, warm smile, mustard kurta", "voice": "female", "char_kind": "person"}


def test_failure_lands_on_the_film_in_plain_words(env, tmp_path, monkeypatch):
    def broken(prompt, aspect, refs):
        raise RuntimeError("400 INVALID_ARGUMENT API key not valid. Please pass a valid API key.")
    ss, st, seen = _st(env, tmp_path, monkeypatch, broken)
    asyncio.run(ss._paint_character("default", st, "film", ASK))
    p = st.load("film")
    assert p["cast_error"].startswith("Riya: the picture service refused the Gemini key") and "Nothing was charged" in p["cast_error"]
    assert p["cast_last"]["name"] == "Riya" and "mustard" in p["cast_last"]["description"]     # Try again refills
    assert ["Riya"] in seen and seen[-1] == []                                                # shown while painting, cleared after
    assert float(p.get("spent_usd") or 0) == 0                                                 # nothing charged


def test_success_clears_the_old_error(env, tmp_path, monkeypatch):
    import io

    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (200, 120, 60)).save(buf, "JPEG")
    ss, st, _ = _st(env, tmp_path, monkeypatch, lambda prompt, aspect, refs: buf.getvalue())
    p = st.load("film")
    p["cast_error"] = "old"
    st.save(p)
    asyncio.run(ss._paint_character("default", st, "film", ASK))
    p = st.load("film")
    assert "Riya" in p["characters"] and p["cast_error"] == ""


def test_plain_reasons():
    from app.studio import service as ss
    assert "out of quota" in ss._paint_why(RuntimeError("429 RESOURCE_EXHAUSTED"))
    assert "would not draw" in ss._paint_why(RuntimeError("blocked by SAFETY"))


def test_skip_and_page():
    from app.studio import service as ss
    assert ss._clean_prefs({"cast_skip": True})["cast_skip"] is True
    js = (ROOT / "server" / "app" / "static" / "console" / "studio.js").read_text()
    for k in ("|| !!p.prefs?.cast_skip", "data-castretry", "data-castskip", "Painting ${p.casting.map(esc)", "p.cast_error",
              "DIR.view?.cast_last", "(p.casting || []).length || (p.approvals || []).length)) poll"):
        assert k in js, k
    main = (ROOT / "server" / "app" / "main.py").read_text()
    assert "cast_skip: bool | None = None" in main
