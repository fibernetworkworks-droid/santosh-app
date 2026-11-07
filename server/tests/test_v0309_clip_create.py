"""v0.309 Video page Create: the storyboard is written in the background, so the price card must wait for it. It used to
be asked for in the same breath ("Pehle storyboard banaiye"), so a clip sat with a plan and no card forever."""
from __future__ import annotations

import asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _setup(env, tmp_path, monkeypatch, shots=True):
    from app.studio import service as ss
    from app.studio import studio as stmod
    st = stmod.Studio(tmp_path / "st")
    st.create("clip1", aspect="9:16", style="reel", language="Hindi", brief="chai")
    if shots:
        st.storyboard_set("clip1", [{"kind": "scene", "prompt": "Steam over a kulhad of chai", "duration": 8}])

    async def fake_studio(tenant):
        return st
    monkeypatch.setattr(ss, "studio", fake_studio)
    monkeypatch.setattr(ss, "_changed", lambda *a, **k: None)
    return ss, st


def _drive(ss, run, plan_first=True):
    async def main():
        if plan_first:                                   # the storyboard is still being written when Create returns
            async def planning():
                await asyncio.sleep(0.05)
            ss._planning["clip1"] = asyncio.ensure_future(planning())
        ss.after_plan("default", "clip1", run)
        key = ss._key("default", "clip1")
        assert key in ss._then
        await ss._then[key]
        ss._planning.pop("clip1", None)
    asyncio.run(main())


def test_price_card_waits_for_the_storyboard(env, tmp_path, monkeypatch):
    ss, st = _setup(env, tmp_path, monkeypatch)
    seen = []

    async def run():
        seen.append(ss._planning.get("clip1").done())  # by now the plan has finished
    _drive(ss, run)
    assert seen == [True] and st.load("clip1").get("error", "") == ""


def test_no_storyboard_and_a_refusal_are_written_on_the_clip(env, tmp_path, monkeypatch):
    ss, st = _setup(env, tmp_path, monkeypatch, shots=False)

    async def run():
        raise AssertionError("must not run without shots")
    _drive(ss, run)
    assert "could not be written" in st.load("clip1")["error"]

    ss, st = _setup(env, tmp_path / "b", monkeypatch)

    async def refused():
        raise ss.StudioJobError("Is mahine ki video limit poori ho gayi")
    _drive(ss, refused)
    assert st.load("clip1")["error"] == "Is mahine ki video limit poori ho gayi"


def test_route_and_page_use_one_call():
    main = (ROOT / "server" / "app" / "main.py").read_text()
    assert 'then: str = Field(default="", pattern="^(|generate|preview)$")' in main and "ss.after_plan(tenant, name" in main
    js = (ROOT / "server" / "app" / "static" / "console" / "studio.js").read_text()
    nc = js[js.index("async function newClip(preview)"):js.index("function clipOpen(name)")]
    assert "then: preview ? 'preview' : 'generate'" in nc and "/generate`" not in nc     # no second, too-early call
    assert "function clipOpen(name)" in js and "if (b.dataset.openproj) { clipOpen(b.dataset.openproj); return; }" in js
    assert 'class="perr"' in js and '"error": p.get("error") or ""' in (ROOT / "server" / "app" / "studio" / "service.py").read_text()
