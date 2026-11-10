#!/usr/bin/env python3
"""v0.718.0 version ritual - SEEKH MANCH ON THE CONSOLE re-ship after COLLISION #20 (built as
v0.716.0; their NAYA ROOP took 0.716.0 - the new logo + chat feel - and their FILE CARD SAHI took
0.717.0 while it sat built; REBASE PROTOCOL onto their 5964cdda7 tip: their code kept whole, my code
files carried byte-exact, the console files hand-merged [their 0.717.0 stamps + their mark.js kept,
my #v-seekh view + seekh.js tag re-applied on top], the version layer REBUILT at v0.718.0).

This ritual:
  1. main.py: APP_VERSION 0.717.0 -> 0.718.0 (SEEKH MANCH ON THE CONSOLE head with the collision
     preamble; their FILE CARD SAHI clause and whole chain kept verbatim after 'Previous:')
  2. pubspec.yaml: 0.717.0+716 -> 0.718.0+717
  3. CLAUDE.md: current-version line re-headed v0.718.0 (their v0.717 line becomes the previous head)
  4. docs/HISTORY.md: the v0.718.0 section prepended (on top of their v0.717.0 section)
  5. docs/WORKLOG.md: the compact Task entry appended
  6. tests: pins 0.717.0+716 -> 0.718.0+717, bare 0.717.0 -> 0.718.0 (zero residual)
  7. NO registry change: the console page adds NO tool (617 stays)
  8. console stamps ?v=0.717.0 -> ?v=0.718.0 (v2 25 [their mark.js + my seekh.js both in] +
     webstudio 4 + appstudio 5)
  9. the newest-story pin (test_v0475) moved to the SEEKH MANCH ON THE CONSOLE marker
 10. the console COUNT pins brought to the true 25: calm_brand sat at 22 (red on main since their
     chain stopped healing it), sessions sat at 23 (their mark.js already made it 24 on their own
     tree), frames sat at 24 - all now 25 (their mark.js + my seekh.js)
 11. my own files re-versioned v0.716 -> v0.718 (seekh.js, seekh_console.py, the v2.js/v2.css/
     employees.js comment tags) and the test renamed test_v0716 -> test_v0718 (born in the collision
     round, ships as v0718; the 0691/0713 precedent)
 12. py_compile over EVERY test file (the 0711 lesson: prove zero broken literals)
"""
from __future__ import annotations

import glob
import py_compile
import subprocess

ROOT = "server"
TESTS = f"{ROOT}/tests/*.py"
STATICS = [f"{ROOT}/app/static/console/v2.html", f"{ROOT}/app/static/console/webstudio.html",
           f"{ROOT}/app/static/console/appstudio.html"]

MY_STORY = (
    "SEEKH MANCH ON THE CONSOLE v0.718.0 (owner: 'NOW WE WILL DEVELOP A CONSOLE PAGE FOR IT - CHECK "
    "THE EXISTING CONSOLE DESIGN AND IN AI EMPLOYEE SECTION BUILD THE HOOLA AI VIDEO LEARNER. In that, "
    "a panel where user can load a video and HOOLA AI will see this and note in REALTIME. Once done, "
    "HOOLA AI will prepare a MEMORY for this. And IN THIS PAGE ONLY user will tell HOOLA to PERFORM "
    "THIS TASK NOW - then HOOLA will use HIS BROWSER for doing that task' + 'PERFECT START THE "
    "DEPLOYMENT' on the prototype shown in chat; built as v0.716.0, their NAYA ROOP took 0.716.0 and "
    "their FILE CARD SAHI took 0.717.0 while it sat built - REBASE PROTOCOL onto their 5964cdda7 tip, "
    "their code kept whole, the console files hand-merged [their 0.717.0 stamps + mark.js kept, my "
    "view + tag re-applied], all kept) = v0.713's learn-from-a-video gets its console page, the HOOLA "
    "AI Video Learner, opening from the AI Employees hub (a wide feature card beside 'Your team'; no "
    "new sidebar row - the v0.456 law). THE PANEL (static/console/seekh.js + the #v-seekh view): load "
    "a video three ways (a YouTube link / Shorts / direct URL typed, or a video FILE picked - it "
    "uploads through the chat file lane, 25 MB, and rides as a file_id); Watch & Learn starts the job "
    "and the page shows the REAL pipeline live - a five-step stepper (Pehchana -> Video dekh rahi "
    "hoon -> Notes likh rahi hoon -> Steps ban rahi hoon -> Memory) with each step's real elapsed "
    "stamp, and HOOLA KI NOTES, the perception text her Gemini eyes returned (the [m:ss] moments "
    "included) paced in word by word; every stage shown is a real on_stage boundary of seekh.watch, "
    "never a guess. When the watch lands, the MEMORY card shows what was kept: the title, "
    "website/other kind, the steps each with its :ss] evidence chip, preconditions, gotchas, unsure, "
    "the confidence meter and the honesty line (learned is NOT proven - the first real run verifies "
    "it); below, 'Seekhe hue kaam' lists every past watch with its recipe badge. PERFORM THIS TASK "
    "NOW lives on the SAME page: her instruction plus the kaam's variables become ONE honest chat "
    "turn through the same /api/conversations/{id}/messages the composer uses - the task runs through "
    "the agent, the computer operator reads the draft recipe at job start and drives ITS OWN browser, "
    "sending still asks her tap; the panel stays put, shows the sent state and offers Live activity + "
    "Chat. SERVER: NEW seekh_console.py (/api/seekh/console/*: POST watch -> job id, GET progress?id= "
    "the 1.2 s pulse, GET watches the memory list with caps; key-protected, tenant-scoped, one watch "
    "at a time per tenant - a second start ADOPTS the running job, a page reload re-adopts it; "
    "in-process ring, a restart drops jobs but the learned kaam lives in the two real memories) + "
    "seekh.watch grew ONLY an additive on_stage callback (classify/fetch/notes/distill_start/distill/"
    "memory/done; a no-op for the tool and every existing test, a broken sink never breaks the "
    "watch). No new tool (registry stays 617), no new pip, no new keys, no new settings; the frozen "
    "PC zone untouched (the lane never imports the operator stack, pinned by test). Tests: "
    "test_v0718_seekh_console.py (25: lane guards, the job lifecycle with the doors patched at the "
    "module seam, stage order, adoption, honest errors, the console files, the pins; born as v0716 "
    "in the collision round, ships as v0718) + the v0713 suite re-run green; Previous: "
)

CLAUDE_ONE = ("the HOOLA AI Video Learner console page (AI Employees section): load a video, watch "
              "Hoola take notes in realtime, see the memory it prepares, and Perform-this-task-NOW on "
              "the same page - one chat turn, the operator's own browser")

V0475_OLD_MARK = "'FILE CARD SAHI'"
V0475_NEW_LINE = ("    assert 'SEEKH MANCH ON THE CONSOLE' in main and '0.718.0' in main  # the "
                  "newest-story precedent (v0.718.0 carries the marker; FILE CARD SAHI rides the "
                  "Previous chain; older stories live in git history)")

HISTORY_SECTION = """## v0.718.0 SEEKH MANCH ON THE CONSOLE — the HOOLA AI Video Learner page (9 Nov 2026; owner: "NOW WE WILL DEVELOP A CONSOLE PAGE FOR IT — CHECK THE EXISTING CONSOLE DESIGN AND IN AI EMPLOYEE SECTION BUILD THE HOOLA AI VIDEO LEARNER. In that, a panel where user can load a video and HOOLA AI will see this and note in REALTIME. Once done, HOOLA AI will prepare a MEMORY for this. And IN THIS PAGE ONLY user will tell HOOLA to PERFORM THIS TASK NOW — then HOOLA will use HIS BROWSER for doing that task" + "PERFECT START THE DEPLOYMENT" on the prototype shown in chat; built as v0.716.0, their NAYA ROOP took 0.716.0 and their FILE CARD SAHI took 0.717.0 while it sat built — REBASE PROTOCOL onto their tip, all kept)

v0.713 taught Hoola to learn a way of working from a video (SEEKH MANCH, the `seekh_video` tool). This
release gives that power its own page on the web console: **AI Employees → HOOLA AI Video Learner**.
She loads a video — a YouTube link, a Shorts, a direct URL, or a file she picks (≤ 25 MB through the
chat lane) — presses **Watch & Learn**, and watches Hoola watch: a five-step stepper tracks the real
pipeline (Pehchana → Video dekh rahi hoon → Notes likh rahi hoon → Steps ban rahi hoon → Memory) with
real elapsed stamps, and **HOOLA KI NOTES** fills with exactly what her Gemini eyes returned — the
[m:ss] moments included — paced in word by word. Every stage the page shows is a real `on_stage`
boundary of `seekh.watch`, never a guess.

- **THE MEMORY CARD** — when the watch lands: the title, website/other-work kind, the steps each with
  its `:ss]` evidence chip, preconditions, gotchas, what she is unsure about, the confidence meter, and
  the honesty line — *learned is NOT proven; the first real run verifies it*. Below, **Seekhe hue
  kaam** lists every past watch with its recipe badge.
- **PERFORM THIS TASK NOW — ON THE SAME PAGE** — her instruction (the learned kaam's fill-in variables
  offered as hints) becomes ONE honest chat turn through the same `/api/conversations/{id}/messages`
  the composer uses. The task runs through the agent; the computer operator reads the video-learned
  **draft recipe** at job start and drives its **own browser**, checking every step against the live
  page; anything that sends or submits still waits for her tap. The panel stays put, shows the sent
  state, and offers Live activity + Chat.
- **THE LANE IS THIN** — NEW `server/app/seekh_console.py` (`/api/seekh/console/*`: `POST /watch` → job
  id, `GET /progress?id=` the 1.2 s pulse, `GET /watches` the memory list with caps; key-protected,
  tenant-scoped, one watch at a time per tenant — a second start **adopts** the running job, a page
  reload re-adopts it; an in-process ring, so a restart drops jobs but the learned kaam lives in the
  two real memories). `seekh.watch` grew ONLY an additive `on_stage` callback (a no-op for the tool and
  every existing test; a broken sink never breaks the watch). **PERFORM is deliberately not an
  endpoint** — the panel composes a chat turn, so the operator lane stays the only doer (pinned by
  test).
- **NO NEW ORGANS** — no new tool (registry stays 617), no new pip, no new keys, no new settings; the
  frozen PC zone untouched (the lane never imports the operator stack, pinned by test). The console
  files: `seekh.js` (the panel), the `#v-seekh` view in `v2.html`, the hub card in `employees.js`, the
  `send`/`upload` helpers in `v2.js` (both ride the chat doors — no new server surface), the styles in
  `v2.css`.
- Tests: `test_v0718_seekh_console.py` (25: lane guards 401/422/403/404, the job lifecycle with the
  perception/distill doors patched at the module seam, stage order, adoption of the running job, honest
  errors, the console file pins, the version pins; born as v0716 in the collision round, ships as
  v0718) and the v0713 suite re-run green (40 — the tool path unchanged). The console COUNT pins
  brought to the true 25 (their mark.js + this release's seekh.js): calm_brand healed from a stale 22,
  sessions from 23, frames from 24. Deploy: the owner's vps-ops dispatch; healthz must grep 0.718.0.


"""


def sweep(path: str, pairs: list[tuple[str, str]]) -> int:
    try:
        src = open(path, encoding="utf-8").read()
    except FileNotFoundError:
        print("  MISSING (skipped):", path)
        return 0
    n = 0
    for old, new in pairs:
        c = src.count(old)
        if c:
            src = src.replace(old, new)
            n += c
    if n:
        open(path, "w", encoding="utf-8").write(src)
    return n


def main() -> None:
    total: dict[str, int] = {}

    def add(key: str, n: int) -> None:
        total[key] = total.get(key, 0) + n

    # ---------- 11. my own files first: re-version v0.716 -> v0.718 (before the global sweeps)
    for f in (f"{ROOT}/app/seekh_console.py", f"{ROOT}/app/seekh.py", f"{ROOT}/app/static/console/seekh.js",
              f"{ROOT}/app/static/console/v2.js", f"{ROOT}/app/static/console/v2.css",
              f"{ROOT}/app/static/console/employees.js", f"{ROOT}/tests/test_v0718_seekh_console.py"):
        add("my-files", sweep(f, [("v0.716 SEEKH MANCH", "v0.718 SEEKH MANCH"),
                                  ("v0.716: the console lane", "v0.718: the console lane"),
                                  ("v0.716 the HOOLA AI Video Learner", "v0.718 the HOOLA AI Video Learner"),
                                  ("v0.716 SEEKH MANCH ON THE CONSOLE", "v0.718 SEEKH MANCH ON THE CONSOLE"),
                                  ("v0.716 the Video Learner", "v0.718 the Video Learner"),
                                  ("// v0.716 the", "// v0.718 the"),
                                  ("v0.716 the Video", "v0.718 the Video"),
                                  ("v0.716 a video folder", "v0.718 a video folder")]))

    # ---------- 1. main.py: the APP_VERSION re-head
    src = open(f"{ROOT}/app/main.py", encoding="utf-8").read()
    old_line = next(l for l in src.splitlines() if l.startswith("APP_VERSION = "))
    assert old_line.startswith('APP_VERSION = "0.717.0"   # FILE CARD SAHI v0.717.0'), "their main head moved"
    their_clause = old_line[len('APP_VERSION = "0.717.0"   # '):]
    new_line = f'APP_VERSION = "0.718.0"   # {MY_STORY}{their_clause}'
    assert "SEEKH MANCH ON THE CONSOLE" in new_line and "FILE CARD SAHI" in new_line
    assert new_line.index("SEEKH MANCH ON THE CONSOLE") < new_line.index("FILE CARD SAHI")
    open(f"{ROOT}/app/main.py", "w", encoding="utf-8").write(src.replace(old_line, new_line))
    add("main", 1)

    # ---------- 2. pubspec
    add("pubspec", sweep("pubspec.yaml", [("version: 0.717.0+716", "version: 0.718.0+717")]))

    # ---------- 3. CLAUDE.md current-version line
    src = open("CLAUDE.md", encoding="utf-8").read()
    their_claude = next(l for l in src.splitlines() if l.startswith("Current version: v0.717.0"))
    new_claude = (f"Current version: v0.718.0 (pubspec 0.718.0+717; SEEKH MANCH ON THE CONSOLE v0.718.0 = "
                  f"{CLAUDE_ONE}); previous head " + their_claude[len("Current version: "):])
    open("CLAUDE.md", "w", encoding="utf-8").write(src.replace(their_claude, new_claude))
    add("claude", 1)

    # ---------- 4. HISTORY.md: prepend this release's section
    src = open("docs/HISTORY.md", encoding="utf-8").read()
    assert src.startswith("## v0.717.0 FILE CARD SAHI"), "history head moved"
    open("docs/HISTORY.md", "w", encoding="utf-8").write(HISTORY_SECTION + src)
    add("history", 1)

    # ---------- 5. WORKLOG.md: the compact entry
    wl = open("docs/WORKLOG.md", encoding="utf-8").read()
    entry = (
        "\n---\nTask ID: v0.718.0 SEEKH MANCH ON THE CONSOLE (re-ship; built as 0.716, their NAYA ROOP "
        "took 0.716 and FILE CARD SAHI took 0.717 - REBASE PROTOCOL onto their 5964cdda7 tip, all kept)\n"
        "Agent: Claude (web session)\n"
        "Ask: \"NOW WE WILL DEVELOP A CONSOLE PAGE FOR IT ... IN AI EMPLOYEE SECTION BUILD THE HOOLA AI "
        "VIDEO LEARNER ... load a video and HOOLA AI will see this and note in REALTIME ... prepare a "
        "MEMORY ... IN THIS PAGE ONLY user will tell HOOLA to PERFORM THIS TASK NOW - then HOOLA will "
        "use HIS BROWSER\" + \"PERFECT START THE DEPLOYMENT\" on the prototype shown in chat.\n"
        "Built: the #v-seekh console view + seekh.js (load video -> live five-step stepper + HOOLA KI "
        "NOTES paced in -> the memory card -> Perform-this-task-NOW on the same page through one chat "
        "turn, the operator's own browser); the AI Employees hub card (employees.js); NEW "
        "server/app/seekh_console.py (/api/seekh/console/*: watch job + progress pulse + watches list; "
        "key-protected, tenant-scoped, one watch at a time, adoption on reload); seekh.watch grew only "
        "an additive on_stage callback (no-op for the tool and the old tests); no new tool (617), no "
        "new pip/keys/settings; frozen PC zone untouched (pinned). 25 tests (born v0716, ships v0718) + "
        "v0713 re-run 40/40; live browser-verified before the push (panel walk, honest 422 + the "
        "no-Gemini error surfaced in the notes area, zero page errors).\n"
        "Deploy: the owner's vps-ops dispatch; healthz must grep 0.718.0.\n")
    open("docs/WORKLOG.md", "w", encoding="utf-8").write(wl.rstrip("\n") + "\n" + entry)
    add("worklog", 1)

    # ---------- 9. the newest-story pin first (before the bare sweep touches its numbers)
    p = f"{ROOT}/tests/test_v0475_console_frames.py"
    src = open(p, encoding="utf-8").read()
    old_line = next(l for l in src.splitlines() if V0475_OLD_MARK in l and "newest-story" in l)
    src = src.replace(old_line, V0475_NEW_LINE)
    open(p, "w", encoding="utf-8").write(src)
    add("v0475", 1)

    # ---------- 6. the version sweeps
    for f in sorted(glob.glob(TESTS)):
        n = sweep(f, [("0.717.0+716", "0.718.0+717"), ("0.717.0", "0.718.0")])
        if n:
            add("tests-version", n)

    # ---------- 10. the console COUNT pins brought to the true 25 (their mark.js + my seekh.js)
    add("calm-brand", sweep(f"{ROOT}/tests/test_v0240_calm_brand.py",
                            [('count(f"?v={APP_VERSION}") == 22', 'count(f"?v={APP_VERSION}") == 25')]))
    add("sessions", sweep(f"{ROOT}/tests/test_v0194_sessions.py",
                          [("len(app) == 23", "len(app) == 25")]))
    add("frames", sweep(f"{ROOT}/tests/test_v0475_console_frames.py",
                        [("s.count(f'v={APP_VERSION}') == 24", "s.count(f'v={APP_VERSION}') == 25")]))

    # ---------- 8. console stamps
    for f in STATICS:
        add("stamps", sweep(f, [("?v=0.717.0", "?v=0.718.0")]))

    print("ritual_0718:", total)

    # ---------- 12. the proofs: zero residual + every test file compiles
    for pat in ("0.717.0", "0.716.0"):
        out = subprocess.run(["grep", "-rn", pat, ROOT + "/tests", "--include=*.py"],
                             capture_output=True, text=True).stdout.strip()
        assert not out, f"residual {pat}:\n{out[:2000]}"
    print("zero residual in tests: OK")
    broken = []
    for f in glob.glob(f"{ROOT}/tests/*.py"):
        try:
            py_compile.compile(f, doraise=True)
        except py_compile.PyCompileError as e:
            broken.append((f, str(e).splitlines()[0][:100]))
    assert not broken, broken
    print("py_compile all test files: OK")


if __name__ == "__main__":
    main()
