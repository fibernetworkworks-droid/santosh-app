"""v0.400 FAST + NEVER LOST + VISITOR TESTS (web Step 1 of docs/WEB_PLATFORM_PLAN.md, owner: "START STEP 1").

FAST: the browser checks spread a big site's pages over parallel browsers (same checks, same results), the critique
looks at every page at once, redraws every weak section at once and re-checks ONLY the changed pages (it was a full
site check after every page), fix rounds repair every failing section at once, and the preview is rebuilt at most
every 20 s while sections arrive (it was rebuilt after every section).
NEVER LOST: a code-mode ask cut short by a restart says so instead of 'working' forever, a half-done translation starts
again by itself, and a 100-page proof is picked up again after a restart (twice at most) with its time and cost kept.
VISITOR TESTS: Chromium walks the built copy like a customer on a phone - menu, enquiry form, add to cart -> checkout
-> order, blog post, language switch - against stand-in answers (never her real data); a broken checkout blocks going
live."""
import json
import os
import time

import pytest

from tests.test_life import conv_ctx
from tests.test_v121_site import T, site_env  # noqa: F401  (fixture)
from tests.test_v0351_dukaan import _built_shop


def _site(S, pages=("contact",)):
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210", "address": "Main Road, Akot"})
    S.approve_plan(T, v["id"], pages=list(pages))
    S.choose_look(T, v["id"], 0)
    return v["id"]


# ---------------------------------------------------------------- FAST
def test_parallel_checks_give_the_same_report(site_env, monkeypatch):
    from app.site import checks as C
    from app.site import service as S
    sid = _site(S, ["about", "services", "contact"])
    r = S._load(sid)
    live = S._assemble_live(r)
    plan = json.loads(r.plan)
    assert C._width(3) == 1 and C._width(40) == 3                     # small sites keep one browser
    one = C.run(live, plan, None, video=False)
    monkeypatch.setattr(C, "_width", lambda n: 2)
    two = C.run(live, plan, None, video=False)
    assert list(two["pages"]) == list(one["pages"])                  # the plan's order, whatever finished first
    assert sorted(x["text"] for x in two["blocking"]) == sorted(x["text"] for x in one["blocking"])
    only = C.run(live, plan, None, video=False, only=["contact"])
    assert list(only["pages"]) == ["contact"]


def test_critique_looks_at_once_and_rechecks_only_changed_pages(site_env, monkeypatch, tmp_path):
    from app.site import checks as C
    from app.site import quality as Q
    from app.site import service as S
    sid = _site(S, ["about", "contact"])
    r = S._load(sid)
    plan = json.loads(r.plan)
    shots = tmp_path / "shots"
    shots.mkdir()
    pages = [p for p in plan["pages"] if p["slug"] in ("home", "about", "contact") and p.get("sections")]
    rep = {"pages": {}, "blocking": []}
    for p in pages:
        for vw in ("390", "1440"):
            (shots / f"{p['slug']}-{vw}.jpg").write_bytes(b"\xff\xd8" + p["slug"].encode())
        rep["pages"][p["slug"]] = {"shots": {"390": f"{p['slug']}-390.jpg", "1440": f"{p['slug']}-1440.jpg"}, "issues": []}
    weak = {p["slug"]: p["sections"][-1]["type"] for p in pages[:2]}            # two pages have one weak section each
    looks = []

    def fake_crit(images, dna, types, words):
        slug = next(p["slug"] for p in pages if [x["type"] for x in p["sections"]] == types)
        looks.append(slug)
        first = looks.count(slug) == 1
        secs = {t: {"score": 8.0, "notes": ""} for t in types}
        if slug in weak:
            secs[weak[slug]] = {"score": 5.0 if first else (8.5 if slug == pages[0]["slug"] else 3.0), "notes": "more air"}
        return {"overall": 7, "sections": secs}
    runs = []

    def fake_run(*a, **k):
        runs.append(k.get("only"))
        return rep
    monkeypatch.setattr(Q, "critique", fake_crit)
    monkeypatch.setattr(Q, "critique_on", lambda: True)
    monkeypatch.setattr(S, "write_section", lambda r, slug, s, others, extra="", system="": (
        {"html": f"<section>NEW {slug}</section>", "css": "", "js": ""}))
    monkeypatch.setattr(S, "_assemble_live", lambda r: tmp_path)
    monkeypatch.setattr(C, "run", fake_run)
    out, crit = S._critique_round(r, plan, shots, rep)
    assert runs == [sorted(weak), None]                         # ONE check of the changed pages, ONE full check at the end
    assert sorted(looks) == sorted([p["slug"] for p in pages] + list(weak))
    a, b = pages[0]["slug"], pages[1]["slug"]
    assert crit["pages"][a]["redrawn"][weak[a]]["kept"] == "new" and crit["pages"][b]["redrawn"][weak[b]]["kept"] == "old"
    assert "NEW" in json.loads(S._sec_path(r, S.sec_key(a, weak[a])).read_text())["html"]
    assert "NEW" not in json.loads(S._sec_path(r, S.sec_key(b, weak[b])).read_text())["html"]


def test_the_preview_is_not_rebuilt_after_every_section(site_env, monkeypatch):
    from app.site import service as S
    calls = []
    real = S._assemble_live
    monkeypatch.setattr(S, "_assemble_live", lambda r: calls.append(1) or real(r))
    monkeypatch.setattr(S, "ASSEMBLE_EVERY_S", 3600)
    sid = _site(S, ["about", "services", "contact"])
    n_secs = len(S._sections(S._load(sid)))
    assert n_secs >= 8 and len(calls) < n_secs                       # was: one rebuild per section (and more)
    assert S.get(T, sid)["status"] == "ready"


# ---------------------------------------------------------------- VISITOR TESTS
def test_visitor_journeys_on_a_real_shop_site(site_env, monkeypatch):
    monkeypatch.setenv("SITE_JOURNEYS", "true")
    from app.config import get_settings
    get_settings.cache_clear()
    from app.site import build as B
    from app.site import journeys as J
    from app.site import service as S
    sid = _built_shop(S)                                              # the build ran the journeys on its version
    g = S.get(T, sid)
    j = {x["name"]: x for x in g["checks"]["journeys"]}
    assert j["menu"]["ok"] and j["shop"]["ok"], j
    assert all(x["ok"] for x in j.values()), j
    # break the checkout on the built copy: the shop journey fails and BLOCKS
    live = B.site_dir(T, sid) / "live"
    js = live / "assets" / "hoola-shop.js"
    js.write_text(js.read_text().replace("req('POST', '/order', body)", "Promise.reject(new Error('Server se jawab nahi'))"))
    res = J.run(live, S._ctx(S._load(sid)))
    shop = next(x for x in res["journeys"] if x["name"] == "shop")
    assert not shop["ok"] and "checkout did not finish" in shop["detail"]
    assert any("Visitor test failed" in x["text"] for x in res["blocking"])
    get_settings.cache_clear()


# ---------------------------------------------------------------- NEVER LOST
def test_cut_short_jobs_are_recovered(site_env, monkeypatch):
    from app.site import build as B
    from app.site import code as CD
    from app.site import service as S
    sid = _site(S)
    r = S._load(sid)
    folder = S._code_dir(r)
    CD.save_task(folder, "abcdef12", {"status": "working", "instruction": "x"})
    old = time.time() - 3600
    os.utime(folder / "abcdef12.json", (old, old))
    monkeypatch.setattr(S, "_BOOT", time.time())
    started = []
    monkeypatch.setattr(S, "_start", lambda site_id, job, **kw: started.append((site_id, job)) or True)
    with S.session() as s:                                          # a second language whose translation never ran
        row = s.get(S.Site, sid)
        row.languages = json.dumps(["hinglish", "hi"])
    S._recover_side_jobs(time.time())
    assert S.code_task(T, sid, "abcdef12")["status"] == "failed"
    assert (sid, "translate") in started
    started.clear()
    S._recover_side_jobs(time.time())
    assert started == []                                            # once per boot
    assert B.site_dir(T, sid).exists()


def test_a_proof_is_picked_up_after_a_restart(site_env, monkeypatch):
    from app.db import session
    from app.site import proof as PR
    PR.ensure_tables()
    with session() as s:
        a = PR.ArenaProof(kind="hoola", brief_id="big-mithai", status="running", site_id="site_x",
                          card=json.dumps({"budget_inr": 900, "t0": 1.0, "inr0": 0.0}))
        b = PR.ArenaProof(kind="rival", brief_id="big-mithai", status="running", url="https://x.example")
        s.add_all([a, b])
        s.flush()
        aid, bid = a.id, b.id
    called = []
    monkeypatch.setattr(PR, "_go", lambda pid, brief, budget, builder: called.append((pid, brief["id"], budget)))
    assert PR.resume_interrupted() == 1
    for th in list(PR._RUNNING.values()):
        th.join(5)
    assert called == [(aid, "big-mithai", 900.0)]
    assert PR.get(bid)["status"] == "failed" and "dobara" in PR.get(bid)["card"]["error"]
    assert PR.get(aid)["card"]["resumes"] == 1 and PR.get(aid)["card"]["t0"] == 1.0          # time + cost kept
    PR._RUNNING.clear()
    PR.resume_interrupted()
    PR._RUNNING.clear()
    PR.resume_interrupted()                                         # a third death: failed, not looping forever
    assert PR.get(aid)["status"] == "failed"


def test_console_shows_the_visitor_tests():
    from pathlib import Path
    js = (Path(__file__).resolve().parents[1] / "app" / "static" / "console" / "build.js").read_text()
    assert "Visitor tests (Hoola used the site like a customer on a phone)" in js and "Add to cart → checkout → order" in js


def test_version():
    from pathlib import Path
    from app.main import APP_VERSION
    assert APP_VERSION == "0.664.0"
    assert "0.664.0+670" in (Path(__file__).resolve().parents[2] / "pubspec.yaml").read_text()
