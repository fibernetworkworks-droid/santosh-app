"""v0.329 SHOWCASE (Phase 5 of the Create Studio design audit): real Hoola-made pictures and clips instead of the drawn
placeholders. No new money path: the showcase is one HIDDEN film in the owner's studio; its pictures / clips come from the
normal price cards (keyframes / generate -> _ask -> her Haan + fingerprint). Found while building: decide() and the
fingerprint card lookup searched only VISIBLE films, so a hidden film's card could never be approved."""
from __future__ import annotations

import asyncio
import io
from pathlib import Path

CON = Path(__file__).resolve().parents[1] / "app" / "static" / "console"


def _jpg() -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (60, 80), (200, 120, 60)).save(b, "JPEG")
    return b.getvalue()


def _go(monkeypatch):
    from app.studio import service as ss
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gem")
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-or")
    ss._studios.clear()
    monkeypatch.setattr(ss, "_publish", lambda *a, **k: None)
    monkeypatch.setattr(ss, "_note", lambda *a, **k: None)
    return ss


def test_setup_is_free_hidden_and_one_shot_per_slot(env, monkeypatch):
    ss = _go(monkeypatch)
    from app.studio import showcase as sc

    async def go():
        o = await sc.setup()
        assert o["set_up"] and o["slots"] == len(sc.SLOTS) == 36 and o["clips"] == 4 and o["spent_inr"] == 0
        st = await ss.studio(sc.owner())
        p = st.load(sc.NAME)
        assert p["hidden"] is True and [s["id"] for s in p["shots"]] == [s for s, _ in sc.SLOTS]
        assert all("No words, letters" in s["prompt"] and s["duration"] == 5 for s in p["shots"])
        assert sc.NAME not in [x["project"] for x in ss.listing(sc.owner())]          # never in her film lists
        assert sc.NAME in [x["project"] for x in ss.listing(sc.owner(), hidden=True)]
        assert (await sc.setup())["set_up"]                                            # twice = the same film
    asyncio.run(go())


def test_price_cards_one_at_a_time_and_clips_after_pictures(env, monkeypatch):
    ss = _go(monkeypatch)
    from app.studio import showcase as sc

    async def go():
        await sc.setup()
        (await ss.studio(sc.owner())).painter = lambda prompt, aspect, refs: _jpg()     # the picture engine is "on" (never called here)
        r = await sc.ask_pictures()
        assert r["waiting_owner"] and abs(r["usd"] - 36 * ss.KEYFRAME_USD) < 1e-6        # the normal opening-pictures card
        try:
            await sc.ask_pictures()
            raise AssertionError("a second card while one waits")
        except sc.ShowcaseError as e:
            assert "already waiting" in str(e)
        # her "Na" -> the card is found on the HIDDEN film and declined (it used to say "Yeh card purana ho gaya")
        assert (await ss.decide(sc.owner(), r["waiting_owner"], False))["status"] == "rejected"
        assert ss.approval_card(sc.owner(), r["waiting_owner"]) is None
        try:
            await sc.ask_clips()
            raise AssertionError("clips before pictures would paint (and charge) 4 pictures twice")
        except sc.ShowcaseError as e:
            assert "pictures first" in str(e)
    asyncio.run(go())


def test_manifest_and_files(env, monkeypatch):
    ss = _go(monkeypatch)
    from app.studio import showcase as sc

    async def go():
        await sc.setup()
        st = await ss.studio(sc.owner())
        d = st.pdir(sc.NAME) / "keyframes"
        d.mkdir(parents=True, exist_ok=True)

        def fn(q):
            for s in q["shots"]:
                if s["id"] in ("film0", "sty3"):
                    f = d / f"{s['id']}.jpg"
                    f.write_bytes(_jpg())
                    s["keyframe"] = str(f)
        await st.update(sc.NAME, fn)
        assert sc.manifest() == {"film0": {"pic": True, "clip": False}, "sty3": {"pic": True, "clip": False}}
        assert sc.file_for("film0", "pic").read_bytes()[:2] == b"\xff\xd8"
        for bad in (("film1", "pic"), ("film0", "clip"), ("../x", "pic"), ("film0", "exe")):
            try:
                sc.file_for(*bad)
                raise AssertionError(bad)
            except sc.ShowcaseError:
                pass
        assert sc.status()["pictures_made"] == 2
    asyncio.run(go())


def test_routes_owner_only_and_files_for_everyone():
    main = (Path(__file__).resolve().parents[1] / "app" / "main.py").read_text()
    assert '@app.get("/api/studio/showcase", dependencies=[Depends(require_key)])' in main
    assert 'if tenant != get_settings().tenant_id:\n        raise HTTPException(403, "The showcase is made by the owner")' in main
    assert '@app.get("/api/studio/showcase/file/{slot}"' in main
    svc = (Path(__file__).resolve().parents[1] / "app" / "studio" / "service.py").read_text()
    assert svc.count("listing(tenant, hidden=True)") >= 3                  # decide, the fingerprint card, the stale-card sweep


def test_pages_lay_the_real_pictures_over_the_drawn_ones():
    js = (CON / "studio.js").read_text()
    css = (CON / "studio.css").read_text()
    assert "function showcaseSwap(root = R)" in js and "showcaseSwap(el);" in js and "load('showcase').then(() => showcaseSwap($('#view')))" in js
    assert "if ((m = /^sty(\\d+)$/.exec(seed))) return 'sty' + m[1];" in js and "'tool' + i" in js
    assert ".catch(() => el.remove())" in js                            # a missing file leaves the drawing, never "File not available"
    assert "prefers-reduced-motion: reduce" in js                      # clips stay still pictures when she asked for less motion
    assert "function drawShowcase(o)" in js and "data-sc=\"clips\"" in js and "o.pictures_made < o.slots ? 'disabled'" in js
    blk = css[css.index("v0.329 PHASE 5: SHOWCASE"):]
    assert ".art.sc{" in blk and ".art.sc.on{opacity:1}" in blk and "infinite" not in blk
