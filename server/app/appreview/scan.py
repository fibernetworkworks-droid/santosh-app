"""The readers: APK / AAB / bundle, source ZIP (or a GitHub zipball) and a website. Each returns
{kind, stack, facts, findings, limits}; a finding = {code, key, detail, evidence, sev?}. Nothing here runs the app or its code.
App Jaanch (app.appcheck) is reused for file sniffing, bundle unpacking, the signing block and (when REA is installed) as a
second way to read the manifest."""
from __future__ import annotations

import io
import json
import re
import ssl
import socket
import time
import zipfile
from datetime import date, datetime, timezone
from pathlib import PurePosixPath
from typing import Any, Callable
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET

from . import binfmt as B
from . import rules as R

MAX_ENTRY = 120 * 1024 * 1024        # biggest single entry we read (dex / .so)
MAX_TEXT = 2 * 1024 * 1024           # biggest source file we read
MAX_SOURCE_FILES = 20_000
MAX_SOURCE_BYTES = 300 * 1024 * 1024
EVIDENCE_PER_KEY = 5


class ScanError(Exception):
    pass


def F(code: str, key: str = "", detail: str = "", evidence: list[dict] | None = None, sev: str | None = None) -> dict[str, Any]:
    return {"code": code, "key": key or code, "detail": detail, "evidence": list(evidence or [])[:EVIDENCE_PER_KEY], "sev": sev}


def _ev(where: str, line: int | None = None, text: str = "") -> dict[str, Any]:
    e: dict[str, Any] = {"where": where[:200]}
    if line:
        e["line"] = line
    if text:
        e["text"] = text.strip()[:160]
    return e


def _int(v: Any) -> int | None:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


# ================================================================= manifest (binary, proto or plain)
SYSTEM_ACTION = re.compile(r"^android\.(?:intent\.action|net\.conn|app\.action|appwidget\.action|bluetooth|hardware|media|"
                           r"provider\.Telephony)")


def manifest_findings(root: ET.Element, where: str, today: date, sdk_hint: dict[str, int | None] | None = None,
                      opts: dict[str, Any] | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    a = B.a
    facts: dict[str, Any] = {"package": root.get("package", ""), "version_name": a(root, "versionName"),
                             "version_code": a(root, "versionCode")}
    out: list[dict[str, Any]] = []
    us = root.find("uses-sdk")
    mn = _int(a(us, "minSdkVersion")) if us is not None else None
    tg = _int(a(us, "targetSdkVersion")) if us is not None else None
    hint = sdk_hint or {}
    mn = mn if mn is not None else hint.get("min")
    tg = tg if tg is not None else hint.get("target")
    if tg is None and mn is not None:
        tg = mn                                               # Android's own default
    facts.update({"min_sdk": mn, "target_sdk": tg})
    perms = sorted({a(p, "name") for p in root.findall("uses-permission") + root.findall("uses-permission-sdk-23") if a(p, "name")})
    facts["permissions"] = perms
    app = root.find("application")
    ev = [_ev(where)]
    if tg is not None:
        need, keep = R.PLAY_TARGET["new_and_updates"], R.PLAY_TARGET["existing_min"]
        if today >= R.PLAY_TARGET["since"]:
            if tg < keep:
                out.append(F("target_sdk", detail=f"{tg} hai (chahiye {need}; {keep} se neeche app naye Android phones par naye "
                                                  f"logon ko dikhni band)", evidence=ev, sev="critical"))
            elif tg < need:
                out.append(F("target_sdk", detail=f"{tg} hai (naye update ke liye {need} chahiye)", evidence=ev, sev="high"))
        elif tg < need:
            out.append(F("target_sdk_soon", detail=f"{tg} hai, {R.PLAY_TARGET['since'].strftime('%d %b %Y')} se {need} chahiye",
                         evidence=ev))
    if mn is not None and mn < 23:
        out.append(F("min_sdk_old", detail=str(mn), evidence=ev))
    if app is not None:
        if a(app, "debuggable") == "true":
            out.append(F("debuggable", evidence=[_ev(where, text='android:debuggable="true"')]))
        if a(app, "testOnly") == "true":
            out.append(F("test_only", evidence=[_ev(where, text='android:testOnly="true"')]))
        ab = a(app, "allowBackup")
        if ab != "false" and not (a(app, "dataExtractionRules") or a(app, "fullBackupContent")):
            out.append(F("allow_backup", evidence=[_ev(where, text=f'android:allowBackup="{ab or "(likha nahi = true)"}"')]))
        ct = a(app, "usesCleartextTraffic")
        if ct == "true" or (not ct and not a(app, "networkSecurityConfig") and tg is not None and tg < 28):
            out.append(F("cleartext", evidence=[_ev(where, text=f'android:usesCleartextTraffic="{ct or "(target < 28: default true)"}"')]))
        facts["network_security_config"] = a(app, "networkSecurityConfig")
        facts["app_label"] = "" if a(app, "label").startswith("@") else a(app, "label")[:120]
        has_fgs_type = False
        n_exp = 0
        for comp in app:
            tag = comp.tag
            if tag not in ("activity", "activity-alias", "service", "receiver", "provider"):
                continue
            name = a(comp, "name") or a(comp, "targetActivity") or "?"
            if name.startswith("."):
                name = facts["package"] + name
            perm = a(comp, "permission")
            if tag == "service" and a(comp, "foregroundServiceType"):
                has_fgs_type = True
            if perm in R.COMPONENT_RULE:
                out.append(F(R.COMPONENT_RULE[perm], key=f"{R.COMPONENT_RULE[perm]}", detail=name,
                             evidence=[_ev(where, text=f"{tag} {name} {perm}")]))
            filters = comp.findall("intent-filter")
            exp = a(comp, "exported")
            if filters and not exp and tg is not None and tg >= 31 and tag != "provider":
                out.append(F("missing_exported", key=f"missing_exported:{name}", detail=f"{tag} {name}",
                             evidence=[_ev(where, text=f"<{tag} {name}> intent-filter, android:exported nahi")]))
                continue
            exported = exp == "true" or (not exp and filters and (tg is None or tg < 31))
            if tag == "provider":
                if exp == "true" and not (perm or a(comp, "readPermission") or a(comp, "writePermission")):
                    out.append(F("exported_provider", key=f"exported_provider:{name}", detail=name,
                                 evidence=[_ev(where, text=f'<provider {name} android:exported="true">')]))
                continue
            if not exported or perm or comp.get("enabled") == "false":
                continue
            actions = {a(x, "name") for f in filters for x in f.findall("action")}
            cats = {a(x, "name") for f in filters for x in f.findall("category")}
            if "android.intent.action.MAIN" in actions and ("android.intent.category.LAUNCHER" in cats or "android.intent.category.LEANBACK_LAUNCHER" in cats):
                continue
            if perm_protected(comp):
                continue
            sev = None
            if actions and all(SYSTEM_ACTION.match(x or "") for x in actions):
                sev = "low"
            elif "android.intent.category.BROWSABLE" in cats:
                sev = "low"
            n_exp += 1
            if n_exp <= 15:
                out.append(F("exported_component", key=f"exported_component:{name}", detail=f"{tag} {name}",
                             evidence=[_ev(where, text=f"<{tag} {name}> exported" + (f" ({', '.join(sorted(a for a in actions if a))[:100]})" if actions else ""))],
                             sev=sev))
        facts["exported_without_permission"] = n_exp
        if "android.permission.FOREGROUND_SERVICE" in perms and tg is not None and tg >= 34 and not has_fgs_type:
            out.append(F("fgs_types", detail="FOREGROUND_SERVICE hai par kisi service par foregroundServiceType nahi", evidence=ev))
        elif has_fgs_type:
            types = sorted({a(c, "foregroundServiceType") for c in app.findall("service") if a(c, "foregroundServiceType")})
            facts["foreground_service_types"] = types
    out += permission_findings(perms, where, facts)
    return facts, out


def perm_protected(comp: ET.Element) -> bool:
    return bool(B.a(comp, "permission"))


def permission_findings(perms: list[str], where: str, facts: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    short = [p.rsplit(".", 1)[-1] for p in perms if p.startswith(("android.permission.", "com.android."))]
    groups: dict[str, list[str]] = {}
    for p in short:
        code = R.PERM_RULE.get(p)
        if code:
            groups.setdefault(code, []).append(p)
    for code, ps in groups.items():
        out.append(F(code, detail=", ".join(ps), evidence=[_ev(where, text="uses-permission " + p) for p in ps]))
    data = sorted({R.SENSITIVE_PERMS[p] for p in short if p in R.SENSITIVE_PERMS})
    facts["data_from_permissions"] = data
    if data:
        out.append(F("perm_sensitive", detail=", ".join(data), evidence=[_ev(where, text=p) for p in short if p in R.SENSITIVE_PERMS]))
    if "com.google.android.gms.permission.AD_ID" in perms:
        out.append(F("ads_id", detail="AD_ID permission manifest mein hai", evidence=[_ev(where, text="com.google.android.gms.permission.AD_ID")]))
    return out


def nsc_findings(root: ET.Element, where: str) -> list[dict[str, Any]]:
    out = []
    if root.tag != "network-security-config":
        return out
    base = root.find("base-config")
    open_to = []
    if base is not None and B.a(base, "cleartextTrafficPermitted", base.get("cleartextTrafficPermitted", "")) == "true":
        open_to.append("base-config (sab domains)")
    for dc in root.findall("domain-config"):
        if dc.get("cleartextTrafficPermitted") == "true":
            open_to += [d.text or "?" for d in dc.findall("domain")][:3]
    if open_to:
        out.append(F("nsc_cleartext", detail=", ".join(open_to), evidence=[_ev(where, text="cleartextTrafficPermitted=true")]))
    for scope in [base] + root.findall("domain-config"):
        if scope is None:
            continue
        for c in scope.iter("certificates"):
            if c.get("src") == "user":
                out.append(F("nsc_user_certs", evidence=[_ev(where, text='<certificates src="user"/>')]))
                return out
    return out


# ================================================================= SDKs / secrets / derived policy findings
def sdk_findings(sdks: list[dict[str, Any]], facts: dict[str, Any], opts: dict[str, Any], login_hint: str,
                 evidence_of: dict[str, list[dict]]) -> list[dict[str, Any]]:
    out = []
    names = [s["name"] for s in sdks]
    facts["sdks"] = [{"name": s["name"], "kind": s["kind"]} for s in sdks]
    trackers = [s for s in sdks if s["kind"] in ("analytics", "ads", "attribution", "engagement", "crash", "push")]
    if trackers:
        out.append(F("trackers", detail=", ".join(f"{s['name']} ({s['kind']})" for s in trackers),
                     evidence=[x for s in trackers for x in evidence_of.get(s["name"], [])][:EVIDENCE_PER_KEY]))
    pay = [s for s in sdks if s["kind"] == "payment"]
    if pay:
        out.append(F("rbi_payment", detail="Mila: " + ", ".join(s["name"] for s in pay),
                     evidence=[x for s in pay for x in evidence_of.get(s["name"], [])][:EVIDENCE_PER_KEY]))
        if any(p.endswith(("READ_SMS", "RECEIVE_SMS")) for p in facts.get("permissions") or []):
            out.append(F("sms_and_payment"))
    ai = [s for s in sdks if s["kind"] == "ai"]
    if ai:
        out.append(F("ai_sdk", detail="Mila: " + ", ".join(s["name"] for s in ai),
                     evidence=[x for s in ai for x in evidence_of.get(s["name"], [])][:EVIDENCE_PER_KEY]))
    auth = [s for s in sdks if s["kind"] == "auth"]
    if auth or login_hint:
        out.append(F("account_deletion", detail=", ".join([s["name"] for s in auth] + ([f"'{login_hint}' screen"] if login_hint else []))))
    data = set(facts.get("data_from_permissions") or [])
    for s in sdks:
        data.update(s.get("data") or [])
    facts["data_safety"] = sorted(data)
    if data:
        out.append(F("data_safety", detail=", ".join(sorted(data))))
        out.append(F("dpdp_notice", detail=", ".join(sorted(data))[:300]))
    if opts.get("kids"):
        bad = [s["name"] for s in sdks if s["kind"] in ("ads", "attribution", "engagement", "analytics") and s["name"] not in R.FAMILIES_CERTIFIED_HINT]
        if bad or "com.google.android.gms.permission.AD_ID" in (facts.get("permissions") or []):
            out.append(F("families", detail="Tracking / ads SDK: " + (", ".join(bad) or "AD_ID permission")))
        out.append(F("dpdp_children"))
    out.append(F("content_rating"))
    return out


def secret_findings(text: str, where: str, line: int | None = None) -> list[dict[str, Any]]:
    out = []
    for pid, sev, label, masked in R.find_secrets(text):
        code = "public_key" if sev == "low" else "secret"
        out.append(F(code, key=f"{code}:{pid}:{masked}", detail=f"{label} ({masked})", evidence=[_ev(where, line, masked)], sev=sev))
    return out


def merge(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One finding per key; evidence joined."""
    by: dict[str, dict[str, Any]] = {}
    for f in findings:
        k = f["key"]
        if k in by:
            ev = by[k]["evidence"]
            for e in f["evidence"]:
                if e not in ev and len(ev) < EVIDENCE_PER_KEY:
                    ev.append(e)
        else:
            by[k] = dict(f)
    return list(by.values())


# ================================================================= APK / AAB
def _read(z: zipfile.ZipFile, info: zipfile.ZipInfo, cap: int = MAX_ENTRY) -> bytes:
    if info.file_size > cap:
        with z.open(info) as f:
            return f.read(cap)
    return z.read(info)


def _rea_manifest(path) -> str:
    """Second route: App Jaanch's locked-down REA (static) when it is installed. Never required."""
    try:
        from ..appcheck.runner import Session, apk_ready
        if not apk_ready():
            return ""
        with Session() as rea:
            staged = rea.stage(path, "app.apk")
            res = rea.call("inspect_android_package", {"path": str(staged), "detail": "complete"})
        nr = res.get("normalized_result") or {}
        nr = nr.get("summary") if isinstance(nr.get("summary"), dict) else nr
        return str(((nr.get("manifest") or {}).get("text")) or "")
    except Exception:
        return ""


def scan_android(path, name: str, opts: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    from ..appcheck import analyze as an
    today = today or date.today()
    out: dict[str, Any] = {"kind": "", "stack": "android", "facts": {}, "findings": [], "limits": []}
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError):
        raise ScanError("Yeh APK / AAB / ZIP file nahi lagti (khul nahi rahi).")
    with z:
        names = z.namelist()
        infos = {i.filename: i for i in z.infolist()}
        if "base/manifest/AndroidManifest.xml" in names:
            kind, pre = "aab", "base/"
            man_name = "base/manifest/AndroidManifest.xml"
        elif "AndroidManifest.xml" in names:
            kind, pre, man_name = "apk", "", "AndroidManifest.xml"
        else:
            raise ScanError("Is file mein AndroidManifest.xml nahi mila: APK / AAB nahi hai.")
        out["kind"] = kind
        findings: list[dict[str, Any]] = []
        root = None
        try:
            root = B.parse_any_xml(z.read(man_name))
        except B.FormatError:
            text = _rea_manifest(path) if kind == "apk" else ""
            if text:
                try:
                    root = ET.fromstring(text.encode())
                    out["limits"].append("Manifest App Jaanch (REA) se padha gaya.")
                except ET.ParseError:
                    root = None
        if root is None:
            raise ScanError("Manifest padha nahi ja saka (file tooti ho sakti hai).")
        facts, mf = manifest_findings(root, man_name, today, opts=opts)
        findings += mf
        # network security config (any res/xml whose root is network-security-config)
        for n in names:
            if n.startswith(pre + "res/xml/") and n.endswith(".xml") and infos[n].file_size < 200_000:
                try:
                    x = B.parse_any_xml(z.read(n))
                except (B.FormatError, ET.ParseError):
                    continue
                if x.tag == "network-security-config":
                    findings += nsc_findings(x, n)
        # signing (APK only; an AAB carries the upload key's v1 signature, Play re-signs)
        if kind == "apk":
            signer = an.apk_signer(path)
            facts["signature_schemes"] = signer.get("schemes") or []
            facts["signed_by"] = (signer.get("cert") or {}).get("subject", "")
            if not facts["signature_schemes"]:
                findings.append(F("unsigned", evidence=[_ev("META-INF / APK Signing Block")]))
            else:
                if "android debug" in facts["signed_by"].lower():
                    findings.append(F("debug_cert", evidence=[_ev("signing certificate", text=facts["signed_by"])]))
                if facts["signature_schemes"] == ["v1"] and (facts.get("target_sdk") or 0) >= 24:
                    findings.append(F("v1_only", evidence=[_ev("META-INF", text="sirf v1")]))
            out["limits"].append("Signature kisne kiya yeh file mein likha hua padha; cryptographic jaanch Android / Play karta hai.")
        # native libraries: 64-bit + 16 KB
        libs: dict[str, list[str]] = {}
        for n in names:
            m = re.match(rf"^{re.escape(pre)}lib/([^/]+)/([^/]+\.so)$", n)
            if m:
                libs.setdefault(m.group(1), []).append(m.group(2))
        facts["native_abis"] = sorted(libs)
        flutter = any("libflutter.so" in v for v in libs.values())
        rn = any(any(x in ("libreactnativejni.so", "libreactnative.so", "libhermes.so") for x in v) for v in libs.values())
        out["stack"] = "flutter" if flutter else "react_native" if rn or (pre + "assets/index.android.bundle") in names else "android"
        facts["built_with"] = {"flutter": "Flutter", "react_native": "React Native", "android": "Android (Kotlin / Java)"}[out["stack"]]
        if libs and ("armeabi-v7a" in libs or "x86" in libs) and "arm64-v8a" not in libs:
            findings.append(F("no_arm64", detail=", ".join(sorted(libs)), evidence=[_ev(pre + "lib/")]))
        bad16, badzip = [], []
        for abi in ("arm64-v8a", "x86_64"):
            for so in libs.get(abi, [])[:60]:
                n = f"{pre}lib/{abi}/{so}"
                info = infos[n]
                head = _read(z, info, 8 * 1024 * 1024)
                ei = B.elf_info(head)
                al = ei.get("load_align")
                if ei.get("elf") and al and al < 16384:
                    bad16.append(f"{abi}/{so} ({al // 1024 or al} {'KB' if al >= 1024 else 'B'})")
                if kind == "apk" and info.compress_type == zipfile.ZIP_STORED:
                    try:
                        with open(path, "rb") as fh:
                            fh.seek(info.header_offset + 26)
                            nl, xl = int.from_bytes(fh.read(2), "little"), int.from_bytes(fh.read(2), "little")
                        if (info.header_offset + 30 + nl + xl) % 16384:
                            badzip.append(f"{abi}/{so}")
                    except OSError:
                        pass
        if bad16:
            findings.append(F("page_16kb", detail=", ".join(bad16[:6]), evidence=[_ev(pre + "lib/" + b.split(" ")[0]) for b in bad16]))
        if badzip:
            findings.append(F("zip_align_16kb", detail=", ".join(badzip[:6]), evidence=[_ev(pre + "lib/" + b) for b in badzip]))
        # code: class prefixes + strings
        prefixes: set[str] = set()
        login_hint = ""
        ev_of: dict[str, list[dict]] = {}
        http_seen: list[str] = []
        dexes = [n for n in names if re.match(rf"^{re.escape(pre)}(?:dex/)?classes\d*\.dex$", n)]
        facts["dex_files"] = len(dexes)
        text_like = [n for n in names if (n.startswith(pre + "assets/") or n.startswith(pre + "res/raw/") or n == pre + "resources.arsc"
                                          or n.endswith("resources.pb") or n.endswith("libapp.so")) and infos[n].file_size <= MAX_ENTRY]
        for n in dexes + text_like:
            b = _read(z, infos[n])
            if n in dexes:
                for p in B.class_prefixes(b):
                    if p not in prefixes:
                        prefixes.add(p)
            blob = "\n".join(B.printable_strings(b))
            findings += secret_findings(blob, n)
            if not login_hint:
                m = R.LOGIN_WORDS.search(blob)
                login_hint = m.group(0) if m and not n.endswith(".dex") else login_hint
            for m in R.HTTP_URL.finditer(blob):
                u = m.group(1)
                if len(http_seen) < 8 and u not in http_seen and not u.startswith("http://schemas"):
                    http_seen.append(u)
        found = {}
        for p in prefixes:
            s = R.sdk_for_class(p)
            if s:
                found[s["name"]] = s
                ev_of.setdefault(s["name"], [_ev("classes*.dex", text=s["p"])])
        sdks = sorted(found.values(), key=lambda s: (s["kind"], s["name"]))
        if http_seen:
            findings.append(F("http_url", detail="http:// addresses: " + ", ".join(http_seen[:5]),
                              evidence=[_ev("dex / assets", text=u) for u in http_seen]))
        findings += sdk_findings(sdks, facts, opts, login_hint, ev_of)
        if opts.get("ios"):
            findings.append(F("apple_basics", detail="Isi app ka iPhone version ho to: account delete app ke andar (5.1.1(v)), Google / "
                                                     "Facebook login ke saath Sign in with Apple (4.8), har SDK ka privacy manifest."))
    out["facts"] = facts
    out["findings"] = merge(findings)
    out["limits"].append("Sirf file padhi gayi (static); app chalayi nahi gayi, isliye runtime ke khatre (server ki galti, login ki "
                         "kamzori) yahan nahi dikhenge.")
    return out


# ================================================================= source ZIP / repo
def _gradle_sdk(text: str) -> dict[str, int | None]:
    def g(pat: str) -> int | None:
        m = re.search(pat, text)
        return int(m.group(1)) if m else None
    return {"target": g(r"targetSdk(?:Version)?\s*(?:=|\s)\s*(\d{2})"), "min": g(r"minSdk(?:Version)?\s*(?:=|\s)\s*(\d{2})"),
            "compile": g(r"compileSdk(?:Version)?\s*(?:=|\s)\s*(\d{2})")}


def _deps_from(name: str, text: str) -> set[str]:
    found: set[str] = set()
    low = name.lower()
    if low.endswith("pubspec.yaml"):
        for m in re.finditer(r"^\s{2}([a-z0-9_]+)\s*:", text, re.M):
            found.add(m.group(1))
    elif low.endswith("package.json"):
        try:
            j = json.loads(text)
            for k in ("dependencies", "devDependencies"):
                found.update((j.get(k) or {}).keys())
        except ValueError:
            pass
    elif low.endswith((".gradle", ".gradle.kts", "libs.versions.toml")):
        for m in re.finditer(r"[\"']([\w.-]+):([\w.-]+)(?::[\w.+-]+)?[\"']", text):
            found.add(m.group(2))
        for m in re.finditer(r"module\s*=\s*\"[\w.-]+:([\w.-]+)\"", text):
            found.add(m.group(1))
    return found


def scan_source(path, name: str, opts: dict[str, Any], today: date | None = None, strip_top: bool = False) -> dict[str, Any]:
    today = today or date.today()
    out: dict[str, Any] = {"kind": "source", "stack": "android", "facts": {}, "findings": [], "limits": []}
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError):
        raise ScanError("ZIP khul nahi rahi.")
    findings: list[dict[str, Any]] = []
    facts: dict[str, Any] = {}
    with z:
        infos = [i for i in z.infolist() if not i.is_dir()]
        if len(infos) > MAX_SOURCE_FILES:
            out["limits"].append(f"Bahut files ({len(infos)}): pehli {MAX_SOURCE_FILES} padhi.")
            infos = infos[:MAX_SOURCE_FILES]

        def rel(n: str) -> str:
            if strip_top and "/" in n:
                return n.split("/", 1)[1]
            return n
        files = {rel(i.filename): i for i in infos}
        paths = list(files)
        low = {p.lower(): p for p in paths}
        if any(p.endswith("pubspec.yaml") for p in low):
            out["stack"] = "flutter"
        elif any(p.endswith("package.json") for p in low):
            pk = next(p for p in paths if p.lower().endswith("package.json"))
            try:
                body = z.read(files[pk]).decode("utf-8", "ignore")
            except Exception:
                body = ""
            out["stack"] = "react_native" if "react-native" in body else ("android" if any(p.endswith("build.gradle") or p.endswith("build.gradle.kts") for p in low) else "web")
        facts["built_with"] = {"flutter": "Flutter", "react_native": "React Native", "android": "Android (Kotlin / Java)", "web": "Web / JS"}[out["stack"]]
        sdk_hint: dict[str, int | None] = {}
        deps: set[str] = set()
        login_hint = ""
        total = 0
        manifests, nscs, plists = [], [], []
        http_seen: list[dict] = []
        code_hits: dict[str, list[dict]] = {}
        for p in paths:
            parts = PurePosixPath(p).parts
            if any(x in R.SKIP_DIRS for x in parts[:-1]):
                continue
            base = parts[-1] if parts else p
            suf = PurePosixPath(base).suffix.lower()
            if base in R.COMMITTED_SECRETS or suf in R.COMMITTED_EXT:
                if not base.endswith(".example") and "debug" not in base.lower():
                    lbl = R.COMMITTED_SECRETS.get(base) or R.COMMITTED_EXT.get(suf, base)
                    findings.append(F("env_committed", key=f"env_committed:{p}", detail=lbl, evidence=[_ev(p)]))
            if suf not in R.TEXT_EXT and base not in R.COMMITTED_SECRETS:
                continue
            info = files[p]
            if info.file_size > MAX_TEXT:
                continue
            total += info.file_size
            if total > MAX_SOURCE_BYTES:
                out["limits"].append("Code bahut bada tha: kuch files chhod di.")
                break
            text = z.read(info).decode("utf-8", "ignore")
            if base == "AndroidManifest.xml" and "/test/" not in p and "/androidTest/" not in p:
                manifests.append((p, text))
            if base.endswith(".xml") and "network-security-config" in text[:600]:
                nscs.append((p, text))
            if base == "Info.plist":
                plists.append((p, text))
            if base.startswith("build.gradle") and ("targetSdk" in text or "minSdk" in text) and ("/app/" in "/" + p or not sdk_hint):
                g = _gradle_sdk(text)
                sdk_hint = {k: (g.get(k) or sdk_hint.get(k)) for k in ("target", "min", "compile")}
            if base in ("pubspec.yaml", "package.json") or base.startswith("build.gradle") or base == "libs.versions.toml":
                deps |= _deps_from(base, text)
            if "/test/" in "/" + p or "/tests/" in "/" + p or base.endswith(("_test.dart", ".test.js", ".spec.ts", "Test.kt")):
                continue
            for ln, line in enumerate(text.splitlines(), 1):
                if len(line) > 2000:
                    line = line[:2000]
                for f in secret_findings(line, p, ln):
                    findings.append(f)
                for code, rx, _what in R.CODE_PATTERNS:
                    if rx.search(line):
                        lst = code_hits.setdefault(code, [])
                        if len(lst) < EVIDENCE_PER_KEY:
                            lst.append(_ev(p, ln, line))
                if len(http_seen) < 8:
                    for m in R.HTTP_URL.finditer(line):
                        http_seen.append(_ev(p, ln, m.group(1)))
                if not login_hint and suf in (".dart", ".kt", ".java", ".xml", ".jsx", ".tsx", ".js", ".swift"):
                    m = R.LOGIN_WORDS.search(line)
                    if m:
                        login_hint = m.group(0)
        facts["dependencies"] = sorted(deps)[:200]
        for code, ev in code_hits.items():
            findings.append(F(code, detail=f"{ev[0]['where']}:{ev[0].get('line', '')} ({len(ev)} jagah)", evidence=ev))
        if http_seen:
            findings.append(F("http_url", detail="http:// addresses: " + ", ".join(e["text"] for e in http_seen[:5]), evidence=http_seen))
        if manifests:
            mp, mt = sorted(manifests, key=lambda x: ("/main/" not in x[0], len(x[0])))[0]
            try:
                root = ET.fromstring(mt.encode())
                mf_facts, mf = manifest_findings(root, mp, today, sdk_hint=sdk_hint, opts=opts)
                facts.update(mf_facts)
                findings += mf
            except ET.ParseError:
                out["limits"].append(f"{mp} padha nahi gaya (XML galat).")
        elif sdk_hint.get("target") is not None:
            facts.update({"target_sdk": sdk_hint.get("target"), "min_sdk": sdk_hint.get("min")})
        for np_, nt in nscs:
            try:
                findings += nsc_findings(ET.fromstring(nt.encode()), np_)
            except ET.ParseError:
                pass
        for pp, pt in plists:
            if re.search(r"<key>NSAllowsArbitraryLoads</key>\s*<true/>", pt):
                findings.append(F("cleartext", key="cleartext:ios", evidence=[_ev(pp, text="NSAllowsArbitraryLoads = true")]))
        sdks, ev_of = [], {}
        for d in sorted(deps):
            nm = R.DEPS.get(d)
            if nm and nm not in [s["name"] for s in sdks]:
                sdks.append(R.SDK_BY_NAME[nm])
                ev_of[nm] = [_ev("dependencies", text=d)]
        findings += sdk_findings(sdks, facts, opts, login_hint, ev_of)
        if plists or opts.get("ios"):
            findings.append(F("apple_basics", detail="iPhone version: account delete app ke andar (5.1.1(v)), Google / Facebook login ke "
                                                     "saath Sign in with Apple (4.8), PrivacyInfo.xcprivacy + required-reason APIs."))
    facts["files"] = len(infos)
    out["facts"] = facts
    out["findings"] = merge(findings)
    out["limits"].append("Code sirf padha gaya (static), chalaya / build nahi kiya. Pattern se mili baatein developer se pakki karwaiye.")
    return out


def classify_zip(path, name: str = "") -> str:
    """apk | aab | apks | source"""
    from pathlib import Path

    from ..appcheck import analyze as an
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
    except (zipfile.BadZipFile, OSError):
        raise ScanError("File khul nahi rahi (APK / AAB / ZIP nahi).")
    if "base/manifest/AndroidManifest.xml" in names:
        return "aab"
    k = an.sniff(Path(path), name or str(path))
    if k in ("apk", "apks"):
        return k
    return "source"


# ================================================================= website (passive)
UA = "HoolaAppReview/1.0 (+owner-requested review)"
Fetcher = Callable[..., dict[str, Any]]


def http_fetch(url: str, *, method: str = "GET", follow: bool = False, limit: int = 2 * 1024 * 1024,
               headers: dict[str, str] | None = None) -> dict[str, Any]:
    """One request, public addresses only (checked by app.web), no cookies kept. -> {status, headers, cookies, body, url}"""
    import httpx
    from .. import web
    web._check_url(url)
    try:
        with httpx.Client(timeout=12, follow_redirects=False, transport=TRANSPORT,
                          headers={"User-Agent": UA, **(headers or {})}) as c:
            r = c.request(method, url)
            hops = 0
            while follow and r.is_redirect and hops < 4:
                nxt = urljoin(str(r.url), r.headers.get("location", ""))
                web._check_url(nxt)
                r = c.request(method, nxt)
                hops += 1
            body = r.content[:limit]
            return {"status": r.status_code, "headers": {k.lower(): v for k, v in r.headers.items()},
                    "cookies": r.headers.get_list("set-cookie"), "body": body, "url": str(r.url)}
    except httpx.HTTPError as e:
        return {"status": 0, "error": e.__class__.__name__, "headers": {}, "cookies": [], "body": b"", "url": url}


TRANSPORT = None          # tests put an httpx.MockTransport here


def cert_days(host: str) -> int | None:
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=8) as s, ctx.wrap_socket(s, server_hostname=host) as t:
            na = t.getpeercert().get("notAfter")
        end = datetime.strptime(na, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        return (end - datetime.now(timezone.utc)).days
    except Exception:
        return None


EXPOSED = [  # path, check(body) -> bool, what
    ("/.git/HEAD", lambda b: b.startswith(b"ref:") or re.match(rb"^[0-9a-f]{40}\s*$", b) is not None, "Git repo (.git) - poora source code"),
    ("/.git/config", lambda b: b"[core]" in b, "Git config"),
    ("/.env", lambda b: re.search(rb"(?m)^[A-Z][A-Z0-9_]{2,}=", b) is not None and b"<html" not in b[:300].lower(), ".env (keys / passwords)"),
    ("/.DS_Store", lambda b: b[:8] == b"\x00\x00\x00\x01Bud1", ".DS_Store (folder list)"),
    ("/phpinfo.php", lambda b: b"PHP Version" in b and b"phpinfo" in b.lower(), "phpinfo page"),
    ("/server-status", lambda b: b"Apache Server Status" in b, "Apache server-status"),
    ("/wp-config.php.bak", lambda b: b"DB_PASSWORD" in b, "WordPress config backup"),
    ("/backup.sql", lambda b: b"CREATE TABLE" in b or b"INSERT INTO" in b, "database backup (.sql)"),
    ("/.htpasswd", lambda b: re.search(rb"^[\w.-]+:\$(?:apr1|2y|2a)\$", b, re.M) is not None, ".htpasswd"),
]
_MIXED = re.compile(rb"<(?:script|img|iframe|audio|video|source|embed)\b[^>]*\bsrc\s*=\s*[\"'](http://[^\"']+)|"
                    rb"<link\b[^>]*rel\s*=\s*[\"']stylesheet[\"'][^>]*href\s*=\s*[\"'](http://[^\"']+)|"
                    rb"<form\b[^>]*action\s*=\s*[\"'](http://[^\"']+)", re.I)


def scan_web(host: str, verified: bool, fetch: Fetcher | None = None, certs: Callable[[str], int | None] | None = None,
             pause: float = 0.3) -> dict[str, Any]:
    fetch = fetch or http_fetch
    certs = certs or cert_days
    out: dict[str, Any] = {"kind": "web", "stack": "web", "facts": {"host": host, "verified": verified}, "findings": [], "limits": []}
    fs: list[dict[str, Any]] = []
    home = f"https://{host}/"
    r = fetch(home, follow=True)
    if not r.get("status"):
        fs.append(F("web_https", detail=f"https://{host} khul nahi rahi ({r.get('error', 'koi jawab nahi')}).", evidence=[_ev(home)]))
        out["findings"] = fs
        out["limits"].append("Website se jawab nahi mila; baaki jaanch nahi hui.")
        return out
    final = r.get("url") or home
    out["facts"].update({"status": r["status"], "final_url": final})
    if urlparse(final).scheme != "https":
        fs.append(F("web_https", detail=f"https par jaane par bhi page {final} par http mein khula.", evidence=[_ev(final)]))
    plain = fetch(f"http://{host}/", follow=False)
    loc = (plain.get("headers") or {}).get("location", "")
    if plain.get("status") and not (plain["status"] in (301, 302, 307, 308) and loc.startswith("https://")):
        fs.append(F("web_https", key="web_https:redirect", detail=f"http://{host} par jaane wale https par nahi bheje jaate "
                                                                  f"(jawab {plain.get('status')}).", evidence=[_ev(f"http://{host}/")], sev="medium"))
    h = r.get("headers") or {}
    out["facts"]["server"] = h.get("server", "")
    if "strict-transport-security" not in h:
        fs.append(F("web_hsts", evidence=[_ev(final, text="Strict-Transport-Security nahi")]))
    csp = h.get("content-security-policy", "")
    if not csp:
        fs.append(F("web_csp", evidence=[_ev(final, text="Content-Security-Policy nahi")]))
    if "x-frame-options" not in h and "frame-ancestors" not in csp:
        fs.append(F("web_frame", evidence=[_ev(final, text="X-Frame-Options / frame-ancestors nahi")]))
    if h.get("x-content-type-options", "").lower() != "nosniff":
        fs.append(F("web_nosniff", evidence=[_ev(final)]))
    if "referrer-policy" not in h:
        fs.append(F("web_referrer", evidence=[_ev(final)]))
    leak = [f"{k}: {h[k]}" for k in ("server", "x-powered-by", "x-aspnet-version") if k in h and re.search(r"\d", h[k])]
    if leak:
        fs.append(F("web_server_leak", detail="; ".join(leak), evidence=[_ev(final, text=x) for x in leak]))
    weak = []
    for c in r.get("cookies") or []:
        nm = c.split("=", 1)[0].strip()
        lc = c.lower()
        miss = [x for x, ok in (("Secure", "secure" in lc), ("HttpOnly", "httponly" in lc), ("SameSite", "samesite" in lc)) if not ok]
        if miss:
            weak.append(f"{nm} ({', '.join(miss)} nahi)")
    if weak:
        fs.append(F("web_cookie", detail=", ".join(weak[:5]), evidence=[_ev(final, text=w) for w in weak]))
    mixed = []
    for m in _MIXED.finditer(r.get("body") or b""):
        u = next(g for g in m.groups() if g).decode("ascii", "ignore")
        if u not in mixed:
            mixed.append(u)
    if mixed:
        fs.append(F("web_mixed", detail=", ".join(mixed[:4]), evidence=[_ev(final, text=u) for u in mixed]))
    days = certs(host)
    out["facts"]["cert_days_left"] = days
    if days is not None and days < 21:
        fs.append(F("web_cert", detail=f"SSL certificate {max(days, 0)} din mein khatam" + (" (khatam ho chuka)" if days < 0 else ""),
                    sev="high" if days < 3 else None))
    if verified:
        for p, check, what in EXPOSED:
            if pause:
                time.sleep(pause)
            x = fetch(f"https://{host}{p}", follow=False, limit=65536)
            if x.get("status") == 200 and check(x.get("body") or b""):
                fs.append(F("web_exposed", key=f"web_exposed:{p}", detail=f"{what} at https://{host}{p}", evidence=[_ev(f"https://{host}{p}")]))
        st = fetch(f"https://{host}/.well-known/security.txt", follow=False, limit=8192)
        if st.get("status") != 200 or b"contact:" not in (st.get("body") or b"").lower():
            fs.append(F("web_security_txt"))
    else:
        out["limits"].append("Domain abhi verify nahi hua: .git / .env jaisi khuli files ki jaanch sirf aapke verify kiye domain par hoti hai.")
    out["limits"].append("Sirf bahar se dikhne wali cheezein dekhi (headers, HTTPS, page); website par koi hamla / login try nahi kiya.")
    out["findings"] = merge(fs)
    return out
