"""v0.999.163 YOUR SOUNDS, DICTIONARY, SETTINGS - on the server: several sounds kept / unkept / removed in one tap, a ZIP
of the chosen sounds in her format, a starred sound never swept by Keep my sounds; a dictionary word changed in place, an
import read and checked before anything is added, the dictionary as CSV, how many of her sounds use each word, a short free
sample read her way; and the three console pages walked in a real Chromium."""
import io
import json
import os
import zipfile
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pytest

from app.vocal import more as M
from app.vocal import service as V
from tests.test_v0999_96_vocal_redesign_server import client, needs_ff, run, tone, vg  # noqa: F401

HERE = os.path.dirname(__file__)
JS = open(os.path.join(HERE, "..", "app", "static", "console", "vocal.js"), encoding="utf-8").read()
CSS = open(os.path.join(HERE, "..", "app", "static", "console", "vocal2.css"), encoding="utf-8").read()


def _sounds(n=3):
    return [V.sfx("t1", "coin", i + 1) for i in range(n)]


# ---------------------------------------------------------------- Your sounds
def test_several_sounds_kept_unkept_and_removed_in_one_tap(vg, client):  # noqa: F811
    a, b, c = _sounds()
    r = client.post("/api/vocal/history/bulk", json={"ids": [a["id"], b["id"], "vo_000000000000"], "action": "keep"}).json()
    assert r["done"] == [a["id"], b["id"]] and r["missing"] == ["vo_000000000000"]
    rows = {h["id"]: h for h in V._load("t1")["history"]}
    assert rows[a["id"]]["star"] and rows[b["id"]]["star"] and "star" not in rows[c["id"]]
    assert V.overview("t1")["usage"]["starred"] == 2
    client.post("/api/vocal/history/bulk", json={"ids": [a["id"]], "action": "unkeep"})
    assert "star" not in {h["id"]: h for h in V._load("t1")["history"]}[a["id"]]
    r = client.post("/api/vocal/history/bulk", json={"ids": [a["id"], c["id"]], "action": "remove"}).json()
    assert sorted(r["done"]) == sorted([a["id"], c["id"]]) and [h["id"] for h in V._load("t1")["history"]] == [b["id"]]
    assert client.post("/api/vocal/history/bulk", json={"ids": [], "action": "keep"}).status_code == 422
    assert client.post("/api/vocal/history/bulk", json={"ids": [b["id"]], "action": "burn"}).status_code == 422


@needs_ff
def test_the_chosen_sounds_as_one_zip_in_her_format(vg, client):  # noqa: F811
    a, b = _sounds(2)
    r = client.post("/api/vocal/history/zip", json={"ids": [a["id"], b["id"]], "format": "mp3"})
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip" and 'filename="hoola-sounds-2.zip"' in r.headers["content-disposition"]
    z = zipfile.ZipFile(io.BytesIO(r.content))
    names = z.namelist()
    assert "Coin #1.mp3" in names and "Coin #2.mp3" in names and "README.txt" in names
    as_is = zipfile.ZipFile(io.BytesIO(client.post("/api/vocal/history/zip", json={"ids": [a["id"]]}).content)).namelist()
    assert "Coin #1.wav" in as_is
    assert client.post("/api/vocal/history/zip", json={"ids": [a["id"]], "format": "exe"}).status_code == 422
    assert client.post("/api/vocal/history/zip", json={"ids": ["vo_000000000000"]}).status_code == 422


def test_a_kept_sound_stays_when_old_sounds_are_swept(vg):  # noqa: F811
    a, b = _sounds(2)
    V.settings_save("t1", {"keep_days": 7})
    old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(timespec="seconds")
    with V._LOCK:
        d = V._load("t1")
        for h in d["history"]:
            h["made"] = old
        V._store("t1", d)
    V.history_star("t1", a["id"])
    M.sweep("t1")
    assert [h["id"] for h in V._load("t1")["history"]] == [a["id"]]


# ---------------------------------------------------------------- Dictionary
def test_a_word_changed_in_place_and_a_twin_refused(vg, client):  # noqa: F811
    w1 = V.rule_add("t1", "Mithas", "Mi-thas", lang="hi")
    V.rule_add("t1", "Nashik", "Naa-shik")
    r = client.put("/api/vocal/rule", json={"id": w1["id"], "word": "Mithas", "say": "Mi-thaas", "ipa": "mɪˈt̪ʰaːs", "lang": "hi"}).json()
    assert r["say"] == "Mi-thaas" and r["ipa"] == "mɪˈt̪ʰaːs"
    assert [x["word"] for x in V._load("t1")["rules"]] == ["Nashik", "Mithas"]           # its place stays
    bad = client.put("/api/vocal/rule", json={"id": w1["id"], "word": "Nashik", "say": "x"})
    assert bad.status_code == 422 and "already in your dictionary" in bad.json()["detail"]
    assert client.put("/api/vocal/rule", json={"id": "pr_000000000000", "word": "a", "say": "b"}).status_code == 404


def test_an_import_is_checked_before_anything_is_added(vg, client):  # noqa: F811
    V.rule_add("t1", "Mithas", "Mi-thas", lang="hi")
    text = "word,say\nMithas,Mi-thaas,,hi\nNashik,Naa-shik\nKolhapur,Kol-haa-pur,,mr\nBiryani,Bir-yaa-nee,,klingon\n,No word\nNashik,Again\nPune\n"
    r = client.post("/api/vocal/rules/check", json={"text": text}).json()
    st = [(x["word"], x["state"], x.get("why", "")) for x in r["rows"]]
    assert st == [("Mithas", "replace", ""), ("Nashik", "new", ""), ("Kolhapur", "new", ""), ("Biryani", "bad", "Unknown language: klingon"),
                  ("", "bad", "Needs a word"), ("Nashik", "bad", "Twice in this list"), ("Pune", "bad", "Needs how to say it")]
    assert (r["new"], r["replace"], r["bad"]) == (2, 1, 4)
    assert len(V._load("t1")["rules"]) == 1                                              # nothing added by the check
    assert client.post("/api/vocal/rules/check", json={"text": "  "}).status_code == 422


def test_the_dictionary_as_csv_and_how_many_sounds_use_each_word(vg, client):  # noqa: F811
    w = V.rule_add("t1", "Mithas", "Mi-thaas", lang="hi", ipa="mɪˈt̪ʰaːs")
    V.rule_add("t1", "Pune", "Poo-nay")
    with V._LOCK:
        d = V._load("t1")
        d["history"] = [{"id": "vo_aaaaaaaaaaa1", "kind": "tts", "text": "Aaj hi aaiye Mithas Sweets", "made": V._now()},
                        {"id": "vo_aaaaaaaaaaa2", "kind": "tts", "text": "mithas, Nashik", "made": V._now()},
                        {"id": "vo_aaaaaaaaaaa3", "kind": "tts", "text": "Mithaswala", "made": V._now()}]
        V._store("t1", d)
    uses = V.overview("t1")["rule_uses"]
    assert uses[w["id"]] == 2 and list(uses.values()).count(0) == 1                    # whole words, any letter case
    csv = client.get("/api/vocal/rules/export")
    assert csv.status_code == 200 and 'filename="hoola-dictionary.csv"' in csv.headers["content-disposition"]
    body = csv.content.decode("utf-8-sig")
    assert body.splitlines()[0] == "word,say,ipa,lang" and "Mithas,Mi-thaas,mɪˈt̪ʰaːs,hi" in body
    assert V.overview("t1")["limits"]["rules"] == V.MAX_RULES


def test_a_short_sample_is_read_her_way_and_kept(vg, client, monkeypatch):  # noqa: F811
    V.rule_add("t1", "Mithas", "Mi-thaas")
    said = []

    async def say(tenant, v, text, lang, style, speed, expressive=0.5, hint=""):
        said.append((text, lang, hint))
        return tone()
    monkeypatch.setattr(V, "_say", say)
    r = client.post("/api/vocal/hear", json={"text": "Aaj hi aaiye Mithas Sweets", "lang": "en"})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/wav" and said[-1][0] == "Aaj hi aaiye Mi-thaas Sweets"
    client.post("/api/vocal/hear", json={"text": "Aaj hi aaiye Mithas Sweets", "lang": "en"})
    assert len(said) == 1                                                                 # heard again = kept, free, not counted
    assert client.post("/api/vocal/hear", json={"text": "x" * 201}).status_code == 422
    monkeypatch.setattr(V, "HEAR_PER_DAY", 1)
    lim = client.post("/api/vocal/hear", json={"text": "something new", "lang": "en"})
    assert lim.status_code == 422 and "free samples today" in lim.json()["detail"]


def test_the_console_page_files():
    for bit in ("sdPage", "sdPanel", "dictPage", "dictImport", "setPage", "/history/bulk", "/history/zip", "/rules/check", "/rules/export",
                "/hear", "Kept on this server", "Download as a ZIP", "Use it again", "Test a sentence", "Import a list", "Check before adding",
                "What things cost", "The rules Hoola keeps", "Keep my sounds", "Every language"):
        assert bit in JS, bit
    assert ".hv-sdr" in CSS and ".hv-setnav" in CSS and ".hv-dtr" in CSS


# ---------------------------------------------------------------- the pages in a real Chromium
from tests.test_v0312_arena_screen import arena_server  # noqa: E402,F401
from tests.test_v0999_96_vocal_redesign_console import CONFIG, ISO, install, open_vocal, overview, page_to  # noqa: E402
from tests.test_v0999_159_voice_changer import NO_SIDEWAYS, UNSAID  # noqa: E402
from tests.test_v121_site import site_env  # noqa: E402,F401

HIST = [{"id": "vo_c1c1c1c1c1c1", "kind": "sfx", "title": "Rain on a tin roof", "text": "Heavy rain on a tin roof", "seconds": 10, "made": ISO(-120), "ext": "mp3",
         "engine": "eleven", "take": "B", "loop": True, "star": True, "credits": 2},
        {"id": "vo_c2c2c2c2c2c2", "kind": "cleanup", "title": "Market interview", "seconds": 118, "made": ISO(-86400 - 3600), "ext": "mp3", "engine": "server",
         "done": ["Noise · strong", "Podcast loudness"], "src": "cl_aaaaaaaaaaaa"}]
RULES = [{"id": "pr_2", "word": "Nashik", "say": "Naa-shik", "ipa": "", "lang": ""}]


def sd(pg, st):
    def route(r):
        req = r.request
        u = urlparse(req.url)
        path, qs = u.path[len("/api/vocal"):], parse_qs(u.query)
        body = req.post_data_json if req.method in ("POST", "PUT") and req.post_data else None
        j = lambda d, s=200: r.fulfill(status=s, content_type="application/json", body=json.dumps(d))  # noqa: E731
        if path == "/overview":
            o = overview()
            o["history"] = [h for h in st["hist"] + o["history"] if h["id"] not in st["gone"]]
            o["rules"] = st["rules"]
            o["rule_uses"] = {"pr_1": 3, "pr_2": 0}
            o["usage"] = {**o["usage"], "by_kind": {"tts": 4, "sfx": 2, "cleanup": 1}, "starred": 1}
            o["limits"] = {**o["limits"], "rules": 200}
            return j(o)
        if path == "/history/bulk":
            st["bulk"].append(body)
            if body["action"] == "remove":
                st["gone"].extend(body["ids"])
            return j({"done": body["ids"], "missing": []})
        if path == "/history/zip":
            st["zip"].append(body)
            return r.fulfill(content_type="application/zip", body=b"PK\x05\x06" + b"\x00" * 18)
        if path == "/history/star":
            st["star"].append(body)
            return j({"id": body["id"], "star": body["on"]})
        if path == "/rule" and req.method in ("POST", "PUT"):
            st["rule"].append((req.method, body))
            row = {"id": body.get("id") or "pr_9", "word": body["word"], "say": body["say"], "ipa": body.get("ipa", ""), "lang": body.get("lang", "")}
            st["rules"] = [x for x in st["rules"] if x["id"] != row["id"]] + [row] if req.method == "POST" else [row if x["id"] == row["id"] else x for x in st["rules"]]
            return j(row)
        if path == "/rules/check":
            st["check"].append(body)
            return j({"rows": [{"line": 1, "word": "Kolhapur", "say": "Kol-haa-pur", "ipa": "", "lang": "mr", "state": "new"},
                               {"line": 2, "word": "Mithas", "say": "Mi-thaas", "ipa": "", "lang": "hi", "state": "replace"},
                               {"line": 3, "word": "Biryani", "say": "Bir-yaa-nee", "ipa": "", "lang": "", "state": "bad", "why": "Unknown language: klingon"}],
                      "new": 1, "replace": 1, "bad": 1, "room": 198})
        if path == "/rules/import":
            st["imported"].append(body)
            return j({"added": 2, "rules": [], "skipped": []})
        if path == "/hear":
            st["hear"].append(body)
            return r.fulfill(content_type="audio/wav", body=b"RIFF\x24\x00\x00\x00WAVEfmt ")
        if path == "/apps":
            return j({"keys": [], "hooks": [], "events": ["sound.ready"], "doors": [], "rate_hour": 120, "max_keys": 5, "max_hooks": 3})
        if path == "/settings" and req.method == "PUT":
            st["settings"].append(body)
            return j({"settings": body})
        return r.fallback()
    pg.route("**/api/vocal/**", route)


def _st():
    return {"calls": [], "tts": [], "sent": [], "rows": [], "items": [], "change": [], "uploads": 0, "settings": [], "addlang": [], "bulk": [], "zip": [], "star": [],
            "rule": [], "check": [], "imported": [], "hear": [], "gone": [], "hist": [dict(h) for h in HIST],
            "rules": [{"id": "pr_1", "word": "Mithas", "say": "Mi-thaas", "ipa": "mɪˈt̪ʰaːs", "lang": "hi"}] + [dict(x) for x in RULES]}


def test_your_sounds_dictionary_and_settings_in_a_real_browser(arena_server):  # noqa: F811
    base, browser, key = arena_server
    shots = os.environ.get("HOOLA_SHOTS")
    for scheme, width in (("light", 1440), ("dark", 1440), ("light", 390)):
        st = _st()
        ctx = browser.new_context(viewport={"width": width, "height": 900}, color_scheme=scheme)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(getattr(e, "stack", "") or e)[:400]))
        pg.on("dialog", lambda d: d.accept())
        pg.route("**/api/console/config", lambda r: r.fulfill(json=CONFIG))
        install(pg, st)
        sd(pg, st)
        open_vocal(pg, base)
        phone = width < 600
        # Your sounds: kinds with counts, by day, the chosen sound on the right
        page_to(pg, "sounds", phone)
        pg.wait_for_selector("#hvView .hv-sdlist")
        v = pg.locator("#hvView")
        t = v.text_content()
        assert "Kept on this server" in t and "Today" in t and "Rain on a tin roof" in t and "Use it again" in t and "Download as" in t
        assert pg.evaluate(UNSAID) == [] and pg.evaluate(NO_SIDEWAYS), (scheme, width)
        if shots:
            pg.screenshot(path=f"{shots}/yd-{scheme}-{width}-1-sounds.png", full_page=True)
        pg.locator("#hvView [data-a='sdkind'][data-val='sfx']").click()
        assert pg.locator("#hvView .hv-sdr").count() == 1
        pg.locator("#hvView [data-a='sdkind'][data-val='kept']").click()
        assert pg.locator("#hvView .hv-sdr").count() == 1
        pg.locator("#hvView [data-a='sdkind'][data-val='all']").click()
        pg.locator("#hvView [data-a='sdsel'][data-id='vo_c2c2c2c2c2c2']").click()
        assert "Hear before and after" in pg.locator("#hvView .hv-sdp").text_content()
        pg.locator("#hvView .hv-sdp [data-a='sdstar']").click()
        pg.wait_for_timeout(200)
        assert st["star"][-1] == {"id": "vo_c2c2c2c2c2c2", "on": True}
        # select several: keep all, a ZIP in MP3, remove
        pg.locator("#hvView [data-a='sdpick']").click()
        pg.locator("#hvView [data-a='sdtick'][data-id='vo_c1c1c1c1c1c1']").first.click()
        pg.locator("#hvView [data-a='sdtick'][data-id='vo_c2c2c2c2c2c2']").first.click()
        assert "2 selected" in v.text_content() and pg.evaluate(UNSAID) == []
        if shots:
            pg.screenshot(path=f"{shots}/yd-{scheme}-{width}-2-select.png")
        pg.locator("#hvView [data-a='sdbulk'][data-val='keep']").click()
        pg.wait_for_timeout(300)
        assert st["bulk"][-1] == {"ids": ["vo_c1c1c1c1c1c1", "vo_c2c2c2c2c2c2"], "action": "keep"}
        pg.locator("#hvView [data-a='sdzip']").click()
        pg.locator(".hmenu .mi", has_text="MP3").click()
        pg.wait_for_timeout(300)
        assert st["zip"][-1] == {"ids": ["vo_c1c1c1c1c1c1", "vo_c2c2c2c2c2c2"], "format": "mp3"}
        pg.locator("#hvView [data-a='sdbulk'][data-val='remove']").click()
        pg.wait_for_function("() => !document.querySelector('#hvView .hv-sdtop.pick')")
        assert st["bulk"][-1]["action"] == "remove" and "Rain on a tin roof" not in v.text_content()
        # Dictionary: add, IPA letters, hear, test a sentence, change, import checked first
        page_to(pg, "dict", phone)
        pg.wait_for_selector("#hvView .hv-dtab")
        t = v.text_content()
        assert "Mi-thaas" in t and "in 3 sounds" in t and "not used yet" in t and "Test a sentence" in t
        pg.locator("#hvDW").fill("Pune")
        pg.locator("#hvDS").fill("Poo-nay")
        pg.locator("#hvView [data-a='dipa'][data-val='ə']").click()
        assert pg.locator("#hvDI").input_value() == "ə"
        pg.locator("#hvView [data-a='dhear'][data-val='form']").click()
        pg.wait_for_timeout(300)
        assert st["hear"][-1]["text"] == "Poo-nay"
        pg.locator("#hvView [data-a='dwsave']").click()
        pg.wait_for_timeout(300)
        assert st["rule"][-1] == ("POST", {"word": "Pune", "say": "Poo-nay", "ipa": "ə", "lang": ""})
        pg.locator("#hvDT").fill("Aaj hi aaiye Mithas Sweets, Nashik mein.")
        assert "2 words will be read your way" in pg.locator("[data-dtline]").text_content()
        pg.locator("#hvView [data-a='dhear'][data-val='test']").click()
        pg.wait_for_timeout(300)
        assert st["hear"][-1]["text"] == "Aaj hi aaiye Mithas Sweets, Nashik mein."
        assert pg.evaluate(UNSAID) == [] and pg.evaluate(NO_SIDEWAYS), (scheme, width)
        if shots:
            pg.screenshot(path=f"{shots}/yd-{scheme}-{width}-3-dict.png", full_page=True)
        pg.locator("#hvView [data-a='dedit'][data-id='pr_2']").click()
        assert pg.locator("#hvDS").input_value() == "Naa-shik"
        pg.locator("#hvDS").fill("Naa-sheek")
        pg.locator("#hvView [data-a='dwsave']").click()
        pg.wait_for_timeout(300)
        assert st["rule"][-1][0] == "PUT" and st["rule"][-1][1]["id"] == "pr_2" and st["rule"][-1][1]["say"] == "Naa-sheek"
        pg.locator("#hvView [data-a='dictimp']").first.click()
        pg.locator("#hvDImp").fill("Kolhapur,Kol-haa-pur,,mr\nMithas,Mi-thaas,,hi\nBiryani,Bir-yaa-nee,,klingon")
        pg.locator("#hvView [data-a='dcheck']").click()
        pg.wait_for_selector("#hvView .hv-dir")
        t = v.text_content()
        assert "Check before adding" in t and "Replaces yours" in t and "Unknown language: klingon" in t and "Add 1 word, replace 1" in t
        if shots:
            pg.screenshot(path=f"{shots}/yd-{scheme}-{width}-4-import.png", full_page=True)
        pg.locator("#hvView [data-a='dimport']").click()
        pg.wait_for_timeout(300)
        assert st["imported"][-1]["text"] == "Kolhapur,Kol-haa-pur,,mr\nMithas,Mi-thaas,,hi"
        # Settings: the section list, the cards, keep my sounds
        page_to(pg, "settings", phone)
        pg.wait_for_selector("#hvView .hv-setnav")
        t = v.text_content()
        assert all(x in t for x in ("Defaults", "Engines", "What things cost", "This month", "Keep my sounds", "For your apps", "The rules Hoola keeps", "What you made, by kind"))
        pg.locator("#hvView [data-a='setgo'][data-val='keep']").click()
        pg.locator("#hvView [data-a='keepset'][data-val='90']").click()
        pg.wait_for_timeout(300)
        assert st["settings"][-1] == {"keep_days": 90}
        assert pg.evaluate(UNSAID) == [] and pg.evaluate(NO_SIDEWAYS), (scheme, width)
        if shots:
            pg.screenshot(path=f"{shots}/yd-{scheme}-{width}-5-settings.png", full_page=True)
        assert not errs, errs
        ctx.close()
