"""P2 THE FINAL CHECK (plan 6.10) - code only, milliseconds.

  figures   every key figure in the answer must be found in the facts the turn had (her own words + what the
            turn's tools returned); checked only when tools ran - an answer from the model's own knowledge has no
            facts list to hold it to, and is not marked down for that
  files     every file the turn says it made exists
  not_done  everything a part could not do is mentioned in the answer

A problem is RECORDED on the job sheet. The fix round (the part runs once more one level up, plan 5.3) is P4.
"""
from __future__ import annotations

import os
import re
from typing import Any

from ..research import figures as F

FILE_ID = re.compile(r'"(?:file_id|fid)"\s*:\s*"([A-Za-z0-9_\-]{6,80})"')
FILE_PATH = re.compile(r'"(?:path|file_path)"\s*:\s*"(/[^"\n]{3,300})"')


def facts_from(user_text: str, tool_outputs: list[str]) -> list[dict]:
    """The facts list of a one-part turn: every figure in her words and in the tools' results, with its source."""
    out: list[dict] = []
    for src, text in [("her", user_text)] + [(f"tool:{i + 1}", t) for i, t in enumerate(tool_outputs)]:
        for v in F.numbers(text or ""):
            out.append({"value": v, "source": src})
    return out


def files_from(tool_outputs: list[str]) -> list[str]:
    found: list[str] = []
    for t in tool_outputs:
        for m in FILE_PATH.finditer(t or ""):
            if m.group(1) not in found:
                found.append(m.group(1))
    return found


def one_step(nums: list[float], cap: int = 12) -> list[float]:
    """v0.966: one step of arithmetic on her own figures (3 x 5 = 15 in a worked answer is a working step, not an
    invented fact). Only her figures, at most 12 of them, so the check keeps its teeth."""
    ns = list(dict.fromkeys(nums))[:cap]
    out: list[float] = []
    # v0.970 a percent of hers is a rate too: 12% -> x 1.12 / x 0.88 / 0.12 (her live v0.969 margin ask: "figure 1.12
    # is in no fact" - it was 1 + 12%), and a percent of another of her figures (12% of 120 = 14.4)
    pcts = [p for p in ns if 0 < p <= 100]
    for p in pcts:
        out += [1 + p / 100, 1 - p / 100, p / 100]
    for i, a in enumerate(ns):
        for b in ns[i + 1:]:
            out += [a * b, a + b, abs(a - b)]
            if b:
                out.append(a / b)
            if a:
                out.append(b / a)
        for p in pcts:
            if p != a:
                out += [a * p / 100, a * (1 + p / 100), a * (1 - p / 100)]
    return out


def final_check(answer: str, user_text: str = "", facts: list[dict] | None = None, files: list[str] | None = None,
                not_done: list[str] | None = None, tools_ran: int = 0) -> dict[str, Any]:
    problems: list[str] = []
    checked: list[str] = []
    if tools_ran and facts is not None:
        checked.append("figures")
        pool = [float(f["value"]) for f in facts if isinstance(f.get("value"), (int, float))]
        pool += one_step([float(f["value"]) for f in facts
                          if f.get("source") == "her" and isinstance(f.get("value"), (int, float))])
        pool.append(100.0)     # v0.999.1 percentages add up to 100 (her live test: "figure 100" was a false alarm)
        for v in F.key_figures(answer or "", asked=user_text or ""):
            if not F.near(v, pool):
                problems.append(f"figure {int(v) if float(v).is_integer() else v} is in no fact the turn had")
    if files:
        checked.append("files")
        for p in files:
            if p.startswith("/") and not os.path.exists(p):
                problems.append(f"file {os.path.basename(p)} does not exist")
    if not_done:
        checked.append("not_done")
        low = (answer or "").lower()
        for item in not_done:
            words = [w for w in re.findall(r"\w{4,}", str(item).lower())][:3]
            if words and not any(w in low for w in words):
                problems.append(f"not said: {item}")
    return {"ok": not problems, "problems": problems[:8], "checked": checked}
