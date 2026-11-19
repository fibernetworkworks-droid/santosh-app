"""v0.416 GAME PLATFORMS (Hoola Game Engine plan, Phase 6): the live game as real downloads for every platform, the store
pages around it, an age-rating draft, and itch.io uploads by her tap.

- RELEASES (`game_releases`): one release = the live version exported for the platforms she picked, each file CHECKED in
  code (exists, the right kind of file inside, size, sha256) and kept with a signed download link.
  * linux / windows / macos: exported ON this server with Godot's release templates (`deploy/setup_godot.py --desktop`),
    one-file builds (the game data embedded), zipped with a README. macOS is ad-hoc signed and NOT notarised: Mac users
    right-click > Open the first time (said in the README and the store kit).
  * android: APK (install on a phone) or AAB (Google Play), built in HER private builds repo (App Builder's GitHub
    runner, workflow hoola-game.yml) because it needs the Android SDK; signed with this game's own UPLOAD key (PKCS12,
    made here, sealed in the vault, never shown). No builds repo = NOT ASSESSED for Android, never a fake file.
  * every Hoola game asks for NO internet permission (games never use the network).
  * the package name is made once per project and never changes; the version code only goes up.
- STORE KIT: store texts for itch.io / Steam / Google Play checked against each store's limits in code, the store
  images in the exact sizes each store asks (from the game's own screens + its title, drawn in code, no money), the
  AI-content disclosure from the asset list, and the Steam upload scripts (Hoola never logs into her Steam).
- AGE RATING DRAFT: the IARC-style questions answered from the Game Bible, the assets and Hoola's own rules (no real
  money, no chat, no location, no ads) - a DRAFT she checks; the real rating comes from IARC / the store.
- ITCH.IO: her own itch.io API key (typed in the app, sealed); an upload is a CARD and only her tap runs itch's official
  `butler push`. Nothing is published by Hoola alone."""
from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import logging
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..config import get_settings
from ..db import Base, new_id, now, session
from . import engine
from . import service as G
from . import template as T

log = logging.getLogger("santosh.gamedesk")
DESKTOP = {"linux": "linux_release.x86_64", "windows": "windows_release_x86_64.exe", "macos": "macos.zip"}
PLATFORMS = ("linux", "windows", "macos", "android")
BUDGET_MB = {"linux": 200, "windows": 220, "macos": 260, "android": 200}
_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gamerelease")


class PlatformError(G.GameError):
    pass


class GameRelease(Base):
    __tablename__ = "game_releases"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("gr"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    studio_id: Mapped[str] = mapped_column(String(40), index=True)
    number: Mapped[str] = mapped_column(String(16), default="")
    version: Mapped[int] = mapped_column(Integer, default=0)            # the game version inside
    version_code: Mapped[int] = mapped_column(Integer, default=0)       # only goes up (stores need that)
    version_name: Mapped[str] = mapped_column(String(20), default="")
    package: Mapped[str] = mapped_column(String(120), default="")
    platforms: Mapped[dict] = mapped_column(JSON, default=dict)         # {platform: {status, file, mb, sha256, checks, note}}
    status: Mapped[str] = mapped_column(String(12), default="building")  # building | done | partial | failed
    log: Mapped[str] = mapped_column(Text, default="")
    itch: Mapped[dict] = mapped_column(JSON, default=dict)              # {card, pushed}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


_READY: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        GameRelease.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def _studio(tenant: str, ref: str):
    from . import studio as S
    with session() as s:
        r = S._studio(s, tenant, ref)
        s.expunge(r)
    return r


def _rdir(tenant: str, sid: str, rid: str) -> Path:
    return G.root() / (re.sub(r"[^\w-]", "_", tenant)[:64] or "t") / "releases" / sid / rid


# ---------------------------------------------------------------- where each platform can be built
def targets() -> dict[str, Any]:
    tpl = engine.templates_dir()
    out = {}
    for p, f in DESKTOP.items():
        ok = bool(engine.find() and tpl and (tpl / f).is_file())
        out[p] = {"ready": ok, "where": "this server",
                  "note": "" if ok else "run deploy/setup_godot.py --desktop on the server once (the desktop templates)"}
    try:
        from ..appmaker.android import runners
        gh = runners.mode() == "github"
    except Exception:                                   # noqa: BLE001
        gh = False
    out["android"] = {"ready": gh, "where": "your private builds repo (GitHub Actions)",
                      "note": "" if gh else "set up App Builder's GitHub builds repo (APP_BUILD_MODE=github) - Android needs the Android SDK"}
    return out


# ---------------------------------------------------------------- identity of the game on the stores
def _slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "", (title or "game").lower())[:24] or "game"
    return s if s[0].isalpha() else f"g{s}"[:24]


def identity(tenant: str, ref: str) -> dict[str, Any]:
    """The package name (made once, never changed) and the next version code."""
    from . import studio as S
    r = _studio(tenant, ref)
    with session() as s:
        row = s.get(S.GameStudio, r.id)
        pf = dict(row.platform or {})
        if not pf.get("package"):
            tail = hashlib.sha1(f"{tenant}:{r.id}".encode()).hexdigest()[:6]
            pf["package"] = f"com.hoola.{_slug(r.title)}{tail}"
            pf["version_code"] = 0
            row.platform = pf
    return pf


def _next_code(sid: str) -> int:
    from . import studio as S
    with session() as s:
        row = s.get(S.GameStudio, sid)
        pf = dict(row.platform or {})
        pf["version_code"] = int(pf.get("version_code") or 0) + 1
        row.platform = pf
        return pf["version_code"]


def _upload_key(tenant: str, sid: str) -> dict[str, str]:
    """This game's Android UPLOAD key (PKCS12 + password), sealed by the vault; Google Play App Signing keeps the real
    app-signing key; a lost upload key can be reset in Play Console. Never shown, never in chat."""
    from ..bazar.security import vault
    f = G.root() / (re.sub(r"[^\w-]", "_", tenant)[:64] or "t") / "releases" / sid / "upload.key.sealed"
    if f.exists():
        return json.loads(vault().open(f.read_text()))
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Hoola game upload key")])
    t0 = datetime.now(timezone.utc) - timedelta(days=1)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(t0).not_valid_after(t0 + timedelta(days=365 * 27))
            .sign(key, hashes.SHA256()))
    pw = secrets.token_hex(16)
    p12 = pkcs12.serialize_key_and_certificates(b"upload", key, cert, None, serialization.BestAvailableEncryption(pw.encode()))
    d = {"p12_b64": base64.b64encode(p12).decode(), "password": pw, "alias": "upload",
         "sha256": hashlib.sha256(cert.public_bytes(serialization.Encoding.DER)).hexdigest()}
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(vault().seal(json.dumps(d)))
    f.chmod(0o600)
    return d


# ---------------------------------------------------------------- checks (code)
def check_artifact(platform: str, path: Path) -> dict[str, list[str]]:
    errors: list[str] = []
    warns: list[str] = []
    if not path.is_file() or path.stat().st_size == 0:
        return {"errors": [f"no {platform} file was made"], "warnings": []}
    mb = path.stat().st_size / 1e6
    if mb > BUDGET_MB[platform]:
        warns.append(f"{round(mb)} MB is big for {platform} (budget {BUDGET_MB[platform]} MB)")
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            if platform == "linux":
                bins = [n for n in names if n.endswith(".x86_64")]
                if not bins or z.read(bins[0])[:4] != b"\x7fELF":
                    errors.append("the Linux zip has no Linux program in it")
            elif platform == "windows":
                exe = [n for n in names if n.endswith(".exe")]
                if not exe or z.read(exe[0])[:2] != b"MZ":
                    errors.append("the Windows zip has no Windows program in it")
            elif platform == "macos":
                if not any(n.endswith(".app/Contents/Info.plist") for n in names):
                    errors.append("the macOS zip has no .app in it")
                if not any(n.endswith(".pck") for n in names):
                    errors.append("the macOS app has no game data (.pck)")
            elif platform == "android":
                if path.suffix == ".apk" and "AndroidManifest.xml" not in names:
                    errors.append("the APK has no AndroidManifest.xml")
                if path.suffix == ".aab" and "base/manifest/AndroidManifest.xml" not in names:
                    errors.append("the AAB has no base manifest")
                if path.suffix == ".apk" and not any(n.startswith("META-INF/") for n in names) and "classes.dex" in names:
                    warns.append("the APK may not be signed (v1 signature files missing; v2 may still be there)")
    except zipfile.BadZipFile:
        errors.append(f"the {platform} file is not a valid package")
    return {"errors": errors, "warnings": warns}


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- building a release
def release(tenant: str, ref: str, platforms: list[str], android_format: str = "apk") -> dict[str, Any]:
    """Start a release of the live version for these platforms (background)."""
    ensure_table()
    plats = [p for p in dict.fromkeys(platforms or []) if p in PLATFORMS]
    if not plats:
        raise PlatformError("platforms = " + ", ".join(PLATFORMS))
    r = _studio(tenant, ref)
    g = G._get(tenant, r.game_id) if r.game_id else None
    good = G._good(g) if g else []
    if not good:
        raise PlatformError("A working version of the game is needed first.")
    with session() as s:
        if s.scalars(select(GameRelease).where(GameRelease.studio_id == r.id, GameRelease.status == "building")).first():
            raise PlatformError("A release is being built now; let it finish.")
        n = len(s.scalars(select(GameRelease.id).where(GameRelease.studio_id == r.id)).all())
    idn = identity(tenant, r.id)
    code = _next_code(r.id)
    rel = GameRelease(tenant_id=tenant, studio_id=r.id, number=f"R-{n + 1:03d}", version=good[-1]["n"], version_code=code,
                      version_name=f"1.0.{code}", package=idn["package"],
                      platforms={p: {"status": "queued"} for p in plats}, status="building")
    rel.platforms = {p: {"status": "queued", **({"format": "aab" if android_format == "aab" else "apk"} if p == "android" else {})}
                     for p in plats}
    with session() as s:
        s.add(rel)
        s.flush()
        rid = rel.id
        s.expunge(rel)
    if os.environ.get("GAME_WORKER", "true").lower() not in ("0", "false", "off"):
        _POOL.submit(_safe, tenant, rid)
    return view(rel)


def _safe(tenant: str, rid: str) -> None:
    try:
        run_release(tenant, rid)
    except Exception as e:                              # noqa: BLE001
        log.exception("release %s", rid)
        with session() as s:
            row = s.get(GameRelease, rid)
            if row is not None:
                row.status, row.log = "failed", f"internal error: {type(e).__name__}: {str(e)[:200]}"


def _readme(title: str, platform: str, version: str) -> str:
    how = {"linux": "Unzip, then run ./game.x86_64 (make it executable: chmod +x game.x86_64).",
           "windows": "Unzip and double-click game.exe. Windows may say 'unknown publisher' (the game is not code-signed): "
                      "More info > Run anyway.",
           "macos": "Unzip and open the app. It is not notarised by Apple, so the first time: right-click > Open > Open."}[platform]
    return f"{title} {version}\n\n{how}\n\nMade with Hoola Studio on Godot Engine (godotengine.org, MIT licence).\n"


def _set(rid: str, platform: str, **kw) -> None:
    with session() as s:
        row = s.get(GameRelease, rid)
        pf = dict(row.platforms or {})
        pf[platform] = {**pf.get(platform, {}), **kw}
        row.platforms = pf
        row.updated_at = now()


def run_release(tenant: str, rid: str) -> dict[str, Any]:
    with session() as s:
        rel = s.get(GameRelease, rid)
        s.expunge(rel)
    r = _studio(tenant, rel.studio_id)
    g = G._get(tenant, r.game_id)
    src = G._vdir(g, rel.version) / "proj"
    out = _rdir(tenant, r.id, rid)
    job = out / "job"
    shutil.rmtree(job, ignore_errors=True)
    shutil.copytree(src, job / "proj", ignore=shutil.ignore_patterns(".godot"))
    _app_icon(tenant, r.id, job / "proj")
    fmt = (rel.platforms.get("android") or {}).get("format", "apk")
    (job / "proj" / "export_presets.cfg").write_text(T.native_presets(r.title, rel.package, rel.version_code,
                                                                       rel.version_name, g.orientation, fmt))
    logs: list[str] = []
    tg = targets()
    desktop = [p for p in rel.platforms if p in DESKTOP]
    if desktop:
        try:
            sm = engine.smoke(job)
            if not sm.get("ok"):
                for p in desktop:
                    _set(rid, p, status="failed", note="the game does not start: " + "; ".join(sm.get("errors", [])[:2]))
                desktop = []
        except engine.EngineError as e:
            for p in desktop:
                _set(rid, p, status="not assessed", note=str(e))
            desktop = []
    for p in desktop:
        if not tg[p]["ready"]:
            _set(rid, p, status="not assessed", note=tg[p]["note"])
            continue
        _set(rid, p, status="building")
        name = {"linux": "Linux", "windows": "Windows Desktop", "macos": "macOS"}[p]
        target = {"linux": "dist/linux/game.x86_64", "windows": "dist/windows/game.exe", "macos": "dist/macos/game.zip"}[p]
        (job / target).parent.mkdir(parents=True, exist_ok=True)
        code, text, to = engine._run(job, ["--path", "proj", "--export-release", name, f"../{target}"], f"export_{p}.log",
                                     int(os.environ.get("GAME_EXPORT_TIMEOUT_S", "300")))
        logs.append(f"[{p}] exit {code}" + (" timeout" if to else "") + " " + " | ".join(engine.errors_in(text)[:3]))
        built = job / target
        if not built.is_file():
            _set(rid, p, status="failed", note=("export timed out" if to else "export failed: ") + " | ".join(engine.errors_in(text)[:2]))
            continue
        final = out / f"{_slug(r.title)}-{rel.version_name}-{p}.zip"
        if p == "macos":
            shutil.copy2(built, final)
        else:
            with zipfile.ZipFile(final, "w", zipfile.ZIP_DEFLATED) as z:
                z.write(built, f"{_slug(r.title)}/{built.name}")
                z.writestr(f"{_slug(r.title)}/README.txt", _readme(r.title, p, rel.version_name))
        ck = check_artifact(p, final)
        _set(rid, p, status="failed" if ck["errors"] else "done", file=final.name, mb=round(final.stat().st_size / 1e6, 1),
             sha256=_sha(final), checks=ck)
    if "android" in rel.platforms:
        if not tg["android"]["ready"]:
            _set(rid, "android", status="not assessed", note=tg["android"]["note"])
        else:
            _set(rid, "android", status="building")
            res = _android(tenant, r, rel, job / "proj", out, fmt)
            logs.append("[android] " + res.get("log", "")[-600:])
            if res.get("file"):
                f = out / res["file"]
                ck = check_artifact("android", f)
                _set(rid, "android", status="failed" if ck["errors"] else "done", file=f.name, mb=round(f.stat().st_size / 1e6, 1),
                     sha256=_sha(f), checks=ck, format=fmt)
            else:
                _set(rid, "android", status="failed", note=res.get("note") or "the builds repo did not return a file")
    shutil.rmtree(job, ignore_errors=True)
    with session() as s:
        row = s.get(GameRelease, rid)
        sts = [v.get("status") for v in (row.platforms or {}).values()]
        row.status = "done" if all(x == "done" for x in sts) else "failed" if not any(x == "done" for x in sts) else "partial"
        row.log = "\n".join(logs)[:6000]
        row.updated_at = now()
        s.flush()
        s.expunge(row)
    from . import studio as S
    S._decide(r, f"Release {row.number} (v{row.version}, {row.version_name}): {row.status}",
              ", ".join(f"{k} {v.get('status')}" for k, v in (row.platforms or {}).items()), by="hoola")
    return view(row)


def _app_icon(tenant: str, sid: str, proj: Path) -> None:
    """The approved 'app_icon' asset (icon kind) becomes the game's icon on every platform."""
    try:
        from . import assets as A
        A.ensure_table()
        with session() as s:
            a = s.scalars(select(A.GameAsset).where(A.GameAsset.studio_id == sid, A.GameAsset.key == "app_icon",
                                                   A.GameAsset.approved > 0)).first()
            if a is None:
                return
            h = next((x for x in a.history or [] if x.get("v") == a.approved), None)
            src = A._dir(tenant, sid, a.key) / h["file"] if h else None
        if src and src.is_file():
            shutil.copy2(src, proj / "icon.png")
            pg = proj / "project.godot"
            txt = pg.read_text()
            if "config/icon=" not in txt:
                pg.write_text(txt.replace('run/main_scene="res://main.tscn"', 'run/main_scene="res://main.tscn"\nconfig/icon="res://icon.png"'))
    except Exception:                                   # noqa: BLE001
        log.exception("app icon")


def _android(tenant: str, r, rel: GameRelease, proj: Path, out: Path, fmt: str) -> dict[str, Any]:
    """Android in her builds repo: the project + this game's upload key pushed to build/game-<project>, workflow
    hoola-game.yml, the APK / AAB back as an artifact."""
    from ..appmaker.android import runners
    push = out / "push"
    shutil.rmtree(push, ignore_errors=True)
    shutil.copytree(proj, push / "game", ignore=shutil.ignore_patterns(".godot", "dist"))
    k = _upload_key(tenant, r.id)
    (push / "keys").mkdir(parents=True)
    (push / "keys" / "upload.p12").write_bytes(base64.b64decode(k["p12_b64"]))
    (push / "keys" / "upload.json").write_text(json.dumps({"alias": k["alias"], "password": k["password"]}))
    t0 = time.time()
    try:
        repo, branch, sha = runners.push_tree(push, f"game-{r.number.lower()}", lambda m: None, prefix="hoola-game")
        jid = hashlib.sha256(f"{rel.id}{sha}{time.time()}".encode()).hexdigest()[:16]
        run = runners.dispatch_wait(repo, branch, sha, "hoola-game.yml", {"job": jid, "format": fmt}, lambda m: None, t0,
                                    int(os.environ.get("GAME_ANDROID_TIMEOUT_S", "2400")))
        if not run:
            return {"note": "the builds repo did not finish in time", "log": ""}
        text, fname = "", ""
        for zb in runners.artifacts(repo, run, (f"hoola-game-{jid}",)):
            with zipfile.ZipFile(io.BytesIO(zb)) as z:
                for n in z.namelist():
                    if n.endswith(f"game.{fmt}"):
                        fname = f"{_slug(r.title)}-{rel.version_name}.{fmt}"
                        (out / fname).write_bytes(z.read(n))
                    elif n.endswith("build.log"):
                        text = z.read(n).decode(errors="replace")
        if run.get("conclusion") != "success":
            return {"note": f"builds repo run {run.get('conclusion')}", "log": text, "file": fname if fname else ""}
        return {"file": fname, "log": text}
    except runners.BuildUnavailable as e:
        return {"note": str(e)[:300], "log": ""}
    finally:
        shutil.rmtree(push, ignore_errors=True)


# ---------------------------------------------------------------- views + downloads
def _dsig(rid: str, platform: str, exp: int) -> str:
    st = get_settings()
    key = st.secret_key or st.api_key or "hoola-release"
    return hmac.new(f"grl:{key}".encode(), f"{rid}/{platform}:{exp}".encode(), hashlib.sha256).hexdigest()[:32]


def download_url(rid: str, platform: str, days: int = 7) -> str:
    exp = int(time.time()) + days * 86400
    return f"/api/gamestudio/release/{rid}/{platform}?exp={exp}&sig={_dsig(rid, platform, exp)}"


def download_file(rid: str, platform: str, exp: int, sig: str) -> Path | None:
    if exp < time.time() or not hmac.compare_digest(_dsig(rid, platform, exp), sig or ""):
        return None
    ensure_table()
    with session() as s:
        row = s.get(GameRelease, rid)
        if row is None or (row.platforms or {}).get(platform, {}).get("status") != "done":
            return None
        p = _rdir(row.tenant_id, row.studio_id, rid) / row.platforms[platform]["file"]
    return p if p.is_file() else None


def view(rel: GameRelease) -> dict[str, Any]:
    pf = {}
    for k, v in (rel.platforms or {}).items():
        pf[k] = {**v, **({"url": download_url(rel.id, k)} if v.get("status") == "done" else {})}
    return {"id": rel.id, "number": rel.number, "version": rel.version, "version_code": rel.version_code,
            "version_name": rel.version_name, "package": rel.package, "status": rel.status, "platforms": pf,
            "log": rel.log[-2000:], "itch": rel.itch or {}, "created_at": rel.created_at.isoformat() if rel.created_at else None}


def releases(tenant: str, ref: str) -> dict[str, Any]:
    ensure_table()
    r = _studio(tenant, ref)
    with session() as s:
        rows = s.scalars(select(GameRelease).where(GameRelease.studio_id == r.id).order_by(GameRelease.created_at.desc())).all()
        out = [view(x) for x in rows]
    return {"releases": out, "targets": targets(), "identity": identity(tenant, r.id), "itch_key": bool(_itch_key(tenant))}


# ---------------------------------------------------------------- store kit
LIMITS = {"itch": {"title": 50, "tagline": 80, "description": 4000}, "steam": {"short": 300, "about": 4000},
          "play": {"title": 30, "short": 80, "full": 4000}}
IMAGES = {"itch_cover": (630, 500), "steam_header": (920, 430), "steam_small": (462, 174), "steam_main": (1232, 706),
          "steam_library": (600, 900), "play_feature": (1024, 500), "play_icon": (512, 512)}

KIT = """You write store pages for a small original game. Write in clear, warm English (no hype words like
"revolutionary", no claims you cannot know: no awards, no player counts, no prices). Use ONLY the facts given. OUTPUT
only JSON: {"itch": {"title", "tagline", "description" (markdown, 120-250 words), "tags": [5-10 lowercase]},
"steam": {"short" (<= 300 characters), "about" (180-350 words, plain), "tags": [5-15]},
"play": {"title" (<= 30), "short" (<= 80), "full" (150-400 words)}}."""


def _facts(tenant: str, r) -> dict[str, Any]:
    g = G._get(tenant, r.game_id)
    facts: dict[str, Any] = {"title": r.title, "goal": r.goal, "design": (g.design or "")[:3000], "orientation": g.orientation}
    try:
        from . import bible as B
        d = B.view(tenant, r.id)["data"]
        facts["pillars"] = (d.get("meta") or {}).get("pillars")
        facts["genre"] = (d.get("meta") or {}).get("genre")
        facts["counts"] = {k: len(v or []) for k, v in (d.get("entities") or {}).items() if v}
    except Exception:                                   # noqa: BLE001
        pass
    return facts


def _clip_text(kit: dict, notes: list[str]) -> dict:
    for store, lim in LIMITS.items():
        for k, n in lim.items():
            v = str(((kit.get(store) or {}).get(k)) or "")
            if len(v) > n:
                notes.append(f"{store} {k} was {len(v)} characters; cut to {n}")
                v = v[:n].rsplit(" ", 1)[0]
            kit.setdefault(store, {})[k] = v
    return kit


def _ai_disclosure(tenant: str, sid: str) -> str:
    try:
        from . import assets as A
        A.ensure_table()
        with session() as s:
            rows = s.scalars(select(A.GameAsset).where(A.GameAsset.studio_id == sid, A.GameAsset.approved > 0)).all()
            ai = sorted({a.kind for a in rows for h in (a.history or []) if h.get("v") == a.approved
                         and h.get("source") not in ("her upload", "synth")})
    except Exception:                                   # noqa: BLE001
        ai = []
    parts = ["The game's code was written with the help of AI (Hoola) and checked and approved by the developer."]
    if ai:
        parts.append("Pre-generated with AI and approved by the developer: " + ", ".join(ai) + ".")
    parts.append("No AI content is generated while the game is played.")
    return " ".join(parts)


def _image(base: bytes | None, size: tuple[int, int], title: str, palette: list[str]) -> bytes:
    from PIL import Image, ImageDraw, ImageFont
    w, h = size
    bg = palette[0] if palette else "#101820"
    canvas = Image.new("RGB", (w, h), bg)
    try:
        src = Image.open(io.BytesIO(base)).convert("RGB") if base else None
    except Exception:                                   # noqa: BLE001 - a broken screenshot = a plain background
        src = None
    if src is not None:
        s = max(w / src.size[0], h / src.size[1])
        src = src.resize((int(src.size[0] * s) + 1, int(src.size[1] * s) + 1))
        canvas.paste(src, ((w - src.size[0]) // 2, (h - src.size[1]) // 2))
    d = ImageDraw.Draw(canvas, "RGBA")
    band = int(h * 0.26)
    d.rectangle((0, h - band, w, h), fill=(0, 0, 0, 150))
    fs = max(14, int(band * 0.5))
    font = None
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.isfile(f):
            font = ImageFont.truetype(f, fs)
            break
    font = font or ImageFont.load_default()
    text = title[:40]
    while font and hasattr(font, "getlength") and font.getlength(text) > w * 0.9 and fs > 12:
        fs -= 2
        font = ImageFont.truetype(font.path, fs) if hasattr(font, "path") else font
    d.text((int(w * 0.05), h - band + (band - fs) // 2), text, fill=(255, 255, 255), font=font)
    buf = io.BytesIO()
    canvas.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def store_kit(tenant: str, ref: str, regen: bool = False) -> dict[str, Any]:
    """Store texts (checked against each store's limits), the store images in exact sizes, the AI disclosure, the age
    rating draft and the Steam upload scripts - one ZIP she downloads; nothing is published."""
    from .. import usage
    r = _studio(tenant, ref)
    facts = _facts(tenant, r)
    kdir = _rdir(tenant, r.id, "kit")
    cache = kdir / "kit.json"
    notes: list[str] = []
    if cache.is_file() and not regen:
        kit = json.loads(cache.read_text())
    else:
        try:
            with usage.scope(tenant, "game"):
                raw = G.ai.ask(KIT, json.dumps(facts, ensure_ascii=False), max_tokens=3000)
            m = re.search(r"\{.*\}", raw or "", re.S)
            kit = json.loads(m.group(0)) if m else {}
        except Exception:                               # noqa: BLE001
            kit = {}
        if not kit:
            notes.append("written from the design (the model was not available)")
            pitch = re.search(r"\*\*Pitch:\*\*\s*(.+)", facts["design"])
            line = (pitch.group(1).strip() if pitch else r.goal or r.title)[:250]
            kit = {"itch": {"title": r.title, "tagline": line[:80], "description": line, "tags": ["casual", "arcade"]},
                   "steam": {"short": line[:300], "about": line, "tags": ["Casual", "Arcade"]},
                   "play": {"title": r.title[:30], "short": line[:80], "full": line}}
    kit = _clip_text(kit, notes)
    kit["ai_disclosure"] = _ai_disclosure(tenant, r.id)
    kit["rating"] = rating_draft(tenant, r.id)
    kit["notes"] = notes + ["macOS build is not notarised: say 'right-click > Open the first time' on the page",
                            "Windows build is not code-signed: Windows SmartScreen may warn"]
    kdir.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({k: kit[k] for k in ("itch", "steam", "play")}, ensure_ascii=False))
    pal: list[str] = []
    try:
        from . import bible as B
        pal = (B.view(tenant, r.id)["data"].get("style") or {}).get("palette") or []
    except Exception:                                   # noqa: BLE001
        pass
    g = G._get(tenant, r.game_id)
    good = G._good(g)
    shot = None
    if good:
        for name in reversed(good[-1].get("shots") or []):
            p = G._vdir(g, good[-1]["n"]) / "shots" / name
            if p.is_file():
                shot = p.read_bytes()
                break
    gold = G.root() / (re.sub(r"[^\w-]", "_", tenant)[:64] or "t") / "qa" / r.id / "golden"
    golden = sorted(gold.glob("*.png")) if gold.is_dir() else []
    base = golden[0].read_bytes() if golden else shot
    imgs = {k: _image(base, v, r.title, pal) for k, v in IMAGES.items()}
    kit["images"] = {k: f"{v[0]}x{v[1]}" for k, v in IMAGES.items()}
    zpath = kdir / f"{_slug(r.title)}-store-kit.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("store-text.json", json.dumps({k: kit[k] for k in ("itch", "steam", "play")}, ensure_ascii=False, indent=2))
        z.writestr("ai-disclosure.txt", kit["ai_disclosure"] + "\n")
        z.writestr("age-rating-draft.json", json.dumps(kit["rating"], indent=2))
        for k, b in imgs.items():
            z.writestr(f"images/{k}-{IMAGES[k][0]}x{IMAGES[k][1]}.png", b)
        for name, body in _steam_scripts(r.title).items():
            z.writestr(f"steam/{name}", body)
    kit["zip"] = download_url("kit-" + r.id, "kit")
    return kit


def kit_file(sid: str, exp: int, sig: str) -> Path | None:
    if exp < time.time() or not hmac.compare_digest(_dsig("kit-" + sid, "kit", exp), sig or ""):
        return None
    from . import studio as S
    with session() as s:
        row = s.get(S.GameStudio, sid)
        if row is None:
            return None
        tenant, title = row.tenant_id, row.title
    p = _rdir(tenant, sid, "kit") / f"{_slug(title)}-store-kit.zip"
    return p if p.is_file() else None


def _steam_scripts(title: str) -> dict[str, str]:
    return {"app_build.vdf": '"AppBuild"\n{\n\t"AppID" "YOUR_APP_ID"\n\t"Desc" "' + title.replace('"', "'")[:60] +
            ' (Hoola)"\n\t"ContentRoot" "../content/"\n\t"BuildOutput" "../output/"\n\t"Depots"\n\t{\n'
            '\t\t"YOUR_WINDOWS_DEPOT_ID" "depot_windows.vdf"\n\t\t"YOUR_LINUX_DEPOT_ID" "depot_linux.vdf"\n\t}\n}\n',
            "depot_windows.vdf": '"DepotBuild"\n{\n\t"DepotID" "YOUR_WINDOWS_DEPOT_ID"\n\t"FileMapping"\n\t{\n'
            '\t\t"LocalPath" "windows/*"\n\t\t"DepotPath" "."\n\t\t"Recursive" "1"\n\t}\n}\n',
            "depot_linux.vdf": '"DepotBuild"\n{\n\t"DepotID" "YOUR_LINUX_DEPOT_ID"\n\t"FileMapping"\n\t{\n'
            '\t\t"LocalPath" "linux/*"\n\t\t"DepotPath" "."\n\t\t"Recursive" "1"\n\t}\n}\n',
            "README.txt": "Steam upload (you run this; Hoola never logs into your Steam account):\n"
            "1. In Steamworks, create the app and two depots (Windows, Linux); put their IDs into the .vdf files.\n"
            "2. Unzip the Windows build into content/windows/ and the Linux build into content/linux/.\n"
            "3. With Valve's SteamCMD: steamcmd +login <your account> +run_app_build ../scripts/app_build.vdf +quit\n"
            "4. Fill the store page with store-text.json, the images/ and ai-disclosure.txt (Steam's AI content survey).\n"}


# ---------------------------------------------------------------- age rating draft (code)
def rating_draft(tenant: str, sid: str) -> dict[str, Any]:
    """IARC-style answers from what Hoola knows for sure. A draft she checks - the real rating comes from IARC."""
    text = ""
    behaviours: set[str] = set()
    enemies = 0
    try:
        from . import bible as B
        d = B.view(tenant, sid)["data"]
        ents = (d.get("entities") or {})
        enemies = len(ents.get("enemy") or [])
        behaviours = {e.get("behaviour") for e in ents.get("enemy") or []}
        # only the words she / the model wrote - never the Bible's own field names ('enemy', 'damage' are in every Bible)
        text = " ".join(str(e.get(f) or "") for k in ("enemy", "item", "character", "level", "quest")
                        for e in ents.get(k) or [] for f in ("name", "notes", "bio", "text")).lower()
        text += " " + json.dumps(d.get("meta") or {}).lower()
    except Exception:                                   # noqa: BLE001
        pass
    r = _studio(tenant, sid)
    g = G._get(tenant, r.game_id)
    text += " " + (g.design or "").lower()
    fight = (enemies > 0 and bool(behaviours & {"shoot", "chase", "dash"})) or \
        bool(re.search(r"\b(shoot|shooter|attack|fight|enemy|enemies|battle|combat|weapon)\b", text))
    scary = bool(re.search(r"\b(horror|ghost|zombie|scary|monster|dark)\b", text))
    answers = {
        "violence": "fantasy / cartoon (abstract shapes hit or avoid each other, no blood)" if fight else "none",
        "blood_or_gore": "no",
        "fear": "mild (spooky theme)" if scary else "no",
        "sexual_content": "no", "nudity": "no", "crude_humour": "no",
        "strong_language": "no (no swearing in Hoola games; check any text you added)",
        "drugs_alcohol_tobacco": "no",
        "gambling": "no - Hoola refuses real-money, betting and loot-box mechanics",
        "in_app_purchases": "no (coins are earned in the game; there is nothing to buy with real money)",
        "users_interact_or_chat": "no (the game never uses the network)",
        "shares_location": "no", "personal_data": "no (only the best score, saved on the device)",
        "ads": "no",
    }
    expect = {"ESRB": "E (Everyone)" + (" - possibly E10+ for fantasy violence" if fight else ""),
              "PEGI": "7" if (fight or scary) else "3", "IARC_generic": "7+" if (fight or scary) else "3+"}
    return {"answers": answers, "expected": expect,
            "note": "A draft from the Game Bible and Hoola's own rules. Answer the real IARC questionnaire yourself (free, "
                    "inside Google Play Console / other stores); the rating it gives is the real one."}


# ---------------------------------------------------------------- itch.io (her key, her tap)
def _itch_key(tenant: str) -> str:
    try:
        from ..site.dns import key
        return key(tenant, "itch")[0]
    except Exception:                                   # noqa: BLE001
        return ""


def itch_card(tenant: str, ref: str, rid: str, target: str) -> dict[str, Any]:
    """A card: which files go to which itch.io page and channel. Nothing runs until her tap (`itch_push`)."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,60}/[A-Za-z0-9_-]{1,80}", target or ""):
        raise PlatformError("Write the itch.io page: your-name/game-name (such as meghana/rickshaw-racer).")
    if not _itch_key(tenant):
        raise PlatformError("First enter your itch.io API key in the app (Settings > itch.io); never in chat.")
    r = _studio(tenant, ref)
    with session() as s:
        rel = s.get(GameRelease, rid)
        if rel is None or rel.studio_id != r.id:
            raise PlatformError("This release was not found.")
        files = {p: v["file"] for p, v in (rel.platforms or {}).items() if v.get("status") == "done" and p != "android"}
        if not files:
            raise PlatformError("No desktop file was built for itch.io in this release.")
        h = hashlib.sha256(json.dumps([rid, target, sorted(files.items())]).encode()).hexdigest()[:24]
        rel.itch = {"card": {"target": target, "files": files, "hash": h, "at": now().isoformat()}, "pushed": (rel.itch or {}).get("pushed", [])}
        s.flush()
        card = {"release": rel.number, "target": target, "channels": {p: f"{target}:{p}" for p in files}, "hash": h,
                "say": f"{r.title} {rel.version_name}: put it on itch.io '{target}' ({', '.join(files)})? "
                       "Your approval is needed; whether the page is public is your setting on itch.io."}
    from ..seo.service import _publish
    _publish(tenant, "game_release", {"kind": "itch", **card}, r.conversation_id)
    return card


BUTLER = "https://broth.itch.zone/butler/linux-amd64/LATEST/archive/default"


def _butler() -> str:
    """itch.io's own upload tool (official, broth.itch.zone), kept in ~/apps/butler."""
    b = Path.home() / "apps" / "butler" / "butler"
    if b.is_file():
        return str(b)
    if shutil.which("butler"):
        return shutil.which("butler")
    import urllib.request
    b.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(BUTLER, timeout=120) as resp, zipfile.ZipFile(io.BytesIO(resp.read())) as z:
        z.extractall(b.parent)
    b.chmod(0o755)
    return str(b)


def itch_push(tenant: str, ref: str, rid: str, hash_: str) -> dict[str, Any]:
    """ONLY HER TAP (API): butler push each file to its channel, with the release's version name."""
    r = _studio(tenant, ref)
    with session() as s:
        rel = s.get(GameRelease, rid)
        if rel is None or rel.studio_id != r.id:
            raise PlatformError("This release was not found.")
        card = (rel.itch or {}).get("card") or {}
        if not card or card.get("hash") != hash_:
            raise PlatformError("The card has changed; ask for a new card.")
        s.expunge(rel)
    keyv = _itch_key(tenant)
    if not keyv:
        raise PlatformError("itch.io key not found.")
    butler = _butler()
    done = []
    for p, f in card["files"].items():
        path = _rdir(tenant, r.id, rid) / f
        env = {"PATH": "/usr/bin:/bin", "HOME": str(Path.home()), "BUTLER_API_KEY": keyv}
        out = subprocess.run([butler, "push", str(path), f"{card['target']}:{p}", "--userversion", rel.version_name],
                             capture_output=True, text=True, timeout=900, env=env)
        done.append({"platform": p, "ok": out.returncode == 0, "log": (out.stdout + out.stderr)[-400:].replace(keyv, "***")})
    with session() as s:
        row = s.get(GameRelease, rid)
        row.itch = {**(row.itch or {}), "card": {}, "pushed": ((row.itch or {}).get("pushed") or []) + [
            {"at": now().isoformat(), "target": card["target"], "results": done}]}
    from . import studio as S
    S._decide(r, f"itch.io: {rel.number} -> {card['target']}", ", ".join(f"{d['platform']} {'ok' if d['ok'] else 'failed'}" for d in done), by="her")
    return {"ok": all(d["ok"] for d in done), "results": done, "url": f"https://{card['target'].split('/')[0]}.itch.io/{card['target'].split('/')[1]}"}


def set_itch_key(tenant: str, raw: str) -> dict[str, Any]:
    """Her itch.io API key (from itch.io > Settings > API keys), typed in the APP only; sealed like her other keys."""
    raw = (raw or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9]{20,80}", raw):
        raise PlatformError("This does not look like an itch.io API key.")
    from ..bazar.security import vault
    from ..site.hosting_models import SiteHostingKey
    with session() as s:
        for k in s.scalars(select(SiteHostingKey).where(SiteHostingKey.tenant_id == tenant, SiteHostingKey.provider == "itch")).all():
            s.delete(k)
        s.add(SiteHostingKey(tenant_id=tenant, provider="itch", sealed=vault().seal(raw), label=f"key ...{raw[-4:]}", verified=False))
    return {"ok": True, "label": f"key ...{raw[-4:]}", "say": "itch.io key sealed. It is never shown again."}
