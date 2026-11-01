"""Pure rules of the Daftar Sahayak: grades from percentages, the code-test harness, reading an answer-sheet CSV, and
the timetable solver (every class gets its periods, no teacher in two rooms at once, a subject at most N times a day)."""
from __future__ import annotations

import csv
import io
import json
import re
from typing import Any

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
# The 8-point scale schools commonly use with CBSE marks (A1 91-100 ... E below 33). It is the SCHOOL's report-card scale,
# not a board result; she can change it in settings when her school uses another.
GRADE_SCALE = [(91, "A1"), (81, "A2"), (71, "B1"), (61, "B2"), (51, "C1"), (41, "C2"), (33, "D"), (0, "E")]
NEVER = ["Marks 'final' sirf teacher ke sign-off se; Hoola ke jaanche marks suggestion hain",
         "Bachche (18 se kam) ke marks / hazri ka kaam guardian ki consent ke bina nahi",
         "Guardian ko message, report card ya alert sirf aapke tap se, aur sirf us bachche ke guardian ko",
         "WhatsApp par khud se bulk message nahi (official API ya aapka bheja draft)",
         "Report card mein sirf sign-off hue marks"]


def grade_of(pct: float, scale: list[tuple[int, str]] | None = None) -> str:
    for cut, g in (scale or GRADE_SCALE):
        if pct >= cut:
            return g
    return (scale or GRADE_SCALE)[-1][1]


def read_sheet(data: bytes) -> list[dict[str, Any]]:
    """A teacher's answer sheet CSV: a roll / name column, then one column per question (Q1, Q2 ...)."""
    text = data.decode("utf-8-sig", "replace")
    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) < 2:
        return []
    head = [h.strip() for h in rows[0]]
    roll_i = next((i for i, h in enumerate(head) if re.fullmatch(r"(?i)roll( ?no\.?| ?number)?|s\.? ?no", h)), None)
    name_i = next((i for i, h in enumerate(head) if re.fullmatch(r"(?i)(student )?name", h)), None)
    qcols = [(i, int(m.group(1))) for i, h in enumerate(head) for m in [re.fullmatch(r"(?i)q\.? ?(\d{1,3})", h)] if m]
    out = []
    for r in rows[1:]:
        if not any(c.strip() for c in r):
            continue
        ans = {n: (r[i].strip() if i < len(r) else "") for i, n in qcols}
        out.append({"roll": r[roll_i].strip() if roll_i is not None and roll_i < len(r) else "",
                    "name": r[name_i].strip() if name_i is not None and name_i < len(r) else "",
                    "answers": [ans.get(n, "") for n in range(1, (max(ans) if ans else 0) + 1)]})
    return out


def code_harness(student_code: str, tests: list[dict[str, Any]]) -> str:
    """A program for the sandbox: the student's code first (its own namespace), then each test as an expression whose
    value is compared to the expected one; prints one JSON line of results. Expected values are JSON."""
    lines = ["import json", "_SRC = " + json.dumps(student_code), "_ns = {}",
             "try:", "    exec(compile(_SRC, 'student.py', 'exec'), _ns)", "    _load = ''",
             "except Exception as e:", "    _load = type(e).__name__ + ': ' + str(e)[:200]",
             "_res = []", "_tests = json.loads(" + json.dumps(json.dumps(tests)) + ")",
             "for t in _tests:",
             "    if _load:",
             "        _res.append({'ok': False, 'why': 'code chala hi nahi: ' + _load}); continue",
             "    try:",
             "        got = eval(t['call'], _ns)",
             "        want = t.get('expected')",
             "        ok = (abs(got - want) <= 1e-6 * max(1, abs(want))) if isinstance(got, (int, float)) and isinstance(want, (int, float)) and not isinstance(got, bool) else got == want",
             "        _res.append({'ok': bool(ok), 'got': repr(got)[:120]})",
             "    except Exception as e:",
             "        _res.append({'ok': False, 'why': type(e).__name__ + ': ' + str(e)[:160]})",
             "print('__RESULT__' + json.dumps(_res))"]
    return "\n".join(lines)


def solve_timetable(spec: dict[str, Any]) -> tuple[dict, list[str]]:
    """spec: {days: [..], periods: n, max_same: 2, needs: [{class, subject, teacher, per_week}]}.
    Greedy with backtracking over (class, subject) demands, hardest first. Returns (grid, problems)."""
    days = spec.get("days") or DAYS[:6]
    periods = int(spec.get("periods") or 8)
    max_same = int(spec.get("max_same") or 2)
    needs = [dict(n) for n in spec.get("needs") or []]
    probs: list[str] = []
    classes = sorted({n["class"] for n in needs})
    for c in classes:
        tot = sum(int(n["per_week"]) for n in needs if n["class"] == c)
        if tot > len(days) * periods:
            probs.append(f"{c}: {tot} periods chahiye, hafte mein sirf {len(days) * periods} hain")
    teach: dict[str, int] = {}
    for n in needs:
        teach[n["teacher"]] = teach.get(n["teacher"], 0) + int(n["per_week"])
    for t, k in teach.items():
        if k > len(days) * periods:
            probs.append(f"{t}: {k} periods, hafte mein sirf {len(days) * periods} slot")
    if probs:
        return {}, probs
    grid = {c: {d: [""] * periods for d in days} for c in classes}
    busy: dict[tuple[str, str, int], str] = {}               # (teacher, day, period) -> class
    slots = [(d, p) for p in range(periods) for d in days]   # spread across days first
    units = []
    for n in sorted(needs, key=lambda n: -(teach[n["teacher"]] + int(n["per_week"]))):
        units += [n] * int(n["per_week"])
    steps = [0]

    def same_day(c, d, subj):
        return sum(1 for x in grid[c][d] if x.split(" / ")[0] == subj)

    def place(i: int) -> bool:
        if i == len(units):
            return True
        steps[0] += 1
        if steps[0] > 200_000:
            return False
        n = units[i]
        c, subj, t = n["class"], n["subject"], n["teacher"]
        order = sorted(slots, key=lambda s: (same_day(c, s[0], subj), s[1], days.index(s[0])))
        for d, p in order:
            if grid[c][d][p] or (t, d, p) in busy or same_day(c, d, subj) >= max_same:
                continue
            grid[c][d][p], busy[(t, d, p)] = f"{subj} / {t}", c
            if place(i + 1):
                return True
            grid[c][d][p] = ""
            del busy[(t, d, p)]
        return False

    if not place(0):
        return {}, ["Yeh shartein ek saath poori nahi hoti (teacher ek waqt do class mein, ya ek din mein ek subject bahut "
                    "baar). Periods ya max_same badhaiye, ya teacher badliye."]
    return grid, []
