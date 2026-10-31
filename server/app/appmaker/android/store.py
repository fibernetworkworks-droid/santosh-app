"""v0.330 PLAY STORE LAUNCH (App Sahayak Phase 5): her app on Google Play, from HER OWN developer account, through Google's
official Play Developer API (androidpublisher v3) - never a scraped console, never Hoola's account.

  1. Store identity: the permanent package name (com.<business>.app; Play never lets it change) - proposed by Hoola,
     confirmed by her; a separate UPLOAD key per app (Play App Signing keeps the real signing key at Google).
  2. Store build: the app's latest built project as an Android App Bundle (.aab) under the store package, signed with the
     upload key, version code above every earlier build.
  3. Listing: title / short / full description (Opus, from her facts; checked against Play's limits; she can edit),
     512 px icon + 1024 x 500 feature graphic drawn from the app's own colours, phone screenshots from the device check.
  4. Pages Play asks for, served by her Hoola: privacy policy and the account-deletion page (both public, per app).
  5. Data safety: the answers for Play Console's form, written from what the app really collects (no API exists for it).
  6. Upload: her service-account key (JSON from her Play Console, typed into the app, sealed, never shown again, never in
     chat) -> edit -> bundle -> internal testing track -> listing + images -> commit. PRODUCTION only by her tap in the app
     (a public change: the tool never does it). The app entry itself is created once by her in Play Console (Google's API
     cannot create apps)."""
from __future__ import annotations

import base64
import hashlib
import html
import io
import json
import logging
import re
import secrets
import shutil
import threading
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from ...db import now, session
from .. import service as AS
from ..models import AppProject
from . import runners as RN
from . import service as AN

log = logging.getLogger("santosh.appmaker.store")
PKG_RE = re.compile(r"^[a-z][a-z0-9_]{1,30}(\.[a-z][a-z0-9_]{1,30}){1,4}$")
LIMITS = {"title": 30, "short": 80, "full": 4000}
TRACKS = ("internal", "alpha", "beta", "production")
API = "https://androidpublisher.googleapis.com/androidpublisher/v3/applications"
UPLOAD = "https://androidpublisher.googleapis.com/upload/androidpublisher/v3/applications"
SCOPE = "https://www.googleapis.com/auth/androidpublisher"
STATS = {"bundles": 0, "uploads": 0, "upload_failed": 0, "listings": 0}
_LOCK = threading.Lock()
_RUNNING: dict[str, threading.Thread] = {}
# tests swap the HTTP layer: fn(method, url, headers, data, params) -> (status, json-or-bytes)
_http: Callable[..., tuple[int, Any]] | None = None


class StoreError(AS.AppError):
    pass


def _j(s: Any, d: Any) -> Any:
    try:
        return json.loads(s) if s else d
    except (TypeError, ValueError):
        return d


def _load(tenant: str, ref: str) -> AppProject:
    with session() as s:
        r = AS._find(s, tenant, ref)
        s.expunge(r)
    return r


def state(r: AppProject) -> dict[str, Any]:
    return AN.state(r).get("store") or {}


def _put(r: AppProject, **kw) -> dict[str, Any]:
    st = dict(state(AS._load(r.id)))
    st.update(kw)
    AN._put(r.id, store=st)
    return st


def _dir(r: AppProject) -> Path:
    d = AN._dir(r) / "store"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------- 1. identity
def propose_package(r: AppProject) -> str:
    """com.<business>.app from her app's name (ASCII only; Play package names are permanent)."""
    import unicodedata
    name = unicodedata.normalize("NFKD", r.name or "").encode("ascii", "ignore").decode().lower()
    words = [w for w in re.split(r"[^a-z0-9]+", name) if w and w not in ("the", "app", "and", "of", "ki", "ka", "ke")]
    slug = "".join(words)[:24] or "hoolaapp" + hashlib.sha1(r.id.encode()).hexdigest()[:6]
    if slug[0].isdigit():
        slug = "a" + slug
    return f"com.{slug}.app"


def setup(tenant: str, ref: str, package: str = "") -> dict[str, Any]:
    """Her confirmation of the permanent package name. Locked after the first upload (Play never allows a change)."""
    r = _load(tenant, ref)
    st = state(r)
    if not AN.state(r).get("apk"):
        raise StoreError("Pehle Android app banaiye (preview build): store build usi se banti hai.")
    pkg = (package or st.get("package") or propose_package(r)).strip().lower()
    if not PKG_RE.match(pkg) or pkg.startswith(("com.example", "in.hoola.preview", "android.", "com.google", "com.android")):
        raise StoreError("Package name sahi nahi (jaise com.sharmakirana.app: chhote akshar, ank, bindu).")
    if st.get("locked") and pkg != st.get("package"):
        raise StoreError(f"Package {st['package']} Play par ja chuka hai; Google ise badalne nahi deta.")
    _put(r, package=pkg, confirmed=now().isoformat())
    _upload_key(r)
    return view(_load(tenant, ref))


def _upload_key(r: AppProject) -> dict[str, str]:
    """This app's UPLOAD key (PKCS12, alias 'preview' so the fixed Gradle file signs with it), sealed by the server vault.
    Play App Signing keeps the real app-signing key at Google; a lost upload key can be reset in Play Console."""
    from ...bazar.security import vault
    f = _dir(r) / "upload.key.sealed"
    if f.exists():
        return json.loads(vault().open(f.read_text()))
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, f"{(r.name or 'App')[:40]} upload key"),
                      x509.NameAttribute(NameOID.ORGANIZATION_NAME, (r.name or "App")[:60])])
    t0 = datetime.now(timezone.utc) - timedelta(days=1)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(t0).not_valid_after(t0 + timedelta(days=365 * 27))
            .sign(key, hashes.SHA256()))
    pw = secrets.token_hex(16)
    p12 = pkcs12.serialize_key_and_certificates(b"preview", key, cert, None, serialization.BestAvailableEncryption(pw.encode()))
    d = {"p12_b64": base64.b64encode(p12).decode(), "password": pw,
         "sha256": hashlib.sha256(cert.public_bytes(serialization.Encoding.DER)).hexdigest(),
         "pem": cert.public_bytes(serialization.Encoding.PEM).decode()}
    f.write_text(vault().seal(json.dumps(d)))
    f.chmod(0o600)
    return d


def upload_cert(tenant: str, ref: str) -> tuple[bytes, str]:
    """The upload certificate (public part only), for Play Console if Google asks for it."""
    r = _load(tenant, ref)
    if not state(r).get("package"):
        raise StoreError("not found")
    return _upload_key(r)["pem"].encode(), f"{state(r)['package']}-upload-cert.pem"


# ---------------------------------------------------------------- her Play service account (sealed)
def set_credentials(tenant: str, ref: str, raw: str) -> dict[str, Any]:
    """Her Play Console service-account JSON: checked, sealed, never returned (only its e-mail, masked)."""
    from ...bazar.security import vault
    r = _load(tenant, ref)
    try:
        d = json.loads(raw)
    except (TypeError, ValueError):
        raise StoreError("Yeh JSON file nahi lagti (Play Console > API access > service account ki key).")
    if d.get("type") != "service_account" or not d.get("client_email") or "PRIVATE KEY" not in str(d.get("private_key") or ""):
        raise StoreError("Service account key chahiye (type service_account, client_email, private_key).")
    keep = {k: d[k] for k in ("type", "project_id", "private_key_id", "private_key", "client_email", "client_id", "token_uri") if k in d}
    (_dir(r) / "play.sealed").write_text(vault().seal(json.dumps(keep)))
    (_dir(r) / "play.sealed").chmod(0o600)
    em = str(d["client_email"])
    _put(r, account=em[:3] + "…" + em[em.find("@"):] if "@" in em else "…", account_at=now().isoformat())
    return view(_load(tenant, ref))


def forget_credentials(tenant: str, ref: str) -> dict[str, Any]:
    r = _load(tenant, ref)
    (_dir(r) / "play.sealed").unlink(missing_ok=True)
    _put(r, account="", account_at="")
    return view(r)


def _creds(r: AppProject) -> dict[str, Any] | None:
    from ...bazar.security import vault
    f = _dir(r) / "play.sealed"
    return json.loads(vault().open(f.read_text())) if f.exists() else None


# ---------------------------------------------------------------- 3. listing + graphics
LISTING_SYSTEM = """You write a Google Play store listing for a small Indian business's app. Return JSON {title, short, full}.
title <= 30 characters (the business name, maybe + 2 words). short <= 80 characters: what the app lets a customer do.
full <= 3500 characters: 3-6 short paragraphs or simple lines starting with "• " - what you can do in the app, how ordering /
booking works, contact, area served. Only facts given (no invented prices, offers, awards, ratings, "best", "No. 1", emoji
spam, other brands, keyword stuffing, ALL CAPS) - Play's metadata policy. Plain English an Indian customer reads easily."""


def _clip(s: Any, n: int) -> str:
    s = re.sub(r"\s+\n", "\n", str(s or "")).strip()
    if len(s) <= n:
        return s
    cut = s[:n]
    return (cut[:cut.rfind(" ")] if " " in cut[n // 2:] else cut).rstrip(" ,;-") if n < 200 else cut[:cut.rfind("\n") if "\n" in cut[n // 2:] else n]


def _template_listing(r: AppProject, facts: dict[str, Any], kinds: list[str]) -> dict[str, str]:
    name = r.name or facts.get("name") or "App"
    what = {"orders": "order", "bookings": "book", "requests": "request a service", "enquiries": "send an enquiry",
            "enrolments": "enrol", "memberships": "get a membership", "registrations": "register"}
    acts = [what[k] for k in kinds if k in what]
    short = f"{name}: " + (", ".join(acts[:2]) + " and track it in the app" if acts else "everything in one app")
    lines = [f"{name} in your pocket."]
    if facts.get("about") or facts.get("tagline"):
        lines.append(str(facts.get("about") or facts.get("tagline"))[:400])
    if acts:
        lines.append("• " + acts[0].capitalize() + " in a few taps and see its status live.")
    lines += ["• Your own account: your orders and requests in one place.", "• Works on a weak network: what you send goes when you are back online."]
    if facts.get("upi_id"):
        lines.append("• Pay by UPI in your own UPI app.")
    contact = ", ".join(str(facts[k]) for k in ("address", "phone") if facts.get(k))
    if contact:
        lines.append("Contact: " + contact)
    return {"title": _clip(name, 30), "short": _clip(short, 80), "full": _clip("\n".join(lines), 3500)}


def listing(tenant: str, ref: str, regen: bool = False, edit: dict[str, Any] | None = None) -> dict[str, Any]:
    """Make (or redo / take her edits to) the store listing; every field kept within Play's limits."""
    from .. import backend as BE
    r = _load(tenant, ref)
    st = state(r)
    cur = dict(st.get("listing") or {})
    if edit:
        for k in ("title", "short", "full"):
            if isinstance(edit.get(k), str) and edit[k].strip():
                if len(edit[k].strip()) > LIMITS[k]:
                    raise StoreError(f"{k}: Play {LIMITS[k]} akshar tak leta hai ({len(edit[k].strip())} hain).")
                cur[k] = edit[k].strip()
        cur["edited"] = True
    elif regen or not cur.get("title"):
        facts = {**AS._j(r.facts, {}), **{k: v for k, v in AS.gather_facts(r.tenant_id, "").items() if v}}
        kinds = [c["key"] for c in BE.schema(r)["collections"]]
        made = None
        try:
            from ...site import ai as SA
            got = SA.ask_json(LISTING_SYSTEM, "FACTS (data): " + json.dumps({k: facts.get(k) for k in ("name", "tagline", "about", "address", "city",
                              "hours", "phone", "upi_id") if facts.get(k)}, ensure_ascii=False) + f"\nAPP LISTS: {', '.join(kinds)}\nAPP NAME: {r.name}",
                              2500, "app_edit")
            if isinstance(got, dict) and got.get("title"):
                made = {"title": _clip(got["title"], 30), "short": _clip(got.get("short"), 80), "full": _clip(got.get("full"), 3500)}
        except Exception:                               # noqa: BLE001
            log.info("store listing: template", exc_info=True)
        cur = made if made and made["short"] and made["full"] else _template_listing(r, facts, kinds)
        cur["by"] = "opus" if made else "template"
        STATS["listings"] += 1
    _put(r, listing=cur)
    return view(_load(tenant, ref))


def _rgb(h: str, d=(80, 60, 200)) -> tuple[int, int, int]:
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", str(h or ""))
    return tuple(int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4)) if m else d       # type: ignore[return-value]


def graphics(r: AppProject) -> dict[str, bytes]:
    """512 px icon + 1024 x 500 feature graphic from the app's own colours and name (no other brand, no stock art)."""
    from PIL import Image, ImageDraw, ImageFont
    tk = (AS._j(r.look, {}).get("tokens") or {})
    p, a = _rgb(tk.get("primary")), _rgb(tk.get("accent"), (240, 150, 60))
    name = (r.name or "App").strip()

    def font(size: int):
        for f in ("DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
            try:
                return ImageFont.truetype(f, size)
            except OSError:
                continue
        return ImageFont.load_default()

    def grad(w: int, h: int) -> Image.Image:
        im = Image.new("RGB", (w, h), p)
        dr = ImageDraw.Draw(im)
        for x in range(w):
            t = x / max(1, w - 1)
            dr.line([(x, 0), (x, h)], fill=tuple(int(p[i] * (1 - t) + a[i] * t) for i in range(3)))
        return im
    icon = grad(512, 512)
    d = ImageDraw.Draw(icon)
    letter = next((ch for ch in name if ch.isalnum()), "A").upper()
    f = font(300)
    bb = d.textbbox((0, 0), letter, font=f)
    d.text(((512 - (bb[2] - bb[0])) / 2 - bb[0], (512 - (bb[3] - bb[1])) / 2 - bb[1]), letter, font=f, fill=(255, 255, 255))
    feat = grad(1024, 500)
    d2 = ImageDraw.Draw(feat)
    size = 96
    while size > 30:
        f2 = font(size)
        bb = d2.textbbox((0, 0), name, font=f2)
        if bb[2] - bb[0] <= 900:
            break
        size -= 6
    d2.text(((1024 - (bb[2] - bb[0])) / 2 - bb[0], (500 - (bb[3] - bb[1])) / 2 - bb[1]), name, font=f2, fill=(255, 255, 255))
    out = {}
    for k, im in (("icon", icon), ("featureGraphic", feat)):
        b = io.BytesIO()
        im.save(b, "PNG")
        out[k] = b.getvalue()
    return out


def screenshots(r: AppProject) -> list[bytes]:
    """Phone screenshots for the listing: the device check's pictures of the latest build (2-8; Play needs 2+)."""
    qa = AN.state(r).get("qa") or {}
    if not qa.get("ran"):
        return []
    d = AN._dir(r) / "qa" / f"b{qa.get('build')}"
    order = [s for s in (qa.get("shots") or []) if not s.startswith("hoola_") and s not in ("privacy", "seller_info", "delete_account")]
    out = []
    for sid in order[:8]:
        f = d / f"{sid}.png"
        if f.exists() and f.stat().st_size > 2000:
            out.append(f.read_bytes())
    return out


# ---------------------------------------------------------------- 4/5. public pages + data safety
def privacy_html(r: AppProject) -> str:
    from . import spec as SP
    facts = {**AS._j(r.facts, {}), **{k: v for k, v in AS.gather_facts(r.tenant_id, "").items() if v}}
    paras = SP.privacy_paras(r.name, r.goal, facts)
    body = "".join(f"<h2>{html.escape(p[2:])}</h2>" if p.startswith("# ") else f"<p>{html.escape(p)}</p>" for p in paras)
    return _page(f"{r.name or 'App'} - Privacy policy", body + _crash_line())


def _crash_line() -> str:
    return ("<h2>Crash reports</h2><p>If the app crashes, it sends the technical error (which screen, app version, the phone's system "
            "version (Android / iOS) and model) so it can be fixed. It contains no personal details and nothing you typed.</p>")


def delete_html(r: AppProject) -> str:
    facts = {**AS._j(r.facts, {}), **{k: v for k, v in AS.gather_facts(r.tenant_id, "").items() if v}}
    contact = " · ".join(html.escape(str(facts[k])) for k in ("email", "phone") if facts.get(k))
    body = (f"<p>You can delete your {html.escape(r.name or 'app')} account and everything it holds (your orders, bookings, requests "
            "and photos) at any time:</p><ol><li>Open the app and go to <b>My account</b> (or Profile).</li><li>Tap <b>Delete my account</b> and "
            "confirm.</li></ol><p>It is removed from the server at once. Bills the law requires us to keep are kept only as long as the law "
            "says.</p>" + (f"<p>No longer have the app? Ask us to delete it: {contact}</p>" if contact else ""))
    return _page(f"{r.name or 'App'} - Delete your account", body)


def _page(title: str, body: str) -> str:
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)}</title><style>body{{font:16px/1.6 system-ui,sans-serif;max-width:720px;margin:32px auto;"
            "padding:0 16px;color:#1d1d1f}h1{font-size:26px}h2{font-size:18px;margin-top:24px}</style></head><body>"
            f"<h1>{html.escape(title)}</h1>{body}<p style='color:#888;font-size:13px'>Updated {now().date().isoformat()}</p></body></html>")


def data_safety(r: AppProject) -> list[dict[str, Any]]:
    """Answers for Play Console > Data safety, from what this app's lists really hold (Google has no API for the form)."""
    from .. import backend as BE
    fields = [(c["key"], f) for c in BE.schema(r)["collections"] for f in c["fields"] if not f.get("hidden")]
    types = {f.get("type") for _c, f in fields}
    keys = {f["key"] for _c, f in fields}
    out = [{"type": "Personal info > Email address", "why": "Account sign-in", "optional": False},
           {"type": "Personal info > Name", "why": "Account, orders / bookings", "optional": "name" not in keys}]
    if "phone" in types:
        out.append({"type": "Personal info > Phone number", "why": "To reach you about your order / booking", "optional": False})
    if keys & {"address"}:
        out.append({"type": "Personal info > Address", "why": "Delivery / visit", "optional": True})
    if "location" in types:
        out.append({"type": "Location > Approximate + Precise location", "why": "Only when you tap 'Use my location'", "optional": True})
    if "photo" in types:
        out.append({"type": "Photos and videos > Photos", "why": "Only photos you choose to attach", "optional": True})
    if BE.schema(r).get("order"):
        out.append({"type": "Financial info > Purchase history", "why": "Your orders", "optional": False})
    out.append({"type": "App info and performance > Crash logs", "why": "Fixing crashes (no personal data)", "optional": False})
    for x in out:
        x.update({"shared": "No", "encrypted_in_transit": "Yes (HTTPS)", "deletion": "Yes - in the app (My account) and by request"})
    return out


# ---------------------------------------------------------------- 2. the store bundle
def build_bundle(tenant: str, ref: str) -> dict[str, Any]:
    r = _load(tenant, ref)
    st = state(r)
    if not st.get("package"):
        raise StoreError("Pehle store ka package name pakka kijiye.")
    if st.get("status") in ("building", "uploading"):
        return view(r)
    _put(r, status="building", error="", now="Play Store bundle (.aab) ban raha hai")
    _bg(r.id, _build_bundle)
    return view(_load(tenant, ref))


def _bg(app_id: str, fn: Callable[[AppProject], None]) -> None:
    def go():
        r = AS._load(app_id)
        try:
            fn(r)
        except Exception as e:                          # noqa: BLE001
            log.exception("store job")
            _put(AS._load(app_id), status="failed", error=str(e)[:400], now="")
            AN._emit(app_id)
        finally:
            with _LOCK:
                _RUNNING.pop(app_id, None)
    if AS._inline():
        go()
        return
    with _LOCK:
        t = _RUNNING.get(app_id)
        if t is not None and t.is_alive():
            return
        t = threading.Thread(target=go, name=f"store-{app_id}", daemon=True)
        _RUNNING[app_id] = t
    t.start()


def _build_bundle(r: AppProject) -> None:
    ast = AN.state(r)
    st = state(r)
    hist = ast.get("history") or []
    if not hist:
        raise StoreError("Pehle Android app ki ek build chahiye.")
    b = hist[-1]["build"]
    z = AN._dir(r) / f"project-b{b}.zip"
    if not z.exists():
        raise StoreError("Aakhri build ka project nahi mila; 'Android app banao' dobara kahiye.")
    if not RN.describe()["ready"] and RN._override is None:
        raise StoreError("Build machine set nahi hai: store bundle nahi ban sakta.")
    src = _dir(r) / "project"
    shutil.rmtree(src, ignore_errors=True)
    with zipfile.ZipFile(z) as zf:
        for m in zf.infolist():
            if str((src / m.filename).resolve()).startswith(str(src.resolve())):
                zf.extract(m, src)
    vc = max(int(ast.get("last_vc") or 0), int(st.get("last_vc") or 0)) + 1
    g = src / "app/build.gradle.kts"
    t = g.read_text()
    t = re.sub(r'applicationId = "[^"]*"', f'applicationId = "{st["package"]}"', t)
    t = re.sub(r"versionCode = \d+", f"versionCode = {vc}", t)
    vname = str(hist[-1].get("version_name") or "1.0")
    t = re.sub(r'versionName = "[^"]*"', f'versionName = "{vname}"', t)
    g.write_text(t)
    (src / "gradlew").chmod(0o755)
    key = _upload_key(r)
    (src / "keys").mkdir(exist_ok=True)
    (src / "keys/preview.p12").write_bytes(base64.b64decode(key["p12_b64"]))
    gp = src / "app/build.gradle.kts"
    gp.write_text(re.sub(r'\?: "[A-Za-z0-9]*"', f'?: "{key["password"]}"', gp.read_text()))    # the export blanked it
    _put(r, now="Bundle compile ho raha hai (build machine)")
    AN._emit(r.id)
    res = RN.build(src, ("store-" + r.id.replace("_", "-"))[:60].lower(), lambda stage: None, "aab")
    shutil.rmtree(src, ignore_errors=True)
    if not (res.get("ok") and res.get("apk")):
        raise StoreError("Store bundle compile nahi hua: " + str(res.get("log") or "")[-300:])
    aab = res["apk"]
    name = f"{st['package']}-{vname}-{vc}.aab"
    for old in _dir(r).glob("*.aab"):
        old.unlink()
    (_dir(r) / name).write_bytes(aab)
    STATS["bundles"] += 1
    AN._put(r.id, last_vc=vc)                    # preview builds keep going UP past the store build too
    _put(AS._load(r.id), status="built", now="", bundle={"file": name, "version_code": vc, "version_name": vname, "size": len(aab),
                                                         "sha256": hashlib.sha256(aab).hexdigest(), "from_build": b, "at": now().isoformat()})
    AN._note(r, f"{r.name or 'App'} ka Play Store bundle taiyaar (v{vname}, code {vc}). Ab 'Internal testing par bhejo' - "
                "pehle aap aur aapke testers dekhenge.")
    AN._emit(r.id, push=True)


# ---------------------------------------------------------------- 6. the upload (Google Play Developer API)
def _token(creds: dict[str, Any]) -> str:
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    c = service_account.Credentials.from_service_account_info(creds, scopes=[SCOPE])
    c.refresh(Request())
    return c.token


def _call(method: str, url: str, token: str, data: Any = None, params: dict | None = None,
          ctype: str = "application/json") -> Any:
    headers = {"Authorization": f"Bearer {token}"}
    if _http is not None:
        st, body = _http(method, url, headers, data, params)
    else:
        import httpx
        kw: dict[str, Any] = {"params": params or {}, "headers": headers, "timeout": 300}
        if isinstance(data, (bytes, bytearray)):
            kw["content"], headers["Content-Type"] = data, ctype
        elif data is not None:
            kw["json"] = data
        resp = httpx.request(method, url, **kw)
        st = resp.status_code
        try:
            body = resp.json()
        except ValueError:
            body = {"error": {"message": resp.text[:300]}}
    if st >= 400:
        msg = ((body or {}).get("error") or {}).get("message") if isinstance(body, dict) else str(body)[:300]
        raise StoreError(f"Google Play ({st}): {msg or 'request refused'}")
    return body


def publish(tenant: str, ref: str, track: str = "internal", her_tap: bool = False) -> dict[str, Any]:
    """Send the bundle + listing to a Play track. Production (public) only with her tap in the app."""
    r = _load(tenant, ref)
    st = state(r)
    if track not in TRACKS:
        raise StoreError("Track: internal / alpha / beta / production.")
    if track == "production" and not her_tap:
        raise StoreError("Production par (sab ke liye public) sirf aap app mein button daba kar bhejti hain.")
    if not _creds(r):
        raise StoreError("Pehle Play Console ki service account key app mein daaliye (Play Store > Developer account).")
    if not st.get("bundle"):
        raise StoreError("Pehle store bundle banaiye.")
    if not (st.get("listing") or {}).get("title"):
        listing(tenant, ref)
    if st.get("status") in ("building", "uploading"):
        return view(r)
    _put(r, status="uploading", error="", now=f"Google Play par bhej rahi hoon ({track})", track_wanted=track)
    _bg(r.id, _publish)
    return view(_load(tenant, ref))


def _publish(r: AppProject) -> None:
    st = state(r)
    track = st.get("track_wanted") or "internal"
    creds = _creds(r)
    tok = _token(creds)
    pkg = st["package"]
    lst = st.get("listing") or {}
    aab = (_dir(r) / st["bundle"]["file"]).read_bytes()
    edit = _call("POST", f"{API}/{pkg}/edits", tok, {})
    eid = edit["id"]
    up = _call("POST", f"{UPLOAD}/{pkg}/edits/{eid}/bundles", tok, aab, {"uploadType": "media"}, "application/octet-stream")
    vc = int(up.get("versionCode") or st["bundle"]["version_code"])
    notes = AN.latest(r).get("notes") or ["Improvements and fixes."]
    release = {"versionCodes": [str(vc)], "status": "completed", "releaseNotes": [{"language": "en-IN", "text": "\n".join(notes)[:500]}]}
    try:
        _call("PUT", f"{API}/{pkg}/edits/{eid}/tracks/{track}", tok, {"track": track, "releases": [release]})
        draft = False
    except StoreError as e:
        if "draft" not in str(e).lower():
            raise
        release["status"] = "draft"                 # a brand-new app Google has not reviewed yet takes draft releases only
        _call("PUT", f"{API}/{pkg}/edits/{eid}/tracks/{track}", tok, {"track": track, "releases": [release]})
        draft = True
    _call("PUT", f"{API}/{pkg}/edits/{eid}/listings/en-IN", tok,
          {"language": "en-IN", "title": lst.get("title"), "shortDescription": lst.get("short"), "fullDescription": lst.get("full")})
    g = graphics(r)
    for kind in ("icon", "featureGraphic"):
        _call("DELETE", f"{API}/{pkg}/edits/{eid}/listings/en-IN/{kind}", tok)
        _call("POST", f"{UPLOAD}/{pkg}/edits/{eid}/listings/en-IN/{kind}", tok, g[kind], {"uploadType": "media"}, "image/png")
    shots = screenshots(r)
    if len(shots) >= 2:
        _call("DELETE", f"{API}/{pkg}/edits/{eid}/listings/en-IN/phoneScreenshots", tok)
        for png in shots:
            _call("POST", f"{UPLOAD}/{pkg}/edits/{eid}/listings/en-IN/phoneScreenshots", tok, png, {"uploadType": "media"}, "image/png")
    _call("POST", f"{API}/{pkg}/edits/{eid}:commit", tok)
    STATS["uploads"] += 1
    rel = {"track": track, "version_code": vc, "version_name": st["bundle"]["version_name"], "status": release["status"],
           "at": now().isoformat(), "screenshots": len(shots)}
    _put(AS._load(r.id), status="done", now="", locked=True, last_vc=vc, releases=((st.get("releases") or []) + [rel])[-20:])
    where = {"internal": "Internal testing", "alpha": "Closed testing", "beta": "Open testing", "production": "Production"}[track]
    AN._note(r, f"{r.name or 'App'} Google Play par chali gayi: {where}, v{rel['version_name']}"
                + (" (draft - nayi app hai: Play Console mein ek baar 'Review release' karke bhejiye)" if draft else "")
                + ". " + ("Google ka review hone ke baad sabko dikhegi." if track == "production" else
                          "Testers ko Play Console > Internal testing se link bhejiye."))
    AN._emit(r.id, push=True)


# ---------------------------------------------------------------- view
def view(r: AppProject) -> dict[str, Any]:
    st = state(r)
    ast = AN.state(r)
    base = (AS._settings().public_base_url or "").rstrip("/")
    key = ast.get("app_key") or ""
    lst = st.get("listing") or {}
    shots = len(screenshots(r))
    steps = [
        {"id": "build", "label": "Android app built", "done": bool(ast.get("apk"))},
        {"id": "package", "label": "Package name (permanent)", "done": bool(st.get("package")), "value": st.get("package") or ""},
        {"id": "account", "label": "Your Play developer account linked", "done": bool(st.get("account")), "value": st.get("account") or ""},
        {"id": "listing", "label": "Store listing", "done": bool(lst.get("title"))},
        {"id": "screens", "label": "Screenshots (from the device check)", "done": shots >= 2, "value": str(shots)},
        {"id": "bundle", "label": "Play Store bundle (.aab)", "done": bool(st.get("bundle"))},
        {"id": "internal", "label": "Internal testing", "done": any(x.get("track") == "internal" for x in st.get("releases") or [])},
        {"id": "production", "label": "Production (your tap)", "done": any(x.get("track") == "production" for x in st.get("releases") or [])},
    ]
    return {"app": r.id, "name": r.name, "package": st.get("package") or "", "proposed": propose_package(r), "locked": bool(st.get("locked")),
            "account": st.get("account") or "", "status": st.get("status") or "", "now": st.get("now") or "", "error": st.get("error") or "",
            "listing": {k: lst.get(k, "") for k in ("title", "short", "full", "by")}, "limits": LIMITS,
            "bundle": st.get("bundle") or {}, "releases": list(reversed(st.get("releases") or []))[:10], "steps": steps,
            "privacy_url": f"{base}/api/app-api/{key}/privacy" if key else "",
            "delete_url": f"{base}/api/app-api/{key}/delete-account" if key else "",
            "data_safety": data_safety(r) if ast.get("apk") else [],
            "console_steps": ["Play Console > Create app (name + default language English (India)) - Google's API can't create it",
                              f"App content > Privacy policy = {base}/api/app-api/{key}/privacy",
                              f"App content > Data deletion = {base}/api/app-api/{key}/delete-account",
                              "App content > Data safety: fill in the answers below",
                              "App content > Content rating questionnaire, Target audience, Ads (No)",
                              "Users and permissions / API access: give the service account 'Release apps to testing tracks' "
                              "(+ 'Release to production' when you want Hoola to send production)"]}


def get(tenant: str, ref: str) -> dict[str, Any]:
    return view(_load(tenant, ref))
