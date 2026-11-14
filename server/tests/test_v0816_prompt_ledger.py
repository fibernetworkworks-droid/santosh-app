"""v0.816 NATIJA KHATA (built as 0.806) - the outcome ledger (plan P4 of docs/HOOLA_PROMPTING_PLAN.md): one row per prompt she took out of
Hoola Prompting and what happened to the result. Shape only - her words are never stored. No model runs here."""
import json
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.test_v0312_arena_screen import arena_server  # noqa: F401
from tests.test_v121_site import site_env  # noqa: F401

REPO = Path(__file__).resolve().parents[2]
CON = REPO / "server" / "app" / "static" / "console"
KEY = "test-key-ledger"
H = {"Authorization": f"Bearer {KEY}"}
PROMPT = ("A festive poster for Roop Salon in Pune: a brass diya with marigold flowers, warm evening light, "
          "the words Diwali offer Rs 499 hair spa, call 9812345678, portrait 4:5")


@pytest.fixture
def lg(env, monkeypatch):
    monkeypatch.setenv("API_KEY", KEY)
    from app.config import get_settings
    get_settings.cache_clear()
    from app.prompting import context as C
    from app.prompting import ledger as L
    monkeypatch.setattr(C, "known", lambda t: {"name": "", "tagline": "", "colours": [], "tone": "", "language": "",
                                                "about": "", "items": []})
    yield L
    get_settings.cache_clear()


def client():
    from app.main import app
    return TestClient(app)


def brief(section="image", score_slots=("subject",)):
    from app.prompting import brief as B
    return B.validate({"section": section, "intent": "diwali poster for my salon, Rs 499",
                       "slots": {k: {"value": "a brass diya", "source": "her_answer"} for k in score_slots}})


def row(L, rid):
    from app.db import session
    with session() as s:
        r = s.get(L.PromptRun, rid)
        return {c.name: getattr(r, c.name) for c in L.PromptRun.__table__.columns}


def test_a_row_holds_shape_never_her_words(lg):
    rid = lg.hand("t1", PROMPT, brief())
    r = row(lg, rid)
    blob = json.dumps({k: str(v) for k, v in r.items()}).lower()
    for secret in ("499", "9812345678", "roop", "pune", "diya", "marigold", "salon", "diwali"):
        assert secret not in blob, secret
    assert r["section"] == "image" and r["status"] == "handed" and r["score"] > 0 and r["dialect"] == "image-1"
    assert json.loads(r["slots"]) == {"subject": "her_answer"}          # slot NAMES and sources only
    assert len(r["brief_hash"]) == 64 and all(len(x) == 10 for x in json.loads(r["sig"]))
    assert lg.signature("t1", PROMPT) != lg.signature("t2", PROMPT)       # salted per user


def test_incognito_and_her_switch_write_nothing(lg, monkeypatch):
    assert lg.hand("t1", PROMPT, brief(), incognito=True) is None
    lg.set_prefs("t1", ledger=False)
    assert lg.hand("t1", PROMPT, brief()) is None
    lg.set_prefs("t1", ledger=True)
    assert lg.hand("t1", PROMPT, brief())
    monkeypatch.setenv("PROMPTING_LEDGER", "false")
    from app.config import get_settings
    get_settings.cache_clear()
    assert lg.hand("t1", PROMPT, brief()) is None and lg.claim("t1", "image", PROMPT, "cj_1") is None


def test_claim_exact_edited_and_stranger(lg):
    rid = lg.hand("t1", PROMPT, brief())
    assert lg.claim("t2", "image", PROMPT, "cj_x") is None                # another user's text is not hers
    assert lg.claim("t1", "image", "a completely different picture of a mountain lake at dawn", "cj_y") is None
    assert lg.claim("t1", "web", PROMPT, "site_1") is None                # another engine
    assert lg.claim("t1", "image", PROMPT + "\nStyle: bright and clean.", "cj_1") == rid
    r = row(lg, rid)
    assert r["status"] == "running" and r["edited_before"] is True and " cj_1 " in r["refs"]


def test_picture_ready_then_kept_edited_dropped(lg):
    rid = lg.hand("t1", PROMPT, brief())
    lg.claim("t1", "image", PROMPT, "cj_1")
    lg.ready("cj_1", ["cr_a", "cr_b"], model="img-model", usd=0.04)
    r = row(lg, rid)
    assert r["status"] == "ready" and r["usd"] == 0.04 and " cr_a " in r["refs"] and r["model"] == "img-model"
    lg.event("t2", "cr_a", "downloaded")                                   # not her result
    assert row(lg, rid)["grade"] == ""
    lg.event("t1", "cr_a", "downloaded")
    r = row(lg, rid)
    assert r["grade"] == "kept" and r["strong"] is True and r["status"] == "settled"
    lg.event("t1", "cr_a", "edited")
    assert row(lg, rid)["grade"] == "kept_after_edit"
    lg.event("t1", "cr_a", "redo")                                         # her keep stands against a later redo
    assert row(lg, rid)["grade"] == "kept_after_edit"
    lg.event("t1", "cr_b", "deleted")                                      # only her delete undoes it
    assert row(lg, rid)["grade"] == "dropped"


def test_same_prompt_again_means_the_first_was_redone(lg):
    first = lg.hand("t1", PROMPT, brief())
    lg.claim("t1", "image", PROMPT, "cj_1")
    lg.ready("cj_1", ["cr_a"])
    second = lg.claim("t1", "image", PROMPT, "cj_2")                       # she pressed Create again
    assert second and second != first
    assert row(lg, first)["grade"] == "redone" and row(lg, second)["origin"] == "again"
    assert row(lg, second)["score"] == row(lg, first)["score"] and row(lg, second)["status"] == "running"
    lg.failed("cj_2")                                                       # the engine failing is not her verdict
    assert row(lg, second)["grade"] == "" and row(lg, second)["status"] == "settled"


def test_silence_is_read_by_rule(lg):
    from app.db import now
    a = lg.hand("t1", PROMPT, brief())                                      # never run
    b = lg.hand("t1", PROMPT + " second one with other words entirely here", brief(), how="copy")
    c = lg.hand("t1", "website for a sweet shop with menu page contact page and order on whatsapp button", brief("web", ("what",)))
    lg.claim("t1", "web", "website for a sweet shop with menu page contact page and order on whatsapp button", "site_9")
    lg.ready("site_9", usd=0.5)
    assert lg.settle("t1") == 0                                             # nothing is old enough yet
    assert lg.settle("t1", at=now() + timedelta(days=4)) == 3
    assert row(lg, a)["grade"] == "unused"
    assert row(lg, b)["grade"] == "" and row(lg, b)["status"] == "settled"   # copied out: unknown, not counted
    assert row(lg, c)["grade"] == "kept" and row(lg, c)["strong"] is False   # quiet keep, counted apart


def _many(L, tenant, n_kept, n_redone, score_slots=("subject",), recipe=""):
    for i in range(n_kept + n_redone):
        text = f"{PROMPT} number {i} {tenant} {'x'.join(score_slots)}"
        b = brief("image", score_slots)
        b["recipe_id"] = recipe
        L.hand(tenant, text, b)
        L.claim(tenant, "image", text, f"cj_{tenant}_{i}_{len(score_slots)}")
        L.ready(f"cj_{tenant}_{i}_{len(score_slots)}", usd=0.05)
        L.event(tenant, f"cj_{tenant}_{i}_{len(score_slots)}", "downloaded" if i < n_kept else "thumb_down")


def test_four_numbers_need_enough_runs(lg):
    _many(lg, "t1", 2, 1)
    n = lg.numbers("t1")["all"]
    assert n["graded"] == 3 and n["enough"] is False and n["kept_rate"] is None and n["inr_per_kept"] is None
    _many(lg, "t1", 4, 2, ("subject", "style"))
    n = lg.numbers("t1")
    a = n["all"]
    assert a["graded"] == 9 and a["kept"] == 6 and a["kept_rate"] == 67 and a["kept_by_her"] == 6
    assert a["redos_per_kept"] == 0.0 and a["dropped"] == 3 and a["inr_per_kept"] > 0 and a["minutes_to_kept"] is not None
    assert n["sections"]["image"]["kept_rate"] == 67 and n["sections"]["web"]["enough"] is False
    assert n["sections"]["image"]["score_check"]["verdict"] == "not_enough"
    assert lg.numbers("t2")["all"]["runs"] == 0                             # her numbers are hers


def test_score_is_checked_against_outcomes(lg):
    _many(lg, "t1", 8, 2, ("subject", "style", "scene", "light"))            # high score: 80% kept
    _many(lg, "t1", 3, 7, ("subject",))                                      # low score: 30% kept
    chk = lg.numbers("t1")["sections"]["image"]["score_check"]
    assert chk["verdict"] == "predicts" and chk["high"] == 80 and chk["low"] == 30
    _many(lg, "t3", 3, 7, ("subject", "style", "scene", "light"))
    _many(lg, "t3", 8, 2, ("subject",))
    assert lg.numbers("t3")["sections"]["image"]["score_check"]["verdict"] == "backwards"


def test_shared_view_and_recipe_order_respect_her_switch(lg):
    _many(lg, "t1", 5, 1, recipe="img-festival-poster")
    _many(lg, "t2", 1, 5, recipe="img-product-shot")
    rates = lg.recipe_rates()
    assert rates["img-festival-poster"] == {"kept": 5, "of": 6} and rates["img-product-shot"] == {"kept": 1, "of": 6}
    from app.prompting import recipes as R
    ids = [r["id"] for r in R.listing("image")["items"]]
    if "img-festival-poster" in ids and "img-product-shot" in ids:
        assert ids.index("img-festival-poster") < ids.index("img-product-shot")
        assert next(r for r in R.listing("image")["items"] if r["id"] == "img-festival-poster")["kept"] == {"kept": 5, "of": 6}
    lg.set_prefs("t2", share=False)
    assert "img-product-shot" not in lg.recipe_rates() and lg.numbers(None)["all"]["runs"] == 6
    assert lg.numbers("t2")["all"]["runs"] == 6                             # she still sees her own
    assert lg.forget("t1") == 6 and lg.numbers("t1")["all"]["runs"] == 0


def test_routes_and_owner_only_view(lg):
    c = client()
    assert c.post("/api/prompting/runs", json={"text": PROMPT}).status_code == 401
    b = brief()
    rid = c.post("/api/prompting/runs", headers=H, json={"text": PROMPT, "brief": b, "how": "run"}).json()["run"]
    assert rid.startswith("prn")
    assert c.post("/api/prompting/runs", headers=H, json={"text": PROMPT, "section": "nope"}).json() == {"run": None}
    got = c.get("/api/prompting/ledger", headers=H).json()
    assert got["recent"][0]["id"] == rid and got["prefs"] == {"share": True, "ledger": True} and got["owner"] is True
    assert "text" not in got["recent"][0] and "prompt" not in got["recent"][0]
    assert c.post(f"/api/prompting/runs/{rid}/thumb", headers=H, json={"value": "up"}).json() == {"ok": True}
    assert c.get("/api/prompting/ledger", headers=H).json()["recent"][0]["grade"] == "kept"
    assert c.post("/api/prompting/runs/zzz/thumb", headers=H, json={"value": "up"}).status_code == 404
    assert c.post("/api/prompting/runs/event", headers=H, json={"ref": "cr_a", "event": "published"}).status_code == 422
    assert c.post("/api/prompting/runs/event", headers=H, json={"ref": "cr_a", "event": "downloaded"}).json() == {"ok": True}
    assert c.put("/api/prompting/ledger/prefs", headers=H, json={"share": False}).json() == {"share": False, "ledger": True}
    assert c.get("/api/prompting/ledger?everyone=1", headers=H).json()["everyone"] is True
    assert c.delete("/api/prompting/ledger", headers=H).status_code == 422
    assert c.delete("/api/prompting/ledger?confirm=DELETE", headers=H).json() == {"deleted": 1}


def test_engine_hooks_are_wired(lg):
    main = (REPO / "server" / "app" / "main.py").read_text()
    for needle in ('L.claim(tenant, "web", brief, str(v["id"]))', '_pled(tenant, sid, "deleted")',
                   '_pled(tenant, _pled_sid(tenant, ref), "published")', '_pled(tenant, _pled_sid(tenant, ref), "edited")',
                   'L.claim, tenant, "image"', 'L.claim(tenant, "script", body.brief', '_pled(tenant, item_id, "deleted")',
                   '_pled(tenant, item_id, "edited")', 'background.add_task(_pled_chat', '"thumb_" + body.value',
                   '_pled(tenant, "conv:" + conversation_id, "redo")'):
        assert needle in main, needle
    assert "_L.ready(j[\"id\"]" in (REPO / "server/app/create/jobs.py").read_text()
    assert "_L.ready(str(r.id)" in (REPO / "server/app/site/service.py").read_text()
    assert "/api/prompting/runs'" in (CON / "improve.js").read_text() and "conversationId: () => CONV" in (CON / "v2.js").read_text()
    assert "event: 'downloaded'" in (CON / "studio.js").read_text() and "#/results" in (CON / "prompting.js").read_text()


def test_script_route_and_chat_hooks_end_to_end(lg, monkeypatch):
    """The Script writer: her handed prompt is claimed, made, edited, deleted. Chat: sent, thumbed; incognito = nothing."""
    from app.create import service as cs

    async def fake_write(*a, **k):
        return "SCENE 1. A shop at dawn."
    monkeypatch.setattr(cs, "write", fake_write)
    c = client()
    text = "Write a 45 second reel script for my coaching class in Akola, friendly tone, end with admissions open"
    rid = c.post("/api/prompting/runs", headers=H, json={"text": text, "brief": brief("script", ("audience",))}).json()["run"]
    got = c.post("/api/create/write", headers=H, json={"kind": "script", "brief": text}).json()
    iid = got["item"]["id"]
    assert row(lg, rid)["status"] == "ready" and f" {iid} " in row(lg, rid)["refs"]
    assert c.put(f"/api/create/items/{iid}/text", headers=H, json={"text": "changed"}).json()["ok"] is True
    assert row(lg, rid)["edits"] == 1
    assert c.post("/api/prompting/runs/event", headers=H, json={"ref": iid, "event": "downloaded"}).json() == {"ok": True}
    assert row(lg, rid)["grade"] == "kept_after_edit"
    assert c.delete(f"/api/create/items/{iid}", headers=H).json() == {"ok": True}
    assert row(lg, rid)["grade"] == "dropped"

    from app import main as M
    from app.config import get_settings
    t = get_settings().tenant_id
    line = "Write a warm festival greeting message for my bakery customers with the Diwali timings and a thank you"
    rid2 = lg.hand(t, line, brief("script", ("audience",)))
    monkeypatch.setattr("app.fence.is_incognito", lambda cid: cid == "secret")
    M._pled_chat(t, "secret", line)
    assert row(lg, rid2)["status"] == "handed"                              # an incognito chat claims nothing
    M._pled_chat(t, "conv1", line)
    assert row(lg, rid2)["status"] == "ready" and " conv:conv1 " in row(lg, rid2)["refs"]
    M._pled(t, "conv:conv1", "thumb_up")
    assert row(lg, rid2)["grade"] == "kept" and row(lg, rid2)["thumb"] == "up"


def test_results_page_in_a_real_browser(arena_server, monkeypatch):  # noqa: F811
    """Results: the four numbers stay blank until enough runs, her recent prompts with their state, thumbs, switches."""
    import os
    base, browser, key = arena_server
    from app.config import get_settings
    from app.prompting import ledger as L
    t = get_settings().tenant_id
    L.forget(t)
    rid = L.hand(t, PROMPT, brief())
    L.claim(t, "image", PROMPT, "cj_b1")
    L.ready("cj_b1", ["cr_b1"], usd=0.04)
    ctx = browser.new_context(viewport={"width": 1360, "height": 900})
    ctx.add_init_script(f"localStorage.setItem('hoola.console.token', '{key}')")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(f"{e} @ {pg.url}"))
    shots = os.environ.get("HOOLA_SHOTS")
    snap = (lambda n: (pg.wait_for_timeout(350), pg.screenshot(path=f"{shots}/ledger_{n}.png", full_page=True))) if shots else (lambda n: None)
    pg.goto(base + "/console/prompting#/results")
    pg.wait_for_selector(".hp-four")
    assert pg.locator(".hp-four b.hp-na").count() == 4 and "Numbers appear after 5" in pg.inner_text(".hp-wrap")
    assert "waiting to see what you do with it" in pg.inner_text(".hp-wrap")
    assert "Rs 499" not in pg.inner_text(".hp-wrap") and "9812345678" not in pg.content()
    snap("1_empty")
    pg.click(f'[data-run="{rid}"][data-thumb="up"]')
    pg.wait_for_selector(f'[data-run="{rid}"][data-thumb="up"][aria-pressed="true"]')
    assert "Kept" in pg.inner_text(".hp-wrap")
    _many(L, t, 4, 1)
    pg.reload()
    pg.wait_for_selector(".hp-four")
    assert pg.locator(".hp-four b.hp-na").count() == 0 and "83%" in pg.inner_text(".hp-four")
    snap("2_numbers")
    pg.uncheck("#hpShare")
    pg.wait_for_timeout(400)
    assert L.prefs(t)["share"] is False
    pg.click('[data-who="1"]')
    pg.wait_for_selector('[data-who="1"][aria-pressed="true"]')
    assert "Your recent prompts" not in pg.inner_text(".hp-wrap")
    # nothing runs off the right edge
    assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    pg.set_viewport_size({"width": 390, "height": 800})
    pg.click('[data-who=""]')
    pg.wait_for_selector("#hpShare")
    assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    snap("3_phone")
    assert not errs, errs
    ctx.close()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.903.0"
    assert "0.903.0+902" in (REPO / "pubspec.yaml").read_text()
