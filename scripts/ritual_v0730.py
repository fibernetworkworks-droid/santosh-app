#!/usr/bin/env python3
"""v0.730.0 SHILP MANCH version ritual.

SHILP (the ArtCraft generation lane, owner "MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE
THIS" on the storytold/artcraft recon) was PLANNED at v0.686.0 while the dev chain ran on to
v0.729.0 (SAB ENGLISH wave 2) - REBASE PROTOCOL: rebuilt fresh on their 53ab8a366 v0.729.0 tip,
their base kept whole, the version layer re-applied coherently 0.729.0/+728 -> 0.730.0/+729.
The registry grows 617 -> 618 (617 + 1 shilp - the lane's ONE tool).

This sweep re-applies that layer across ALL test files (version tokens with the parser-stamp
guard: `v0.729.0-...`-shaped pins STAY - they pin someone's own stamp, not APP_VERSION),
pubspec, the console cache-buster stamps (the v0179 law: stamps == APP_VERSION), the APP_VERSION
story (my SHILP head, their SAB ENGLISH wave 2 story verbatim in Previous), and the three
mirrors (HISTORY / WORKLOG / CLAUDE.md). Zero residual expected on exit.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEW, NEW_BUILD = "0.730.0", "+729"
OLD_V, OLD_BUILD = "0.729.0", "+728"

# ---------------------------------------------------------------- 1. the test-file sweep
changed, tokens = [], 0
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    text = f.read_text(encoding="utf-8")
    orig = text
    hits = re.findall(r"(?<!v)0\.729\.0", text)          # the v-prefixed stamps stay theirs
    tokens += len(hits)
    text = re.sub(r"(?<!v)0\.729\.0", NEW, text)
    text = re.sub(r"\+728\b", NEW_BUILD, text)
    if text != orig:
        f.write_text(text, encoding="utf-8")
        changed.append(f.name)
print(f"tests swept: {len(changed)} files ({tokens} version tokens)")

# ---------------------------------------------------------------- 1b. the registry pins (617 -> 618,
# the v0681 law: the pins heal WITH the arithmetic note - the newest entry prepends its story)
PIN_NEW = ('"617 + 1 shilp (v0.730 SHILP MANCH: the ArtCraft generation lane, their Omni API '
           'api.storyteller.ai, BYOK - owner \'MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE '
           'THIS\' -> the plan\'s W0). 616 + 1 seekh_video')
pins = 0
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    text = f.read_text(encoding="utf-8")
    orig = text
    text = re.sub(r"(len\(TOOLS\)|len\(tools\.TOOLS\)|len\(T\.TOOLS\)) == 617\b", r"\1 == 618", text)
    if PIN_NEW[1:40] not in text:                        # idempotent: never prepend twice
        text = text.replace('"616 + 1 seekh_video', PIN_NEW)
    if text != orig:
        f.write_text(text, encoding="utf-8")
        pins += 1
print(f"registry pins healed: {pins} files (617 -> 618, the shilp story prepended)")

# ---------------------------------------------------------------- 2. pubspec
pub = ROOT / "pubspec.yaml"
text = pub.read_text(encoding="utf-8")
text, n = re.subn(r"version: 0\.\d+\.\d+\+\d+", f"version: {NEW}{NEW_BUILD}", text, count=1)
pub.write_text(text, encoding="utf-8")
print("pubspec ->", f"{NEW}{NEW_BUILD}" if n else "!! PATTERN MISS")

# ---------------------------------------------------------------- 3. the console cache-busters (the v0179 law)
stamped = 0
for f in sorted((ROOT / "server" / "app" / "static" / "console").glob("*")):
    if f.suffix not in (".html", ".htm", ".js", ".css"):
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
MY_HEAD = (
f'APP_VERSION = "{NEW}"   # v0.730.0: SHILP MANCH - the ArtCraft generation lane, their Omni '
"API behind her tool (owner: \"MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS\" after the "
"READ of github.com/storytold/artcraft - 'the IDE for artists', MIT/Apache-2.0; planned at "
"v0.686.0, the dev chain ran on to v0.729.0 SAB ENGLISH wave 2 while SHILP sat planned - REBASE "
"PROTOCOL, rebuilt fresh on their 53ab8a366 v0.729.0 tip, their base kept whole; shilp = craft): "
"ONE tool `shilp`, SIX actions over EXACTLY the surface their public doc proves (their "
"_docs/artcraft_omni_api.md, base https://api.storyteller.ai - their doc's own emphasis: NOT "
"api.getartcraft.com): video (POST /v1/omni_api/generate/video - model, prompt, "
"duration_seconds, aspect_ratio, negative_prompt, resolution, generate_audio, start/end frame "
"image urls + reference image/video/audio url lists -> an inference job token) | image (POST "
"/v1/omni_api/generate/image) | job (GET /v1/omni_api/job_status/job/{token} - their states ride "
"raw: pending/started/attempt_failed still run, complete_success/complete_failure/dead/"
"cancelled_by_user/cancelled_by_system terminal; the finished media at "
"state.maybe_result.media_links.cdn_url) | jobs (the batch, up to 25 tokens) | status + models "
"(zero network; the curated 62-model catalog from their public README, dated). THE LAWS: BYOK "
"owner-level (config artcraft_api_key, VPS .env only - ARTCRAFT_API_KEY, never chat/repo/"
"envelope; API access gated per account by the ArtCraft team) | money is hers (every generate "
"spends credits; 402 -> PAYMENT, FINAL, never retried; the tool description says only on her "
"explicit ask) | idempotency minted here (fresh UUID4 per call, returned in the envelope, "
"caller tokens ignored) | reference urls cross the lane's own wall BEFORE any byte moves "
"(http(s) only per their rule, no embedded credentials, no loopback/RFC1918/link-local/"
"reserved/metadata hosts - internal endpoints never land in their logs; shape problems "
"BAD_INPUT, wall refusals NOT_ALLOWED) | URL inputs only (their *_media_tokens fields accepted "
"ONLY to be refused BY NAME with their own mutual-exclusivity rule quoted - the upload "
"endpoints are not in the public doc, nothing invented) | caps refuse never clamp (prompt 8000, "
"refs 20/field, url 2048, batch 25) | one network seam _http (tests monkeypatch exactly it, the "
"suite offline; lazy httpx, zero new pip) | one envelope {schema_version, ok, tool, action, ..., "
"meta{elapsed_ms, backend}, error{code, message, hint}}; kill switch shilp_enabled default on; "
"ALL strings English (the standing rule). DOORS: the toolbelt door (agent/tools.py registry 617 "
"-> 618, 618 = 617 + 1 shilp) + the MCP stdio door (server/app/shilp/mcp_server.py, the kaan "
"wire: line-delimited JSON-RPC 2.0 protocol 2025-06-18, one tool shilp, dispatch through "
"agent.shilp_tools._sync so the doors can never drift, serverInfo hoola-shilp). Tests: NEW "
"test_v0730_shilp.py (43, zero network, the seam fake records every call so the tests assert "
"method/url/body/auth not just outcomes): envelope shape, unknown action, kill switch, status "
"zero-network + keyless + never-leaks-the-key, NEED_SETUP on every network action keyless, "
"models 62 complete, the media-token mutual-exclusivity refusal, the 12-case reference-url wall "
"table (loopback/RFC1918/link-local/metadata/credentials/ftp/file/garbage - all refused before "
"the seam), the 20-ref + 8000-prompt caps refusing, video/image happy paths asserting the POST "
"url + Bearer key + body + minted UUID4, fresh idempotency per call, their 401 -> AUTH / 402 -> "
"PAYMENT-final / 400 rides their words, their doc's own pending + complete_success example "
"states mapped verbatim, complete_failure honest with the credits note, job-token shape, batch "
"happy + cap + shape, registry 618 pin, enum pin, APP_VERSION pin, purity (no top-level httpx), "
"the MCP door (initialize hoola-shilp + tools/list one tool + the six-action enum + tools/call "
"riding the same dispatch + NEED_SETUP through the door). Zero new pip, zero new keys (BYOK "
"rides HER key), zero Flutter change. Server-only deploy = owner's vps-ops dispatch. NOT "
"VERIFIED live: her first real generation (needs HER ArtCraft key in the VPS .env - "
"action=status shows the setup directions); the zero-network status/models ride the deploy. "
"Previous: "
)


if their.startswith(f'APP_VERSION = "{NEW}"'):
    print("APP_VERSION story already spliced - skipping (idempotent re-run)")
else:
    assert their.startswith(f'APP_VERSION = "{OLD_V}"'), "line 36 is not the SAB ENGLISH wave 2 story"
    # their head at this tip reads `APP_VERSION = "0.729.0"   # SAB ENGLISH wave 2 v0.729.0 (owner: ...)`
    t_marker = their.index("   # ") + len("   # ")
    lines[35] = MY_HEAD + their[t_marker:]
    main.write_text("\n".join(lines), encoding="utf-8")
    print("APP_VERSION story spliced (SHILP head, their SAB ENGLISH wave 2 story verbatim in Previous)")

# ---------------------------------------------------------------- 5. the CLAUDE.md mirror
cl = ROOT / "CLAUDE.md"
text = cl.read_text(encoding="utf-8")
text, n = re.subn(r"Current version: v0\.729\.0 \(pubspec 0\.729\.0\+728;",
                  "Current version: v0.730.0 (pubspec 0.730.0+729; SHILP MANCH v0.730.0 = the "
                  "ArtCraft generation lane (their Omni API api.storyteller.ai, BYOK, one `shilp` "
                  "tool, six actions, registry 618); previous head v0.729.0 (pubspec 0.729.0+728;",
                  text, count=1)
bullet = ("- v0.730 SHILP MANCH (planned at 0.686, rebuilt on their v0.729 tip; owner: \"MAKE A PLAN "
          "FOR HOOLA AI THUS HOOLA USER CAN USE THIS\" on the storytold/artcraft recon): the "
          "ArtCraft generation lane - ONE tool `shilp`, six actions over their DOCUMENTED Omni API "
          "surface (video / image generation -> job tokens; job / jobs polling to their raw states "
          "with cdn_url on success; keyless status / models with the curated 62-model README "
          "catalog). BYOK: ARTCRAFT_API_KEY in the VPS .env only, never in any envelope; every "
          "generate spends her credits and a 402 is FINAL; idempotency minted here (fresh UUID4 per "
          "call); reference urls cross the lane's own wall first (http(s), no credentials, no "
          "private hosts); media-token inputs refused by name (their upload endpoints are not in "
          "the public doc); caps refuse never clamp; one network seam, zero new pip; toolbelt door "
          "(registry 618) + the kaan-wire MCP door (hoola-shilp); shilp_enabled default on; 43 "
          "tests.\n")
text = text.replace("## Current state (latest first, one line each)\n",
                    "## Current state (latest first, one line each)\n" + bullet, 1)
cl.write_text(text, encoding="utf-8")
print("CLAUDE.md:", "current-version line + Current state bullet" if n else "!! current-version PATTERN MISS")

# ---------------------------------------------------------------- 6. HISTORY.md + WORKLOG.md
hist = ROOT / "docs" / "HISTORY.md"
section = """## v0.730.0 SHILP MANCH — the ArtCraft generation lane, their Omni API behind her tool (9 Nov 2026; owner: "MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS" on the storytold/artcraft recon)

Planned at v0.686.0; the dev chain ran on to v0.729.0 (SAB ENGLISH waves) while the plan sat — REBASE PROTOCOL onto their 53ab8a366 v0.729.0 tip, their base kept whole. **Registry 617 → 618** (617 + 1 shilp). Zero new pip, zero new keys (BYOK rides her key), zero Flutter change. ArtCraft is github.com/storytold/artcraft (MIT/Apache-2.0), "the IDE for artists"; this lane ports their DOCUMENTED Omni API surface only — nothing inferred (the kala law).

- **One tool, six actions** — `agent/shilp_tools.py`: `video` / `image` (POST /v1/omni_api/generate/... → an inference job token; video takes model, prompt, duration_seconds, aspect_ratio, negative_prompt, resolution, generate_audio, start/end frame urls + reference image/video/audio url lists; image takes model, prompt, image_urls) | `job` / `jobs` (GET /v1/omni_api/job_status/{job,batch} — their states ride raw; pending/started/attempt_failed still run, complete_success/complete_failure/dead/cancelled_* terminal; the finished media at state.maybe_result.media_links.cdn_url) | `status` / `models` (zero network; the curated 62-model catalog from their public README, dated, with the honest note that audio/mesh/splat have NO documented Omni API endpoint yet).
- **BYOK, owner-level** — config `artcraft_api_key` (VPS .env only, ARTCRAFT_API_KEY, never in chat, the repo, or any envelope — tested); API access is gated per account by the ArtCraft team (app.getartcraft.com → Settings → API Keys); no key = every network action answers NEED_SETUP with those exact directions.
- **Money is hers** — every generate call spends her ArtCraft credits; the tool description tells the model to fire only on her explicit ask; their 402 maps to `PAYMENT`, FINAL, never retried (hint: top up, then ask again); a 401 maps to `AUTH` naming the .env knob; their other 400s ride their own words inside UPSTREAM.
- **Idempotency minted here** — a fresh UUID4 per generate call (their doc's own rule), returned in the envelope; caller-supplied tokens ignored.
- **The reference-url wall** — every *_url crosses the lane's own check BEFORE any byte moves: http(s) only (their own rule), no embedded credentials, no loopback / RFC1918 / link-local / reserved / metadata hosts (an internal endpoint must never land in their server logs). Shape problems → BAD_INPUT; wall refusals → NOT_ALLOWED. Tested as a 12-case table, all refused before the seam.
- **URL inputs only** — their *_media_tokens fields are accepted only to be refused BY NAME, quoting their own mutual-exclusivity rule ("Either reference_image_media_tokens or reference_image_urls must be set, not both"); the upload endpoints behind the tokens are not in the public doc, so nothing is invented.
- **Caps refuse, never clamp** — prompt 8000 chars, 20 refs per field, 2048 per url, 25 batch tokens; a generation is money, silently trimming an ask would change the job behind her back.
- **One envelope, honest jobs** — {schema_version, ok, tool, action, ..., meta{elapsed_ms, backend}, error{code, message, hint}}; `ok` is the CALL, `job_ok` is the JOB — a failed generation is not a failed lane call and never hides behind one. Kill switch `shilp_enabled` (default on). All strings English.
- **Doors** — the toolbelt door (agent/tools.py, registry 618) + the MCP stdio door (`app/shilp/mcp_server.py`, the kaan wire: line-delimited JSON-RPC 2.0, protocol 2025-06-18, one tool `shilp`, dispatch through `shilp_tools._sync` so the doors can never drift, serverInfo `hoola-shilp`).
- Tests: NEW `test_v0730_shilp.py` (43, zero network; the seam fake records every call so tests assert method / url / body / auth shape, not just outcomes). Two pins ran red until the ritual landed the version — by design.
- Version ritual: `scripts/ritual_v0730.py` — version tokens swept with the parser-stamp guard, pubspec 0.730.0+729, console stamps `?v=0.730.0`, the APP_VERSION story splice, the three mirrors.
- Server-only deploy = owner's vps-ops dispatch; desktop untouched. NOT VERIFIED live: her first real generation — needs HER ArtCraft key in the VPS .env (`shilp` action=status shows the setup directions); the zero-network status/models ride the deploy. Next: W1 SHILP SEVAK (the job butler worker) once a real key exists.

"""
text = hist.read_text(encoding="utf-8")
hist.write_text(section + text, encoding="utf-8")
print("HISTORY.md section prepended")

work = ROOT / "docs" / "WORKLOG.md"
task = """# HOOLA — Multi-Session Worklog
Task ID: v0.730.0 SHILP MANCH (the ArtCraft generation lane, W0)
Agent: main (shilp lane)
Task: owner "MAKE A PLAN FOR HOOLA AI THUS HOOLA USER CAN USE THIS" after the READ of github.com/storytold/artcraft; the plan's W0 (the lane, six actions, two doors, BYOK, ~43 tests; W1 SEVAK worker + W2 BHANDAR store wait on a real key).
Work Log: REBASE PROTOCOL (planned v0.686, rebuilt on their v0.729 tip 53ab8a366, their base kept whole); agent/shilp_tools.py NEW (envelope, _http seam, _call status table, _ref_url wall, _no_tokens media-token refusal, _gen_body, _generate, _act_job/_act_jobs, _map_state, _act_status/_act_models, _error_of, _sync, SHILP_TOOLS spec); agent/tools.py registry 617 -> 618; config.py shilp_enabled + artcraft_api_key + artcraft_base_url; app/shilp/mcp_server.py NEW (the kaan wire, serverInfo hoola-shilp); test_v0730_shilp.py NEW (43, offline, the seam fake records calls); ritual_v0730.py swept (parser-stamp guard), pubspec 0.730.0+729, console stamps, APP_VERSION story, CLAUDE.md + HISTORY.md + WORKLOG mirrors.
Stage Summary: pushed to main as v0.730.0 + tag; vps-ops deploy fired; live test = action=status zero-network + her first real generation once ARTCRAFT_API_KEY is in the VPS .env.
"""
text = work.read_text(encoding="utf-8")
if "# HOOLA — Multi-Session Worklog\n" in text:
    text = text.replace("# HOOLA — Multi-Session Worklog\n", task, 1)
    print("WORKLOG task inserted")
else:
    print("!! WORKLOG header PATTERN MISS - insert the task manually")
work.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------- 7. the residual check
residual = 0
for f in sorted((ROOT / "server" / "tests").glob("*.py")):
    residual += len(re.findall(rf"(?<!v){re.escape(OLD_V)}", f.read_text(encoding="utf-8")))
pub_text = pub.read_text(encoding="utf-8")
main_text = main.read_text(encoding="utf-8")
residual += len(re.findall(rf"\?v={re.escape(OLD_V)}", main_text))
print(f"residual {OLD_V} tokens in tests: {residual}")
print(f"pubspec now: {re.search(r'version: .*', pub_text).group(0)}")
print(f"APP_VERSION head: {main_text.splitlines()[35][:80]}...")
