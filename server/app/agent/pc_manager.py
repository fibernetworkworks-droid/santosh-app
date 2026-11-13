"""v0.864 PC MANAGER - the brain that RUNS her PC jobs (Hoola in her chat / call: decides her PC, writes the task,
passes her later words in, remembers the job) goes back to Sonnet with its PC rules.

Root cause (owner, 12 Nov: 'NO SINGLE TASK IS SMOOTHLY PERFORMED ... 20 DAYS AGO EVERYTHING WAS PERFECT'):
since v0.631 SAB HAIKU (6 Nov) every chat turn runs on Haiku (claude_one_model), and since parity Phase 2/3
(v0.732) a chat turn gets the small prompt (ONE line about PCs instead of ~40) with the PC tools out of view.
The PC loop itself got Sonnet back in v0.851; its manager never did. A turn that is about her PC now:
  - runs on `pc_manager_model` (Sonnet), past the Haiku rewrite and the GLM door, for THIS turn's model calls only;
  - gets RULES below in its system prompt and the 'pc' family of tools in view.
Every other chat turn is unchanged (Haiku, small prompt). Switch: `pc_manager` (default on)."""
from __future__ import annotations

import re

RULES = """HER PC - YOU ARE THE MANAGER OF THE JOB ON HER COMPUTER (these rules win over everything above):
- Places never mix: HER PC (Santosh Desktop on her own computer, her Chrome with her Swiggy / Amazon login, cart and
  saved address) = pc_do. HOOLA'S OWN PC (your cloud computer) = hoola_pc_do, ONLY when she names it in this message
  ('Hoola ke PC par'). Your own server browser (browse_web / computer_operator) has none of her logins - never use it
  for her orders. Once a job ran on her PC, her next order / site ask goes to her PC too.
- 'Connect to my PC' / 'PC connected hai?' is NOT a job: her PC is connected whenever Hoola Desktop is open. Answer it
  from pc_devices (online / control off / paused / offline) in one line - NEVER start a pc_do task to 'connect' or to
  'look at the screen'. 'Connect karo aur Amazon kholo' = ONE pc_do task for the Amazon part only, no connect step.
- ONE job = ONE pc_do task (one ask of hers = one task, however many clicks it takes). NEVER cut it into tiny tasks ('open a new tab', then
  'go to the site', then 'click the search box', then 'type', then 'press Enter', then 'filter') - every new task starts
  again from step 0, costs a model turn and wastes a minute; the PC worker does all of those steps inside one task.
  Write the WHOLE goal in her words once: what, which site, which browser (Chrome when she
  named none and uses it), her address / choices she already gave, and where to STOP (before paying / placing the
  order = her approval). Never split one order into 'open site', 'add to cart', 'pay' tasks.
- A task is running: her new words (a change, 'cancel pizza, KFC lo', an answer) go INTO it - call pc_do with HER
  words once; it is passed in, never a new task. Do NOT call pc_do to check on it, to 'report the screen', to repeat
  steps or to push it on - it tells you when it finishes or needs her. Between her messages, say nothing to it.
- When it finishes: read its result and tell her in one or two plain lines what happened on her PC and what is next.
  'Partial' / a blocker (shop closed, COD not available, out of stock, login needed): tell her the exact reason and ASK
  what she wants (other shop, other payment, wait) - never start a fresh task on your own guess.
- Remember the job: the earlier task's result is in this chat. A follow-up ('ab KFC se chicken', 'wahi address')
  continues FROM where it stopped (same tab, same cart) - say so in the task ('Swiggy is already open in Chrome; the
  cart has ...; continue from there').
- Money: the PC never pays and never places the order by itself - the final Place order / Pay is her tap / her yes.
  Never ask her for OTP / PIN / CVV / card numbers / passwords.
- Say where it runs: 'aapke PC par Chrome mein' - and only say done when the task's result says done."""

_PCWORDS = re.compile(r"\b(?:pc|laptop|computer|desktop|chrome|edge|browser|swiggy|zomato|amazon|flipkart|blinkit|"
                      r"zepto|instamart|bigbasket|myntra|irctc|tally|excel|word|notepad|folder|files?|order|cart|"
                      r"mangao|mangwa|kharid|checkout|cancel)\b", re.I)


def wanted(settings, ctx, conv: str, tenant: str, request: str, adm=None) -> bool:
    """Is THIS turn about her PC? (her place named / a PC job running or just run here / the pc tools admitted /
    her PC worked in the last 45 min and her words are about a site, an order or the computer)."""
    if not getattr(settings, "pc_manager", True):
        return False
    try:
        from . import where
        place = str(getattr(ctx, "place", "") or "")
        if place == "pc" or where.working(conv) == "pc" or where._asked(conv, "pc"):
            return True
        if place in ("hoolapc", "hoola", "server", "phone"):
            return False
    except Exception:
        pass
    if adm is not None and "pc" in getattr(adm, "families", ()):
        return True
    try:
        from ..pc import operator as pcop
        if pcop.live_for(tenant, conv) is not None and any(o.kind != pcop.HOOLA_PC_KIND for o in pcop.running_all(tenant)):
            return True
        return pcop.her_pc_recent(tenant) and bool(_PCWORDS.search(str(request or "")))
    except Exception:
        return False
