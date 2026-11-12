"""v0.691.0 KAAM MANCH - the work-discipline layer, backend-only (owner: "GO" on the OWL deploy
plan; upstream github.com/camel-ai/owl @ 2df367e, Apache-2.0, external PRs welcome; IDEA-ONLY:
zero upstream code crossed the wall - what ported is the orchestration doctrine: the specialist
workers' search/verify/code heuristics (examples/run.py prompts + the society's <tips> block),
the <TASK_DONE> "never say done unless solved" law, and run_society's per-round honest record).

NOT a tool and NOT a family: registry stays 615, zero new deps, zero network, zero keys. Three
surfaces, all behind settings.kaam_enabled (default True, off = byte-identical behaviour):
  1. TIPS - the heuristics block, house-written, appended to the system prompt ALWAYS (after the
     family cut, never admission-dropped);
  2. done_note - the free in-code backstop inside _pakka_check: a strong done-claim while every
     real call of the turn failed sets the correction note (no model call, no loop);
  3. ledger - one (Kaam: ...) work-receipt note row under the answer when tools ran (pure
     arithmetic over the turn's own state; no token count because state holds none - a made-up
     number is worse than none, the house's own after_call law).

The whole suite is OFFLINE (zero network): the layer has no seam to patch because it makes no
call - the tests exercise the pure functions, the source wiring, the switches and the pins.
"""
import ast
import subprocess
import sys
from pathlib import Path

import pytest

from app.agent import kaam_laws as K
from app.agent import prompts as P
from app.agent.tools import TOOLS

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "server"


# ---------------------------------------------------------------- TIPS (the prompt block)

def test_tips_exist_and_deterministic():
    assert K.TIPS.strip()
    assert K.tips_block() == K.TIPS == K.tips_block()          # pure, deterministic


def test_tips_provenance_in_module():
    src = (SERVER / "app" / "agent" / "kaam_laws.py").read_text()
    assert "camel-ai/owl@2df367e" in src and "Apache-2.0" in src and "IDEA-ONLY" in src
    assert K.SOURCE == "camel-ai/owl@2df367e (Apache-2.0, idea-only)"


def test_tips_house_register():
    # Hinglish house flavour, not upstream English
    assert "kaam" in K.TIPS.lower() and "ho gaya" in K.TIPS.lower()
    assert "KAAM MANCH (v0.688" in K.TIPS


def test_tips_carry_the_seven_heuristics():
    t = K.TIPS.lower()
    assert "broad" in t and "narrow" in t            # coarse-to-fine search
    assert "snippet" in t and "page" in t            # snippet is not a number
    assert "sources" in t                            # name your sources
    assert "different query" in t                    # if one road fails
    assert "run" in t and "code" in t                # code is not work until you run it
    assert "proven" in t                             # done means proven
    assert "one step at a time" in t                 # lamba kaam decomposition


def test_no_upstream_sentence_verbatim():
    # distinctive OWL sentences that must NOT appear (rewritten, never quoted)
    for needle in ("Never flip roles", "answer does exists", "single step",
                   "TASK_DONE", "OwlRolePlaying", "camel-ai[owl]"):
        assert needle.lower() not in K.TIPS.lower(), needle


def test_tips_not_baked_into_SYSTEM():
    # the block appends AFTER the family cut, it is not a SYSTEM block (so no admission gating)
    assert K.TIPS not in P.SYSTEM


def test_system_text_carries_tips_always():
    full = P.system_text(None)                       # admission off / routines path
    cut = P.system_text(frozenset({"office"}))       # an admitted-family turn
    for text in (full, cut):
        assert text.endswith(K.TIPS)


def test_switch_off_is_byte_identical(monkeypatch):
    from app.config import get_settings
    s = get_settings()
    monkeypatch.setattr(s, "kaam_enabled", False)
    assert P.system_text(None) == P.SYSTEM           # no append at all
    assert P._kaam_tips() == ""


# ---------------------------------------------------------------- LEDGER (the work receipt)

def _st(**kw):
    base = {"calls": [{"tool": "duniya", "ok": True}, {"tool": "workspace", "ok": True},
                      {"tool": "duniya", "ok": False}]}
    base.update(kw)
    return base


def test_ledger_empty_state_no_line():
    assert K.ledger({"calls": []}, 3, 24) == ""
    assert K.ledger({}, 3, 24) == ""


def test_ledger_shape():
    line = K.ledger(_st(), 7, 24)
    assert line.startswith("(Kaam: ") and line.endswith(")")
    assert " · " in line


def test_ledger_steps_and_cap():
    assert "7/24 steps" in K.ledger(_st(), 7, 24)
    assert "9/80 steps" in K.ledger(_st(), 9, 80)     # the goal cap reads the same way


def test_ledger_calls_and_ok_count():
    assert "3 calls (2 ok)" in K.ledger(_st(), 7, 24)


def test_ledger_plan_line():
    line = K.ledger(_st(), 7, 80, plan_left=3, plan_total=5)
    assert "plan 2/5" in line


def test_ledger_left_over_beats_done_tick():
    assert "left:" in K.ledger(_st(left="invoice bhejni hai"), 7, 24)
    assert "done" not in K.ledger(_st(left="invoice bhejni hai"), 7, 24)
    assert "done ✓" in K.ledger(_st(), 7, 24)        # clean close shows the tick
    assert "done ✓" not in K.ledger(_st(kept_going=1), 7, 24)


def test_ledger_per_tool_cap():
    calls = [{"tool": f"t{i}", "ok": True} for i in range(15)]
    line = K.ledger({"calls": calls}, 5, 24)
    assert "t0" in line and "t11" in line and "t12" not in line and "+3" in line


def test_ledger_never_raises():
    assert K.ledger({"calls": "oops"}, 7, 24) == ""           # garbage state
    assert K.ledger({"calls": [{"tool": None, "ok": None}]}, None, None)  # junk values still line or ""
    assert K.ledger(_st(), 7, 24)                             # sanity: the good path unaffected


# ---------------------------------------------------------------- DONE LAW (the backstop)

def test_done_note_fires_on_failed_claim():
    st = {"calls": [{"tool": "scrape", "ok": False}, {"tool": "scrape", "ok": False}]}
    note = K.done_note(st, "Bill ban gaya aur bhej diya!")
    assert note.startswith("(Kaam:") and "fail" in note.lower()


def test_done_note_quiet_when_a_call_succeeded():
    assert K.done_note({"calls": [{"tool": "x", "ok": True}]}, "sab ho gaya") == ""


def test_done_note_quiet_without_calls():
    assert K.done_note({"calls": []}, "ho gaya") == ""


def test_done_note_respects_negation():
    st = {"calls": [{"tool": "scrape", "ok": False}]}
    for text in ("Abhi poora nahi hua, tools fail ho gaye.",
                 "It is not done yet - the page would not open.",
                 "Maine file create nahi ki, error aaya."):
        assert K.done_note(st, text) == "", text


def test_done_note_quiet_on_plain_text():
    st = {"calls": [{"tool": "scrape", "ok": False}]}
    assert K.done_note(st, "Main check kar raha hoon, ek minute.") == ""
    assert K.done_note(st, "Yeh kya ho gaya yahan?") == ""      # question echo, not a claim


def test_done_note_hinglish_and_honest():
    note = K.done_note({"calls": [{"tool": "scrape", "ok": False}]}, "payment ho gaya")
    assert "To be clear" in note and "not done" in note


# ---------------------------------------------------------------- WIRING (switches + sources)

def test_config_switches_default_on():
    from app.config import get_settings
    s = get_settings()
    assert s.kaam_enabled is True
    assert s.kaam_ledger_enabled is True


def test_santosh_wiring_pins():
    src = (SERVER / "app" / "agent" / "santosh.py").read_text()
    # the ledger block: both switches gate it, the note rides as its own row (the v0.668 law)
    assert "settings.kaam_enabled and settings.kaam_ledger_enabled" in src
    assert src.count('_kaam.ledger(state, ran_steps') == 1
    # the backstop: gated, sets the correction note only, never a nudge loop
    assert "_kaam.done_note(state, final_text)" in src
    assert 'state["correct"] = _note' in src


def test_prompts_wiring_pin():
    src = (SERVER / "app" / "agent" / "prompts.py").read_text()
    assert "def _kaam_tips()" in src
    assert "get_settings().kaam_enabled" in src
    assert "kaam_laws.tips_block()" in src


def test_ledger_switch_alone_can_go_quiet(monkeypatch):
    from app.config import get_settings
    s = get_settings()
    monkeypatch.setattr(s, "kaam_ledger_enabled", False)
    # tips + backstop still on: the prompt still carries the block
    assert P.system_text(None).endswith(K.TIPS)


# ---------------------------------------------------------------- PINS & PURITY

def test_registry_unchanged_615():
    # KAAM MANCH adds ZERO tools (it is a laws layer, not a family): the count the v0.681/v0.687
    # pins carry stays exactly what their ships left
    assert len(TOOLS) == 629, "626 + 1 app_engine (v0.824 APP ENGINE 1: the Web Studio React app lane - one new tool). 625 + 1 hoola_design (v0.817.0 HOOLA DESIGN: the design editor's one tool). 624 + 1 ai_app (v0.785 HOOLA AI APPS). 623 + 1 video_kit (v0.772 VIDEO KIT: exact ffmpeg video edits). 617 + 1 shilp (v0.730 SHILP MANCH: the ArtCraft generation lane, their Omni API api.storyteller.ai, BYOK - owner 'MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS' -> the plan's W0). 616 + 1 seekh_video (v0.713 SEEKH MANCH: the learn-from-video bridge tool, owner 'GO' on the SEEKH MANCH plan). v0.688 KAAM MANCH must not add tools"


def test_no_kaam_tool_registered():
    names = {t["name"] for t in TOOLS}
    assert "kaam" not in names and "kaam_laws" not in names
    assert not hasattr(K, "KAAM_TOOLS") and not hasattr(K, "HANDLERS")   # not a tool module


def test_module_purity_stdlib_only():
    tree = ast.parse((SERVER / "app" / "agent" / "kaam_laws.py").read_text())
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    assert imports == {"re"}, imports                       # stdlib re only, nothing else


def test_fresh_interpreter_import_inert():
    # LAW-PURITY: a fresh interpreter imports the module with zero side effects (no threads, no
    # env, no files, no network) - the P1 inertness probe precedent, one subprocess
    code = ("import sys; sys.path.insert(0, r'%s'); "
            "import threading, os; n0 = threading.active_count(); "
            "from app.agent import kaam_laws; "
            "assert threading.active_count() == n0, 'spawned threads'; "
            "assert kaam_laws.TIPS; print('inert-ok')") % str(SERVER)
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0 and "inert-ok" in out.stdout, out.stderr


def test_app_version_pin():
    from app.main import APP_VERSION
    assert APP_VERSION == "0.857.0"                        # conscious-bump guard: moves with every release


def test_pubspec_pin():
    pub = (ROOT / "pubspec.yaml").read_text()
    assert "version: 0.857.0+856" in pub
