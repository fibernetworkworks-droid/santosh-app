"""App Review Sahayak: static review of her APK / AAB / source ZIP / GitHub repo / website. Fixtures are built here byte by byte
(binary AXML manifest, aapt2 protobuf manifest, ELF headers, a fake DEX string table), so no Android tools are needed. GitHub and
the website are fakes; nothing is ever run."""
import asyncio
import io
import json
import struct
import sys
import types
import zipfile
from datetime import date, datetime, timezone
from xml.etree import ElementTree as ET

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.appreview.models  # noqa: F401  (tables for the env fixture's init_db)
from app.agent.tools import Ctx, ToolError
from tests.test_life import conv_ctx

SKL = "sk_" + "live_"  # fake Stripe-shaped prefix built at runtime (keeps push protection quiet)

T = "default"
NS = "http://schemas.android.com/apk/res/android"
TODAY = date(2026, 10, 23)


# ---------------------------------------------------------------- fixture builders
def axml(root: ET.Element) -> bytes:
    """ElementTree -> Android binary XML (UTF-16 string pool, typed attribute values)."""
    pool: list[str] = []

    def idx(s: str) -> int:
        if s not in pool:
            pool.append(s)
        return pool.index(s)
    idx("android")
    idx(NS)
    for el in root.iter():
        idx(el.tag)
        for k, v in el.attrib.items():
            idx(k.split("}")[-1])
            if not (v.lstrip("-").isdigit() or v in ("true", "false")):
                idx(v)
    data = b""
    offs = []
    for s in pool:
        offs.append(len(data))
        data += struct.pack("<H", len(s)) + s.encode("utf-16le") + b"\0\0"
    while len(data) % 4:
        data += b"\0"
    sp_hdr = 28
    sp = struct.pack("<HHIIIIII", 1, sp_hdr, sp_hdr + 4 * len(pool) + len(data), len(pool), 0, 0, sp_hdr + 4 * len(pool), 0)
    sp += struct.pack(f"<{len(pool)}I", *offs) + data
    body = struct.pack("<HHIIIII", 0x0100, 16, 24, 1, 0xFFFFFFFF, idx("android"), idx(NS))

    def emit(el: ET.Element) -> bytes:
        attrs = b""
        for k, v in el.attrib.items():
            uri = k[1:].split("}")[0] if k.startswith("{") else ""
            name = k.split("}")[-1]
            ns = idx(uri) if uri else 0xFFFFFFFF
            if v.lstrip("-").isdigit():
                raw, typ, d = 0xFFFFFFFF, 0x10, int(v) & 0xFFFFFFFF
            elif v in ("true", "false"):
                raw, typ, d = 0xFFFFFFFF, 0x12, 0xFFFFFFFF if v == "true" else 0
            else:
                raw, typ, d = idx(v), 0x03, idx(v)
            attrs += struct.pack("<IIIHBBI", ns, idx(name), raw, 8, 0, typ, d)
        n = len(el.attrib)
        out = struct.pack("<HHIII", 0x0102, 16, 36 + 20 * n, 1, 0xFFFFFFFF) + struct.pack("<IIHHHHHH", 0xFFFFFFFF, idx(el.tag), 20, 20, n, 0, 0, 0) + attrs
        for ch in el:
            out += emit(ch)
        return out + struct.pack("<HHIIIII", 0x0103, 16, 24, 1, 0xFFFFFFFF, 0xFFFFFFFF, idx(el.tag))
    body += emit(root) + struct.pack("<HHIIIII", 0x0101, 16, 24, 1, 0xFFFFFFFF, idx("android"), idx(NS))
    total = 8 + len(sp) + len(body)
    return struct.pack("<HHI", 3, 8, total) + sp + body


def _v(n: int) -> bytes:
    out = b""
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out += bytes([b | 0x80])
        else:
            return out + bytes([b])


def _ld(f: int, payload: bytes) -> bytes:
    return _v(f << 3 | 2) + _v(len(payload)) + payload


def proto_xml(el: ET.Element) -> bytes:
    e = _ld(3, el.tag.encode())
    for k, v in el.attrib.items():
        uri = k[1:].split("}")[0] if k.startswith("{") else ""
        e += _ld(4, (_ld(1, uri.encode()) if uri else b"") + _ld(2, k.split("}")[-1].encode()) + _ld(3, v.encode()))
    for ch in el:
        e += _ld(5, proto_xml(ch))
    return _ld(1, e)


def elf(align: int) -> bytes:
    hdr = b"\x7fELF" + bytes([2, 1, 1]) + b"\0" * 9
    hdr += struct.pack("<HHIQQQIHHHHHH", 3, 183, 1, 0, 64, 0, 0, 64, 56, 1, 0, 0, 0)
    ph = struct.pack("<IIQQQQQQ", 1, 5, 0, 0, 0, 0x1000, 0x1000, align)
    return hdr + ph + b"\0" * 64


def A(name: str) -> str:
    return "{%s}%s" % (NS, name)


def manifest(target: int = 34, minsdk: int = 21, bad: bool = True) -> ET.Element:
    m = ET.Element("manifest", {"package": "com.ingle.dukaan", A("versionCode"): "12", A("versionName"): "1.2" if bad else "1.3"})
    ET.SubElement(m, "uses-sdk", {A("minSdkVersion"): str(minsdk), A("targetSdkVersion"): str(target)})
    perms = ["INTERNET", "ACCESS_FINE_LOCATION", "CAMERA"] + (["READ_SMS", "QUERY_ALL_PACKAGES", "FOREGROUND_SERVICE"] if bad else [])
    for p in perms:
        ET.SubElement(m, "uses-permission", {A("name"): "android.permission." + p})
    if bad:
        ET.SubElement(m, "uses-permission", {A("name"): "com.google.android.gms.permission.AD_ID"})
    app_attrs = {A("label"): "Ingle Dukaan"}
    if bad:
        app_attrs.update({A("debuggable"): "true", A("usesCleartextTraffic"): "true", A("networkSecurityConfig"): "@xml/network_security_config"})
    else:
        app_attrs.update({A("allowBackup"): "false"})
    app = ET.SubElement(m, "application", app_attrs)
    main = ET.SubElement(app, "activity", {A("name"): ".Main", A("exported"): "true"})
    f = ET.SubElement(main, "intent-filter")
    ET.SubElement(f, "action", {A("name"): "android.intent.action.MAIN"})
    ET.SubElement(f, "category", {A("name"): "android.intent.category.LAUNCHER"})
    if bad:
        ET.SubElement(app, "activity", {A("name"): ".PayActivity", A("exported"): "true"})
        svc = ET.SubElement(app, "service", {A("name"): ".SyncService"})
        sf = ET.SubElement(svc, "intent-filter")
        ET.SubElement(sf, "action", {A("name"): "com.ingle.SYNC"})
        ET.SubElement(app, "provider", {A("name"): ".DataProvider", A("authorities"): "com.ingle.data", A("exported"): "true"})
    return m


def nsc() -> ET.Element:
    n = ET.Element("network-security-config")
    b = ET.SubElement(n, "base-config", {"cleartextTrafficPermitted": "true"})
    ta = ET.SubElement(b, "trust-anchors")
    ET.SubElement(ta, "certificates", {"src": "system"})
    ET.SubElement(ta, "certificates", {"src": "user"})
    return n


DEX_BAD = (b"dex\n035\0" + b"\0" * 40 + b"Lcom/appsflyer/AppsFlyerLib;\0Lcom/razorpay/Checkout;\0Landroidx/core/app/A;\0"
           b"Lcom/google/firebase/analytics/FirebaseAnalytics;\0AKIAQWERTYUIOPASDFGH\0https://api.ingle.in\0")
DEX_OK = b"dex\n035\0" + b"\0" * 40 + b"Lcom/razorpay/Checkout;\0Landroidx/core/app/A;\0"


def apk(bad: bool = True, target: int = 34) -> bytes:
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("AndroidManifest.xml", axml(manifest(target=target, minsdk=21 if bad else 26, bad=bad)))
        z.writestr("classes.dex", DEX_BAD if bad else DEX_OK)
        if bad:
            z.writestr("res/xml/network_security_config.xml", axml(nsc()))
            z.writestr("assets/config.json", '{"stripe": "' + SKL + '51Habcdefghijklmnopqrstuv", "maps": "AIzaSyA1234567890abcdefghijklmnopqrstuv"}')
            z.writestr("assets/ui.txt", "Sign in with mobile OTP")
        zi = zipfile.ZipInfo("lib/arm64-v8a/libnative.so")
        zi.compress_type = zipfile.ZIP_STORED
        z.writestr(zi, elf(0x1000 if bad else 0x4000))
        z.writestr("META-INF/CERT.RSA", b"not-a-cert")
    return bio.getvalue()


def aab() -> bytes:
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        z.writestr("base/manifest/AndroidManifest.xml", proto_xml(manifest(target=36, minsdk=26, bad=False)))
        z.writestr("base/dex/classes.dex", DEX_OK)
        z.writestr("base/lib/arm64-v8a/libok.so", elf(0x4000))
        z.writestr("BundleConfig.pb", b"")
    return bio.getvalue()


def source_zip(fixed: bool = False) -> bytes:
    bio = io.BytesIO()
    p = "myshop/"
    with zipfile.ZipFile(bio, "w") as z:
        z.writestr(p + "pubspec.yaml", "name: myshop\ndependencies:\n  flutter:\n    sdk: flutter\n  razorpay_flutter: ^1.3.7\n"
                                       "  firebase_analytics: ^11.0.0\n  google_sign_in: ^6.2.1\n")
        z.writestr(p + "android/app/build.gradle", "android {\n  compileSdk 35\n  defaultConfig {\n    minSdkVersion 23\n"
                                                   f"    targetSdkVersion {36 if fixed else 35}\n  }}\n")
        perms = "" if fixed else '<uses-permission android:name="android.permission.READ_CALL_LOG"/>'
        z.writestr(p + "android/app/src/main/AndroidManifest.xml",
                   f'<manifest xmlns:android="{NS}" package="in.myshop.app">{perms}<application android:label="MyShop" '
                   'android:allowBackup="false"><activity android:name=".MainActivity" android:exported="true"><intent-filter>'
                   '<action android:name="android.intent.action.MAIN"/><category android:name="android.intent.category.LAUNCHER"/>'
                   '</intent-filter></activity></application></manifest>')
        body = ["import 'dart:io';", "class Api {", "  final base = 'https://api.myshop.in/v1';"]
        if not fixed:
            body += ["  void setup(HttpClient client) {", "    client.badCertificateCallback = (cert, host, port) => true;", "  }",
                     "  const key = '" + SKL + "51Hzyxwvutsrqponmlkjihgf';", "  final old = 'http://api.myshop.in/legacy';"]
        body += ["}", "// Login screen: Sign in with phone"]
        z.writestr(p + "lib/api.dart", "\n".join(body) + "\n")
        if not fixed:
            z.writestr(p + ".env", "RAZORPAY_KEY_SECRET=abcd1234abcd1234abcd\n")
        z.writestr(p + "ios/Runner/Info.plist", "<plist><dict><key>NSAppTransportSecurity</key><dict><key>NSAllowsArbitraryLoads</key>"
                                                f"<{'false' if fixed else 'true'}/></dict></dict></plist>")
        z.writestr(p + "node_modules/x/index.js", "const k = '" + SKL + "51Hshouldnotbeseenatallxxxx';")
    return bio.getvalue()


# ---------------------------------------------------------------- fixtures
@pytest.fixture
def ar(env, monkeypatch, tmp_path):
    from app.appreview import service as S
    monkeypatch.setenv("APPREVIEW_DIR", str(tmp_path / "appreview"))
    events = []
    monkeypatch.setattr(S, "_publish", lambda tenant, kind, payload, conv="": events.append((kind, payload)))
    S.EVENTS = events
    return S


def keys(v):
    return {r["key"] for r in v["risks"]}


def codes(v):
    return {r["code"] for r in v["risks"]}


def risk(v, code):
    return next(r for r in v["risks"] if r["code"] == code)


# ---------------------------------------------------------------- tests
def test_binary_readers():
    from app.appreview import binfmt as B
    root = B.parse_axml(axml(manifest()))
    assert root.tag == "manifest" and root.get("package") == "com.ingle.dukaan"
    assert B.a(root.find("uses-sdk"), "targetSdkVersion") == "34" and B.a(root.find("application"), "debuggable") == "true"
    p = B.parse_proto_xml(proto_xml(manifest(target=36, bad=False)))
    assert B.a(p.find("uses-sdk"), "targetSdkVersion") == "36" and B.a(p.find("application"), "allowBackup") == "false"
    assert B.elf_info(elf(0x1000))["load_align"] == 4096 and B.elf_info(elf(0x4000))["load_align"] == 16384
    assert {"com.appsflyer", "com.razorpay"} <= B.class_prefixes(DEX_BAD)
    from app.appreview import rules as R
    found = {x[0] for x in R.find_secrets('x = "AKIAQWERTYUIOPASDFGH"; password = "hunter2hunter2"; key="your_api_key_here"')}
    assert found == {"aws", "generic"}
    assert R.find_secrets('password = "xxxxxxxxxx"') == []
    assert R.sdk_for_class("com.razorpay.Checkout")["name"] == "Razorpay" and R.sdk_for_class("com.razorpayx") is None
    for code, rl in R.RULES.items():           # every rule is complete and its sources exist
        assert rl["title"] and rl["explain"] and rl["fix"] and rl["area"] in R.AREAS and rl["sev"] in R.SEVERITIES, code
        assert all(r in R.SOURCES for r in rl["refs"]), code


def test_apk_review_explains_and_fixes(ar, monkeypatch):
    S = ar
    S.save_settings(T, kids=True, ios=True)
    up = S.upload(T, "ingle-dukaan-1.2.apk", apk(bad=True))
    v = S.review_file(T, up["file"], today=TODAY)
    c = codes(v)
    must = {"target_sdk", "min_sdk_old", "debuggable", "allow_backup", "cleartext", "nsc_cleartext", "nsc_user_certs",
            "exported_component", "missing_exported", "exported_provider", "fgs_types", "perm_sms", "perm_query_all", "perm_sensitive",
            "ads_id", "v1_only", "page_16kb", "zip_align_16kb", "secret", "public_key", "trackers", "rbi_payment", "sms_and_payment",
            "account_deletion", "data_safety", "dpdp_notice", "dpdp_children", "families", "content_rating", "apple_basics"}
    assert must <= c, must - c
    assert v["kind"] == "apk" and v["number"] == "AR-0001" and v["facts"]["package"] == "com.ingle.dukaan"
    t = risk(v, "target_sdk")
    assert t["sev"] == "critical" and "36" in t["explain"] and t["sources"][0]["url"].startswith("https://developer.android.com")
    assert t["snippet"]["lang"] == "kotlin" and "targetSdk = 36" in t["snippet"]["code"]
    sec = [r for r in v["risks"] if r["code"] == "secret"]
    assert sec and all("…" in r["evidence"][0]["text"] for r in sec)            # masked, never the full key
    assert "AKIAQWERTYUIOPASDFGH" not in json.dumps(v) and (SKL + "51Habcdefghijklmnopqrstuv") not in json.dumps(v)
    assert {"exported_component:com.ingle.dukaan.PayActivity", "exported_provider:com.ingle.dukaan.DataProvider",
            "missing_exported:com.ingle.dukaan.SyncService"} <= keys(v)
    assert not any("Main" in k for k in keys(v) if k.startswith("exported_component"))
    assert v["risks"][0]["sev"] == "critical" and v["score"] < 30
    assert {"AppsFlyer", "Razorpay", "Google Firebase Analytics"} <= {s["name"] for s in v["facts"]["sdks"]}
    assert S.EVENTS[-1][0] == "appreview_report" and S.EVENTS[-1][1]["top"]
    # second version of the same app: compared with the first
    up2 = S.upload(T, "ingle-dukaan-1.3.apk", apk(bad=False, target=36))
    v2 = S.review_file(T, up2["file"], today=TODAY)
    fixed = {f["key"] for f in v2["compare"]["fixed"]}
    assert v2["compare"]["previous"] == "AR-0001" and {"target_sdk", "debuggable", "perm_sms", "page_16kb", "allow_backup"} <= fixed
    assert v2["score"] > v["score"] and "target_sdk" not in codes(v2) and "theek hue" in v2["say"]
    assert all(r["change"] == "still_open" for r in v2["risks"] if r["code"] == "rbi_payment")


def test_aab_and_bundle_reading(ar):
    S = ar
    up = S.upload(T, "dukaan.aab", aab())
    v = S.review_file(T, up["file"], today=TODAY)
    assert v["kind"] == "aab" and v["facts"]["target_sdk"] == 36 and v["facts"]["native_abis"] == ["arm64-v8a"]
    c = codes(v)
    assert "target_sdk" not in c and "page_16kb" not in c and "unsigned" not in c and "debuggable" not in c
    assert "rbi_payment" in c and "allow_backup" not in c
    with pytest.raises(S.ReviewError):
        S.upload(T, "notes.txt", b"hello")


def test_source_zip_and_repo(ar, monkeypatch):
    S = ar
    up = S.upload(T, "myshop-src.zip", source_zip())
    v = S.review_file(T, up["file"], today=TODAY)
    c = codes(v)
    assert v["kind"] == "source" and v["stack"] == "flutter"
    assert {"target_sdk", "perm_call_log", "weak_tls", "secret", "http_url", "env_committed", "cleartext", "rbi_payment", "trackers",
            "account_deletion", "apple_basics"} <= c, c
    tls = risk(v, "weak_tls")
    assert tls["evidence"][0]["where"] == "lib/api.dart" and tls["evidence"][0]["line"] == 5 and tls["sev"] == "critical"
    assert tls["snippet"]["lang"] == "dart"
    assert risk(v, "target_sdk")["sev"] == "high"                      # 35: listing stays, updates need 36
    assert not any("node_modules" in e["where"] for r in v["risks"] for e in r["evidence"])
    assert any(r["key"] == "env_committed:.env" for r in v["risks"])
    # GitHub (read-only token, typed only in the app)
    from app.appreview import service as svc
    calls = []

    def gh(req: httpx.Request):
        calls.append((req.method, req.url.path, req.headers.get("authorization", "")))
        if req.url.path == "/user":
            tok = req.headers.get("authorization", "")
            return httpx.Response(200, json={"login": "meghana"}, headers={"x-oauth-scopes": "repo"} if "ghp_" in tok else {})
        if req.url.path == "/repos/ingle/myshop":
            return httpx.Response(200, json={"default_branch": "main", "private": True})
        if req.url.path == "/repos/ingle/myshop/zipball/main":
            return httpx.Response(200, content=source_zip(fixed=True))
        return httpx.Response(404, json={"message": "Not Found"})
    monkeypatch.setattr(svc, "GH_TRANSPORT", httpx.MockTransport(gh))
    with pytest.raises(S.ReviewError, match="likha ja sakta"):
        S.set_github(T, "ghp_" + "a" * 36)                              # classic token with write scope refused
    tok = "github_pat_" + "B" * 40
    out = S.set_github(T, tok)
    assert out["github"]["label"] == "@meghana"
    from app.appreview.models import AppReviewSettings
    from app.db import session
    with session() as s:
        assert tok not in s.get(AppReviewSettings, T).gh_sealed
    assert tok not in json.dumps(S.settings(T))
    r = S.review_repo(T, "https://github.com/ingle/myshop", today=TODAY)
    assert r["kind"] == "repo" and r["facts"]["repo"] == "ingle/myshop" and calls[-1][2] == f"Bearer {tok}"
    assert "weak_tls" not in codes(r) and "env_committed" not in codes(r) and "target_sdk" not in codes(r)
    # tool never takes a token in chat
    from app.agent import appreview_tools as AT
    ctx = conv_ctx()
    with pytest.raises(ToolError, match="Token chat"):
        asyncio.run(AT.app_review(ctx, "repo", repo="ingle/myshop", ref=tok))


def _site(verified_token=""):
    calls = []

    def fetch(url, *, method="GET", follow=False, limit=0, headers=None):
        calls.append(url)
        if url == "https://ingle.in/":
            return {"status": 200, "url": url, "headers": {"server": "nginx/1.18.0", "x-powered-by": "PHP/7.4.3"},
                    "cookies": ["sid=abc; Path=/"], "body": b'<html><img src="http://cdn.ingle.in/logo.png"><script src="/a.js"></script></html>'}
        if url == "http://ingle.in/":
            return {"status": 200, "url": url, "headers": {}, "cookies": [], "body": b"<html></html>"}
        if url.startswith("https://cloudflare-dns.com/"):
            ans = [{"data": f'"hoola-verify={verified_token}"'}] if verified_token else []
            return {"status": 200, "url": url, "headers": {}, "cookies": [], "body": json.dumps({"Answer": ans}).encode()}
        if url == "https://ingle.in/.git/HEAD":
            return {"status": 200, "url": url, "headers": {}, "cookies": [], "body": b"ref: refs/heads/main\n"}
        if url == "https://ingle.in/.env":
            return {"status": 200, "url": url, "headers": {}, "cookies": [], "body": b"<html>Not found page</html>"}
        return {"status": 404, "url": url, "headers": {}, "cookies": [], "body": b""}
    return fetch, calls


def test_website_passive_and_verified(ar):
    S = ar
    fetch, calls = _site()
    v = S.review_web(T, "https://ingle.in/shop", fetch=fetch, certs=lambda h: 10, pause=0)
    c = codes(v)
    assert {"web_https", "web_hsts", "web_csp", "web_frame", "web_nosniff", "web_server_leak", "web_cookie", "web_mixed", "web_cert"} <= c
    assert not any("/.git" in u or "/.env" in u for u in calls)          # not verified: no exposed-file probes
    assert any("verify nahi" in x for x in v["limits"])
    d = S.domain_add(T, "ingle.in")
    assert d["how"]["dns"]["name"] == "_hoola.ingle.in" and not d["verified"]
    assert not S.domain_verify(T, "ingle.in", fetch=_site()[0])["verified"]
    fetch2, calls2 = _site(d["how"]["dns"]["value"].split("=", 1)[1])
    assert S.domain_verify(T, "ingle.in", fetch=fetch2)["verified"]
    v2 = S.review_web(T, "ingle.in", fetch=fetch2, certs=lambda h: 90, pause=0)
    ex = [r for r in v2["risks"] if r["code"] == "web_exposed"]
    assert [r["key"] for r in ex] == ["web_exposed:/.git/HEAD"] and ex[0]["sev"] == "critical"   # .env was an HTML 404 page
    assert "web_cert" not in codes(v2) and {f["key"] for f in v2["compare"]["fixed"]} >= {"web_cert"}
    with pytest.raises(S.ReviewError):
        S.review_web(T, "not a site", fetch=fetch)


def test_mark_files_handoff_tap_only(ar, monkeypatch):
    S = ar
    v = S.review_file(T, S.upload(T, "app.apk", apk())["file"], today=TODAY)
    with pytest.raises(S.ReviewError, match="wajah"):
        S.mark(T, v["number"], "target_sdk", "ignored")
    m = S.mark(T, v["number"], "perm_query_all", "ignored", "Launcher app hai, Play declaration bhara hai")
    assert next(r for r in m["risks"] if r["key"] == "perm_query_all")["status"] == "ignored" and m["score"] >= v["score"]
    again = S.review_file(T, S.upload(T, "app.apk", apk())["file"], today=TODAY)
    assert next(r for r in again["risks"] if r["key"] == "perm_query_all")["status"] == "ignored"   # her decision is kept
    files = S.report_files(T, again["id"])
    names = [f["name"] for f in files["files"]]
    assert any(n.endswith(".pdf") for n in names) and any(n.endswith(".xlsx") for n in names) and any(n.endswith(".md") for n in names)
    md = S.fix_list_md(S.get(T, again["id"]))
    assert "targetSdk = 36" in md
    assert not any(t["key"] == "perm_query_all" for t in S.fix_list(S.get(T, again["id"])))
    # hand-off: the tool only makes the card
    from app.agent import appreview_tools as AT
    ctx = conv_ctx()
    card = asyncio.run(AT.app_review(ctx, "handoff", review=again["number"]))
    assert card["status"] == "needs_tap" and S.EVENTS[-1][0] == "appreview_handoff"
    with pytest.raises(S.ReviewError):
        S.handoff_decide(T, card["id"], True, card["hash"])               # not from a tap
    with pytest.raises(S.ReviewError, match="purana"):
        S.handoff_decide(T, card["id"], True, "x" * 64, by_tap=True)
    got = []
    pkg = types.ModuleType("app.devsahayak")
    mod = types.ModuleType("app.devsahayak.service")
    mod.tasks_from_review = lambda tenant, payload: (got.append(payload), {"tasks": len(payload["tasks"])})[1]
    pkg.service = mod
    monkeypatch.setitem(sys.modules, "app.devsahayak", pkg)
    monkeypatch.setitem(sys.modules, "app.devsahayak.service", mod)
    res = S.handoff_decide(T, card["id"], True, card["hash"], by_tap=True)
    assert res["status"] == "sent" and got and got[0]["tasks"][0]["do"]
    with pytest.raises(S.ReviewError, match="ho chuka"):
        S.handoff_decide(T, card["id"], True, card["hash"], by_tap=True)
    dev = S.handoff_request(T, again["number"], to="developer")
    out = S.handoff_decide(T, dev["id"], True, dev["hash"], by_tap=True)
    assert out["wa"].startswith("https://wa.me/") and "Fix list" in out["fix_list"]
    # actors
    staff = Ctx(T, ctx.conversation_id, actor="staff:1")
    with pytest.raises(ToolError, match="owner"):
        asyncio.run(AT.app_review(staff, "handoff", review=again["number"]))
    with pytest.raises(ToolError):
        asyncio.run(AT.app_review(Ctx(T, ctx.conversation_id, actor="customer:wa:9"), "web", url="ingle.in"))
    rd = asyncio.run(AT.app_review_dekho(staff, "compare", review=again["number"]))
    assert rd["compare"]["previous"]


def test_tick_and_api(ar, monkeypatch):
    S = ar
    v = S.review_file(T, S.upload(T, "app.apk", apk())["file"], today=TODAY)
    out = S.tick(datetime(2026, 10, 24, 6, tzinfo=timezone.utc))
    assert out["alerts"] == 1 and S.EVENTS[-1][0] == "appreview_alert" and "36" in S.EVENTS[-1][1]["say"]
    assert S.tick(datetime(2026, 10, 24, 9, tzinfo=timezone.utc))["alerts"] == 0          # once a day
    t3 = S.tick(datetime(2026, 11, 2, 9, tzinfo=timezone.utc))
    assert t3["alerts"] == 0 and t3["cleaned"] == 1          # at most every 30 days; upload gone after 7 days
    from app.appreview.api import make_router
    app = FastAPI()
    app.include_router(make_router(lambda: None, lambda: "default"))
    c = TestClient(app)
    up = c.post("/api/appreview/upload", files={"file": ("x.aab", aab(), "application/octet-stream")})
    assert up.status_code == 200, up.text
    r = c.post("/api/appreview/reviews", json={"file": up.json()["file"]})
    assert r.status_code == 200 and r.json()["kind"] == "aab"
    assert c.get("/api/appreview").json()["targets"]
    assert c.get(f"/api/appreview/reviews/{v['number']}").json()["id"] == v["id"]
    assert "markdown" in c.get(f"/api/appreview/reviews/{v['number']}/fixlist").json()
    h = c.post(f"/api/appreview/reviews/{v['number']}/handoff", json={"to": "developer"}).json()
    assert c.post(f"/api/appreview/handoffs/{h['id']}/decide", json={"yes": False, "hash": h["hash"]}).json()["status"] == "rejected"
    assert c.post("/api/appreview/reviews", json={}).status_code == 400
    assert c.put("/api/appreview/settings", json={"stack": "nope"}).status_code == 400
