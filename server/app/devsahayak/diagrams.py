"""HOOLA DIAGRAM D4 (docs/DIAGRAM_TOOL_PLAN.md): the diagram tool inside Hoola Code.

The same engines as Hoola chat (app/diagram/service.py: archify, diagram-design, draw.io), with three things only a
coding session has:
  1. READ THE CODE FIRST - a diagram about her code names the files it is drawn from (`files`, and archify's own
     `sources` on each part); every one must be a file of this working copy that Hoola has READ in this session, or the
     draw is refused before any engine runs. The card shows those files. Nothing is written into her repo.
  2. CODE ANALYSIS - archify's own static analyser (modules/code-analysis: dependency cycles, hubs, layer leaks,
     complex functions) over the working copy: it reads files, never runs her code, hooks or package scripts.
  3. PR WALKTHROUGH - the same analyser comparing where this session started with the working copy now (what this
     change adds, removes and couples), on a snapshot commit that never moves her branch.
Each result is a card in "Made in this session" (devsahayak/made.py kinds diagram / analysis / review) that opens full
screen, with versions; nothing is posted in her chat."""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

ANALYSE_TIMEOUT = 300
MAX_FILES = 40
MAX_REPORT = 12_000_000           # archify's analysis page carries the captured source excerpts
LANGS = {"ts": (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts"), "py": (".py",), "java": (".java",),
         "go": (".go",), "rust": (".rs",)}
NEEDS = {"go": "go", "rust": "cargo"}          # these two compile archify's helper on the server; ts / py / java need node only
SKIP = {".git", "node_modules", "dist", "build", "target", "vendor", "venv", ".venv", "__pycache__", ".tox", "coverage"}

TOOL: dict[str, Any] = {
    "name": "diagram",
    "description": (
        "Draw a DIAGRAM of her code or her plan, checked by a real engine, shown as a card in her session (\"Made in "
        "this session\") that she opens full screen - the same engines as Hoola chat: archify for systems, flows and "
        "code (architecture, sequence, dataflow, lifecycle, erd, class, tree, workflow, timeline, waterfall - its code "
        "places every box and line), diagram-design for the other types, drawio when she wants to edit it by hand. "
        "READ THE CODE FIRST: a diagram about her code is drawn from files you have READ in this session - pass them in "
        "`files` (repo paths), and in archify put each part's file in its `sources`; a file you have not read is "
        "refused. STEPS: action=guide with type -> action=draw with type, title, content (archify JSON / the whole "
        "diagram-design page / draw.io cells) and files -> a failing check comes back with its problems: fix and draw "
        "again with the SAME diagram_id (3 rounds) -> a passing one comes back WITH A PICTURE: look at it, fix with "
        "action=update, then tell her in one or two sentences what it shows. action=analyze = archify's Code Analysis "
        "of the working copy (dependency cycles, hubs, layer leaks, complex functions; optional scope = a folder, "
        "language = ts|py|java|go|rust) - for architecture health / coupling / refactoring questions. action=pr = a "
        "walkthrough of THIS session's change (where it started vs now: what it adds, removes, couples). Both read "
        "files only and never run her code. read / change / editable / list work as in chat (draw.io: read first, then "
        "change id by id). Never write the diagram into the repo unless she asks for it in the repo."),
    "input_schema": {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["types", "guide", "draw", "update", "read", "change", "editable",
                                              "analyze", "pr", "list"]},
        "type": {"type": "string", "description": "guide / draw: the diagram type, e.g. architecture, sequence, workflow"},
        "engine": {"type": "string", "enum": ["archify", "diagram-design", "drawio"]},
        "title": {"type": "string", "description": "draw: a short name she will recognise, e.g. 'Login flow'"},
        "content": {"description": "draw / update: the WHOLE description (archify JSON, diagram-design page, draw.io cells)"},
        "files": {"type": "array", "items": {"type": "string"},
                  "description": "draw: the repo files (paths) this diagram is drawn from - each one READ in this session"},
        "not_about_code": {"type": "boolean", "description": "draw: true only when the diagram is not about her code "
                                                             "(a plan, a user journey) - then files may be empty"},
        "diagram_id": {"type": "string"}, "from_id": {"type": "string"},
        "ops": {"type": "array", "items": {"type": "object"}},
        "edits": {"type": "array", "items": {"type": "object", "properties": {"old_str": {"type": "string"},
                                                                               "new_str": {"type": "string"}},
                                             "required": ["old_str", "new_str"]}},
        "scope": {"type": "string", "description": "analyze / pr: a folder of the repo to look at (default: all of it)"},
        "language": {"type": "string", "enum": list(LANGS), "description": "analyze / pr: default = the repo's main one"}},
        "required": ["action"]}}

HOWTO = ("DIAGRAMS (the diagram tool): when she asks to SEE how something works - a diagram of the login flow, the "
         "architecture, the tables, a sequence - read the code it is about first (read / grep / code_map), then draw with "
         "diagram (guide -> draw with the files you read -> look at the picture -> fix). For 'is the architecture "
         "healthy', cycles, coupling or where to refactor: diagram action=analyze. To walk her through what this "
         "session changed: diagram action=pr. Each is a card she opens; say in one or two sentences what it shows. Do "
         "not put diagrams in the repo unless she asks for a file in the repo.")


def _settings():
    from ..config import get_settings
    return get_settings()


def on() -> bool:
    try:
        from ..diagram import service as S
        return bool(getattr(_settings(), "dev_diagram", True)) and S.on()
    except Exception:
        return False


def place(tid: str) -> str:
    from ..diagram import service as S
    return S.CODE_PLACE + tid


# ---------------------------------------------------------------- the picture the model looks at
def picture_block(path: str) -> dict[str, Any] | None:
    """A diagram's look (a JPEG under data/) as an image block - never as text."""
    try:
        f = Path(path).resolve()
        if not str(f).startswith(str(Path("data").resolve())) or not f.is_file() or f.stat().st_size > 3_000_000:
            return None
        mt = "image/png" if f.suffix.lower() == ".png" else "image/jpeg"
        return {"type": "image", "source": {"type": "base64", "media_type": mt, "data": base64.b64encode(f.read_bytes()).decode()}}
    except OSError:
        return None


# ---------------------------------------------------------------- read the code first
def _sources(content: Any) -> list[str]:
    """archify's per-part `sources` paths (and its meta.repository files), wherever they sit in the description."""
    try:
        d = json.loads(content) if isinstance(content, str) else content
    except (TypeError, ValueError):
        return []
    out: list[str] = []

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                if k == "sources" and isinstance(v, list):
                    out.extend(str(s.get("path")) for s in v if isinstance(s, dict) and s.get("path"))
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(d)
    return out


def unread(tools: Any, paths: list[str]) -> tuple[list[str], list[str]]:
    """(the files as repo paths, the ones that are not a READ file of this working copy)."""
    rels, bad = [], []
    for p in paths:
        try:
            rel = tools._rel(str(p))
        except Exception:
            rel = ""
        f = tools.s.real(rel) if rel else None
        if not rel or f is None or not f.is_file() or rel not in tools.read:
            bad.append(str(p))
        elif rel not in rels:
            rels.append(rel)
    return rels, bad


# ---------------------------------------------------------------- the tool
def tool(tools: Any, tid: str, tenant: str, inp: dict[str, Any]) -> tuple[str, dict[str, Any] | None, dict[str, Any] | None]:
    """(what the model reads back, a picture block or None, the session event or None). Never raises."""
    from ..diagram import service as S
    act = str(inp.get("action") or "").strip().lower()
    try:
        if act == "types":
            return "\n".join(f"{t['type']} ({t['engine']}): {t['use']}" for t in S.catalogue()), None, None
        if act == "guide":
            if not inp.get("type"):
                return "guide needs type (action=types lists them).", None, None
            g = S.guide(str(inp["type"]), str(inp.get("engine") or ""))
            return (g.get("guide") if g.get("ok") else g.get("error", "No such type.")) or "", None, None
        if act == "list":
            rows = [r for r in _made_rows(tid) if r["kind"] in ("diagram", "analysis", "review")]
            return ("Nothing drawn in this session yet." if not rows else "\n".join(
                f"{(r.get('extra') or {}).get('diagram_id') or r['id']}: {r['kind_label']} '{r['title']}' v{r['version']}"
                for r in rows)), None, None
        if act == "analyze":
            return analyze(tools, tid, inp)
        if act == "pr":
            return review(tools, tid, inp)
        if act in ("draw", "update", "read", "change", "editable"):
            return _diagram(tools, tid, tenant, act, inp)
        return "action must be types, guide, draw, update, read, change, editable, analyze, pr or list.", None, None
    except Exception as e:  # noqa: BLE001 - one bad call never ends the round
        return f"diagram could not do that ({e.__class__.__name__}: {str(e)[:200]}).", None, None


def _made_rows(tid: str) -> list[dict[str, Any]]:
    from . import made as MD
    return MD.listing(tid)


def _mine(tenant: str, tid: str, did: str) -> bool:
    from ..diagram import service as S
    m = S._meta(tenant, did)
    return bool(m) and S.code_task(m) == tid


def _diagram(tools: Any, tid: str, tenant: str, act: str, inp: dict[str, Any]):
    from ..diagram import service as S
    did = str(inp.get("diagram_id") or "")
    if did and not _mine(tenant, tid, did):
        return f"No diagram {did} in this session (diagram action=list shows them).", None, None
    if act == "read":
        return _said(S.read(tenant, did)) if did else ("read needs diagram_id.", None, None)
    if act == "editable":
        return _said(S.editable(tenant, did)) if did else ("editable needs diagram_id.", None, None)
    if act == "change":
        if not did or not isinstance(inp.get("ops"), list):
            return "change needs diagram_id and ops - call action=read first.", None, None
        return _said(S.change(tenant, "", did, inp["ops"]))
    if act == "update":
        if not did:
            return "update needs diagram_id.", None, None
        if inp.get("content") not in (None, ""):
            _, bad = unread(tools, _sources(inp.get("content")))
            if bad:
                return "Not changed: read these files first - " + ", ".join(bad[:12]) + ".", None, None
        roots: list[str] = []

        def prep(c: Any) -> Any:
            new, root = _pin(tools, tid, c)
            if root:
                roots.append(root)
            return new
        try:
            return _said(S.update(tenant, "", did, inp.get("edits"), inp.get("content"), str(inp.get("title") or ""),
                                  repo_root="", prepare=prep, root_of=lambda: roots[-1] if roots else ""))
        finally:
            for r_ in roots:
                shutil.rmtree(r_, ignore_errors=True)
    # draw
    if inp.get("content") in (None, ""):
        return "draw needs content: the whole description (read action=guide for the type first).", None, None
    if not inp.get("type") and not did:
        return "draw needs type (or diagram_id for a fix round).", None, None
    from_id = str(inp.get("from_id") or "")
    if from_id and not _mine(tenant, tid, from_id):
        return f"No diagram {from_id} in this session.", None, None
    files = [str(x) for x in (inp.get("files") or []) if str(x).strip()][:MAX_FILES]
    srcs = _sources(inp.get("content"))
    if not files and not srcs and not did and not from_id and not inp.get("not_about_code"):
        return ("Read the code first: pass `files` - the repo files this diagram is drawn from, each one read in this "
                "session (read / grep). Only a diagram that is not about her code (a plan, a journey) goes without them: "
                "then say not_about_code=true."), None, None
    rels, bad = unread(tools, files + srcs)
    if bad:
        return ("Not drawn: read these files first, then draw again - " + ", ".join(bad[:12])
                + ". A diagram of her code shows only what you have read in this working copy."), None, None
    pinned, root = _pin(tools, tid, inp.get("content"))
    try:
        out = S.draw(tenant, "", str(inp.get("type") or ""), str(inp.get("title") or ""), pinned,
                     str(inp.get("engine") or ""), did, from_id, place=place(tid),
                     files=rels if (files or srcs) else None, repo_root=root)
    finally:
        if root:
            shutil.rmtree(root, ignore_errors=True)
    return _said(out)


def _pin(tools: Any, tid: str, content: Any) -> tuple[Any, str]:
    """(the description, the evidence repo or ""). An archify description that cites her files gets THIS working copy
    pinned in meta.repository - a snapshot commit of the files as they are now (her branch never moves) - and a small
    throwaway evidence repo (its objects are the working copy's, by git alternates; its origin = the repo's name) is
    made for archify, which checks every cited path + line range at that commit. The model never writes this part:
    only Hoola knows which bytes it read."""
    if not _sources(content):
        return content, ""
    try:
        d = json.loads(content) if isinstance(content, str) else dict(content)
    except (TypeError, ValueError):
        return content, ""
    if not isinstance(d.get("meta"), dict):
        return content, ""
    sha = snapshot(tools.s.repo)
    if not sha:
        return content, ""
    url = "https://github.com/" + (str(tools.s.meta.get("repo") or "") or "local/repo")
    root = Path(tempfile.mkdtemp(prefix="hoola-ev-", dir=str(_work(tid))))
    from . import engine as EN
    env = EN._git_env()
    ok = True
    for a_ in (["init", "-q"], ["remote", "add", "origin", url]):
        ok = ok and subprocess.run(["git", "-C", str(root), *EN.GIT_SAFE, *a_], capture_output=True, env=env,
                                   timeout=30).returncode == 0
    if ok:
        (root / ".git" / "objects" / "info").mkdir(parents=True, exist_ok=True)
        (root / ".git" / "objects" / "info" / "alternates").write_text(
            str((tools.s.repo / ".git" / "objects").resolve()) + "\n")
        ok = subprocess.run(["git", "-C", str(root), *EN.GIT_SAFE, "update-ref", "refs/heads/main", sha],
                            capture_output=True, env=env, timeout=30).returncode == 0
    if not ok:
        shutil.rmtree(root, ignore_errors=True)
        return content, ""
    d["meta"]["repository"] = {"url": url, "link_mode": "local-only", "revision": sha}
    return d, str(root)


def _said(out: dict[str, Any]):
    pic = picture_block(out.pop("_look", "")) if out.get("_look") else None
    out.pop("editor", None)                      # her editor link is on the card, never in the model's context
    ev = None
    if out.get("ok") and out.get("made_id"):
        ev = {"k": "made", "id": out["made_id"], "v": out.get("version") or 1, "kind": "diagram",
              "title": out.get("title", "")}
    text = json.dumps(out, ensure_ascii=False)[:60000]
    if pic:
        text += "\nThe picture of the diagram is attached below - look at it."
    return text, pic, ev


# ---------------------------------------------------------------- Code Analysis + PR walkthrough (archify's analyser)
def _language(repo: Path, scope: str, want: str) -> tuple[str, str]:
    if want:
        if want not in LANGS:
            return "", f"language must be one of {', '.join(LANGS)}."
        if want in NEEDS and not shutil.which(NEEDS[want]):
            return "", f"{want} analysis needs {NEEDS[want]} on the server, which is not installed."
        return want, ""
    count = {k: 0 for k in LANGS}
    seen = 0
    for d, dirs, names in os.walk(repo / scope if scope else repo):
        dirs[:] = [x for x in dirs if x not in SKIP and not x.startswith(".")]
        for n in names:
            seen += 1
            for k, exts in LANGS.items():
                if n.endswith(exts):
                    count[k] += 1
        if seen > 50000:
            break
    order = sorted((c, k) for k, c in count.items() if c and (k not in NEEDS or shutil.which(NEEDS[k])))
    if not order:
        return "", ("No code archify reads here (JavaScript / TypeScript, Python, Java" +
                    ", Go" * bool(shutil.which("go")) + ", Rust" * bool(shutil.which("cargo")) + ").")
    return order[-1][1], ""


def _scope(tools: Any, scope: str) -> tuple[str, str]:
    if not scope.strip() or scope.strip() in (".", "/"):
        return "", ""
    rel = tools._rel(scope)
    if not rel or not (tools.s.repo / rel).is_dir() or os.path.islink(tools.s.repo / rel):
        return "", f"No folder '{scope}' in the working copy."
    return rel, ""


def _env() -> dict[str, str]:
    from ..diagram import runners as R
    env = dict(R._env())
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_COUNT": "3",
                "GIT_CONFIG_KEY_0": "core.fsmonitor", "GIT_CONFIG_VALUE_0": "false",
                "GIT_CONFIG_KEY_1": "core.hooksPath", "GIT_CONFIG_VALUE_1": "/dev/null",
                "GIT_CONFIG_KEY_2": "core.pager", "GIT_CONFIG_VALUE_2": "cat"})
    return env


def run_analysis(repo: Path, out: Path, language: str, scope: str = "", base: str = "", head: str = "") -> dict[str, Any]:
    """archify's `code-analysis prepare` (static: reads files and git objects, never runs the project)."""
    from ..diagram import runners as R
    from ..diagram import vendor as V
    node = R.node_bin()
    if not node:
        return {"ok": False, "said": "Code analysis needs Node.js 18+ on the server (vps-ops diagram_setup)."}
    cmd = [node, str(V.ARCHIFY / "bin" / "archify.mjs"), "code-analysis", "prepare", str(Path(repo).resolve()),
           "--out", str(Path(out).resolve()),
           "--language", language, "--locale", "en"]
    if scope:
        cmd += ["--scope", scope]
    if base and head:
        cmd += ["--base", base, "--head", head]
    t0 = time.monotonic()
    try:
        p = subprocess.run(cmd, cwd=str(V.ARCHIFY), env=_env(), capture_output=True, text=True, timeout=ANALYSE_TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"ok": False, "said": f"The analysis took longer than {ANALYSE_TIMEOUT // 60} minutes - try a smaller scope."}
    rec = R._last_json(p.stdout or "") or {}
    secs = round(time.monotonic() - t0, 1)
    html = Path(str(rec.get("html") or ""))
    if p.returncode != 0 or rec.get("status") != "ok" or not html.is_file():
        err = (rec.get("error") or rec.get("message") or (p.stderr or p.stdout or "")[-600:]).strip()
        return {"ok": False, "said": "The analysis did not finish: " + re.sub(r"/\S+/", "", str(err))[:500], "secs": secs}
    page = html.read_text("utf-8")
    for real, shown in ((str(Path(out).resolve()), "out"), (str(Path(repo).resolve()), "your-repo"),
                        (str(V.ARCHIFY.resolve()), "archify"), (str(Path("data").resolve()), "data")):
        page = page.replace(real, shown)                 # the server's own folders never reach her page
    return {"ok": True, "page": page, "summary": rec.get("summary") or {}, "secs": secs}


def _facts(summary: dict[str, Any]) -> dict[str, Any]:
    cov = summary.get("coverage") or {}
    counts = summary.get("counts") or {}
    leads = [{k: x.get(k) for k in ("code", "severity", "message", "where")} for x in (summary.get("leads") or [])[:8]]
    return {"counts": {k: counts.get(k) for k in ("findings", "error", "warning", "info")},
            "files": (cov.get("files") or {}).get("analyzed"), "parse_errors": len((cov.get("files") or {}).get("parseErrors") or []),
            "rules_run": (cov.get("rules") or {}).get("run") or [], "other_languages": cov.get("otherLanguages") or [],
            "unresolved": cov.get("unresolved") or {}, "leads": leads}


def _keep_page(tid: str, kind: str, title: str, page: str, line: str, mid: str, extra: dict[str, Any], big: bool):
    from . import made as MD
    if len(page) > MAX_REPORT:
        raise ValueError("the report is too large to keep - try a smaller scope")
    return MD.keep_built(tid, kind, title, page, {"line": line}, mid=mid, note=line, extra=extra,
                         cap=MAX_REPORT if big else 0)


def analyze(tools: Any, tid: str, inp: dict[str, Any]):
    repo = tools.s.repo
    scope, err = _scope(tools, str(inp.get("scope") or ""))
    if err:
        return err, None, None
    lang, err = _language(repo, scope, str(inp.get("language") or ""))
    if err:
        return err, None, None
    out = Path(tempfile.mkdtemp(prefix="hoola-ca-", dir=str(_work(tid))))
    try:
        res = run_analysis(repo, out, lang, scope)
        if not res["ok"]:
            return res["said"], None, None
        f = _facts(res["summary"])
        c = f["counts"]
        line = (f"{f['files']} files ({lang}) · {c.get('error') or 0} errors, {c.get('warning') or 0} warnings, "
                f"{c.get('info') or 0} notes")
        row = _keep_page(tid, "analysis", "Code analysis" + (f" · {scope}" if scope else ""),
                         res["page"], line, (_find(tid, "analysis", scope) or {}).get("id", ""),
                         {"what": "analysis", "scope": scope, "language": lang, "counts": c, "leads": f["leads"]},
                         len(res["page"]) > 3_000_000)
    finally:
        shutil.rmtree(out, ignore_errors=True)
    said = {"ok": True, "card": row["id"], "version": row["version"], "language": lang, "scope": scope or "(whole repo)",
            "seconds": res["secs"], **f,
            "said": ("Code Analysis is on her card (it opens the full report: the map, each finding with its source). A "
                     "zero means zero among the rules that ran (rules_run); say the one or two findings that matter most, "
                     "in plain words, and that a finding is a lead to check, not a proven bug. Never claim a fix from it.")}
    return json.dumps(said, ensure_ascii=False)[:30000], None, {"k": "made", "id": row["id"], "v": row["version"],
                                                               "kind": "analysis", "title": row["title"]}


def _find(tid: str, what: str, scope: str) -> dict[str, Any] | None:
    from . import made as MD
    for r in MD.listing(tid):
        m = MD._meta(tid, r["id"]) or {}
        x = m.get("extra") or {}
        if m.get("kind") in MD.BUILT and x.get("what") == what and str(x.get("scope") or "") == scope:
            return m
    return None


def snapshot(repo: Path) -> str:
    """A commit of the working tree as it is now, made with a private index: her branch, HEAD and index never move."""
    from . import engine as EN
    with EN._git_lock(repo):
        env = EN._git_env()
        fd, idx = tempfile.mkstemp(prefix="hoola-idx-")
        os.close(fd)
        os.unlink(idx)
        env["GIT_INDEX_FILE"] = idx

        def g(*a: str) -> tuple[int, str]:
            p = subprocess.run(["git", "-C", str(repo), *EN.GIT_SAFE, *a], capture_output=True, text=True, timeout=120,
                               env=env)
            return p.returncode, (p.stdout or "").strip()
        try:
            if g("read-tree", "HEAD")[0] != 0 or g("add", "-A")[0] != 0:
                return ""
            rc, tree = g("write-tree")
            if rc != 0:
                return ""
            rc, sha = g("commit-tree", tree, "-p", "HEAD", "-m", "hoola: the working copy for a PR walkthrough")
            return sha if rc == 0 and re.fullmatch(r"[0-9a-f]{40}", sha) else ""
        finally:
            Path(idx).unlink(missing_ok=True)


def review(tools: Any, tid: str, inp: dict[str, Any]):
    repo = tools.s.repo
    base = str(tools.s.meta.get("base") or "")
    if not re.fullmatch(r"[0-9a-f]{40}", base):
        return "This session has no starting point recorded yet - open the working copy first.", None, None
    changed = tools.s.changed(base)
    if not changed:
        return "Nothing has changed in this session yet, so there is no change to walk through.", None, None
    scope, err = _scope(tools, str(inp.get("scope") or ""))
    if err:
        return err, None, None
    lang, err = _language(repo, scope, str(inp.get("language") or ""))
    if err:
        return err, None, None
    head = snapshot(repo)
    if not head:
        return "The working copy could not be captured for the walkthrough (git).", None, None
    out = Path(tempfile.mkdtemp(prefix="hoola-pr-", dir=str(_work(tid))))
    try:
        res = run_analysis(repo, out, lang, scope, base=base, head=head)
        if not res["ok"]:
            return res["said"], None, None
        f = _facts(res["summary"])
        page = res["page"]
        line = f"{len(changed)} files changed · {f['counts'].get('error') or 0} errors in the new code"
        row = _keep_page(tid, "review", "PR walkthrough" + (f" · {scope}" if scope else ""), page, line,
                         (_find(tid, "review", scope) or {}).get("id", ""),
                         {"what": "review", "scope": scope, "language": lang, "counts": f["counts"], "leads": f["leads"],
                          "base": base[:12], "head": head[:12], "changed_files": [c["path"] for c in changed][:60]},
                         len(page) > 3_000_000)
    finally:
        shutil.rmtree(out, ignore_errors=True)
    said = {"ok": True, "card": row["id"], "version": row["version"], "changed_files": [c["path"] for c in changed][:60],
            "language": lang, "seconds": res["secs"], **f,
            "said": ("The PR walkthrough is on her card: where this session started vs the working copy now - added, "
                     "changed and removed parts, new or removed dependencies, and the direct callers of what changed. "
                     "Walk her through it in a few plain sentences, biggest change first. A change is not a proven "
                     "behaviour change and an existing finding is not caused by this change unless the report says so.")}
    return json.dumps(said, ensure_ascii=False)[:30000], None, {"k": "made", "id": row["id"], "v": row["version"],
                                                               "kind": "review", "title": row["title"]}


def _work(tid: str) -> Path:
    from . import made as MD
    d = MD._tdir(tid).parent / "_work"
    d.mkdir(parents=True, exist_ok=True)
    return d
