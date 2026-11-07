#!/usr/bin/env python3
"""v0.670.0 KAAN W6 re-version ritual - the REBASE PROTOCOL's second half.

W6 built as 0.667.0; their console-stamp + PREMIUM STUDIO took 0.667.0, DUNIYA MANCH 0.668.0
and HOOLA AURA 0.669.0 while W6 sat built - REBASE PROTOCOL, rebuilt fresh on their 0d89877bc
tip, all their work kept. This sweep re-applies the version layer coherently:
0.668.0/0.669.0 -> 0.670.0 (+675 -> +676, my built-as 0.667.0 test file included) across ALL
test files, pubspec, and the APP_VERSION story (their HOOLA AURA story spliced into the
Previous chain untouched). Registry stays 607 - W6 adds dials, not tools; the kaan enum stays 18.
"""
import re
from pathlib import Path

ROOT = Path("/home/z/my-project/santosh-app")
NEW, NEW_BUILD = "0.670.0", "+676"

# ---------------------------------------------------------------- 1. the test-file sweep
changed = []
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    text = f.read_text(encoding="utf-8")
    orig = text
    for old in ("0.666.0", "0.667.0", "0.668.0", "0.669.0", "+672", "+673", "+674", "+675"):
        text = text.replace(old, NEW if old.startswith("0.") else NEW_BUILD)
    if text != orig:
        f.write_text(text, encoding="utf-8")
        changed.append(f.name)
print(f"tests swept: {len(changed)} files")

# ---------------------------------------------------------------- 2. pubspec
pub = ROOT / "pubspec.yaml"
text = pub.read_text(encoding="utf-8")
text = re.sub(r"version: 0\.\d{3}\.0\+\d{3}", f"version: {NEW}{NEW_BUILD}", text, count=1)
pub.write_text(text, encoding="utf-8")
print("pubspec ->", f"{NEW}{NEW_BUILD}")

# ---------------------------------------------------------------- 3. the APP_VERSION story splice
main = ROOT / "server" / "app" / "main.py"
lines = main.read_text(encoding="utf-8").split("\n")
their36 = lines[35]
assert their36.startswith('APP_VERSION = "0.669.0"'), "line 36 is not their AURA story"
# their story: everything after "# v0.669.0 " (chain included, kept verbatim below my head)
t_marker = their36.index("# v0.669.0 ") + len("# ")
their_story = their36[t_marker:]

REBASE_NOTE = ("built as 0.667.0; their console-stamp + PREMIUM STUDIO took 0.667.0, DUNIYA MANCH 0.668.0 and "
               "HOOLA AURA 0.669.0 while W6 sat built - REBASE PROTOCOL, rebuilt fresh on their 0d89877bc tip, "
               "ALL their work kept intact, the version layer re-applied coherently 0.669.0/+675 -> 0.670.0/+676, "
               "ritual_0670.py")
body = their_story  # placeholder to keep the variable naming clear below

MY_HEAD = (
    f'APP_VERSION = "{NEW}"   # v0.670.0 KAAN W6 - HISAAB AUR SAFAI ({REBASE_NOTE}) '
    '(owner: "W6 (quotas + retention -> unlocks real voiceprint diarization) -- start" on the kaan plan - Wave W6 '
    'of the WhisperAI feed, after W0 v0.601.0, W1 v0.613.0, W2 v0.619.0, W3 v0.639.0, W4 v0.659.0 and W5 v0.666.0 '
    'proved live on the box): the accountability layer her audio runs on, then the unlock it buys. '
    'NEW server/app/kaan/limits.py - month_usage (finished kn_ duration_s per calendar month, per tenant; a live '
    'session\'s seconds count ONCE, by the kn_ row its stop writes - never double-counted), check_quota_file (the '
    'ffprobe estimate runs BEFORE the engine spends; duration 0.0 - ffprobe absent - never blocks, the finished '
    'row still counts honestly), check_quota_live_start (no new session once the cap is hit), retention_sweep '
    '(kn_ rows past KAAN_RETENTION_DAYS go - pinned rows survive, the column W0 baked for exactly this; live '
    'sessions past the cutoff go WITH their spine PCM files; the last sweep is surfaced in status), '
    'voiceprint_ready (the unlock guard). NEW server/app/kaan/voiceprint.py - diarize=voiceprint at transcribe '
    'time: DI.cut_turns cuts the timeline, each turn\'s audio slice is embedded ONCE and scored against HER '
    'enrolled Awaaz Pehchaan prints through voiceid.service (the identify threshold+margin law, nothing '
    'invented, nothing stored twice); sure matches get the person\'s name, unsure turns stay unnamed - no '
    'guessing; a technical failure degrades to an honest note and the transcript survives; the guard refuses '
    'BEFORE the engine burns a transcription (KAAN_VOICEPRINT=1 AND KAAN_RETENTION_DAYS>0 - voiceprints are '
    'biometric, matching audio with them is only allowed where retention is bounded). pause_turns also rides '
    'fresh audio now (the W1 law on new recordings). WIRING: service.transcribe_file grows the diarize param '
    '(quota before the engine, voiceprint guard before the engine, speakers stored into row.speakers + named in '
    'the note); live.start refuses at the cap; api.py transcribe grows the diarize Form field (the honest 400 '
    'carries the service\'s own words); kaan_tools schema grows the diarize enum (18 actions UNCHANGED, registry '
    '607 UNCHANGED - W6 adds dials, not tools); worker.py kaan_jobs (daily throttle, mirrors eventlog_jobs) '
    'calls the sweep. CONFIG: kaan_quota_audio_min=0, kaan_retention_days=0, kaan_voiceprint=False - all default '
    'OFF, her box keeps everything until she says otherwise. ZERO new tables, ZERO new pip. The W6 plan\'s third '
    'leg - a fresh read of whisperai.com\'s live prices (7 Nov 2026): Free $0 (5 min/mo), Premium $14.99/mo '
    '(120 min, rollover to 360), Business Pro $24.99/mo unlimited, Enterprise $75/mo (5 seats), Developer API '
    '$99/mo (10k API min); their single-file cap 10 h, live sessions 12 h, MCP connector is a paid-tier feature '
    '- kaan\'s answer stays local-first: no per-minute meter at all unless SHE sets the cap, same 5 GB ceiling, '
    '2 h live sessions, MCP/HTTP doors free, and the one thing none of their tiers sell: speaker names from '
    'voiceprints she enrolled and owns. Tests: NEW test_v0667_kaan_w6.py (26, the file name keeps the '
    'first-build number, the v0.566 precedent; zero network, zero torch, scripted engine + the seams - '
    '_duration_of, VP._people, VP._identify, VS.pcm16k - the W5 house-safe patching lesson): quota (default '
    'unlimited, finished-rows-only metering, over-cap refusal naming the reset date, within-cap pass, '
    'ffprobe-absent honesty, live start at cap + counted once at stop), retention (0 = honest no-op, old '
    'unpinned swept + fresh kept, pinned survive, spine files removed, last-sweep block, worker daily throttle), '
    'voiceprint (off refuses naming the switch, needs bounded retention, needs enrolment, names sure turns only '
    '+ persists + notes, technical failure keeps the transcript, pause_turns fresh, unknown value refuses), '
    'surfaces (status blocks, HTTP diarize param + honest 400, pinned in rows, registry/enum untouched, MCP door '
    'rides the same KS, no new tables, APP_VERSION). Green on the merged tree: kaan chain W0-W6 (153) + their '
    'DUNIYA MANCH + AURA suites re-run as the merge proof; the soorat tone red is WORKTREE-PROVEN pre-existing '
    '(_TonedCall.conv - not W6\'s lane). ritual_0670.py swept the version layer 0.669.0 -> 0.670.0 (+676) '
    'across the test files (their 0.669.0 layer, my built-as 0.667.0 file included), ZERO residual; CLAUDE.md + '
    'HISTORY + WORKLOG mirrors on top of their entries. Server-only deploy = owner\'s vps-ops dispatch; desktop '
    'untouched - old APKs keep working; Mera PC freeze respected. NOT VERIFIED live: the first '
    'quota/retention/voiceprint checks on the VPS - the bake block rides the deploy. Previous: '
)
lines[35] = MY_HEAD + their_story
main.write_text("\n".join(lines), encoding="utf-8")
print("APP_VERSION story: W6 0.670.0 head + their HOOLA AURA chain verbatim")

# ---------------------------------------------------------------- 4. the mirrors
h = ROOT / "docs" / "HISTORY.md"
t = h.read_text(encoding="utf-8")
sec = ("## v0.670.0 KAAN W6 — HISAAB AUR SAFAI (7 Nov 2026, built as 0.667.0; their console-stamp + PREMIUM "
       "STUDIO 0.667.0, DUNIYA MANCH 0.668.0, HOOLA AURA 0.669.0 - REBASE PROTOCOL, rebuilt on their tip, all kept)\n\n"
       "The accountability layer her audio runs on, then the unlock it buys — quotas + retention -> real voiceprint diarization.\n\n"
       "- **NEW server/app/kaan/limits.py** — `month_usage` (finished kn_ duration_s per calendar month; a live session's seconds count ONCE, by the kn_ row its stop writes), `check_quota_file` (ffprobe estimate BEFORE the engine spends; 0.0 never blocks), `check_quota_live_start` (no new session at cap), `retention_sweep` (kn_ rows past KAAN_RETENTION_DAYS go, **pinned survive** — the column W0 baked for this; live sessions + spine PCM files go with the cutoff), `voiceprint_ready` (the unlock guard). status() grows usage / retention / voiceprint blocks (English notes).\n"
       "- **NEW server/app/kaan/voiceprint.py** — `diarize=voiceprint` at transcribe time: pause-cut turns, each turn's audio slice embedded once and scored against HER enrolled Awaaz Pehchaan prints through voiceid.service (identify's threshold+margin law; nothing invented, nothing stored twice); sure matches get the person's name, unsure turns stay unnamed — no guessing; a technical failure degrades to an honest note, the transcript survives; the guard refuses BEFORE the engine burns a run (KAAN_VOICEPRINT=1 AND KAAN_RETENTION_DAYS>0 — voiceprints are biometric, matching audio with them is only allowed where retention is bounded). `pause_turns` also rides fresh audio now.\n"
       "- **Wiring** — service.transcribe_file grows the `diarize` param (quota before engine, guard before engine, speakers stored + named in the note); live.start refuses at the cap; api.py transcribe grows the diarize Form field (honest 400 in the service's own words); kaan_tools schema grows the diarize enum (18 actions, registry 607 — UNCHANGED); worker.py `kaan_jobs` (daily throttle, mirrors eventlog_jobs) calls the sweep. Config: `kaan_quota_audio_min=0`, `kaan_retention_days=0`, `kaan_voiceprint=False` — all default OFF. ZERO new tables, ZERO new pip.\n"
       "- **The whisperai.com fresh price read (7 Nov 2026)** — Free $0 (5 min/mo), Premium $14.99/mo (120 min, rollover to 360), Business Pro $24.99/mo unlimited, Enterprise $75/mo (5 seats, $15/extra seat), Developer API $99/mo (10k API min, real-time + pre-recorded, translation API 86 languages); single-file cap 10 h, live sessions 12 h, MCP connector is a paid-tier feature. Kaan's answer stays local-first: no per-minute meter unless SHE sets the cap, same 5 GB ceiling, 2 h live sessions, MCP/HTTP doors free, and the one thing no tier sells — speaker names from voiceprints she enrolled and owns.\n"
       "- Tests: **test_v0667_kaan_w6.py (26, name keeps the first-build number)** — quota, retention, voiceprint, surfaces, pins; kaan chain W0–W6 green on the merged tree with their suites re-run as the merge proof.\n\n")
h.write_text(sec + t, encoding="utf-8")

w = ROOT / "docs" / "WORKLOG.md"
t = w.read_text(encoding="utf-8")
lines_w = t.split("\n")
idx = next(i for i, l in enumerate(lines_w) if l.startswith("Task ID:"))
lines_w.insert(idx, "Task ID: v0.670.0 KAAN W6 HISAAB AUR SAFAI (built as 0.667.0; their 0.667.0/0.668.0/0.669.0 took the version numbers while W6 sat built - REBASE PROTOCOL, rebuilt on their tip, all kept)\n")
w.write_text("\n".join(lines_w), encoding="utf-8")

c = ROOT / "CLAUDE.md"
t = c.read_text(encoding="utf-8")
anchor = "- v0.669 "
if anchor not in t:
    anchor = "- v0.668 "
i = t.index(anchor)
bullet = ("- v0.670 KAAN W6 HISAAB AUR SAFAI (built as 0.667.0, rebased on their 0.669.0): the accountability layer her audio runs on — "
          "kaan_quota_audio_min (monthly per-tenant audio-minutes cap, ffprobe-estimated BEFORE the engine spends, live start refuses at cap, meter counts finished kn_ rows only) "
          "+ kaan_retention_days (daily worker sweep, pinned rows survive, live spines go with their sessions) -> the unlock: diarize=voiceprint names speakers from her enrolled Awaaz Pehchaan prints "
          "(voiceid threshold law, sure matches only, guard refuses BEFORE the engine unless KAAN_VOICEPRINT=1 AND retention is bounded); status grows usage/retention/voiceprint blocks; "
          "diarize enum in the tool/HTTP schema; 18 actions + registry 607 UNCHANGED; all three dials default OFF; zero new tables/pip; 26 tests; + the fresh whisperai.com price read (docs).\n")
t = t[:i] + bullet + t[i:]
c.write_text(t, encoding="utf-8")
print("mirrors written on top of their entries")

# ---------------------------------------------------------------- 5. residual check
residual = []
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    text = f.read_text(encoding="utf-8")
    if any(v in text for v in ("0.666.0", "0.667.0", "0.668.0", "0.669.0")):
        residual.append(f.name)
print("residual 0.666-0.669 in tests:", residual or "ZERO")
