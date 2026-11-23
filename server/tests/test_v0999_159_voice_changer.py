"""v0.999.159 VOICE CHANGER, PREMIUM - on the server: only the part she marks is changed, the two sliders reach ElevenLabs as
voice settings, her own recording is kept beside the change (and goes with the last change that needs it, or after 30 days),
up to three voices from one recording, again from a kept recording, a price per voice; and the console page walked in a
real Chromium: record, the part she marks, into a voice, Before / After, three voices side by side, Your changes, and the
page that says plainly when the changer cannot run."""
import json
import os
import subprocess
import time
from urllib.parse import parse_qs, urlparse

import pytest

from app.vocal import eleven as EL
from app.vocal import service as V
from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v0999_96_vocal_redesign_console import CONFIG, FAKE_MIC, ISO, install, open_vocal, overview, page_to
from tests.test_v0999_96_vocal_redesign_server import client, eleven, needs_ff, tone, vg  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

HERE = os.path.dirname(__file__)
JS = open(os.path.join(HERE, "..", "app", "static", "console", "vocal.js"), encoding="utf-8").read()
CSS = open(os.path.join(HERE, "..", "app", "static", "console", "vocal2.css"), encoding="utf-8").read()


def _premium(tenant="t1"):
    d = V._load(tenant)
    d["voices"][:0] = [{"id": "ev_arjun", "name": "Arjun", "kind": "hoola", "engine": "eleven", "eid": "arjun", "tier": "premium", "ready": True},
                       {"id": "ev_kavya", "name": "Kavya", "kind": "hoola", "engine": "eleven", "eid": "kavya", "tier": "premium", "ready": True}]
    V._store(tenant, d)


def _rec(tmp_path, seconds=4.0):
    f = tmp_path / "rec.wav"
    f.write_bytes(tone(seconds))
    return str(f)


@needs_ff
def test_the_marked_part_the_sliders_and_her_recording_kept(vg, eleven, tmp_path, monkeypatch):  # noqa: F811
    sent, _ = eleven
    _premium()
    monkeypatch.setattr(V, "_voice", lambda d, vid: next(v for v in d["voices"] if v["id"] == vid))
    out = V.change("t1", _rec(tmp_path, 4.0), "ev_arjun", start=1.0, end=3.0, closeness=80, feel=70)
    m, url, kw = sent[-1]
    assert url.endswith("/v1/voice-changer/arjun")
    sentwav = kw["files"]["audio"][1]
    import wave
    from io import BytesIO
    with wave.open(BytesIO(sentwav)) as w:
        assert abs(w.getnframes() / w.getframerate() - 2.0) < 0.1          # only the two marked seconds went out
    assert json.loads(kw["data"]["voice_settings"]) == {"similarity_boost": 0.8, "stability": 0.3}
    assert out["trim"] == [1.0, 3.0] and out["closeness"] == 80 and out["feel"] == 70 and out["src"].startswith("cs_")
    f, h = V.change_source("t1", out["id"])
    assert f.read_bytes() == sentwav and h["id"] == out["id"]
    with pytest.raises(V.VocalError, match="at least one second"):
        V.change("t1", _rec(tmp_path, 4.0), "ev_arjun", start=1.0, end=1.5)
    with pytest.raises(V.VocalError, match="numbers from 0 to 100"):
        V.change("t1", _rec(tmp_path, 4.0), "ev_arjun", closeness="loud")
    whole = V.change("t1", _rec(tmp_path, 4.0), "ev_arjun")                 # no marks, no sliders: as before, no settings sent
    assert "voice_settings" not in sent[-1][2]["data"] and whole["trim"] is None


@needs_ff
def test_three_voices_again_from_a_kept_recording_and_the_cleanup(vg, eleven, client, tmp_path, monkeypatch):  # noqa: F811
    sent, replies = eleven
    _premium()
    monkeypatch.setattr(V, "_voice", lambda d, vid: next(v for v in d["voices"] if v["id"] == vid))
    replies["/voice-changer/kavya"] = lambda m, u, kw: type("R", (), {"status_code": 429, "text": "busy", "json": lambda self: {"detail": "Too many requests"}})()
    r = V.change_many("t1", _rec(tmp_path), ["ev_arjun", "ev_kavya"])
    assert [x["voice"] for x in r["items"]] == ["ev_arjun"] and r["failed"][0]["name"] == "Kavya"     # one failing voice never stops the others
    del replies["/voice-changer/kavya"]
    with pytest.raises(V.VocalError, match="Up to 3 voices"):
        V.change_many("t1", _rec(tmp_path), ["ev_arjun", "ev_kavya", "a", "b"])
    first = r["items"][0]
    again = V.change_many("t1", "", ["ev_kavya"], source_of=first["id"])                   # no new upload: her kept recording
    assert again["items"][0]["src"] == first["src"] and sent[-1][1].endswith("/kavya")
    # the route: one voice = the sound; several = items + failed; a price per voice
    up = tmp_path / "up.wav"; up.write_bytes(tone(2.0))
    monkeypatch.setattr(V, "change_many", V.change_many)
    q1 = client.post("/api/vocal/quote", json={"job": "change", "seconds": 60}).json()
    q3 = client.post("/api/vocal/quote", json={"job": "change", "seconds": 60, "voices": 3}).json()
    assert q3["credits"] == q1["credits"] * 3 and "for 3 voices" in q3["line"]
    s = client.get(f"/api/vocal/change/source?id={first['id']}")
    assert s.status_code == 200 and s.content[:4] == b"RIFF" and s.headers["cache-control"].startswith("private")
    assert client.get("/api/vocal/change/source?id=vo_zzzzzzzzzzzz").status_code in (404, 422)
    # removing one change keeps her recording while another change still needs it
    srcf = V._home("t1") / "sources" / f"{first['src']}.wav"
    V.history_remove("t1", first["id"])
    assert srcf.is_file()
    V.history_remove("t1", again["items"][0]["id"])
    assert not srcf.exists()
    # after 30 days her recording goes, the change stays
    keep = V.change("t1", _rec(tmp_path), "ev_arjun")
    n = V.sources_sweep("t1", now=time.time() + 31 * 86400)
    row = next(h for h in V._load("t1")["history"] if h["id"] == keep["id"])
    assert n >= 1 and "src" not in row and (V._home("t1") / "audio" / f"{keep['id']}.wav").is_file()
    with pytest.raises(V.VocalError, match="no longer kept"):
        V.change_source("t1", keep["id"])


def test_the_files_carry_the_design():
    for k in ("chgMain", "chgCompare", "chgList", "chgNot", "chgPick", "chgPlay", "chgTrim", "chgPeaks", "Say it your way",
              "Hear the difference", "How close to", "Keep my feeling", "Only this part is changed", "Try it in other voices",
              "Into another voice", "Your changes", "Say it once. Hear it in another voice.", "Cannot be used here",
              "'cleanup' : 'change'}/source", "source_of", "voices: vs"):
        assert k in JS, k
    for k in ("v0.999.159 Voice changer", ".hv-chggrid", ".hv-chgwave", ".hv-chgsel", ".hv-chglane", ".hv-chgslots", ".hv-chglist", ".hv-chgnots"):
        assert k in CSS, k
    assert "case 'pickinto'" not in JS and "case 'change':" not in JS          # the old one-box changer is gone


HIST = [{"id": "vo_cccccccccccc", "kind": "change", "title": "Shop greeting", "voice": "v_thandi", "voice_name": "Thandi", "seconds": 29,
         "made": ISO(-120), "ext": "wav", "src": "cs_aaaaaaaaaaaa", "src_secs": 29, "denoise": True, "trim": [11, 40]},
        {"id": "vo_dddddddddddd", "kind": "change", "title": "Story opening", "voice": "v_mine", "voice_name": "My voice", "seconds": 160,
         "made": ISO(-86400 * 9), "ext": "wav", "denoise": False}]


def chg(pg, st):
    def route(r):
        req = r.request
        u = urlparse(req.url)
        path, qs = u.path[len("/api/vocal"):], parse_qs(u.query)
        body = req.post_data_json if req.method in ("POST", "PUT") and req.post_data else None
        j = lambda d, s=200: r.fulfill(status=s, content_type="application/json", body=json.dumps(d))  # noqa: E731
        if path == "/overview":
            o = overview()
            o["history"] = st["hist"] + o["history"]
            if st.get("noeleven"):
                o["engines"] = [{**e, "state": "needs_key"} if e["id"] == "eleven" else e for e in o["engines"]]
            return j(o)
        if path == "/quote" and (body or {}).get("job") == "change":
            n = int((body or {}).get("voices") or 1) * 12
            return j({"credits": n, "usd": n / 1000, "engine": "eleven", "line": "nothing is spent until you tap"})
        if path == "/change":
            st["chg"].append(body)
            vs = body.get("voices") or [body.get("voice")]
            items = [{"id": f"vo_n{i}{'x' * 10}"[:15], "kind": "change", "title": "Changed", "voice": v, "voice_name": "Thandi" if v == "v_thandi" else "My voice",
                      "seconds": 3, "made": ISO(), "ext": "wav", "src": "cs_bbbbbbbbbbbb", "src_secs": 3} for i, v in enumerate(vs)]
            st["hist"][:0] = items
            return j(items[0] if "voice" in body and "voices" not in body and "source_of" not in body else {"items": items, "failed": []})
        if path == "/change/source":
            st["src"].append(qs["id"][0])
            return r.fulfill(content_type="audio/wav", body=b"RIFF\x24\x00\x00\x00WAVEfmt ")
        if path == "/history" and req.method == "DELETE":
            st["deleted"].append(qs["id"][0])
            st["hist"] = [h for h in st["hist"] if h["id"] != qs["id"][0]]
            return j({"removed": qs["id"][0]})
        return r.fallback()
    pg.route("**/api/vocal/**", route)


NO_SIDEWAYS = "() => document.documentElement.scrollWidth <= innerWidth + 1 && document.querySelector('#hvRoot').scrollWidth <= document.querySelector('#hvRoot').clientWidth + 1"
UNSAID = """() => [...document.querySelectorAll('#hvView :is(button,input):disabled')].filter(e => { const id = e.getAttribute('aria-describedby'), w = id && document.getElementById(id);
  return !((w && w.textContent.trim()) || e.closest('[role=radiogroup]')); }).map(e => e.outerHTML.slice(0, 120))"""


def test_voice_changer_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    shots = os.environ.get("HOOLA_SHOTS")
    for scheme, width in (("light", 1440), ("dark", 1440), ("light", 390)):
        st = {"calls": [], "tts": [], "sent": [], "rows": [], "items": [], "change": [], "uploads": 0, "chg": [], "src": [], "deleted": [],
              "hist": [dict(h) for h in HIST]}
        ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        ctx.add_init_script(FAKE_MIC)
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(getattr(e, "stack", "") or e)[:400]))
        pg.on("dialog", lambda d: d.accept())
        pg.route("**/api/console/config", lambda r: r.fulfill(json=CONFIG))
        install(pg, st)
        chg(pg, st)
        open_vocal(pg, base)
        narrow = width < 600
        page_to(pg, "changer", narrow)
        # the first step: the mic, the tips, a recent change, and Change it says why it waits
        pg.wait_for_selector("#hvView .hv-chg .hv-recb.xl")
        v = pg.locator("#hvView")
        assert "Say it your way" in v.text_content() and "Recent changes" in v.text_content() and "Shop greeting" in v.text_content()
        assert pg.locator("#hvView [data-qbtn='chg']").is_disabled() and pg.locator("#hvRoot h1").count() == 1
        assert pg.evaluate(UNSAID) == [] and pg.evaluate(NO_SIDEWAYS), (scheme, width)
        if shots:
            pg.screenshot(path=f"{shots}/chg-{scheme}-{width}-1-start.png")
        # record in the page: the recording, the part she marks, the checks
        pg.locator("#hvRoot [data-a='rec'][data-k='chg']").click()
        pg.wait_for_selector("#hvRoot [data-a='recstop'][data-k='chg']")
        assert "of 5:00" in v.text_content()
        pg.wait_for_timeout(2600)
        pg.locator("#hvRoot [data-a='recstop'][data-k='chg']").click()
        pg.wait_for_selector("#hvView [data-trimwave]")
        pg.wait_for_function("() => document.querySelector('#hvView .hv-chgchk')?.textContent.includes('Uploaded')", timeout=10000)
        assert "All of it is changed" in v.text_content()
        pg.evaluate("() => { const s = document.querySelector('#hvChgA'); s.value = 1; s.dispatchEvent(new Event('input', {bubbles: true})); }")
        assert "Only this part is changed" in pg.locator("#hvView [data-triml]").text_content()
        assert float(pg.evaluate("() => getComputedStyle(document.querySelector('[data-trimwave]')).getPropertyValue('--chga')")) > 0
        # into a voice: grouped, the ones that cannot change say why
        pg.locator("#hvView [data-a='chgpick']").click()
        menu = pg.locator(".hmenu")
        assert "Premium voices" in menu.text_content() and "Cannot be used here" in menu.text_content()
        old = pg.locator(".hmenu .mi", has_text="Old storyteller")
        assert old.get_attribute("aria-disabled") == "true"
        pg.locator(".hmenu .mi", has_text="Thandi").click()
        pg.evaluate("() => { const s = document.querySelector('#hvChgC'); s.value = 90; s.dispatchEvent(new Event('input', {bubbles: true})); }")
        pg.wait_for_function("() => !document.querySelector('[data-qbtn=chg]').disabled && document.querySelector('[data-qbtn=chg]').textContent.includes('12')", timeout=10000)
        pg.locator("#hvView [data-qbtn='chg']").click()
        pg.wait_for_selector("#hvView .hv-chgab [data-a='chgplay']")
        b = st["chg"][-1]
        assert b["voice"] == "v_thandi" and b["file_id"].startswith("f_up") and b["start"] == 1 and b["closeness"] == 90 and b["feel"] == 50 and b["denoise"] is True
        # Before / After switch in place
        pg.locator("#hvView [data-a='chghear'][data-val='before']").click()
        assert "on" in pg.locator("#hvView .hv-chglane.l-before").get_attribute("class")
        assert pg.evaluate(UNSAID) == [] and pg.evaluate(NO_SIDEWAYS), (scheme, width)
        if shots:
            pg.screenshot(path=f"{shots}/chg-{scheme}-{width}-2-changed.png")
        # three voices side by side, priced together; she picks one and the others go
        pg.locator("#hvView [data-a='chgview'][data-val='compare']").click()
        pg.wait_for_selector("#hvView .hv-chgslot")
        assert pg.locator("#hvView .hv-chgslot").count() == 3 and "Thandi" in pg.locator("#hvView .hv-chgslot").first.text_content()
        pg.locator("#hvView [data-a='chgslot'][data-i='1']").click()
        pg.locator(".hmenu .mi", has_text="My voice").click()
        pg.wait_for_function("() => document.querySelector('[data-qbtn=chgn]').textContent.includes('24')", timeout=10000)
        pg.locator("#hvView [data-qbtn='chgn']").click()
        pg.wait_for_selector("#hvView [data-a='chgcpick']")
        assert st["chg"][-1]["voices"] == ["v_thandi", "v_mine"]
        pg.locator("#hvView [data-a='chgcpick']").nth(1).click()
        if shots:
            pg.screenshot(path=f"{shots}/chg-{scheme}-{width}-3-compare.png")
        pg.locator("#hvView [data-a='chggo']").click()
        pg.wait_for_selector("#hvView .hv-chggrid")
        assert len(st["deleted"]) == 1
        # Your changes: pairs, her own recording played from the server, again into another voice
        pg.locator("#hvView .hv-chgtop [data-a='chgview'][data-val='list']").click()
        pg.wait_for_selector("#hvView .hv-chgc")
        assert "Your recording no longer kept" in v.text_content()
        pg.locator("#hvView [data-a='chgsrc'][data-id='vo_cccccccccccc']").click()
        pg.wait_for_timeout(400)
        assert "vo_cccccccccccc" in st["src"]
        if shots:
            pg.screenshot(path=f"{shots}/chg-{scheme}-{width}-4-list.png")
        pg.locator("#hvView [data-a='chganother'][data-id='vo_cccccccccccc']").click()
        pg.locator(".hmenu .mi", has_text="My voice").click()
        pg.wait_for_selector("#hvView .hv-chggrid")
        assert st["chg"][-1]["source_of"] == "vo_cccccccccccc" and st["chg"][-1]["voices"] == ["v_mine"]
        assert pg.evaluate(NO_SIDEWAYS), (scheme, width)
        assert not errs, errs
        ctx.close()
    # when ElevenLabs is not on the server, the page says so plainly and charges nothing
    st = {"calls": [], "tts": [], "sent": [], "rows": [], "items": [], "change": [], "uploads": 0, "chg": [], "src": [], "deleted": [], "hist": [], "noeleven": True}
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.route("**/api/console/config", lambda r: r.fulfill(json=CONFIG))
    install(pg, st)
    chg(pg, st)
    open_vocal(pg, base)
    page_to(pg, "changer")
    pg.wait_for_selector("#hvView .hv-chgnot")
    t = pg.locator("#hvView").text_content()
    assert "Say it once. Hear it in another voice." in t and "The voice engine is not on this server" in t and "nothing is charged" in t
    assert pg.locator("#hvView [data-qbtn='chg']").count() == 0
    if shots:
        pg.screenshot(path=f"{shots}/chg-light-1440-5-not-ready.png")
    ctx.close()
