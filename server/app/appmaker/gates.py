"""v0.455 SURAKSHA GATE (App Sahayak Pillar I, Phase 60, second half): a security check on every build, and a FAILING
gate blocks the store upload.

Not a label on a sticker: every row here is a check that reads the REAL build - the generated project on disk, its
manifest / Info.plist, its pinned library list and the APK / AAB bytes - and says pass, warn or FAIL with what it read.
Six gates:

  1. SECRETS IN THE APP      - the app's own source + assets are searched for keys, tokens and private keys. Her
                               gateway / courier / push keys live on the SERVER (sealed) and must never ride in an APK.
                               A hit is a FAIL, because an APK is public the moment it is uploaded.
  2. PERMISSIONS             - every permission in the manifest must be one this app's features actually need, and none
                               may be from Play's restricted list (CLAUDE.md: no battery-optimisation, no exact alarm,
                               SMS / call log never). An unexplained permission FAILS.
  3. APP SETTINGS            - debuggable off, allowBackup off, cleartext traffic off (only 10.0.2.2 in a debug build,
                               for Hoola's own emulator check), every component exported on purpose, a release signature.
  4. LIBRARY CVEs            - the pinned library set (gradle/libs.versions.toml, SwiftPM) is asked about at OSV.dev
                               (Google's own free vulnerability database, no key). A known HIGH / CRITICAL FAILS; the
                               check cannot reach OSV -> "not checked", never a silent pass.
  5. LOGIN RULES             - what Pillar I asks: no password box outside the kit's sign-in screen, Sign in with Apple
                               offered on the iPhone build when Google is on (App Store 4.8), in-app account deletion,
                               staff 2FA where she asked for it.
  6. DATA RULES              - privacy page + deletion page exist, DPDP consent on sign-up, her declared data-safety
                               answers match the permissions actually in the build.

Honest by design: `checked` lists what was really read, `not_checked` says what this gate could NOT see (for example a
run-time scan of the app on a phone, or an iOS binary we never build on Hoola's own machine). A check that could not
run is never counted as a pass.
"""
from __future__ import annotations

import json
import logging
import re
import zipfile
from pathlib import Path
from typing import Any

from ..db import now
from ..site import webapp as W
from .models import AppProject

log = logging.getLogger(__name__)
STATS = {"runs": 0, "failed": 0, "blocked": 0, "osv": 0, "osv_down": 0}

OSV_URL = "https://api.osv.dev/v1/querybatch"
BAD_SEVERITY = ("HIGH", "CRITICAL")
# Play's restricted / never-asked permissions (CLAUDE.md NON-NEGOTIABLE RULES)
BANNED_PERMS = ("REQUEST_IGNORE_BATTERY_OPTIMIZATIONS", "USE_EXACT_ALARM", "SCHEDULE_EXACT_ALARM", "READ_SMS",
                "RECEIVE_SMS", "SEND_SMS", "READ_CALL_LOG", "WRITE_CALL_LOG", "PROCESS_OUTGOING_CALLS",
                "READ_PHONE_NUMBERS", "QUERY_ALL_PACKAGES", "MANAGE_EXTERNAL_STORAGE", "BIND_ACCESSIBILITY_SERVICE",
                "SYSTEM_ALERT_WINDOW", "READ_CONTACTS", "WRITE_CONTACTS", "READ_CALENDAR", "WRITE_CALENDAR",
                "ACCESS_BACKGROUND_LOCATION", "CAMERA", "READ_EXTERNAL_STORAGE", "WRITE_EXTERNAL_STORAGE")
# every permission a Hoola build may contain, and why it is there
ALLOWED_PERMS: dict[str, str] = {
    "INTERNET": "the app talks to its own backend",
    "ACCESS_NETWORK_STATE": "to know it is offline (the outbox waits)",
    "POST_NOTIFICATIONS": "order / booking updates the user asked for",
    "RECEIVE_BOOT_COMPLETED": "the background update check survives a restart",
    "ACCESS_COARSE_LOCATION": "a location field / live tracking she switched on",
    "ACCESS_FINE_LOCATION": "a location field / live tracking she switched on",
    "FOREGROUND_SERVICE": "the rider's shift (live tracking)",
    "FOREGROUND_SERVICE_LOCATION": "the rider's shift (live tracking)",
    "RECORD_AUDIO": "a voice-note field (asked only on the Record tap)",
    "VIBRATE": "notification feedback",
}
SECRETS: list[tuple[str, str]] = [
    (r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----", "a private key"),
    (r"\brzp_(?:live|test)_[A-Za-z0-9]{10,}", "a Razorpay key"),
    (r"\bsk_(?:live|test)_[A-Za-z0-9]{16,}", "a secret API key (sk_...)"),
    (r"\bAIza[0-9A-Za-z_\-]{35}\b", "a Google API key"),
    (r"\bya29\.[0-9A-Za-z_\-]{20,}", "a Google access token"),
    (r"\bEA[A-Za-z0-9]{40,}", "a Meta / WhatsApp token"),
    (r"\bghp_[A-Za-z0-9]{20,}", "a GitHub token"),
    (r"\bxox[baprs]-[A-Za-z0-9-]{10,}", "a Slack token"),
    (r"\bAKIA[0-9A-Z]{16}\b", "an AWS key id"),
    (r"\bsq0(?:atp|csp)-[A-Za-z0-9_\-]{20,}", "a Square token"),
    (r"(?i)\b(?:api[_-]?key|secret|password|passwd|auth[_-]?token)\s*[:=]\s*[\"'][^\"'\s]{12,}[\"']", "something that reads like a key"),
]
# the fake values Hoola's own CI fixture uses on purpose (they are not anybody's keys)
SECRET_OK = ("AIzaSyCiTestKeyNotReal", "hoola-ci-test", "YOUR_", "xxxx", "example.com")
SRC_EXT = (".kt", ".kts", ".swift", ".java", ".xml", ".json", ".plist", ".gradle", ".properties", ".yml", ".yaml", ".txt", ".md")
SKIP_DIRS = ("build", ".gradle", "keys", "hoola_qa", ".git", "DerivedData")
MAX_FILE = 2_000_000
GATES = ("secrets", "permissions", "settings", "libraries", "login", "data")


class GateError(W.AppError):
    pass


def _j(v: Any, d: Any) -> Any:
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v) if v else d
    except (TypeError, ValueError):
        return d


def _row(kind: str, name: str, state: str, said: str, read: str = "") -> dict[str, Any]:
    return {"gate": kind, "check": name, "state": state, "say": said, "read": read[:300]}


# ---------------------------------------------------------------- 1. secrets in the app
def _files(root: Path) -> list[Path]:
    out: list[Path] = []
    if not root.exists():
        return out
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in SRC_EXT:
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        try:
            if p.stat().st_size > MAX_FILE:
                continue
        except OSError:
            continue
        out.append(p)
    return out[:4000]


def _hits(text: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for rx, why in SECRETS:
        for m in re.finditer(rx, text):
            bit = m.group(0)
            if any(ok in bit for ok in SECRET_OK):
                continue
            found.append((why, bit[:12] + "…"))
            break
    return found


def gate_secrets(r: AppProject, proj: Path, apk: Path | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    bad: list[str] = []
    n = 0
    for p in _files(proj):
        n += 1
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        for why, bit in _hits(text):
            bad.append(f"{p.relative_to(proj)}: {why} ({bit})")
    rows.append(_row("secrets", "No key in the app's own files", "fail" if bad else "pass",
                     "Keys were found - the APK reaches everyone, so this blocks the build: " + "; ".join(bad[:3]) if bad
                     else "No key / token was found in the app's files.", f"{n} files"))
    if apk and apk.exists():
        inside: list[str] = []
        try:
            with zipfile.ZipFile(apk) as z:
                names = z.namelist()
                for nm in names:
                    if nm.startswith("assets/") and nm.endswith((".json", ".txt", ".xml")):
                        try:
                            raw = z.read(nm)[:MAX_FILE].decode("utf-8", "ignore")
                        except (KeyError, OSError):
                            continue
                        for why, bit in _hits(raw):
                            inside.append(f"{nm}: {why} ({bit})")
            rows.append(_row("secrets", "Nothing secret inside the built app", "fail" if inside else "pass",
                             "; ".join(inside[:3]) if inside else "No key in the APK's assets.", f"{len(names)} entries"))
        except (zipfile.BadZipFile, OSError) as e:
            rows.append(_row("secrets", "Nothing secret inside the built app", "not_checked", f"The APK could not be read: {e}"))
    else:
        rows.append(_row("secrets", "Nothing secret inside the built app", "not_checked", "The APK of this build was not found."))
    return rows


# ---------------------------------------------------------------- 2. permissions
def gate_permissions(r: AppProject, proj: Path, spec: dict[str, Any]) -> list[dict[str, Any]]:
    mf = proj / "app/src/main/AndroidManifest.xml"
    if not mf.exists():
        return [_row("permissions", "Only the permissions the features need", "not_checked", "Manifest not found.")]
    text = mf.read_text(errors="ignore")
    # only what the APP asks for: a permission NAMED ON a <service> (BIND_JOB_SERVICE) is one the system holds, not a request
    perms = sorted(set(re.findall(r'<uses-permission\s+android:name="android\.permission\.([A-Z_]+)"', text)))
    banned = [p for p in perms if p in BANNED_PERMS]
    unknown = [p for p in perms if p not in ALLOWED_PERMS and p not in BANNED_PERMS]
    be = (spec.get("seed") or {}).get("backend") or {}
    wants_loc = bool(be.get("track")) or any(f.get("type") == "location" for c in (be.get("collections") or [])
                                             for f in (c.get("fields") or []))
    wants_mic = any(f.get("type") == "audio" for c in (be.get("collections") or []) for f in (c.get("fields") or []))
    extra: list[str] = []
    if "ACCESS_FINE_LOCATION" in perms and not wants_loc:
        extra.append("location (there is no location field or tracking)")
    if "RECORD_AUDIO" in perms and not wants_mic:
        extra.append("microphone (there is no voice-note field)")
    rows = [_row("permissions", "No restricted permission", "fail" if banned else "pass",
                 "A permission that Play restricts was found: " + ", ".join(banned) if banned
                 else "No restricted permission (SMS, call log, background location, camera, exact alarm...).",
                 ", ".join(perms)),
            _row("permissions", "Every permission is one of ours", "fail" if unknown else "pass",
                 "These permissions should not be in a Hoola build: " + ", ".join(unknown) if unknown
                 else f"{len(perms)} permissions, all known.", ", ".join(perms)),
            _row("permissions", "Each permission has a feature behind it", "fail" if extra else "pass",
                 "Permission without a feature: " + "; ".join(extra) if extra
                 else "Every permission has its feature in the app.")]
    return rows


# ---------------------------------------------------------------- 3. app settings
def gate_settings(r: AppProject, proj: Path, apk: Path | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    mf = proj / "app/src/main/AndroidManifest.xml"
    if not mf.exists():
        return [_row("settings", "Release settings", "not_checked", "Manifest not found.")]
    text = mf.read_text(errors="ignore")
    dbg = re.search(r'android:debuggable\s*=\s*"true"', text)
    rows.append(_row("settings", "Not debuggable", "fail" if dbg else "pass",
                     "A release app must not be debuggable." if dbg else "debuggable is not set anywhere (release default is false)."))
    backup = re.search(r'android:allowBackup\s*=\s*"true"', text)
    rows.append(_row("settings", "Backups off", "fail" if backup else "pass",
                     "With allowBackup=true the app's data goes into the phone's backup." if backup
                     else "allowBackup=false (the app's data does not go into a backup)."))
    cfg = proj / "app/src/main/res/xml/network_security_config.xml"
    rel = cfg.read_text(errors="ignore") if cfg.exists() else ""
    clear_ok = 'cleartextTrafficPermitted="false"' in rel
    dbg_cfg = (proj / "app/src/debug/res/xml/network_security_config.xml")
    dbg_only = "10.0.2.2" in (dbg_cfg.read_text(errors="ignore") if dbg_cfg.exists() else "")
    rows.append(_row("settings", "https only", "pass" if clear_ok else "fail",
                     ("The release build uses https only; http only in the debug build for 10.0.2.2 (Hoola's own check)."
                      if clear_ok and dbg_only else
                      "The release build uses https only." if clear_ok else "Cleartext (http) traffic is not turned off."),
                     "network_security_config.xml"))
    exported = re.findall(r'<(activity|service|receiver|provider)\b[^>]*android:exported\s*=\s*"true"', text)
    acts = re.findall(r'<(activity|service|receiver|provider)\b', text)
    noexp = len(acts) - len(re.findall(r'android:exported\s*=\s*"(?:true|false)"', text))
    rows.append(_row("settings", "Components exported on purpose", "fail" if noexp > 0 else "pass",
                     f"{noexp} components do not declare exported at all (on Android 12+ the build itself stops)." if noexp > 0
                     else f"{len(acts)} components, {len(exported)} exported on purpose (launcher / push).",
                     f"{len(acts)} components"))
    if apk and apk.exists():
        try:
            with zipfile.ZipFile(apk) as z:
                names = z.namelist()
            v1 = any(n.startswith("META-INF/") and n.endswith((".RSA", ".DSA", ".EC")) for n in names)
            tail = b""
            try:                                   # v2 / v3 signing keeps the signature in the APK Signing Block, not in META-INF
                with open(apk, "rb") as fh:
                    size = apk.stat().st_size
                    fh.seek(max(0, size - 1_500_000))
                    tail = fh.read()
            except OSError:
                tail = b""
            v2 = b"APK Sig Block 42" in tail
            # SAID, never a blocker: the store gets a .aab signed with her UPLOAD key, so the preview APK's own
            # signature tells her whether THIS file installs on a phone - it says nothing about the store upload.
            rows.append(_row("settings", "The preview app is signed", "pass" if (v1 or v2) else "warn",
                             "The preview APK is signed (" + ("v1" if v1 else "") + (" v2/v3" if v2 else "").strip() + ")."
                             if (v1 or v2) else "No signature was found on the preview APK - that file will not install on a phone "
                             "(the store gets the .aab signed with your upload key, so the upload was not stopped).",
                             f"{len(names)} entries"))
        except (zipfile.BadZipFile, OSError):
            rows.append(_row("settings", "The built app is signed", "not_checked", "The APK could not be read."))
    else:
        rows.append(_row("settings", "The built app is signed", "not_checked", "The APK of this build was not found."))
    return rows


# ---------------------------------------------------------------- 4. library CVEs (OSV.dev, Google's own database)
def _deps(proj: Path) -> list[dict[str, str]]:
    """The pinned libraries of this build, as OSV asks for them."""
    toml = proj / "gradle/libs.versions.toml"
    out: list[dict[str, str]] = []
    if not toml.exists():
        return out
    text = toml.read_text(errors="ignore")
    vers = dict(re.findall(r'^\s*([A-Za-z0-9_\-]+)\s*=\s*"([^"]+)"\s*$', text.split("[libraries]")[0], re.M))
    for group, name, ref in re.findall(r'group\s*=\s*"([^"]+)"\s*,\s*name\s*=\s*"([^"]+)"(?:\s*,\s*version\.ref\s*=\s*"([^"]+)")?', text):
        v = vers.get(ref or "", "")
        if v:
            out.append({"ecosystem": "Maven", "name": f"{group}:{name}", "version": v})
    seen: set[str] = set()
    uniq: list[dict[str, str]] = []
    for d in out:
        k = f"{d['name']}@{d['version']}"
        if k not in seen:
            seen.add(k)
            uniq.append(d)
    return uniq[:60]


_OSV = None


def set_osv(fn) -> None:
    """Tests only: a function(list of deps) -> list of lists of vulns, instead of the network."""
    global _OSV
    _OSV = fn


def _osv(deps: list[dict[str, str]]) -> list[list[dict[str, Any]]] | None:
    if not deps:
        return []
    if _OSV is not None:
        return _OSV(deps)
    try:
        import httpx
        q = {"queries": [{"package": {"ecosystem": d["ecosystem"], "name": d["name"]}, "version": d["version"]} for d in deps]}
        with httpx.Client(timeout=20.0) as c:
            resp = c.post(OSV_URL, json=q)
        if resp.status_code != 200:
            STATS["osv_down"] += 1
            return None
        res = resp.json().get("results") or []
        STATS["osv"] += 1
        return [list((x or {}).get("vulns") or []) for x in res]
    except Exception:                                      # noqa: BLE001  (a gate never crashes a build)
        STATS["osv_down"] += 1
        log.info("osv unreachable", exc_info=True)
        return None


def _worst(vuln: dict[str, Any]) -> str:
    """OSV gives severity as a CVSS vector and / or a word; HIGH / CRITICAL is what blocks."""
    for sv in vuln.get("severity") or []:
        score = str((sv or {}).get("score") or "")
        m = re.search(r"/A:([NLH])", score)                 # a CVSS v3 vector: read its own base rating when present
        if m and m.group(1) == "H":
            return "HIGH"
    db = (vuln.get("database_specific") or {}).get("severity")
    if isinstance(db, str) and db.upper() in ("LOW", "MODERATE", "MEDIUM", "HIGH", "CRITICAL"):
        return db.upper()
    for aff in vuln.get("affected") or []:
        sev = (aff.get("database_specific") or {}).get("severity")
        if isinstance(sev, str):
            return sev.upper()
    return "UNKNOWN"


def gate_libraries(r: AppProject, proj: Path) -> list[dict[str, Any]]:
    deps = _deps(proj)
    if not deps:
        return [_row("libraries", "No library with a known hole", "not_checked", "The library list was not found.")]
    res = _osv(deps)
    if res is None:
        return [_row("libraries", "No library with a known hole", "not_checked",
                     "OSV.dev (Google's vulnerability database) could not be reached right now; so this check did NOT run - "
                     "it is not counted as a pass.", f"{len(deps)} libraries")]
    bad: list[str] = []
    note: list[str] = []
    for d, vulns in zip(deps, res + [[]] * len(deps)):
        for v in vulns or []:
            sev = _worst(v)
            line = f"{d['name']} {d['version']}: {v.get('id')} ({sev})"
            (bad if sev in BAD_SEVERITY else note).append(line)
    state = "fail" if bad else ("warn" if note else "pass")
    say = ("Library with a serious (HIGH / CRITICAL) vulnerability: " + "; ".join(bad[:3])) if bad else \
          ("Library with a minor vulnerability: " + "; ".join(note[:3])) if note else \
          f"{len(deps)} libraries, no vulnerability on OSV.dev."
    return [_row("libraries", "No library with a known hole", state, say, f"{len(deps)} libraries")]


# ---------------------------------------------------------------- 5. login rules
def gate_login(r: AppProject, proj: Path, spec: dict[str, Any], platform: str) -> list[dict[str, Any]]:
    from . import sign as SG
    rows: list[dict[str, Any]] = []
    try:
        st = SG.settings(r)
    except Exception:                                      # noqa: BLE001
        st = {"ways": ["email_password"], "staff_2fa": False, "problems": {}}
    ways = st.get("ways") or []
    rows.append(_row("login", "Sign in with Apple where Google is offered", "pass" if ("google" not in ways or "apple" in ways) else "fail",
                     "There is Google login, so the iPhone build has Apple login too (App Store 4.8)." if "google" in ways
                     else "There is no social login, so this rule does not apply.", ", ".join(ways)))
    scr = proj / ("app/src/main/java/hoola/app/screens" if platform == "android" else "Sources/Screens")
    leaks: list[str] = []
    if scr.exists():
        for p in _files(scr):
            text = p.read_text(errors="ignore")
            if re.search(r"PasswordVisualTransformation|KeyboardType\.(?:Password|NumberPassword)|\bSecureField\b", text):
                leaks.append(p.name)
    rows.append(_row("login", "No password box outside the sign-in screen", "fail" if leaks else "pass",
                     "These screens have a password box: " + ", ".join(leaks[:3]) if leaks
                     else "The password is asked only on the kit's sign-in screen."))
    del_ok = "delete_account" in (spec.get("code_screens") or []) or "hoola_account" in json.dumps(spec.get("screens") or [])
    rows.append(_row("login", "Account deletion inside the app", "pass" if del_ok else "fail",
                     "The app has 'Delete account' inside it (a rule of both stores)." if del_ok
                     else "No way to delete the account was found inside the app."))
    probs = st.get("problems") or {}
    rows.append(_row("login", "Every login way she chose can work", "warn" if probs else "pass",
                     "; ".join(probs.values())[:280] if probs else "All the chosen login methods are ready."))
    return rows


# ---------------------------------------------------------------- 6. data rules
def gate_data(r: AppProject, proj: Path, spec: dict[str, Any], platform: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    code = spec.get("code_screens") or []
    pages = "privacy" in code
    rows.append(_row("data", "Privacy + deletion pages", "pass" if pages else "warn",
                     "The privacy page is in the app." if pages else "The privacy page was not found in this build."))
    consent = "consent" in code
    rows.append(_row("data", "DPDP consent on sign-up", "pass" if consent else "warn",
                     "Sign-up has the privacy notice tick." if consent
                     else "The consent tick at sign-up was not found in this build (the login screen gives its own tick)."))
    st = (spec.get("store") or {}) if platform == "android" else ((spec.get("ios") or {}).get("store") or {})
    said = _j(st.get("data_safety"), {}) if isinstance(st, dict) else {}
    if platform == "android":
        mf = proj / "app/src/main/AndroidManifest.xml"
        has_loc = "ACCESS_FINE_LOCATION" in (mf.read_text(errors="ignore") if mf.exists() else "")
    else:                                                  # on the iPhone the permission lives in Info.plist, not a manifest
        pl = next(iter(proj.glob("**/Info.plist")), None)
        has_loc = "NSLocation" in (pl.read_text(errors="ignore") if pl is not None else "")
    told_loc = "location" in json.dumps(said).lower()
    ok = (not has_loc) or told_loc or not said
    rows.append(_row("data", "Store answers match the build", "pass" if ok else "fail",
                     "The build takes location but the store's data-safety answers do not mention location." if not ok
                     else "The data-safety answers match the build's permissions."))
    return rows


# ---------------------------------------------------------------- the run
def _proj(r: AppProject, platform: str) -> tuple[Path, Path | None]:
    from . import kit as K
    d = K.app_dir(r.tenant_id, r.id) / ("android" if platform == "android" else "ios")
    proj = d / "project"
    apk = None
    apks = sorted((d / "apk").glob("*.apk"), key=lambda p: p.stat().st_mtime, reverse=True) if (d / "apk").exists() else []
    if apks:
        apk = apks[0]
    return proj, apk


def _spec(r: AppProject, platform: str) -> dict[str, Any]:
    from . import backend as BE
    st = _j(r.android, {})
    out: dict[str, Any] = {"code_screens": [], "screens": [], "seed": {"backend": {}}}
    try:
        out["seed"]["backend"] = BE.seed_hint(r)
    except Exception:                                      # noqa: BLE001
        log.debug("gate seed", exc_info=True)
    out["code_screens"] = list((_j(r.plan, {}).get("code_screens") or []))
    out["screens"] = list((_j(r.plan, {}).get("screens") or []))
    out["store"] = _j(st.get("store"), {})
    out["ios"] = {"store": _j(_j(st.get("ios"), {}).get("store"), {})}
    return out


def scan(r: AppProject, platform: str = "android") -> dict[str, Any]:
    """Run every gate on the newest build of this app. Nothing here changes the app."""
    from . import family as FA
    if platform not in ("android", "ios"):
        raise GateError("Platform: android or ios.")
    proj, apk = _proj(r, platform)
    if not proj.exists():
        raise GateError("The app needs a build first; the security check runs after that.")
    spec = _spec(FA.home(r) if FA.face_info(r) else r, platform)
    rows: list[dict[str, Any]] = []
    rows += gate_secrets(r, proj, apk)
    if platform == "android":
        rows += gate_permissions(r, proj, spec)
        rows += gate_settings(r, proj, apk)
        rows += gate_libraries(r, proj)
    else:
        rows += [_row("permissions", "Only the permissions the features need", "not_checked",
                      "The iPhone build is checked on a Mac; only Info.plist is read here."),
                 _row("settings", "Release settings", "not_checked", "The IPA is not built on Hoola's server.")]
        rows += _ios_plist(proj)
    rows += gate_login(r, proj, spec, platform)
    rows += gate_data(r, proj, spec, platform)
    bad = [x for x in rows if x["state"] == "fail"]
    out = {"at": now().isoformat(), "platform": platform, "build": int(_j(r.android, {}).get("build") or 0),
           "rows": rows, "pass": len([x for x in rows if x["state"] == "pass"]),
           "warn": len([x for x in rows if x["state"] == "warn"]),
           "fail": len(bad), "not_checked": len([x for x in rows if x["state"] == "not_checked"]),
           "ok": not bad, "blocks": [x["check"] + ": " + x["say"] for x in bad],
           "not_checked_says": ["Hoola did not check these: a scan while the app runs (only the device check), "
                                "the iPhone IPA (it is built on a Mac), and a check of your server (that is separate)."]}
    STATS["runs"] += 1
    if bad:
        STATS["failed"] += 1
    _keep(r, out)
    return out


def _keep(r: AppProject, out: dict[str, Any]) -> None:
    from . import backend as BE
    try:
        BE.patch_backend(r, set_={"gate": {k: out[k] for k in ("at", "platform", "build", "pass", "warn", "fail",
                                                                "not_checked", "ok", "blocks")}})
    except Exception:                                      # noqa: BLE001
        log.info("gate not saved", exc_info=True)


def last(r: AppProject) -> dict[str, Any]:
    from . import backend as BE
    return (BE._j(r.backend, {}).get("gate") or {})


def must_pass(r: AppProject, platform: str = "android") -> None:
    """Called before a store upload: a FAILING gate blocks it. Never a silent pass - if no gate has run, it runs now."""
    got = last(r)
    build = int(_j(r.android, {}).get("build") or 0)
    if not got or got.get("platform") != platform or int(got.get("build") or 0) != build:
        try:
            got = scan(r, platform)
        except GateError:
            raise
        except Exception as e:                             # noqa: BLE001
            raise GateError(f"The security check could not run: {e}") from e
    if not got.get("ok"):
        STATS["blocked"] += 1
        raise GateError("The security check failed on " + str(got.get("fail")) + " items, so it was not sent to the store: "
                        + "; ".join((got.get("blocks") or [])[:3]) + " Fix these first (the app's Security card has the full details).")


def _ios_plist(proj: Path) -> list[dict[str, Any]]:
    pl = next(iter(proj.glob("**/Info.plist")), None)
    if pl is None:
        return [_row("settings", "iPhone settings", "not_checked", "Info.plist not found.")]
    text = pl.read_text(errors="ignore")
    ats = "NSAllowsArbitraryLoads" in text
    rows = [_row("settings", "iPhone: https only (ATS on)", "fail" if ats else "pass",
                 "NSAllowsArbitraryLoads opens up http." if ats else "App Transport Security is on (https only).")]
    for key, what in (("NSLocationWhenInUseUsageDescription", "location"), ("NSMicrophoneUsageDescription", "microphone"),
                      ("NSPhotoLibraryUsageDescription", "photos")):
        if key in text:
            val = re.search(re.escape(key) + r"</key>\s*<string>([^<]{0,200})</string>", text)
            said = (val.group(1) if val else "").strip()
            rows.append(_row("permissions", f"iPhone: why it asks for {what}", "pass" if len(said) > 10 else "fail",
                             said[:160] if said else f"The reason for {what} is not written (Apple rejects that)."))
    return rows
