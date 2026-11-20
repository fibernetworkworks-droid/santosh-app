"""v0.999.48 O1 OPEN TO EVERYTHING (docs/WEB_DESIGN_ENGINE_PLAN.md phase O1, owner: "WE WANT ENTIER SAME LIKE A LOVABLE NAD
EMERGENT --- NOT ONLY FOR BUINESS" -> "GO O1"): the Web Studio plans any kind of site, not only a business. The architect
names what a site is FOR (purpose) beside its kind, a new kind `interactive` (a tool / calculator / quiz / game that works on
the page), the writer prompts stop assuming a business, a working section's script may be up to 16,000 characters (still no
network / storage / innerHTML), the home copy / starters / details form follow the site's purpose.
Done-when: a portfolio, a wedding, a game page and a calculator each get a plan of their own kind, not a business plan."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1] / "app"


def _plan(kind: str, purpose: str, words: str, title: str) -> dict:
    from app.site import architect as AR
    raw = {"name": title, "summary": words, "kind": kind, "purpose": purpose, "complexity": "simple",
           "pages": [{"slug": "home", "title": "Home", "purpose": "the first page", "for": "public",
                      "sections": [{"type": "hero", "why": "say what it is"}]}]}
    return AR.clean(raw, words)


def test_four_non_business_asks_keep_their_own_kind_and_purpose():
    cases = [("brochure", "personal", "A portfolio for my wedding photography", "Portfolio"),
             ("lead_site", "event", "A wedding website for Asha and Ravi with RSVP", "Asha and Ravi"),
             ("interactive", "game", "A small arcade game page with a best score", "Kite Run"),
             ("interactive", "tool", "An EMI calculator with sliders and a chart", "EMI calculator")]
    for kind, purpose, words, title in cases:
        s = _plan(kind, purpose, words, title)
        assert s["kind"] == kind and s["purpose"] == purpose, (words, s["kind"], s["purpose"])
        assert s["kind"] not in ("portal", "web_app", "shop"), words           # never turned into a business system


def test_purpose_and_interactive_are_known_words():
    from app.site import architect as AR
    assert "interactive" in AR.KINDS and "interactive" not in AR.APP_KINDS
    for p in ("business", "personal", "creator", "event", "community", "education", "tool", "game", "product", "ai_app"):
        assert p in AR.PURPOSES and AR.PURPOSE_LABELS.get(p)
    assert _plan("brochure", "made-up", "A page", "X")["purpose"] == ""      # an unknown purpose is dropped, not kept
    sysp = " ".join(AR._system().split())
    assert "@@PURPOSES@@" not in sysp and "@@PURPOSES@@" not in AR.UNDERSTAND
    assert "NOT every ask is a business" in sysp and "INTERACTIVE kind" in sysp and "game" in sysp


def test_interactive_words_with_login_still_become_a_system_only_when_not_interactive():
    s = _plan("interactive", "game", "a quiz game for my class, no sign in", "Quiz")
    assert s["kind"] == "interactive"                                         # 'sign in' in her words does not force a portal
    assert _plan("brochure", "business", "a portal where parents sign in", "School")["kind"] == "portal"


def test_writer_prompts_do_not_assume_a_business():
    from app.site import ai as AI
    assert "Not every site is a business" in AI.SECTION_SYSTEM and "WORKING SECTIONS" in AI.SECTION_SYSTEM
    assert "requestAnimationFrame" in AI.SECTION_SYSTEM


def test_a_working_section_has_room_but_keeps_the_bans():
    from app.site import build as B
    assert B.JS_MAX == 16000
    for bad in ("fetch('/x')", "localStorage.setItem('a','b')", "el.innerHTML = s", "eval('1')"):
        assert B.BAD_JS.search(bad), bad


def test_photo_step_and_questions_speak_plainly():
    src = (ROOT / "site" / "service.py").read_text()
    assert "Making photos for your business" not in src and "Making photos for your site" in src
    assert "skip if it is not a place" in src
    from app.site import activity as A
    assert "Making photos for your site" in (ROOT / "site" / "activity.py").read_text()
    assert A is not None


def test_studio_home_and_details_follow_purpose():
    js = (ROOT / "static" / "console" / "webstudio.js").read_text()
    assert "Describe your business in one line" not in js and "three complete designs" not in js
    assert "for yourself, an event, a class, or just for fun" in js
    assert "'a wedding website with RSVP...'" in js and "'a quiz game for my class...'" in js and "'an EMI calculator...'" in js
    assert "const CHIPS = ['Website', 'Online store', 'Web app', 'Portfolio', 'Event', 'Community', 'Course', 'Tool or game'];" in js
    assert "biz ? 'Business details' : 'Site details'" in js and "M(M(v.plan).spec).purpose" in js
    assert "yourbusiness" not in js


def test_starters_cover_every_kind_of_site():
    from app.site import starters as ST
    js = (ROOT / "static" / "console" / "webstudio.js").read_text()
    assert all(f"'{c}'" in js for c in ST.CHIPS)                              # the page and the server name the same chips
    kinds = {x["kind"] for x in ST.STARTERS}
    assert {"Portfolio", "Event", "Community", "Course", "Tool or game"} <= kinds
    ids = {x["id"] for x in ST.STARTERS}
    assert {"event-wedding", "tool-emi", "game-quiz", "game-arcade", "port-dev"} <= ids
