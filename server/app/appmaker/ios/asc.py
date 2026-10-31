"""v0.338 APP STORE LAUNCH (App Phase 7): the App Store Connect API client that runs INSIDE her private builds repo
(workflow hoola-ios.yml, kinds store / review), so her App Store Connect key never leaves GitHub's encrypted secrets.

    python3 asc.py push   <project dir> <screens dir>   # listing + 6.9" screenshots + the build, onto the editable version
    python3 asc.py submit <project dir>                 # Submit for Review (only ever started by HER tap in Hoola)

Reads hoola_qa/store.json (written by Hoola: bundle id, version, build number, listing texts, urls) and the key from the
env (ASC_KEY_ID, ASC_ISSUER_ID, ASC_KEY_P8). Writes asc_result.json (+ prints it) for Hoola to read back. Official API only
(api.appstoreconnect.apple.com, JWT ES256, aud appstoreconnect-v1, 20 minutes). Needs `cryptography` (the JWT signature);
everything else is the standard library. Endpoints / attribute names from Apple's App Store Connect API reference."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

API = "https://api.appstoreconnect.apple.com"
DISPLAY = "APP_IPHONE_67"                                  # the 6.7" / 6.9" iPhone slot
SIZES = {(1320, 2868), (1290, 2796), (1260, 2736)}         # portrait sizes App Store Connect takes for it
LIMITS = {"name": 30, "subtitle": 30, "keywords": 100, "description": 4000, "promotionalText": 170, "whatsNew": 4000}
EDITABLE = ("PREPARE_FOR_SUBMISSION", "DEVELOPER_REJECTED", "REJECTED", "METADATA_REJECTED", "INVALID_BINARY")


class AscError(Exception):
    pass


# ---------------------------------------------------------------- auth
def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def token(key_id: str, issuer: str, p8: str, now: int | None = None) -> str:
    """ES256 JWT for the App Store Connect API (header alg/kid/typ, payload iss/iat/exp/aud), valid 19 minutes."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
    t = int(now or time.time())
    head = _b64(json.dumps({"alg": "ES256", "kid": key_id, "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64(json.dumps({"iss": issuer, "iat": t, "exp": t + 19 * 60, "aud": "appstoreconnect-v1"}, separators=(",", ":")).encode())
    key = serialization.load_pem_private_key(p8.strip().encode(), password=None)
    der = key.sign(f"{head}.{body}".encode(), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)                      # JWT wants raw r||s (64 bytes), not DER
    return f"{head}.{body}.{_b64(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))}"


# ---------------------------------------------------------------- http (tests replace _http)
def _real_http(method: str, url: str, headers: dict[str, str], body: bytes | None) -> tuple[int, bytes]:
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


_http: Callable[[str, str, dict[str, str], bytes | None], tuple[int, bytes]] = _real_http


class Client:
    def __init__(self, tok: str):
        self.tok = tok
        self.calls: list[str] = []

    def call(self, method: str, path: str, data: dict[str, Any] | None = None, ok404: bool = False) -> dict[str, Any]:
        self.calls.append(f"{method} {path.split('?')[0]}")
        body = json.dumps(data).encode() if data is not None else None
        code, raw = _http(method, API + path, {"Authorization": f"Bearer {self.tok}", "Content-Type": "application/json",
                                               "Accept": "application/json"}, body)
        if code == 404 and ok404:
            return {}
        if code >= 400:
            try:
                errs = json.loads(raw).get("errors") or []
                why = "; ".join(f"{e.get('code', '')}: {e.get('detail') or e.get('title') or ''}" for e in errs[:3])
            except ValueError:
                why = raw[:200].decode(errors="replace")
            raise AscError(f"{method} {path.split('?')[0]} -> {code} {why}")
        return json.loads(raw) if raw else {}


def _rel(kind: str, rid: str) -> dict[str, Any]:
    return {"data": {"type": kind, "id": rid}}


def _cut(field: str, v: Any) -> str:
    return str(v or "").strip()[:LIMITS.get(field, 4000)]


def png_size(b: bytes) -> tuple[int, int]:
    if b[:8] != b"\x89PNG\r\n\x1a\n":
        raise AscError("screenshot is not a PNG")
    return int.from_bytes(b[16:20], "big"), int.from_bytes(b[20:24], "big")


# ---------------------------------------------------------------- the steps
def find_app(c: Client, bundle: str) -> str:
    d = c.call("GET", "/v1/apps?" + urllib.parse.urlencode({"filter[bundleId]": bundle, "limit": 1}))
    rows = d.get("data") or []
    if not rows:
        raise AscError(f"NO_APP_RECORD {bundle}")
    return rows[0]["id"]


def editable_version(c: Client, app: str, version: str) -> dict[str, Any]:
    """The iOS version she can still edit; made when there is none (versionString = the app's version)."""
    d = c.call("GET", f"/v1/apps/{app}/appStoreVersions?" + urllib.parse.urlencode(
        {"filter[platform]": "IOS", "filter[appStoreState]": ",".join(EDITABLE), "limit": 5}))
    rows = d.get("data") or []
    if rows:
        v = rows[0]
        if (v.get("attributes") or {}).get("versionString") != version:
            c.call("PATCH", f"/v1/appStoreVersions/{v['id']}",
                   {"data": {"type": "appStoreVersions", "id": v["id"], "attributes": {"versionString": version}}})
        return v
    return c.call("POST", "/v1/appStoreVersions", {"data": {"type": "appStoreVersions",
                  "attributes": {"platform": "IOS", "versionString": version, "releaseType": "MANUAL"},
                  "relationships": {"app": _rel("apps", app)}}})["data"]


def version_localization(c: Client, ver: str, locale: str, attrs: dict[str, str]) -> str:
    d = c.call("GET", f"/v1/appStoreVersions/{ver}/appStoreVersionLocalizations")
    row = next((x for x in d.get("data") or [] if (x.get("attributes") or {}).get("locale") == locale), None)
    if row:
        c.call("PATCH", f"/v1/appStoreVersionLocalizations/{row['id']}",
               {"data": {"type": "appStoreVersionLocalizations", "id": row["id"], "attributes": attrs}})
        return row["id"]
    return c.call("POST", "/v1/appStoreVersionLocalizations", {"data": {"type": "appStoreVersionLocalizations",
                  "attributes": {"locale": locale, **attrs}, "relationships": {"appStoreVersion": _rel("appStoreVersions", ver)}}})["data"]["id"]


def info_localization(c: Client, app: str, locale: str, attrs: dict[str, str]) -> None:
    infos = c.call("GET", f"/v1/apps/{app}/appInfos").get("data") or []
    if not infos:
        raise AscError("no appInfo for this app")
    info = next((i for i in infos if (i.get("attributes") or {}).get("appStoreState") in EDITABLE), infos[0])
    d = c.call("GET", f"/v1/appInfos/{info['id']}/appInfoLocalizations")
    row = next((x for x in d.get("data") or [] if (x.get("attributes") or {}).get("locale") == locale), None)
    if row:
        c.call("PATCH", f"/v1/appInfoLocalizations/{row['id']}",
               {"data": {"type": "appInfoLocalizations", "id": row["id"], "attributes": attrs}})
    else:
        c.call("POST", "/v1/appInfoLocalizations", {"data": {"type": "appInfoLocalizations", "attributes": {"locale": locale, **attrs},
                                                             "relationships": {"appInfo": _rel("appInfos", info["id"])}}})


def screenshots(c: Client, loc: str, shots: list[Path]) -> int:
    """Replace the 6.9" screenshot set with these PNGs (reserve -> PUT each part -> commit with the MD5)."""
    sets = c.call("GET", f"/v1/appStoreVersionLocalizations/{loc}/appScreenshotSets").get("data") or []
    old = next((s for s in sets if (s.get("attributes") or {}).get("screenshotDisplayType") == DISPLAY), None)
    if old:
        for sh in c.call("GET", f"/v1/appScreenshotSets/{old['id']}/appScreenshots").get("data") or []:
            c.call("DELETE", f"/v1/appScreenshots/{sh['id']}", ok404=True)
        sid = old["id"]
    else:
        sid = c.call("POST", "/v1/appScreenshotSets", {"data": {"type": "appScreenshotSets", "attributes": {"screenshotDisplayType": DISPLAY},
                     "relationships": {"appStoreVersionLocalization": _rel("appStoreVersionLocalizations", loc)}}})["data"]["id"]
    n = 0
    for p in shots[:10]:
        b = p.read_bytes()
        if png_size(b) not in SIZES:
            raise AscError(f"{p.name} is {png_size(b)[0]}x{png_size(b)[1]}; the 6.9-inch slot needs 1320x2868")
        res = c.call("POST", "/v1/appScreenshots", {"data": {"type": "appScreenshots", "attributes": {"fileSize": len(b), "fileName": p.name},
                     "relationships": {"appScreenshotSet": _rel("appScreenshotSets", sid)}}})["data"]
        for op in (res.get("attributes") or {}).get("uploadOperations") or []:
            off, ln = int(op.get("offset") or 0), int(op.get("length") or len(b))
            hdr = {h["name"]: h["value"] for h in op.get("requestHeaders") or []}
            code, raw = _http(op.get("method") or "PUT", op["url"], hdr, b[off:off + ln])   # pre-signed: no bearer token
            if code >= 300:
                raise AscError(f"screenshot upload part -> {code}")
        c.call("PATCH", f"/v1/appScreenshots/{res['id']}", {"data": {"type": "appScreenshots", "id": res["id"],
               "attributes": {"uploaded": True, "sourceFileChecksum": hashlib.md5(b).hexdigest()}}})
        n += 1
    return n


def attach_build(c: Client, app: str, ver: str, build_number: str) -> str:
    """The TestFlight build with this build number (processed by Apple) goes onto the version."""
    d = c.call("GET", "/v1/builds?" + urllib.parse.urlencode({"filter[app]": app, "filter[version]": build_number, "limit": 1}))
    rows = d.get("data") or []
    if not rows:
        raise AscError(f"NO_BUILD {build_number}")
    state = (rows[0].get("attributes") or {}).get("processingState")
    if state and state != "VALID":
        raise AscError(f"BUILD_PROCESSING {build_number} {state}")
    c.call("PATCH", f"/v1/appStoreVersions/{ver}", {"data": {"type": "appStoreVersions", "id": ver,
           "relationships": {"build": _rel("builds", rows[0]["id"])}}})
    return rows[0]["id"]


def push(store: dict[str, Any], shots: list[Path], c: Client) -> dict[str, Any]:
    lst = store.get("listing") or {}
    app = find_app(c, store["bundle_id"])
    ver = editable_version(c, app, str(store["version"]))
    locale = store.get("locale") or "en-US"
    vattrs = {k: _cut(k, lst.get(k)) for k in ("description", "keywords", "promotionalText") if lst.get(k)}
    for k in ("supportUrl", "marketingUrl"):
        if store.get(k):
            vattrs[k] = store[k]
    if lst.get("whatsNew") and store.get("not_first"):
        vattrs["whatsNew"] = _cut("whatsNew", lst["whatsNew"])
    loc = version_localization(c, ver["id"], locale, vattrs)
    iattrs = {k: _cut(k, lst.get(k)) for k in ("name", "subtitle") if lst.get(k)}
    if store.get("privacyPolicyUrl"):
        iattrs["privacyPolicyUrl"] = store["privacyPolicyUrl"]
    info_localization(c, app, locale, iattrs)
    n = screenshots(c, loc, shots) if shots else 0
    build = attach_build(c, app, ver["id"], str(store["build"]))
    return {"ok": True, "app": app, "version": ver["id"], "version_string": store["version"], "screenshots": n, "build": build,
            "state": (ver.get("attributes") or {}).get("appStoreState") or "PREPARE_FOR_SUBMISSION"}


def submit(store: dict[str, Any], c: Client) -> dict[str, Any]:
    """Submit for Review: a review submission for the app, the version as its item, then submitted = true."""
    app = find_app(c, store["bundle_id"])
    ver = editable_version(c, app, str(store["version"]))
    sub = c.call("POST", "/v1/reviewSubmissions", {"data": {"type": "reviewSubmissions", "attributes": {"platform": "IOS"},
                 "relationships": {"app": _rel("apps", app)}}})["data"]
    c.call("POST", "/v1/reviewSubmissionItems", {"data": {"type": "reviewSubmissionItems", "relationships": {
        "reviewSubmission": _rel("reviewSubmissions", sub["id"]), "appStoreVersion": _rel("appStoreVersions", ver["id"])}}})
    c.call("PATCH", f"/v1/reviewSubmissions/{sub['id']}", {"data": {"type": "reviewSubmissions", "id": sub["id"],
           "attributes": {"submitted": True}}})
    return {"ok": True, "submitted": True, "submission": sub["id"], "version": ver["id"], "version_string": store["version"]}


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in ("push", "submit"):
        print(__doc__)
        return 2
    proj = Path(argv[1])
    store = json.loads((proj / "hoola_qa" / "store.json").read_text())
    out: dict[str, Any]
    try:
        miss = [k for k in ("ASC_KEY_ID", "ASC_ISSUER_ID", "ASC_KEY_P8") if not os.environ.get(k)]
        if miss:
            raise AscError("MISSING_SECRET " + " ".join(miss))
        c = Client(token(os.environ["ASC_KEY_ID"], os.environ["ASC_ISSUER_ID"], os.environ["ASC_KEY_P8"]))
        if argv[0] == "push":
            want = [str(x) for x in store.get("shots") or []]
            folder = Path(argv[2]) if len(argv) > 2 else proj / "qa" / "store"
            shots = [folder / f"{s}.png" for s in want if (folder / f"{s}.png").exists()]
            out = push(store, shots, c)
        else:
            out = submit(store, c)
        out["calls"] = len(c.calls)
    except AscError as e:
        out = {"ok": False, "error": str(e)}
    (proj / "asc_result.json").write_text(json.dumps(out))
    print("ASC_RESULT " + json.dumps(out))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
