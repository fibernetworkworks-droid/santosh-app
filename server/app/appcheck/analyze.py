"""Pure-Python checks around REA's results: what kind of file it is, who signed an APK (as stated in the file), Windows
version info, and the scam-pattern rules that turn facts into a plain English verdict. Nothing here runs the file."""
from __future__ import annotations

import hashlib
import re
import struct
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

ANDROID = "{http://schemas.android.com/apk/res/android}"

# ---------------------------------------------------------------- file kind
SCRIPT_EXT = {".scr": "high", ".hta": "high", ".vbs": "high", ".vbe": "high", ".js": "high", ".jse": "high", ".wsf": "high",
              ".lnk": "high", ".ps1": "medium", ".bat": "medium", ".cmd": "medium", ".msi": "medium", ".jar": "medium",
              ".sh": "medium", ".reg": "high"}
DOC_EXT = (".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".mp4", ".mp3", ".zip")


def sniff(path: Path, name: str) -> str:
    """apk | apks | exe | elf | macho | electron | zip | script | other"""
    low = name.lower()
    with path.open("rb") as f:
        head = f.read(8)
    if head[:2] == b"MZ":
        return "exe"
    if head[:4] == b"\x7fELF":
        return "elf"
    if head[:4] in (b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xca\xfe\xba\xbe"):
        return "macho"
    if low.endswith(".asar"):
        return "electron"
    if head[:2] == b"PK":
        try:
            with zipfile.ZipFile(path) as z:
                names = z.namelist()
        except (zipfile.BadZipFile, OSError):
            return "other"
        if "AndroidManifest.xml" in names and any(n.startswith("classes") and n.endswith(".dex") for n in names):
            return "apk"
        if any(n.lower().endswith(".apk") for n in names) and (low.endswith((".xapk", ".apks", ".apkm")) or
                                                                "manifest.json" in names or "toc.pb" in names):
            return "apks"
        return "zip"
    if Path(low).suffix in SCRIPT_EXT:
        return "script"
    return "other"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def base_apk(path: Path, out_dir: Path) -> tuple[Path | None, list[str]]:
    """From an .xapk / .apks bundle, pull out the main APK (base.apk or the biggest one)."""
    with zipfile.ZipFile(path) as z:
        apks = [i for i in z.infolist() if i.filename.lower().endswith(".apk") and not i.is_dir()]
        if not apks:
            return None, []
        pick = next((i for i in apks if Path(i.filename).name.lower() == "base.apk"), None) or max(apks, key=lambda i: i.file_size)
        if pick.file_size > 600 * 1024 * 1024:
            return None, [i.filename for i in apks]
        dst = out_dir / "base.apk"
        with z.open(pick) as src, dst.open("wb") as out:
            while chunk := src.read(1 << 20):
                out.write(chunk)
        return dst, [i.filename for i in apks]


def zip_listing(path: Path, limit: int = 400) -> list[dict[str, Any]]:
    out = []
    with zipfile.ZipFile(path) as z:
        for i in z.infolist()[:limit]:
            if not i.is_dir():
                out.append({"name": i.filename, "size": i.file_size})
    return out


# ---------------------------------------------------------------- scam lures in names
BRAND = re.compile(r"\b(sbi|yono|hdfc|icici|axis|kotak|pnb|canara|baroda|bob ?world|union ?bank|indusind|idfc|yes ?bank|"
                   r"federal ?bank|paytm|phonepe|phone ?pe|gpay|google ?pay|bhim|upi|aadhaar|aadhar|uidai|pan ?card|"
                   r"pm ?kisan|parivahan|rto|income ?tax|epfo|lic|india ?post|digilocker|npci|rbi)\b", re.I)
LURE = re.compile(r"\b(kyc|e ?kyc|rewards?|reward ?points?|challan|e ?challan|refund|bijli|electricity|light ?bill|"
                  r"customs|courier|fedex|dhl|blue ?dart|parcel|loan|credit ?card|cashback|lottery|prize|"
                  r"invitation|invite|wedding|shaadi|lagna|aamantran|subsidy|gas ?bill|update|apk ?file)\b", re.I)

OFFICIAL_PKGS = {
    "net.one97.paytm": "Paytm", "com.phonepe.app": "PhonePe", "com.google.android.apps.nbu.paisa.user": "Google Pay",
    "com.sbi.lotusintouch": "SBI YONO", "com.csam.icici.bank.imobile": "ICICI iMobile", "com.snapwork.hdfc": "HDFC Bank",
    "com.axis.mobile": "Axis Mobile", "in.gov.uidai.mAadhaarPlus": "mAadhaar", "com.digilocker.android": "DigiLocker",
    "in.org.npci.upiapp": "BHIM",
}


def _words(s: str) -> str:
    return re.sub(r"[_\-.+()\[\]]+", " ", s or "")


def name_lures(name: str) -> tuple[list[str], list[str]]:
    w = _words(Path(name).stem if "." in name else name)
    return sorted({m.group(1).lower() for m in BRAND.finditer(w)}), sorted({m.group(1).lower() for m in LURE.finditer(w)})


def double_extension(name: str) -> bool:
    low = name.lower()
    parts = low.rsplit(".", 2)
    return len(parts) == 3 and ("." + parts[1]) in DOC_EXT and ("." + parts[2]) in (".exe", ".scr", ".apk", ".com", ".bat",
                                                                                   ".cmd", ".js", ".vbs", ".hta", ".msi", ".lnk")


# ---------------------------------------------------------------- APK signer (as written in the file; not verified)
def _lp(b: bytes, off: int) -> tuple[bytes, int]:
    (n,) = struct.unpack_from("<I", b, off)
    return b[off + 4: off + 4 + n], off + 4 + n


def _cert_info(der: bytes) -> dict[str, Any]:
    out: dict[str, Any] = {"sha256": hashlib.sha256(der).hexdigest()}
    try:
        from cryptography import x509
        c = x509.load_der_x509_certificate(der)
        out["subject"] = c.subject.rfc4514_string()
        out["issuer"] = c.issuer.rfc4514_string()
        out["valid_from"] = c.not_valid_before_utc.date().isoformat()
        out["valid_to"] = c.not_valid_after_utc.date().isoformat()
    except Exception:
        pass
    return out


def apk_signer(path: Path) -> dict[str, Any]:
    """Reads the signing certificate the APK carries (v2/v3 signing block, else v1 META-INF). This tells who the file
    says signed it; Santosh does not cryptographically verify the signature (Android does that at install)."""
    schemes: list[str] = []
    cert = None
    try:
        size = path.stat().st_size
        with path.open("rb") as f:
            f.seek(max(0, size - 65_557))
            tail = f.read()
            eocd = tail.rfind(b"PK\x05\x06")
            if eocd >= 0:
                (cd_off,) = struct.unpack_from("<I", tail, eocd + 16)
                if cd_off >= 32:
                    f.seek(cd_off - 24)
                    footer = f.read(24)
                    if footer[8:] == b"APK Sig Block 42":
                        (blk,) = struct.unpack_from("<Q", footer, 0)
                        if 0 < blk < 64 * 1024 * 1024:
                            f.seek(cd_off - blk - 8)
                            block = f.read(blk + 8)
                            off, end = 8, len(block) - 24
                            while off + 12 <= end:
                                (ln,) = struct.unpack_from("<Q", block, off)
                                (pid,) = struct.unpack_from("<I", block, off + 8)
                                val = block[off + 12: off + 8 + ln]
                                if pid in (0x7109871A, 0xF05368C0, 0x1B93AD61):
                                    schemes.append({0x7109871A: "v2", 0xF05368C0: "v3", 0x1B93AD61: "v3.1"}[pid])
                                    if cert is None:
                                        try:
                                            signers, _ = _lp(val, 0)
                                            signer, _ = _lp(signers, 0)
                                            signed, _ = _lp(signer, 0)
                                            _digests, o = _lp(signed, 0)
                                            certs, _ = _lp(signed, o)
                                            der, _ = _lp(certs, 0)
                                            cert = _cert_info(der)
                                        except (struct.error, ValueError):
                                            pass
                                off += 8 + ln
        with zipfile.ZipFile(path) as z:
            sigs = [n for n in z.namelist() if re.match(r"META-INF/[^/]+\.(RSA|DSA|EC)$", n, re.I)]
            if sigs:
                schemes.insert(0, "v1")
                if cert is None:
                    try:
                        from cryptography.hazmat.primitives.serialization import pkcs7
                        from cryptography.hazmat.primitives.serialization import Encoding
                        certs = pkcs7.load_der_pkcs7_certificates(z.read(sigs[0]))
                        if certs:
                            cert = _cert_info(certs[0].public_bytes(Encoding.DER))
                    except Exception:
                        pass
    except (OSError, zipfile.BadZipFile, struct.error):
        pass
    return {"schemes": sorted(set(schemes), key=schemes.index), "cert": cert or {}, "verified": False}


# ---------------------------------------------------------------- APK manifest
DANGER_PERMS = {
    "READ_SMS": ("high", "can read your SMS (OTPs too)"),
    "RECEIVE_SMS": ("high", "can catch incoming SMS / OTPs"),
    "SEND_SMS": ("high", "can send SMS in your name"),
    "RECEIVE_MMS": ("medium", "can catch MMS"),
    "READ_CALL_LOG": ("high", "can read your call history"),
    "PROCESS_OUTGOING_CALLS": ("high", "can see / redirect your outgoing calls"),
    "REQUEST_INSTALL_PACKAGES": ("high", "can get other apps installed by itself"),
    "SYSTEM_ALERT_WINDOW": ("medium", "can show a fake screen over other apps"),
    "REQUEST_DELETE_PACKAGES": ("medium", "can ask to uninstall apps"),
    "READ_CONTACTS": ("medium", "can read your contacts"),
    "WRITE_CONTACTS": ("medium", "can change contacts"),
    "CALL_PHONE": ("medium", "can place a call without opening the dialer"),
    "READ_PHONE_STATE": ("medium", "can read the phone's identity / SIM details"),
    "READ_PHONE_NUMBERS": ("medium", "can read your mobile number"),
    "ANSWER_PHONE_CALLS": ("medium", "can answer / end calls"),
    "QUERY_ALL_PACKAGES": ("medium", "can see which bank / UPI apps are on the phone"),
    "MANAGE_EXTERNAL_STORAGE": ("medium", "can read / delete all files on the phone"),
    "WRITE_SETTINGS": ("medium", "can change phone settings"),
    "GET_ACCOUNTS": ("medium", "can see the accounts added to the phone"),
    "RECORD_AUDIO": ("low", "can record from the mic"),
    "CAMERA": ("low", "can use the camera"),
    "ACCESS_FINE_LOCATION": ("low", "can know your exact location"),
    "ACCESS_BACKGROUND_LOCATION": ("medium", "can get your location even when the app is closed"),
    "READ_MEDIA_IMAGES": ("low", "can read photos"),
    "READ_EXTERNAL_STORAGE": ("low", "can read files / photos"),
    "BODY_SENSORS": ("low", "can read health sensors"),
    "USE_FULL_SCREEN_INTENT": ("low", "can show a full screen on the lock screen"),
}
COMPONENT_PERMS = {
    "android.permission.BIND_ACCESSIBILITY_SERVICE": ("high", "accessibility service: can read the screen and tap by itself (this is what bank fraud apps ask for)"),
    "android.permission.BIND_DEVICE_ADMIN": ("high", "device admin: can lock / reset the phone and block its own uninstall"),
    "android.permission.BIND_NOTIFICATION_LISTENER_SERVICE": ("high", "can read all notifications (OTPs too)"),
    "android.permission.BIND_VPN_SERVICE": ("medium", "VPN: can route your internet traffic its own way"),
    "android.permission.BIND_INPUT_METHOD": ("medium", "keyboard: can see what you type"),
}


def manifest_facts(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {"launcher": None, "components": [], "sms_receiver": False, "debuggable": False,
                           "cleartext": False, "label": ""}
    if not text:
        return out
    try:
        root = ET.fromstring(text.encode("utf-8") if isinstance(text, str) else text)
    except ET.ParseError:
        out["launcher"] = bool(re.search(r"android\.intent\.category\.LAUNCHER", text))
        for perm, _ in COMPONENT_PERMS.items():
            if perm in text:
                out["components"].append(perm)
        out["sms_receiver"] = "android.provider.Telephony.SMS_RECEIVED" in text
        return out
    app = root.find("application")
    if app is not None:
        out["debuggable"] = app.get(ANDROID + "debuggable") == "true"
        out["cleartext"] = app.get(ANDROID + "usesCleartextTraffic") == "true"
        lab = app.get(ANDROID + "label") or ""
        out["label"] = "" if lab.startswith("@") else lab[:120]
        launcher = False
        for comp in app:
            perm = comp.get(ANDROID + "permission") or ""
            if perm in COMPONENT_PERMS and perm not in out["components"]:
                out["components"].append(perm)
            for f in comp.findall("intent-filter"):
                acts = {a.get(ANDROID + "name") for a in f.findall("action")}
                cats = {c.get(ANDROID + "name") for c in f.findall("category")}
                if comp.tag in ("activity", "activity-alias") and "android.intent.action.MAIN" in acts and \
                        "android.intent.category.LAUNCHER" in cats and comp.get(ANDROID + "enabled") != "false":
                    launcher = True
                if "android.provider.Telephony.SMS_RECEIVED" in acts or "android.provider.Telephony.SMS_DELIVER" in acts:
                    out["sms_receiver"] = True
        out["launcher"] = launcher
    return out


def _flag(level: str, text: str, code: str) -> dict[str, str]:
    return {"level": level, "text": text, "code": code}


def apk_flags(pkg: dict[str, Any], man: dict[str, Any], signer: dict[str, Any], name: str) -> list[dict[str, str]]:
    flags: list[dict[str, str]] = []
    perms = [p.rsplit(".", 1)[-1] for p in pkg.get("permissions") or [] if p.startswith("android.permission.")]
    for p in perms:
        if p in DANGER_PERMS:
            lvl, why = DANGER_PERMS[p]
            flags.append(_flag(lvl, why, f"perm:{p}"))
    for c in man.get("components") or []:
        lvl, why = COMPONENT_PERMS[c]
        flags.append(_flag(lvl, why, f"component:{c.rsplit('.', 1)[-1]}"))
    if man.get("sms_receiver") and not any(f["code"] == "perm:RECEIVE_SMS" for f in flags):
        flags.append(_flag("high", "is built to catch every incoming SMS", "sms_receiver"))
    if man.get("launcher") is False:
        flags.append(_flag("medium", "has no app icon: it can run hidden after install", "no_launcher"))
    if man.get("debuggable"):
        flags.append(_flag("medium", "is a test (debug) build, not like a real company's release", "debuggable"))
    try:
        tsdk = int(str(pkg.get("target_sdk") or "0"))
    except ValueError:
        tsdk = 0
    if 0 < tsdk < 29:
        flags.append(_flag("medium", f"is built for old Android (SDK {tsdk}); new apps do not come to the Play Store like this, "
                                     "fraud apps often do it to get permissions without asking", "old_target"))
    cert = signer.get("cert") or {}
    subj = (cert.get("subject") or "").lower()
    if not signer.get("schemes"):
        flags.append(_flag("high", "this APK has no signature (real apps are always signed)", "unsigned"))
    elif "android debug" in subj:
        flags.append(_flag("medium", "is signed with the Android Debug key (a developer's test build, not a company's)", "debug_cert"))
    brands, lures = name_lures(name)
    label_b, label_l = name_lures(man.get("label") or "")
    pid = str(pkg.get("package_name") or "")
    brands = sorted(set(brands) | set(label_b))
    lures = sorted(set(lures) | set(label_l))
    if pid in OFFICIAL_PKGS:
        flags.append(_flag("medium", f"the package name looks like the real {OFFICIAL_PKGS[pid]}, but the file did not come from the Play Store; "
                                     "install the real app only from the Play Store", "official_pkg_sideloaded"))
    elif brands:
        flags.append(_flag("high", f"the name contains '{', '.join(brands)}', but bank / UPI / government apps are never sent as an APK file "
                                   "on WhatsApp / SMS", "brand_lure"))
    elif lures:
        flags.append(_flag("high", f"the name contains '{', '.join(lures)}': APK files posing as KYC, a reward, a challan, an electricity bill, a courier or a wedding "
                                   "card are a common fraud method", "lure_name"))
    return flags


def verdict(flags: list[dict[str, str]]) -> str:
    hi = {f["code"] for f in flags if f["level"] == "high"}
    med = [f for f in flags if f["level"] == "medium"]
    sms = bool(hi & {"perm:READ_SMS", "perm:RECEIVE_SMS", "sms_receiver", "component:BIND_NOTIFICATION_LISTENER_SERVICE"})
    takeover = bool(hi & {"component:BIND_ACCESSIBILITY_SERVICE", "component:BIND_DEVICE_ADMIN"})
    lure = bool(hi & {"brand_lure", "lure_name", "double_ext"})
    hidden = any(f["code"] == "no_launcher" for f in flags)
    if lure or (sms and (takeover or hidden or "perm:REQUEST_INSTALL_PACKAGES" in hi)) or (takeover and hidden) or len(hi) >= 3:
        return "danger"
    if hi or len(med) >= 2:
        return "caution"
    return "clear"


# ---------------------------------------------------------------- Windows EXE
def pe_basics(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"signed": None, "arch": "", "dll": False, "gui": None}
    try:
        with path.open("rb") as f:
            mz = f.read(0x40)
            (lfanew,) = struct.unpack_from("<I", mz, 0x3C)
            f.seek(lfanew)
            hdr = f.read(24 + 240)
        if hdr[:4] != b"PE\0\0":
            return out
        machine, _n, _t, _p, _s, opt_size, chars = struct.unpack_from("<HHIIIHH", hdr, 4)
        out["arch"] = {0x14C: "x86 (32-bit)", 0x8664: "x64", 0xAA64: "ARM64"}.get(machine, hex(machine))
        out["dll"] = bool(chars & 0x2000)
        opt = hdr[24:]
        magic = struct.unpack_from("<H", opt, 0)[0]
        dd = 96 if magic == 0x10B else 112
        (subsys,) = struct.unpack_from("<H", opt, 68)
        out["gui"] = subsys == 2
        (sec_rva, sec_size) = struct.unpack_from("<II", opt, dd + 4 * 8)
        out["signed"] = bool(sec_rva and sec_size)
    except (OSError, struct.error):
        pass
    return out


def _vs_strings(b: bytes, off: int, end: int, out: dict[str, str], depth: int = 0) -> None:
    while off + 6 <= end and depth < 6:
        ln, vl, ty = struct.unpack_from("<HHH", b, off)
        if ln < 6:
            return
        blk_end = min(off + ln, end)
        p = off + 6
        k = p
        while k + 1 < blk_end and b[k:k + 2] != b"\0\0":
            k += 2
        key = b[p:k].decode("utf-16le", "ignore")
        p = (k + 2 + 3) & ~3
        vbytes = vl * 2 if ty == 1 else vl
        val = b[p:p + vbytes]
        if ty == 1 and vl and key not in ("VS_VERSION_INFO", "StringFileInfo", "VarFileInfo"):
            txt = val.decode("utf-16le", "ignore").rstrip("\0").strip()
            if txt and re.fullmatch(r"[A-Za-z]{2,40}", key):
                out[key] = txt[:200]
        child = (p + vbytes + 3) & ~3
        if child < blk_end:
            _vs_strings(b, child, blk_end, out, depth + 1)
        off = (blk_end + 3) & ~3


def pe_version_info(path: Path, resources: list[dict[str, Any]]) -> tuple[dict[str, str], str]:
    """VS_VERSIONINFO strings (company, product, description) and the requested execution level, from the payload
    locations REA reported."""
    info: dict[str, str] = {}
    level = ""
    try:
        with path.open("rb") as f:
            for r in resources or []:
                t = (r.get("type") or {}).get("id")
                loc = ((r.get("payload") or {}).get("location") or {})
                off, n = int(loc.get("offset") or 0), int(loc.get("bytes") or 0)
                if not off or not (0 < n <= 2 * 1024 * 1024):
                    continue
                if t == 16 and not info:
                    f.seek(off)
                    b = f.read(n)
                    _vs_strings(b, 0, len(b), info)
                elif t == 24 and not level:
                    f.seek(off)
                    m = re.search(rb'requestedExecutionLevel[^>]*level\s*=\s*["\'](\w+)', f.read(n))
                    level = m.group(1).decode() if m else ""
    except (OSError, ValueError, struct.error):
        pass
    keep = ("CompanyName", "ProductName", "FileDescription", "OriginalFilename", "FileVersion", "ProductVersion", "LegalCopyright")
    return {k: info[k] for k in keep if k in info}, level


def exe_flags(name: str, basics: dict[str, Any], vinfo: dict[str, str], level: str) -> list[dict[str, str]]:
    flags: list[dict[str, str]] = []      # (the double-extension trick is flagged once for every kind, in service._run)
    if basics.get("signed") is False:
        flags.append(_flag("medium", "this program has no company digital signature", "unsigned"))
    if level == "requireAdministrator":
        flags.append(_flag("medium", "asks for Administrator (control of the whole PC) as soon as it runs", "admin"))
    if not vinfo.get("CompanyName") and not vinfo.get("ProductName"):
        flags.append(_flag("low", "the file does not name a company / product", "no_version_info"))
    brands, lures = name_lures(name)
    if brands:
        flags.append(_flag("high", f"the name contains '{', '.join(brands)}': a bank / government office never sends an .exe file", "brand_lure"))
    elif lures and any(w in lures for w in ("kyc", "refund", "challan", "e challan", "lottery", "prize", "invitation", "wedding")):
        flags.append(_flag("high", f"the name contains '{', '.join(lures)}': programs with names like this are a common fraud method", "lure_name"))
    return flags


VERDICT_TEXT = {
    "danger": "This looks dangerous: do not install / open it.",
    "caution": "Be careful: some things do not look right.",
    "clear": "No major risk seen (this is not a guarantee).",
    "unknown": "The full check could not be completed.",
}
ADVICE = {
    "apk": "Install apps only from the Play Store. If someone sent you an APK on WhatsApp / SMS, do not open it, and if any app "
           "asks for accessibility or SMS permission, refuse. If you installed it by mistake and money was debited, "
           "call 1930 at once or file a complaint at cybercrime.gov.in.",
    "exe": "Download programs only from the company's official website. Do not run an .exe file that came by email / WhatsApp.",
    "script": "This file runs commands as soon as it is opened. Do not open it until you are sure who sent it and why.",
}
