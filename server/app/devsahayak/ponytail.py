"""v0.999 PONYTAIL in Hoola Code (owner: "now ponytell to hoola code", on github.com/DietrichGebert/ponytail, MIT,
commit ebd8654, v5.3.3 - read whole: the skill, AGENTS.md, the review / audit / debt / gain / help skills, the hooks and
the benchmark).

Ponytail is one prompt ("the lazy senior developer: the whole problem with the least new code") plus three commands.
Its own benchmark (Claude Code, 39 tasks, 5 runs each) reports -53% lines of code and -26% cost against no skill, with
more risky logic shipping a test (98% vs 68%) - their numbers, not measured here.

What it adds on top of the Karpathy rules (karpathy.py), rewritten in Hoola's words, no file copied:
  - THE LADDER: stop at the first rung that fully works - does it need to exist / already in this repo / the standard
    library or platform / an installed dependency / one clear line / only then the minimum. Never a new dependency for
    a few lines.
  - Scope first: every place the change must reach (callers, tests, fixtures, config, exports) and what it could break.
  - Lazy about the solution, never about the change: a bug fix greps every caller and fixes the root cause once;
    moved code keeps its checks; new risky logic leaves one small test; NEVER cut validation at trust boundaries,
    data-loss handling, security or accessibility.
  - `shortcut: <the limit>, <when to upgrade>` comments for a deliberate shortcut, and /ponytail-debt to list them.
  - Levels lite / full (default) / ultra / off per session (`/ponytail <level>`; a repo's `.claude/settings.json` may
    set "ponytail": "<level>"; the server default is `dev_ponytail`).
  - /ponytail-review (this session's change) and /ponytail-audit (the whole repo): read-only rounds that report in
    four parts per finding (what this is / problem / fix / if we skip it), Must / Should / Nice, a verdict.
NOT brought in: the Claude Code "band" above the prompt and the local board (Hoola Code has its own cost, context and
test status on the session), the per-agent installers and the npm package.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

CREDIT = "(adapted from Ponytail, MIT)"
LEVELS = ("lite", "full", "ultra", "off")

RULES = """THE SMALLEST COMPLETE CHANGE """ + CREDIT + """ - be lazy about the solution, never about the change:
- Before you write, list every place the change must reach (callers, tests, fixtures, config, exports) and what it could
  break for her users (data lost or exposed, callers that stop working). That is the scope; extras are not.
- Then take the FIRST rung that fully works: (1) does it need to exist? skip what nobody asked for and name it in one
  line - "build me X" gets the smallest version that does the core job; (2) already in this repo (a helper, component,
  service, pattern)? use it the way the code around it does; (3) the standard library or the platform does it? use it
  (the repo's own component beats a native widget); (4) an installed dependency does it? use it - never add a dependency
  for a few lines; (5) one line a reader gets at a glance? one line; (6) only then the minimum code that works.
- Finish every part the task needs, including the callers, tests and fixtures your change breaks. A bug fix: grep every
  caller of the function first, then fix the root cause once in the shared code, not in one caller.
- Code you move or merge keeps its error handling and validation. Between options of equal size, take the one that is
  right on edge cases. A one-liner that needs decoding is not short.
- New logic that is not trivial (a branch, a loop, a parser, money or security, a whole new script) leaves one small test.
- A deliberate shortcut with a known limit gets a comment: `shortcut: <the limit>, <when to upgrade>`.
- NEVER cut: validation where outside input comes in, error handling that prevents data loss, security, accessibility,
  anything she asked for.
- In done `risk`, say in one or two lines what you skipped or did not check."""

LEVEL_TEXT = {
    "lite": "PONYTAIL LEVEL lite: build what she asked; where a smaller option exists, name it in one line and let her pick.",
    "full": "",
    "ultra": ("PONYTAIL LEVEL ultra: also question the request - before building, push back on any part her need does not "
              "justify (ask ONE short question in done if a part looks unneeded, and change nothing until she answers)."),
}

SUB_RULES = ("Take the first option that fully works: does it need to exist, already in this repo, the standard library, an "
             "installed dependency, one clear line, only then the minimum; never a new dependency for a few lines; never "
             "cut input validation, data-loss handling or security. " + CREDIT)

REVIEW_EXTRA = (" A finding needs a concrete case (this input or situation gives this wrong result) - no case, no finding. A "
                "`shortcut:` comment that names its limit is a decision, not a finding, unless the expected load already "
                "crosses it. " + CREDIT)

_FORMAT = """Write in very simple English: short sentences, everyday words; explain a technical term the first time.
Start with "What this {what} does:" in two or three sentences{load}. Then the findings in three groups (skip an empty
group): **Must fix** (bug, security, data loss, breaks at the expected load), **Should fix** (risky code without a test,
real slowness, duplication, a function that mixes jobs, code that should not exist), **Nice to have** (small speed-ups,
shorter forms). Number them across all groups so she can say "fix 2 and 5"{cap}. Every finding has a bold title with
`path:line`, then four short parts: **What this is**, **Problem**, **Fix** (the smallest fix that works - prefer one that
deletes code, never add layers or config the problem does not need), **If we skip it**. End with "Verdict:" (Ship / fix
1 and 3 first{healthy}), "Lean: -N lines possible." when there are lean findings, and "Not checked:" for what mattered
and could not be checked. Nothing found: "What this {what} does:", then "{clean}" and one line on what you checked.
Before you report, check every finding: re-read the lines, grep that the caller exists, that the value can really be
empty, that the code really is unused (tests, config and string references too). No style taste, no "consider", no
vague worries. Change NO file. Put the whole report in done explain."""

LOOK_FOR = """Look for, in this order: (1) BUG - wrong result, crash, missed edge case (empty, zero, last item, rounding,
time zones), a caller broken by the change, a fix in one caller while the shared function stays broken; (2) RISK -
injection, weak randomness, secrets, missing checks on input from users, data loss (swallowed errors, writes in the wrong
order, no transaction); (3) SCALE - fine for one user, wrong for many: check-then-write races, the same work done by
every process, lists or memory that only grow, a query per item, O(n^2) on big input; (4) MISSING TEST - risky logic (a
branch, a parser, money, security, data writes, a bug fix) with no test that fails when it breaks; (5) SPEED - big
slowdowns are problems, small wins are suggestions; (6) LEAN - dead code, unused options, speculative features, a helper
the repo already has (name the path), the standard library already does it, an abstraction with one implementation,
near-copies that must change together, one function doing several unrelated jobs (split by job, never by line count)."""

REVIEW = ("<her_command>/ponytail-review</her_command>\nReview this session's change like the senior developer who gets "
          "paged when it breaks " + CREDIT + ". Order: correct, safe, holds under load, tested, fast, lean. First "
          "understand: show_diff, then read the code it touches - callers of every changed function, what they call, the "
          "tests; when a signature, return value or behaviour changed, grep every caller (a change can break code it "
          "does not touch). Find the expected load in the repo (README, deploy config) and judge scale against it.\n"
          + LOOK_FOR + "\n" + _FORMAT.format(what="change", load="", cap="", healthy="", clean="Looks good. Ship."))

AUDIT = ("<her_command>/ponytail-audit</her_command>\nAudit the whole repo (or the folder she names) like the senior "
         "developer who just inherited it and will be paged when it breaks " + CREDIT + ". Map first: the README, "
         "deploy and build config, the dependency list, the entry points (main, routes, handlers, jobs, CLI), the tests; "
         "the expected load (one person running a script, or many users at once); trace the main flows end to end and "
         "read fully the paths where a mistake costs most (user input, money, auth, data writes, background jobs, "
         "anything shared between processes). A big repo: go deep where it matters and say which parts you did not read. "
         "Use code-explorer agents for separate areas when the repo is large.\n" + LOOK_FOR + "\n"
         + _FORMAT.format(what="repo", load=", and the load you assumed", cap="; at most 20, and say how many smaller "
                          "ones you left out", healthy=" / healthy", clean="Healthy. Nothing to fix."))

MARK = re.compile(r"(?:#|//|/\*|--|<!--)\s?(shortcut|ponytail):\s*(.*)", re.I)


def _set(name: str, default: Any) -> Any:
    try:
        from ..config import get_settings
        v = getattr(get_settings(), name, default)
        return default if v is None else v
    except Exception:  # noqa: BLE001
        return default


def default_level() -> str:
    v = str(_set("dev_ponytail", "full") or "full").strip().lower()
    return v if v in LEVELS else "full"


def level(ses: Any, conf: dict[str, Any] | None = None) -> str:
    """This session's level: her /ponytail choice, else the repo's settings.json "ponytail", else the server's default."""
    for v in ((getattr(ses, "meta", {}) or {}).get("ponytail"), (conf or {}).get("ponytail")):
        v = str(v or "").strip().lower()
        if v in LEVELS:
            return v
    return default_level()


def block(lvl: str) -> str:
    """What rides in the coder's fixed prompt for this level ('' when off)."""
    if lvl not in LEVELS or lvl == "off":
        return ""
    return RULES + (("\n" + LEVEL_TEXT[lvl]) if LEVEL_TEXT.get(lvl) else "")


def parse_level(words: str) -> tuple[bool, str]:
    """Her `/ponytail [lite|full|ultra|off]`: (is it that command, the level or '' for none / unknown)."""
    m = re.match(r"^\s*/ponytail(?:\s+(\S+))?\s*$", words or "", re.I)
    if not m:
        return False, ""
    arg = (m.group(1) or "").lower()
    return True, {"normal": "off", "stop": "off", "on": "full", "default": "full"}.get(arg, arg if arg in LEVELS else "")


def set_level(ses: Any, conf: dict[str, Any] | None, want: str) -> dict[str, Any]:
    """Ponytail's own rule: no level = switch it on at the default when it is off, otherwise report the level."""
    now = level(ses, conf)
    want = str(want or "").strip().lower()
    if want and want not in LEVELS:
        raise ValueError("Ponytail levels are lite, full, ultra and off.")
    new = want or (default_level() if now == "off" else now)
    if new == "off" and default_level() == "off":
        ses.meta.pop("ponytail", None)
    else:
        ses.meta["ponytail"] = new
    ses.save_meta()
    said = {"lite": "Ponytail lite: Hoola builds what you ask and names a smaller option.",
            "full": "Ponytail full: the smallest change that fully solves the task.",
            "ultra": "Ponytail ultra: Hoola also questions parts of a request your need does not justify.",
            "off": "Ponytail is off for this session."}[new]
    if new == now:
        said = "Ponytail is " + new + " for this session. Type /ponytail lite, full, ultra or off to change it."
    else:
        said += " From your next message."
    return {"ok": True, "ponytail": new, "said": said}


def debt(repo: Path, word: str = "") -> list[dict[str, Any]]:
    """Every `shortcut:` (or older `ponytail:`) comment in the working copy: path, line, the limit, the trigger."""
    word = re.sub(r"[^\w-]", "", word or "")[:30]
    rx = re.compile(r"(?:#|//|/\*|--|<!--)\s?(" + re.escape(word) + r"):\s*(.*)", re.I) if word else MARK
    pat = (r"(#|//|/[*]|--|<!--) ?(" + (re.escape(word) if word else "shortcut|ponytail") + "):")
    try:
        out = subprocess.run(["git", "-C", str(repo), "grep", "-nIiE", pat, "--", "."], capture_output=True, text=True,
                             timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        out = ""
    rows = []
    for ln in out.splitlines()[:400]:
        parts = ln.split(":", 2)
        if len(parts) < 3:
            continue
        m = rx.search(parts[2])
        if not m:
            continue
        text = re.sub(r"\s*(\*/|-->)\s*$", "", m.group(2)).strip()
        limit, _, trig = text.partition(",")
        rows.append({"path": parts[0], "line": int(parts[1]) if parts[1].isdigit() else 0, "text": text[:300],
                     "limit": limit.strip()[:200], "upgrade": trig.strip()[:200], "no_trigger": not trig.strip()})
    return rows


def debt_text(rows: list[dict[str, Any]], word: str = "") -> str:
    mark = word or "shortcut"
    if not rows:
        return (f"<her_command>/ponytail-debt</her_command>\nThe working copy has no `{mark}:` comments. Tell her: "
                "\"No shortcut debt. Clean ledger.\" Change NO file.")
    lines = [f"- {r['path']}:{r['line']} - {r['text']}" + (" [no-trigger]" if r["no_trigger"] else "") for r in rows[:200]]
    nt = sum(1 for r in rows if r["no_trigger"])
    return (f"<her_command>/ponytail-debt</her_command>\nThe deliberate shortcuts marked with `{mark}:` comments in the "
            f"working copy, found by Hoola (git grep) " + CREDIT + ":\n" + "\n".join(lines) +
            "\nTurn this into her ledger, grouped by file, one row each: `path:line, what was simplified. limit: ... "
            "upgrade: ...` (read the line around a comment when it does not say what was simplified). Skip a hit that is "
            "not a deferral (a note about a keyboard shortcut). A row with no upgrade trigger is tagged no-trigger - those "
            f"are the ones that quietly rot. End with \"{len(rows)} markers, {nt} with no trigger.\" Change NO file; "
            "put the ledger in done explain. If she wants it kept, she will ask for a file.")


def command(words: str) -> str:
    """Which Ponytail report her message asks for: 'review' | 'audit' | 'debt' | ''."""
    m = re.match(r"^\s*/ponytail-(review|audit|debt)\b", words or "", re.I)
    return m.group(1).lower() if m else ""
