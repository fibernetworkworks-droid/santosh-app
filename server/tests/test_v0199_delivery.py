"""v0.199.0 VOICE DELIVERY (Phase A of the natural-voice plan, "script for the ear"): the persona now teaches the
voice instrument itself - pauses as punctuation, one idea per breath, energy matched within his own band, real
laughter allowed, softer/lower on heavy news, the newsreader tone banned - and every canned line that reaches her
ears carries delivery: the wake turn and the one-shot brief say "write it like speech", the kaamwatch voice note
rides with an energy-matching instruction, the ack clips get per-flavour energy, and the followup's chat line is
spoken-shaped (symbols out, the flat colon becomes a comma) before it enters a live call."""
import re

from app import kaam_followup, voice
from app.kaam_followup import _ONE_SHOT_SYSTEM, KaamFollowup, _canned, _spoken, _wake_text


def _row(state="stopped", detail=None, link=None):
    return KaamFollowup(label="Reel", title="Mera reel", state=state, detail=detail, link=link)


# ---------------- persona: the delivery block ----------------

def test_persona_has_delivery_block():
    assert "How it sounds (delivery)" in voice.PERSONA
    before, after = voice.PERSONA.split("How it sounds (delivery)", 1)
    assert before.rstrip().endswith("never repeat them word for word.")   # sits right after "How you talk"
    assert "When to speak" in after.split("About the user")[0]            # and before "When to speak"


def test_delivery_block_teaches_the_instrument():
    block = voice.PERSONA.split("How it sounds (delivery)", 1)[1].split("When to speak", 1)[0]
    assert "newsreader" in block and "robot rhythm" in block              # the flat tone is banned by name
    assert "Pauses are punctuation" in block and "thinking pause" in block
    assert "One idea per breath" in block
    assert "energy" in block and "never an imitation" in block            # match her, stay himself
    assert "laugh, short and real" in block                               # real laughter is allowed and wanted
    assert "softer and lower" in block and "no forced cheer" in block     # heavy news has its own rules
    assert "own it in one plain line" in block                            # mistakes: plain ownership
    assert "{" not in block and "}" not in block                          # the format() contract


def test_persona_prompt_carries_delivery(env):
    m = voice.persona_prompt("Santosh", "m")
    f = voice.persona_prompt("Santosh", "f")
    for p in (m, f):
        assert "How it sounds (delivery)" in p and "laugh, short and real" in p


# ---------------- ack clips: per-flavour energy ----------------

def test_ack_ask_energy_flavours():
    assert "bright, a small found-it lift" in voice._ack_ask("Haan, mil gaya... ek second.", "m")
    assert "bright, a small found-it lift" in voice._ack_ask("Haan, ho gaya... bas ek minute.", "f")
    assert "a touch slower, thinking out loud" in voice._ack_ask("Hmm... sochne do, ek second.", "m")
    assert "a touch slower, thinking out loud" in voice._ack_ask("Hmm, ek minute.", "f")
    assert "warm, a little hurried" in voice._ack_ask("Haan, ek second.", "m")   # plain busy lines keep the v0.181 ask
    assert "warm, a little hurried" in voice._ack_ask("Achha, dekhta hoon.", "m")
    assert "real feeling in the voice" in voice._ack_ask("Theek hai, dekh raha hoon.", "f")
    assert "young Indian woman" in voice._ack_ask("Haan, ek second.", "f")
    assert "young Indian guy" in voice._ack_ask("Haan, ek second.", "m")


# ---------------- canned lines: chat keeps its shape, the voice gets speech ----------------

def test_canned_chat_lines_keep_their_shape():
    assert "✅" in _canned(_row("done")) and "ho gaya" in _canned(_row("done"))
    assert "❌" in _canned(_row("failed")) and "ruk gaya, dikkat aayi" in _canned(_row("failed"))
    assert "⏹" in _canned(_row("stopped")) and "band kar diya gaya" in _canned(_row("stopped")) \
        and "bol dena" in _canned(_row("stopped"))                       # the v0.189 pins stay true


def test_spoken_shape_strips_symbols_and_colon():
    for state in ("done", "failed", "stopped"):
        s = _spoken(_canned(_row(state)))
        assert not re.search(r"[✅❌⏹▶🔄⚠⏳]", s), s                     # symbols never reach her ears
        assert ": " not in s.split(",")[0], s                            # the flat "title: state" reads as a comma
        assert "band kar diya gaya" in s or "ho gaya" in s or "ruk gaya" in s
    assert _spoken("✅ Mera reel: ho gaya. (2 files)") == "Mera reel, ho gaya. (2 files)"
    assert _spoken(None) == "" and _spoken("") == ""


# ---------------- proactive lines: written for the ear ----------------

def test_wake_text_carries_delivery():
    t = _wake_text(_row(state="done", detail="4 shots ban gaye", link="https://x.y"))
    assert "apni awaaz mein 1-3 chhoti lines" in t                        # the v0.192 instruction stays
    assert "energy natije ke hisaab se" in t                              # v0.193: energy matches the result
    assert "comma ka matlab chhota pause" in t
    assert "https://x.y" in t and "4 shots ban gaye" in t                 # the digest is untouched


def test_one_shot_system_carries_delivery():
    assert "Jaise phone par bolti hai waise likho" in _ONE_SHOT_SYSTEM
    assert "energy natije ke hisaab se" in _ONE_SHOT_SYSTEM
    assert "koi ✅ ❌ jaise symbol nahi" in _ONE_SHOT_SYSTEM              # the old rules all survive
    assert "kuch apne aap se jodna mat" in _ONE_SHOT_SYSTEM


def test_kaamwatch_voice_note_rides_with_delivery(env, monkeypatch):
    from app import kaamwatch
    from app import voice as v
    got = []
    monkeypatch.setattr(v, "inject", lambda conv, text: got.append((conv, text)) or 1)
    kaamwatch._voice("t1", "c1", "Mera reel, ho gaya. link hai")
    assert got and got[0][0] == "c1"
    note = got[0][1]
    assert "energy that matches the news" in note and "short sentences" in note
    assert "a small smile in the voice" in note and "don't read symbols" in note
    assert "Mera reel, ho gaya. link hai" in note                         # her line rides unchanged


def test_followup_sends_spoken_line_to_the_call(env, monkeypatch):
    """The voice path gets _spoken(line); the chat keeps the original with its symbols."""
    import asyncio
    from sqlalchemy import select
    from app import voice as v
    from app.kaam_followup import KaamFollowup as K
    from app.config import get_settings
    from app.db import session
    calls = {"notify": [], "voice": []}
    monkeypatch.setattr(v, "inject", lambda conv, text: calls["voice"].append(text) or 1)
    monkeypatch.setattr("app.kaam_followup.notify", lambda conv, text: calls["notify"].append(text))
    monkeypatch.setattr("app.kaam_followup._model_line",
                        lambda r, s: asyncio.sleep(0, result=""))          # force the canned fallback
    monkeypatch.setattr("app.kaam_followup._recent_said", lambda conv, title: False)
    monkeypatch.setattr("app.kaam_followup._wake_allowed", lambda conv, s: False)
    assert kaam_followup.enqueue("default", "conv_spoken",
                                 {"key": "video:mera-reel", "kind": "video", "label": "Reel", "title": "Mera reel",
                                  "state": "done", "detail": None, "link": None})
    with session() as s:
        fid = s.scalars(select(K).where(K.conversation_id == "conv_spoken")).first().id
    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(
        kaam_followup._send(fid, get_settings()))
    assert calls["notify"] and calls["notify"][0].startswith("✅")        # chat: the honest canned line
    assert calls["voice"] and "✅" not in calls["voice"][0]               # call: spoken-shaped
    with session() as s:
        assert s.get(K, fid).status == "sent"


# ---------------- version ----------------

def test_version():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.324.0"
