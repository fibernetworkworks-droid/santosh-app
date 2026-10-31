"""v0.225 Website Sahayak phase 3, builder quality: website calls ride the App Sahayak Opus path (adaptive thinking,
effort per job, no quiet fallback), every look gets an art-direction DNA kept different from its siblings and carried
into every section prompt, the owner sees a rupee andaaza before the build, sections are written several at a time,
and Opus looks at the real home page screenshots and redraws weak sections once (a worse redraw is thrown away)."""
import json
import threading
import time

import pytest

from tests.test_life import conv_ctx
from tests.test_v121_site import site_env  # noqa: F401  (fixture)

T = "default"


class _Msg:
    def __init__(self, text):
        self.content = [type("B", (), {"type": "text", "text": text})()]


class _Client:
    def __init__(self, text="{}"):
        self.calls = []
        self.text = text
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        return _Msg(self.text)


# ---------------------------------------------------------------- 1. the Opus path
def test_site_kinds_ride_the_opus_path(env, monkeypatch):
    from app.config import get_settings
    from app.site import ai as AI
    get_settings.cache_clear()
    cl = _Client('{"ok": 1}')
    monkeypatch.setattr(AI, "_APP_CLIENT", cl)
    assert AI.ask_json("SYS", "p", 2000, "site_art") == {"ok": 1}
    kw = cl.calls[-1]
    assert kw["model"] == "claude-opus-5-5" and kw["thinking"] == {"type": "adaptive"}
    assert kw["output_config"] == {"effort": "xhigh"} and kw["max_tokens"] <= 20000
    AI.ask("SYS", "p", 9000, "build")
    assert cl.calls[-1]["output_config"] == {"effort": "high"}
    AI.ask("SYS", "p", 1500, "site_edit")
    assert cl.calls[-1]["output_config"] == {"effort": "medium"}
    # Opus failing for good = a plain error, never a quiet other model
    class Boom:
        messages = None

        def __init__(self):
            self.messages = self

        def create(self, **kw):
            e = Exception("not found")
            e.status_code = 404
            raise e
    monkeypatch.setattr(AI, "_APP_CLIENT", Boom())
    with pytest.raises(AI.AiError):
        AI.ask("SYS", "p", 9000, "build")
    # switched off = the v0.121 path
    monkeypatch.setenv("SITE_OPUS", "false")
    get_settings.cache_clear()
    assert not AI._opus_kind("build") and AI._opus_kind("app")
    get_settings.cache_clear()


# ---------------------------------------------------------------- 2. art direction
def test_dna_is_cleaned_carried_and_kept_different(env, monkeypatch):
    from app.config import get_settings
    from app.site import ai as AI
    from app.site import quality as Q
    d = Q.clean_dna({"concept": "Mithai ki chaabi", "layout": {"system": "bento", "hero": "nonsense"},
                     "signature": "a gold arch frame", "motion": {"entrance": "split"},
                     "sections": {"hero": "big arch", "evil": "x"}}, "editorial_calm", ["hero", "products"])
    assert d["layout"]["system"] == "bento" and d["layout"]["hero"] == "big_type" and d["sections"] == {"hero": "big arch"}
    blk = Q.dna_block(d, "hero")
    assert "DESIGN DNA" in blk and "gold arch frame" in blk and "big arch" in blk and 'data-m="split"' in blk
    assert Q.clean_dna("garbage", "editorial_calm", ["hero"])["ai"] is False and Q.dna_block(None) == ""
    # off by default in tests (conftest) -> no Opus call at all
    assert Q.make_dna("b", "editorial_calm", {}, "{}", "", []) is None
    monkeypatch.setenv("SITE_ART", "true")
    get_settings.cache_clear()
    same = {"concept": "A", "layout": {"system": "bento", "hero": "big_type", "rhythm": "steady"},
            "signature": "gold arch frame", "motion": {"entrance": "reveal"}}
    other = {"concept": "B", "layout": {"system": "magazine", "hero": "split_media", "rhythm": "crescendo"},
             "signature": "torn paper edge", "motion": {"entrance": "draw"}}
    answers = [same, other]
    prompts = []

    def fake_ask(system, prompt, max_tokens=6000, kind="build", images=None, effort=""):
        assert kind == "site_art"
        prompts.append(prompt)
        return json.dumps(answers.pop(0))
    monkeypatch.setattr(AI, "ask", fake_ask)
    sib = Q.clean_dna(same, "editorial_calm", ["hero"])
    got = Q.make_dna("BRIEF", "editorial_calm", {"pages": [{"sections": [{"type": "hero"}]}]}, "{}", "her words", [sib])
    assert got["concept"] == "B" and len(prompts) == 2 and "TOO CLOSE" in prompts[1] and "clearly DIFFERENT" in prompts[0]
    get_settings.cache_clear()


def test_estimate_before_the_build(env):
    from app.site import quality as Q
    plan = {"pages": [{"sections": [{"type": "hero"}, {"type": "about"}]}, {"sections": [{"type": "contact"}]}]}
    e = Q.estimate(plan)
    assert e["sections"] == 3 and e["to_write"] == 3 and 0 < e["inr_low"] <= e["inr"] <= e["inr_high"]
    assert "₹" in e["say"] and "Opus" in e["say"]
    assert Q.estimate(plan, have=3, looks=0)["inr"] < e["inr"]


def test_planned_site_shows_the_andaaza(site_env):
    from app.site import service as S
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210"})
    g = S.get(T, v["id"])
    assert g["estimate"] and g["estimate"]["inr"] > 0
    assert "Andaaza" in S._say(g)


# ---------------------------------------------------------------- 3. sections several at a time
def test_sections_are_written_in_parallel_and_stop_still_works(site_env, monkeypatch):
    from app.site import service as S
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210"})
    r = S._load(v["id"])
    plan = json.loads(r.plan)
    keys = [S.sec_key(p["slug"], s["type"]) for p in plan["pages"] for s in p["sections"]]
    assert len(keys) >= 4
    live = {"now": 0, "max": 0}
    lock = threading.Lock()

    def slow(r, slug, s, others, extra="", system=""):
        with lock:
            live["now"] += 1
            live["max"] = max(live["max"], live["now"])
        time.sleep(0.15)
        with lock:
            live["now"] -= 1
        return {"html": f'<section id="{S.sec_id(slug, s["type"])}"><h2>x</h2></section>', "css": "", "js": ""}
    monkeypatch.setattr(S, "write_section", slow)
    monkeypatch.setattr(S, "_assemble_live", lambda r: None)
    monkeypatch.setenv("SITE_PARALLEL", "3")
    from app.config import get_settings
    get_settings.cache_clear()
    states = {k: "todo" for k in keys}
    t0 = time.time()
    assert S._write_sections(r, plan, states, {}) is True
    assert live["max"] >= 2 and all(v == "done" for v in states.values())
    assert time.time() - t0 < 0.15 * len(keys)          # faster than one after another
    # Rokiye before the next ones start -> stopped, nothing half-written
    states = {k: "todo" for k in keys}
    S._save(v["id"], stop=True)
    assert S._write_sections(S._load(v["id"]), plan, states, {}) is False
    assert S._load(v["id"]).status == "stopped"
    get_settings.cache_clear()


def test_one_bad_section_fails_the_build_plainly(site_env, monkeypatch):
    from app.site import service as S
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210"})
    r = S._load(v["id"])
    plan = json.loads(r.plan)

    def bad(r, slug, s, others, extra="", system=""):
        raise S.SiteError(f"{s['type']} section nahi ban paya")
    monkeypatch.setattr(S, "write_section", bad)
    states = {S.sec_key(p["slug"], s["type"]): "todo" for p in plan["pages"] for s in p["sections"]}
    with pytest.raises(S.SiteError):
        S._write_sections(r, plan, states, {})
    assert "building" not in states.values()


def test_section_files_are_written_in_one_step(site_env):
    from app.site import service as S
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210"})
    r = S._load(v["id"])
    k = S.sec_key("home", "hero")
    S._put_sec(r, k, {"html": "<section>A</section>"})
    S._put_sec(r, k, {"html": "<section>B</section>"})
    d = S._sec_path(r, k).parent
    assert json.loads(S._sec_path(r, k).read_text())["html"] == "<section>B</section>"
    assert not list(d.glob("*.tmp"))                    # a reader never meets a half-written file


# ---------------------------------------------------------------- 4. Opus looks at its own work
def _crit_setup(site_env, monkeypatch, tmp_path, after_score):
    from app.site import checks as C
    from app.site import quality as Q
    from app.site import service as S
    v = S.new(T, "mithai dukaan ki website", conv_ctx().conversation_id, name="Sharma Sweets",
              answers={"phone": "9876543210"})
    r = S._load(v["id"])
    plan = json.loads(r.plan)
    home = next(p for p in plan["pages"] if p["slug"] == "home")
    typ = home["sections"][1]["type"]
    k = S.sec_key("home", typ)
    S._sec_path(r, k).parent.mkdir(parents=True, exist_ok=True)
    S._sec_path(r, k).write_text(json.dumps({"html": "<section>OLD</section>", "css": "", "js": ""}))
    shots = tmp_path / "shots"
    shots.mkdir()
    (shots / "home-390.jpg").write_bytes(b"\xff\xd8 phone")
    (shots / "home-1440.jpg").write_bytes(b"\xff\xd8 desk")
    rep = {"pages": {"home": {"shots": {"390": "home-390.jpg", "1440": "home-1440.jpg"}}}, "blocking": []}
    seen = []

    def fake_crit(images, dna, types, words):
        seen.append(len(images))
        score = 5.0 if len(seen) == 1 else after_score
        return {"overall": 6, "sections": {typ: {"score": score, "notes": "bigger headline, real spacing"}}}
    monkeypatch.setattr(Q, "critique", fake_crit)
    monkeypatch.setattr(Q, "critique_on", lambda: True)
    monkeypatch.setattr(S, "write_section", lambda r, slug, s, others, extra="", system="": (
        {"html": "<section>NEW</section>", "css": "", "js": "", "extra": extra}))
    monkeypatch.setattr(S, "_assemble_live", lambda r: tmp_path)
    monkeypatch.setattr(C, "run", lambda *a, **k: rep)
    return S, r, plan, shots, rep, k, typ, seen


def test_critique_redraws_a_weak_section_and_keeps_the_better(site_env, monkeypatch, tmp_path):
    S, r, plan, shots, rep, k, typ, seen = _crit_setup(site_env, monkeypatch, tmp_path, after_score=8.5)
    out, crit = S._critique_round(r, plan, shots, rep)
    assert seen == [2, 2]
    sec = json.loads(S._sec_path(r, k).read_text())
    assert "NEW" in sec["html"] and "real spacing" in sec["critique"]
    assert crit["redrawn"][typ] == {"before": 5.0, "after": 8.5, "kept": "new"}


def test_critique_throws_away_a_worse_redraw(site_env, monkeypatch, tmp_path):
    S, r, plan, shots, rep, k, typ, seen = _crit_setup(site_env, monkeypatch, tmp_path, after_score=4.0)
    out, crit = S._critique_round(r, plan, shots, rep)
    assert "OLD" in json.loads(S._sec_path(r, k).read_text())["html"]
    assert crit["redrawn"][typ]["kept"] == "old"


def test_critique_off_and_weak_rules(env, monkeypatch):
    from app.config import get_settings
    from app.site import quality as Q
    get_settings.cache_clear()
    assert Q.critique_on() is False                     # conftest: SITE_CRITIQUE=off
    assert Q.critique([b"x"], None, ["hero"], "") is None
    w = Q.weak({"sections": {"hero": {"score": 3, "notes": "a"}, "about": {"score": 5, "notes": "b"},
                             "contact": {"score": 9, "notes": "c"}}})
    assert [t for t, _ in w] == ["about", "hero"]         # worst first, the chosen look's hero last
    c = Q.clean_critique({"overall": "7", "sections": {"about": {"score": 99}, "evil": {"score": 1}}}, ["about"])
    assert c == {"overall": 7.0, "sections": {"about": {"score": 10.0, "notes": ""}}}


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.333.0"
