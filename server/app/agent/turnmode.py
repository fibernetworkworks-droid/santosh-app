"""v0.782 TEEN MODE (L2 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L2") - Build / Plan / Chat, enforced on the SERVER.

The Web Studio sends one line with every message: `[Web console mode: build|plan|chat]` (it rides inside her message,
so a turn re-run after a restart keeps its mode). `begin(text)` reads it at the start of the turn into a contextvar:

  build  - nothing changes (the default; any other surface never sends the line)
  plan   - Hoola investigates and writes a PLAN; every tool that changes something is REFUSED here, not just asked nicely
  chat   - Hoola talks about the site and the idea; every changing tool is refused; when the talk needs real work the
           reply ends with `[[start-building: <one line>]]` and the Studio draws a "Start building" card (Build / Skip)

`allowed(tool)` is checked by `santosh._run_tool` before ANY tool runs. Reads (draftcheck._is_read: *_dekho, the READS
set, read-name patterns) plus a few page readers stay open, so Plan / Chat can still look at the site, a reference page
or her memory. The refusal tells the model what to do instead, so the turn ends cleanly.

The same line carries the site (`site id <id>`): `site_block()` adds the site's STANDING INSTRUCTIONS (her brief for this
website, up to 10,000 characters, `site/plans.py`) and, in Build mode, the APPROVED plan the build should follow."""
from __future__ import annotations

import contextvars
import re

MODE: contextvars.ContextVar[str] = contextvars.ContextVar("hoola_turn_mode", default="")
SITE: contextvars.ContextVar[str] = contextvars.ContextVar("hoola_turn_site", default="")
_MODE_RE = re.compile(r"\[Web console mode: (build|plan|chat)\]")
_SITE_RE = re.compile(r"\(site id ([A-Za-z0-9_\-]{3,80})\)")
# page readers that change nothing: Plan / Chat may look at a reference page or the live site
_OPEN = {"web_fetch", "scrape_page", "scrape", "reach", "open_website", "duniya", "api_box", "jharokha"}
STATS = {"refused": 0, "plan": 0, "chat": 0}


def parse(text: str) -> tuple[str, str]:
    t = str(text or "")
    m, s = _MODE_RE.search(t), _SITE_RE.search(t)
    return (m.group(1) if m else ""), (s.group(1) if s else "")


def begin(text: str) -> str:
    """Set this turn's mode + site from her message. Returns the mode ('' = build / not the Studio)."""
    from ..config import get_settings
    mode, site = parse(text)
    if not getattr(get_settings(), "studio_modes", True):
        mode = ""
    mode = "" if mode == "build" else mode
    MODE.set(mode)
    SITE.set(site)
    if mode:
        STATS[mode] = STATS.get(mode, 0) + 1
    return mode


def allowed(tool: str) -> bool:
    mode = MODE.get()
    if mode not in ("plan", "chat"):
        return True
    if tool in _OPEN:
        return True
    from . import draftcheck
    return draftcheck._is_read(tool)


def refusal(tool: str) -> str:
    STATS["refused"] += 1
    if MODE.get() == "plan":
        return (f"Plan mode: '{tool}' would change something, so it did not run. In Plan mode you only look and write the "
                "plan (what changes, what stays the same, the steps, anything you need from her). She approves it, then "
                "Build mode does the work.")
    return (f"Chat mode: '{tool}' would change something, so it did not run. Chat mode only talks and looks. If she wants "
            "this done, end your reply with one line `[[start-building: <what to do, one line>]]` - she gets a "
            "Start building card and decides.")


def rules() -> str:
    """The mode's rules for the system prompt (the Studio's own hint says the same; this is the server's copy)."""
    mode = MODE.get()
    if mode == "plan":
        return ("\n\nPLAN MODE (Web Studio): investigate (read the site, her words, any page she named) and reply with a "
                "PLAN in markdown: ## Goal, ## What changes, ## What stays the same, ## Steps (numbered), ## Questions "
                "(only if you truly need her answer). Change NOTHING - every changing tool is refused in this mode. "
                "Keep it to what she asked; no extra features.")
    if mode == "chat":
        return ("\n\nCHAT MODE (Web Studio): talk with her about this website or her idea - explain, compare, suggest. "
                "Change NOTHING (changing tools are refused). Keep answers short. When the talk turns into work she "
                "wants done, end with exactly one line `[[start-building: <what to do, one line>]]`.")
    return ""


def site_block(tenant: str) -> str:
    """Her standing instructions for this site (+ the approved plan in Build mode), for the system prompt."""
    site = SITE.get()
    if not site:
        return ""
    out = ""
    try:
        from ..site import plans as P
        out = P.prompt_block(tenant, site, build=MODE.get() == "")
    except Exception:
        out = ""
    try:                                     # v0.795 YEH WALA: the elements she pointed at, read once by this turn
        from ..site import yehwala as YW
        out += YW.selection_block(tenant, site)
    except Exception:
        pass
    return out
