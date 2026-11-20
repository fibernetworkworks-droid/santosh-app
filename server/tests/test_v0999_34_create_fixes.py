"""v0.999.34 CREATE FIXES (owner: "GO FIX ALL" after the Create check): a Director storyboard that fails says so on the
film, "Storyboard ready" only when the shots are there, engine failures are one plain line (never the provider's raw
"Error code: 401 - {...}"), and a tool whose engine is not set up says so BEFORE a job starts (console + phone)."""
from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "server/app/static/console"
RAW_401 = "Error code: 401 - {'type': 'error', 'error': {'type': 'authentication_error', 'message': 'Invalid bearer token'}}"


def _studio(env, tmp_path, monkeypatch):
    from app.studio import service as ss
    from app.studio import studio as stmod
    st = stmod.Studio(tmp_path / "st")
    st.create("film1", aspect="16:9", style="reel", language="Hindi", brief="A Diwali ad for my chai brand")

    async def fake_studio(tenant):
        return st
    monkeypatch.setattr(ss, "studio", fake_studio)
    monkeypatch.setattr(ss, "studio_sync", lambda tenant: st)
    monkeypatch.setattr(ss, "_changed", lambda *a, **k: None)
    return ss, st


def _plan_and_wait(ss, brief="A Diwali ad for my chai brand"):
    async def main():
        r = await ss.plan("default", "film1", brief, 30)
        t = ss._planning.get("film1")
        if t is not None:
            await t
        return r
    return asyncio.run(main())


def test_a_failed_storyboard_is_written_on_the_film_in_plain_words(env, tmp_path, monkeypatch):
    ss, st = _studio(env, tmp_path, monkeypatch)

    async def broken(*a, **k):
        raise RuntimeError(RAW_401)
    monkeypatch.setattr(ss, "_write", broken)
    _plan_and_wait(ss)
    err = st.load("film1").get("error", "")
    assert err and "not connected" in err and "Error code" not in err and "{" not in err, err
    assert "film1" not in ss._planning                                   # not left "writing" for ever


def test_a_fresh_try_clears_the_last_failure(env, tmp_path, monkeypatch):
    ss, st = _studio(env, tmp_path, monkeypatch)
    asyncio.run(st.update("film1", lambda q: q.update(error="The storyboard could not be written this time.")))

    async def slow(*a, **k):
        await asyncio.sleep(0.2)
        raise RuntimeError("timed out")
    monkeypatch.setattr(ss, "_write", slow)

    async def main():
        await ss.plan("default", "film1", "A Diwali ad for my chai brand", 30)
        cleared = st.load("film1").get("error", "")                      # while the new try runs
        await ss._planning["film1"]
        return cleared, st.load("film1").get("error", "")
    cleared, after = asyncio.run(main())
    assert cleared == "" and after == "This took too long this time. Try again."


def test_a_clip_keeps_the_reason_and_says_press_create(env, tmp_path, monkeypatch):
    ss, st = _studio(env, tmp_path, monkeypatch)

    async def broken(*a, **k):
        raise RuntimeError("Error code: 529 - {'type': 'error', 'error': {'type': 'overloaded_error'}}")
    monkeypatch.setattr(ss, "_write", broken)

    async def main():
        await ss.plan("default", "film1", "A Diwali ad for my chai brand", 6)

        async def run():
            raise AssertionError("must not run without shots")
        ss.after_plan("default", "film1", run)
        await ss._then[ss._key("default", "film1")]
    asyncio.run(main())
    err = st.load("film1")["error"]
    assert err == "The writing engine is busy right now. Try again in a minute. Press Create again.", err


@pytest.mark.parametrize("raw,want", [
    (RAW_401, "not connected on the server"),
    ("Error code: 402 - {'error': 'insufficient credit balance'}", "run out of credit"),
    ("Error code: 429 - {'error': 'rate limit'}", "busy right now"),
    ("ReadTimeout: timed out", "took too long"),
    ("KeyError: 'choices' {'weird': 1}", "FALLBACK"),
])
def test_plain_lines(raw, want):
    from app.create import service as cs
    out = cs.plain(RuntimeError(raw), "writing", "FALLBACK")
    assert want in out and "{" not in out and "Error code" not in out


def test_script_writer_never_shows_the_raw_error(env, monkeypatch):
    from app import main
    from app.studio import service as ss

    async def broken(*a, **k):
        raise RuntimeError(RAW_401)
    monkeypatch.setattr(ss, "_write", broken)
    with TestClient(main.app) as c:
        r = c.post("/api/create/write", json={"kind": "script", "brief": "A 30 second ad for a chai shop in Pune"})
    d = r.json()["detail"]
    assert r.status_code == 400 and "not connected" in d and "Error code" not in d and "authentication_error" not in d, d


def test_a_job_that_breaks_says_one_plain_line(env, monkeypatch):
    from app import main
    from app.create import service as cs

    async def broken(*a, **k):
        raise RuntimeError("Error code: 500 - {'type': 'error', 'error': {'type': 'api_error'}}")
    monkeypatch.setattr(cs, "voice", broken)
    with TestClient(main.app) as c:
        j = c.post("/api/create/jobs", json={"kind": "voice", "text": "Namaste"}).json()
        for _ in range(50):
            x = c.get(f"/api/create/jobs/{j['id']}").json()
            if x["status"] != "running":
                break
            time.sleep(0.1)
    assert x["status"] == "failed" and "{" not in x["error"] and "Error code" not in x["error"], x


def test_the_page_learns_which_engines_are_missing(env):
    from app import main
    from app.create import service as cs
    with TestClient(main.app) as c:
        d = c.get("/api/create").json()
    assert d["ready"]["image"] is False and set(d["need"]) == {"image", "song", "voice", "dub"}
    assert d["need"] == cs.NEED and all("on the server" in v for v in cs.NEED.values())


def test_console_and_phone_check_before_a_job_and_say_ready_only_with_shots():
    js = (CON / "studio.js").read_text()
    start = js[js.index("async function startJob("):js.index("const running = kind =>")]
    assert "c?.ready?.[eng] === false" in start and "c.need?.[eng]" in start
    assert start.index("ready?.[eng]") < start.index("'/api/create/jobs'")           # checked before anything is posted
    film = js[js.index("async function newFilm()"):js.index("W.director = async")]
    assert "(p.shots || []).length ? 'Storyboard ready." in film and "Writing your storyboard" in film
    assert "data-planerr" in js and "Press Write the storyboard to try again." in js
    dart = (ROOT / "lib/ui/create/create_kit.dart").read_text()
    st = dart[dart.index("Future<Map<String, dynamic>> start("):dart.index("Future<Map<String, dynamic>> write(")]
    assert "ready[eng] == false" in st and st.index("ready[eng] == false") < st.index("'/api/create/jobs'")


def test_in_a_real_browser(arena_server, monkeypatch):  # noqa: F811
    """Image with no engine: the line shows and nothing is posted. Director with a broken writer: the film says why."""
    from app.studio import service as ss

    async def broken(*a, **k):
        raise RuntimeError(RAW_401)
    monkeypatch.setattr(ss, "_write", broken)
    base, browser, key = arena_server
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs, posted = [], []
    pg.on("pageerror", lambda e: errs.append(str(e)[:300]))
    pg.on("request", lambda r: r.method == "POST" and "/api/create/jobs" in r.url and posted.append(r.url))
    pg.goto(base + "/console/?v=creative")
    pg.wait_for_selector("#cstudio #snav")
    pg.locator("#cstudio #snav [data-go='image']").first.click()
    pg.locator("#cstudio #imgq").fill("A clay kulhad of chai on a wooden table")
    # v0.999.53 IMAGE CHAT: the engine that is not set up is said under the chat box before anything is sent
    pg.wait_for_function("() => (document.querySelector('#cstudio').shadowRoot.querySelector('#iprice')?.textContent || '').includes('GEMINI_API_KEY')", timeout=10000)
    assert posted == []
    pg.locator("#cstudio #snav [data-go='director']").first.click()
    pg.locator("#cstudio #dirq").fill("A 30 second Diwali ad for my chai brand")
    pg.locator("#cstudio #dirForm button:not([type=button])").first.click()
    pg.locator("#cstudio [data-planerr]").wait_for(timeout=20000)
    box = pg.locator("#cstudio [data-planerr]").inner_text()
    assert "not connected" in box and "Nothing was spent" in box and "Error code" not in box
    assert "Storyboard ready" not in pg.evaluate("() => document.body.innerText")
    if os.environ.get("CONSOLE_SHOTS"):
        pg.screenshot(path=f"{os.environ['CONSOLE_SHOTS']}/create-fix-director.png")
    assert errs == [], errs


from tests.test_v0312_arena_screen import arena_server  # noqa: E402,F401
from tests.test_v121_site import site_env  # noqa: E402,F401
