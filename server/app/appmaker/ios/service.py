"""v0.332 IPHONE (App Phase 6): from her approved design to a real iPhone app - the same design, the same backend, the same
data as her Android app.

Flow (`build`, ONLY on her approved design, like Android): every screen is written in Swift + SwiftUI by Opus from its
approved web design (cached per screen like v0.325: an update rewrites only changed screens), checked against the house
rules -> the fixed Xcode project is generated (HoolaKit in Swift, the app's own backend + offline outbox, accounts, forms,
photos, location, UPI claim, privacy + in-app account deletion) -> compiled on a Mac (her private GitHub builds repo,
workflow hoola-ios.yml, macOS runner; Hoola's server never compiles) -> compile errors go back to Opus per screen (max
APP_BUILD_ROUNDS, stops when the same errors come back) -> a screen that still fails gets its code-made version -> every
screen opened in an iPhone simulator (crash = one Opus fix with the real crash, then the code-made version) -> with
kind 'testflight' the SAME build is archived, signed by Apple's cloud signing and uploaded to TestFlight with HER App
Store Connect key, which lives only as a secret in her builds repo. App Store review / release stays her tap in App Store
Connect (Hoola never submits for review)."""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import secrets
import threading
import time
import zipfile
from datetime import timedelta
from pathlib import Path
from typing import Any

from ...db import now, session
from .. import service as AS
from ..models import AppProject
from ..android import runners as RN
from ..android import service as AN
from ..android import spec as SP
from . import gen as G
from . import prompts as PR

log = logging.getLogger("santosh.appmaker.ios")
_LOCK = threading.Lock()
_RUNNING: dict[str, threading.Thread] = {}
KIT_REV = "i1"            # bump when the Swift kit's public API changes in a way old screen code may not compile against
LINK_DAYS = 7
KINDS = ("sim", "testflight")


class IosError(AS.AppError):
    pass


# ---------------------------------------------------------------- state (inside the app's build JSON, key "ios")
def state(r: AppProject) -> dict[str, Any]:
    return AN.state(r).get("ios") or {}


def _put(app_id: str, **kw) -> dict[str, Any]:
    st = dict(state(AS._load(app_id)))
    st.update(kw)
    AN._put(app_id, ios=st)
    return st


def _states(app_id: str, upd: dict[str, str], now_line: str = "") -> None:
    st = state(AS._load(app_id))
    ss = dict(st.get("states") or {})
    ss.update(upd)
    kw: dict[str, Any] = {"states": ss}
    if now_line:
        kw["now"] = now_line
    _put(app_id, **kw)


def _dir(r: AppProject) -> Path:
    d = AN._dir(r).parent / "ios"
    d.mkdir(parents=True, exist_ok=True)
    return d


def bundle_id(r: AppProject) -> str:
    """The iPhone bundle ID = her confirmed Play package (one identity for both stores), else the preview id."""
    from ..android import store as ST
    pkg = ST.state(r).get("package") or ""
    if not pkg:
        pkg = f"in.hoola.app.{re.sub(r'[^a-z0-9]', '', (r.id or 'app').lower())[:24] or 'app'}"
    return pkg.replace("_", "-")


def ready() -> dict[str, Any]:
    """Can an iPhone build run? Only on a Mac: the GitHub builds repo (APP_BUILD_MODE=github) with hoola-ios.yml."""
    if RN._override is not None or _override is not None:
        return {"ready": True, "where": "test"}
    s = AN.AS._settings()
    ok = RN.mode() == "github" and bool((s.app_build_gh_repo or "").strip()) and bool(s.app_build_gh_token)
    return {"ready": ok, "where": "github" if ok else "",
            "why": "" if ok else "iPhone apps compile only on a Mac: set up the private GitHub builds repo (APP_BUILD_MODE=github) "
                                 "and copy server/app_builder/hoola-ios.yml into it."}


# ---------------------------------------------------------------- start
def build(tenant: str, ref: str, conv: str = "", kind: str = "sim", only: list[str] | None = None) -> dict[str, Any]:
    """Her tap / words 'iPhone app banao' (kind sim) or 'TestFlight par bhejo' (kind testflight) on an approved design."""
    if kind not in KINDS:
        raise IosError("kind: sim ya testflight")
    with session() as s:
        r = AS._find(s, tenant, ref)
        s.expunge(r)
    if r.status != "approved" or not r.approved_hash:
        raise IosError("Pehle design pakka kijiye ('Design pakka' button): iPhone app bhi usi design se banti hai.")
    from .. import kit as K
    h = K.design_hash(AS._screens(r), AS._ctx(r))
    if h != r.approved_hash:
        raise IosError("Design pakka hone ke baad badla hai; naya design dekh kar dobara pakka kijiye.")
    st = state(r)
    if st.get("status") in ("writing", "building", "fixing", "uploading"):
        with _LOCK:
            t = _RUNNING.get(r.id)
        if t is not None and t.is_alive():
            return view(r)
    n = int(st.get("build") or 0) + 1
    _put(r.id, status="writing", kind=kind, build=n, design_version=r.version, error="", note="", rounds=0,
         started=now().isoformat(), ended="", now="Screens SwiftUI mein likh raha hoon", states={}, conv=conv or r.conv,
         redo=list(only or []))
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
    th = threading.Thread(target=go, name=f"ios-{app_id}", daemon=True)
    with _LOCK:
        _RUNNING[app_id] = th
    th.start()


def _emit(app_id: str, push: bool = False) -> None:
    r = AS._load(app_id)
    v = view(r)
    v["push"] = push
    AS._publish(r.tenant_id, "app_ios", v, state(r).get("conv") or r.conv)


# ---------------------------------------------------------------- 1. screens in SwiftUI
def _ask(system: str, prompt: str) -> str:
    from ...site import ai as SA
    return PR.code_of(SA.ask(system, prompt, 9000, "app_code"))


def _skey(sid: str, ctx: dict[str, Any], sp: dict[str, Any], screens: dict[str, dict[str, Any]]) -> str:
    return hashlib.sha256((AN._skey(sid, ctx, sp, screens) + KIT_REV).encode()).hexdigest()[:16]


def _all_ids(sp: dict[str, Any]) -> list[str]:
    return [s["id"] for s in sp["screens"]] + list(G.CODE_SCREENS) + list(G.KIT_SCREENS)


def write_screen(r: AppProject, sid: str, ctx: dict[str, Any], sp: dict[str, Any], scr: dict[str, Any]) -> tuple[str, list[str]]:
    ids = _all_ids(sp)
    me = next(s for s in sp["screens"] if s["id"] == sid)
    system = PR.screen_system(sid, ids=ids, lists=SP.list_fields(sp["seed"]),
                              facts=sorted(k for k in sp["seed"]["facts"] if k != "privacy"), lang=AS._lang_line(r.language),
                              backend=sp["seed"].get("backend"))
    prompt = (f"APP: {sp['app']['name']} ({ctx.get('goal')}).\nSCREEN: {sid} = {me['label']}"
              f"{' (a bottom tab)' if me['tab'] else ' (opened on top of a tab; Back is automatic)'}.\nPURPOSE: {me['purpose']}\n"
              f"DATA SHOWN: {', '.join(me['data'])}\n"
              f"ACTIONS (label -> screen): {'; '.join(a['label'] + ' -> ' + a['go'] for a in me['actions'])}\n"
              f"COMPONENTS IN THE DESIGN: {', '.join(me['components'])}\n{AN._dna_lines(ctx, sid, {'scenes': {}})}\n"
              f"APPROVED WEB DESIGN OF THIS SCREEN (HTML; match it):\n{AN._design_html(scr)}")
    src = _ask(system, prompt)
    probs = G.scan_screen(src, sid, ids)
    if probs:
        src2 = _ask(PR.fix_system(sid, ids), "HOUSE-RULE PROBLEMS:\n- " + "\n- ".join(probs) + "\n\nFILE:\n```swift\n" + src + "```")
        p2 = G.scan_screen(src2, sid, ids)
        if len(p2) < len(probs) or not p2:
            src, probs = src2, p2
    return src, probs


# ---------------------------------------------------------------- 2. the Mac build (her GitHub builds repo)
_override = None


def set_runner(fn) -> None:
    """Tests: a fake Mac. fn(src, key, kind) -> {ok, log, report, shots, uploaded, upload_log}."""
    global _override
    _override = fn


def _mac(src: Path, key: str, kind: str, progress) -> dict[str, Any]:
    if _override is not None:
        return _override(src, key, kind)
    s = AN.AS._settings()
    t0 = time.time()
    repo, branch, sha = RN.push_tree(src, f"{key}-ios", progress, prefix="ios")
    job = hashlib.sha256(f"{key}{sha}{time.time()}".encode()).hexdigest()[:16]
    run = RN.dispatch_wait(repo, branch, sha, "hoola-ios.yml", {"job": job, "kind": kind}, progress, t0,
                           max(int(s.app_build_timeout_s or 1800), 2400))
    if not run:
        return {"ok": False, "log": "iPhone build timed out", "seconds": round(time.time() - t0)}
    text, up, report, shots = "", "", None, {}
    for zb in RN.artifacts(repo, run, (f"hoola-{job}",)):
        with zipfile.ZipFile(io.BytesIO(zb)) as z:
            for nm in z.namelist():
                if nm.endswith("build.log"):
                    text = z.read(nm).decode(errors="replace")
                elif nm.endswith("upload.log"):
                    up = z.read(nm).decode(errors="replace")
        qa = RN.qa_from_zip(zb)
        if qa:
            report, shots = qa["report"], qa["shots"]
    built = run.get("conclusion") == "success" or ("error:" not in text and bool(report))
    return {"ok": built and "error:" not in text, "log": text or f"GitHub run {run.get('conclusion')}", "report": report,
            "shots": shots, "uploaded": "UPLOADED_TO_TESTFLIGHT" in up, "upload_log": up[-4000:],
            "seconds": round(time.time() - t0)}


def _crashed(report: dict[str, Any] | None, ids: list[str]) -> dict[str, str]:
    return {sid: str(x.get("excerpt") or "the app closed on this screen") for sid, x in ((report or {}).get("screens") or {}).items()
            if sid in ids and isinstance(x, dict) and x.get("crashed")}


def run(app_id: str) -> None:
    r = AS._load(app_id)
    try:
        _run(r)
    except Exception as e:                           # noqa: BLE001
        log.exception("ios build %s", app_id)
        _put(app_id, status="failed", error=AS._tidy(str(e), 300), ended=now().isoformat(), now="")
        _emit(app_id, push=True)


def _run(r: AppProject) -> None:
    st = state(r)
    ast = AN.state(r)
    n = int(st.get("build") or 1)
    kind = st.get("kind") or "sim"
    ctx = AS._ctx(r)
    screens = AS._screens(r)
    work = _dir(r)
    base = (AS._settings().public_base_url or "").rstrip("/")
    # the iPhone build number only goes up (TestFlight refuses a build number it has seen)
    bn = max(int(st.get("last_bn") or 0) + 1, r.version * 100 + (n % 100))
    sp = SP.build(r, ctx["plan"], ctx["tokens"], ctx["facts"], screens, work, version_code=bn, base_url=base,
                  app_key=AN._app_key(r))
    from .. import backend as BE
    sp["seed"]["backend"] = BE.seed_hint(r)          # the SAME backend as the Android app: one set of accounts and orders
    bid = bundle_id(r)
    sp["ios"] = {"bundle_id": bid, "version": f"{r.version}.{int(ast.get('build') or 0) or n}", "build": bn}
    try:
        sp["ios"]["icon_png_b64"] = _icon_b64(sp)
    except Exception:                                # noqa: BLE001  no resvg: the code-drawn icon
        log.debug("icon", exc_info=True)
    ids = [s["id"] for s in sp["screens"]]
    cache = work / "screens"
    cache.mkdir(exist_ok=True)
    redo = set(st.get("redo") or [])
    swift: dict[str, str] = {}
    code_only: set[str] = set()
    written: list[str] = []
    _put(r.id, states={sid: "writing" for sid in ids}, total=len(ids), bundle_id=bid)
    _emit(r.id)
    for i, sid in enumerate(ids):
        if AS._load(r.id).stop:
            raise IosError("rok diya")
        if sid in G.AUTH_IDS:
            _states(r.id, {sid: "written"})
            continue
        f = cache / f"{_skey(sid, ctx, sp, screens)}-{sid}.swift"
        if f.exists() and sid not in redo:
            swift[sid] = f.read_text()
            _states(r.id, {sid: "written"})
            continue
        _states(r.id, {sid: "writing"}, f"SwiftUI: {next(s['label'] for s in sp['screens'] if s['id'] == sid)} ({i + 1}/{len(ids)})")
        _emit(r.id)
        try:
            src, probs = write_screen(r, sid, ctx, sp, screens.get(sid) or {})
        except Exception as e:                       # noqa: BLE001
            from ...site import ai as SA
            if isinstance(e, SA.AiError):
                raise IosError(str(e)) from e
            log.info("ios screen %s not written: %s", sid, e)
            src, probs = "", ["not written"]
        if probs:
            code_only.add(sid)
            _states(r.id, {sid: "code"})
        else:
            swift[sid] = src
            f.write_text(src)
            written.append(sid)
            _states(r.id, {sid: "written"})
    src_dir = work / "project"
    sp["screens_swift"] = swift
    G.write_project(sp, src_dir)
    _zip(r, n, src_dir)
    rd = ready()
    if not rd["ready"]:
        _put(r.id, status="zip", ended=now().isoformat(), now="", note=rd["why"])
        AN._note(r, "iPhone app ka Xcode project taiyaar (ZIP). iPhone app sirf Mac par compile hoti hai: GitHub builds repo mein "
                    "hoola-ios.yml lagate hi 'iPhone app banao' dobara kahiye.")
        _emit(r.id, push=True)
        return
    key = r.id.replace("_", "-")[:60].lower()
    rounds = max(1, int(AS._settings().app_build_rounds or 4))
    seen: dict[str, set[str]] = {}
    res: dict[str, Any] = {}
    all_ids = _all_ids(sp)
    for rnd in range(rounds + 1):
        _put(r.id, status="building" if rnd == 0 else "fixing", rounds=rnd,
             now="Mac par Xcode se compile + iPhone simulator check" if rnd == 0 else f"Compile ki galtiyan theek: round {rnd}")
        _states(r.id, {sid: "compiling" for sid in swift})
        _emit(r.id)
        res = _mac(src_dir, key, "sim", lambda stage: _put(r.id, stage=stage))
        _put(r.id, seconds=res.get("seconds"))
        if res.get("ok"):
            break
        errs = G.screen_errors(res.get("log") or "")
        bad = {sid: el for cls, el in errs.items() for sid in ids if G.swift_name(sid) == cls}
        if not bad:
            other = [ln.strip() for ln in (res.get("log") or "").splitlines() if "error:" in ln][:3]
            raise IosError("iPhone build nahi hua: " + ("; ".join(other) or AS._tidy(res.get("log") or "", 200)))
        last = rnd == rounds
        for sid, el in bad.items():
            sig = hashlib.sha256("\n".join(re.sub(r"line \d+: ", "", e) for e in el).encode()).hexdigest()[:12]
            again = sig in seen.setdefault(sid, set())
            seen[sid].add(sig)
            if last or again or sid not in swift:
                swift.pop(sid, None)
                code_only.add(sid)
                _states(r.id, {sid: "code"})
                continue
            _states(r.id, {sid: "fixing"}, f"Theek kar raha hoon: {sid}")
            fixed = _fix(sid, all_ids, "COMPILE ERRORS (Xcode):\n- " + "\n- ".join(el), swift[sid])
            if fixed:
                swift[sid] = fixed
                (cache / f"{_skey(sid, ctx, sp, screens)}-{sid}.swift").write_text(fixed)
            else:
                swift.pop(sid, None)
                code_only.add(sid)
                _states(r.id, {sid: "code"})
        sp["screens_swift"] = swift
        G.write_project(sp, src_dir)
    if not res.get("ok"):
        raise IosError("iPhone app compile nahi hui.")
    # HOOLA QA on the simulator: a crashed Opus screen gets one fix with the real crash, then its code-made version
    crashed = {k: v for k, v in _crashed(res.get("report"), ids).items() if k in swift}
    if crashed:
        _put(r.id, status="fixing", now="Simulator check: " + ", ".join(list(crashed)[:4]) + " crash hui - theek kar raha hoon")
        _emit(r.id)
        for sid, crash in crashed.items():
            fixed = _fix(sid, all_ids, "THIS SCREEN CRASHED IN THE iPHONE SIMULATOR. Find the cause and fix it (empty lists, "
                                       "index out of range, force unwraps, missing keys).\nCRASH REPORT:\n" + crash[:3500], swift[sid])
            if fixed:
                swift[sid] = fixed
                (cache / f"{_skey(sid, ctx, sp, screens)}-{sid}.swift").write_text(fixed)
            else:
                swift.pop(sid, None)
                code_only.add(sid)
        sp["screens_swift"] = swift
        G.write_project(sp, src_dir)
        again = _mac(src_dir, key, "sim", lambda stage: _put(r.id, stage=stage))
        still = {k for k in _crashed(again.get("report"), ids) if k in swift} if again.get("ok") else set(crashed)
        if still:
            for sid in still:
                swift.pop(sid, None)
                code_only.add(sid)
            sp["screens_swift"] = swift
            G.write_project(sp, src_dir)
            again = _mac(src_dir, key, "sim", lambda stage: _put(r.id, stage=stage))
        if again.get("ok"):
            res = again
    _keep_qa(r, n, res)
    _zip(r, n, src_dir)
    tf: dict[str, Any] = dict(st.get("testflight") or {})
    if kind == "testflight":
        _put(r.id, status="uploading", now="TestFlight par bhej raha hoon (Apple ka signing + upload)")
        _emit(r.id)
        up = _mac(src_dir, key, "testflight", lambda stage: _put(r.id, stage=stage))
        if not up.get("uploaded"):
            raise IosError(_upload_why(up.get("upload_log") or up.get("log") or ""))
        tf = {"version": sp["ios"]["version"], "build": bn, "at": now().isoformat(), "bundle_id": bid}
    _states(r.id, {sid: ("code" if sid in code_only else "done") for sid in ids})
    hist = list(st.get("history") or [])
    hist.append({"build": n, "kind": kind, "version": sp["ios"]["version"], "build_number": bn, "at": now().isoformat(),
                 "written": written, "code": sorted(code_only), "testflight": kind == "testflight"})
    _put(r.id, status="ready", ended=now().isoformat(), now="", error="", last_bn=bn, testflight=tf, history=hist[-20:],
         stats={"model": len(swift), "code": len(code_only)}, kinds={sid: ("code" if sid in code_only else "model") for sid in ids})
    msg = (f"iPhone app taiyaar: {r.name or 'App'} (v{sp['ios']['version']}, build {bn}). {len(swift)} screens Opus ne SwiftUI mein "
           f"likhi" + (f", {len(code_only)} saada (code se)" if code_only else "") + "." + qa_line(state(AS._load(r.id)).get("qa")))
    if kind == "testflight":
        msg += (" TestFlight par pahunch gayi: Apple ki processing ke baad (10-30 minute) TestFlight app mein dikhegi. "
                "App Store par bhejna App Store Connect mein aapka tap hai.")
    else:
        msg += " TestFlight par bhejne ke liye 'TestFlight par bhejo' kahiye."
    AN._note(r, msg)
    _emit(r.id, push=True)


def _fix(sid: str, ids: list[str], why: str, src: str) -> str:
    try:
        out = _ask(PR.fix_system(sid, ids), why + "\n\nFILE:\n```swift\n" + src + "```")
    except Exception as e:                           # noqa: BLE001
        from ...site import ai as SA
        if isinstance(e, SA.AiError):
            raise IosError(str(e)) from e
        return ""
    return out if out and not G.scan_screen(out, sid, ids) else ""


def _upload_why(text: str) -> str:
    """Apple's upload refusal -> what SHE does (the exact step), never a raw log."""
    t = text or ""
    if "MISSING_SECRET" in t:
        miss = re.findall(r"MISSING_SECRET (\w+)", t)
        return ("TestFlight ke liye builds repo mein secret nahi mila: " + ", ".join(miss)
                + ". GitHub > builds repo > Settings > Secrets and variables > Actions mein daaliye (App Store Connect key).")
    if re.search(r"No suitable application records|Could not find .*app|app record", t, re.I):
        return "App Store Connect mein yeh app abhi bani nahi: My Apps > + > New App, bundle ID wahi chuniye jo card par hai."
    if re.search(r"bundle version must be higher|has already been used|CFBundleVersion", t, re.I):
        return "Yeh build number Apple pehle le chuka hai; 'TestFlight par bhejo' dobara kahiye (naya number lagega)."
    if re.search(r"agreement|Program License", t, re.I):
        return "Apple Developer ka naya agreement accept karna baaki hai (developer.apple.com > Account)."
    if re.search(r"authentication|401|Invalid issuer|key", t, re.I):
        return "App Store Connect key kaam nahi kar rahi (ID / Issuer ID / .p8 dobara check kijiye; key ko Admin access chahiye)."
    return "TestFlight upload nahi hua: " + AS._tidy(t[-300:], 300)


def _icon_b64(sp: dict[str, Any]) -> str:
    """The design's own line icon on her primary colour, 1024 px, opaque (App Store), drawn by resvg (same as v0.300 logos)."""
    import base64
    import resvg_py
    tk = sp.get("tokens") or {}
    icons = sp.get("icons") or {}
    glyph = icons.get(sp.get("app_icon") or "store") or icons.get("store") or ["M8 12h8"]
    bg, fg = G._hex(tk.get("primary"), "#3355FF"), G._hex(tk.get("on_primary"), "#FFFFFF")
    paths = "".join(f'<path d="{d}" fill="none" stroke="{fg}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
                    for d in glyph if re.fullmatch(r"[0-9MmLlHhVvCcSsQqTtAaZz .,\-eE]+", d))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 24 24">'
           f'<rect width="24" height="24" fill="{bg}"/><g transform="translate(5.5 5.5) scale(0.54)">{paths}</g></svg>')
    png = resvg_py.svg_to_bytes(svg_string=svg)
    png = bytes(png)
    if png[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("no png")
    return base64.b64encode(png).decode()


def _zip(r: AppProject, n: int, src_dir: Path) -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(src_dir.rglob("*")):
            if p.is_file():
                rel = p.relative_to(src_dir).as_posix()
                info = zipfile.ZipInfo(rel, date_time=(2026, 1, 1, 0, 0, 0))
                info.external_attr = (0o755 if rel.endswith(".sh") else 0o644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, p.read_bytes())
    work = _dir(r)
    name = f"ios-project-b{n}.zip"
    (work / name).write_bytes(buf.getvalue())
    AN._prune(work, "ios-project-b", 5)
    _put(r.id, zip=name, zip_size=len(buf.getvalue()), zip_token=secrets.token_urlsafe(24),
         zip_expires=(now() + timedelta(days=LINK_DAYS)).isoformat())


def _keep_qa(r: AppProject, n: int, res: dict[str, Any]) -> None:
    rep = res.get("report")
    if not isinstance(rep, dict):
        _put(r.id, qa={"ran": False, "why": "no simulator report (use the v0.332 hoola-ios.yml)"})
        return
    d = _dir(r) / "qa" / f"b{n}"
    d.mkdir(parents=True, exist_ok=True)
    for sid, png in (res.get("shots") or {}).items():
        if re.fullmatch(r"[a-z][a-z0-9_]{0,48}", sid) and png[:8] == b"\x89PNG\r\n\x1a\n":
            (d / f"{sid}.png").write_bytes(png)
    import shutil
    for old in sorted((x for x in (_dir(r) / "qa").glob("b*") if x.is_dir()), key=lambda x: x.stat().st_mtime, reverse=True)[3:]:
        shutil.rmtree(old, ignore_errors=True)
    _put(r.id, qa={"ran": True, "build": n, "passed": bool(rep.get("passed")), "opened": rep.get("opened"), "total": rep.get("total"),
                   "crashed": rep.get("crashed") or [], "blank": rep.get("blank") or [], "perf": rep.get("perf") or {},
                   "shots": sorted(p.stem for p in d.glob("*.png")), "at": now().isoformat()})


def qa_line(qa: dict[str, Any] | None) -> str:
    if not qa or not qa.get("ran"):
        return ""
    p = qa.get("perf") or {}
    bits = [f"iPhone simulator check: {qa.get('opened')}/{qa.get('total')} screens bina crash ke khuli"]
    if p.get("launch_ms") is not None:
        bits.append(f"app {p['launch_ms']} ms mein khulti hai")
    if p.get("app_mb") is not None:
        bits.append(f"app {p['app_mb']} MB")
    return " " + ", ".join(bits) + "."


def qa_shot(tenant: str, ref: str, name: str) -> Path:
    with session() as s:
        r = AS._find(s, tenant, ref)
        s.expunge(r)
    qa = state(r).get("qa") or {}
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,48}", name or "") or not qa.get("build"):
        raise IosError("not found")
    f = _dir(r) / "qa" / f"b{qa['build']}" / f"{name}.png"
    if not f.exists():
        raise IosError("not found")
    return f


# ---------------------------------------------------------------- views / files
def view(r: AppProject) -> dict[str, Any]:
    st = state(r)
    plan = AN._j(r.plan, {})
    labels = plan.get("labels") or {}
    ss = st.get("states") or {}
    base = (AS._settings().public_base_url or "").rstrip("/")
    zurl = (f"{base}/api/app-ios-zip/{st['zip_token']}/{st['zip']}" if st.get("zip_token") and st.get("zip")
            and st.get("zip_expires", "") > now().isoformat() else "")
    return {"id": r.id, "number": r.number, "name": r.name, "status": st.get("status") or "", "kind": st.get("kind") or "",
            "build": st.get("build") or 0, "now": st.get("now") or "", "stage": st.get("stage") or "", "error": st.get("error") or "",
            "note": st.get("note") or "", "rounds": st.get("rounds") or 0, "seconds": st.get("seconds"),
            "bundle_id": st.get("bundle_id") or bundle_id(r), "runner": ready(), "approved": bool(r.approved_hash),
            "screens": [{"id": sid, "label": labels.get(sid) or sid, "state": ss.get(sid, "todo")} for sid in plan.get("screens", [])],
            "stats": st.get("stats") or {}, "qa": st.get("qa") or {}, "testflight": st.get("testflight") or {},
            "history": list(reversed((st.get("history") or [])[-12:])), "zip": bool(st.get("zip")), "zip_size": st.get("zip_size") or 0,
            "zip_url": zurl, "say": _say(r, st)}


def _say(r: AppProject, st: dict[str, Any]) -> str:
    s = st.get("status")
    if s == "writing":
        return f"iPhone app ban rahi hai: {st.get('now') or 'screens SwiftUI mein'}."
    if s in ("building", "fixing"):
        return "Mac par compile + iPhone simulator check" + (f", round {st.get('rounds')}" if st.get("rounds") else "") + "."
    if s == "uploading":
        return "TestFlight par bhej rahi hoon."
    if s == "ready":
        tf = st.get("testflight") or {}
        if st.get("kind") == "testflight" and tf:
            return f"iPhone app TestFlight par (v{tf.get('version')}, build {tf.get('build')})."
        return f"iPhone app taiyaar (build {st.get('build')}), simulator check paas. 'TestFlight par bhejo' kahiye."
    if s == "zip":
        return "iPhone ka Xcode project ZIP taiyaar (Mac build set nahi hai)."
    if s == "failed":
        return f"iPhone build mein dikkat: {st.get('error')}"
    return "Design pakka hai: 'iPhone app banao' kahiye." if r.approved_hash else "Pehle design pakka kijiye."


def get(tenant: str, ref: str) -> dict[str, Any]:
    with session() as s:
        r = AS._find(s, tenant, ref)
        s.expunge(r)
    return view(r)


def zip_by_token(token: str, name: str) -> Path:
    """The public link (random token, 7 days): her Xcode project ZIP (open on a Mac)."""
    if not re.fullmatch(r"[A-Za-z0-9_\-]{20,64}", token or "") or not re.fullmatch(r"ios-project-b\d+\.zip", name or ""):
        raise IosError("not found")
    with session() as s:
        rows = s.query(AppProject).filter(AppProject.android.like(f"%{token}%")).limit(3).all()
        for r in rows:
            s.expunge(r)
    for r in rows:
        st = state(r)
        if (st.get("zip_token") and secrets.compare_digest(st["zip_token"], token) and st.get("zip") == name
                and st.get("zip_expires", "") > now().isoformat()):
            f = _dir(r) / name
            if f.exists():
                return f
    raise IosError("not found")
