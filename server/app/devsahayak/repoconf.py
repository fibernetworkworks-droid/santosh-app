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

import os

import fnmatch
import json
import re
from pathlib import Path
from typing import Any

DIRS = (".claude", ".hoola")
TOOL_NAMES = {"bash": "Bash", "read": "Read", "write": "Write", "edit": "Edit", "multi_edit": "Edit", "glob": "Glob",
              "grep": "Grep", "ls": "LS", "web_fetch": "WebFetch", "web_search": "WebSearch", "notebook_edit": "NotebookEdit",
              "todo_write": "TodoWrite", "agent": "Task", "mcp": "mcp"}
HOOK_EVENTS = ("PreToolUse", "PostToolUse", "UserPromptSubmit", "SessionStart", "Stop", "SubagentStop", "PreCompact",
               "SessionEnd", "Notification",
               # v0.999 the rest of Claude Code's events that mean something in Hoola Code
               "SubagentStart", "PermissionRequest", "PermissionDenied", "PostToolUseFailure", "PostToolBatch", "PostCompact",
               "StopFailure", "InstructionsLoaded", "UserPromptExpansion", "TaskCreated", "TaskCompleted",
               "WorktreeCreate", "WorktreeRemove")              # v0.999 an agent's own copy made / removed
HOOK_TYPES = ("command", "prompt", "agent", "http", "mcp_tool")
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


# ---------------------------------------------------------------- settings (permissions + hooks + env + mode + style)
def _hook_groups(out: dict[str, Any], hooks: Any) -> None:
    for ev, groups in (hooks or {}).items() if isinstance(hooks, dict) else []:
        if ev not in HOOK_EVENTS or not isinstance(groups, list):
            continue
        for g in groups:
            if not isinstance(g, dict):
                continue
            specs = [s for s in (hook_spec(h) for h in (g.get("hooks") or [])[:5]) if s]
            if specs:
                out["hooks"].setdefault(ev, []).append({
                    "matcher": str(g.get("matcher") or ""), "specs": specs,
                    "commands": [s["command"] for s in specs if s["type"] == "command"],
                    "timeout": int(next((h.get("timeout") for h in g.get("hooks") or [] if isinstance(h, dict) and h.get("timeout")), 60) or 60)})


def hook_spec(h: Any) -> dict[str, Any] | None:
    """One hook of a settings file, Claude Code's types: command | prompt (a model judges) | agent (an agent checks with
    read-only tools) | http (POST the event to a url) | mcp_tool (a tool of one of the repo's MCP servers); onFailure."""
    if not isinstance(h, dict):
        return None
    kind = str(h.get("type") or "command")
    if kind not in HOOK_TYPES:
        return None
    s: dict[str, Any] = {"type": kind, "on_failure": "block" if str(h.get("onFailure") or "") == "block" else "",
                         "timeout": max(1, min(int(h.get("timeout") or (30 if kind in ("prompt", "http") else 60) or 60), 300))}
    if kind == "command":
        s["command"] = str(h.get("command") or "")[:2000]
        return s if s["command"].strip() else None
    if kind in ("prompt", "agent"):
        s["prompt"] = str(h.get("prompt") or "")[:4000]
        s["model"] = str(h.get("model") or "")[:80]
        return s if s["prompt"].strip() else None
    if kind == "http":
        s["url"] = str(h.get("url") or "")[:500]
        s["headers"] = {str(k): str(v) for k, v in (h.get("headers") or {}).items()
                        if isinstance(h.get("headers"), dict) and "${" not in str(v)}
        return s if s["url"].startswith("https://") else None
    s["server"] = str(h.get("server") or "")[:60]
    s["tool"] = str(h.get("tool") or "")[:120]
    s["input"] = h.get("input") if isinstance(h.get("input"), dict) else {}
    return s if s["server"] and s["tool"] else None


ENV_OK = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
ENV_NEVER = re.compile(r"(?i)(TOKEN|SECRET|PASSWORD|PASSWD|API_?KEY|PRIVATE|CREDENTIAL|^AWS_|^GH_|^GITHUB_)")
MODES_MAP = {"default": "steps", "acceptedits": "steps", "plan": "plan", "dontask": "auto"}   # bypassPermissions: never


def settings(repo: Path, plugins: list[Path] | tuple = ()) -> dict[str, Any]:
    """permissions {allow, ask, deny}, hooks {event: [{matcher, commands}]}, env {name: value}, mode, style - merged from
    .claude/ and .hoola/ settings(.local).json and the hooks of her enabled plugins (hooks/hooks.json)."""
    out: dict[str, Any] = {"allow": [], "ask": [], "deny": [], "hooks": {}, "env": {}, "mode": "", "accept_edits": False,
                           "style": "", "hard_deny": []}
    files = [Path(repo) / d / name for d in DIRS for name in ("settings.json", "settings.local.json")]
    files += [Path(pl) / "hooks" / "hooks.json" for pl in plugins]
    for f in files:
        raw = _read(f, 400_000)
        if not raw.strip():
            continue
        try:
            j = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(j, dict):
            continue
        perm = j.get("permissions") if isinstance(j.get("permissions"), dict) else {}
        for k in ("allow", "ask", "deny"):
            for r in perm.get(k) or []:
                if isinstance(r, str) and r.strip():
                    out[k].append(r.strip()[:300])
        mode = str(perm.get("defaultMode") or "").strip().lower()
        if mode in MODES_MAP:
            out["mode"], out["accept_edits"] = MODES_MAP[mode], mode == "acceptedits"
        _hook_groups(out, j.get("hooks"))
        am = j.get("autoMode") if isinstance(j.get("autoMode"), dict) else {}
        for r in am.get("hard_deny") or []:               # v0.999 Auto mode: refused with no review (Claude Code's own key)
            if isinstance(r, str) and r.strip():
                out["hard_deny"].append(r.strip()[:300])
        env = j.get("env") if isinstance(j.get("env"), dict) else {}
        for k, v in list(env.items())[:40]:           # plain settings for commands; anything that looks secret is left out
            if ENV_OK.match(str(k)) and not ENV_NEVER.search(str(k)) and isinstance(v, (str, int, float, bool)):
                out["env"][str(k)] = str(v)[:500]
        if isinstance(j.get("outputStyle"), str):
            out["style"] = j["outputStyle"].strip()[:60]
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
        if "*" in spec:                                  # v0.999 Claude Code's wildcard anywhere: Bash(npm run *), Bash(git * main)
            want = " ".join(spec.split())
            pat = "".join(".*" if ch == "*" else re.escape(ch) for ch in want)
            if want.endswith(" *"):                      # 'ls *' also matches a bare 'ls' (Claude Code's word boundary)
                return bool(re.fullmatch(pat, cmd, re.S)) or cmd == want[:-2]
            return bool(re.fullmatch(pat, cmd, re.S))
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


def hooks_for(conf: dict[str, Any], event: str, tool: str = "") -> list[dict[str, Any]]:
    """The hooks to run for this event (and tool), each a hook_spec ({type, command | prompt | url | server+tool, timeout,
    on_failure})."""
    out: list[dict[str, Any]] = []
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
        out += g.get("specs") or [{"type": "command", "command": c, "timeout": max(1, min(int(g.get("timeout") or 60), 300)),
                                   "on_failure": ""} for c in g.get("commands") or []]
    return out[:8]


# v0.999 hook input / output in Claude Code's own field names (a hook script reads .tool_input.file_path, not path)
FIELD_TO_CLAUDE = {"read": {"path": "file_path"}, "write": {"path": "file_path"}, "edit": {"path": "file_path"},
                   "multi_edit": {"path": "file_path"}, "notebook_edit": {"path": "notebook_path", "cell": "cell_number"}}


def to_claude_input(tool: str, inp: dict[str, Any] | None) -> dict[str, Any]:
    m = FIELD_TO_CLAUDE.get(tool, {})
    return {m.get(k, k): v for k, v in (inp or {}).items() if not str(k).startswith("_")}


def from_claude_input(tool: str, upd: dict[str, Any]) -> dict[str, Any]:
    back = {v: k for k, v in FIELD_TO_CLAUDE.get(tool, {}).items()}
    return {back.get(k, k): v for k, v in (upd or {}).items() if not str(k).startswith("_")}


def hook_answer(event: str, rc: int, stdout: str, stderr: str) -> dict[str, Any]:
    """One hook's answer, read the way Claude Code reads it.
    exit 2 = block, its stderr is the reason (JSON ignored); exit 0 = stdout may be JSON (continue / stopReason /
    systemMessage / suppressOutput / decision / reason / hookSpecificOutput: permissionDecision, permissionDecisionReason,
    updatedInput, additionalContext), or plain text (context for SessionStart / UserPromptSubmit, otherwise only shown);
    any other exit = a non-blocking error shown to her, the work goes on."""
    a: dict[str, Any] = {"block": False, "reason": "", "context": "", "decision": "", "updated": None, "stop": False,
                         "stop_reason": "", "message": "", "shown": "", "error": "", "output": None, "retry": False, "title": ""}
    out, err = (stdout or "").strip(), (stderr or "").strip()
    if rc == 2:
        a["block"], a["reason"] = True, (err or out)[-4000:]
        return a
    if rc != 0:
        a["error"] = (err or out)[-1500:]
        return a
    j = None
    if out.startswith("{"):
        try:
            j = json.loads(out)
        except ValueError:
            j = None
    if not isinstance(j, dict):
        if event in ("SessionStart", "UserPromptSubmit"):
            a["context"] = out[-6000:]
        else:
            a["shown"] = out[-1500:]
        return a
    if j.get("continue") is False:
        a["stop"], a["stop_reason"] = True, str(j.get("stopReason") or "")[:1000]
    a["message"] = str(j.get("systemMessage") or "")[:1000]
    dec = str(j.get("decision") or "").lower()
    reason = str(j.get("reason") or "")[:4000]
    hs = j.get("hookSpecificOutput") if isinstance(j.get("hookSpecificOutput"), dict) else {}
    if event == "PreToolUse":
        pd = str(hs.get("permissionDecision") or "").lower() or {"approve": "allow", "block": "deny"}.get(dec, "")
        if pd in ("allow", "deny", "ask"):                # 'defer' = no decision: the normal flow decides
            a["decision"] = pd
            a["reason"] = str(hs.get("permissionDecisionReason") or reason or "")[:4000]
        if isinstance(hs.get("updatedInput"), dict):
            a["updated"] = hs["updatedInput"]
    elif event == "PermissionRequest":                    # v0.999 answer the permission prompt instead of her
        d = hs.get("decision") if isinstance(hs.get("decision"), dict) else {}
        beh = str(d.get("behavior") or "").lower()
        if beh in ("allow", "deny"):
            a["decision"], a["reason"] = beh, str(d.get("message") or reason or "")[:4000]
        if isinstance(d.get("updatedInput"), dict):
            a["updated"] = d["updatedInput"]
    elif dec == "block":
        a["block"], a["reason"] = True, reason
    if event == "PermissionDenied" and (hs.get("retry") is True or j.get("retry") is True):
        a["retry"] = True
    if event == "PostToolUse" and "updatedToolOutput" in hs:
        v = hs["updatedToolOutput"]
        a["output"] = v if isinstance(v, str) else json.dumps(v, default=str)
    if isinstance(hs.get("sessionTitle"), str) and event in ("SessionStart", "UserPromptSubmit"):
        a["title"] = hs["sessionTitle"].strip()[:120]
    if event in ("SessionStart", "UserPromptSubmit", "PostToolUse", "PostToolUseFailure", "SubagentStart",
                 "UserPromptExpansion", "PostToolBatch") and hs.get("additionalContext"):
        a["context"] = str(hs["additionalContext"])[:6000]
    return a


def judge_answer(event: str, text: str) -> str:
    """A prompt / agent hook's verdict ({"ok": true|false, "reason": "..."}, Claude Code's shape) as the stdout JSON a
    command hook would print, so one reader handles both."""
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        j = json.loads(m.group(0)) if m else {}
    except ValueError:
        j = {}
    if not isinstance(j, dict) or "ok" not in j:
        return ""
    if j.get("ok") is True:
        return json.dumps({"hookSpecificOutput": {"additionalContext": str(j.get("reason") or "")}} if j.get("reason") else {})
    why = str(j.get("reason") or "the hook said no")[:2000]
    if event == "PreToolUse":
        return json.dumps({"hookSpecificOutput": {"permissionDecision": "deny", "permissionDecisionReason": why}})
    if event == "PermissionRequest":
        return json.dumps({"hookSpecificOutput": {"decision": {"behavior": "deny", "message": why}}})
    return json.dumps({"decision": "block", "reason": why})


def hook_input(event: str, tid: str, tool: str = "", inp: dict[str, Any] | None = None, out: str = "",
               prompt: str = "", extra: dict[str, Any] | None = None) -> dict[str, Any]:
    j: dict[str, Any] = {"session_id": tid, "hook_event_name": event, "cwd": "/work"}
    for k, v in (extra or {}).items():                    # v0.999 what each newer event carries (error, agent_type, ...)
        j[str(k)] = v
    if tool:
        j["tool_name"] = _claude_name(tool)
        j["tool_input"] = to_claude_input(tool, inp)
    if event in ("PostToolUse", "PostToolUseFailure"):
        j["tool_response" if event == "PostToolUse" else "error"] = out[:20000]
    if prompt:
        j["message" if event == "Notification" else "prompt"] = prompt[:20000]
    return j


# ---------------------------------------------------------------- custom slash commands
def _bases(repo: Path, sub: str, plugins: list[Path] | tuple = ()) -> list[tuple[Path, Path, str]]:
    """(folder, the root paths are shown against, where from) for the repo's .claude/<sub> and each plugin's <sub>."""
    out = [(Path(repo) / d / sub, Path(repo), "repo") for d in DIRS]
    out += [(Path(pl) / sub, Path(pl).parent, "plugin " + Path(pl).name) for pl in plugins]
    return out


def commands(repo: Path, plugins: list[Path] | tuple = ()) -> dict[str, dict[str, str]]:
    """{name: {description, hint, body, path, origin}} from .claude/commands/**/*.md (+ .hoola, + her plugins)."""
    out: dict[str, dict[str, str]] = {}
    for base, rel_to, origin in _bases(repo, "commands", plugins):
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
                         "body": body, "path": str(f.relative_to(rel_to)), "origin": origin}
    return out


def expand_command(repo: Path, text: str, plugins: list[Path] | tuple = ()) -> tuple[str, str] | None:
    """'/name args' -> (name, the command's text with the arguments filled in), or None."""
    m = re.match(r"^\s*/([a-z0-9][a-z0-9_-]{0,40})(?:\s+(.*))?$", text or "", re.S)
    if not m:
        return None
    cmd = commands(repo, plugins).get(m.group(1).lower())
    if not cmd:
        return None
    args = (m.group(2) or "").strip()
    words = args.split()
    body = cmd["body"].replace("$ARGUMENTS", args)
    body = re.sub(r"\$(\d)", lambda x: words[int(x.group(1)) - 1] if 0 < int(x.group(1)) <= len(words) else "", body)
    return m.group(1).lower(), body.strip()


# ---------------------------------------------------------------- the repo's own subagents
def agents(repo: Path, plugins: list[Path] | tuple = ()) -> dict[str, dict[str, str]]:
    """{name: spec} in subagent.py's shape (name, title, tools = read | run | edit, prompt, description)."""
    out: dict[str, dict[str, str]] = {}
    for base, rel_to, origin in _bases(repo, "agents", plugins):
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
                         "prompt": f"THIS {'REPO' if origin == 'repo' else origin.upper()}'S OWN AGENT (from " + str(f.relative_to(rel_to)) + "):\n" + body.strip()[:20000],
                         "description": meta.get("description", "")[:300], "repo": "1", "origin": origin,
                         "model": str(meta.get("model", "") or "").strip()[:80],       # v0.999 Claude Code's `model:` line
                         "isolation": "worktree" if str(meta.get("isolation", "") or "").strip().lower() == "worktree" else ""}
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


# ---------------------------------------------------------------- v0.999 the repo's skills (.claude/skills/<name>/SKILL.md)
def skills(repo: Path, plugins: list[Path] | tuple = ()) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for base, rel_to, origin in _bases(repo, "skills", plugins):
        if not base.is_dir():
            continue
        for f in sorted(base.glob("*/SKILL.md"))[:100]:
            if f.is_symlink() or not f.is_file():
                continue
            meta, body = front(_read(f, 80_000))
            name = (meta.get("name") or f.parent.name).strip().lower()
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,60}", name) or name in out or not body.strip():
                continue
            extra = sorted(str(x.relative_to(rel_to)) for x in f.parent.rglob("*") if x.is_file() and x.name != "SKILL.md")[:30]
            out[name] = {"name": name, "description": meta.get("description", "")[:400], "body": body.strip(),
                         "path": str(f.relative_to(rel_to)), "files": extra, "origin": origin}
    return out


# ---------------------------------------------------------------- v0.999 the repo's MCP servers (.mcp.json)
def mcp_servers(repo: Path, plugins: list[Path] | tuple = ()) -> dict[str, dict[str, Any]]:
    """{name: {kind, url, headers, ok, why} | {kind: stdio, argv, env, ok, why}}. A REMOTE server (http / sse with an https
    address) is called over the internet; v0.999 a server that RUNS AS A PROGRAM (`command` + `args`, Claude Code's stdio
    servers: npx ..., uvx ..., node ./x.js, python -m x) runs inside the session's locked box like her commands. A header
    or variable that names a ${VARIABLE} Hoola does not have is left out: it never guesses a secret."""
    out: dict[str, dict[str, Any]] = {}
    for f in [Path(repo) / ".mcp.json"] + [Path(pl) / ".mcp.json" for pl in plugins]:
        raw = _read(f, 200_000)
        if not raw.strip():
            continue
        try:
            j = json.loads(raw)
        except ValueError:
            continue
        for name, cfg in ((j.get("mcpServers") or {}) if isinstance(j, dict) else {}).items():
            if not isinstance(cfg, dict) or not re.fullmatch(r"[\w.-]{1,60}", str(name)) or name in out:
                continue
            url = str(cfg.get("url") or "")
            if cfg.get("command"):
                out[name] = stdio_spec(cfg, f.parent, plugin=f.parent != Path(repo))
                continue
            if not url:
                out[name] = {"kind": "http", "url": "", "headers": {}, "ok": False, "why": "it has no address and no command"}
                continue
            if not url.startswith("https://"):
                out[name] = {"kind": "http", "url": url, "headers": {}, "ok": False, "why": "only https addresses are reached"}
                continue
            hdr = {str(k): str(v) for k, v in (cfg.get("headers") or {}).items() if "${" not in str(v)}
            out[name] = {"kind": "http", "url": url[:500], "headers": hdr, "ok": True, "why": ""}
    return out


VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def _expand(v: str, env: dict[str, str]) -> str | None:
    """${VAR} / ${VAR:-default} the way Claude Code expands .mcp.json; None = it names something Hoola does not have."""
    missing = []

    def one(m: re.Match) -> str:
        k, d = m.group(1), m.group(2)
        if k in env:
            return env[k]
        if d is not None:
            return d
        missing.append(k)
        return ""
    out = VAR.sub(one, str(v))
    return None if missing else out


def stdio_spec(cfg: dict[str, Any], base: Path, plugin: bool = False) -> dict[str, Any]:
    """A program-type MCP server, ready to start inside the box: argv with ${VAR}s filled from what Hoola has
    (CLAUDE_PROJECT_DIR = the repo in the box), its own env (a value naming a secret Hoola does not have is left out)."""
    known = {"CLAUDE_PROJECT_DIR": "/work"}
    cmd = str(cfg.get("command") or "").strip()
    args = [str(a) for a in (cfg.get("args") or []) if isinstance(a, (str, int, float))][:40]
    if plugin and any("${CLAUDE_PLUGIN_ROOT}" in x for x in [cmd] + args):
        return {"kind": "stdio", "argv": [], "env": {}, "ok": False,
                "why": "it runs a program kept inside the plugin's own folder, which the box cannot see"}
    argv = [_expand(x, known) for x in [cmd] + args]
    if not cmd or any(x is None for x in argv):
        return {"kind": "stdio", "argv": [], "env": {}, "ok": False,
                "why": "its command names a variable Hoola does not have" if cmd else "it has no command"}
    env = {}
    for k, v in (cfg.get("env") or {}).items():
        val = _expand(str(v), known)
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,60}", str(k)) and val is not None and not ENV_NEVER.search(str(k)):
            env[str(k)] = val[:2000]
    return {"kind": "stdio", "argv": [x[:500] for x in argv], "env": env, "ok": True, "why": "",
            "dropped": sorted(str(k) for k in (cfg.get("env") or {}) if str(k) not in env)}


# ---------------------------------------------------------------- v0.999 CLAUDE.md: imports, CLAUDE.local.md, folders
RULE_NAMES = ("CLAUDE.md", "AGENTS.md", "CLAUDE.local.md")
IMPORT = re.compile(r"(?m)(?:^|\s)@((?:~/|\.{1,2}/|/)?[\w.\-/]+\.\w+)")


def rule_text(repo: Path, rel: str, depth: int = 0, seen: set[str] | None = None) -> str:
    """One rules file with its `@path` imports pulled in (5 deep, each file once, inside the repo only)."""
    seen = seen if seen is not None else set()
    rel = _clean(os.path.normpath(str(rel)))
    if rel in seen or depth > 5 or rel.startswith("..") or rel in (".", ""):
        return ""
    seen.add(rel)
    f = Path(repo) / rel
    try:
        if f.is_symlink() or not f.is_file() or not f.resolve().is_relative_to(Path(repo).resolve()):
            return ""
    except (OSError, ValueError):
        return ""
    body = _read(f, 40_000)
    parts = []
    for m in IMPORT.finditer(body):
        imp = m.group(1)
        if imp.startswith("~/") or imp.startswith("/"):
            continue                                       # a file on her own computer: not in the repo
        target = _clean(os.path.normpath(str(Path(rel).parent / imp)))
        txt = rule_text(repo, target, depth + 1, seen)
        if txt:
            parts.append(f'<imported path="{_clean(target)}">\n{txt}\n</imported>')
    return body + ("\n" + "\n".join(parts) if parts else "")


def folder_rules(paths: list[str], rel: str) -> list[str]:
    """The rules files of the folders above `rel` (not the root), nearest last: what Claude Code loads when work moves there."""
    folders = []
    parts = _clean(rel).split("/")[:-1]
    for i in range(1, len(parts) + 1):
        folders.append("/".join(parts[:i]))
    have = set(paths)
    return [f"{d}/{n}" for d in folders for n in RULE_NAMES if f"{d}/{n}" in have]


# ---------------------------------------------------------------- v0.999 output styles
STYLES = {
    "default": "",
    "explanatory": ("OUTPUT STYLE - EXPLANATORY: while you work, add short 'Insight' notes that explain WHY you chose an "
                    "approach and how this codebase works (patterns, trade-offs), so she learns her code as you go. Keep "
                    "the work itself just as efficient."),
    "learning": ("OUTPUT STYLE - LEARNING: work together with her. Explain your choices briefly, and for small, meaningful "
                 "pieces (5-10 lines: a condition, a test case, a name) leave a `TODO(you)` with a clear hint and ask her to "
                 "write it, instead of writing everything yourself. Never leave the code broken."),
}


def styles(repo: Path, plugins: list[Path] | tuple = ()) -> dict[str, dict[str, str]]:
    """Built-in styles + the repo's own (.claude/output-styles/*.md: name, description, the instructions)."""
    out = {k: {"name": k, "description": {"default": "Hoola's normal way of working",
                                          "explanatory": "Explains why, as it works",
                                          "learning": "Leaves small parts for you to write"}[k], "prompt": v, "origin": "hoola"}
           for k, v in STYLES.items()}
    for base, _rel, origin in _bases(repo, "output-styles", plugins):
        if not base.is_dir():
            continue
        for f in sorted(base.glob("*.md"))[:30]:
            meta, body = front(_read(f, 30_000))
            name = (meta.get("name") or f.stem).strip().lower()
            if re.fullmatch(r"[a-z0-9][a-z0-9 _-]{0,40}", name) and name not in out and body.strip():
                out[name] = {"name": name, "description": meta.get("description", "")[:200],
                             "prompt": f"OUTPUT STYLE - {name.upper()} (this repo's own):\n" + body.strip()[:8000], "origin": origin}
    return out
