"""v0.999.174 TEMPLATES, REDESIGNED (owner, on the design claude.ai/artifact/JzJ7s7bqJGC983XfwCZbMk: "PERFECT GO BUILD"):
the library (her own templates first, the ready-made ones as cards with a poster, what each is for and its blanks), the
Use page (one field per blank with a plain label, the live preview filling in, language / face / voice / engine / frame,
the draft free and the video priced again in the Studio), saving a video as a template by tapping the words that change,
and one free draft per row of a sheet - every control on a real route, walked in a real browser at computer and phone width."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.interactive import hub as H
from app.interactive import studio as S
from tests.test_v0999_172_interactive_chat import DRAFT, ix, ix_server   # noqa: F401  (fixtures)

ROOT = Path(__file__).resolve().parents[1]


def _vals(t):
    return {b["key"]: f"v-{b['key']}" for b in t["blanks"]}


def test_the_ready_made_set_explains_every_blank(ix):
    ts = {t["id"]: t for t in H.templates("default")}
    assert {"tp_remind", "tp_event"} <= set(ts) and len([t for t in ts.values() if not t["mine"]]) == 8
    for t in ts.values():
        assert t["line"] and t["seconds"] > 3 and t["count"] == len(t["scenes"])
        for b in t["blanks"]:
            assert b["label"] and b["example"].startswith(("e.g.", "with")) and (b["where"] or b["closing"]), (t["id"], b)
            assert "India" not in b["example"]
    off = ts["tp_offer"]
    assert [b["key"] for b in off["blanks"]] == ["festival", "shop", "item", "price", "last_date"]
    assert off["blanks"][1]["where"] == [1, 3] and off["blanks"][1]["closing"] is True
    assert ts["tp_reel"]["group"] == "Reels" and ts["tp_thanks"]["name"] == "Thank you"


def test_using_one_refuses_a_gap_by_name_and_keeps_her_picks(ix):
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    t = next(x for x in H.templates("default") if x["id"] == "tp_offer")
    vals = {"festival": "Christmas", "shop": "Café Azul", "item": "Pastel de nata box", "price": "€9"}
    r = c.post("/api/interactive/hub/template/use", json={"id": "tp_offer", "values": vals})
    assert r.status_code == 422 and r.json()["detail"] == "Fill in: last day of the offer."
    vals["last_date"] = "31 December"
    p = c.post("/api/interactive/hub/template/use", json={"id": "tp_offer", "values": vals, "lang": "auto",
                                                          "opts": {"aspect": "1:1", "voice": "v_warm", "face_layout": "full"}}).json()
    assert p["lang"] == "en" and p["aspect"] == "1:1" and p["voice"] == "v_warm" and p["template"] == "tp_offer"
    assert "Pastel de nata box is now only €9." in [s["say"] for s in p["scenes"]] and p["closing"] == "Café Azul"
    q = c.post("/api/interactive/hub/template/use", json={"id": "tp_offer", "values": vals, "opts": {"aspect": "9:16"}}).json()
    assert q["shape"] == "reel" and q["aspect"] == "9:16"
    assert next(x for x in H.templates("default") if x["id"] == "tp_offer")["used"] == 2
    assert t["used"] == 0


def test_another_language_is_translated_and_numbers_are_checked(ix, monkeypatch):
    vals = {"name": "Amara", "place": "Riverside Clinic", "date": "Thursday", "time": "3:30 pm"}

    def think(system, prompt):
        lines = [ln.split(". ", 1)[1] for ln in prompt.split("Lines:\n", 1)[1].splitlines() if ". " in ln]
        return {"lines": [f"[pt] {x}" for x in lines]}
    p = H.template_use("default", "tp_remind", vals, lang="pt", think=think)
    assert p["lang"] == "pt" and p["template"] == "tp_remind" and p["title"] == "Appointment reminder"
    assert p["scenes"][1]["say"].startswith("[pt] ") and "3:30 pm" in p["scenes"][1]["say"]
    ids = [x["id"] for x in S._load("default")["projects"]]
    assert ids == [p["id"]]                                  # the English one in between is not left behind

    def broken(system, prompt):
        return {"lines": []}
    q = H.template_use("default", "tp_remind", vals, lang="ja", think=broken)
    assert q["lang"] == "en" and "could not translate" in q["notice"]
    # Hindi ready-made words are written, not translated
    h = H.template_use("default", "tp_rate", {"item": "Sona", "rate": "₹7,200", "shop": "Mehta Jewellers"}, lang="hi", think=broken)
    assert h["lang"] == "hi" and "rate" in h["scenes"][0]["say"] and "notice" not in h


def test_saving_marks_her_words_as_blanks(ix):
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    p = S.draft("default", "Welcome new guests to my café in Lisbon", lang="pt")
    S.save("default", p["id"], {"scenes": [{"say": "Fresh sourdough this Saturday, only $6 each.", "look": {"kind": "price", "new": "$6", "label": "Sourdough loaf"}},
                                           {"say": "Come early to Rosie's Bakery. We open at 8 am on 14 March.", "look": {"kind": "none"}}],
                                "closing": "Rosie's Bakery", "brand": "Rosie's Bakery"})
    w = c.get(f"/api/interactive/hub/template/suggest?project={p['id']}").json()["words"]
    got = {x["kind"]: x["text"] for x in w}
    assert got["shop"] == "Rosie's Bakery" and got["price"] == "$6" and got["time"] == "8 am" and got["date"] == "14 March" and got["day"] == "Saturday"
    r = c.post("/api/interactive/hub/template", json={"project": p["id"], "name": "Weekend bake sale", "blanks": [{"text": "Mars", "key": "x"}]})
    assert r.status_code == 422 and "is not in this video" in r.json()["detail"]
    t = c.post("/api/interactive/hub/template", json={"project": p["id"], "name": "Weekend bake sale", "blanks": [
        {"text": "$6", "key": "price", "label": "Price"}, {"text": "Rosie's Bakery", "key": "shop name", "label": "Shop name"}]}).json()
    assert t["mine"] and t["lang"] == "pt" and t["line"].startswith("From ")
    assert t["scenes"][0]["say"] == "Fresh sourdough this Saturday, only {price} each." and t["scenes"][0]["look"]["new"] == "{price}"
    assert t["closing"] == "{shop_name}" and [b["key"] for b in t["blanks"]] == ["price", "shop_name"]
    assert t["blanks"][1]["label"] == "Shop name" and t["blanks"][1]["example"] == "e.g. Rosie's Bakery"
    assert S.project("default", p["id"])["scenes"][0]["say"].startswith("Fresh sourdough")      # the video stays as it was


def test_a_sheet_makes_one_draft_per_row_and_names_the_gaps(ix):
    c = TestClient(__import__("app.main", fromlist=["app"]).app)
    rows = [{"name": "Amara", "shop": "Bloom Florist"}, {"name": "", "shop": "Bloom Florist"}, {"Name": "Kenji", "shop": "Bloom Florist", "title": "Kenji"}]
    r = c.post("/api/interactive/hub/template/many", json={"id": "tp_thanks", "rows": rows}).json()
    assert len(r["made"]) == 2 and r["skipped"] == [{"row": 2, "why": "Fill in: their name."}]
    ps = {x["id"]: x for x in S._load("default")["projects"]}
    assert ps[r["made"][1]]["title"] == "Kenji" and "Kenji" in ps[r["made"][1]]["scenes"][0]["say"]
    big = c.post("/api/interactive/hub/template/many", json={"id": "tp_thanks", "rows": [{"name": "a", "shop": "b"}] * 51})
    assert big.status_code == 422


def test_the_page_code_is_wired():
    root = ROOT / "app" / "static" / "console"
    js = (root / "interactive.js").read_text("utf-8")
    css = (root / "interactive2.css").read_text("utf-8")
    assert subprocess.run(["node", "--check", str(root / "interactive.js")], capture_output=True).returncode == 0
    blk = js[js.index("templates (v0.999.174"):js.index("// ------------------------------------------------------------------ pages ---")]
    drawn = set(re.findall(r'data-a="([a-z]+)"', blk))
    cases = set(re.findall(r"case '([a-z]+)':", js))
    assert drawn <= cases, drawn - cases
    assert "prompt(`${v.replace" not in js                           # no more one-box-per-word prompts
    for r in ("/template/use", "/template/suggest?project=", "/template/many", "/estimate?engine=", "/api/vocal/hear"):
        assert r in js, r
    for c in (".hx-tgrid", ".hx-tc", ".hx-tpo", ".hx-tm", ".hx-tempty", ".hx-tuse", ".hx-tform", ".hx-tlive", ".hx-topt", ".hx-tprice",
              ".hx-dlg", ".hx-svw", ".hx-svb", ".g-offers"):
        assert f"#hxRoot {c}" in css, c


def _until(ok, wait=8.0):
    import time
    end = time.time() + wait
    while time.time() < end:
        if ok():
            return
        time.sleep(0.15)
    assert ok()


def _open(pg, base, vp):
    pg.goto(base + "/console/?v=interactive")
    pg.wait_for_selector("#hxRoot .hx-side [data-p=templates]", state="attached", timeout=25000)
    if vp["width"] < 900:
        pg.click("#hxRoot .hx-menu")
    pg.click("#hxRoot .hx-side [data-p=templates]")
    pg.wait_for_selector("#hxRoot .hx-tgrid", timeout=15000)


def test_templates_in_a_real_browser(ix_server):
    base, browser, key = ix_server
    shots = os.environ.get("HOOLA_SHOTS")
    errors: list[str] = []
    p = S.draft("default", "Welcome new guests to my café in Lisbon", lang="pt")
    S.save("default", p["id"], {"scenes": [{"say": "Fresh sourdough this Saturday, only $6 each.", "look": {"kind": "none"}},
                                           {"say": "Come early. We open at 8 am.", "look": {"kind": "none"}}], "title": "Saturday bakes"})
    for vp in ({"width": 1440, "height": 900}, {"width": 390, "height": 844}):
        ctx = browser.new_context(viewport=vp)
        ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        _open(pg, base, vp)
        assert pg.locator(".hx-tc").count() == 8
        pg.click(".hx-tchips [data-val=Reminders]")
        assert pg.locator(".hx-tc").count() == 1 and "Appointment reminder" in pg.inner_text("#hxTplList")
        pg.click(".hx-tchips [data-val=all]")
        pg.fill("#hxTq", "zzz-none")
        assert "No templates match" in pg.inner_text("#hxTplList")
        pg.fill("#hxTq", "")
        if vp["width"] > 900:
            pg.click(".hx-libbar [data-a=ttab][data-val=mine]")
            pg.wait_for_selector(".hx-tempty", timeout=5000)
            if shots:
                pg.wait_for_timeout(400)
                pg.screenshot(path=f"{shots}/ix174-yours-empty-1440.png", full_page=True)
            pg.click(".hx-tempty [data-a=ttab][data-val=ready]")
        if shots:
            pg.wait_for_timeout(400)
            pg.screenshot(path=f"{shots}/ix174-library-{vp['width']}.png", full_page=True)
        assert pg.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 1
        # using one
        pg.click(".hx-tc:has-text('Festival offer') .hx-tcf [data-a=tpluse]")
        pg.wait_for_selector("#hxRoot .hx-tuse", timeout=10000)
        assert "0 of 5 filled" in pg.inner_text("#hxTuN") and pg.locator("[data-a=tumake]").is_disabled()
        for k, v in (("festival", "Christmas"), ("shop", "Café Azul"), ("item", "Pastel de nata box"), ("price", "€9")):
            pg.fill(f"[data-tv={k}]", v)
        assert "4 of 5 filled" in pg.inner_text("#hxTuN") and "last day of the offer" in pg.inner_text("#hxTuPrice")
        if vp["width"] > 900:
            assert "Pastel de nata box" in pg.inner_text("#hxTuScenes") and pg.locator("#hxTuScenes mark.hx-tgap").count() == 1
        pg.click("[data-a=tuscene][data-n='1'] >> nth=0")
        assert "€9" in pg.inner_text("#hxTuStage")
        pg.wait_for_selector("#hxTuPrice .hx-num:has-text('credit')", timeout=8000)
        if shots:
            pg.screenshot(path=f"{shots}/ix174-use-{vp['width']}.png", full_page=True)
        assert pg.evaluate("document.documentElement.scrollWidth - window.innerWidth") <= 1
        pg.fill("[data-tv=last_date]", "31 December")
        pg.click("[data-a=tuaspect][data-val='1:1']")
        pg.click("[data-a=tumake]")
        pg.wait_for_selector("#hxRoot .hx-edb", timeout=15000)
        made = S._load("default")["projects"][0]
        assert made["template"] == "tp_offer" and made["aspect"] == "1:1" and "Café Azul" in made["closing"]
        ctx.close()
    # saving a video as a template, then a sheet
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    _open(pg, base, {"width": 1440})
    pg.click(".hx-libh [data-a=tplfrom]")
    pg.click(".hx-tpr:has-text('Saturday bakes')")
    pg.wait_for_selector("#hxSvText .hx-svs", timeout=8000)                 # Hoola's suggestions are underlined
    pg.click("#hxSvText .hx-svs:has-text('$6')")
    pg.click("#hxSvText .hx-svw:has-text('sourdough')")
    _until(lambda: pg.locator(".hx-svbr").count() == 2)
    assert pg.inner_text("#hxSvText .hx-svb >> nth=0").strip() in ("sourdough", "price")      # a blank shows its name
    pg.fill("[data-svk='1']", "bake")
    if shots:
        pg.wait_for_timeout(500)
        pg.screenshot(path=f"{shots}/ix174-save-1440.png")
    pg.click("[data-a=svsave]")
    pg.wait_for_selector(".hx-tm", timeout=8000)
    mine = next(t for t in H.templates("default") if t["mine"])
    assert [b["key"] for b in mine["blanks"]] == ["bake", "price"] and "{bake}" in mine["scenes"][0]["say"]
    pg.click(".hx-tm [data-a=tpluse]")
    pg.wait_for_selector("#hxRoot .hx-tuse", timeout=10000)
    pg.click("[data-a=tusheet]")
    pg.fill("#hxShText", "bake,price\nBagels,$3\nCroissants,$2\n,$5")
    assert "3 rows" in pg.inner_text("#hxShSum")
    pg.click("[data-a=shmake]")
    pg.wait_for_selector("#hxDlg .hx-why", timeout=15000)
    assert "2 drafts made" in pg.inner_text("#hxDlg") and "Row 3" in pg.inner_text("#hxDlg .hx-why")
    pg.click("#hxDlg [data-a=shstudio]")
    pg.wait_for_selector("#hxRoot .hx-kpis", timeout=15000)
    ctx.close()
    assert not errors, errors
