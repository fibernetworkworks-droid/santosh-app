"""v0.268 DO HISSE - the update line gets the recipe Claude and ChatGPT actually use (owner: "GIVE ME STEP BY STEP
HOW THEY USE PERFECT SHORT ENGLISH UPDATE REPLY FOR ANY TASK. DEEP RESEARCH FIRST", then "GO").

No vendor documents the wording, so her own screenshot of Claude working and her own Hoola run were MEASURED:

    Claude  16-35 words/line, median 28 · 2 sentences · 2 hard facts · 3 of 4 end in a next action
    Hoola   16-28 words/line, median 20 · 2 sentences · 2 hard facts · 4 of 4 end in a next action

The shape was already right; the grammar and the ban list were not written down anywhere. Claude's line is always
the same TWO HALVES - the FACT is a full sentence whose subject is the THING ("The live site is on v0.256.0"),
and the NEXT STEP is a short tail ending in the doing word ("Creating the checkpoint branch"). v0.268 makes both
halves, the real-figure requirement and the never-list hard rules in all three places that steer a reply.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- the two halves
def test_the_narration_ask_spells_out_both_halves():
    from app.agent import goal as G
    n = G.NARRATE
    assert "THEEK DO HISSE" in n
    assert "KYA MILA" in n and "AB KYA" in n
    assert "subject CHEEZ ho, tum nahi" in n            # the thing is the subject, not "I"
    assert "Bina number wali line bekaar hai" in n      # a line with no real figure is filler
    assert "15-30 shabd" in n and "Teesra vaakya mat jodo" in n


def test_the_narration_ask_carries_the_never_list():
    from app.agent import goal as G
    n = G.NARRATE
    for ban in ("Bilkul!", "Perfect!", "lagta hai", "bullet, heading, emoji",
                "kaam_plan, TypeError, thread-level listing"):
        assert ban in n, ban
    assert "Maafi ya drama nahi" in n                   # bad news stays calm
    assert "kaam ab POORA ho gaya hai to yeh line mat likho" in n


def test_the_tool_fact_still_rides_in_and_nothing_is_invented():
    from app.agent import goal as G
    withf = G.narrate_line(["20 mails mile hain", "env~9831 sabse naya"])
    assert "20 mails mile hain" in withf and "naya mat banao" in withf
    assert G.narrate_line([]) == G.NARRATE and G.narrate_line(None) == G.NARRATE


# ---------------------------------------------------------------- the shared rulebook
def test_the_rulebook_carries_the_recipe_on_chat_only():
    from app.agent import replystyle as R
    c = R.CHAT
    assert "TWO HALVES" in c
    assert "subject is the THING, not you" in c
    assert "A line with no real figure in it is filler" in c
    assert "ends in the doing word" in c
    assert "Two sentences, 15-30 words, one idea" in c
    assert "with no apology" in c
    # the call keeps its own pacing (v0.230 news queue / murmurs); the quick lane runs no tools
    for other in (R.VOICE, R.QUICK):
        assert "TWO HALVES" not in other
    for t in (R.CHAT, R.QUICK, R.VOICE):
        assert "{" not in t and "}" not in t            # voice.PERSONA is .format()ed


def test_the_rulebook_bans_the_filler_and_the_machine_words():
    from app.agent import replystyle as R
    c = R.CHAT
    for ban in ('"Bilkul!"', '"Perfect!"', '"let me go ahead and"', '"aur kuch?"',
                "bullets, headings or emoji", "never a word from inside the machine"):
        assert ban in c, ban
    assert "a tool name, a Python" in c                 # the exact leak her run showed
    assert "say what it means for HER work in plain words" in c


# ---------------------------------------------------------------- the system prompt
def test_the_prompt_asks_for_the_opener_and_both_halves():
    p = (ROOT / "server/app/agent/prompts.py").read_text()
    assert "CHALTE CHALTE BOLO" in p
    assert "pehla kadam kya hai" in p                   # the opener names the first move too
    assert "DO HISSON mein" in p
    assert "bina asli figure wali line mat likho" in p
    assert "15-30 shabd" in p
    assert "machine ke\n  andar ki koi baat" in p or "machine ke andar ki koi baat" in p.replace("\n  ", " ")


# ---------------------------------------------------------------- nothing earlier is undone
def test_the_cadence_and_the_short_final_answer_still_stand():
    from app.agent import replystyle as R
    from app.config import get_settings
    st = get_settings()
    assert st.agent_narrate_every == 1 and st.agent_narrate_max == 6      # v0.258
    assert "Results of work, the short way" in R.CHAT                     # v0.240
    assert "never a bullet list of the steps you ran" in R.CHAT
    head = R.CHAT.split("How you understand her")[0]
    assert "Her language, first and always" in head                      # v0.260, still first


def test_v0260_fixes_are_untouched():
    from app.agent.goal_tools import GOAL_TOOLS
    spec = [t for t in GOAL_TOOLS if t["name"] == "kaam_plan"][0]
    assert "current, reason)" in spec["description"] and "current, note)" not in spec["description"]
    assert 'say = "Yeh raasta nahi chala — ek doosra tareeka try karta hoon…"' in \
        (ROOT / "server/app/agent/pakka.py").read_text()
    assert "def _answered_since" in (ROOT / "server/app/kaam_followup.py").read_text()


def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.271.0"
    assert "0.271.0+311" in (ROOT / "pubspec.yaml").read_text()
