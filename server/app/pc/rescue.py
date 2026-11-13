"""v0.867 PC SASTA (owner: "GO QWEN 27B" after the deep search for a very low cost desktop brain): the three things that
make a CHEAP model safe to give a PC.

  1. PLAYBOOK  - a short fixed skill the cheap worker reads on every task (how to look, act, check, ask, stop).
  2. RESCUE    - the cheap worker runs most steps; when it is stuck (the same action again and again, the screen
                 not changing, errors in a row) the next few steps run on the strong model (Sonnet via OpenRouter)
                 which sees the same history, then the cheap worker takes over again.
  3. SPEND     - a step cap per task and a daily rupee cap per person (an ESTIMATE from a flat price per step of the
                 brain that ran it, not an invoice), so a test can never silently burn thousands again.

Pure functions + a few dicts; operator.py calls `observe` once per turn and `over_budget` before each step, brain.py
asks `rescue_active` which model to use. Nothing here touches the PC.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

from ..config import get_settings

log = logging.getLogger("santosh.pc")

STATS: dict[str, int] = {"rescues": 0, "budget_stops": 0}

# estimated rupees for ONE PC step (about 8k tokens in, 300 out, ~Rs 88 / USD, read from OpenRouter's list prices on
# 12 Nov 2026) - an estimate for the daily cap, nothing more
STEP_INR: dict[str, float] = {"qwen27": 0.2, "qwen": 1.5, "sonnet-or": 1.8, "sonnet": 2.0}
SPEND: dict[tuple[str, str], float] = {}     # (tenant, IST day) -> estimated rupees spent on PC steps

PLAYBOOK = """
DESKTOP PLAYBOOK (follow it on every step - it is how a careful person does PC work without mistakes):
1. LOOK first. Read the screenshot and the window list before you act. Say to yourself what the screen is.
2. ONE job, ONE plan. Work the task in the shortest sensible order. Never start over, never redo what is done.
3. ACT, then CHECK. After every action the next screenshot must show the change you expected (a page opened, a field
   filled, a number changed). If it did not change, do NOT repeat the same action: look again, try another way
   (page_elements by ref, a keyboard shortcut, scroll, a different button) - the same click three times is a bug.
4. Websites: open_url (it reuses an open tab), then page_elements and page_click / page_type BY REF; page_text only when
   you need exact words or prices. Shopping and food sites are slow: wait 2 and look at the screenshot, do not poll.
5. Desktop apps: open_app or focus_window, then ax_snapshot / ax_click / ax_set_value BY REF; keyboard shortcuts for
   save, find, select all. Files: File Explorer, sort by the column she names, select, then move / rename / delete.
6. CHOICES are hers. If the task leaves a choice open (which item, size, address, payment) read the real options and
   ask_user with 3-6 of them and their prices. Never pick for her, never guess a price.
7. If an option is not available (cash on delivery off, item sold out, slot full, login wall), do not give up and do
   not pick another on your own: say exactly what you see and ask_user what she wants instead.
8. STOP before money or sending. At payment, final order, send, delete or install: ask_approval. Never type a password,
   PIN, OTP or card number yourself.
9. DONE means the result is on the screen. Before done, look once more: is the thing she asked for really there
   (order placed on the page, file moved, text saved)? Then done with the key facts. Not finished = done(success=false)
   saying what is left. Never say done because you ran out of ideas.
10. Short turns: do the next 1-3 actions that you can already see are right, not a long guess.
"""


def playbook_on(op: Any) -> bool:
    st = get_settings()
    return bool(getattr(st, "pc_playbook", True)) and getattr(op, "brain", "") == "qwen27"


# ------------------------------------------------------------------ rescue
def rescue_route() -> tuple[str, str] | None:
    """(brain, model) of the strong helper: Sonnet through OpenRouter. None = no OpenRouter key or rescue off."""
    st = get_settings()
    if not getattr(st, "pc_rescue", True):
        return None
    from . import brain as _b
    if _b.qwen_route() is None:
        return None
    return "sonnet-or", str(getattr(st, "pc_openrouter_sonnet", "") or "anthropic/claude-sonnet-5.5")


def rescue_active(op: Any) -> tuple[str, str] | None:
    """(brain, model) for THIS step when a rescue is running, and use one of its steps up; None = the task's own brain."""
    left = int(getattr(op, "rescue_left", 0) or 0)
    if left <= 0:
        return None
    route = rescue_route()
    if route is None:
        op.rescue_left = 0
        return None
    op.rescue_left = left - 1
    return route


def _sig(name: str, args: dict) -> str:
    try:
        return name + ":" + json.dumps(args, sort_keys=True, default=str)[:300]
    except Exception:
        return name


_PASSIVE = {"wait", "screenshot", "scroll", "zoom", "tabs", "downloads", "page_text", "page_elements", "ax_snapshot",
            "ax_text", "ax_find", "ax_apps", "ask_user", "ask_approval", "ask_otp", "stage_done"}


def _result_text(r: dict) -> str:
    c = r.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
    return ""


def _shot_hash(shot: Any) -> str:
    """Hash of the screenshot the model is about to see (the image bytes). Same screen = same hash; a clock or a blinking
    cursor makes a different hash - so this can only MISS a stuck screen, never call a moving one stuck."""
    try:
        for b in shot or []:
            if isinstance(b, dict) and b.get("type") == "image":
                data = (b.get("source") or {}).get("data") or ""
                if data:
                    return hashlib.md5(str(data).encode()).hexdigest()
    except Exception:
        pass
    return ""


def observe(op: Any, uses: list[dict], results: list[dict], shot: Any) -> str:
    """Called once per finished turn (after its actions and the new screenshot). Returns a short note to append to the
    turn's result when the cheap worker is stuck and a rescue starts, else ''. Sets op.rescue_left."""
    st = get_settings()
    if not getattr(st, "pc_rescue", True) or getattr(op, "brain", "") != "qwen27":
        return ""
    acts = [(u.get("name", ""), u.get("input") or {}) for u in uses]
    active = [s for s in (_sig(n, a) for n, a in acts) if s.split(":", 1)[0] not in _PASSIVE]
    sigs = getattr(op, "sigs", None)
    if sigs is None:
        sigs = op.sigs = []
    sigs.append("|".join(active) if active else "")
    del sigs[:-6]
    hashes = getattr(op, "shots", None)
    if hashes is None:
        hashes = op.shots = []
    h = _shot_hash(shot)
    hashes.append((h, bool(active)))
    del hashes[:-6]
    errs = [t for t in (_result_text(r) for r in results) if t.startswith(("ERROR", "REFUSED", "NOT RUN"))]
    op.err_run = (int(getattr(op, "err_run", 0) or 0) + 1) if (results and len(errs) == len(results)) else 0
    if int(getattr(op, "rescue_left", 0) or 0) > 0:
        return ""                                       # a rescue is already running
    why = ""
    if len(sigs) >= 3 and sigs[-1] and sigs[-1] == sigs[-2] == sigs[-3]:
        why = "the same action three times in a row"
    elif len(hashes) >= 3 and all(x[1] for x in hashes[-2:]) and hashes[-1][0] and \
            hashes[-1][0] == hashes[-2][0] == hashes[-3][0]:
        why = "the screen did not change after two actions"
    elif op.err_run >= 2:
        why = "two turns in a row ended in an error"
    elif int(getattr(op, "aim_repeats", 0) or 0) >= 2:      # v0.876 the same aim again (open the site again...)
        why = "it kept redoing work that was already done"
    elif getattr(op, "drift_stuck", False):                 # v0.882 many steps with nothing new done (steady.drift)
        why = "many steps went by with nothing new done for the task"
    if not why:
        return ""
    if int(getattr(op, "rescues", 0) or 0) >= int(getattr(st, "pc_rescue_max", 4) or 4):
        return ""
    route = rescue_route()
    if route is None:
        return ""
    op.rescues = int(getattr(op, "rescues", 0) or 0) + 1
    op.rescue_left = max(1, int(getattr(st, "pc_rescue_steps", 3) or 3))
    op.sigs, op.shots, op.err_run = [], [], 0
    op.aim_repeats = 0
    op.drift_stuck = False
    STATS["rescues"] += 1
    log.info("pc rescue %s step %d #%d -> %s for %d steps | %s", getattr(op, "id", "?"), getattr(op, "step", 0), op.rescues,
             route[1], op.rescue_left, why)
    return (f"\n(HOOLA: the last steps were not working - {why}. A stronger helper takes the next steps: look at the "
            "screen fresh, do NOT repeat what failed, choose a different way.)")


# ------------------------------------------------------------------ spend
def _day() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(time.time() + 19800))     # IST


def charge(op: Any, brain: str) -> None:
    key = (str(getattr(op, "tenant", "") or ""), _day())
    SPEND[key] = SPEND.get(key, 0.0) + STEP_INR.get(brain, 1.5)
    for k in [k for k in SPEND if k[1] != key[1]]:
        SPEND.pop(k, None)


def spent_today(tenant: str) -> float:
    return round(SPEND.get((str(tenant or ""), _day()), 0.0), 2)


def over_budget(op: Any) -> str:
    """A plain sentence when she has used up today's PC allowance (estimate), else ''."""
    cap = float(getattr(get_settings(), "pc_daily_inr", 300) or 0)
    if cap <= 0:
        return ""
    used = spent_today(getattr(op, "tenant", ""))
    if used < cap:
        return ""
    STATS["budget_stops"] += 1
    return (f"Aaj ka PC kharcha limit (Rs {cap:.0f}, andaaza) poora ho gaya (Rs {used:.0f}). Kal phir chalega, ya limit "
            "badhane ke liye PC_DAILY_INR badaliye.")


def step_cap(steps_max: int) -> int:
    cap = int(getattr(get_settings(), "pc_step_cap", 0) or 0)
    return min(steps_max, cap) if cap > 0 else steps_max
