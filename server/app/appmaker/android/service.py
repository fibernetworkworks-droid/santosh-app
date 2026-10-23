"""v0.132 App Sahayak, part 4: from her 'Design pakka' to a real Android app on her phone.

Flow (`build`, ONLY on her approved design): every screen is written in Kotlin + Jetpack Compose by Opus from its approved
web design + the design contract, checked against the house rules (no password / PIN / card fields, no network / files /
intents in screens, only the kit) -> the fixed project is generated (HoolaKit, theme, navigation, legal screens by code) ->
built on the build machine (never this server) -> compile errors go back to the model per screen (max APP_BUILD_ROUNDS,
stops when the same errors come back) -> a screen that still fails gets its simple code-made version, so the app always
builds -> signed with this app's own preview key -> APK on her phone (Android's own "Install?" screen). The project ZIP is
always kept (also when no build machine is set up). Nothing is published to any store here."""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ...db import now, session
from .. import kit as K
from .. import service as AS
from ..models import AppProject
from . import errors as ER
from . import gen as G
from . import prompts as PR
from . import runners as RN
from . import spec as SP

log = logging.getLogger("santosh.appmaker.android")
_LOCK = threading.Lock()
_RUNNING: dict[str, threading.Thread] = {}
APK_LINK_DAYS = 7
STATES = ("writing", "written", "compiling", "fixing", "done", "code")


class AndroidError(AS.AppError):
    pass


def _j(s: str | None, d: Any) -> Any:
    try:
        return json.loads(s) if s else d
    except (TypeError, ValueError):
        return d


def _dir(r: AppProject) -> Path:
    d = K.app_dir(r.tenant_id, r.id) / "android"
    d.mkdir(parents=True, exist_ok=True)
    return d


def state(r: AppProject) -> dict[str, Any]:
    return _j(r.android, {})


def _put(app_id: str, **kw) -> dict[str, Any]:
    with session() as s:
        r = s.get(AppProject, app_id)
        st = _j(r.android, {})
        st.update(kw)
        r.android = json.dumps(st, ensure_ascii=False, default=str)
        r.updated_at = now()
        return st


def _states(app_id: str, upd: dict[str, str], now_line: str = "") -> None:
    with session() as s:
        r = s.get(AppProject, app_id)
        st = _j(r.android, {})
        ss = dict(st.get("states") or {})
        ss.update(upd)
        st["states"] = ss
        if now_line:
            st["now"] = now_line
        r.android = json.dumps(st, ensure_ascii=False, default=str)


# ---------------------------------------------------------------- the app's own preview signing key (same for every build)
def _key(r: AppProject) -> dict[str, str]:
    """PKCS12 (RSA 2048, self-signed, 25 years) sealed with the server vault; the password sealed too. Same key for every
    build of this app, so a new build installs over the old one on her phone."""
    from ...bazar.security import vault
    f = _dir(r) / "preview.key.sealed"
    if f.exists():
        d = json.loads(vault().open(f.read_text()))
        return d
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, f"Hoola preview {r.number or r.id}"),
                      x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Hoola App Sahayak preview")])
    t0 = datetime.now(timezone.utc) - timedelta(days=1)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(t0).not_valid_after(t0 + timedelta(days=365 * 25))
            .sign(key, hashes.SHA256()))
    pw = secrets.token_hex(16)
    p12 = pkcs12.serialize_key_and_certificates(b"preview", key, cert, None,
                                                serialization.BestAvailableEncryption(pw.encode()))
    d = {"p12_b64": base64.b64encode(p12).decode(), "password": pw,
         "sha256": hashlib.sha256(cert.public_bytes(serialization.Encoding.DER)).hexdigest()}
    f.write_text(vault().seal(json.dumps(d)))
    f.chmod(0o600)
    return d


def _app_key(r: AppProject) -> str:
    st = state(r)
    if st.get("app_key"):
        return st["app_key"]
    k = "ak" + secrets.token_hex(12)
    _put(r.id, app_key=k)
    return k


# ---------------------------------------------------------------- start
def build(tenant: str, ref: str, conv: str = "", only: list[str] | None = None) -> dict[str, Any]:
    """Her tap / words 'Android app banao' on an approved design."""
    with session() as s:
        r = AS._find(s, tenant, ref)
        s.expunge(r)
    if r.status != "approved" or not r.approved_hash:
        raise AndroidError("Pehle design pakka kijiye ('Design pakka' button): asli app usi design se banti hai.")
    h = K.design_hash(AS._screens(r), AS._ctx(r))
    if h != r.approved_hash:
        raise AndroidError("Design pakka hone ke baad badla hai; naya design dekh kar dobara pakka kijiye.")
    st = state(r)
    if st.get("status") in ("writing", "building", "fixing"):
        with _LOCK:
            t = _RUNNING.get(r.id)
        if t is not None and t.is_alive():
            return view(r)
    n = int(st.get("build") or 0) + 1
    _put(r.id, status="writing", build=n, design_version=r.version, design_hash=h, error="", note="", rounds=0,
         started=now().isoformat(), ended="", now="Screens Kotlin mein likh raha hoon", states={}, where="",
         conv=conv or r.conv, redo=list(only or []))
    _start(r.id)
    return view(AS._load(r.id))


def _start(app_id: str) -> None:
    if AS._inline():
        run(app_id)
        return
    with _LOCK:
        t = _RUNNING.get(app_id)
        if t is not None and t.is_alive():
            return

    def go():
        try:
            run(app_id)
        finally:
            with _LOCK:
                _RUNNING.pop(app_id, None)
    th = threading.Thread(target=go, name=f"android-{app_id}", daemon=True)
    with _LOCK:
        _RUNNING[app_id] = th
    th.start()


def _emit(app_id: str, push: bool = False) -> None:
    r = AS._load(app_id)
    v = view(r)
    v["push"] = push
    AS._publish(r.tenant_id, "app_android", v, state(r).get("conv") or r.conv)


# ---------------------------------------------------------------- 1. screens in Kotlin
def _cache(r: AppProject) -> Path:
    d = _dir(r) / "screens"
    d.mkdir(exist_ok=True)
    return d


def _ask(system: str, prompt: str) -> str:
    from ...site import ai as SA
    return PR.code_of(SA.ask(system, prompt, 9000, "build"))


def _design_html(s: dict[str, Any]) -> str:
    import re
    h = s.get("html") or ""
    h = re.sub(r"<svg\b.*?</svg>", "<svg/>", h, flags=re.S)
    return h[:14000]


def write_screen(r: AppProject, sid: str, ctx: dict[str, Any], sp: dict[str, Any], scr: dict[str, Any],
                 extra: str = "") -> tuple[str, list[str]]:
    ids = [s["id"] for s in sp["screens"]] + [c for c in ("seller_info", "privacy", "delete_account") if c in sp["code_screens"]]
    me = next(s for s in sp["screens"] if s["id"] == sid)
    system = PR.screen_system(sid, back=not me["tab"], ids=ids, lists=SP.list_fields(sp["seed"]),
                              facts=sorted(k for k in sp["seed"]["facts"] if k != "privacy"), lang=AS._lang_line(r.language),
                              icons=list(sp["icons"]))
    prompt = (f"APP: {sp['app']['name']} ({ctx.get('goal')}).\nSCREEN: {sid} = {me['label']}"
              f"{' (a bottom tab)' if me['tab'] else ''}.\nPURPOSE: {me['purpose']}\nDATA SHOWN: {', '.join(me['data'])}\n"
              f"ACTIONS (label -> screen): {'; '.join(a['label'] + ' -> ' + a['go'] for a in me['actions'])}\n"
              f"COMPONENTS IN THE DESIGN: {', '.join(me['components'])}\n"
              f"LOOK: card {ctx['tokens'].get('card')}, button {ctx['tokens'].get('button')}, header {ctx['tokens'].get('header')} "
              f"(the kit draws these by itself).\n{extra}\nAPPROVED WEB DESIGN OF THIS SCREEN (HTML; match it):\n{_design_html(scr)}")
    src = _ask(system, prompt)
    probs = G.scan_screen(src, sid, ids)
    if probs:
        src2 = _ask(PR.fix_system(sid, ids), "HOUSE-RULE PROBLEMS:\n- " + "\n- ".join(probs) + "\n\nFILE:\n```kotlin\n" + src + "```")
        p2 = G.scan_screen(src2, sid, ids)
        if len(p2) < len(probs) or not p2:
            src, probs = src2, p2
    return src, probs


# ---------------------------------------------------------------- 2..5 generate, build, fix, deliver
def run(app_id: str) -> None:
    r = AS._load(app_id)
    try:
        _run(r)
    except Exception as e:                           # noqa: BLE001
        log.exception("android build %s", app_id)
        _put(app_id, status="failed", error=AS._tidy(str(e), 300), ended=now().isoformat(), now="")
        _emit(app_id, push=True)


def _run(r: AppProject) -> None:
    st = state(r)
    n = int(st.get("build") or 1)
    ctx = AS._ctx(r)
    screens = AS._screens(r)
    work = _dir(r)
    base = (AS._settings().public_base_url or "").rstrip("/")
    key = _key(r)
    sp = SP.build(r, ctx["plan"], ctx["tokens"], ctx["facts"], screens, work, version_code=r.version * 100 + (n % 100),
                  base_url=base, app_key=_app_key(r))
    sp["preview_key"] = key
    ids = [s["id"] for s in sp["screens"]]
    cache = _cache(r)
    redo = set(st.get("redo") or [])
    kt: dict[str, str] = {}
    code_only: set[str] = set()
    _put(r.id, states={sid: "writing" for sid in ids}, total=len(ids))
    _emit(r.id)
    for i, sid in enumerate(ids):
        if AS._load(r.id).stop:
            raise AndroidError("rok diya")
        f = cache / f"{st.get('design_hash', '')[:12]}-{sid}.kt"
        if f.exists() and sid not in redo:
            kt[sid] = f.read_text()
            _states(r.id, {sid: "written"})
            continue
        _states(r.id, {sid: "writing"}, f"Kotlin: {next(s['label'] for s in sp['screens'] if s['id'] == sid)} ({i + 1}/{len(ids)})")
        _emit(r.id)
        try:
            src, probs = write_screen(r, sid, ctx, sp, screens.get(sid) or {})
        except Exception as e:                       # noqa: BLE001
            log.info("screen %s not written: %s", sid, e)
            src, probs = "", ["not written"]
        if probs:
            code_only.add(sid)
            _states(r.id, {sid: "code"})
        else:
            kt[sid] = src
            f.write_text(src)
            _states(r.id, {sid: "written"})
    src_dir = work / "project"
    sp["screens_kt"] = kt
    res = G.write_project(sp, src_dir)
    zip_bytes = RN.zip_project(src_dir, export=True)
    (work / f"project-b{n}.zip").write_bytes(zip_bytes)
    _prune(work, "project-b", 3)
    _put(r.id, zip=f"project-b{n}.zip", zip_size=len(zip_bytes), package=res["app_id"], kinds=res["screens"],
         zip_token=secrets.token_urlsafe(24), zip_expires=(now() + timedelta(days=APK_LINK_DAYS)).isoformat())
    if not RN.describe()["ready"] and RN._override is None:
        _put(r.id, status="zip", ended=now().isoformat(), now="",
             note="Build machine abhi set nahi hai: project ZIP taiyaar hai (Android Studio mein khul jaata hai).")
        _note(r, "Android app ka project taiyaar (ZIP). APK banane wali machine abhi set nahi hai; set hote hi 'Android app banao' "
                 "dobara kahiye.")
        _emit(r.id, push=True)
        return
    rounds = max(1, int(AS._settings().app_build_rounds or 4))
    seen: dict[str, set[str]] = {}
    result: dict[str, Any] = {}
    for rnd in range(rounds + 1):
        _put(r.id, status="building" if rnd == 0 else "fixing", rounds=rnd,
             now="Android Studio ki tarah compile ho raha hai" if rnd == 0 else f"Compile ki galtiyan theek: round {rnd}")
        _states(r.id, {sid: "compiling" for sid in kt})
        _emit(r.id)
        result = RN.build(src_dir, r.id.replace("_", "-")[:60].lower(), lambda stage: _put(r.id, stage=stage))
        _put(r.id, where=result.get("where", ""), seconds=result.get("seconds"))
        if result.get("ok") and result.get("apk"):
            break
        errs = ER.parse(result.get("log") or "")
        if errs["project"]:
            raise AndroidError("Build machine par project nahi bana (Hoola ki taraf ki galti, team ko bataiye): "
                               + "; ".join(errs["project"][:3]))
        bad = {}
        for cls, el in errs["screens"].items():
            sid = next((s for s in ids if G.kotlin_name(s) == cls), None)
            if sid:
                bad[sid] = el
        if not bad:
            raise AndroidError("Build nahi hua: " + "; ".join(errs["other"][:3]))
        last = rnd == rounds
        for sid, el in bad.items():
            sig = ER.signature(el)
            again = sig in seen.setdefault(sid, set())
            seen[sid].add(sig)
            if last or again or sid not in kt:
                kt.pop(sid, None)
                code_only.add(sid)
                _states(r.id, {sid: "code"})
                continue
            _states(r.id, {sid: "fixing"}, f"Theek kar raha hoon: {sid}")
            try:
                src = _ask(PR.fix_system(sid, ids), "COMPILE ERRORS:\n" + ER.for_model(el, kt[sid]) + "\n\nFILE:\n```kotlin\n" + kt[sid] + "```")
            except Exception:                        # noqa: BLE001
                src = ""
            if src and not G.scan_screen(src, sid, ids):
                kt[sid] = src
                (cache / f"{st.get('design_hash', '')[:12]}-{sid}.kt").write_text(src)
            else:
                kt.pop(sid, None)
                code_only.add(sid)
                _states(r.id, {sid: "code"})
        sp["screens_kt"] = kt
        G.write_project(sp, src_dir)
    if not (result.get("ok") and result.get("apk")):
        raise AndroidError("APK nahi bana (" + "; ".join(ER.parse(result.get("log") or "")["other"][:2]) + ")")
    apk = result["apk"]
    name = f"{AS._tidy(r.name, 30).replace(' ', '-') or 'app'}-v{r.version}-b{n}.apk"
    (work / "apk").mkdir(exist_ok=True)
    for old in (work / "apk").glob("*.apk"):
        old.unlink()
    (work / "apk" / name).write_bytes(apk)
    zb = RN.zip_project(src_dir, export=True)
    (work / f"project-b{n}.zip").write_bytes(zb)
    _put(r.id, zip_size=len(zb))
    sha = hashlib.sha256(apk).hexdigest()
    token = secrets.token_urlsafe(24)
    _states(r.id, {sid: ("code" if sid in code_only else "done") for sid in ids})
    _put(r.id, status="ready", ended=now().isoformat(), now="", error="",
         apk={"file": name, "sha256": sha, "size": len(apk), "package": sp["app"]["app_id"], "version_code": sp["app"]["version_code"],
              "version_name": sp["app"]["version_name"], "token": token,
              "expires": (now() + timedelta(days=APK_LINK_DAYS)).isoformat(), "at": now().isoformat()},
         stats={"model": len(kt), "code": len(code_only)}, kinds={sid: ("code" if sid in code_only else "model") for sid in ids})
    _note(r, f"Android app taiyaar: {r.name or 'App'} (v{r.version}, build {n}). {len(kt)} screens Opus ne Kotlin mein likhi"
             + (f", {len(code_only)} saada (code se)" if code_only else "") + ". 'Phone pe install karo' dabaiye.")
    _emit(r.id, push=True)


def _prune(d: Path, prefix: str, keep: int) -> None:
    files = sorted(d.glob(f"{prefix}*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in files[keep:]:
        p.unlink(missing_ok=True)


def _note(r: AppProject, text: str) -> None:
    from ...events import notify
    try:
        conv = state(AS._load(r.id)).get("conv") or r.conv
        if not conv:
            from ...net.service import home_conv
            conv = home_conv(r.tenant_id)
        notify(conv, text)
    except Exception:
        log.debug("note", exc_info=True)


# ---------------------------------------------------------------- views / files
def view(r: AppProject) -> dict[str, Any]:
    st = state(r)
    plan = _j(r.plan, {})
    labels = plan.get("labels") or {}
    ss = st.get("states") or {}
    base = (AS._settings().public_base_url or "").rstrip("/")
    apk = st.get("apk") or {}
    link = ""
    if apk.get("token") and apk.get("expires", "") > now().isoformat():
        link = f"{base}/api/app-apk/{apk['token']}/{apk['file']}"
    return {"id": r.id, "number": r.number, "name": r.name, "design_status": r.status, "design_version": r.version,
            "status": st.get("status") or "", "build": st.get("build") or 0, "now": st.get("now") or "", "stage": st.get("stage") or "",
            "error": st.get("error") or "", "note": st.get("note") or "", "rounds": st.get("rounds") or 0, "where": st.get("where") or "",
            "seconds": st.get("seconds"), "runner": RN.describe(),
            "screens": [{"id": sid, "label": labels.get(sid) or sid, "state": ss.get(sid, "todo")} for sid in plan.get("screens", [])],
            "stats": st.get("stats") or {}, "zip": bool(st.get("zip")), "zip_size": st.get("zip_size") or 0,
            "zip_url": (f"{base}/api/app-zip/{st['zip_token']}/{st['zip']}" if st.get("zip_token") and st.get("zip")
                        and st.get("zip_expires", "") > now().isoformat() else ""),
            "apk": {k: apk.get(k) for k in ("file", "sha256", "size", "package", "version_code", "version_name", "at")} if apk else {},
            "apk_url": link, "approved": bool(r.approved_hash), "say": _say(r, st, link)}


def _say(r: AppProject, st: dict[str, Any], link: str) -> str:
    s = st.get("status")
    if s == "writing":
        return f"Android app ban rahi hai: {st.get('now') or 'screens Kotlin mein'}."
    if s in ("building", "fixing"):
        return f"Compile ho rahi hai ({st.get('where') or 'build machine'})" + (f", round {st.get('rounds')}" if st.get("rounds") else "") + "."
    if s == "ready":
        return f"Android app taiyaar (build {st.get('build')}). Phone pe install karne ke liye card par 'Install' dabaiye."
    if s == "zip":
        return "Android project ZIP taiyaar (build machine set nahi hai, isliye APK nahi bana)."
    if s == "failed":
        return f"Android build mein dikkat: {st.get('error')}"
    return "Design pakka hai: 'Android app banao' kahiye." if r.approved_hash else "Pehle design pakka kijiye."


def get(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = AS._find(s, tenant, ref)
        s.expunge(r)
    return view(r)


def zip_file(tenant: str, ref: str) -> tuple[Path, str]:
    with session() as s:
        r = AS._find(s, tenant, ref)
        s.expunge(r)
    st = state(r)
    f = _dir(r) / str(st.get("zip") or "")
    if not st.get("zip") or not f.exists():
        raise AndroidError("Project ZIP abhi nahi bana.")
    return f, f"{AS._tidy(r.name, 30).replace(' ', '-') or 'app'}-android-project.zip"


def file_by_token(token: str, name: str, kind: str = "apk") -> Path:
    """The public links (random token, 7 days): her phone's installer downloads the APK, her laptop the project ZIP."""
    if not token or len(token) < 20 or "/" in name or ".." in name:
        raise AndroidError("not found")
    with session() as s:
        rows = s.query(AppProject).filter(AppProject.android.like(f'%"{token}"%')).all()
        for r in rows:
            st = _j(r.android, {})
            if kind == "apk":
                apk = st.get("apk") or {}
                good = secrets.compare_digest(apk.get("token", ""), token) and apk.get("file") == name and apk.get("expires", "") > now().isoformat()
                f = K.app_dir(r.tenant_id, r.id) / "android" / "apk" / name
            else:
                good = secrets.compare_digest(str(st.get("zip_token") or ""), token) and st.get("zip") == name and st.get("zip_expires", "") > now().isoformat()
                f = K.app_dir(r.tenant_id, r.id) / "android" / name
            if good and f.exists():
                return f
    raise AndroidError("not found")


def apk_by_token(token: str, name: str) -> Path:
    return file_by_token(token, name, "apk")


def apk_file(tenant: str, ref: str) -> tuple[Path, str]:
    with session() as s:
        r = AS._find(s, tenant, ref)
        s.expunge(r)
    apk = state(r).get("apk") or {}
    f = _dir(r) / "apk" / str(apk.get("file") or "")
    if not apk.get("file") or not f.exists():
        raise AndroidError("APK abhi nahi bana.")
    return f, apk["file"]


# ---------------------------------------------------------------- the app's live content (public, read only)
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def content(app_key: str) -> dict[str, Any]:
    """What the installed app shows: her PUBLIC facts and products (fresh), sample lists marked as samples. No orders, no
    customers, nothing private: the same things her website shows."""
    if not app_key or not app_key.startswith("ak") or len(app_key) > 40:
        raise AndroidError("not found")
    hit = _CACHE.get(app_key)
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    with session() as s:
        r = s.query(AppProject).filter(AppProject.android.like(f'%"app_key": "{app_key}"%')).first()
        if r is None or _j(r.android, {}).get("app_key") != app_key:
            raise AndroidError("not found")
        s.expunge(r)
    facts = AS.gather_facts(r.tenant_id, "")
    merged = {**_j(r.facts, {}), **{k: v for k, v in facts.items() if v}}
    sd = SP.seed(r.name, r.goal, merged, _j(r.plan, {}))
    out = {"facts": sd["facts"], "lists": sd["lists"], "demo_lists": sd["demo_lists"], "at": now().isoformat()}
    _CACHE[app_key] = (time.time(), out)
    return out
