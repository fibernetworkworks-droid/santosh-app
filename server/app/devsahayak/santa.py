"""v0.999 TWO REVIEWERS MUST BOTH PASS, from ECC's Santa method (affaan-m/ECC skills/santa-method, MIT, by Ronald
Skelton; the idea is theirs, the code is Hoola's own).

One reviewer shares the blind spots of the coder that wrote the change. The Santa method puts two independent reviewers
on it - same rubric, same inputs, neither sees the other's answer - and the change may only finish when BOTH pass. If
either fails, every critical issue from both goes back to the coder in one list, it fixes them, and both review again,
up to `dev_santa_rounds` (3) times. Still failing after that = the round finishes with the open issues written into its
risk, so she decides (ECC's "escalate to a human").

Per session and optional: /santa on, /santa off (default off - two extra reviews cost time and money). Switch for the
whole feature: `dev_santa` (default on = she may turn it on).
"""
from __future__ import annotations

import concurrent.futures as CF
import contextvars
import re
from typing import Any

CREDIT = "(adapted from ECC's Santa method)"

RUBRIC = """1. Complete: every part of her request is done - nothing skipped, stubbed, faked or left as TODO.
2. Correct: the logic is right for normal input, empty input, the edges, and errors; it would really run.
3. Scope: nothing changed that her request did not need (no drive-by renames, reformatting or refactors).
4. Safe: no secret in the code, input is checked where it enters, no injection, nothing destructive by default.
5. Proven: the change has a test or a run that shows it works, and the coder's claims match what the code does.
6. Consistent: it follows how this repo already does things (names, errors, structure, its own rules files)."""

PROMPT = """SANTA REVIEWER """ + CREDIT + """. You are ONE of two independent reviewers of a code change. You have NOT seen
the other review and never will. Your job is to find problems, not to approve: be rigorous.

Read her request, then the REAL change in the working copy (git diff, the changed files, the code around them; run the
tests or a command if one is known). Judge it against EACH criterion of the rubric below, PASS or FAIL, citing the exact
file:line for a FAIL.

RUBRIC
""" + RUBRIC + """

Answer in this shape, nothing before the first line:
VERDICT: PASS            (or VERDICT: FAIL)
1 Complete: PASS|FAIL - <detail>
2 Correct: PASS|FAIL - <detail>
3 Scope: PASS|FAIL - <detail>
4 Safe: PASS|FAIL - <detail>
5 Proven: PASS|FAIL - <detail>
6 Consistent: PASS|FAIL - <detail>
CRITICAL:
- <each blocker that must be fixed, with file:line; "none" if there are none>
SUGGESTIONS:
- <non-blocking improvements>

VERDICT: FAIL only when there is at least one CRITICAL issue. A suggestion never fails the change."""

SPEC = {"name": "santa-reviewer", "title": "Santa reviewer", "group": "review", "tools": "run",
        "when": "Only by Hoola, when two-reviewer mode is on: one of two independent reviews before a round may finish.",
        "prompt": PROMPT, "langs": (), "files": "", "words": "", "ecc": "skills/santa-method/SKILL.md"}


def _set(name: str, default: Any) -> Any:
    try:
        from ..config import get_settings
        v = getattr(get_settings(), name, default)
        return default if v is None else v
    except Exception:  # noqa: BLE001
        return default


def available() -> bool:
    return bool(_set("dev_santa", True))


def is_on(ses: Any) -> bool:
    return available() and bool((getattr(ses, "meta", {}) or {}).get("santa"))


def parse_cmd(words: str) -> tuple[bool, str]:
    """Her /santa [on|off]: (is it the command, 'on' | 'off' | '' = turn on)."""
    m = re.match(r"^\s*/santa(?:-loop)?\b\s*(\S*)\s*$", words or "", re.I)
    if not m:
        return False, ""
    return True, m.group(1).lower()


def set_on(ses: Any, want: str) -> str:
    if not available():
        return "Two-reviewer mode is switched off on this server."
    if want not in ("", "on", "off", "yes", "no"):
        raise ValueError("Say /santa on or /santa off.")
    on = want in ("", "on", "yes")
    ses.meta["santa"] = on
    ses.save_meta()
    return ("Two-reviewer mode is ON for this session: before a change finishes, two independent reviewers check it "
            f"and both must pass (up to {int(_set('dev_santa_rounds', 3) or 3)} fix rounds)." if on else
            "Two-reviewer mode is OFF for this session.")


def verdict(text: str) -> tuple[str, list[str]]:
    """('pass' | 'fail' | 'unclear', critical issues)."""
    body = text.split("]\n", 1)[1] if text.startswith("[") and "]\n" in text else text
    first = next((ln.strip().upper() for ln in body.splitlines() if ln.strip()), "")
    crit: list[str] = []
    m = re.search(r"(?ims)^\s*CRITICAL:\s*\n(.*?)(?:^\s*SUGGESTIONS:|\Z)", body)
    if m:
        for ln in m.group(1).splitlines():
            x = re.sub(r"^\s*[-*]\s*", "", ln).strip()
            if x and not re.match(r"(?i)^none\b", x):
                crit.append(x[:600])
    if first.startswith("VERDICT: PASS"):
        return "pass", []
    if first.startswith("VERDICT: FAIL"):
        return "fail", crit[:12] or ["(the reviewer failed it without naming the issue - see its report)"]
    return "unclear", crit[:12]


def task_text(t: Any, follow_up: str, finish: dict[str, Any], files: list[str], earlier: list[str]) -> str:
    return ("Her request for this round:\n" + str(follow_up or getattr(t, "text", "") or "")[:3000]
            + ("\n\n(The session started with: " + str(getattr(t, "text", ""))[:1200] + ")" if follow_up else "")
            + "\n\nThe coder says it is finished. Its words: " + str(finish.get("explain") or "")[:1500]
            + "\nWhat it says it ran: " + str(finish.get("test_plan") or "(nothing named)")[:800]
            + "\nFiles changed: " + ", ".join(files[:40])
            + ("\n\nIssues an earlier review round raised (check whether each is really fixed now):\n- "
               + "\n- ".join(earlier[:12]) if earlier else "")
            + "\n\nReview the REAL working copy against the rubric. Start with the VERDICT line.")


def review(tools: Any, ses: Any, t: Any, follow_up: str, finish: dict[str, Any], emit: Any, stopped: Any,
           earlier: list[str], pick: tuple[str, str] = ("", ""), part: dict | None = None) -> dict[str, Any]:
    """Run both reviewers at the same time. {ok, issues, reports, ran}; ran False = it could not run (never blocks)."""
    from . import subagent as SA
    files = [r["path"] for r in ses.changed()][:40]
    task = task_text(t, follow_up, finish, files, earlier)
    who = ("Santa reviewer A", "Santa reviewer B")

    def one(label: str) -> str:
        return SA.run_one(tools, "santa-reviewer", task + f"\n\n(You are {label}.)", files, emit=emit, stopped=stopped,
                          pick=pick, part=part)

    with CF.ThreadPoolExecutor(max_workers=2) as ex:
        futs = [ex.submit(contextvars.copy_context().run, one, w) for w in who]
        reports = [f.result() for f in futs]
    got = [verdict(r) for r in reports]
    if all(v == "unclear" and not c for v, c in got):
        return {"ok": True, "ran": False, "issues": [], "reports": reports}
    issues: list[str] = []
    for (v, c), w in zip(got, who):
        for x in c:
            issues.append(f"[{w}] {x}")
    ok = all(v == "pass" for v, _ in got)
    return {"ok": ok, "ran": True, "issues": issues, "reports": reports, "verdicts": [v for v, _ in got]}


def back_text(res: dict[str, Any], n: int, limit: int) -> str:
    return ("NOT finished yet " + CREDIT + f" - review round {n} of {limit}: two independent reviewers checked your change "
            "and they do not BOTH pass it. Every critical issue they raised:\n- " + "\n- ".join(res["issues"][:20])
            + "\n\nConfirm each one in the code yourself. Fix the real ones and prove it with a run; one you can show is "
            "wrong, leave and say why in risk. Then call done again - both reviewers will look again.")


def open_risk(res: dict[str, Any]) -> str:
    return ("Two independent reviewers still did not both pass it after the last fix round " + CREDIT + ". Open issues:\n- "
            + "\n- ".join(res["issues"][:12]))
