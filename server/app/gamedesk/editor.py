"""v0.425 ASK HOOLA IN THE EDITOR (Hoola Game Engine plan Phase 8): a real MCP server for her Game Desk, and a Godot
editor plugin that talks to it.

- EDITOR TOKENS: she makes one in the console ("Connect your editor"); it is shown ONCE and kept only as a sha256
  hash; it can read her game projects and ask Hoola, and add a To-do task - nothing else (no money, no publishing, no
  deleting, no account settings). Revocable; last use is recorded.
- MCP: POST /mcp/gamedesk speaks the Model Context Protocol over Streamable HTTP (JSON-RPC 2.0: initialize,
  notifications/initialized, ping, tools/list, tools/call; batches too), so any MCP client - the Hoola Godot plugin,
  Claude Desktop, Cursor, a Godot MCP bridge - can use it with `Authorization: Bearer <editor token>`. Tools:
  hoola_projects, hoola_tasks, hoola_bible, hoola_bugs, hoola_ask (her question + the open script -> an answer from
  her design doc, Game Bible and live code), hoola_add_task. Answers are text; nothing is applied to her files by
  Hoola - the plugin shows them and SHE copies what she wants.
- GODOT PLUGIN: addons/hoola (plugin.cfg + plugin.gd + dock.gd, @tool) - an "Ask Hoola" dock with Ask / Tasks / Bible
  / Bugs, the token kept in HER EditorSettings on her machine (never in the project, never in git). Loaded and parsed
  by the real Godot editor (headless) before it is offered."""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import secrets
import time
import zipfile
from collections import defaultdict, deque
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, String, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session
from . import service as G

log = logging.getLogger("santosh.gamedesk")
# v0.447: MCP's CURRENT revision is 2026-07-28, which REMOVED the `initialize` handshake - a request now declares its
# version in `_meta["io.modelcontextprotocol/protocolVersion"]` (and, on HTTP, the MCP-Protocol-Version header), and
# `server/discover` is MUST-implement. The spec's own compatibility table: a dual-era client falls back to `initialize`
# and works against a legacy server, but a MODERN-ONLY client FAILS. So both eras are served here.
PV_KEY = "io.modelcontextprotocol/protocolVersion"
CLIENT_KEY = "io.modelcontextprotocol/clientInfo"
MODERN = ("2026-07-28",)
LEGACY = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
PROTOCOLS = MODERN + LEGACY
UNSUPPORTED = -32022
SERVER_INFO = {"name": "hoola-gamedesk", "title": "Hoola Game Desk", "version": "1.0.0"}
INSTRUCTIONS = ("Hoola Game Desk: her Hoola-built game projects (tasks, Game Bible, bugs, Ask Hoola) and her big-studio "
                "projects in Unity / Unreal / Godot (hoola_studio_*: next task + a checked proposal, report the editor's "
                "compile result). The server never writes her files: a proposal is applied only by her, in her editor.")
_ASK_RATE: dict[str, deque] = defaultdict(deque)
TOKEN_PREFIX = "hoola_ed_"


class EditorError(G.GameError):
    pass


class EditorToken(Base):
    __tablename__ = "game_editor_tokens"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("et"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    label: Mapped[str] = mapped_column(String(60), default="")
    hash: Mapped[str] = mapped_column(String(64), index=True)
    hint: Mapped[str] = mapped_column(String(16), default="")
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_used: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_READY: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        EditorToken.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def _h(tok: str) -> str:
    return hashlib.sha256(tok.encode()).hexdigest()


def create_token(tenant: str, label: str = "") -> dict[str, Any]:
    ensure_table()
    with session() as s:
        live = s.scalars(select(EditorToken).where(EditorToken.tenant_id == tenant, EditorToken.revoked.is_(False))).all()
        if len(live) >= 10:
            raise EditorError("There are already 10 editor tokens; remove one.")
        tok = TOKEN_PREFIX + secrets.token_urlsafe(32)
        r = EditorToken(tenant_id=tenant, label=(label or "Godot editor")[:60], hash=_h(tok), hint=tok[-4:])
        s.add(r)
        s.flush()
        rid = r.id
    return {"id": rid, "token": tok, "say": "This token is shown only now - put it into the editor. Hoola will not show it again."}


def tokens(tenant: str) -> list[dict[str, Any]]:
    ensure_table()
    with session() as s:
        rows = s.scalars(select(EditorToken).where(EditorToken.tenant_id == tenant).order_by(EditorToken.created_at.desc())).all()
        return [{"id": r.id, "label": r.label, "hint": "..." + r.hint, "revoked": r.revoked,
                 "created": r.created_at.isoformat() if r.created_at else "", "last_used": r.last_used.isoformat() if r.last_used else ""}
                for r in rows[:20]]


def revoke(tenant: str, tid: str) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        r = s.get(EditorToken, tid)
        if r is None or r.tenant_id != tenant:
            raise EditorError("Token not found.")
        r.revoked = True
    return {"ok": True}


def auth(header: str) -> tuple[str, str] | None:
    """(tenant, token id) for a live editor token in 'Authorization: Bearer ...', else None."""
    m = re.match(r"^Bearer\s+(\S+)$", (header or "").strip())
    if not m or not m.group(1).startswith(TOKEN_PREFIX):
        return None
    ensure_table()
    with session() as s:
        r = s.scalars(select(EditorToken).where(EditorToken.hash == _h(m.group(1)), EditorToken.revoked.is_(False))).first()
        if r is None:
            return None
        r.last_used = now()
        return r.tenant_id, r.id


# ================================================================ the tools
TOOLS = [
    {"name": "hoola_projects", "title": "Her game projects",
     "description": "Her Hoola Studio game projects: id, title, live version, play link, QA verdict, open bugs and tasks.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "hoola_tasks", "title": "Task board", "description": "The task board of one project (id S-0001; optional when she has one).",
     "inputSchema": {"type": "object", "properties": {"project": {"type": "string"}, "state": {"type": "string",
                     "enum": ["open", "done", "all"]}}, "additionalProperties": False}},
    {"name": "hoola_bible", "title": "Game Bible", "description": "The project's Game Bible (names, numbers, palette) as JSON.",
     "inputSchema": {"type": "object", "properties": {"project": {"type": "string"}}, "additionalProperties": False}},
    {"name": "hoola_bugs", "title": "Bugs", "description": "The project's numbered bugs from Hoola's QA farm and her own reports.",
     "inputSchema": {"type": "object", "properties": {"project": {"type": "string"}}, "additionalProperties": False}},
    {"name": "hoola_ask", "title": "Ask Hoola",
     "description": "Ask Hoola about her game: it answers from the design doc, the Game Bible and the live code (plus the "
                    "script she has open, if sent). Text only - nothing is changed in her files.",
     "inputSchema": {"type": "object", "properties": {"question": {"type": "string"}, "project": {"type": "string"},
                     "script": {"type": "string", "description": "the open script's text (optional, max 20,000 chars)"},
                     "script_name": {"type": "string"}}, "required": ["question"], "additionalProperties": False}},
    {"name": "hoola_add_task", "title": "Add a task",
     "description": "Add a To-do task to the project's board (it waits there for her OK like every task).",
     "inputSchema": {"type": "object", "properties": {"title": {"type": "string"}, "detail": {"type": "string"},
                     "project": {"type": "string"}}, "required": ["title"], "additionalProperties": False}},
]

ASK = """You are Hoola, the game developer inside her Godot editor. Answer her question about HER game only, from the
design doc, the Game Bible, the live code and the open script given. Be concrete: name the file, the function and the
line to change and show the exact GDScript (Godot 4.x). Keep it short. Never invent a file or a number that is not in
what you were given; say what you would need. Original content only; no real-money mechanics."""


def _one_project(tenant: str, ref: str):
    from . import studio as S
    if ref:
        return S.get(tenant, ref)
    mine = S.studios(tenant)
    if len(mine) != 1:
        raise EditorError(f"Which project? project = {', '.join(p['number'] for p in mine[:8]) or 'no project'}")
    return S.get(tenant, mine[0]["id"])


def _rate(tid: str, limit: int = 30, window: float = 3600.0) -> bool:
    q = _ASK_RATE[tid]
    t = time.time()
    while q and q[0] < t - window:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(t)
    return True


def call_tool(tenant: str, tid: str, name: str, args: dict) -> Any:
    from . import bigstudio as BIG
    from . import qa as Q
    from . import studio as S
    args = args if isinstance(args, dict) else {}
    if name in BIG.NAMES:                                # v0.433 big-studio mode (Unity / Unreal / outside Godot)
        return BIG.call_tool(tenant, tid, name, args)
    if name == "hoola_projects":
        out = []
        for p in S.studios(tenant):
            full = S.get(tenant, p["id"])
            g = full.get("game") or {}
            out.append({"id": p["number"], "title": p.get("title"), "live_version": g.get("version"), "play": g.get("play_url"),
                        "qa": (full.get("qa") or {}).get("verdict"), "open_bugs": (full.get("qa") or {}).get("open"),
                        "tasks_open": sum(1 for t in full.get("tasks", []) if t.get("status") in S.OPEN)})
        return out
    p = _one_project(tenant, str(args.get("project") or ""))
    if name == "hoola_tasks":
        st = str(args.get("state") or "open")
        rows = [t for t in p.get("tasks", []) if st == "all" or (st == "open") == (t.get("status") in S.OPEN)]
        return [{k: t.get(k) for k in ("number", "title", "status", "milestone", "role", "priority")} for t in rows[:60]]
    if name == "hoola_bible":
        from . import bible as B
        return B.view(tenant, p["id"]).get("data") or {}
    if name == "hoola_bugs":
        return [{k: b.get(k) for k in ("number", "title", "status", "severity", "kind")} for b in Q.bugs(tenant, p["id"]).get("bugs", [])[:60]]
    if name == "hoola_add_task":
        t = S.add_task(tenant, p["id"], str(args.get("title") or ""), str(args.get("detail") or ""), source="editor")
        return {"added": t.get("number") or (t.get("task") or {}).get("number"), "note": "It waits on the board for her OK."}
    if name == "hoola_ask":
        q = str(args.get("question") or "").strip()
        if len(q) < 3:
            raise EditorError("Write the question.")
        if not _rate(tid):
            raise EditorError("30 questions were asked this hour; try again in a while.")
        from . import ai
        from . import bible as B
        g = G._get(tenant, (p.get("game") or {}).get("id") or "")
        code = G._current_files(g)
        listing = "\n".join(f"=== {n} ===\n{c}" for n, c in code.items() if not n.startswith("hoola_"))[:40000]
        script = str(args.get("script") or "")[:20000]
        bible = json.dumps(B.view(tenant, p["id"]).get("data") or {})[:12000]
        prompt = (f"Design doc:\n{(g.design or '')[:6000]}\n\nGame Bible:\n{bible}\n\nLive code:\n{listing}\n\n"
                  + (f"Open script ({str(args.get('script_name') or 'script')}):\n{script}\n\n" if script else "")
                  + f"Her question: {q}")
        return {"answer": ai.ask(ASK, prompt, max_tokens=2500).strip()}
    raise EditorError(f"unknown tool {name}")


# ================================================================ JSON-RPC / MCP
def _err(rid: Any, code: int, msg: str) -> dict:
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": msg}}


def _asked_version(msg: dict, header: str = "") -> str:
    """The protocol version a request declares: `_meta` first (the spec's own place), then the HTTP header."""
    meta = (msg.get("params") or {}).get("_meta") or {}
    v = meta.get(PV_KEY) if isinstance(meta, dict) else None
    if not v and isinstance(msg.get("_meta"), dict):
        v = msg["_meta"].get(PV_KEY)
    return str(v or header or "")


def discover() -> dict[str, Any]:
    """server/discover - MUST-implement in the current revision: supported versions, capabilities and identity at once."""
    from . import bigstudio as BIG
    return {"resultType": "complete", "supportedVersions": list(PROTOCOLS),
            "capabilities": {"tools": {"listChanged": False}},
            "instructions": INSTRUCTIONS, "ttlMs": 3600000, "cacheScope": "public",
            "_meta": {"io.modelcontextprotocol/serverInfo": SERVER_INFO},
            "tools": [t["name"] for t in TOOLS + BIG.TOOLS]}


def handle_one(tenant: str, tid: str, msg: Any, header: str = "") -> dict | None:
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
        return _err(msg.get("id") if isinstance(msg, dict) else None, -32600, "Invalid Request")
    rid, method, params = msg.get("id"), msg["method"], msg.get("params") or {}
    if "id" not in msg:                                  # a notification: no answer
        return None
    want = _asked_version(msg, header)
    if want and want not in PROTOCOLS:
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": UNSUPPORTED, "message": "Unsupported protocol version",
                                                       "data": {"supported": list(PROTOCOLS), "requested": want}}}
    if method == "server/discover":
        return {"jsonrpc": "2.0", "id": rid, "result": discover()}
    if method == "initialize":
        want = str((params or {}).get("protocolVersion") or "")
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": want if want in PROTOCOLS else PROTOCOLS[0], "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
            "instructions": INSTRUCTIONS}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}
    if method == "tools/list":
        from . import bigstudio as BIG
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS + BIG.TOOLS}}
    if method == "tools/call":
        name = str((params or {}).get("name") or "")
        from . import bigstudio as BIG
        if name not in {t["name"] for t in TOOLS} | BIG.NAMES:
            return _err(rid, -32602, f"Unknown tool: {name}")
        try:
            out = call_tool(tenant, tid, name, (params or {}).get("arguments") or {})
            text = out["answer"] if isinstance(out, dict) and set(out) == {"answer"} else json.dumps(out, ensure_ascii=False, indent=1)
            return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": text}], "isError": False}}
        except G.GameError as e:
            return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": str(e)}], "isError": True}}
        except Exception:                               # noqa: BLE001
            log.exception("mcp tool %s", name)
            return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": "Hoola could not do that right now."}],
                                                            "isError": True}}
    return _err(rid, -32601, f"Method not found: {method}")


def handle(tenant: str, tid: str, body: Any, header: str = "") -> Any:
    if isinstance(body, list):
        if not body:
            return _err(None, -32600, "Invalid Request")
        out = [r for r in (handle_one(tenant, tid, m, header) for m in body[:20]) if r is not None]
        return out or None
    return handle_one(tenant, tid, body, header)


# ================================================================ the Godot editor plugin
PLUGIN_CFG = '''[plugin]

name="Hoola"
description="Ask Hoola inside the Godot editor: your Studio tasks, Game Bible, bugs, and questions about your code."
author="Hoola (Newtika)"
version="1.0"
script="plugin.gd"
'''

PLUGIN_GD = '''@tool
extends EditorPlugin
# Hoola editor plugin: adds the "Hoola" dock. Talks to Hoola's MCP server with YOUR editor token (kept in your
# EditorSettings on this machine - never in the project or in git).
var dock: Control

func _enter_tree() -> void:
	dock = preload("res://addons/hoola/dock.gd").new()
	dock.name = "Hoola"
	add_control_to_dock(DOCK_SLOT_RIGHT_UL, dock)
	print("Hoola panel ready")

func _exit_tree() -> void:
	if dock:
		remove_control_from_docks(dock)
		dock.queue_free()
		dock = null
'''

DOCK_GD = '''@tool
extends VBoxContainer
# The Hoola dock: Ask / Tasks / Bible / Bugs over MCP (JSON-RPC to <server>/mcp/gamedesk). Nothing is applied to your
# files - copy what you want from the answer.
var http: HTTPRequest
var server: LineEdit
var token: LineEdit
var project: LineEdit
var question: TextEdit
var send_script: CheckBox
var out: RichTextLabel
var busy := false

func _ready() -> void:
	var es := EditorInterface.get_editor_settings()
	if not es.has_setting("hoola/server"):
		es.set_setting("hoola/server", "__SERVER__")
	if not es.has_setting("hoola/token"):
		es.set_setting("hoola/token", "")
	server = _row("Server", String(es.get_setting("hoola/server")))
	token = _row("Editor token", String(es.get_setting("hoola/token")))
	token.secret = true
	project = _row("Project (S-0001)", "")
	var save := Button.new()
	save.text = "Save"
	save.pressed.connect(_save)
	add_child(save)
	question = TextEdit.new()
	question.placeholder_text = "Ask Hoola about your game..."
	question.custom_minimum_size = Vector2(0, 90)
	add_child(question)
	send_script = CheckBox.new()
	send_script.text = "Send the open script"
	send_script.button_pressed = true
	add_child(send_script)
	var h := HBoxContainer.new()
	for pair in [["Ask", "hoola_ask"], ["Tasks", "hoola_tasks"], ["Bible", "hoola_bible"], ["Bugs", "hoola_bugs"]]:
		var b := Button.new()
		b.text = String(pair[0])
		var tool_name: String = pair[1]
		b.pressed.connect(func(): _go(tool_name))
		h.add_child(b)
	add_child(h)
	out = RichTextLabel.new()
	out.selection_enabled = true
	out.size_flags_vertical = Control.SIZE_EXPAND_FILL
	out.custom_minimum_size = Vector2(0, 240)
	add_child(out)
	http = HTTPRequest.new()
	add_child(http)
	http.request_completed.connect(_done)

func _row(label: String, value: String) -> LineEdit:
	var l := Label.new()
	l.text = label
	add_child(l)
	var e := LineEdit.new()
	e.text = value
	add_child(e)
	return e

func _save() -> void:
	var es := EditorInterface.get_editor_settings()
	es.set_setting("hoola/server", server.text.strip_edges())
	es.set_setting("hoola/token", token.text.strip_edges())
	out.text = "Saved on this computer."

func _go(tool_name: String) -> void:
	if busy:
		return
	var args := {}
	if project.text.strip_edges() != "":
		args["project"] = project.text.strip_edges()
	if tool_name == "hoola_ask":
		if question.text.strip_edges().length() < 3:
			out.text = "Write your question first."
			return
		args["question"] = question.text
		if send_script.button_pressed:
			var sc = EditorInterface.get_script_editor().get_current_script()
			if sc != null:
				args["script"] = String(sc.source_code).left(20000)
				args["script_name"] = String(sc.resource_path)
	var body := {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool_name, "arguments": args}}
	busy = true
	out.text = "Asking Hoola..."
	var err := http.request(server.text.strip_edges().trim_suffix("/") + "/mcp/gamedesk",
		["Content-Type: application/json", "Accept: application/json, text/event-stream", "Authorization: Bearer " + token.text.strip_edges()],
		HTTPClient.METHOD_POST, JSON.stringify(body))
	if err != OK:
		busy = false
		out.text = "Could not reach Hoola (error %d)." % err

func _done(_result: int, code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	busy = false
	if code == 401:
		out.text = "Hoola did not accept the token - make a new one in Hoola's Game Desk > Editor."
		return
	var data = JSON.parse_string(body.get_string_from_utf8())
	if data is Dictionary and data.has("result"):
		var parts := PackedStringArray()
		for c in data["result"].get("content", []):
			parts.append(String(c.get("text", "")))
		out.text = "\\n".join(parts)
	elif data is Dictionary and data.has("error"):
		out.text = "Hoola: " + String(data["error"].get("message", "error"))
	else:
		out.text = "No answer (HTTP %d)." % code
'''


def plugin_files(server_url: str) -> dict[str, str]:
    return {"addons/hoola/plugin.cfg": PLUGIN_CFG, "addons/hoola/plugin.gd": PLUGIN_GD,
            "addons/hoola/dock.gd": DOCK_GD.replace("__SERVER__", server_url.rstrip("/")),
            "addons/hoola/README.txt": "Hoola for Godot\n\n1. Copy the addons folder into your Godot project.\n2. Project > Project "
                                       "Settings > Plugins: enable Hoola.\n3. In Hoola's Game Desk > Editor, make an editor "
                                       "token and paste it in the Hoola dock (kept in your EditorSettings, never in the project).\n"
                                       "Other MCP clients: POST " + server_url.rstrip("/") + "/mcp/gamedesk with "
                                       "'Authorization: Bearer <token>'.\n"}


def plugin_zip(server_url: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n, t in plugin_files(server_url).items():
            z.writestr(n, t)
    return buf.getvalue()


def editor_check(job) -> dict:
    """Load the plugin in the REAL Godot editor (headless): parse errors in addons/hoola fail it."""
    import shutil
    from pathlib import Path
    from . import engine, template
    job = Path(job)
    shutil.rmtree(job, ignore_errors=True)
    (job / "proj").mkdir(parents=True)
    for name, txt in template.files("Hoola plugin check", "landscape", {"main.gd": "extends Node\n"}).items():
        (job / "proj" / name).write_text(txt, encoding="utf-8")
    for n, t in plugin_files("https://hoola.example.in").items():
        p = job / "proj" / n
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(t, encoding="utf-8")
    pg = (job / "proj" / "project.godot").read_text()
    (job / "proj" / "project.godot").write_text(pg + '\n[editor_plugins]\n\nenabled=PackedStringArray("res://addons/hoola/plugin.cfg")\n')
    engine._run(job, ["--path", "proj", "--import"], "import.log", 180)
    code, logtxt, to = engine._run(job, ["--editor", "--path", "proj", "--quit-after", "300"], "editor.log", 240)
    errs = [e for e in engine.errors_in(logtxt or "") if "addons/hoola" in e or "hoola" in e.lower()]
    return {"ok": "Hoola panel ready" in (logtxt or "") and not errs, "ready": "Hoola panel ready" in (logtxt or ""),
            "errors": errs[:5], "timed_out": to}
