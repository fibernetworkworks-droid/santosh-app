"""v0.315 from HER live test run of v0.314 ("TEST 3 :: FAIL (PLAN CARD NOT APPER) DIRECT RESULT, TEST 4 : PASS (BUT
CREATED SEVERAL PDF ... NEED WORK ON IT), TEST 6: PASS BUT WORK CONTINUE ON PC AND AFTER 10 MIN GET THE TASK FAIL").

1. PLAN CARD: a clearly big ask got PLAN_FIRST, the model skipped it and finished in 5 steps - the server plan only came
   at step 7. Now a big ask gets the server's plan right after the first tool round, its steps read off her words.
2. EK HI FILE: doc_studio put the card in chat BEFORE its QA; a warning made the model build file 2, then 3. Now QA runs
   first, a draft with problems is held for ONE fix, and only one file reaches her.
3. NO QUIET PC: a site that refuses Hoola's server (Amazon / Flipkart) was moved to HER PC by computer_operator
   where=auto. Now she is asked first (v0.271's rule: a PC only on her word).
"""
import asyncio

from tests.test_bazar import bz  # noqa: F401
from tests.test_v0186_long_goal import FakeBrain, _set_brain, gz, tu, txt  # noqa: F401

T3 = ("Meri bakery ke liye ek poora marketing plan banao: competitors ka research karo, 5 social media post ke ideas "
      "likho, ek mahine ka posting calendar banao, aur sab ko ek PDF mein do.")


# ---------------------------------------------------------------- 1. the plan card for a big ask
def test_her_steps_are_read_off_her_words():
    from app.agent.santosh import _ask_steps
    goal, steps = _ask_steps(T3)
    assert goal == "Meri bakery ke liye ek poora marketing plan banao"
    assert steps == ["competitors ka research karo", "5 social media post ke ideas likho",
                     "ek mahine ka posting calendar banao", "sab ko ek PDF mein do"]
    _, s1 = _ask_steps("Teen kaam ek ek karke karo: pehle aaj Mumbai ka weather dekho, phir Bandra mein 3 achhe "
                       "South Indian restaurant dhoondo, aur aakhir mein dono ka ek chhota summary do.")
    assert len(s1) == 3 and s1[1].startswith("Bandra")
    _, s2 = _ask_steps("India mein electric scooters par deep research karo — top 8 brands, unki price, range. "
                       "Alag sources se check karo, phir ek proper PDF report bana do.")
    assert len(s2) == 3 and "unki price, range" in s2[0]            # a list inside a step stays one step
    assert _ask_steps("saare kaam dekho") == ("saare kaam dekho", ["saare kaam dekho"])


def test_a_big_ask_gets_its_card_after_the_first_round(gz, monkeypatch):  # noqa: F811
    conv = gz["conv"]
    brain = _set_brain(monkeypatch, FakeBrain([
        ([tu(1, "google_search", query="bakery competitors")], "tool_use"),       # skips "kaam_plan set" first
        ([tu(2, "google_search", query="post ideas")], "tool_use"),
        ([tu(3, "kaam_status", q="calendar")], "tool_use"),
        ([txt("Plan taiyaar hai, PDF chat mein hai.")], "end_turn"),
    ]))
    import app.agent.santosh as S

    async def tool(name, args, ctx, settings, route=None):
        return {"results": ["ok"]}
    monkeypatch.setattr(S, "_run_tool", tool)
    from app.agent import goal
    seen_cards = []
    real_set = goal.set_goal

    def spy(*a, **k):
        v = real_set(*a, **k)
        seen_cards.append(v)
        return v
    monkeypatch.setattr(goal, "set_goal", spy)
    out = asyncio.run(S.run_turn(conv, T3, tenant_id="default"))
    assert seen_cards and seen_cards[0]["total"] == 4                       # the card, with her 4 parts
    first = next(i for i, c in enumerate(brain.seen) if "server ne yeh plan bana diya" in str(c["messages"][-1]))
    assert first == 1                                                        # right after the FIRST round
    assert "PDF chat mein hai" in out and goal.active_for(conv) is None      # closed by the real final answer


# ---------------------------------------------------------------- 2. one file, not three
def _doc(monkeypatch, statuses):
    from app.agent import docstudio_tools as D
    published = []
    monkeypatch.setattr(D, "_deliver", lambda ctx, name, data, src: published.append(name) or {"file_id": f"f{len(published)}"})
    seq = list(statuses)
    monkeypatch.setattr(D.preview, "preview", lambda kind, data, res: {"qa": {"status": seq.pop(0) if seq else "ok",
                                                                              "issues": ["table cut on page 2"]}})
    monkeypatch.setattr(D, "make_pdf", lambda *a, **k: {"data": b"%PDF-1.4 x", "design": None})
    return D, published


def _ctx(conv="c1"):
    from app.agent.tools import Ctx
    return Ctx(tenant_id="default", conversation_id=conv)


def test_a_draft_with_problems_is_held_for_one_fix(monkeypatch):
    D, published = _doc(monkeypatch, ["warn", "warn"])
    ctx = _ctx("c-hold")
    r1 = asyncio.run(D.doc_studio(ctx, kind="pdf", title="Repos", text="# x"))
    assert r1["status"] == "held_for_fix" and published == []              # nothing in her chat yet
    assert "NOT sent to her" in r1["note"] and "table cut" in r1["note"]
    r2 = asyncio.run(D.doc_studio(ctx, kind="pdf", title="Repos", text="# fixed"))
    assert published == ["Repos.pdf"] and "FINAL file" in r2["note"]       # ONE file, even if it still warns
    assert D.flush_held("c-hold") is False                                   # nothing left behind


def test_a_held_draft_is_never_lost(monkeypatch):
    D, published = _doc(monkeypatch, ["warn"])
    asyncio.run(D.doc_studio(_ctx("c-lost"), kind="pdf", title="Report", text="# x"))
    assert published == []
    assert D.flush_held("c-lost") is True and published == ["Report.pdf"]  # the turn's end delivers it


def test_send_held_sends_the_draft_as_it_is(monkeypatch):
    D, published = _doc(monkeypatch, ["warn"])
    ctx = _ctx("c-send")
    asyncio.run(D.doc_studio(ctx, kind="pdf", title="Report", text="# x"))
    r = asyncio.run(D.doc_studio(ctx, kind="pdf", title="Report", send_held=True))
    assert published == ["Report.pdf"] and "FINAL" in r["note"]


def test_a_clean_draft_goes_straight_to_her(monkeypatch):
    D, published = _doc(monkeypatch, ["ok"])
    r = asyncio.run(D.doc_studio(_ctx("c-ok"), kind="pdf", title="Quote", text="# x"))
    assert published == ["Quote.pdf"] and "do not make another version" in r["note"]


# ---------------------------------------------------------------- 3. a refused site asks before any PC
def test_a_refused_site_asks_before_her_pc(monkeypatch):
    from app.agent import operator_tools as O
    from app.operator import reach
    monkeypatch.setattr(reach, "check", lambda task, url, live=True: {"ok": False, "site": "amazon.in", "why": "403"})
    called = []

    async def no_pc(*a, **k):
        called.append(a)
        return {}
    monkeypatch.setattr(O, "_to_pc", no_pc)
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "operator_preflight", True, raising=False)
    r = asyncio.run(O.computer_operator(_ctx("c-site"), "start", task="iPhone price on amazon.in", where="auto"))
    assert called == [] and r["status"] == "site_blocks_server"
    assert "Aapke PC par Chrome mein kar doon?" in r["say"] and "Never move it to her PC" in r["next"]


def test_her_own_pc_word_still_goes_to_her_pc(monkeypatch):
    from app.agent import operator_tools as O
    from app.operator import reach
    monkeypatch.setattr(reach, "check", lambda task, url, live=True: {"ok": False, "site": "amazon.in", "why": "403"})
    went = []

    async def to_pc(ctx, a, chk):
        went.append(chk)
        return {"place": "pc"}
    monkeypatch.setattr(O, "_to_pc", to_pc)
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "operator_preflight", True, raising=False)
    ctx = _ctx("c-mine")
    ctx.place = "pc"
    asyncio.run(O.computer_operator(ctx, "start", task="iPhone price on amazon.in", where="auto"))
    assert went                                                               # she said PC: it may go there


def test_browse_web_no_longer_suggests_a_quiet_move():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "app/agent/web_tools.py").read_text()
    assert "it moves the \"\n                             \"job to her PC" not in src
    assert "Never move it to her PC or the cloud PC by" in src


# ---------------------------------------------------------------- v0.330 her test A: the card was made but never DRAWN
def test_the_console_draws_the_plan_card():
    """The server made the plan; the console's progress policy folded every 'goal' event into the progress line, so
    no card ever showed on the console. The plan is her todo list: it is a card (one per job, updated in place)."""
    from pathlib import Path
    js = (Path(__file__).resolve().parents[1] / "app/static/console/workspace.js").read_text()
    quiet = js.split("quiet(kind,p={}) {", 1)[1].split("},", 1)[0]
    folded = quiet.split("return [", 1)[1].split("]", 1)[0]                  # the list itself, not the comments
    assert "'goal'" not in folded and "'step'" in folded                    # steps still fold, the plan does not
    v2 = (Path(__file__).resolve().parents[1] / "app/static/console/v2.js").read_text()
    assert "if (kind === 'goal') {" in v2 and "const key = kind + ':' + (p.id" in v2   # one card per goal id


def test_her_test_a_asks_are_big_with_clean_steps():
    from app.agent import goal
    from app.agent.santosh import _ask_steps
    a = ("Mere kapdon ke naye online store ke liye launch ki taiyari karo: pehle 3 competitor stores ki pricing check "
         "karo, phir 10 product descriptions likho, uske baad launch week ka Instagram posting schedule banao, aur "
         "aakhir mein sab ek Word file mein do.")
    b = ("Ek chhota business plan banao chai cafe ke liye: location ke options socho, starting kharcha ka hisaab lagao, "
         "menu aur rates likho, phir sab ek PDF mein do.")
    for t in (a, b):
        assert goal.looks_big(t)
        assert len(_ask_steps(t)[1]) == 4
    assert _ask_steps(a)[1][2] == "launch week ka Instagram posting schedule banao"     # 'uske baad' stripped
    for t in ("Kal Mumbai mein baarish hogi kya?", "Time: kitna baj gaya?", "Note: kal meeting hai"):
        assert not goal.looks_big(t)
