#!/usr/bin/env python3
"""v0.711.0 version ritual - SEEKH MANCH (a fresh build on the dev's v0.710.0 ARCHITECT OPUS tip; no
collision for this release - their chain rides verbatim as the Previous head).

Sweeps:
  1. main.py: APP_VERSION 0.710.0 -> 0.711.0 (SEEKH MANCH story head; their ARCHITECT OPUS clause and the
     whole deeper chain kept verbatim after 'Previous:')
  2. pubspec.yaml: 0.710.0+709 -> 0.711.0+710
  3. CLAUDE.md: current-version line re-headed v0.711.0 (their v0.710 line becomes the previous head)
  4. docs/HISTORY.md: the v0.711.0 SEEKH MANCH section prepended (newest-first; the file's head was
     v0.694 - the dev chain stopped writing HISTORY sections there, their sections stay at their anchors)
  5. docs/WORKLOG.md: the compact Task entry appended
  6. tests: pins 0.710.0+709 -> 0.711.0+710, bare 0.710.0 -> 0.711.0 (zero residual, house rule)
  7. registry pins: == 616 -> == 617 across the suite + the '+ 1 seekh_video' clause prepended to the
     pin comments (the two # comment variants get their clause appended in place). NOTE: the first run
     of step 7 inserted the clause WITH a closing quote, breaking 29 string literals; the repair
     (ritual_0711_finish.py's regex - drop the inserted quote where the original text follows directly)
     is part of this release's record, and the pattern below is the corrected form.
  8. console stamps ?v=0.710.0 -> ?v=0.711.0 (v2.html 23 + webstudio.html 4 + appstudio.html 5)
  9. the newest-story pin (test_v0475) moved to the v0.711.0 marker (SEEKH MANCH carries it)

NOT touched: the dev's scripts, WORKLOG's older entries, CLAUDE.md's frozen-zone block.
"""
from __future__ import annotations

import glob

ROOT = "server"
TESTS = f"{ROOT}/tests/*.py"
STATICS = [f"{ROOT}/app/static/console/v2.html", f"{ROOT}/app/static/console/webstudio.html",
           f"{ROOT}/app/static/console/appstudio.html"]

MY_STORY = (
    "SEEKH MANCH v0.711.0 = learn a way of working by WATCHING a video (owner: 'NOW LETS WORK ON A HOOLA "
    "AI AGENT THAT WILL SEE THE YOUTUBVIDEO FROM LINK, SHORTS, MP4 OR ANY VIDEO FORMAT. EXAMPLE FEELING "
    "THE FORM OR ANY WORK --- AI WILL LEARN THAT TRAIN ITSELF KEEP IN MEMORY AND IF TASK GIVEN RELATED TO "
    "IT IT WILL PERFORM SMOOTHLY' + 'GO' on the SEEKH MANCH plan): ONE new tool `seekh_video` (family "
    "seekh, tools 616 -> 617), NEW server/app/seekh.py (the bridge) + agent/seekh_tools.py + "
    "procedures.save_video; the eyes and the memories already ship and are only READ - youtube/"
    "service.gemini_video for links, the videoedit/brain inline-bytes pattern for attached files, the "
    "procedures memory (hint() injects it into every owner turn), the operator recipe box (find() reads it "
    "at every job start, Memory.save versions and backs up); the pipeline: classify (YouTube link / Shorts "
    "/ chat file_id / direct URL) -> perceive (Gemini, the way-of-working ask) -> distill (Claude through "
    "brain.think, strict JSON, one re-ask on validation problems then the honest salvage) -> store (a "
    "procedure row + an operator recipe DRAFT with runs=0 and a DRAFT note - a proven recipe is never "
    "clobbered) -> recall is automatic (hint + 'Recipes that may fit'), and the first good real run "
    "overwrites the draft with reality (from_trace); LAWS: every step carries its [m:ss] evidence or is "
    "demoted to gotchas, no literal personal value is ever kept (digits masked, values become "
    "{variables}), learned is not proven until one real run has worked, caps (seekh_max_per_day=20, file "
    "200 MB / 30 min) + the seekh_enabled kill switch; zero new pip, zero new keys, the frozen PC zone "
    "untouched; 32 offline tests test_v0711_seekh_manch.py; Previous: "
)

MY_CLAUSE = (
    '616 + 1 seekh_video (v0.711 SEEKH MANCH: the learn-from-video bridge tool, owner \'GO\' on the SEEKH '
    "MANCH plan). "
)

CLAUDE_ONE = ("learn a way of working from a video: watch it, distill the steps with [m:ss] evidence, keep "
              "them in the two shipped memories as unproven (a procedure row + an operator recipe draft); "
              "the first good real run makes them proven")

V0475_OLD = ("    assert 'ARCHITECT OPUS' in main and '0.710.0' in main  # the newest-story precedent "
             "(v0.710.0 carries the marker; older stories live in git history)")
V0475_NEW = ("    assert 'SEEKH MANCH' in main and '0.711.0' in main  # the newest-story precedent "
             "(v0.711.0 carries the marker; ARCHITECT OPUS rides the Previous chain; older stories live "
             "in git history)")

HISTORY_SECTION = """## v0.711.0 SEEKH MANCH — learn a way of working from a video (9 Nov 2026; owner: "NOW LETS WORK ON A HOOLA AI AGENT THAT WILL SEE THE YOUTUBVIDEO FROM LINK, SHORTS, MP4 OR ANY VIDEO FORMAT. EXAMPLE FEELING THE FORM OR ANY WORK --- AI WILL LEARN THAT TRAIN ITSELF KEEP IN MEMORY AND IF TASK GIVEN RELATED TO IT IT WILL PERFORM SMOOTHLY" + "GO" on the SEEKH MANCH plan)

She sends a video — a YouTube link, a Shorts, an MP4 she attached, a direct video URL — and says "isse
seekh lo". Hoola watches it, writes down the way of working as steps (each stamped with the [m:ss]
moment it was seen at), and keeps them in the two memories that already ship: "Seekhe hue kaam" (the
procedures list — `hint()` reads it into every owner turn) and, for website work, the computer
operator's recipe box as a **draft** (`find()` reads it at every job start). Weeks later a related ask
finds the learned way already suggested; the operator follows the draft as a guide, checking every step
against the live page — and the first real run that works **overwrites the draft with reality**
(`from_trace`, versioned, `.v1` backup kept). Learned is never claimed as proven until then.

- **THE BRIDGE, NOT A SECOND BRAIN** — the perception doors, the memories and the replay all shipped
  before this; SEEKH adds only the middle. ONE new tool `seekh_video` (family `seekh`, registry 616 →
  617). NEW `server/app/seekh.py` (~330 LOC: classify → perceive → distill → store, pure functions, lazy
  imports) + `agent/seekh_tools.py` + `procedures.save_video`. Zero new pip, zero new keys, the frozen
  PC zone untouched (pinned by test).
- **THE LAWS** (tested): every distilled step carries ≥1 `[m:ss]` evidence timestamp or is demoted to
  `gotchas`; no literal personal value survives anywhere (3+ digit runs masked, filled values become
  `{variables}` with hints — the same law as operator recipes and procedures); a draft recipe has
  `runs=0`, a DRAFT note, and never clobbers a proven recipe (it sits beside it as "<name> (video)");
  caps (20 watches/day, file ≤ 200 MB and ≤ 30 min, YouTube ≤ 3 h like `youtube_watch`) and the
  `seekh_enabled` kill switch (off = the tool errors honestly, the prompt bullet is family-gated away).
- **THE HONEST LADDER** — watched → distilled → *(one real run worked)* → "smoothly". The tool's reply
  always says "seekh liya — pehle ek baar sahi se chal ke dekhein" until `wins ≥ 1`; `unsure` and low
  confidence are surfaced, never hidden.
- **ROUTING** — admit `EXTRA_KEYS["seekh"]` + an INTENTS entry where the learn word must sit next to a
  video word, so "kya seekha" (the list), "banana sikhao" (the build family) and `hoola_seekha` (voice
  style) keep their own lanes (pinned by test).
- Tests: `test_v0711_seekh_manch.py` (32, zero network — the perception and distill doors patched at
  the module seam). Version ritual `scripts/ritual_0711.py`: pins → 0.711.0/+710 (zero residual), the
  31 registry pins `== 616` → `== 617` with the clause prepended, 32 console stamps, the newest-story
  pin moved to the SEEKH MANCH marker. Deploy: the owner's vps-ops dispatch; healthz must grep 0.711.0.


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

    # ---------- 1. main.py: the APP_VERSION re-head
    src = open(f"{ROOT}/app/main.py", encoding="utf-8").read()
    old_line = next(l for l in src.splitlines() if l.startswith("APP_VERSION = "))
    assert old_line.startswith('APP_VERSION = "0.710.0"   # ARCHITECT OPUS v0.710.0 = '), "their main head moved"
    their_clause = old_line[len('APP_VERSION = "0.710.0"   # '):]        # 'ARCHITECT OPUS v0.710.0 = ... [chain]'
    new_line = f'APP_VERSION = "0.711.0"   # {MY_STORY}{their_clause}'
    assert "SEEKH MANCH" in new_line and "ARCHITECT OPUS" in new_line
    assert new_line.index("SEEKH MANCH") < new_line.index("ARCHITECT OPUS")
    open(f"{ROOT}/app/main.py", "w", encoding="utf-8").write(src.replace(old_line, new_line))
    add("main", 1)

    # ---------- 2. pubspec
    add("pubspec", sweep("pubspec.yaml", [("version: 0.710.0+709", "version: 0.711.0+710")]))

    # ---------- 3. CLAUDE.md current-version line
    src = open("CLAUDE.md", encoding="utf-8").read()
    mark = "Current version: v0.710.0"
    their_claude = next(l for l in src.splitlines() if l.startswith(mark))
    new_claude = (f"Current version: v0.711.0 (pubspec 0.711.0+710; SEEKH MANCH v0.711.0 = {CLAUDE_ONE}"
                  f"); previous head " + their_claude[len("Current version: "):])
    open("CLAUDE.md", "w", encoding="utf-8").write(src.replace(their_claude, new_claude))
    add("claude", 1)

    # ---------- 4. HISTORY.md: prepend this release's section
    src = open("docs/HISTORY.md", encoding="utf-8").read()
    assert src.startswith("## v0.694.0 WEB CLONE"), "history head moved"
    open("docs/HISTORY.md", "w", encoding="utf-8").write(HISTORY_SECTION + src)
    add("history", 1)

    # ---------- 5. WORKLOG.md: the compact entry
    wl = open("docs/WORKLOG.md", encoding="utf-8").read()
    entry = (
        "\n---\nTask ID: v0.711.0 SEEKH MANCH\nAgent: Claude (web session)\n"
        "Ask: \"NOW LETS WORK ON A HOOLA AI AGENT THAT WILL SEE THE YOUTUBVIDEO FROM LINK, SHORTS, MP4 OR "
        "ANY VIDEO FORMAT ... AI WILL LEARN THAT TRAIN ITSELF KEEP IN MEMORY AND IF TASK GIVEN RELATED TO "
        "IT IT WILL PERFORM SMOOTHLY\" + \"GO\" on the SEEKH MANCH plan.\n"
        "Built: ONE tool seekh_video (616 -> 617, family seekh); server/app/seekh.py (classify -> Gemini "
        "perceive -> Claude distill -> store) + agent/seekh_tools.py + procedures.save_video; operator "
        "recipe DRAFTS through the public Memory.save format (runs=0, proven recipes never clobbered); "
        "evidence law, digit masking, value variables, day/size/length caps, seekh_enabled switch; "
        "routing words kept off 'kya seekha' / 'banana sikhao' / hoola_seekha; 32 offline tests.\n"
        "Deploy: the owner's vps-ops dispatch; healthz must grep 0.711.0.\n")
    open("docs/WORKLOG.md", "w", encoding="utf-8").write(wl.rstrip("\n") + "\n" + entry)
    add("worklog", 1)

    # ---------- 9. the newest-story pin first (before the bare sweep touches its numbers)
    add("v0475", sweep(f"{ROOT}/tests/test_v0475_console_frames.py", [(V0475_OLD, V0475_NEW)]))

    # ---------- 6-7. the test sweeps: versions, then the registry pins
    for f in sorted(glob.glob(TESTS)):
        n = sweep(f, [("0.710.0+709", "0.711.0+710"), ("0.710.0", "0.711.0")])
        if n:
            add("tests-version", n)
    for f in sorted(glob.glob(TESTS)):
        n = sweep(f, [('== 616, "', f'== 617, "{MY_CLAUSE}')])
        if n:
            add("tests-registry", n)
    n = sweep(f"{ROOT}/tests/test_v0663_kaan_w5.py",
              [("== 616", "== 617"),
               ("# W5 adds doors, not tools", "# +1 seekh_video (v0.711 SEEKH MANCH); W5 adds doors, not tools")])
    add("tests-registry", n)
    n = sweep(f"{ROOT}/tests/test_v0544_leads_scale.py",
              [("== 616", "== 617"),
               ("# the registry pin: no new tool", "# +1 seekh_video (v0.711 SEEKH MANCH); the registry pin")])
    add("tests-registry", n)

    # ---------- 8. console stamps
    for f in STATICS:
        add("stamps", sweep(f, [("?v=0.710.0", "?v=0.711.0")]))

    print("ritual_0711:", total)
    # zero-residual proof
    import subprocess
    for pat in ("0.710.0", "== 616"):
        out = subprocess.run(["grep", "-rn", pat, ROOT + "/tests", "--include=*.py"],
                             capture_output=True, text=True).stdout.strip()
        assert not out, f"residual {pat}:\n{out[:2000]}"
    print("zero residual: OK")


if __name__ == "__main__":
    main()
