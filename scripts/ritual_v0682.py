#!/usr/bin/env python3
"""v0.682.0 KAAN W6 FIX version ritual.

The first live W6 check on the VPS crashed at kaan/status - limits.voiceprint_ready unpacked
ok, why = VE.available() but the pre-existing voiceid engine contract is a PLAIN BOOL
(available() -> bool; only the kaan engine's EN.available() is the tuple pair), so the live
process died on TypeError: cannot unpack non-iterable bool object while the W6 suite stayed
195/195 green - its three engine patches assumed the same wrong tuple shape. THE FIX makes W6
consume their lane as-is (the house law: their base kept whole, nothing invented).

This sweep re-applies the version layer 0.681.0/+680 -> 0.682.0/+681 across ALL test files
(version tokens + the pubspec-string pins), pubspec, the console cache-buster stamps (the
test_v0179 law: stamps == APP_VERSION), the APP_VERSION story (my FIX head, their KALA chain
verbatim in Previous), and the three mirrors (HISTORY / WORKLOG / CLAUDE.md). Registry stays
609 - the fix adds no tools. Zero residual expected on exit.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_BUILD = "0.682.0", "+681"
OLD_V, OLD_BUILD = "0.681.0", "+680"

# ---------------------------------------------------------------- 1. the test-file sweep
changed, tokens = [], 0
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    text = f.read_text(encoding="utf-8")
    orig = text
    tokens += len(re.findall(rf"\b{re.escape(OLD_V)}\b", text))
    text = text.replace(OLD_V, NEW)
    text = re.sub(rf"\+{re.escape(OLD_BUILD[1:])}\b", NEW_BUILD, text)
    if text != orig:
        f.write_text(text, encoding="utf-8")
        changed.append(f.name)
print(f"tests swept: {len(changed)} files ({tokens} version tokens)")

# ---------------------------------------------------------------- 2. pubspec
pub = ROOT / "pubspec.yaml"
text = pub.read_text(encoding="utf-8")
text, n = re.subn(r"version: 0\.\d+\.\d+\+\d+", f"version: {NEW}{NEW_BUILD}", text, count=1)
pub.write_text(text, encoding="utf-8")
print("pubspec ->", f"{NEW}{NEW_BUILD}" if n else "!! PATTERN MISS")

# ---------------------------------------------------------------- 3. the console cache-busters (the v0179 law)
stamped = 0
for f in sorted((ROOT / "server" / "app" / "static" / "console").glob("*")):
    if f.suffix not in (".html", ".htm"):
        continue
    text = f.read_text(encoding="utf-8")
    new_text, n = re.subn(rf"\?v={re.escape(OLD_V)}", f"?v={NEW}", text)
    if n:
        f.write_text(new_text, encoding="utf-8")
        stamped += n
print(f"console cache-busters: {stamped} stamps -> {NEW}")

# ---------------------------------------------------------------- 4. the APP_VERSION story splice
main = ROOT / "server" / "app" / "main.py"
lines = main.read_text(encoding="utf-8").split("\n")
their = lines[35]
assert their.startswith(f'APP_VERSION = "{OLD_V}"'), "line 36 is not the KALA story"
t_marker = their.index(f"# v{OLD_V}") + len("# ")
their_story = their[t_marker:]

MY_HEAD = (
    f'APP_VERSION = "{NEW}"   # v{NEW}: KAAN W6 FIX - the unlock guard\'s engine seam made honest '
    '(owner: "W6 (quotas + retention -> unlocks real voiceprint diarization) -- start" - the first '
    'live W6 check on the VPS crashed at kaan/status: limits.voiceprint_ready did '
    'ok, why = VE.available() but the pre-existing voiceid engine contract is a PLAIN BOOL '
    'available() -> bool (only the kaan engine\'s EN.available() is the tuple pair) - TypeError: '
    'cannot unpack non-iterable bool object, so NOT ONE W6 number surfaced; the W6 suite stayed '
    '195/195 green because its three engine patches assumed the same wrong tuple shape - the tests '
    'inherited the bug, the classic seam lesson) - THE FIX: W6 adapts to THEIR lane as-is (the '
    'house law: their base kept whole, nothing invented) - limits.py consumes the bool and composes '
    'the honest why itself (sherpa_onnx or the CAM++/TitaNet speaker models in voiceid_models_dir '
    'are missing), the voiceid lane untouched (main.py feature flag, voiceid service status + mode '
    'guard keep their bool), the three W6 test patches healed to the real contract lambda: True, '
    'NEW regression test speaking the REAL unpatched contract (isinstance bool + voiceprint_ready '
    'returns (False, why) with nothing patched - the test that would have caught the crash), quota '
    '+ retention paths untouched. Version ritual: ritual_v0682.py swept 0.681.0 -> 0.682.0 (+681) '
    'across the test files (version tokens + the pubspec-string pins), pubspec, the console '
    'cache-buster stamps (the v0179 law: stamps == APP_VERSION), ZERO registry change (609 stands - '
    'W6 FIX adds no tools), ZERO pip; CLAUDE.md current-version line + the Current state bullet, '
    'docs/HISTORY.md section, docs/WORKLOG.md task. Server-only deploy = owner\'s vps-ops dispatch; '
    'desktop untouched - old APKs keep working. NOT VERIFIED live: the W6 retest on the VPS rides '
    'this deploy (the same single-line check, now past status). Previous: '
)
lines[35] = MY_HEAD + their_story
main.write_text("\n".join(lines), encoding="utf-8")
print("APP_VERSION story: W6 FIX 0.682.0 head + their KALA chain verbatim")

# ---------------------------------------------------------------- 5. the mirrors
h = ROOT / "docs" / "HISTORY.md"
t = h.read_text(encoding="utf-8")
sec = ("## v0.682.0 KAAN W6 FIX — the unlock guard's engine seam made honest (8 Nov 2026)\n\n"
       "The first live W6 check on the VPS crashed at kaan/status: limits.voiceprint_ready unpacked "
       "`ok, why = VE.available()` but the pre-existing voiceid engine contract is a plain bool "
       "(`available() -> bool`; only the kaan engine's `EN.available()` is the tuple pair). The W6 "
       "suite stayed 195/195 green because its three engine patches assumed the same wrong tuple "
       "shape — the tests inherited the bug.\n\n"
       "- **THE FIX** — W6 adapts to their lane as-is: limits.py consumes the bool and composes the "
       "honest why itself (sherpa_onnx or the CAM++/TitaNet models in voiceid_models_dir missing); "
       "the voiceid lane untouched; the three W6 test patches healed to `lambda: True`; NEW "
       "regression test speaking the real unpatched contract.\n"
       "- Version ritual: ritual_v0682.py swept 0.681.0 -> 0.682.0 (+681) across the test tokens, "
       "pubspec, the console cache-buster stamps; registry 609 stands (no tools); zero pip.\n"
       "- Server-only deploy = owner's vps-ops dispatch; the W6 retest on the VPS rides this deploy.\n\n")
h.write_text(sec + t, encoding="utf-8")
print("HISTORY: W6 FIX section prepended")

w = ROOT / "docs" / "WORKLOG.md"
t = w.read_text(encoding="utf-8")
lines_w = t.split("\n")
idx = next(i for i, l in enumerate(lines_w) if l.startswith("Task ID:"))
lines_w.insert(idx, 'Task ID: v0.682.0 KAAN W6 FIX - the unlock guard\'s engine seam made honest (voiceprint_ready consumes the real voiceid bool contract; the live box TypeError healed at kaan/status; the three W6 test patches healed + one NEW regression test on the real unpatched contract; ritual_v0682.py 0.681.0 -> 0.682.0 (+681); owner: "W6 (quotas + retention -> unlocks real voiceprint diarization) -- start")\n')
w.write_text("\n".join(lines_w), encoding="utf-8")
print("WORKLOG: task inserted")

c = ROOT / "CLAUDE.md"
t = c.read_text(encoding="utf-8")
old_head = "- Current version: v0.681.0 (pubspec 0.681.0+680; "
new_head = ("- Current version: v0.682.0 (pubspec 0.682.0+681; KAAN W6 FIX v0.682.0 = the unlock "
            "guard's engine seam made honest: voiceprint_ready consumes the pre-existing voiceid "
            "BOOL contract (the live TypeError: cannot unpack non-iterable bool object healed at "
            "kaan/status), the voiceid lane untouched, the three W6 test patches healed to the real "
            "shape + one NEW regression test speaking the real unpatched contract, zero tools "
            "(registry 609 stands) zero pip, owner 'W6 (quotas + retention -> unlocks real "
            "voiceprint diarization) -- start'; previous head: v0.681.0 (pubspec 0.681.0+680; ")
assert old_head in t, "the Current version line head moved"
t = t.replace(old_head, new_head, 1)
anchor = "## Current state (latest first, one line each)\n"
i = t.index(anchor) + len(anchor)
bullet = ('- v0.682 KAAN W6 FIX (owner: "W6 (quotas + retention -> unlocks real voiceprint '
          'diarization) -- start"): the first live W6 check on the VPS crashed at kaan/status - '
          "limits.voiceprint_ready did `ok, why = VE.available()` but the pre-existing voiceid "
          "engine returns a plain bool (only the kaan engine's EN.available() is the tuple pair); "
          "the W6 suite stayed green because its three engine patches assumed the same wrong shape. "
          "THE FIX: W6 adapts to their lane as-is - limits.py consumes the bool and composes the "
          "honest why itself (sherpa_onnx or the CAM++/TitaNet models missing); the voiceid lane "
          "untouched; the three test patches healed; a NEW regression test speaks the real "
          "unpatched contract. Registry 609 stands; zero pip; server-only deploy.\n")
t = t[:i] + bullet + t[i:]
c.write_text(t, encoding="utf-8")
print("CLAUDE.md: current-version line + Current state bullet")

# ---------------------------------------------------------------- 6. residual check
residual_v = []
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    text = f.read_text(encoding="utf-8")
    if re.search(rf"\b{re.escape(OLD_V)}\b", text):
        residual_v.append(f.name)
print("residual 0.681.0 in tests:", residual_v or "ZERO")
pub_now = pub.read_text(encoding="utf-8")
assert f"version: {NEW}{NEW_BUILD}" in pub_now
main_now = main.read_text(encoding="utf-8")
assert f'APP_VERSION = "{NEW}"' in main_now
print("ritual_v0682: DONE")
