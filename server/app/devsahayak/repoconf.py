"""v0.999 THE REPO'S OWN CLAUDE CODE SETUP, read by Hoola Code (owner: "NOW CHECK HOOLA CODE IS 100% SAME AS CLAUDE CODE"
-> the gaps -> "GO ALL").

A repo that already works with Claude Code carries its setup in `.claude/`; Hoola Code now honours the same files:
  * `.claude/commands/<name>.md`  her custom slash commands: `/name args` in her message becomes the file's text, with
    $ARGUMENTS (and $1, $2...) filled in. A command's `!`shell`` lines are NOT run (they stay as text).
  * `.claude/agents/<name>.md`    the repo's own subagents (frontmatter name / description / tools + the prompt), beside
    Hoola's built-in ones.
  * `.claude/settings.json`       `permissions.allow / ask / deny` rules (Bash(npm run test:*), Read(./.env), Edit(src/**),
    WebFetch(domain:x)...) - deny refuses the step, ask makes it wait for her yes in any mode, allow lets it run without
    asking in 'Ask each step' - and `hooks` (PreToolUse / PostToolUse / UserPromptSubmit / SessionStart / Stop): each
    hook command runs IN THE LOCKED BOX (never on Hoola's server) with the event as JSON on its stdin; exit code 2 blocks
    (PreToolUse, Stop) or tells the model (PostToolUse) with what it printed.
  * `@path/to/file` in her message: that file's text rides along (cut at 60 KB a file, 5 files).
`.hoola/` is read the same way when a repo wants Hoola-only settings. Files that hold secrets stay hidden as before.
Nothing here can widen the box's walls: hooks run with no network and no secret, like any other command."""
from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path
from typing import Any

DIRS = (".claude", ".hoola")
TOOL_NAMES = {"bash": "Bash", "read": "Read", "write": "Write", "edit": "Edit", "multi_edit": "Edit", "glob": "Glob",
              "grep": "Grep", "ls": "LS", "web_fetch": "WebFetch", "web_search": "WebSearch", "notebook_edit": "NotebookEdit",
              "todo_write": "TodoWrite", "agent": "Task", "mcp": "mcp"}
HOOK_EVENTS = ("PreToolUse", "PostToolUse", "UserPromptSubmit", "SessionStart", "Stop")
MENTION = re.compile(r"(?<![\w/])@((?:[\w.-]+/)*[\w.-]+\.[\w]+|(?:[\w.-]+/)+[\w.-]+)")
MENTION_MAX = 5
MENTION_CHARS = 60_000


def _read(p: Path, cap: int = 200_000) -> str:
    try:
        return p.read_bytes()[:cap].decode("utf-8", errors="replace")
    except OSError:
        return ""


def front(text: str) -> tuple[dict[str, str], str]:
    """A markdown file's frontmatter (simple key: value lines) and its body."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text or "", re.S)
    if not m:
        return {}, text or ""
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        k, sep, v = line.partition(":")
        if sep and k.strip():
            meta[k.strip().lower()] = v.strip().strip("\"'")
    return meta, m.group(2)


# ---------------------------------------------------------------- settings (permissions + hooks)
def settings(repo: Path) -> dict[str, Any]:
    """permissions {allow, ask, deny} + hooks {event: [{matcher, commands}]}, merged from .claude/ and .hoola/."""
    out: dict[str, Any] = {"allow": [], "ask": [], "deny": [], "hooks": {}}
    for d in DIRS:
        for name in ("settings.json", "settings.local.json"):
            raw = _read(Path(repo) / d / name, 400_000)
            if not raw.strip():
                continue
            try:
                j = json.loads(raw)
            except ValueError:
                continue
            perm = j.get("permissions") if isinstance(j, dict) else None
            for k in ("allow", "ask", "deny"):
                for r in (perm or {}).get(k) or [] if isinstance(perm, dict) else []:
                    if isinstance(r, str) and r.strip():
                        out[k].append(r.strip()[:300])
            hooks = j.get("hooks") if isinstance(j, dict) else None
            for ev, groups in (hooks or {}).items() if isinstance(hooks, dict) else []:
                if ev not in HOOK_EVENTS or not isinstance(groups, list):
                    continue
                for g in groups:
                    if not isinstance(g, dict):
                        continue
                    cmds = [str(h.get("command") or "")[:2000] for h in g.get("hooks") or []
                            if isinstance(h, dict) and str(h.get("type") or "command") == "command" and h.get("command")]
                    if cmds:
                        out["hooks"].setdefault(ev, []).append({"matcher": str(g.get("matcher") or ""), "commands": cmds[:5],
                                                                "timeout": int(next((h.get("timeout") for h in g.get("hooks") or []
                                                                                     if isinstance(h, dict) and h.get("timeout")), 60) or 60)})
    return out


def _clean(path: str) -> str:
    """'./src/a.py' -> 'src/a.py', '.env' stays '.env' (lstrip('./') would eat the dot of a dotfile)."""
    while path.startswith("./"):
        path = path[2:]
    return path.lstrip("/")


def _claude_name(tool: str) -> str:
    return TOOL_NAMES.get(tool, tool)


def _rule_parts(rule: str) -> tuple[str, str | None]:
    m = re.match(r"^([\w.\-*]+)(?:\((.*)\))?$", rule.strip(), re.S)
    return (m.group(1), m.group(2)) if m else (rule.strip(), None)


def rule_matches(rule: str, tool: str, inp: dict[str, Any]) -> bool:
    """One Claude Code permission rule against one Hoola tool call."""
    name, spec = _rule_parts(rule)
    cname = _claude_name(tool)
    if tool == "mcp":                                    # mcp__server__tool / mcp__server
        if not name.startswith("mcp__"):
            return False
        parts = name.split("__")
        srv, tl = str(inp.get("pack_id") or ""), str(inp.get("tool") or "")
        return (len(parts) >= 2 and parts[1] in (srv, srv.replace("mcp-", ""))) and (len(parts) < 3 or parts[2] in ("*", tl))
    if name not in (cname, "*"):
        return False
    if spec is None or spec in ("", "*"):
        return True
    if cname == "Bash":
        cmd = " ".join(str(inp.get("command") or "").split())
        if spec.endswith(":*"):
            return cmd == spec[:-2] or cmd.startswith(spec[:-2] + " ") or cmd.startswith(spec[:-2])
        return cmd == spec.strip()
    if cname == "WebFetch":
        if spec.startswith("domain:"):
            host = re.sub(r"^https?://", "", str(inp.get("url") or "")).split("/")[0].split(":")[0].lower()
            want = spec[7:].lower()
            return host == want or host.endswith("." + want)
        return False
    path = _clean(str(inp.get("path") or inp.get("pattern") or ""))
    pat = spec.strip()
    for pre in ("//", "~/", "./", "/"):
        if pat.startswith(pre):
            pat = pat[len(pre):]
            break
    return fnmatch.fnmatch(path, pat) or fnmatch.fnmatch(path, pat.rstrip("/") + "/*") or path == pat


def decide(conf: dict[str, Any], tool: str, inp: dict[str, Any]) -> str:
    """'deny' | 'ask' | 'allow' | '' - deny wins over ask, ask over allow (Claude Code's order)."""
    for kind in ("deny", "ask", "allow"):
        if any(rule_matches(r, tool, inp if isinstance(inp, dict) else {}) for r in conf.get(kind) or []):
            return kind
    return ""


def hooks_for(conf: dict[str, Any], event: str, tool: str = "") -> list[tuple[str, int]]:
    """The commands to run for this event (and tool): (command, timeout seconds)."""
    out: list[tuple[str, int]] = []
    cname = _claude_name(tool) if tool else ""
    for g in (conf.get("hooks") or {}).get(event) or []:
        m = g.get("matcher") or ""
        if tool and m not in ("", "*"):
            try:
                if not re.fullmatch(m, cname) and not re.fullmatch(m, tool):
                    continue
            except re.error:
                if m not in (cname, tool):
                    continue
        out += [(c, max(1, min(int(g.get("timeout") or 60), 300))) for c in g["commands"]]
    return out[:8]


def hook_input(event: str, tid: str, tool: str = "", inp: dict[str, Any] | None = None, out: str = "",
               prompt: str = "") -> dict[str, Any]:
    j: dict[str, Any] = {"session_id": tid, "hook_event_name": event, "cwd": "/work"}
    if tool:
        j["tool_name"] = _claude_name(tool)
        j["tool_input"] = {k: v for k, v in (inp or {}).items() if not str(k).startswith("_")}
    if event == "PostToolUse":
        j["tool_response"] = out[:20000]
    if prompt:
        j["prompt"] = prompt[:20000]
    return j


# ---------------------------------------------------------------- custom slash commands
def commands(repo: Path) -> dict[str, dict[str, str]]:
    """{name: {description, hint, body, path}} from .claude/commands/**/*.md (+ .hoola/commands)."""
    out: dict[str, dict[str, str]] = {}
    for d in DIRS:
        base = Path(repo) / d / "commands"
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*.md"))[:200]:
            if f.is_symlink() or not f.is_file():
                continue
            meta, body = front(_read(f, 60_000))
            name = f.stem.lower()
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,40}", name) or name in out:
                continue
            first = next((x.strip() for x in body.splitlines() if x.strip()), "")
            out[name] = {"description": (meta.get("description") or first)[:200], "hint": meta.get("argument-hint", "")[:120],
                         "body": body, "path": str(f.relative_to(repo))}
    return out


def expand_command(repo: Path, text: str) -> tuple[str, str] | None:
    """'/name args' -> (name, the command's text with the arguments filled in), or None."""
    m = re.match(r"^\s*/([a-z0-9][a-z0-9_-]{0,40})(?:\s+(.*))?$", text or "", re.S)
    if not m:
        return None
    cmd = commands(repo).get(m.group(1).lower())
    if not cmd:
        return None
    args = (m.group(2) or "").strip()
    words = args.split()
    body = cmd["body"].replace("$ARGUMENTS", args)
    body = re.sub(r"\$(\d)", lambda x: words[int(x.group(1)) - 1] if 0 < int(x.group(1)) <= len(words) else "", body)
    return m.group(1).lower(), body.strip()


# ---------------------------------------------------------------- the repo's own subagents
def agents(repo: Path) -> dict[str, dict[str, str]]:
    """{name: spec} in subagent.py's shape (name, title, tools = read | run | edit, prompt, description)."""
    out: dict[str, dict[str, str]] = {}
    for d in DIRS:
        base = Path(repo) / d / "agents"
        if not base.is_dir():
            continue
        for f in sorted(base.glob("*.md"))[:60]:
            if f.is_symlink() or not f.is_file():
                continue
            meta, body = front(_read(f, 60_000))
            name = (meta.get("name") or f.stem).strip().lower()
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,50}", name) or name in out or not body.strip():
                continue
            tl = {x.strip().lower() for x in re.split(r"[,\s]+", meta.get("tools", "")) if x.strip()}
            level = ("edit" if not tl or tl & {"edit", "write", "multiedit", "multi_edit", "notebookedit"}
                     else "run" if tl & {"bash"} else "read")
            out[name] = {"name": name, "title": name.replace("-", " ").replace("_", " ").title(), "tools": level,
                         "prompt": "THIS REPO'S OWN AGENT (from " + str(f.relative_to(repo)) + "):\n" + body.strip()[:20000],
                         "description": meta.get("description", "")[:300], "repo": "1"}
    return out


# ---------------------------------------------------------------- @file in her message
def mentions(repo: Path, text: str, real=None, hidden: set[str] | None = None) -> str:
    """The files her message names with @path, as blocks the model reads (secrets stay hidden)."""
    seen: list[str] = []
    for m in MENTION.finditer(text or ""):
        rel = _clean(m.group(1).strip()).rstrip(".,;:)")
        if rel in seen or len(seen) >= MENTION_MAX:
            continue
        seen.append(rel)
    out = []
    for rel in seen:
        if hidden and rel in hidden:
            out.append(f'<her_file path="{rel}">(this file holds secrets - hidden)</her_file>')
            continue
        f = real(rel) if real else Path(repo) / rel
        if f is None or not Path(f).exists():
            continue
        if Path(f).is_dir():
            try:
                names = sorted(x.name + ("/" if x.is_dir() else "") for x in Path(f).iterdir())[:200]
            except OSError:
                continue
            out.append(f'<her_folder path="{rel}">\n' + "\n".join(names) + "\n</her_folder>")
            continue
        body = _read(Path(f), MENTION_CHARS + 1)
        cut = len(body) > MENTION_CHARS
        out.append(f'<her_file path="{rel}">\n{body[:MENTION_CHARS]}' + ("\n... (cut: read the rest with read)" if cut else "")
                   + "\n</her_file>")
    return ("She pointed at these with @ in her message:\n" + "\n".join(out)) if out else ""


def find_files(paths: list[str], q: str, limit: int = 20) -> list[str]:
    """Files for the @ picker: name matches first, then path matches."""
    q = (q or "").strip().lower().lstrip("@")
    if not q:
        return paths[:limit]
    by_name = [p for p in paths if p.rsplit("/", 1)[-1].lower().startswith(q)]
    rest = [p for p in paths if q in p.lower() and p not in by_name]
    return (by_name + rest)[:limit]
