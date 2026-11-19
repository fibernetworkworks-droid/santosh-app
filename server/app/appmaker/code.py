"""v0.342 APNA CODE (App Sahayak Phase 9, owner: "START PHASE 9"): her app's whole source in HER OWN GitHub, one commit
per build - the open promise of the original Phase 4 ("each app's code is kept with its full history and can be exported to
her GitHub").

Same rules and same card as the website export (site/github.py, v0.124): her own fine-grained GitHub token typed only in
the app; a card with the repo, private / public, the build and the file count; ONLY her tap pushes (POST
/api/sites-github/<id>/push with the card's hash). Each export is a NEW commit on top of the repo's branch, so her repo
carries the app's history build by build, the commit message = that build's "what's new".

Repo layout: android/ (Android Studio project: Kotlin + Jetpack Compose, the HoolaKit, Gradle wrapper), ios/ (the XcodeGen
project: SwiftUI kit + screens, `xcodegen generate` then open in Xcode) when an iPhone build exists, README.md (how to open,
build and sign; where the app's backend lives), CHANGELOG.md (every build). Never in the repo: the preview signing key
and its password, the Play upload key, App Store Connect keys, build output, caches."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any

from ..db import now, session
from . import service as AS
from .models import AppProject

log = logging.getLogger("santosh.appmaker")
SKIP_PARTS = {"keys", "build", ".gradle", "dd", "ddr", "DerivedData", ".idea", "qa", "__pycache__", ".tmp"}
SKIP_NAMES = {"local.properties", "asc_result.json", "build.log", "release.log", "upload.log"}


class CodeError(AS.AppError):
    pass


def _load(tenant: str, ref: str) -> AppProject:
    with session() as s:
        r = AS._find(s, tenant, ref)
        s.expunge(r)
    return r


def _clean(rel: str, data: bytes) -> bytes:
    """No secret ever leaves: the preview key's password in the Gradle file is blanked (her developer sets her own)."""
    if rel.endswith("app/build.gradle.kts"):
        data = re.sub(rb'\?: "[A-Za-z0-9]*"', b'?: ""', data)
    return data


def _copy(src: Path, dest: Path) -> int:
    n = 0
    for p in sorted(src.rglob("*")):
        rel = p.relative_to(src)
        if not p.is_file() or set(rel.parts) & SKIP_PARTS or p.name in SKIP_NAMES or p.suffix in (".p12", ".jks", ".p8", ".keystore"):
            continue
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(_clean(rel.as_posix(), p.read_bytes()))
        if p.name == "gradlew":
            out.chmod(0o755)
        n += 1
    return n


def _readme(r: AppProject, an: dict[str, Any], io: dict[str, Any], has_ios: bool) -> str:
    base = (AS._settings().public_base_url or "").rstrip("/")
    apk = an.get("apk") or {}
    tf = io.get("testflight") or {}
    lines = [f"# {r.name or 'App'}", "", f"Made with Hoola App Assistant (Newtika). Design version {r.version}, build {an.get('build') or 0}"
             + (f" (Android {apk.get('version_name')})" if apk.get("version_name") else "")
             + (f", iPhone {tf.get('version')} ({tf.get('build')})" if tf.get("build") else "") + ".", "",
             "## What is here", "",
             "- `android/` - the Android app: Kotlin + Jetpack Compose. Open the folder in Android Studio, or build with "
             "`./gradlew assembleRelease` (JDK 17, Android SDK 37). Signing: set your own keystore in `app/build.gradle.kts` "
             "(Hoola's preview key is never in this repo)."]
    if has_ios:
        lines.append("- `ios/` - the iPhone app: Swift + SwiftUI (iOS 16+). Install XcodeGen (`brew install xcodegen`), run "
                     "`xcodegen generate` inside `ios/`, open the `.xcodeproj` in Xcode, pick your team and run.")
    lines += ["- `CHANGELOG.md` - every build Hoola made, newest first.", "",
              "## The app's server", "",
              "Accounts, orders, bookings and staff lists live on the business's Hoola server "
              f"({base or 'the Hoola server'}), under `/api/app-api/<app key>/...` (the key is in "
              "`android/app/src/main/java/hoola/app/MainActivity.kt` / `ios/Sources/App/AppTokens.swift`). The apps work only "
              "through that API; the data stays with the business.", "",
              "## Rules this code keeps", "",
              "- No password / PIN / card fields in any screen; sign-in is the kit's own screen.",
              "- Payments go to the business's own UPI ID in the customer's UPI app; the app never sees money.",
              "- Photos through the system photo picker, location only while the app is open, scanning through Google's / "
              "Apple's own scanner.", ""]
    return "\n".join(lines)


def _changelog(an: dict[str, Any], io: dict[str, Any]) -> str:
    out = ["# Changelog", ""]
    for e in reversed(an.get("history") or []):
        notes = e.get("notes") or []
        out.append(f"## Android build {e.get('build')} - {e.get('version_name') or ''} ({str(e.get('at') or '')[:10]})")
        out += [f"- {n}" for n in notes] + [""]
    for e in reversed(io.get("history") or []):
        out.append(f"## iPhone build {e.get('build')} - {e.get('version') or ''} ({str(e.get('at') or '')[:10]})"
                   + (" - TestFlight" if e.get("testflight") else ""))
        ch = [str(x).replace("_", " ") for x in e.get("written") or []]
        out += [f"- Updated: {', '.join(ch[:6])}." if ch else "- Improvements and fixes.", ""]
    return "\n".join(out)


def stage(r: AppProject) -> tuple[Path, int, str]:
    """The repo's content for this app now (android/ + ios/ + README + CHANGELOG) -> (folder, files, fingerprint)."""
    from .android import service as AN
    an = AN.state(r)
    io = an.get("ios") or {}
    src_a = AN._dir(r) / "project"
    if not (src_a / "settings.gradle.kts").exists():
        raise CodeError("Let the Android app be built first ('build the Android app'): the code comes from that build.")
    dest = AN._dir(r).parent / "github"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    n = _copy(src_a, dest / "android")
    src_i = AN._dir(r).parent / "ios" / "project"
    has_ios = (src_i / "project.yml").exists()
    if has_ios:
        n += _copy(src_i, dest / "ios")
    (dest / "README.md").write_text(_readme(r, an, io, has_ios))
    (dest / "CHANGELOG.md").write_text(_changelog(an, io))
    (dest / ".gitignore").write_text("build/\n.gradle/\nlocal.properties\nkeys/\n*.p12\n*.jks\n*.p8\nios/*.xcodeproj/\nios/dd/\nDerivedData/\n")
    n += 3
    h = hashlib.sha256()
    for p in sorted(dest.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(dest).as_posix().encode())
            h.update(hashlib.sha256(p.read_bytes()).digest())
    return dest, n, h.hexdigest()[:24]


def repo_name(r: AppProject) -> str:
    from ..site.hosting import slug_for
    return (slug_for(r.name or r.number or "app") + "-app")[:90]


def _message(r: AppProject) -> str:
    from .android import service as AN
    an = AN.state(r)
    hist = an.get("history") or []
    e = hist[-1] if hist else {}
    head = f"Hoola app build {an.get('build') or 0}" + (f" ({e.get('version_name')})" if e.get("version_name") else "")
    tf = (an.get("ios") or {}).get("testflight") or {}
    if tf.get("build"):
        head += f" + iPhone {tf.get('version')} ({tf.get('build')})"
    return head + "\n\n" + "\n".join(f"- {x}" for x in (e.get("notes") or ["Improvements and fixes."]))


def request(tenant: str, ref: str, repo: str = "", private: bool = True, conv: str = "") -> dict[str, Any]:
    """Her ask (tool or app button) -> the GitHub card; nothing is sent until she taps it."""
    from ..site import github as GH
    from .android import service as AN
    r = _load(tenant, ref)
    _folder, n, fp = stage(r)
    size = sum(p.stat().st_size for p in _folder.rglob("*") if p.is_file())
    if n > GH.MAX_FILES or size > GH.MAX_BYTES:
        raise CodeError(f"The project is too large ({n} files, {size // 1048576} MB); use the project ZIP.")
    me = GH.Gh(GH._token(tenant)).me()
    name = re.sub(r"[^A-Za-z0-9._-]", "-", (repo or repo_name(r)).strip())[:90].strip("-.") or "hoola-app"
    build = int(AN.state(r).get("build") or 0)
    with session() as s:
        o = GH.SiteGithubExport(tenant_id=tenant, site_id="app:" + r.id, version=build, owner=str(me.get("login") or ""),
                                repo=name, private=bool(private), files=n)
        s.add(o)
        s.flush()
        o.hash = GH._hash(o, fp)
        s.flush()
        s.expunge(o)
    has_ios = (_folder / "ios").exists()
    card = {"kind": "github", "id": o.id, "app": {"id": r.id, "number": r.number, "name": r.name}, "repo": f"{o.owner}/{o.repo}",
            "private": o.private, "version": build, "files": n, "size_kb": size // 1024, "hash": o.hash,
            "say": (f"Put the code of {r.name} (Android{' + iPhone' if has_ios else ''}, build {build}, {n} files) in your GitHub "
                    f"'{o.owner}/{o.repo}'? "
                    + ("Private: only you can see it." if o.private else "PUBLIC: anyone can see it.")
                    + " Signing keys are never included. Your approval is needed."), "push": True}
    AS._publish(tenant, "site_github", card, conv or r.conv)
    return card


def push(tenant: str, o: Any, hash_: str) -> dict[str, Any]:
    """ONLY her tap (called by site.github.push for an app export): one new commit on top of the branch."""
    from ..site import github as GH
    r = _load(tenant, o.site_id[4:])
    folder, _n, fp = stage(r)
    if hash_ != GH._hash(o, fp):
        raise GH.GithubError("A new build of the app has arrived; ask for a new card ('put the code in GitHub').")
    gh = GH.Gh(GH._token(tenant))
    GH._set(o.id, status="pushing")
    try:
        repo = gh.req("GET", f"/repos/{o.owner}/{o.repo}", ok404=True)
        if repo is None:
            repo = gh.req("POST", "/user/repos", {"name": o.repo, "private": o.private, "auto_init": True,
                                                   "description": f"{r.name} - app made with Hoola"})
        branch = repo.get("default_branch") or "main"
        ref = gh.req("GET", f"/repos/{o.owner}/{o.repo}/git/ref/heads/{branch}", ok404=True)
        parent = ((ref or {}).get("object") or {}).get("sha")
        import base64
        tree = []
        for p in sorted(x for x in folder.rglob("*") if x.is_file()):
            rel = p.relative_to(folder).as_posix()
            blob = gh.req("POST", f"/repos/{o.owner}/{o.repo}/git/blobs",
                          {"content": base64.b64encode(p.read_bytes()).decode(), "encoding": "base64"})
            tree.append({"path": rel, "mode": "100755" if rel.endswith(("gradlew", ".sh")) else "100644", "type": "blob", "sha": blob["sha"]})
        # a full tree (no base_tree): files a newer build removed are removed in the repo too
        t = gh.req("POST", f"/repos/{o.owner}/{o.repo}/git/trees", {"tree": tree})
        c = gh.req("POST", f"/repos/{o.owner}/{o.repo}/git/commits",
                   {"message": _message(r), "tree": t["sha"], "parents": [parent] if parent else []})
        if ref:
            gh.req("PATCH", f"/repos/{o.owner}/{o.repo}/git/refs/heads/{branch}", {"sha": c["sha"], "force": False})
        else:
            gh.req("POST", f"/repos/{o.owner}/{o.repo}/git/refs", {"ref": f"refs/heads/{branch}", "sha": c["sha"]})
    except GH.GithubError as e:
        GH._set(o.id, status="failed", error=str(e))
        raise
    url = f"https://github.com/{o.owner}/{o.repo}"
    GH._set(o.id, status="done", url=url)
    from .android import service as AN
    exp = list(AN.state(AS._load(r.id)).get("github") or [])
    exp.append({"build": o.version, "repo": f"{o.owner}/{o.repo}", "commit": c["sha"], "at": now().isoformat(), "private": o.private})
    AN._put(r.id, github=exp[-20:])
    say = f"The code of {r.name} is now in GitHub (build {o.version}): {url}"
    AS._publish(tenant, "site_github", {"kind": "github_done", "id": o.id, "url": url, "say": say, "push": False}, r.conv)
    return {"ok": True, "url": url, "commit": c["sha"], "say": say}


def view(tenant: str, ref: str) -> dict[str, Any]:
    from ..site import github as GH
    from ..site import dns as D
    from .android import service as AN
    r = _load(tenant, ref)
    linked = False
    try:
        linked = bool(D.key(tenant, "github")[0])
    except Exception:                                   # noqa: BLE001
        linked = False
    return {"linked": linked, "repo": repo_name(r), "exports": GH.exports(tenant, "app:" + r.id),
            "commits": list(reversed(AN.state(r).get("github") or [])),
            "ready": (AN._dir(r) / "project" / "settings.gradle.kts").exists()}
