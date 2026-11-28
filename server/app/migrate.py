"""v0.999 BRING YOUR OLD ASSISTANT - her memory, skills and past chats from OpenClaw, Hermes, ChatGPT or Claude.

OpenClaw and Hermes each import the other (OpenClaw's `migrate-hermes` plugin, Hermes's `agent-importers`). Both read a
folder on the same computer. Hoola runs on a server, so here she UPLOADS what her old assistant kept - a .zip or the
files - or pastes text, sees exactly what will come in, and only her tap brings it in. Formats read from the projects'
own code and docs (28 Nov 2026):

  OpenClaw   ~/.openclaw/workspace: MEMORY.md (long-term facts), USER.md (about her), memory/YYYY-MM-DD.md (daily
             notes), skills/<name>/SKILL.md; SOUL.md / AGENTS.md / IDENTITY.md are its personality and rules.
  Hermes     ~/.hermes: memories/MEMORY.md and memories/USER.md (entries split by a line holding only the section
             sign), skills/<category>/<name>/SKILL.md, SOUL.md.
  ChatGPT    the data export zip: conversations.json (each chat's `mapping` of messages). Its saved memories and
             custom instructions are NOT in the export - she copies them from Settings > Personalization and pastes.
  Claude     the data export: conversations.json (each chat's `chat_messages`, sender human / assistant).
  Any        a SKILL.md anywhere becomes a skill; pasted text becomes facts, one per line.

Where it lands (Hoola's own stores, nothing new to search): short facts -> her facts (`yaad.save_fact`, source
`import:<from>`, global, the same privacy filter as every fact: no money, ID numbers, secrets, health / caste /
religion unless she switched sensitive topics on); long notes, daily logs and past chats -> her memory index
(`yaad.add_item`, kind `import`), found by past-chat search like her own chats; skills -> her skill library
(`skills_store.install`, never overwriting one she has).

Never brought in: keys, tokens, passwords, settings and session files (.env, auth.json, config.yaml, openclaw.json,
*.db) - they are not even read; anything coder/guard.py flags (hidden instructions, skipping her tap, sending her data
out, card / Aadhaar numbers, invisible characters); her old assistant's personality and rules files (Hoola keeps its
own - the name it went by is shown). Every import is kept as a record she can UNDO in one tap. Zips are opened safely:
no paths outside the archive, no links, at most 5,000 files / 200 MB unpacked / 5 MB a file.
"""
from __future__ import annotations

import io
import json
import logging
import re
import secrets
import threading
import time
import zipfile
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, new_id, now, session

log = logging.getLogger("santosh.migrate")

LABELS = {"openclaw": "OpenClaw", "hermes": "Hermes", "chatgpt": "ChatGPT", "claude": "Claude", "text": "pasted text",
          "skills": "skill files"}
MAX_FILES, MAX_TOTAL, MAX_FILE, MAX_UPLOAD = 5000, 200 * 1024 * 1024, 5 * 1024 * 1024, 60 * 1024 * 1024
MAX_FACTS, MAX_NOTES, MAX_SKILLS, MAX_CHATS, MAX_EXCHANGES = 200, 3000, 100, 500, 4000
FACT_CHARS, NOTE_CHARS = 400, 900
TEXT_EXT = (".md", ".markdown", ".txt", ".json")
NEVER = re.compile(r"(?i)(^|/)(\.env(\..*)?|auth\.json|config\.ya?ml|openclaw\.json5?|credentials[^/]*|[^/]*\.db|"
                   r"[^/]*\.sqlite3?|mcp-tokens/.*|sessions?/.*|pairing/.*|logs?/.*|\.ssh/.*|[^/]*secret[^/]*)$")
PERSONA = re.compile(r"(?i)(^|/)(SOUL|AGENTS|IDENTITY|BOOT|BOOTSTRAP|TOOLS|HEARTBEAT|CLAUDE)\.md$")
DAILY = re.compile(r"(?i)(^|/)memory/(\d{4}-\d{2}-\d{2})[^/]*\.md$")
SECTION = re.compile(r"\n\s*§\s*\n")
_PENDING: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()
PENDING_S = 1800


class MemoryImport(Base):
    __tablename__ = "memory_imports"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    counts: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fact_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    item_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    undone_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_READY: set[int] = set()


def ensure_table() -> None:
    from . import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is None or id(eng) in _READY:
        return
    MemoryImport.__table__.create(bind=eng, checkfirst=True)
    _READY.add(id(eng))


class ImportError_(ValueError):
    pass


# ---------------------------------------------------------------- reading what she uploaded
def _clean_path(name: str) -> str | None:
    p = str(name or "").replace("\\", "/")
    if not p or p.endswith("/") or p.startswith("/") or re.match(r"^[A-Za-z]:", p):
        return None
    parts = [x for x in PurePosixPath(p).parts if x not in ("", ".")]
    if any(x == ".." for x in parts) or not parts:
        return None
    if parts[0] == "__MACOSX" or parts[-1].startswith("._"):
        return None
    return "/".join(parts)


def read_upload(files: list[tuple[str, bytes]]) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """{path: text} for the text files worth reading, and what was left out (and why)."""
    out: dict[str, str] = {}
    left: dict[str, int] = {}

    def skip(why: str) -> None:
        left[why] = left.get(why, 0) + 1

    def take(path: str | None, data: bytes) -> None:
        if path is None:
            return skip("a path outside the upload")
        if NEVER.search(path):
            return skip("settings, keys, passwords and session files (never read)")
        if not path.lower().endswith(TEXT_EXT):
            return skip("not a text file Hoola reads")
        if len(data) > MAX_FILE:
            return skip("a file over 5 MB")
        out[path] = data.decode("utf-8", errors="replace")

    total = 0
    for name, data in files:
        data = bytes(data or b"")
        if len(data) > MAX_UPLOAD:
            raise ImportError_("That upload is over 60 MB. Send the memory and skills folders only.")
        if zipfile.is_zipfile(io.BytesIO(data)):
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                infos = [i for i in z.infolist() if not i.is_dir()]
                if len(infos) > MAX_FILES:
                    raise ImportError_("That zip has more than 5,000 files. Send the memory and skills folders only.")
                for i in infos:
                    if (i.external_attr >> 16) & 0o170000 == 0o120000:
                        skip("a link inside the zip")
                        continue
                    total += i.file_size
                    if total > MAX_TOTAL:
                        raise ImportError_("That zip unpacks to more than 200 MB. Send the memory and skills folders only.")
                    if i.file_size > MAX_FILE:
                        skip("a file over 5 MB")
                        continue
                    p = _clean_path(i.filename)
                    if p and (NEVER.search(p) or not p.lower().endswith(TEXT_EXT)):
                        take(p, b"")
                        continue
                    take(p, z.read(i))
        else:
            take(_clean_path(PurePosixPath(str(name or "file.txt")).name), data)
    return out, [{"what": k, "n": v} for k, v in left.items()]


# ---------------------------------------------------------------- what kind of export it is
def _has(paths: list[str], rx: str) -> bool:
    r = re.compile(rx, re.I)
    return any(r.search(p) for p in paths)


def detect(files: dict[str, str], hint: str = "") -> str:
    if hint in LABELS and hint != "skills":
        return hint
    paths = list(files)
    if _has(paths, r"(^|/)memories/(MEMORY|USER)\.md$"):
        return "hermes"
    conv = next((t for p, t in files.items() if p.lower().endswith("conversations.json")), None)
    if conv:
        head = conv[:200000]
        if '"chat_messages"' in head:
            return "claude"
        if '"mapping"' in head:
            return "chatgpt"
    if _has(paths, r"(^|/)(MEMORY|USER|IDENTITY)\.md$") or _has(paths, DAILY.pattern):
        return "openclaw"
    if _has(paths, r"(^|/)SKILL\.md$"):
        return "skills"
    return "text"


# ---------------------------------------------------------------- turning files into pieces
def _strip_md(line: str) -> str:
    s = re.sub(r"^\s{0,6}([-*+]|\d{1,3}[.)])\s+", "", line)
    s = re.sub(r"^\s*>\s?", "", s)
    s = re.sub(r"\*\*|__|`", "", s)
    return " ".join(s.split())


def pieces(text: str, sep: str = "") -> list[str]:
    """A memory file -> its separate entries (Hermes: the section-sign line; else bullets / lines / paragraphs)."""
    t = (text or "").replace("\r\n", "\n")
    t = re.sub(r"^---\n.*?\n---\n", "", t, flags=re.S)            # front matter
    blocks = SECTION.split(t) if (sep == "section" or SECTION.search(t)) else re.split(r"\n\s*\n", t)
    out: list[str] = []
    for b in blocks:
        lines = [ln for ln in b.split("\n") if ln.strip() and not re.match(r"^\s*(#{1,6}\s|<!--|-->|```|---\s*$)", ln)]
        if not lines:
            continue
        bullet = sum(bool(re.match(r"^\s{0,6}([-*+]|\d{1,3}[.)])\s+", ln)) for ln in lines) >= max(2, len(lines) // 2)
        if bullet:
            cur = ""
            for ln in lines:
                if re.match(r"^\s{0,6}([-*+]|\d{1,3}[.)])\s+", ln):
                    if cur:
                        out.append(cur)
                    cur = _strip_md(ln)
                else:
                    cur = (cur + " " + _strip_md(ln)).strip()
            if cur:
                out.append(cur)
        else:
            out.append(" ".join(_strip_md(ln) for ln in lines))
    return [p for p in (x.strip() for x in out) if len(p) >= 6]


def _front(text: str) -> tuple[dict[str, str], str]:
    m = re.match(r"^﻿?---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text or "", re.S)
    if not m:
        return {}, text or ""
    head: dict[str, str] = {}
    for ln in m.group(1).splitlines():
        kv = re.match(r"^(\w[\w-]*)\s*:\s*(.*)$", ln)
        if kv:
            head[kv.group(1).lower()] = kv.group(2).strip().strip("\"'")
    return head, m.group(2)


def _skill_name(raw: str) -> str:
    n = re.sub(r"[^a-z0-9]+", "-", str(raw or "").lower()).strip("-")
    return n[:64].strip("-")


def _ts(v: Any) -> datetime | None:
    try:
        if isinstance(v, (int, float)) and v > 0:
            return datetime.fromtimestamp(float(v), tz=timezone.utc)
        if isinstance(v, str) and v:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except (ValueError, OSError, OverflowError):
        return None
    return None


def _chatgpt(text: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(text)
    except ValueError:
        return []
    chats = []
    for c in (data if isinstance(data, list) else [])[:MAX_CHATS]:
        if not isinstance(c, dict):
            continue
        msgs = []
        for node in (c.get("mapping") or {}).values():
            m = (node or {}).get("message") or {}
            role = ((m.get("author") or {}).get("role") or "")
            parts = (m.get("content") or {}).get("parts") or []
            body = " ".join(str(p) for p in parts if isinstance(p, str)).strip()
            if role in ("user", "assistant") and body:
                msgs.append((m.get("create_time") or 0, role, body))
        msgs.sort(key=lambda x: x[0] or 0)
        chats.append({"title": str(c.get("title") or "Untitled chat")[:120], "at": _ts(c.get("create_time")),
                      "msgs": [(r, b) for _, r, b in msgs]})
    return chats


def _claude(text: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(text)
    except ValueError:
        return []
    chats = []
    for c in (data if isinstance(data, list) else [])[:MAX_CHATS]:
        if not isinstance(c, dict):
            continue
        msgs = []
        for m in c.get("chat_messages") or []:
            if not isinstance(m, dict):
                continue
            body = str(m.get("text") or "").strip()
            if not body:
                body = " ".join(str(x.get("text") or "") for x in (m.get("content") or []) if isinstance(x, dict)).strip()
            role = {"human": "user", "assistant": "assistant"}.get(str(m.get("sender") or ""), "")
            if role and body:
                msgs.append((role, body))
        chats.append({"title": str(c.get("name") or "Untitled chat")[:120], "at": _ts(c.get("created_at")), "msgs": msgs})
    return chats


def _exchanges(chat: dict[str, Any], label: str) -> list[str]:
    out, her = [], ""
    for role, body in chat["msgs"]:
        if role == "user":
            if her:
                out.append(f"{label} chat “{chat['title']}” - she asked: {her[:500]}")
            her = body
        elif her:
            out.append(f"{label} chat “{chat['title']}” - she asked: {her[:500]} | reply: {body[:340]}")
            her = ""
    if her:
        out.append(f"{label} chat “{chat['title']}” - she asked: {her[:500]}")
    return out[:40]


# ---------------------------------------------------------------- the plan she sees
def build(tenant: str, files: dict[str, str], text: str = "", hint: str = "") -> dict[str, Any]:
    """What WOULD come in. Nothing is written."""
    from . import yaad
    from .coder import guard
    src = detect(files, hint) if files else ("text" if (text or "").strip() else hint or "text")
    try:
        from .fence import prefs
        sens = bool(prefs(tenant).get("sensitive"))
    except Exception:  # noqa: BLE001
        sens = False
    facts: list[str] = []
    notes: list[dict[str, Any]] = []
    skills: list[dict[str, str]] = []
    skipped: dict[str, int] = {}
    persona: dict[str, Any] = {"files": [], "name": ""}
    known = yaad._known(tenant, 2000) if tenant else []
    try:
        from .coder import skills_store
        have = {s["name"] for s in skills_store.listing(tenant)}
    except Exception:  # noqa: BLE001
        have = set()

    def no(why: str) -> None:
        skipped[why] = skipped.get(why, 0) + 1

    def check(piece: str) -> bool:
        hit = guard.scan(piece)
        if hit:
            no({"injection": "looked like an instruction to override your rules",
                "her_tap": "tried to skip your approval", "leaving": "tried to send your data somewhere",
                "secret": "had a key, password, card or ID number", "hidden": "had hidden characters"}.get(hit[0], "unsafe"))
            return False
        return True

    def fact(piece: str, where: str) -> None:
        p = piece.strip()
        if len(p) > FACT_CHARS:
            return note(p, where, None)
        if not check(p):
            return
        why = yaad.fact_ok(p, sens)
        if why:
            no({"secret": "had a key, password, card or ID number", "number": "had an ID number",
                "money_or_secret": "was about money or a secret", "money": "was about money",
                "health": "was about health (turn on sensitive topics to keep these)",
                "sensitive": "was a sensitive topic (turn on sensitive topics to keep these)",
                "too_short": "too short to be useful"}.get(why, "not kept by Hoola's memory rules"))
            return
        if p in facts or yaad.is_dupe(tenant, p, known):
            no("you already have it")
            return
        if len(facts) >= MAX_FACTS:
            return note(p, where, None)
        facts.append(p)

    def note(piece: str, where: str, at: datetime | None) -> None:
        if len(notes) >= MAX_NOTES:
            no("over the 3,000-note limit for one import")
            return
        if not check(piece):
            return
        for i in range(0, min(len(piece), NOTE_CHARS * 4), NOTE_CHARS):
            notes.append({"text": f"[{where}] " + piece[i:i + NOTE_CHARS], "at": at})

    label = LABELS.get(src, "Imported")
    for path, body in sorted(files.items()):
        low = path.lower()
        if low.endswith("skill.md"):
            if len(skills) >= MAX_SKILLS:
                no("over the 100-skill limit for one import")
                continue
            head, rest = _front(body)
            parent = PurePosixPath(path).parent.name
            name = _skill_name(head.get("name") or parent or "imported-skill")
            desc = " ".join((head.get("description") or "").split())[:1024]
            if not name or not rest.strip() or not desc:
                no("a skill file with no name, description or steps")
                continue
            if not check(f"{name}\n{desc}\n{rest}"):
                continue
            if name in have or any(s["name"] == name for s in skills):
                no("you already have a skill with that name")
                continue
            skills.append({"name": name, "description": desc, "body": rest.strip()[:30000], "from": path})
            continue
        if PERSONA.search(path):
            persona["files"].append(PurePosixPath(path).name)
            if low.endswith("identity.md"):
                m = re.search(r"(?im)^\s*(?:[-*]\s*)?\**name\**\s*[:\-]\s*\**([^\n*]{1,40})", body)
                persona["name"] = (m.group(1).strip() if m else persona["name"])
            continue
        if low.endswith("conversations.json"):
            chats = _claude(body) if src == "claude" else _chatgpt(body)
            n = 0
            for c in chats:
                for ex in _exchanges(c, label):
                    if n >= MAX_EXCHANGES:
                        no("over the 4,000-exchange limit for one import")
                        break
                    if check(ex):
                        notes.append({"text": ex[:NOTE_CHARS], "at": c["at"]})
                        n += 1
            persona["chats"] = len(chats)
            continue
        if low.endswith(".json"):
            continue                                       # other export files (user.json, feedback...) carry no memory
        d = DAILY.search(path)
        if d:
            at = _ts(d.group(2) + "T12:00:00+00:00")
            for p in pieces(body):
                note(p, f"{label} note {d.group(2)}", at)
            continue
        is_user = bool(re.search(r"(?i)(^|/)USER\.md$", path))
        is_mem = bool(re.search(r"(?i)(^|/)MEMORY\.md$", path))
        for p in pieces(body, "section" if src == "hermes" else ""):
            if is_user or is_mem:
                fact(p, f"{label} memory")
            else:
                note(p, f"{label} file {PurePosixPath(path).name}", None)
    for line in (text or "").splitlines():
        ln = _strip_md(line)
        if len(ln) >= 6:
            fact(ln, label)
    return {"source": src, "label": label, "facts": facts, "notes": notes, "skills": skills,
            "skipped": [{"what": k, "n": v} for k, v in sorted(skipped.items(), key=lambda kv: -kv[1])],
            "persona": persona}


def preview(tenant: str, files: list[tuple[str, bytes]], text: str = "", hint: str = "") -> dict[str, Any]:
    if not files and not (text or "").strip():
        raise ImportError_("Upload your old assistant's files (a .zip is fine) or paste your memories.")
    got, left = read_upload(files)
    plan = build(tenant, got, text, hint)
    if not (plan["facts"] or plan["notes"] or plan["skills"]):
        why = "; ".join(f"{x['n']} {x['what']}" for x in (plan["skipped"] + left)[:4])
        raise ImportError_("Nothing in that upload could be brought in" + (f" ({why})." if why else
                           ". For OpenClaw send your workspace folder, for Hermes your .hermes folder, for ChatGPT or "
                           "Claude the data export zip."))
    token = secrets.token_urlsafe(18)
    with _LOCK:
        now_s = time.time()
        for k in [k for k, v in _PENDING.items() if v["exp"] < now_s]:
            _PENDING.pop(k, None)
        _PENDING[token] = {"tenant": tenant, "plan": plan, "exp": now_s + PENDING_S}
    return {"token": token, "source": plan["source"], "label": plan["label"],
            "counts": {"facts": len(plan["facts"]), "notes": len(plan["notes"]), "skills": len(plan["skills"])},
            "facts": plan["facts"][:60], "skills": [{"name": s["name"], "description": s["description"][:200]}
                                                    for s in plan["skills"][:40]],
            "notes_sample": [n["text"][:200] for n in plan["notes"][:5]], "chats": plan["persona"].get("chats", 0),
            "skipped": plan["skipped"] + left, "persona": {"name": plan["persona"]["name"],
                                                           "files": plan["persona"]["files"][:10]}}


def apply(tenant: str, token: str) -> dict[str, Any]:
    """Her tap: the plan she saw comes in. Returns the import record."""
    from . import yaad
    with _LOCK:
        pend = _PENDING.pop(str(token or ""), None)
    if not pend or pend["tenant"] != tenant or pend["exp"] < time.time():
        raise ImportError_("That preview has expired. Upload the files again.")
    plan = pend["plan"]
    ensure_table()
    rec_id = new_id("imp")
    fact_ids, item_ids, skill_names, failed = [], [], [], 0
    for f in plan["facts"]:
        r = yaad.save_fact(tenant, f, source=f"import:{plan['source']}"[:20])
        if r and r.get("id"):
            fact_ids.append(int(r["id"]))
    for i, n in enumerate(plan["notes"]):
        rid = yaad.add_item(tenant, "import", n["text"], ref=f"imp:{rec_id}:{i}", at=n.get("at"))
        if rid:
            item_ids.append(int(rid))
    if plan["skills"]:
        from .coder import skills_store
        for s in plan["skills"]:
            try:
                skills_store.install(tenant, s["name"], s["description"], s["body"], extra={"source": plan["label"]})
                skill_names.append(s["name"])
            except Exception as e:  # noqa: BLE001 - one bad skill never sinks the import
                failed += 1
                log.info("import skill %s not installed: %s", s["name"], e)
    counts = {"facts": len(fact_ids), "notes": len(item_ids), "skills": len(skill_names), "failed": failed}
    with session() as s:
        s.add(MemoryImport(id=rec_id, tenant_id=tenant, source=plan["source"], counts=counts, fact_ids=fact_ids,
                           item_ids=item_ids, skills=skill_names))
    return {"id": rec_id, "source": plan["source"], "label": plan["label"], "counts": counts,
            "said": f"Brought in {counts['facts']} facts, {counts['notes']} notes and past chats, and "
                    f"{counts['skills']} skills from {plan['label']}."}


def imports(tenant: str) -> list[dict[str, Any]]:
    ensure_table()
    with session() as s:
        rows = s.scalars(select(MemoryImport).where(MemoryImport.tenant_id == tenant)
                         .order_by(MemoryImport.created_at.desc()).limit(30)).all()
        return [{"id": r.id, "source": r.source, "label": LABELS.get(r.source, r.source), "counts": r.counts or {},
                 "at": r.created_at.isoformat() if r.created_at else "", "undone": r.undone_at is not None} for r in rows]


def undo(tenant: str, import_id: str) -> dict[str, Any]:
    """Takes one import back out: its facts, notes and skills (a fact or skill she changed since stays as it is now
    only if it was pinned - her pinned facts are hers)."""
    from . import yaad
    from .yaad import YaadItem
    ensure_table()
    with session() as s:
        r = s.get(MemoryImport, str(import_id))
        if r is None or r.tenant_id != tenant:
            raise ImportError_("No such import.")
        if r.undone_at is not None:
            return {"ok": True, "already": True}
        fids, iids, names = list(r.fact_ids or []), list(r.item_ids or []), list(r.skills or [])
    removed = {"facts": 0, "notes": 0, "skills": 0}
    for fid in fids:
        if yaad.retire_fact(tenant, fid):
            removed["facts"] += 1
    with session() as s:
        for iid in iids:
            it = s.get(YaadItem, iid)
            if it is not None and it.tenant_id == tenant and str(it.ref or "").startswith(f"imp:{import_id}:"):
                s.delete(it)
                removed["notes"] += 1
    if names:
        from .coder import skills_store
        for n in names:
            try:
                skills_store.read(tenant, n)
                skills_store.delete(tenant, n)
                removed["skills"] += 1
            except Exception:  # noqa: BLE001 - already gone
                continue
    with session() as s:
        r = s.get(MemoryImport, str(import_id))
        if r is not None:
            r.undone_at = now()
    return {"ok": True, "removed": removed}
