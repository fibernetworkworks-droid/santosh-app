"""v0.224 KAAM KA SCORECARD: the same 24 Hinglish asks, measured the same way before and after a change.

The free pipeline card (no model, no keys) guards Phase 2's win; the reply card measures what she would really get
(first word, length, shape, honesty) and is proved here with a scripted brain; compare() turns two runs into
"behtar / bura" per number."""
import asyncio
import types

from app.quality import run as R
from app.quality import score as S
from app.quality.asks import ASKS, BY_ID, SET_V, check, turns_of
from tests.test_bazar import bz  # noqa: F401  (fresh DB)


# ---------------------------------------------------------------- the set itself

def test_the_set_is_sound_and_fixed():
    assert check() == [] and len(ASKS) == 24 and SET_V == 1
    kinds = {a["kind"] for a in ASKS}
    for need in ("greeting", "yesno", "fact", "figure", "advice", "plan", "multi", "work", "vague", "style",
                 "heavy", "money", "general", "explain"):
        assert need in kinds, need
    assert any(len(turns_of(a)) == 2 for a in ASKS)          # her style must hold over two turns
    assert any(S.script_of(" ".join(turns_of(a))) == "deva" for a in ASKS)   # her script is in the set


# ---------------------------------------------------------------- the scorer: the same reply always scores the same

def test_filler_and_closing_cost_points():
    good = S.score_one(BY_ID["greet"], "Theek hoon - aap bataiye, kaam kaisa chal raha hai?")
    assert good["points"] == 100 and good["flags"] == []
    bad = S.score_one(BY_ID["greet"], "Bilkul! Main theek hoon. Aur kuch?")
    assert "filler (Bilkul)" in bad["flags"] and "closing" in bad["flags"]
    assert bad["points"] == 100 - S.PENALTY["filler"] - S.PENALTY["closing"]
    # "Bilkul" as the ANSWER is not a filler
    assert S.filler_open("Bilkul ho sakta hai, Marathi mein likh dunga.") == ""


def test_answer_first_and_yes_no():
    a = BY_ID["yesno"]
    assert S.score_one(a, "Haan, Marathi mein likh dunga.")["flags"] == []
    back = S.score_one(a, "Aap jaanna chahte hain ki main Marathi mein letter likh sakta hoon?")
    assert "answer_first" in back["flags"]
    assert "answer_first" in S.score_one(a, "Marathi ek sundar bhasha hai aur bahut log bolte hain.")["flags"]


def test_length_band_and_padding_costs_more_than_short():
    a = BY_ID["greet"]
    long = S.score_one(a, " ".join(["shabd"] * 60))
    assert long["fit"] == "long" and "long (60 shabd)" in long["flags"]
    short = S.score_one(BY_ID["plan"], "Dukaan khol lijiye.")
    assert short["fit"] == "short"
    assert S.PENALTY["long"] > S.PENALTY["short"]


def test_her_script_and_lists_and_light_formatting():
    hi = BY_ID["greet_hi"]
    assert S.score_one(hi, "मैं ठीक हूँ, आप बताइए।")["flags"] == []
    assert any(f.startswith("script") for f in S.score_one(hi, "Main theek hoon, aap bataiye.")["flags"])
    listy = S.score_one(BY_ID["greet"], "Theek hoon.\n- ek\n- do\n- teen")
    assert any(f.startswith("list") for f in listy["flags"])
    assert "plain" in S.score_one(BY_ID["greet"], "## Haal\n**Theek** hoon.")["flags"]
    # a list is the right shape for a plan: no list penalty there
    plan = S.score_one(BY_ID["plan"], "Yeh steps hain.\n" + "\n".join(f"{i}. kaam {i}" for i in range(1, 9))
                       + "\n" + " ".join(["shabd"] * 60))
    assert not any(f.startswith("list") for f in plan["flags"])


def test_an_invented_figure_is_the_biggest_shape_penalty_but_her_own_numbers_are_free():
    a = BY_ID["figure"]
    ok = S.score_one(a, "Total Rs 450 hua - 3 bori x Rs 150.")
    assert ok["flags"] == [] and ok["points"] == 100          # 450 is declared derivable in the ask
    bad = S.score_one(a, "Total Rs 450 hua, aur delivery Rs 9,900 extra lagegi.")
    assert any(f.startswith("invent") and "9,900" in f for f in bad["flags"])
    assert S.PENALTY["invent"] > S.PENALTY["long"]


def test_a_claim_with_nothing_behind_it_is_the_worst():
    a = BY_ID["work_money"]
    assert any(f.startswith("claim") for f in S.score_one(a, "Rs 500 bhej diya Ramesh ko.")["flags"])
    card = S.score_one(a, "Rs 500 ka payment card bhej diya hai - aap haan kar dijiye.",
                       {"calls": [{"tool": "bazar_pay", "ok": True}]})
    assert not any(f.startswith("claim") for f in card["flags"])   # a real tool ran: that is not a fake claim
    assert S.PENALTY["claim"] == max(S.PENALTY.values())


def test_a_vague_ask_may_ask_one_question_not_three():
    a = BY_ID["vague"]
    assert S.score_one(a, "Pichhli report samajh ke bhej raha hoon - galat ho to bata dijiye.")["flags"] == []
    assert S.score_one(a, "Kaun si file? Kisko bhejun? Aaj hi?")["flags"]


def test_totals_count_every_flag():
    cards = [S.score_one(BY_ID["greet"], "Bilkul! Theek hoon."),
             S.score_one(BY_ID["greet"], "Theek hoon, aap bataiye."),
             S.score_one(BY_ID["yesno"], "Marathi bahut sundar bhasha hai.")]
    t = S.totals(cards)
    assert t["asks"] == 3 and t["clean"] == 1 and t["flags"]["filler"] == 1 and t["flags"]["answer_first"] == 1
    assert 0 < t["points"] < 100


# ---------------------------------------------------------------- the free card (what CI runs)

def test_the_free_card_needs_no_model_and_guards_the_slim_prompt():
    from app.agent import prompts
    card = R.pipeline_card()
    assert len(card["rows"]) == len(ASKS) and card["rules_present"] and card["rules_missing"] == []
    full = round(len(prompts.SYSTEM) / 1024, 1)
    assert card["full_guide_kb"] == full
    assert card["prompt_kb_median"] < full * 0.5, card["prompt_kb_median"]   # Phase 2's win, pinned
    assert card["prompt_kb_max"] <= full and 10 < card["tools_median"] < 200
    from app.agent.tools import TOOLS
    assert card["tools_all"] == len(TOOLS) and card["tools_median"] < card["tools_all"] * 0.5
    gst = [r for r in card["rows"] if r["id"] == "general"][0]
    assert gst["tools"] >= 1 and isinstance(gst["families"], list)


def test_the_free_card_notices_if_the_rulebook_ever_leaves_the_prompt(monkeypatch):
    from app.agent import prompts
    monkeypatch.setattr(prompts, "SYSTEM", prompts.SYSTEM.replace("Answer first", "Jawab pehle"))
    monkeypatch.setattr(prompts, "_GUIDE", None)        # the cut-up guide is cached: rebuild it
    card = R.pipeline_card()
    assert not card["rules_present"] and "Answer first" in card["rules_missing"]


# ---------------------------------------------------------------- the real card, with a scripted brain

class FakeBrain:
    def __init__(self, reply):
        self.reply = reply
        self.seen = []
        self.messages = self

    async def create(self, **kw):
        self.seen.append(kw)
        await asyncio.sleep(0.05)
        return types.SimpleNamespace(content=[{"type": "text", "text": self.reply}], stop_reason="end_turn")


def test_a_real_turn_is_measured_end_to_end(bz, monkeypatch):
    import app.agent.santosh as sa
    from app.chats import enabled as _ch
    monkeypatch.setattr("app.chats.enabled", lambda: False)      # no background titling call
    brain = FakeBrain("Haan, Marathi mein likh dunga.")
    monkeypatch.setattr(sa, "get_client", lambda: brain)
    card = asyncio.run(R._one_ask(BY_ID["yesno"], "default", judge=False))
    assert card["id"] == "yesno" and card["flags"] == [] and card["points"] == 100
    assert card["words"] == 5 and card["model_calls"] == 1
    assert card["prompt_kb"] and card["prompt_kb"] > 5 and card["tools"] and card["tools"] > 10
    assert isinstance(card["total_ms"], int) and card["total_ms"] >= 50
    assert card["ttfw_ms"] is None or card["ttfw_ms"] <= card["total_ms"]
    assert _ch is not None


def test_a_two_turn_ask_scores_only_the_last_reply(bz, monkeypatch):
    import app.agent.santosh as sa
    monkeypatch.setattr("app.chats.enabled", lambda: False)
    brain = FakeBrain("Portal par login karke GSTR-3B bhariye, phir challan bana lijiye.")
    monkeypatch.setattr(sa, "get_client", lambda: brain)
    card = asyncio.run(R._one_ask(BY_ID["style_short"], "default", judge=False))
    assert card["id"] == "style_short" and card["words"] == 10 and card["flags"] == []
    assert len(brain.seen) >= 2                                  # the set-up turn really ran first


def test_a_broken_ask_never_loses_the_run(bz, monkeypatch):
    import app.agent.santosh as sa
    monkeypatch.setattr("app.chats.enabled", lambda: False)

    async def boom(*a, **k):
        raise RuntimeError("brain down")

    monkeypatch.setattr(sa, "run_turn", boom)
    out = asyncio.run(R.reply_card([BY_ID["greet"], BY_ID["yesno"]], tenant="default"))
    assert out["asks"] == 0 and len(out["cards"]) == 2
    assert all(c["flags"] == ["error"] for c in out["cards"])


def test_the_judge_is_optional_and_averaged(bz, monkeypatch):
    import app.agent.santosh as sa
    from app.agent import pakka
    monkeypatch.setattr("app.chats.enabled", lambda: False)
    monkeypatch.setattr(sa, "get_client", lambda: FakeBrain("Haan, likh dunga."))

    async def fake_ask(system, text, settings):
        assert "You grade ONE reply" in system
        return '{"answered": 5, "useful": 4, "why": "seedha jawab"}'

    monkeypatch.setattr(pakka, "_ask", fake_ask)
    out = asyncio.run(R.reply_card([BY_ID["yesno"]], tenant="default", judge=True))
    assert out["judge_answered"] == 5.0 and out["judge_useful"] == 4.0
    assert out["cards"][0]["judge"]["why"] == "seedha jawab"


# ---------------------------------------------------------------- snapshots and the before / after line

def test_a_snapshot_is_saved_and_listed(tmp_path, monkeypatch):
    monkeypatch.setenv("QUALITY_DIR", str(tmp_path))
    snap = asyncio.run(R.snapshot(live=False, label="pehle"))
    assert snap["set"] == SET_V and snap["label"] == "pehle" and snap["pipeline"]["rules_present"]
    rows = R.snapshots()
    assert rows and rows[0]["label"] == "pehle" and rows[0]["live"] is False
    again = R.load(rows[0]["file"])
    assert again["at"] == snap["at"]
    said = R.lines(snap)
    assert any("Prompt:" in ln for ln in said) and any("Rulebook" in ln for ln in said)


def test_compare_says_behtar_or_bura_for_every_number():
    before = {"set": 1, "version": "0.1", "pipeline": {"prompt_kb_median": 128.0, "tools_median": 390},
              "replies": {"points": 70.0, "clean": 5, "words_median": 120, "ttfw_median_ms": 2400,
                          "flags": {"filler": 6, "invent": 2}}}
    after = {"set": 1, "version": "0.2", "pipeline": {"prompt_kb_median": 31.3, "tools_median": 48},
             "replies": {"points": 88.0, "clean": 17, "words_median": 60, "ttfw_median_ms": 1800,
                         "flags": {"filler": 0, "invent": 3}}}
    v = R.compare(before, after)
    by = {r["metric"]: r for r in v["rows"]}
    assert by["prompt_kb_median"]["verdict"] == "behtar" and by["ttfw_median_ms"]["verdict"] == "behtar"
    assert by["points"]["verdict"] == "behtar" and by["words_median"]["verdict"] == "bura"  # fewer words != better
    flags = {f["flag"]: f for f in v["flags"]}
    assert flags["filler"]["verdict"] == "behtar" and flags["invent"]["verdict"] == "bura"
    assert "invent" in v["worse"] and "Behtar:" in v["say"]


def test_compare_refuses_two_different_question_sets():
    v = R.compare({"set": 1, "pipeline": {}}, {"set": 2, "pipeline": {}})
    assert v["same_set"] is False and "set badal gaya" in v["say"]


def test_the_api_shows_the_card(bz, monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from app.main import app
    monkeypatch.setenv("QUALITY_DIR", str(tmp_path))
    c = TestClient(app)
    h = {"X-API-Key": "test-key"}
    assert c.get("/api/quality/asks", headers=h).json()["set"] == SET_V
    made = c.post("/api/quality/pipeline", headers=h)
    assert made.status_code == 200 and made.json()["snapshot"]["pipeline"]["rules_present"]
    over = c.get("/api/quality", headers=h).json()
    assert over["asks"] == 24 and over["snapshots"] and over["lines"]
    name = over["snapshots"][0]["file"]
    assert c.get(f"/api/quality/report/{name}", headers=h).json()["snapshot"]["set"] == SET_V
    assert c.get("/api/quality/report/nahi.json", headers=h).status_code == 404


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.237.0"
