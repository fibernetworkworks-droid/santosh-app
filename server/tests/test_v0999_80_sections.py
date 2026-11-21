"""v0.999.80 D8 wave 3 (docs/WEB_DESIGN_ENGINE_PLAN.md phase D8): the sections of sites that are not a business - a
person (about me, resume, case studies), an event (schedule, RSVP, venue), a community (members, discussions), a course
(lessons, quiz, progress), a tool (a calculator with Hoola's own checked sums) and a game (memory, scramble) - as kit
blocks the writer fills from her prototype by code (Rs 0). Her prototype names such a section custom_<words>; the writer
finds the block by those words; a section no block fits (or a quiz without her marked answers) is written specially as
before. An RSVP and a question reach her as enquiries."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.appengine import parity as PY
from app.appengine import writer as W
from tests.test_v0814_app_engine import _box, ae_env  # noqa: F401  (fixture)
from tests.test_v0999_77_features import _serve
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[2]
NEW = ["about-me", "resume", "case-studies", "schedule", "rsvp", "venue", "members", "discussions", "lessons", "quiz",
       "progress", "tool-panel", "game-area"]


@pytest.fixture(autouse=True)
def _on(monkeypatch):
    monkeypatch.setenv("APP_ENGINE_AUTOFIX", "true")
    monkeypatch.setenv("STUDIO_REACT_SITES", "true")
    monkeypatch.setenv("SITE_CRITIC", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _pages():
    return [{"slug": "home", "title": "Home", "for": "public", "sections": [
        {"type": "hero", "heading": "Asha and Rohan are getting married", "line": "14 and 15 December, in Pune.", "cta": "Will you come?"},
        {"type": "custom_schedule", "label": "Schedule", "heading": "The programme", "line": "Two days in one courtyard.",
         "items": ["Saturday 14 Dec · 5:00 pm - Haldi in the courtyard", "8:00 pm - Sangeet and dinner",
                   "Sunday 15 Dec · 11:30 am - The wedding - Lunch follows"]},
        {"type": "custom_rsvp", "label": "RSVP", "heading": "Will you come?", "line": "Tell us by 30 November.", "items": []},
        {"type": "custom_venue", "label": "Venue", "heading": "Venue", "line": "",
         "items": ["The Banyan Courtyard, Law College Road, Pune 411004", "Ten minutes by auto from Deccan"]},
        {"type": "custom_quiz", "label": "Couple quiz", "heading": "How well do you know us?", "line": "Three questions.",
         "items": ["Where did they meet? College library* / A wedding / Office", "Who cooks? Rohan / Asha*"]},
        {"type": "custom_emi_calculator", "label": "EMI calculator", "heading": "Plan your loan", "line": "", "items": []},
        {"type": "custom_memory_game", "label": "Memory game", "heading": "Find the pairs", "line": "",
         "items": ["Mango", "Lotus", "Peacock"]},
    ]}]


# ---------------------------------------------------------------- 1. the blocks and the writer, by code
def test_every_new_block_passes_the_rules_and_has_a_writer():
    from app.appengine import image as IMG
    from app.appengine import rules as RL
    deps = set(IMG.CORE) | set(IMG.DEV)
    for name in NEW + ["_send"]:
        rel = f"src/components/blocks/{name}.tsx"
        code = (ROOT / "server/app/appengine/template" / rel).read_text()
        assert RL.check_file(rel, code, deps) == [], rel
        if name != "_send":
            assert name.replace("-", "_") in W.MAPPERS, name
            assert W.variants_of(name.replace("-", "_")), name


def test_her_custom_sections_find_their_block_by_their_words():
    ctx = W.Ctx("Asha & Rohan", _pages(), {"_site": {"id": "site_abc"}}, "s")
    got = {s["type"]: (W.block_props(s, ctx, 0) or ("",))[0] for s in _pages()[0]["sections"][1:]}
    assert got == {"custom_schedule": "schedule", "custom_rsvp": "rsvp", "custom_venue": "venue", "custom_quiz": "quiz",
                   "custom_emi_calculator": "tool_panel", "custom_memory_game": "game_area"}
    assert all(W.kit_ok(s, ctx) for s in _pages()[0]["sections"][1:])
    for odd in ({"type": "custom_lucky_spin", "label": "Lucky spin wheel", "items": ["a", "b", "c"]},
                {"type": "custom_mortgage_vs_rent", "label": "Rent or buy calculator", "items": []},
                {"type": "custom_quiz", "label": "Quiz", "items": ["Which is best? A / B / C"]}):   # no answer she marked
        assert not W.kit_ok(odd, ctx), odd                                                    # -> written specially


def test_the_words_are_read_without_inventing_anything():
    ctx = W.Ctx("Asha & Rohan", _pages(), {"_site": {"id": "site_abc"}}, "s")
    secs = {s["type"]: s for s in _pages()[0]["sections"]}
    _, _, sch = W.block_props(secs["custom_schedule"], ctx, 0)
    assert [d["day"] for d in sch["days"]] == ["Saturday 14 Dec", "Sunday 15 Dec"]
    assert sch["days"][0]["items"][1] == {"time": "8:00 pm", "title": "Sangeet and dinner", "note": "", "place": ""}
    _, _, qz = W.block_props(secs["custom_quiz"], ctx, 0)
    assert qz["questions"] == [{"q": "Where did they meet?", "options": ["College library", "A wedding", "Office"], "answer": 0},
                               {"q": "Who cooks?", "options": ["Rohan", "Asha"], "answer": 1}]
    _, _, vn = W.block_props(secs["custom_venue"], ctx, 0)
    assert vn["address"].startswith("The Banyan Courtyard") and vn["ways"] == ["Ten minutes by auto from Deccan"]
    _, _, rs = W.block_props(secs["custom_rsvp"], ctx, 0)
    assert rs["endpoint"] == "/api/site-forms/site_abc"
    _, _, rv = W.block_props({"type": "custom_resume", "label": "Experience",
                              "items": ["Design lead - Payments co (2021 - now)", "Skills: research, systems"]}, ctx, 0)
    assert rv["roles"] == [{"role": "Design lead", "place": "Payments co", "when": "2021 - now", "note": ""}]
    assert rv["skills"] == ["research", "systems"]
    files, rows = W.plan_files(_pages(), ctx)
    home = files["src/pages/HomePage.tsx"]
    assert 'tool="emi"' in home and '"answer":1' in home
    kit = W.kit_files(rows, False)
    assert "src/components/blocks/_send.tsx" in kit and "src/components/blocks/rsvp.tsx" in kit
    leaks = [x for x in W.sample_sentences() if x in home]
    assert not leaks, leaks                                                    # no kit sample words on her page


def test_the_checklist_reads_the_new_sections():
    st = {r["key"]: r for r in PY.check()["rows"]}
    for k in ("personal", "event", "tool", "game"):
        assert st[k]["state"] == "works", st[k]
    for k in ("community", "learning"):
        assert st[k]["state"] == "partial" and st[k]["missing"], st[k]


def test_the_prototype_is_told_the_shape_of_these_items():
    from app.site import prototype as PT
    assert "right answer*" in PT.COPY_SYSTEM and "Part name: lesson" in PT.COPY_SYSTEM


# ---------------------------------------------------------------- 2. a real wedding website, walked in Chromium
def test_a_guest_reads_the_programme_answers_the_rsvp_plays_and_calculates(ae_env, monkeypatch):
    from sqlalchemy import select
    from playwright.sync_api import sync_playwright
    from app.appengine import service as AE
    from app.appengine import speed as SP
    from app.db import session
    from app.site import ai as AI
    from app.site import prototype as PT
    from app.site import service as S
    from app.site.models import SiteLead
    _box()
    calls: list[str] = []
    monkeypatch.setattr(AI, "ask", lambda *a, **k: calls.append("ask") or (_ for _ in ()).throw(RuntimeError("no model")))
    v = S.new(T, "A wedding website for Asha and Rohan in Pune.", name="Asha and Rohan")
    PT._write_version(S._load(v["id"]), _pages(), "test", "hoola")
    calls.clear()
    PT.approve(T, v["id"], PT.meta(S._load(v["id"]))["hash"])
    out = S.view(S._load(v["id"]))
    assert out["status"] == "ready", out.get("error")
    assert calls == []                                         # every section from the kit: no model call
    app = AE._load(T, out["react"]["id"])
    dist = AE.ver_dir(app, app.version) / "dist"
    html = (dist / "index.html").read_text()
    for words in ("Haldi in the courtyard", "Sangeet and dinner", "Will you come?", "Ten minutes by auto from Deccan",
                  "Where did they meet?", "Plan your loan"):
        assert words in html, words                            # pre-rendered: readable before any JavaScript
    srv, base = _serve(dist)
    errors: list[str] = []
    try:
        with sync_playwright() as pw:
            b = SP._browser(pw)
            pg = b.new_page(viewport={"width": 1280, "height": 900})
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto(base, wait_until="load")
            sch = pg.locator('section[data-block="schedule"]')
            sch.scroll_into_view_if_needed()
            sch.get_by_role("tab", name="Sunday 15 Dec").click(timeout=15000)
            sch.get_by_text("The wedding").wait_for()
            rs = pg.locator('section[data-block="rsvp"]')
            rs.scroll_into_view_if_needed()
            pg.wait_for_timeout(600)
            rs.get_by_label("Your name").fill("Meera")
            rs.get_by_label("Mobile number").fill("9988776655")
            rs.get_by_role("radio", name="Yes, I will come").click()
            rs.get_by_label("How many of you, with you?").fill("3")
            rs.get_by_role("button", name="Send my answer").click()
            pg.get_by_text("See you there").first.wait_for(timeout=15000)
            qz = pg.locator('section[data-block="quiz"]')
            qz.scroll_into_view_if_needed()
            qz.get_by_role("button", name="College library").click(timeout=15000)
            qz.get_by_text("Right.").wait_for()
            tl = pg.locator('section[data-block="tool_panel"]')
            tl.scroll_into_view_if_needed()
            pg.wait_for_timeout(600)
            tl.get_by_label("Loan amount (₹)").fill("100000")
            tl.get_by_label("Interest a year (%)").fill("12")
            tl.get_by_label("Months").fill("12")
            tl.get_by_text("₹8,885").first.wait_for(timeout=15000)                  # 1,00,000 at 12 % for 12 months
            gm = pg.locator('section[data-block="game_area"]')
            gm.scroll_into_view_if_needed()
            pg.wait_for_timeout(600)
            gm.get_by_role("button", name="Card 1, face down").click(timeout=15000)
            gm.get_by_text("0 of 3 pairs · 0 turns").wait_for()
            b.close()
    finally:
        srv.shutdown()
    assert not errors, errors
    with session() as s:
        leads = list(s.scalars(select(SiteLead).where(SiteLead.site_id == v["id"])))
    assert len(leads) == 1 and "RSVP: coming, 3 people" in (leads[0].message or "")
