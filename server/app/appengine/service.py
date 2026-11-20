"""v0.814 APP ENGINE 1 (L8 of docs/LOVABLE_STUDIO_PLAN.md, owner: "GO L8") - a real React app per project.

One app = one folder: `data/appengine/<tenant>/<id>/src/` is the working copy (the one template + what Hoola wrote),
`versions/v<N>/` keeps every built version (source + built files), `live/` is what visitors see at /apps/<name>/.

- create: copies the template, writes package.json (core packages only) and tokens.css (the app's look), AGENTS.md.
- the tools (view / search / edit_lines / write / rename / delete / add_dependency / tokens) change the working copy
  through rules.py (paths, safety, design drift) - a refused write changes NOTHING and says the line and the fix;
- a change schedules a build in the box ~2 s after the last write (the preview rebuilds itself); `build` waits for it.
  A good build = a new version the preview shows; a failed build keeps the last good version on screen and its
  problems (TypeScript + Vite, file and line) are what `logs` returns;
- publish = HER tap in the Studio (never the tool): the exact version she sees, refused while the whole-app check finds
  a safety or drift problem or TypeScript fails; a published app is static files + nothing else (no server code).

What is NOT here yet (said plainly): Hoola Cloud data / sign-in (src/lib/hoola.ts says not connected), hot reload
inside the page (each change is a fresh build, ~5 s), click-to-source and the style panel (L9), tests / browser checks
before done (L11), a custom domain for an app."""
from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from ..db import now, session
from . import image as IMG
from . import rules as RL
from . import runner as RN
from . import tokens as TK
from . import genome as GN
from .models import AppProject, ensure_table

TEMPLATE = Path(__file__).resolve().parent / "template"
KEEP_VERSIONS = 30
DEBOUNCE = 2.0
MAX_VIEW_LINES = 400
_LOCKS: dict[str, threading.Lock] = {}
_TIMERS: dict[str, threading.Timer] = {}
_BUILD_DONE: dict[str, threading.Event] = {}
_MAP_LOCK = threading.Lock()
# v0.825 L9 the HMR-gate idea: a change made inside a Hoola turn is NOT built (shown) until that turn has finished,
# so the preview never shows a half-written change set; the model's own action=build means "this set is complete".
import contextvars as _cv
TURN_CONV: _cv.ContextVar[str] = _cv.ContextVar("hoola_ae_turn_conv", default="")
_GATE_CONV: dict[str, tuple[str, float]] = {}
GATE_POLL = 1.5
GATE_MAX = 1800.0
# the template files Hoola owns: refreshed into every app before each build (an older app gets today's tooling)
TOOLING = ("vite.config.ts", "tsconfig.json", "hoola.plugin.mjs", "src/main.tsx", "src/index.css", "src/lib/utils.ts",
           "src/lib/hoola.ts",
           # v0.999.64 D3: pre-rendering + islands
           "hoola.prerender.mjs", "src/entry-server.tsx", "src/islands-entry.tsx", "src/islands-wake.tsx", "src/lib/island.tsx",
           "src/lib/seo.tsx")

# v0.999.64 D3 (docs/WEB_DESIGN_ENGINE_PLAN.md P6): how the pages go out. "site" = every page pre-rendered to plain HTML
# that loads JavaScript only for its islands (fast, read by Google); a page with <AppPage> or an app screen stays the
# full app. "app" = every page pre-rendered, then the whole app takes over in the browser (an app made before D3).
RENDER_MODES = ("site", "app")
_HOOKS = re.compile(r"\bReact\.use(?:State|Reducer|Effect|Ref)\s*\(|\buse(?:State|Reducer|Effect)\s*\(|\bon[A-Z]\w+=\{")
_USE_CLIENT = re.compile(r"^(?:\s*(?://[^\n]*\n|/\*[\s\S]*?\*/))*\s*[\"']use client[\"'];?")


def site_dead_code(d: Path) -> list[str]:
    """v0.999.64 D3: on a SITE app, code that needs JavaScript but is not inside a "use client" component (under
    src/components or src/islands) renders as plain HTML that does nothing - name those files so they get fixed."""
    out = []
    src = d / "src"
    for f in sorted(src.rglob("*.tsx")):
        rel = f.relative_to(d).as_posix()
        if rel in RL.LOCKED or rel.startswith(("src/components/ui/", "src/components/effects/", "src/components/blocks/screen-")):
            continue                                  # the kit's parts + app screens (a page with one runs as the app)
        try:
            code = f.read_text("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        tpl = TEMPLATE / rel
        if tpl.is_file() and tpl.read_text("utf-8") == code:
            continue                                  # a kit file as Hoola made it
        island = rel.startswith(("src/components/", "src/islands/")) and _USE_CLIENT.match(code)
        if not island and "<AppPage" not in code and _HOOKS.search(code):
            out.append(rel)
    return out


def render_mode(r: AppProject) -> str:
    try:
        m = json.loads(r.look or "{}").get("render")
    except (ValueError, AttributeError):
        m = None
    return m if m in RENDER_MODES else "app"


def _prep_snap(r: AppProject, snap: Path) -> None:
    """what a build copy gets beyond her files: the genome's fonts (D2) and how the pages go out (D3)"""
    g = _genome(r)
    if g:
        GN.write_fonts(g, snap / "src" / "styles" / "fonts")
    (snap / "hoola.render.json").write_text(json.dumps({"mode": render_mode(r)}) + "\n", "utf-8")


class AppEngineError(Exception):
    def __init__(self, msg: str, code: int = 400, problems: list | None = None):
        super().__init__(msg)
        self.code = code
        self.problems = problems or []


def root() -> Path:
    return Path(os.environ.get("APP_ENGINE_DIR", "data/appengine"))


def pdir(tenant: str, pid: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", tenant or "default")
    return root() / safe / pid


def src_dir(r: AppProject) -> Path:
    return pdir(r.tenant_id, r.id) / "src"


def ver_dir(r: AppProject, v: int) -> Path:
    return pdir(r.tenant_id, r.id) / "versions" / f"v{int(v)}"


def live_dir(r: AppProject) -> Path:
    return pdir(r.tenant_id, r.id) / "live"


def _lock(pid: str) -> threading.Lock:
    with _MAP_LOCK:
        return _LOCKS.setdefault(pid, threading.Lock())


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "app").lower()).strip("-")[:40] or "app"
    return s


# ------------------------------------------------------------------ rows

def _find(s, tenant: str, ref: str) -> AppProject:
    ensure_table()
    ref = str(ref or "").strip()
    q = select(AppProject).where(AppProject.tenant_id == tenant)
    r = s.scalars(q.where(AppProject.id == ref)).first()
    if r is None and ref.isdigit():
        r = s.scalars(q.where(AppProject.number == int(ref))).first()
    if r is None and ref:
        r = s.scalars(q.where(AppProject.slug == ref)).first()
    if r is None:
        raise AppEngineError(f"There is no app '{ref}'.", 404)
    return r


def _load(tenant: str, ref: str) -> AppProject:
    with session() as s:
        r = _find(s, tenant, ref)
        s.expunge(r)
    return r


def _save(pid: str, **kw) -> None:
    with session() as s:
        r = s.get(AppProject, pid)
        for k, v in kw.items():
            setattr(r, k, v)
        r.updated_at = now()


def _deps(r: AppProject) -> set[str]:
    try:
        pkg = json.loads((src_dir(r) / "package.json").read_text())
    except (OSError, ValueError):
        return set(IMG.CORE)
    return set(pkg.get("dependencies") or {}) | set(pkg.get("devDependencies") or {})


def _files(r: AppProject) -> list[Path]:
    base = src_dir(r)
    return sorted(p for p in base.rglob("*") if p.is_file() and "node_modules" not in p.parts and "dist" not in p.parts[len(base.parts):len(base.parts) + 1])


def _rel(r: AppProject, p: Path) -> str:
    return p.relative_to(src_dir(r)).as_posix()


def view(r: AppProject, full: bool = True) -> dict[str, Any]:
    try:
        lb = json.loads(r.last_build or "{}")
    except ValueError:
        lb = {}
    out = {"id": r.id, "number": r.number, "name": r.name, "slug": r.slug, "status": r.status, "version": r.version,
           "live_version": r.live_version, "dirty": bool(r.dirty), "brief": r.brief or "",
           "preview": f"/api/app-preview/{r.preview_token}/" if r.version else "",
           "live_url": f"/apps/{r.slug}/" if r.live_version else "", "conversation_id": r.conversation_id or "",
           "created_at": r.created_at.isoformat() if r.created_at else "", "updated_at": r.updated_at.isoformat() if r.updated_at else "",
           "published_at": r.published_at.isoformat() if r.published_at else "",
           "held": held(r.id), "render": render_mode(r),
           "branch_of": r.branch_of or "", "branch_name": r.branch_name or "", "branch_base": int(r.branch_base or 0),
           "last_build": {k: lb.get(k) for k in ("ok", "seconds", "version", "types_ok", "types", "build_problems", "at", "why", "queued", "runner", "prerender")}}
    if full:
        try:
            look = json.loads(r.look or "{}")
        except ValueError:
            look = {}
        t = _theme(r)
        out["theme"] = TK.theme_json(t)
        out["palette"] = look.get("palette") or TK.DEFAULT
        if look.get("genome"):                       # v0.999.58 D2: the app's own design
            out["design"] = GN.summary(look["genome"])
        out["files"] = files_list(r)
        out["versions"] = versions(r)
        out["engine"] = RN.available()
    return out


# ------------------------------------------------------------------ create / list

def create(tenant: str, name: str = "", brief: str = "", palette: str = "", values: dict | None = None,
           site_look: dict | None = None, conversation_id: str = "", genome: dict | None = None,
           design_md: str = "", render: str = "") -> dict[str, Any]:
    """v0.999.58 D2: an app with no palette / colours / Web Studio look named gets its OWN design genome from her
    name + words (or the one / the DESIGN.md given); a named palette keeps the classic tokens."""
    ensure_table()
    name = " ".join(str(name or "").split())[:80] or "My app"
    vals = dict(values or {})
    if site_look:
        vals = {**TK.from_site_look(site_look), **vals}
    if palette and palette not in TK.PALETTES:
        raise AppEngineError(f"Palette '{palette}' does not exist (one of: {', '.join(TK.PALETTES)}).")
    if render and render not in RENDER_MODES:
        raise AppEngineError("render is 'site' (a website: pre-rendered pages + islands) or 'app' (a full app).")
    mode = render or "app"                           # v0.999.64 D3: a site only when asked (its pages run no code but islands)
    gen = None
    try:
        if design_md:
            gen = GN.from_design_md(design_md)
        elif genome:
            gen = GN.clean(genome)
        elif not palette and not vals:
            gen = GN.for_brief(name, brief)
        t = GN.tokens(gen) if gen else TK.resolve(vals, palette)
    except ValueError as e:
        raise AppEngineError(str(e))
    with session() as s:
        n = (s.scalar(select(func.max(AppProject.number)).where(AppProject.tenant_id == tenant)) or 0) + 1
        slug = _slugify(name)
        while s.scalars(select(AppProject).where(AppProject.slug == slug)).first() is not None:
            slug = f"{_slugify(name)[:32]}-{secrets.token_hex(2)}"
        r = AppProject(tenant_id=tenant, number=n, name=name, slug=slug, brief=str(brief or "")[:4000], status="new",
                       look=json.dumps({"palette": palette or TK.DEFAULT, "values": vals, "render": mode, **({"genome": gen} if gen else {})}),
                       preview_token=secrets.token_urlsafe(24), conversation_id=str(conversation_id or "")[:64])
        s.add(r)
        s.flush()
        s.expunge(r)
    d = src_dir(r)
    shutil.copytree(TEMPLATE, d)
    (d / "src" / "styles").mkdir(parents=True, exist_ok=True)
    _write_design(d, gen, t)
    (d / "package.json").write_text(json.dumps(IMG.project_package(r.slug), indent=2) + "\n", "utf-8")
    html = (d / "index.html").read_text().replace("<title>My app</title>", f"<title>{_esc(name)}</title>")
    (d / "index.html").write_text(html, "utf-8")
    (d / ".hoola" / "plan").mkdir(parents=True, exist_ok=True)
    _write_theme_json(r, t)
    if brief:
        (d / ".hoola" / "plan" / "brief.md").write_text(f"# What she asked for\n\n{brief.strip()}\n", "utf-8")
    schedule_build(tenant, r.id)
    return {**view(_load(tenant, r.id)), "say": f"App {n} \"{name}\" made from the template; its first build is starting."}


def site_look(tenant: str, ref: str) -> dict | None:
    """The look of one of her websites (so an app can carry the same brand); None when there is no such site."""
    try:
        from ..site import service as S
        with session() as s:
            r = S._find(s, tenant, ref)
            return json.loads(r.look or "{}") or None
    except Exception:                                # noqa: BLE001 - no site = no brand carried over
        return None


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def list_(tenant: str) -> list[dict[str, Any]]:
    ensure_table()
    with session() as s:
        rows = s.scalars(select(AppProject).where(AppProject.tenant_id == tenant)
                         .where((AppProject.branch_of == "") | (AppProject.branch_of.is_(None)))   # v0.978 branches live inside their app
                         .order_by(AppProject.updated_at.desc())).all()
        for r in rows:
            s.expunge(r)
    return [view(r, False) for r in rows]


def get(tenant: str, ref: str, full: bool = True) -> dict[str, Any]:
    return view(_load(tenant, ref), full)


def rename_app(tenant: str, ref: str, name: str) -> dict[str, Any]:
    r = _load(tenant, ref)
    name = " ".join(str(name or "").split())[:80]
    if not name:
        raise AppEngineError("The new name is empty.")
    _save(r.id, name=name)
    return view(_load(tenant, r.id), False)


def set_conversation(tenant: str, ref: str, conv: str) -> dict[str, Any]:
    r = _load(tenant, ref)
    _save(r.id, conversation_id=str(conv or "")[:64])
    return {"ok": True}


def delete_app(tenant: str, ref: str) -> dict[str, Any]:
    r = _load(tenant, ref)
    if r.live_version:
        raise AppEngineError("This app is live; take it down first (Studio > Publish > Take down).", 409)
    from . import branches as BR
    if not r.branch_of and BR.open_of(r):
        raise AppEngineError("This app has open branches; accept or discard them first (Studio > Branches).", 409)
    from . import cloud as CL
    CL.forget(r)                                      # v0.999.7 B4 its data project + preview twin + every row / member
    with session() as s:
        s.delete(s.get(AppProject, r.id))
    shutil.rmtree(pdir(r.tenant_id, r.id), ignore_errors=True)
    return {"ok": True, "say": f"App {r.number} deleted."}


# ------------------------------------------------------------------ files

def files_list(r: AppProject) -> list[dict[str, Any]]:
    out = []
    for p in _files(r):
        rel = _rel(r, p)
        out.append({"path": rel, "size": p.stat().st_size, "locked": rel in RL.LOCKED})
    return out


def _path_in(r: AppProject, rel: str) -> Path:
    p = (src_dir(r) / rel).resolve()
    base = src_dir(r).resolve()
    if base not in p.parents and p != base:
        raise AppEngineError(f"'{rel}' is not inside the app.")
    if p.is_symlink():
        raise AppEngineError(f"'{rel}' is a link; it is not read or written.")
    return p


def read_file(tenant: str, ref: str, path: str, from_line: int = 0, to_line: int = 0) -> dict[str, Any]:
    r = _load(tenant, ref)
    try:
        rel = RL.norm(path)
    except RL.RuleError as e:
        raise AppEngineError(str(e))
    p = _path_in(r, rel)
    if not p.is_file():
        near = [f["path"] for f in files_list(r) if rel.rsplit("/", 1)[-1].split(".")[0].lower() in f["path"].lower()][:6]
        raise AppEngineError(f"{rel} does not exist." + (f" Did you mean: {', '.join(near)}" if near else ""), 404)
    text = p.read_text("utf-8", "replace")
    lines = text.splitlines()
    a = max(1, int(from_line or 1))
    b = min(len(lines), int(to_line or 0) or len(lines), a + MAX_VIEW_LINES - 1)
    body = "\n".join(f"{i:>4}| {lines[i - 1]}" for i in range(a, b + 1)) if lines else ""
    return {"path": rel, "lines": len(lines), "from": a, "to": b, "locked": rel in RL.LOCKED, "code": body,
            "more": b < len(lines), "say": f"{rel}: lines {a}-{b} of {len(lines)}" + (" (more: ask for from_line)" if b < len(lines) else "")}


def search(tenant: str, ref: str, query: str, limit: int = 40) -> dict[str, Any]:
    r = _load(tenant, ref)
    q = str(query or "").strip()
    if not q:
        raise AppEngineError("What should I look for?")
    ql, hits, total = q.lower(), [], 0
    for p in _files(r):
        rel = _rel(r, p)
        if rel == "package-lock.json" or RL.ext(rel) not in RL.TEXT_EXT:
            continue
        try:
            text = p.read_text("utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if ql in line.lower():
                total += 1
                if len(hits) < limit:
                    hits.append({"file": rel, "line": n, "text": line.strip()[:240]})
    return {"query": q, "hits": hits, "total": total,
            "say": f"{total} place(s) found" + (f", first {len(hits)} shown" if total > len(hits) else "") if total else "Not found in the app."}


def _check(r: AppProject, rel: str, code: str) -> None:
    if len(code.encode("utf-8")) > RL.MAX_FILE:
        raise AppEngineError(f"{rel} would be over {RL.MAX_FILE // 1000} KB; split it into smaller components.")
    probs = RL.check_file(rel, code, _deps(r))
    if probs:
        raise AppEngineError(f"Not written - {rel} has a problem: " + RL.say(probs), 422, probs)


def _write(r: AppProject, rel: str, code: str) -> dict[str, Any]:
    p = _path_in(r, rel)
    old = p.read_text("utf-8", "replace") if p.exists() else None
    if old is None and len(_files(r)) >= RL.MAX_FILES:
        raise AppEngineError(f"The app already has {RL.MAX_FILES} files.")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(code, "utf-8")
    _save(r.id, dirty=True)
    schedule_build(r.tenant_id, r.id)
    import difflib
    diff = "".join(difflib.unified_diff((old or "").splitlines(True), code.splitlines(True), f"a/{rel}", f"b/{rel}", n=2))
    return {"file": rel, "new": old is None, "changed": old != code, "diff": diff[:12000],
            "say": (f"{'Made' if old is None else 'Changed'} {rel}. The preview rebuilds in a few seconds "
                    "(action=build waits for it and tells you if it failed).")}


def write(tenant: str, ref: str, path: str, code: str) -> dict[str, Any]:
    r = _load(tenant, ref)
    try:
        rel = RL.writable(path)
    except RL.RuleError as e:
        raise AppEngineError(str(e))
    code = str(code if code is not None else "")
    if not code.strip():
        raise AppEngineError("The file would be empty; to remove it use action=delete.")
    if not code.endswith("\n"):
        code += "\n"
    with _lock(r.id):
        _check(r, rel, code)
        return _write(r, rel, code)


def _apply_one(text: str, lines: list[str], ed: dict[str, Any], i: int) -> tuple[int, int, str]:
    """(start, end, replacement) for one edit, located in the ORIGINAL text. Never guesses."""
    find = str(ed.get("search") or ed.get("find") or "")
    repl = str(ed.get("replace") if ed.get("replace") is not None else "")
    if not find.strip():
        raise AppEngineError(f"edit {i + 1}: the search text is empty; copy the exact lines from action=view.")
    lo = int(ed.get("first_line") or 0)
    hi = int(ed.get("last_line") or 0)
    off = [0]
    for ln in lines:
        off.append(off[-1] + len(ln))
    a = off[lo - 1] if lo >= 1 and lo - 1 < len(off) else 0
    b = off[min(hi, len(lines))] if hi >= 1 else len(text)
    if lo and hi and hi < lo:
        raise AppEngineError(f"edit {i + 1}: last_line {hi} is before first_line {lo}.")
    part = find.split("\n...\n") if "\n...\n" in find else None
    if part and len(part) == 2:                       # "..." skips a long middle: match the head, then the tail after it
        head, tail = part
        hs = [m.start() for m in re.finditer(re.escape(head), text[a:b])]
        if len(hs) != 1:
            raise AppEngineError(f"edit {i + 1}: the first part of the search appears {len(hs)} times"
                                 + (f" in lines {lo}-{hi}" if lo else "") + "; give lines or more text.")
        s0 = a + hs[0]
        t = text.find(tail, s0 + len(head), b)
        if t < 0:
            raise AppEngineError(f"edit {i + 1}: the part after '...' was not found after the first part.")
        return s0, t + len(tail), repl
    n = text.count(find, a, b)
    if n != 1:
        where = f" in lines {lo}-{hi}" if lo or hi else ""
        if n == 0:
            import difflib
            first = find.strip().splitlines()[0].strip()
            near = difflib.get_close_matches(first, [x.strip() for x in lines], n=3, cutoff=0.5)
            raise AppEngineError(f"edit {i + 1}: the search text is not in the file{where} exactly (spaces and quotes count)."
                                 + (" Closest lines: " + " | ".join(x[:160] for x in near) if near else ""))
        raise AppEngineError(f"edit {i + 1}: the search text appears {n} times{where}; give first_line / last_line or more text.")
    s0 = text.find(find, a, b)
    return s0, s0 + len(find), repl


def edit_lines(tenant: str, ref: str, path: str, edits: list[dict[str, Any]]) -> dict[str, Any]:
    """Exact search -> replace edits in ONE file, each located in the ORIGINAL file (so line numbers from one view
    stay right for every edit); overlapping edits are refused; all or nothing."""
    r = _load(tenant, ref)
    try:
        rel = RL.writable(path)
    except RL.RuleError as e:
        raise AppEngineError(str(e))
    if isinstance(edits, dict):
        edits = [edits]
    edits = [e for e in (edits or []) if isinstance(e, dict)][:30]
    if not edits:
        raise AppEngineError("No edits given: each edit is {search, replace, first_line?, last_line?}.")
    with _lock(r.id):
        p = _path_in(r, rel)
        if not p.exists():
            raise AppEngineError(f"{rel} does not exist; use action=write to make it.", 404)
        text = p.read_text("utf-8")
        lines = text.splitlines(True)
        spans = sorted((_apply_one(text, lines, e, i) for i, e in enumerate(edits)), key=lambda x: x[0])
        for x, y in zip(spans, spans[1:]):
            if y[0] < x[1]:
                raise AppEngineError("Two edits overlap; merge them into one.")
        out, pos = [], 0
        for s0, e0, rep in spans:
            out.append(text[pos:s0])
            out.append(rep)
            pos = e0
        out.append(text[pos:])
        new = "".join(out)
        if new == text:
            raise AppEngineError("The edits change nothing.")
        _check(r, rel, new)
        res = _write(r, rel, new)
        res["edits"] = len(spans)
        return res


def rename(tenant: str, ref: str, path: str, to: str) -> dict[str, Any]:
    r = _load(tenant, ref)
    try:
        a, b = RL.writable(path), RL.writable(to)
    except RL.RuleError as e:
        raise AppEngineError(str(e))
    with _lock(r.id):
        pa, pb = _path_in(r, a), _path_in(r, b)
        if not pa.exists():
            raise AppEngineError(f"{a} does not exist.", 404)
        if pb.exists():
            raise AppEngineError(f"{b} already exists.")
        _check(r, b, pa.read_text("utf-8", "replace"))
        pb.parent.mkdir(parents=True, exist_ok=True)
        pa.rename(pb)
        _save(r.id, dirty=True)
        schedule_build(r.tenant_id, r.id)
    return {"from": a, "to": b, "say": f"Moved {a} to {b}. Update the imports that name the old path (action=search)."}


def delete(tenant: str, ref: str, path: str) -> dict[str, Any]:
    r = _load(tenant, ref)
    try:
        rel = RL.writable(path)
    except RL.RuleError as e:
        raise AppEngineError(str(e))
    if rel in ("src/App.tsx", "index.html"):
        raise AppEngineError(f"{rel} is the app's entry; change it instead of deleting it.")
    with _lock(r.id):
        p = _path_in(r, rel)
        if not p.exists():
            raise AppEngineError(f"{rel} does not exist.", 404)
        p.unlink()
        _save(r.id, dirty=True)
        schedule_build(r.tenant_id, r.id)
    return {"file": rel, "say": f"Deleted {rel}. It is still in earlier versions."}


def add_dependency(tenant: str, ref: str, package: str) -> dict[str, Any]:
    r = _load(tenant, ref)
    raw = str(package or "").strip()
    name = ("@" + raw[1:].split("@")[0]) if raw.startswith("@") else raw.split("@")[0]
    if name not in IMG.VETTED:
        raise AppEngineError(f"'{name}' is not in the vetted list. Vetted extras: "
                             + "; ".join(f"{k} ({v[1]})" for k, v in IMG.EXTRA.items())
                             + ". The template already has: " + ", ".join(sorted(IMG.CORE)) + ".")
    with _lock(r.id):
        f = src_dir(r) / "package.json"
        pkg = json.loads(f.read_text())
        deps = pkg.setdefault("dependencies", {})
        if name in deps:
            return {"package": name, "version": deps[name], "added": False, "say": f"{name} is already in this app."}
        deps[name] = IMG.VETTED[name]
        pkg["dependencies"] = dict(sorted(deps.items()))
        f.write_text(json.dumps(pkg, indent=2) + "\n")
        _save(r.id, dirty=True)
    return {"package": name, "version": IMG.VETTED[name], "added": True,
            "say": f"Added {name} {IMG.VETTED[name]} (already in the build box, nothing downloaded)."}


def set_tokens(tenant: str, ref: str, values: dict | None = None, palette: str = "") -> dict[str, Any]:
    r = _load(tenant, ref)
    try:
        look = json.loads(r.look or "{}")
    except ValueError:
        look = {}
    if palette and palette not in TK.PALETTES:
        raise AppEngineError(f"Palette '{palette}' does not exist (one of: {', '.join(TK.PALETTES)}).")
    vals = {**(look.get("values") or {}), **{str(k).replace("-", "_"): v for k, v in (values or {}).items()}}
    if palette:
        vals = {k: v for k, v in (values or {}).items()}            # a new palette starts clean; her values on top
    pal = palette or look.get("palette") or TK.DEFAULT
    try:
        t = TK.resolve(vals, pal)
    except ValueError as e:
        raise AppEngineError(str(e))
    with _lock(r.id):
        _write_design(src_dir(r), None, t)         # her named colours / palette: the classic tokens (no genome)
        _write_theme_json(r, t)
        _save(r.id, look=json.dumps({"palette": pal, "values": vals}), dirty=True)
        schedule_build(r.tenant_id, r.id)
    th = TK.theme_json(t)
    warn = []
    if th["contrast_ink_on_bg"] < 4.5:
        warn.append(f"text on the background is hard to read (contrast {th['contrast_ink_on_bg']}, needs 4.5)")
    warn += [w for w in TK.audit(t) if not w.startswith("ink on bg")]        # v0.999.51 the contrast floor
    return {"theme": th, "warnings": warn, "say": "The design tokens changed; every screen follows them." +
            (" Warning: " + "; ".join(warn) + "." if warn else "")}


# ------------------------------------------------------------------ the whole-app check

def check_all(r: AppProject) -> dict[str, Any]:
    deps, probs = _deps(r), []
    for p in _files(r):
        rel = _rel(r, p)
        if RL.ext(rel) not in RL.TEXT_EXT or rel in RL.LOCKED:      # Hoola's own locked template files
            continue
        try:
            probs += RL.check_file(rel, p.read_text("utf-8"), deps)
        except UnicodeDecodeError:
            probs.append({"file": rel, "line": 1, "rule": "file", "found": "not a text file"})
    return {"ok": not probs, "problems": probs[:60], "count": len(probs)}


# ------------------------------------------------------------------ builds + versions

def _turn_running(conv: str) -> bool:
    try:
        from ..agent import santosh
        return bool(conv) and santosh.turn_running(conv)
    except Exception:                                # noqa: BLE001 - no way to tell = never hold a build
        return False


def held(pid: str) -> bool:
    """Is a change of this app waiting for Hoola's turn to finish before it is built?"""
    g = _GATE_CONV.get(pid)
    return bool(g) and _turn_running(g[0])


def schedule_build(tenant: str, pid: str, delay: float | None = None) -> None:
    """The preview rebuilds itself ~2 s after the last change (many quick edits = one build) - and, for a change made
    inside a Hoola turn, only once that turn has finished (never a half-written change set on screen)."""
    conv = TURN_CONV.get()
    delay = DEBOUNCE if delay is None else delay
    with _MAP_LOCK:
        if conv:
            _GATE_CONV[pid] = (conv, _GATE_CONV.get(pid, (conv, time.time()))[1])
        t = _TIMERS.pop(pid, None)
        if t:
            t.cancel()
        ev = _BUILD_DONE.get(pid)
        if ev is None or ev.is_set():
            _BUILD_DONE[pid] = threading.Event()
        if os.environ.get("HOOLA_APPENGINE_AUTOBUILD", "1") == "0":
            return
        tm = threading.Timer(delay, _bg_build, args=(tenant, pid))
        tm.daemon = True
        _TIMERS[pid] = tm
        tm.start()


def _bg_build(tenant: str, pid: str) -> None:
    with _MAP_LOCK:
        _TIMERS.pop(pid, None)
        g = _GATE_CONV.get(pid)
        if g and _turn_running(g[0]) and time.time() - g[1] < GATE_MAX:     # the turn is still writing: wait for it
            tm = threading.Timer(GATE_POLL, _bg_build, args=(tenant, pid))
            tm.daemon = True
            _TIMERS[pid] = tm
            tm.start()
            return
        _GATE_CONV.pop(pid, None)
    try:
        build(tenant, pid)
    except Exception:                                # noqa: BLE001 - the result is stored on the row either way
        import logging
        logging.getLogger("santosh.appengine").warning("app build %s failed", pid, exc_info=True)


def build(tenant: str, ref: str) -> dict[str, Any]:
    """Build the working copy now (in the box). A good build becomes the next version; the preview shows it."""
    r = _load(tenant, ref)
    with _MAP_LOCK:
        t = _TIMERS.pop(r.id, None)
        if t:
            t.cancel()
        ev = _BUILD_DONE.setdefault(r.id, threading.Event())
    with _lock(r.id):
        av = RN.available()
        if not av["ok"]:
            lb = {"ok": False, "why": av["why"], "at": now().isoformat(), "runner": av.get("runner")}
            _save(r.id, last_build=json.dumps(lb), status="failed" if not r.version else r.status)
            ev.set()
            raise AppEngineError("The app could not be built: " + av["why"], 503)
        _GATE_CONV.pop(r.id, None)
        _refresh_template(r)
        _save(r.id, status="building")
        snap = Path(pdir(r.tenant_id, r.id) / "_snap")
        shutil.rmtree(snap, ignore_errors=True)
        shutil.copytree(src_dir(r), snap, ignore=shutil.ignore_patterns("node_modules", "dist"))
        _prep_snap(r, snap)                       # v0.999.58 D2 fonts + v0.999.64 D3 render mode, in the build copy only
    try:
        res = RN.build(snap)
    except RuntimeError as e:
        res = {"ok": False, "why": str(e), "seconds": 0}
    shutil.rmtree(snap, ignore_errors=True)
    if res.get("queued"):
        _save(r.id, status="ready" if r.version else "new")
        ev.set()
        return {**view(_load(tenant, r.id), False), "queued": True, "say": res["why"]}
    stamp = now().isoformat()
    lb = {k: res.get(k) for k in ("ok", "seconds", "types_ok", "types", "build_problems", "why", "runner", "log", "types_log", "prerender")}
    lb["at"] = stamp
    with _lock(r.id):
        r = _load(tenant, r.id)
        if res.get("ok"):
            v = int(r.version or 0) + 1
            d = ver_dir(r, v)
            shutil.rmtree(d, ignore_errors=True)
            d.mkdir(parents=True)
            shutil.copytree(res["dist"], d / "dist")
            shutil.copytree(src_dir(r), d / "src", ignore=shutil.ignore_patterns("node_modules", "dist"))
            (d / "build.json").write_text(json.dumps({**lb, "version": v}))
            lb["version"] = v
            _save(r.id, version=v, status="ready", dirty=False, last_build=json.dumps(lb))
            _prune(r)
        else:
            lb["version"] = r.version
            _save(r.id, status="ready" if r.version else "failed", last_build=json.dumps(lb))
    shutil.rmtree(res.get("out_dir") or "/nonexistent", ignore_errors=True)
    ev.set()
    r = _load(tenant, r.id)
    if res.get("ok"):
        say = f"Built version {r.version} in {res.get('seconds')} s; the preview shows it." + prerender_line(res.get("prerender") or {})
        if render_mode(r) == "site":
            dead = site_dead_code(src_dir(r))
            if dead:
                say += (" On a site page these files' buttons, forms and state do NOTHING (no script runs there): "
                        + ", ".join(dead[:6]) + ". Move the interactive part into a component in src/components or "
                        "src/islands that starts with \"use client\";, or wrap the page in <AppPage>.")
        if not res.get("types_ok"):
            say += " TypeScript found problems (it still built; fix them before going live): " + \
                   "; ".join(f"{x['file']}:{x['line']} {x['message']}" for x in res.get("types", [])[:5])
    else:
        say = ("The build failed, so the preview still shows version " + str(r.version) + ". Problems: " +
               ("; ".join(f"{x.get('file') or '?'}:{x.get('line') or ''} {x['message']}" for x in res.get("build_problems", [])[:6])
                or (res.get("why") or "see action=logs")))
    return {**view(r, False), "built": bool(res.get("ok")), "say": say}


def prerender_line(p: dict) -> str:
    """v0.999.64 D3: what the pre-render did, in one plain sentence (nothing when the build had no pre-render step)"""
    if not p:
        return ""
    if not p.get("ok"):
        return " The pages could not be pre-rendered, so they draw in the browser: " + (p.get("why") or "see action=logs")[:300]
    out = f" Pre-rendered {p.get('pages')} page(s) as finished HTML ({p.get('mode')})."
    bad = p.get("failed") or []
    if bad:
        out += " Could not render (they draw in the browser; fix them): " + "; ".join(
            f"{x.get('path')}: {x.get('why')}" for x in bad[:4])
    return out


def _refresh_template(r: AppProject) -> None:
    """Hoola's own tooling files (locked) are copied fresh from the template, tokens.css and theme.json are written
    again from the app's look: an app made by an older version builds with today's plugin + settings."""
    d = src_dir(r)
    for rel in TOOLING:
        f = TEMPLATE / rel
        if f.exists():
            (d / rel).parent.mkdir(parents=True, exist_ok=True)
            if not (d / rel).exists() or (d / rel).read_bytes() != f.read_bytes():
                shutil.copy2(f, d / rel)
    from . import cloud as CL
    CL.write_types(r, quiet=True)                       # v0.827 the typed lists of its Hoola Cloud
    t = _theme(r)
    _write_design(d, _genome(r), t)
    _write_theme_json(r, t)


def _genome(r: AppProject) -> dict | None:
    try:
        g = json.loads(r.look or "{}").get("genome")
    except (ValueError, AttributeError):
        return None
    return g if isinstance(g, dict) else None


def _theme(r: AppProject) -> dict[str, Any]:
    g = _genome(r)
    if g:
        return GN.tokens(g)
    try:
        look = json.loads(r.look or "{}")
    except ValueError:
        look = {}
    return TK.resolve(look.get("values") or {}, look.get("palette") or "")


def _write_design(d: Path, gen: dict | None, t: dict[str, Any]) -> None:
    """tokens.css (+ DESIGN.md for a genome) - only what changed is written. The fonts are not her files: build() puts
    them in the build copy, so branches / GitHub sync / file lists only ever see text."""
    styles = d / "src" / "styles"
    styles.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(styles / "fonts", ignore_errors=True)      # fonts ride the BUILD copy only (her files stay text)
    if gen:
        css = GN.css(gen)
        md = GN.design_md(gen)
        if not (d / "DESIGN.md").exists() or (d / "DESIGN.md").read_text() != md:
            (d / "DESIGN.md").write_text(md, "utf-8")
    else:
        css = TK.css(t)
        (d / "DESIGN.md").unlink(missing_ok=True)
    tf = styles / "tokens.css"
    if not tf.exists() or tf.read_text() != css:
        tf.write_text(css, "utf-8")


# ------------------------------------------------------------------ v0.999.58 D2 the design genome

def set_render(tenant: str, ref: str, mode: str) -> dict[str, Any]:
    """v0.999.64 D3: 'site' = pre-rendered pages with islands; 'app' = the whole app in the browser. The next build uses it."""
    if mode not in RENDER_MODES:
        raise AppEngineError("render is 'site' (a website: pre-rendered pages + islands) or 'app' (a full app).")
    r = _load(tenant, ref)
    with _lock(r.id):
        look = json.loads(_load(tenant, r.id).look or "{}")
        look["render"] = mode
        _save(r.id, look=json.dumps(look), dirty=True)
    schedule_build(r.tenant_id, r.id)
    say = ("Every page will be plain HTML that opens at once and is read by Google; only forms, booking, menus and "
           "other islands load code." if mode == "site" else "The whole app will run in the browser (pages are still pre-rendered first).")
    return {**view(_load(tenant, r.id), False), "say": say + " It applies from the next build."}


def get_design(tenant: str, ref: str) -> dict[str, Any]:
    r = _load(tenant, ref)
    g = _genome(r)
    if not g:
        return {"design": None, "say": "This app uses a named palette (classic tokens), not its own design genome yet: "
                                       "action=design_new makes one."}
    return {"design": GN.summary(g), "design_md": GN.design_md(g), "genome": g}


def set_design(tenant: str, ref: str, *, hue: float | None = None, direction: str = "", mode: str = "", pin: str = "",
               seed: str = "", words: str = "", fonts: dict | None = None, genes: dict | None = None,
               design_md: str = "") -> dict[str, Any]:
    """A new design genome for the app (or her DESIGN.md imported) - every colour pair checked before it is used."""
    r = _load(tenant, ref)
    try:
        if design_md:
            g = GN.from_design_md(design_md)
        else:
            old = _genome(r) or {}
            if genes:
                g = GN.clean({**old, **genes})
            else:
                g = GN.generate(seed=seed or f"{r.id}:{secrets.token_hex(3)}", hue=hue, direction=direction,
                                mode=mode, pin=pin, words=words or r.brief or "", name=r.name, fonts=fonts)
    except ValueError as e:
        raise AppEngineError(str(e))
    with _lock(r.id):
        try:
            look = json.loads(r.look or "{}")
        except ValueError:
            look = {}
        look["genome"] = g
        t = GN.tokens(g)
        _write_design(src_dir(r), g, t)
        _write_theme_json(r, t)
        _save(r.id, look=json.dumps(look), dirty=True)
        schedule_build(r.tenant_id, r.id)
    sm = GN.summary(g)
    return {"design": sm, "say": f"New design: {sm['direction']} ({sm['mode']}), brand colour {sm['primary']}, "
                                 f"{sm['fonts']['display']} headings on {sm['fonts']['text']} text, corners {sm['radius']}px, "
                                 f"{sm['density']} spacing, {sm['motion']} motion; every colour pair checked. Every screen "
                                 "follows it; DESIGN.md holds it."}


def _write_theme_json(r: AppProject, t: dict[str, Any]) -> None:
    from . import pick as PK
    f = src_dir(r) / ".hoola" / "theme.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({**TK.theme_json(t), "classes": PK.FAMILIES_VIEW}, indent=2) + "\n", "utf-8")


def wait_build(tenant: str, ref: str, timeout: float = 90.0) -> dict[str, Any]:
    """The tool's action=build: run any pending build now and return its result."""
    r = _load(tenant, ref)
    with _MAP_LOCK:
        pending = r.id in _TIMERS
    if pending or r.dirty or not r.version:
        return build(tenant, r.id)
    ev = _BUILD_DONE.get(r.id)
    if ev and not ev.is_set():
        ev.wait(timeout)
    return {**view(_load(tenant, r.id), False), "say": "Nothing changed since version %d." % r.version}


def logs(tenant: str, ref: str) -> dict[str, Any]:
    r = _load(tenant, ref)
    try:
        lb = json.loads(r.last_build or "{}")
    except ValueError:
        lb = {}
    chk = check_all(r)
    from . import pick as PK
    runtime = [x for x in PK._read_errors(r) if x["state"] == "open"][:10]
    return {"version": r.version, "dirty": bool(r.dirty), "last_build": lb, "check": chk, "preview_errors": runtime,
            "say": ("Last build: " + ("ok" if lb.get("ok") else "failed") + (f" ({lb.get('seconds')} s)" if lb.get("seconds") else "")
                    + ("; TypeScript ok" if lb.get("types_ok") else f"; TypeScript problems: {len(lb.get('types') or [])}")
                    + (f"; rule problems: {chk['count']}" if chk["count"] else "; rules ok")
                    + (f"; the preview reported {len(runtime)} error(s): " + "; ".join(
                        x["message"][:120] + (f" at {x['file']}:{x['line']}" if x.get("file") else "") for x in runtime[:3])
                       if runtime else "")) if lb else "Not built yet."}


def versions(r: AppProject) -> list[dict[str, Any]]:
    out = []
    base = pdir(r.tenant_id, r.id) / "versions"
    for d in sorted(base.glob("v*"), key=lambda x: int(x.name[1:]) if x.name[1:].isdigit() else 0, reverse=True):
        try:
            b = json.loads((d / "build.json").read_text())
        except (OSError, ValueError):
            b = {}
        n = int(d.name[1:]) if d.name[1:].isdigit() else 0
        out.append({"version": n, "at": b.get("at"), "seconds": b.get("seconds"), "types_ok": b.get("types_ok"),
                    "live": n == r.live_version})
    return out


def _prune(r: AppProject) -> None:
    vs = versions(r)
    for v in vs[KEEP_VERSIONS:]:
        if v["version"] != r.live_version:
            shutil.rmtree(ver_dir(r, v["version"]), ignore_errors=True)


# ------------------------------------------------------------------ publish (her tap)

def publish_check(r: AppProject, v: int) -> list[str]:
    bl = []
    d = ver_dir(r, v)
    if not (d / "dist" / "index.html").exists():
        return [f"version {v} is not built"]
    try:
        b = json.loads((d / "build.json").read_text())
    except (OSError, ValueError):
        b = {}
    if not b.get("types_ok"):
        bl.append("TypeScript found problems in this version: " + "; ".join(
            f"{x['file']}:{x['line']} {x['message']}" for x in (b.get("types") or [])[:4]))
    deps = set()
    try:
        deps = set((json.loads((d / "src" / "package.json").read_text()).get("dependencies") or {}))
    except (OSError, ValueError):
        pass
    probs = []
    for p in sorted((d / "src").rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(d / "src").as_posix()
        if RL.ext(rel) in RL.TEXT_EXT and rel not in RL.LOCKED:
            try:
                probs += RL.check_file(rel, p.read_text("utf-8"), deps | set(IMG.DEV))
            except UnicodeDecodeError:
                continue
    if probs:
        bl.append("the code check found: " + RL.say(probs, 4))
    if getattr(RN._settings(), "app_engine_publish_checks", True):      # v0.832 SABOOT: the scans + rule tests + browser check must not FAIL
        from . import saboot as SB
        bl += SB.blockers(r, v)
    return bl


def publish(tenant: str, ref: str, version: int, confirm: bool = False) -> dict[str, Any]:
    """Only from HER tap in the Studio (the route needs confirm=true; the agent tool cannot call this)."""
    r = _load(tenant, ref)
    v = int(version or 0)
    if not confirm:
        raise AppEngineError("Going live needs her tap in the Studio (confirm).", 403)
    if r.branch_of:
        raise AppEngineError("A branch never goes live. Accept it into its app first, then publish the app.", 409)
    if not v or v > int(r.version or 0):
        raise AppEngineError(f"There is no built version {v}.", 404)
    bl = publish_check(r, v)
    if bl:
        raise AppEngineError("Not published: " + " | ".join(bl), 409)
    # v0.825 the preview build carries source tags + source maps; what goes live is a CLEAN build of the same source
    snap = pdir(r.tenant_id, r.id) / "_pub"
    shutil.rmtree(snap, ignore_errors=True)
    shutil.copytree(ver_dir(r, v) / "src", snap)
    _prep_snap(r, snap)                           # v0.999.64: fonts + render mode reach the live build too
    try:
        res = RN.build(snap, source=False)
    except RuntimeError as e:
        raise AppEngineError("The app could not be built for going live: " + str(e), 503)
    finally:
        shutil.rmtree(snap, ignore_errors=True)
    if res.get("queued"):
        raise AppEngineError(res["why"], 409)
    if not res.get("ok"):
        shutil.rmtree(res.get("out_dir") or "/nonexistent", ignore_errors=True)
        raise AppEngineError("The clean build for going live failed: " + (res.get("why") or ""), 409)
    leak = [p.name for p in Path(res["dist"]).rglob("*") if p.is_file() and (p.suffix == ".map" or b"data-hs" in p.read_bytes())]
    if leak:
        shutil.rmtree(res.get("out_dir") or "/nonexistent", ignore_errors=True)
        raise AppEngineError("The live build still carried preview tags (" + ", ".join(leak[:3]) + "); not published.", 500)
    with _lock(r.id):
        tmp = live_dir(r).with_name("live.new")
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.copytree(res["dist"], tmp)
        shutil.rmtree(res.get("out_dir") or "/nonexistent", ignore_errors=True)
        old = live_dir(r).with_name("live.old")
        shutil.rmtree(old, ignore_errors=True)
        if live_dir(r).exists():
            live_dir(r).rename(old)
        tmp.rename(live_dir(r))
        shutil.rmtree(old, ignore_errors=True)
        _save(r.id, live_version=v, published_at=now())
    return {**view(_load(tenant, r.id), False), "say": f"Version {v} is live at /apps/{r.slug}/."}


def unpublish(tenant: str, ref: str, confirm: bool = False) -> dict[str, Any]:
    r = _load(tenant, ref)
    if not confirm:
        raise AppEngineError("Taking the app down needs her tap (confirm).", 403)
    shutil.rmtree(live_dir(r), ignore_errors=True)
    _save(r.id, live_version=0)
    return {**view(_load(tenant, r.id), False), "say": "The app is not live any more."}


# ------------------------------------------------------------------ serving (preview + live)

TYPES = {".html": "text/html; charset=utf-8", ".js": "application/javascript", ".css": "text/css",
         ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
         ".ico": "image/x-icon", ".json": "application/json", ".txt": "text/plain; charset=utf-8", ".woff2": "font/woff2",
         ".webmanifest": "application/manifest+json", ".gif": "image/gif", ".avif": "image/avif"}
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https:; "
       "font-src 'self' data:; connect-src 'self'; media-src 'self' blob: https:; frame-ancestors 'self'; base-uri 'self'; "
       "form-action 'self'; object-src 'none'")


SHELL_CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-src 'self'; "
             "img-src 'self' data:; frame-ancestors 'self'; base-uri 'none'; form-action 'self'; object-src 'none'")


def _shell(r, prefix: str, ds: str) -> tuple[bytes, str, dict[str, str]]:
    """v0.827 the page at the app's address: Hoola's shell, which frames the sealed app and keeps its sign-in."""
    from . import cloud as CL
    cfg = {"base": prefix, "cloud": f"/api/cloud/{CL.key_of(r, ds)}", "key": r.slug + (":p" if ds == "preview" else ""),
           "title": r.name}
    meta = _esc(json.dumps(cfg)).replace("'", "&#39;")
    html = (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, '
            f'initial-scale=1"><title>{_esc(r.name)}</title><link rel="icon" href="data:,"><meta name="hoola-app" content=\'{meta}\'>'
            '<style>html,body{margin:0;height:100%;background:#fff}</style>'
            f'<script src="{prefix}__hoola/shell.js" defer></script></head><body></body></html>\n')
    hdr = {"Content-Security-Policy": SHELL_CSP, "X-Content-Type-Options": "nosniff", "Cache-Control": "no-store",
           "Referrer-Policy": "strict-origin-when-cross-origin"}
    if ds == "preview":
        hdr["X-Robots-Tag"] = "noindex, nofollow"
    return html.encode("utf-8"), "text/html; charset=utf-8", hdr


# v0.999.64 D3: a pre-rendered SITE page goes out at the app's own address with no frame around it, so Google reads
# it and it opens at once. The browser still seals it: `sandbox` in its CSP gives the page its own blank origin (as
# the frame did), so it cannot read any sign-in or other app on this address. Scripts run only for its islands.
SITE_CSP = ("sandbox allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox allow-downloads; " + CSP)


def pages_of(root_: Path) -> dict[str, Any]:
    """what the build's pre-render wrote (dist/__pages.json); {} for a build made before D3"""
    try:
        return json.loads((root_ / "__pages.json").read_text())
    except (OSError, ValueError):
        return {}


def _page_file(root_: Path, rel: str) -> Path | None:
    """the pre-rendered page for an address of the app ("" = home), if the build wrote one"""
    parts = [x for x in rel.strip("/").split("/") if x]
    if any(x in ("..", ".") or x.startswith("__") for x in parts):
        return None
    f = root_.joinpath(*parts, "index.html") if parts else root_ / "index.html"
    return f if f.is_file() and not f.is_symlink() else None


def _is_site_page(root_: Path, rel: str) -> bool:
    pg = pages_of(root_)
    if pg.get("mode") != "site":
        return False
    want = "/" + rel.strip("/")
    return any(p.get("path") == want and p.get("kind") == "site" for p in pg.get("pages") or [])


def _origin() -> str:
    try:
        from ..config import get_settings
        return str(get_settings().public_base_url or "").rstrip("/")
    except Exception:  # noqa: BLE001
        return ""


def _route(r, root_: Path, rel: str, prefix: str, ds: str) -> tuple[bytes, str, dict[str, str]]:
    """shell page / its script / the sealed app under __app/ (v0.827: every app runs in a sealed frame); v0.999.64 D3:
    on a LIVE site app its pre-rendered site pages (and their files, sitemap.xml, robots.txt) are served directly."""
    here = Path(__file__).resolve().parent
    if rel == "__app/__hoola/preview.js":            # the app page asks for its helper relative to its own base
        rel = "__hoola/preview.js"
    if rel in ("__hoola/shell.js", "__hoola/preview.js"):
        if rel.endswith("preview.js") and ds != "preview":
            raise AppEngineError("not found", 404)
        return (here / rel.split("/")[1]).read_bytes(), "application/javascript", {
            "Content-Security-Policy": CSP, "Cache-Control": "no-store", "Access-Control-Allow-Origin": "*",
            "X-Content-Type-Options": "nosniff"}
    if rel == "__app" or rel.startswith("__app/"):
        return _serve(root_, rel[len("__app/"):] if rel.startswith("__app/") else "", prefix + "__app/", ds == "preview")
    last = rel.rsplit("/", 1)[-1]
    if ds == "live" and pages_of(root_).get("mode") == "site":
        if rel and "." in last:                      # the site page's own files (assets, fonts, sitemap, robots)
            return _serve(root_, rel, prefix, False, site=True)
        if _is_site_page(root_, rel):
            from . import cloud as CL
            return _serve(root_, rel, prefix, False, site=True, cloud=f"/api/cloud/{CL.key_of(r, 'live')}")
    if rel and "." in last:
        raise AppEngineError("not found", 404)
    return _shell(r, prefix, ds)


def _fill(txt: str, prefix: str, preview: bool = False) -> str:
    """the build writes /__hoola_base__ and __hoola_origin__ where the app's own address goes (D3). Links follow the
    page's own place; the canonical link, sitemap and robots always name the app's PUBLIC page (never the frame's
    __app/ copy), and a preview (never indexed) carries no canonical link at all."""
    if preview:
        txt = re.sub(r'\n?\s*<link rel="canonical"[^>]*>', "", txt)
    public = prefix[:-len("__app/")] if prefix.endswith("__app/") else prefix
    txt = txt.replace("__hoola_origin__/__hoola_base__", _origin() + public.rstrip("/"))
    return txt.replace("__hoola_origin__", _origin()).replace("/__hoola_base__", prefix.rstrip("/"))


def _serve(root_: Path, path: str, prefix: str, preview: bool, site: bool = False,
           cloud: str = "") -> tuple[bytes, str, dict[str, str]]:
    rel = (path or "").lstrip("/")
    if ".." in rel.split("/") or "\0" in rel or any(x.startswith("__") for x in rel.split("/")):
        raise AppEngineError("not found", 404)       # __pages.json / __spa.html are the build's own
    f = (root_ / rel) if rel else root_ / "index.html"
    if rel and (not f.is_file() or f.is_symlink()):
        if "." in rel.rsplit("/", 1)[-1]:
            raise AppEngineError("not found", 404)
        # v0.999.64 D3: the page the build pre-rendered for this address; else the plain app page (React Router)
        f = _page_file(root_, rel) or (root_ / "__spa.html" if (root_ / "__spa.html").is_file() else root_ / "index.html")
    rp, rr = f.resolve(), root_.resolve()
    if rr not in rp.parents or not f.is_file():
        raise AppEngineError("not found", 404)
    data = f.read_bytes()
    ext = f.suffix.lower()
    # v0.827 in the Studio the shell itself runs in a sealed (blank-origin) frame, so the preview app cannot demand a
    # same-origin parent; a LIVE app keeps frame-ancestors 'self' (its shell is the top page)
    # (no frame-ancestors at all: '*' does not match a blank-origin parent; the preview is reached only by its secret link)
    csp = CSP.replace(" frame-ancestors 'self';", "") if preview else (SITE_CSP if site else CSP)
    hdr = {"Content-Security-Policy": csp, "X-Content-Type-Options": "nosniff", "Referrer-Policy": "strict-origin-when-cross-origin",
           "Permissions-Policy": "camera=(), microphone=(), geolocation=()"}
    if ext == ".html":
        txt = _fill(data.decode("utf-8", "replace"), prefix, preview)
        txt = re.sub(r"<head>", f'<head>\n    <base href="{prefix}">', txt, count=1)
        if cloud:                                     # a site page reaches the PUBLIC Cloud calls itself (lib/hoola.ts)
            txt = txt.replace("</head>", f'    <meta name="hoola-cloud" content="{_esc(cloud)}">\n  </head>', 1)
        if preview:                                   # v0.825 the preview helper: errors, select, live style (never live)
            txt = txt.replace("</head>", '    <script src="__hoola/preview.js"></script>\n  </head>', 1)
        data = txt.encode("utf-8")
        hdr["Cache-Control"] = "no-store" if preview else ("public, max-age=60" if site else "no-store")
    elif ext in (".xml", ".txt"):
        data = _fill(data.decode("utf-8", "replace"), prefix, preview).encode("utf-8")
        hdr["Cache-Control"] = "no-store" if preview else "public, max-age=300"
        if ext == ".xml":
            hdr["Content-Type"] = "application/xml"
    else:
        hashed = "/assets/" in f"/{rel}" or f"/{rel}".startswith("/isl/")      # file names carry their content hash
        hdr["Cache-Control"] = "no-store" if preview else ("public, max-age=31536000, immutable" if hashed else "public, max-age=300")
    if preview:
        hdr["X-Robots-Tag"] = "noindex, nofollow"
    hdr["Access-Control-Allow-Origin"] = "*"        # the app runs in a sealed frame (a blank origin): its files load with CORS
    ctype = "application/xml" if ext == ".xml" else TYPES.get(ext, "application/octet-stream")
    hdr.pop("Content-Type", None)
    return data, ctype, hdr


def preview_file(token: str, path: str) -> tuple[bytes, str, dict[str, str]]:
    if not token or len(token) < 16:
        raise AppEngineError("not found", 404)
    ensure_table()
    with session() as s:
        r = s.scalars(select(AppProject).where(AppProject.preview_token == token)).first()
        if r is None:
            raise AppEngineError("not found", 404)
        s.expunge(r)
    v, rel = int(r.version or 0), path or ""
    m = re.match(r"^__v/(\d+)/?(.*)$", rel)
    if m:
        v, rel = int(m.group(1)), m.group(2)
    if not v or not (ver_dir(r, v) / "dist").exists():
        raise AppEngineError("not built yet", 404)
    prefix = f"/api/app-preview/{token}/" + (f"__v/{v}/" if m else "")
    if rel.endswith(".map"):                         # hidden maps stay on the server (the error collector reads them)
        raise AppEngineError("not found", 404)
    return _route(r, ver_dir(r, v) / "dist", rel, prefix, "preview")


def live_file(slug: str, path: str) -> tuple[bytes, str, dict[str, str]]:
    ensure_table()
    with session() as s:
        r = s.scalars(select(AppProject).where(AppProject.slug == slug)).first()
        if r is None or not r.live_version:
            raise AppEngineError("not found", 404)
        s.expunge(r)
    return _route(r, live_dir(r), (path or "").lstrip("/"), f"/apps/{r.slug}/", "live")


# ------------------------------------------------------------------ the turn's block (the app she is working on)

def prompt_block(tenant: str) -> str:
    from ..agent import turnmode as TM
    ref = TM.APP.get()
    if not ref:
        return ""
    try:
        r = _load(tenant, ref)
    except AppEngineError:
        return ""
    # v0.999.51 the kit's ~100 files stay as the template made them: named once (kit line), not file by file, so
    # her app's own files always fit the list; a kit file she changed is listed like any other
    kit_dirs = ("src/components/ui/", "src/components/effects/", "src/components/blocks/")

    def _as_template(path: str) -> bool:
        t = TEMPLATE / path
        try:
            return t.exists() and (src_dir(r) / path).read_bytes() == t.read_bytes()
        except OSError:
            return False
    files = [f["path"] + (" (locked)" if f["locked"] else "") for f in files_list(r)
             if f["path"] != "package-lock.json" and not f["path"].startswith(".hoola/")
             and not (f["path"].startswith(kit_dirs) and _as_template(f["path"]))][:80]
    try:
        from . import kit as KIT
        kit_line = KIT.prompt_line() + "\n"
    except Exception:                                # noqa: BLE001
        kit_line = ""
    try:
        agents = (src_dir(r) / "AGENTS.md").read_text()[:3000]
    except OSError:
        agents = ""
    try:
        lb = json.loads(r.last_build or "{}")
    except ValueError:
        lb = {}
    deps = sorted(set(json.loads((src_dir(r) / "package.json").read_text()).get("dependencies") or {}))
    state = ("not built yet" if not r.version else f"version {r.version}" + (" (newer changes not built yet)" if r.dirty else ""))
    if lb and not lb.get("ok"):
        state += "; the LAST BUILD FAILED - fix it first (app_engine action=logs)"
    try:
        from . import pick as PK
        state += PK.open_block(r)
    except Exception:                                # noqa: BLE001
        pass
    try:
        from . import cloud as CL
        state += CL.prompt_block(r)
    except Exception:                                # noqa: BLE001
        pass
    if r.branch_of:                                  # v0.978 a branch knows it is one
        from . import branches as BR
        state += "; " + BR.prompt_line(r)
    return (f"<app_engine_project>\nYou are working on App Engine app {r.number} \"{r.name}\" (app id {r.id}), a real "
            f"React 18 + TypeScript + Vite + Tailwind v4 app; {state}. Change it ONLY with the app_engine tool "
            "(view / search before you edit; edit_lines for small changes; write for a new file). Rules the tool "
            "enforces: colours / corners / fonts only from the tokens (bg surface ink muted line primary primary-ink "
            "accent ok warn bad; rounded-card rounded-control shadow-card font-head font-body) - never a hex colour, "
            "a Tailwind palette colour or a one-off [value]; change how a shared part looks in its cva variants in "
            "src/components/ui; packages only from the vetted list; no outside address (data comes through "
            "src/lib/hoola.ts, which is not connected yet - keep data on the page and say so). After changes, call "
            "action=build and read the result before you say it is done. Going live is HER tap in the Studio.\n"
            f"Packages: {', '.join(deps)}\nFiles: {', '.join(files)}\n{kit_line}AGENTS.md:\n{agents}\n</app_engine_project>")


def status() -> dict[str, Any]:
    return {"engine": RN.available(), "image": IMG.IMAGE, "image_rev_wanted": IMG.IMAGE_REV, "runner": RN.mode(),
            "previews_at_once": RN._GATE_N or int(getattr(RN._settings(), "app_engine_previews", 2) or 2),
            "stats": dict(RN.STATS), "vetted": sorted(IMG.VETTED), "palettes": list(TK.PALETTES)}
