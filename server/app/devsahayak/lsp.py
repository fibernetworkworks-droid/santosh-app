"""v0.999 CODE INTELLIGENCE, Claude Code's LSP tool (owner: "GO NEXT - CODE INTELLIGENCE (LSP)").

Claude Code talks to a language server (pyright, typescript-language-server, gopls, rust-analyzer, clangd ...) through one
`LSP` tool - goToDefinition, findReferences, hover, documentSymbol, workspaceSymbol, goToImplementation,
prepareCallHierarchy, incomingCalls, outgoingCalls - and hands the model the server's errors after it edits a file.
Servers come from plugins (`.lsp.json` / `lspServers`). Hoola Code does the same, with the house's walls:

- A language server READS AND RUNS the repo's code (TypeScript plugins from tsconfig, rust-analyzer build scripts,
  pyright's own config), so it runs only in the session's LOCKED BOX, with no network, like every command. A small
  driver in the box starts the server, does the LSP handshake (clientInfo "Hoola Code"), opens the file, sends ONE
  request (or waits for its diagnostics), prints the answer and shuts the server down.
- Where servers come from: the ones in the box image (pyright for Python, typescript-language-server for JS / TS,
  and gopls / rust-analyzer / clangd / jdtls when the repo's setup installed them); the repo's own `.lsp.json` (Claude
  Code's plugin format); her enabled plugins' `.lsp.json` / `lspServers`. A server the REPO or a plugin names is a
  program: she is asked before it starts the first time (as for a repo's MCP server).
- Places in node_modules / venv / site-packages are left out of references (Claude Code's fix too); a definition
  outside the repo is kept and labelled.
- After the coder edits files a server covers, the server checks them in the background and its errors and
  warnings arrive at the coder's next step (Claude Code's diagnostics after edits) - only problems, never "all fine".
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.devsahayak.lsp")
STATS = {"calls": 0, "diagnostics": 0, "no_server": 0, "failed": 0}

OPS = ("goToDefinition", "findReferences", "hover", "documentSymbol", "workspaceSymbol", "goToImplementation",
       "prepareCallHierarchy", "incomingCalls", "outgoingCalls", "diagnostics")

# the servers the box knows by itself: first command found on its PATH wins
BUILTIN: list[dict[str, Any]] = [
    {"name": "pyright", "candidates": [["pyright-langserver", "--stdio"], ["basedpyright-langserver", "--stdio"], ["pylsp"]],
     "ext": {".py": "python", ".pyi": "python"}},
    {"name": "typescript", "candidates": [["typescript-language-server", "--stdio"]],
     "ext": {".ts": "typescript", ".tsx": "typescriptreact", ".js": "javascript", ".jsx": "javascriptreact",
             ".mjs": "javascript", ".cjs": "javascript", ".mts": "typescript", ".cts": "typescript"}},
    {"name": "gopls", "candidates": [["gopls"]], "ext": {".go": "go"}},
    {"name": "rust-analyzer", "candidates": [["rust-analyzer"]], "ext": {".rs": "rust"}},
    {"name": "clangd", "candidates": [["clangd"]],
     "ext": {".c": "c", ".h": "c", ".cc": "cpp", ".cpp": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hh": "cpp"}},
    {"name": "jdtls", "candidates": [["jdtls"]], "ext": {".java": "java"}},
]

TOOL = {
    "name": "lsp",
    "description": (
        "Code intelligence from a language server, like Claude Code's LSP tool: it knows the code the way an editor does. "
        "goToDefinition / goToImplementation / findReferences / hover (the type and docs) / prepareCallHierarchy / "
        "incomingCalls / outgoingCalls take filePath + line + character (both from 1, the position of the symbol in the "
        "file as `read` shows it); documentSymbol takes filePath (every class / function in it); workspaceSymbol takes "
        "query (find a symbol anywhere); diagnostics takes filePath (the server's errors and warnings). Prefer it over "
        "grep when you need what a NAME really refers to (overloads, imports, renames). It is slow the first time "
        "(the server reads the project) - do not use it for plain text search."),
    "input_schema": {"type": "object", "properties": {
        "operation": {"type": "string", "enum": list(OPS)},
        "filePath": {"type": "string", "description": "the file, relative to the repo"},
        "line": {"type": "integer", "description": "1-based line"},
        "character": {"type": "integer", "description": "1-based column of the symbol"},
        "query": {"type": "string", "description": "workspaceSymbol: the name to look for"}},
        "required": ["operation"]},
}


def _set(name: str, default: Any) -> Any:
    try:
        from ..config import get_settings
        v = getattr(get_settings(), name, default)
        return default if v is None else v
    except Exception:  # noqa: BLE001
        return default


def on() -> bool:
    return bool(_set("dev_lsp", True))


# ---------------------------------------------------------------- where servers come from
def _from_file(f: Path, origin: str) -> list[dict[str, Any]]:
    """Claude Code's .lsp.json: {name: {command, args, extensionToLanguage, env, initializationOptions, settings,
    startupTimeout, requestTimeout}} (also accepted wrapped as {"lspServers": {...}})."""
    try:
        if f.is_symlink() or not f.is_file() or f.stat().st_size > 200_000:
            return []
        d = json.loads(f.read_text("utf-8"))
    except (OSError, ValueError):
        return []
    return _from_dict(d, origin)


def _from_dict(d: Any, origin: str) -> list[dict[str, Any]]:
    if isinstance(d, dict) and isinstance(d.get("lspServers"), dict):
        d = d["lspServers"]
    out = []
    for name, c in (d.items() if isinstance(d, dict) else []):
        if not isinstance(c, dict) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,60}", str(name)):
            continue
        cmd = str(c.get("command") or "").strip()
        ext = c.get("extensionToLanguage")
        if not cmd or not isinstance(ext, dict) or not ext:
            continue
        args = [str(a) for a in (c.get("args") or []) if isinstance(a, (str, int, float))][:30]
        exts = {str(k).lower() if str(k).startswith(".") else "." + str(k).lower(): str(v)[:40]
                for k, v in list(ext.items())[:40] if str(k).strip()}
        env = {str(k): str(v) for k, v in (c.get("env") or {}).items()
               if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,60}", str(k))} if isinstance(c.get("env"), dict) else {}
        out.append({"name": str(name), "candidates": [[cmd] + args], "ext": exts, "env": env, "origin": origin,
                    "init": c.get("initializationOptions") if isinstance(c.get("initializationOptions"), dict) else {},
                    "settings": c.get("settings") if isinstance(c.get("settings"), dict) else {},
                    "start_s": max(5, min(int(c.get("startupTimeout") or 120000) // 1000, 300)),
                    "req_s": max(5, min(int(c.get("requestTimeout") or 60000) // 1000, 300))})
    return out


def servers(repo: Path, tenant: str = "") -> list[dict[str, Any]]:
    """The repo's own first, then her plugins', then the box's (a repo naming a server for .py wins over pyright)."""
    out = _from_file(Path(repo) / ".lsp.json", "repo")
    if tenant:
        try:
            from . import plugins as PL
            for root in PL.roots(tenant):
                out += _from_file(root / ".lsp.json", "plugin:" + root.name)
                pj = root / ".claude-plugin" / "plugin.json"
                try:
                    m = json.loads(pj.read_text("utf-8")) if pj.is_file() else {}
                except (OSError, ValueError):
                    m = {}
                if isinstance(m.get("lspServers"), dict):
                    out += _from_dict(m["lspServers"], "plugin:" + root.name)
                elif isinstance(m.get("lspServers"), str):          # a path to its own .lsp.json inside the plugin
                    f = (root / m["lspServers"]).resolve()
                    if str(f).startswith(str(root.resolve()) + "/"):
                        out += _from_file(f, "plugin:" + root.name)
        except Exception:  # noqa: BLE001 - plugins never stop the tool
            pass
    for b in BUILTIN:
        out.append({**b, "origin": "builtin", "env": {}, "init": {}, "settings": {}, "start_s": 120, "req_s": 60})
    return out


def server_for(repo: Path, path: str, tenant: str = "", every: list | None = None) -> dict[str, Any] | None:
    ext = Path(str(path or "")).suffix.lower()
    for s in every if every is not None else servers(repo, tenant):
        if ext and ext in s["ext"]:
            return s
    return None


# ---------------------------------------------------------------- the driver that runs in the box
DRIVER = r'''
import json, os, queue, shutil, subprocess, sys, threading, time
from urllib.parse import quote, unquote
job = json.load(open(os.environ.get("HOOLA_LSP_JOB") or "/tmp/hoola_lsp.json"))
S = job["server"]
ROOT = os.path.realpath(os.getcwd())
SKIP = ("/node_modules/", "/.venv/", "/venv/", "/site-packages/", "/dist-packages/", "/.git/", "/__pycache__/", "/target/debug/", "/.tox/")
def out(d):
    print("HOOLA_LSP_RESULT " + json.dumps(d)); sys.stdout.flush()
argv = None
for c in S["candidates"]:
    if c and (shutil.which(c[0]) or os.path.isfile(c[0])):
        argv = c; break
if argv is None:
    out({"ok": False, "missing": [c[0] for c in S["candidates"]]}); sys.exit(0)
env = dict(os.environ); env.update(S.get("env") or {})
p = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=ROOT, env=env)
ERR = []
def _err():
    n = 0
    for ln in p.stderr:
        if n < 20000:
            ERR.append(ln.decode("utf-8", "replace")); n += len(ln)
threading.Thread(target=_err, daemon=True).start()
Q = queue.Queue()
def _read():
    f = p.stdout
    while True:
        head = {}
        while True:
            ln = f.readline()
            if not ln:
                Q.put(None); return
            ln = ln.strip()
            if not ln:
                break
            k, _, v = ln.decode("ascii", "replace").partition(":")
            head[k.strip().lower()] = v.strip()
        n = int(head.get("content-length") or 0)
        body = f.read(n) if n else b""
        try:
            Q.put(json.loads(body.decode("utf-8", "replace")))
        except ValueError:
            pass
threading.Thread(target=_read, daemon=True).start()
def send(o):
    b = json.dumps(o).encode("utf-8")
    p.stdin.write(b"Content-Length: %d\r\n\r\n" % len(b) + b); p.stdin.flush()
NID = [0]
DIAG = {}
DIAG_AT = [0.0]
def setting(section):
    cur = S.get("settings") or {}
    for part in (section or "").split(".") if section else []:
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur
def handle(m):
    if m is None:
        raise SystemExit("the server stopped")
    meth = m.get("method")
    if meth and "id" in m:
        res = None
        if meth == "workspace/configuration":
            res = [setting((it or {}).get("section")) for it in (m.get("params") or {}).get("items") or []]
        elif meth == "workspace/workspaceFolders":
            res = [{"uri": "file://" + quote(ROOT), "name": "work"}]
        send({"jsonrpc": "2.0", "id": m["id"], "result": res})
    elif meth == "textDocument/publishDiagnostics":
        pr = m.get("params") or {}
        DIAG[pr.get("uri")] = pr.get("diagnostics") or []
        DIAG_AT[0] = time.time()
def request(meth, params, timeout):
    NID[0] += 1; my = NID[0]
    send({"jsonrpc": "2.0", "id": my, "method": meth, "params": params})
    end = time.time() + timeout
    while time.time() < end:
        try:
            m = Q.get(timeout=max(0.05, end - time.time()))
        except queue.Empty:
            break
        if m is not None and m.get("id") == my and "method" not in m:
            if m.get("error"):
                raise RuntimeError(str((m["error"] or {}).get("message") or m["error"])[:400])
            return m.get("result")
        handle(m)
    raise TimeoutError(meth + " timed out after %ds" % timeout)
def pump(sec):
    end = time.time() + sec
    while time.time() < end:
        try:
            handle(Q.get(timeout=max(0.05, end - time.time())))
        except queue.Empty:
            return
def uri(rel):
    return "file://" + quote(os.path.join(ROOT, rel))
def rel_of(u):
    path = unquote(str(u or "")[7:]) if str(u or "").startswith("file://") else str(u or "")
    rp = os.path.realpath(path)
    return (os.path.relpath(rp, ROOT) if rp == ROOT or rp.startswith(ROOT + os.sep) else rp), rp
LINES = {}
def line_text(rp, n):
    if rp not in LINES:
        try:
            LINES[rp] = open(rp, encoding="utf-8", errors="replace").read().splitlines() if os.path.getsize(rp) < 3000000 else []
        except OSError:
            LINES[rp] = []
    L = LINES[rp]
    return L[n].strip()[:200] if 0 <= n < len(L) else ""
def loc(x):
    u = x.get("targetUri") or x.get("uri") or (x.get("location") or {}).get("uri")
    rg = x.get("targetSelectionRange") or x.get("range") or (x.get("location") or {}).get("range") or {}
    st = rg.get("start") or {}
    r, rp = rel_of(u)
    inside = not os.path.isabs(r)
    return {"path": r, "line": int(st.get("line", 0)) + 1, "col": int(st.get("character", 0)) + 1,
            "text": line_text(rp, int(st.get("line", 0))), "inside": inside,
            "skip": (not inside) and any(s in rp + "/" for s in SKIP) or any(s in "/" + r + "/" for s in SKIP)}
def locs(res):
    if res is None:
        return []
    return [loc(x) for x in (res if isinstance(res, list) else [res]) if isinstance(x, dict)]
def hover_text(h):
    c = (h or {}).get("contents")
    def one(v):
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            return str(v.get("value") or "")
        return ""
    if isinstance(c, list):
        return "\n\n".join(one(v) for v in c if one(v))
    return one(c)
def syms(res, depth=0, acc=None):
    acc = [] if acc is None else acc
    for s in res or []:
        if not isinstance(s, dict):
            continue
        rg = s.get("selectionRange") or s.get("range") or (s.get("location") or {}).get("range") or {}
        r = ""
        if s.get("location"):
            r = rel_of((s["location"] or {}).get("uri"))[0]
        acc.append({"name": s.get("name"), "kind": s.get("kind"), "line": int((rg.get("start") or {}).get("line", 0)) + 1,
                    "depth": depth, "path": r, "detail": str(s.get("detail") or s.get("containerName") or "")[:120]})
        if len(acc) < 600 and s.get("children"):
            syms(s["children"], depth + 1, acc)
    return acc
def item(it):
    rg = it.get("selectionRange") or it.get("range") or {}
    return {"name": it.get("name"), "kind": it.get("kind"), "path": rel_of(it.get("uri"))[0],
            "line": int((rg.get("start") or {}).get("line", 0)) + 1, "detail": str(it.get("detail") or "")[:120]}
result = {"ok": True, "server": argv[0]}
try:
    caps = (request("initialize", {
        "processId": os.getpid(), "clientInfo": {"name": "Hoola Code", "version": "1"},
        "rootUri": "file://" + quote(ROOT), "rootPath": ROOT,
        "workspaceFolders": [{"uri": "file://" + quote(ROOT), "name": "work"}],
        "initializationOptions": S.get("init") or {},
        "capabilities": {
            "textDocument": {"synchronization": {"didSave": True}, "definition": {"linkSupport": True},
                             "implementation": {"linkSupport": True}, "references": {}, "callHierarchy": {},
                             "hover": {"contentFormat": ["markdown", "plaintext"]},
                             "documentSymbol": {"hierarchicalDocumentSymbolSupport": True},
                             "publishDiagnostics": {"relatedInformation": False}, "diagnostic": {}},
            "workspace": {"symbol": {}, "configuration": True, "workspaceFolders": True},
            "window": {"workDoneProgress": False}}}, S.get("start_s", 120)) or {}).get("capabilities") or {}
    send({"jsonrpc": "2.0", "method": "initialized", "params": {}})
    if S.get("settings"):
        send({"jsonrpc": "2.0", "method": "workspace/didChangeConfiguration", "params": {"settings": S["settings"]}})
    files = job.get("files") or ([job["file"]] if job.get("file") else [])
    opened = []
    for f in files[:60]:
        fp = os.path.realpath(os.path.join(ROOT, f))
        if not fp.startswith(ROOT + os.sep) or not os.path.isfile(fp):
            continue
        try:
            text = open(fp, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        ext = os.path.splitext(f)[1].lower()
        send({"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {"textDocument": {
            "uri": uri(f), "languageId": (S.get("ext") or {}).get(ext, "plaintext"), "version": 1, "text": text}}})
        opened.append(f)
    if job.get("file") and job["file"] not in opened and job["op"] != "workspaceSymbol":
        raise RuntimeError("the file " + job["file"] + " is not in the working copy")
    op, T = job["op"], S.get("req_s", 60)
    pos = {"textDocument": {"uri": uri(job.get("file") or "")}, "position": {"line": job.get("line", 0), "character": job.get("char", 0)}}
    if op in ("goToDefinition", "goToImplementation"):
        result["locations"] = locs(request("textDocument/definition" if op == "goToDefinition" else "textDocument/implementation", pos, T))
    elif op == "findReferences":
        result["locations"] = locs(request("textDocument/references", {**pos, "context": {"includeDeclaration": True}}, T))
    elif op == "hover":
        result["hover"] = hover_text(request("textDocument/hover", pos, T))[:12000]
    elif op == "documentSymbol":
        result["symbols"] = syms(request("textDocument/documentSymbol", {"textDocument": pos["textDocument"]}, T))
    elif op == "workspaceSymbol":
        pump(1.0)
        result["symbols"] = syms(request("workspace/symbol", {"query": job.get("query") or ""}, T))[:200]
    elif op in ("prepareCallHierarchy", "incomingCalls", "outgoingCalls"):
        items = request("textDocument/prepareCallHierarchy", pos, T) or []
        result["items"] = [item(i) for i in items]
        if op != "prepareCallHierarchy" and items:
            calls = request("callHierarchy/" + op, {"item": items[0]}, T) or []
            key = "from" if op == "incomingCalls" else "to"
            result["calls"] = [item(c.get(key) or {}) for c in calls if isinstance(c, dict)][:200]
    elif op == "diagnostics":
        want = [uri(f) for f in opened]
        if caps.get("diagnosticProvider"):
            for f in opened:
                try:
                    r = request("textDocument/diagnostic", {"textDocument": {"uri": uri(f)}}, T) or {}
                    DIAG[uri(f)] = r.get("items") or []
                except Exception:
                    pass
        end = time.time() + float(job.get("diag_wait") or 25)
        while time.time() < end and not all(u in DIAG for u in want):
            pump(0.3)
        if DIAG_AT[0]:
            pump(0.8)                                   # a second, settled publish replaces the first
        result["diagnostics"] = {}
        for u in want:
            rows = []
            for d in DIAG.get(u) or []:
                st = ((d.get("range") or {}).get("start") or {})
                rows.append({"line": int(st.get("line", 0)) + 1, "col": int(st.get("character", 0)) + 1,
                             "sev": int(d.get("severity") or 1), "msg": str(d.get("message") or "")[:400],
                             "source": str(d.get("source") or "")[:40], "code": str(d.get("code") or "")[:40]})
            result["diagnostics"][rel_of(u)[0]] = rows[:200]
        result["waited_for"] = [rel_of(u)[0] for u in want if u not in DIAG]
except SystemExit as e:
    result = {"ok": False, "error": str(e)}
except Exception as e:
    result = {"ok": False, "error": e.__class__.__name__ + ": " + str(e)[:400]}
result["stderr"] = "".join(ERR)[-1500:]
try:
    request("shutdown", None, 5)
except Exception:
    pass
try:
    send({"jsonrpc": "2.0", "method": "exit", "params": None})
except Exception:
    pass
try:
    p.wait(3)
except Exception:
    p.kill()
out(result)
'''


def _exec(tools: Any, job: dict[str, Any], timeout: int) -> dict[str, Any]:
    """Run the driver in the session's box. One seam: the tests run it straight on this machine."""
    img, note = tools._image()
    if not img:
        return {"ok": False, "error": "the box is not available on this server right now" + (f" ({note.strip('[]')})" if note else "")}
    from ..devlab import box
    end = "HOOLA_LSP_" + uuid.uuid4().hex
    shell = (f"cd {box.WORK}; cat > /tmp/hoola_lsp.py <<'{end}'\n{DRIVER}\n{end}\n"
             f"cat > /tmp/hoola_lsp.json <<'{end}'\n{json.dumps(job)}\n{end}\npython3 /tmp/hoola_lsp.py")
    tools.bash_runs = getattr(tools, "bash_runs", 0) + 1
    r = box.run_in(img, str(tools.s.repo), shell, timeout=timeout, network=False, env=tools.env or None)
    return _parse(str(r.get("out") or ""), bool(r.get("timed_out")))


def _parse(out: str, timed_out: bool = False) -> dict[str, Any]:
    m = re.search(r"HOOLA_LSP_RESULT (\{.*\})\s*$", out, re.S)
    try:
        got = json.loads(m.group(1)) if m else None
    except ValueError:
        got = None
    if isinstance(got, dict):
        return got
    return {"ok": False, "error": ("the language server timed out" if timed_out else "the language server did not answer"),
            "stderr": out[-1200:]}


KIND = {1: "file", 2: "module", 3: "namespace", 4: "package", 5: "class", 6: "method", 7: "property", 8: "field",
        9: "constructor", 10: "enum", 11: "interface", 12: "function", 13: "variable", 14: "constant", 15: "string",
        16: "number", 17: "boolean", 18: "array", 19: "object", 20: "key", 21: "null", 22: "enum member", 23: "struct",
        24: "event", 25: "operator", 26: "type parameter"}
SEV = {1: "error", 2: "warning", 3: "info", 4: "hint"}


def _job(spec: dict[str, Any], op: str, **kw: Any) -> dict[str, Any]:
    srv = {k: spec.get(k) for k in ("candidates", "env", "init", "settings", "start_s", "req_s", "ext")}
    return {"server": srv, "op": op, **kw}


def _timeout(spec: dict[str, Any], extra: int = 30) -> int:
    return max(30, min(int(spec.get("start_s") or 120) + int(spec.get("req_s") or 60) + extra,
                       int(_set("dev_lsp_s", 300) or 300)))


def _missing_line(spec: dict[str, Any], ext: str, got: dict[str, Any]) -> str:
    names = ", ".join(got.get("missing") or [c[0] for c in spec["candidates"]])
    return (f"No language server for {ext} files in this box: {names} is not installed. Install it in this repo's setup "
            "command (Settings > Repos), or name another one in .lsp.json. Use grep / read meanwhile.")


def tool(tools: Any, inp: dict[str, Any]) -> str:
    """The coder's lsp call -> its answer as text."""
    op = str(inp.get("operation") or "")
    if op not in OPS:
        return "operation must be one of: " + ", ".join(OPS) + "."
    path = str(inp.get("filePath") or inp.get("path") or "").strip().lstrip("./") if (inp.get("filePath") or inp.get("path")) else ""
    rel = tools._rel(path) if path else ""
    every = servers(tools.s.repo, getattr(tools, "tenant", ""))
    if op == "workspaceSymbol" and not rel:
        q = str(inp.get("query") or "").strip()
        if not q:
            return "workspaceSymbol needs query (the name to look for)."
        spec = next((s for s in every if any(tools.s.real(p) and Path(p).suffix.lower() in s["ext"]
                                               for p in _sample(tools))), None)
        if spec is None:
            return "No language server knows this repo's files. Use grep instead."
        job = _job(spec, op, query=q, files=_mentions(tools, spec, q, ""))
    else:
        if not rel:
            return "Give filePath (the file, relative to the repo)."
        if rel in getattr(tools, "hidden", set()):
            return "Refused: this file holds secrets."
        spec = server_for(tools.s.repo, rel, every=every)
        if spec is None:
            STATS["no_server"] += 1
            return (f"No language server covers {Path(rel).suffix or 'this kind of'} files. Use grep / read instead, or name a "
                    "server for them in .lsp.json.")
        line, ch = int(inp.get("line") or 0), int(inp.get("character") or 0)
        if op not in ("documentSymbol", "diagnostics", "workspaceSymbol") and (line < 1 or ch < 1):
            return f"{op} needs line and character (both from 1) of the symbol in {rel}."
        files = [rel]
        if op in WIDE:                                     # the server answers from the files it has OPEN: open the ones
            files += _mentions(tools, spec, _word_at(tools, rel, line, ch), rel)   # that name the symbol (git grep)
        job = _job(spec, op, file=rel, line=max(0, line - 1), char=max(0, ch - 1), query=str(inp.get("query") or ""),
                   files=files, diag_wait=int(_set("dev_lsp_diag_wait_s", 25) or 25))
    STATS["calls"] += 1
    try:
        got = _exec(tools, job, _timeout(spec))
    except Exception as e:  # noqa: BLE001
        STATS["failed"] += 1
        return f"The language server could not run: {e.__class__.__name__}: {str(e)[:200]}"
    if not got.get("ok"):
        if got.get("missing"):
            STATS["no_server"] += 1
            return _missing_line(spec, Path(rel).suffix or "these", got)
        STATS["failed"] += 1
        return (f"The language server ({spec['name']}) failed: {got.get('error') or 'no answer'}"
                + (f"\nIts log:\n{_clean(got.get('stderr'))[-800:]}" if got.get("stderr") else ""))
    return render(op, got, rel, inp)


WIDE = ("findReferences", "incomingCalls", "goToImplementation", "workspaceSymbol")


def _word_at(tools: Any, rel: str, line: int, ch: int) -> str:
    """The identifier under line:character (1-based) of the file."""
    try:
        f = tools.s.real(rel)
        text = f.read_text("utf-8", errors="replace").splitlines()[line - 1] if f is not None else ""
    except (OSError, IndexError):
        return ""
    for m in re.finditer(r"[A-Za-z_$][A-Za-z0-9_$]*", text):
        if m.start() <= ch - 1 < m.end():
            return m.group(0)
    return ""


def _mentions(tools: Any, spec: dict[str, Any], word: str, skip: str) -> list[str]:
    """Files of this server's kinds that name `word` (git grep, whole word), so the server has them open."""
    if not word or len(word) < 2:
        return []
    from . import engine as EN
    globs = ["*" + e for e in spec["ext"]]
    rc, out = EN._git(tools.s.repo, "grep", "-l", "-w", "-I", "--untracked", "-e", word, "--", *globs)
    hidden = set(getattr(tools, "hidden", set()) or set())
    bad = ("node_modules/", ".venv/", "venv/", "site-packages/", "dist/", "build/", ".git/")
    got = [x for x in out.splitlines() if rc == 0 and x and x != skip and x not in hidden and not x.startswith(bad)]
    return got[:int(_set("dev_lsp_open_max", 40) or 40)]


def _sample(tools: Any) -> list[str]:
    try:
        return tools.s.walk()[:3000]
    except Exception:  # noqa: BLE001
        return []


def _clean(s: Any) -> str:
    try:
        from .engine import scrub
        return scrub(str(s or ""))
    except Exception:  # noqa: BLE001
        return str(s or "")


def _where(x: dict[str, Any]) -> str:
    return f"{x['path']}:{x['line']}:{x['col']}" + (f"  {x['text']}" if x.get("text") else "") + ("" if x.get("inside", True) else "  (outside the repo)")


def render(op: str, got: dict[str, Any], rel: str, inp: dict[str, Any]) -> str:
    at = f"{rel}:{inp.get('line')}:{inp.get('character')}" if inp.get("line") else rel
    if op in ("goToDefinition", "goToImplementation", "findReferences"):
        xs = got.get("locations") or []
        if op == "findReferences":
            dropped = [x for x in xs if x.get("skip")]
            xs = [x for x in xs if not x.get("skip")]
        else:
            dropped = []
        word = {"goToDefinition": "definition", "goToImplementation": "implementation", "findReferences": "reference"}[op]
        if not xs:
            return f"No {word} found for the symbol at {at}." + (" (Is the position on the symbol's name?)" if op != "findReferences" else "")
        head = f"{len(xs)} {word}{'s' if len(xs) != 1 else ''} of the symbol at {at}:"
        files = len({x["path"] for x in xs})
        if op == "findReferences":
            head = f"{len(xs)} reference{'s' if len(xs) != 1 else ''} in {files} file{'s' if files != 1 else ''} (symbol at {at}):"
        body = "\n".join("- " + _where(x) for x in xs[:150])
        more = f"\n... and {len(xs) - 150} more" if len(xs) > 150 else ""
        skip = f"\n({len(dropped)} in node_modules / virtualenvs / build folders left out)" if dropped else ""
        return head + "\n" + body + more + skip
    if op == "hover":
        h = str(got.get("hover") or "").strip()
        return f"At {at}:\n{h}" if h else f"Nothing to show at {at} (is the position on a name?)."
    if op in ("documentSymbol", "workspaceSymbol"):
        ss = got.get("symbols") or []
        if not ss:
            return "No symbols found." if op == "workspaceSymbol" else f"No symbols in {rel}."
        rows = []
        for s in ss[:400]:
            rows.append("  " * int(s.get("depth") or 0) + f"- {KIND.get(s.get('kind'), 'symbol')} {s.get('name')}"
                        + (f" ({s['detail']})" if s.get("detail") else "")
                        + (f" - {s['path']}:{s['line']}" if s.get("path") else f" - line {s['line']}"))
        return (f"Symbols in {rel}:" if op == "documentSymbol" else f"Symbols matching {inp.get('query')!r}:") + "\n" + "\n".join(rows)
    if op in ("prepareCallHierarchy", "incomingCalls", "outgoingCalls"):
        items = got.get("items") or []
        if not items:
            return f"No function or method at {at}."
        it = items[0]
        if op == "prepareCallHierarchy":
            return "\n".join(f"- {KIND.get(i.get('kind'), 'symbol')} {i.get('name')} - {i.get('path')}:{i.get('line')}" for i in items)
        cs = got.get("calls") or []
        word = "Called from" if op == "incomingCalls" else "Calls"
        if not cs:
            return f"{it.get('name')}: " + ("nothing calls it (that the server can see)." if op == "incomingCalls" else "it calls nothing the server can see.")
        return f"{word} ({it.get('name')}, {len(cs)}):\n" + "\n".join(f"- {KIND.get(c.get('kind'), 'symbol')} {c.get('name')} - {c.get('path')}:{c.get('line')}" for c in cs)
    if op == "diagnostics":
        rows = (got.get("diagnostics") or {}).get(rel)
        if rows is None and got.get("waited_for"):
            return f"The server did not report on {rel} in time."
        return diag_text(got.get("diagnostics") or {}, all_ok=True) or f"No problems in {rel}."
    return json.dumps(got)[:4000]


def diag_text(diags: dict[str, list[dict[str, Any]]], all_ok: bool = False, min_sev: int = 2) -> str:
    """Problems only (errors + warnings), the way Claude Code passes them on."""
    out, n = [], 0
    for path, rows in diags.items():
        bad = [r for r in rows if int(r.get("sev") or 1) <= min_sev]
        if not bad:
            continue
        out.append(f"{path}:")
        for r in bad[:25]:
            n += 1
            out.append(f"  {r['line']}:{r['col']} {SEV.get(int(r.get('sev') or 1), 'error')}: {r['msg']}"
                       + (f" [{r['source']}{' ' + r['code'] if r.get('code') else ''}]" if r.get("source") else ""))
        if len(bad) > 25:
            out.append(f"  ... and {len(bad) - 25} more")
    return "\n".join(out)


# ---------------------------------------------------------------- diagnostics after edits (in the background)
_PENDING: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()


def after_edits(tools: Any, paths: list[str], allowed: set[str] | None = None) -> bool:
    """The coder edited these files: a server checks them in the background; the result waits for its next step.
    Only servers she does not have to approve (the box's own, or ones she allowed) start on their own."""
    if not on() or not bool(_set("dev_lsp_diagnostics", True)):
        return False
    every = servers(tools.s.repo, getattr(tools, "tenant", ""))
    groups: dict[str, tuple[dict[str, Any], list[str]]] = {}
    for p in dict.fromkeys(paths):
        if not p or p in getattr(tools, "hidden", set()) or not (tools.s.repo / p).is_file():
            continue
        spec = server_for(tools.s.repo, p, every=every)
        if spec is None or (spec["origin"] != "builtin" and spec["name"] not in (allowed or set())):
            continue
        groups.setdefault(spec["name"], (spec, []))[1].append(p)
    if not groups:
        return False
    tid = str(getattr(tools.s, "tid", ""))
    rec = {"done": threading.Event(), "text": "", "files": [f for _, fs in groups.values() for f in fs], "at": time.time()}

    def run() -> None:
        parts = []
        for spec, fs in groups.values():
            try:
                got = _exec(tools, _job(spec, "diagnostics", files=fs[:20], diag_wait=int(_set("dev_lsp_diag_wait_s", 25) or 25)),
                            _timeout(spec))
            except Exception as e:  # noqa: BLE001
                log.info("lsp diagnostics failed: %s", e)
                continue
            if got.get("ok"):
                t = diag_text(got.get("diagnostics") or {})
                if t:
                    parts.append(t)
        rec["text"] = "\n".join(parts)
        STATS["diagnostics"] += 1
        rec["done"].set()
    import contextvars
    th = threading.Thread(target=contextvars.copy_context().run, args=(run,), name=f"dev-lsp-{tid}", daemon=True)
    with _LOCK:
        _PENDING[tid] = rec
    th.start()
    return True


def take(tid: str, wait: float = 0.0) -> str:
    """The diagnostics that came back for the coder's last edits ('' = none yet, or no problems)."""
    with _LOCK:
        rec = _PENDING.get(tid)
    if rec is None:
        return ""
    if not rec["done"].wait(max(0.0, wait)):
        return ""
    with _LOCK:
        _PENDING.pop(tid, None)
    if not rec["text"]:
        return ""
    return ("<new_diagnostics>\nThe language server found these problems in the files you just edited (they may be fixed "
            "by edits you have not made yet):\n" + rec["text"][:12000] + "\n</new_diagnostics>")


def forget(tid: str) -> None:
    with _LOCK:
        _PENDING.pop(tid, None)
