"""v0.605 EK YAAD - ONE memory door, the way Claude has one memory per scope.

Hoola's memory grew in six places over the versions: her facts (memory_facts), the chat index (yaad_items), the
Coder vault (observations), the knowledge graph (kgmemory), her "Mere baare mein" page and the workspace. Each
store kept its own search, its own forget and its own view, which is exactly how v0.603's three bugs happened
(an incognito leak, two versions of one fact, a forget that missed the copies).

The stores stay where they are - moving live rows between tables would risk her data for no gain - but every
question about her memory now goes through THIS door:

- search_all  : one search across every store, each hit labelled with where it came from (the one tool the model
                calls - Claude's own pattern: past chats are looked up by a tool call, just in time, never pasted
                into every message);
- everything  : one view of all she has told Hoola, per store, for the memory screen;
- reset_all   : one "reset everything" (Claude's reset) - facts, chat index, Coder vault, graph, page. Her chats
                themselves are never deleted.

Every rule the stores already keep holds here: the Session fence (fence.chats_in), her "Purani chats se yaad"
switch, incognito chats never a source. The workspace is left out on purpose: it holds her working FILES, not
memory, and its own tool reads them.
"""
from __future__ import annotations

import logging
import re
from typing import Any

log = logging.getLogger("santosh.memory")

CAPS = {"fact": 6, "chat": 6, "work": 4, "graph": 4, "page": 3, "diary": 5}   # per-store share of one answer
LABELS = {"fact": "saved fact", "chat": "past chat / call / job", "work": "work note (Coder memory)",
          "graph": "knowledge graph", "page": "Mere baare mein",
          "diary": "work diary (jobs, website jobs, files, calls)"}
DIARY_SEARCH_DAYS = 30   # parity Phase 7: the diary left the chat turn, so its search looks further back than its 7 days


def _words(q: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9ऀ-ॿ]+", (q or "").lower()) if len(w) > 2}


def _facts(tenant: str, conv: str, query: str) -> list[dict]:
    from . import yaad
    hits = yaad.relevant_facts(tenant, query, None, top=CAPS["fact"], conversation_id=conv)
    return [{"source": "fact", "id": i, "text": t} for i, t in hits]


def _chats(tenant: str, conv: str, query: str, days: int | None) -> list[dict]:
    from . import yaad
    from .fence import prefs
    if not prefs(tenant)["recall"]:        # her "Purani chats se yaad" switch
        return []
    hits = yaad.search(tenant, query, CAPS["chat"], days or None, None, conversation_id=conv)
    titles = _titles({h.get("conversation_id") for h in hits if h.get("conversation_id")})
    return [{"source": "chat", "kind": h.get("kind"), "when": h.get("at"), "conversation_id": h.get("conversation_id"),
             **({"chat_title": titles[h.get("conversation_id")]} if titles.get(h.get("conversation_id")) else {}),
             "text": str(h.get("text") or "")[:600]} for h in hits]


def _titles(ids: set) -> dict:
    """parity Phase 7: a past-chat hit names its chat, so she can be told where it was said ('your chat "Sharma
    quotation"')."""
    if not ids:
        return {}
    try:
        from sqlalchemy import select
        from .db import Conversation, session
        with session() as s:
            return {c.id: (c.title or "").strip() for c in
                    s.scalars(select(Conversation).where(Conversation.id.in_(list(ids)))).all()}
    except Exception:
        return {}


def _diary(tenant: str, conv: str, query: str, days: int | None) -> list[dict]:
    """parity Phase 7: the work diary (her jobs, website jobs / orders, files, call receipts) used to ride every chat
    turn; now it is searched like every other store. Fenced to this chat's Session like the diary itself."""
    from . import semantic, yaad
    d = yaad.diary(tenant, conv, days=min(int(days or DIARY_SEARCH_DAYS), 90))
    lines = [(f"{k}:{i}", ln) for k in ("jobs", "web", "files", "calls") for i, ln in enumerate(d.get(k) or [])]
    if not lines:
        return []
    want = _words(query)
    scored = []
    for key, ln in lines:
        hit = len(want & _words(ln))
        if hit:
            scored.append((hit / max(1, len(want)), key, ln))
    if not scored and semantic.available():
        scored = [(sc, k, t) for k, t, sc in semantic.rank(query, lines, top=CAPS["diary"], floor=0.42)]
    scored.sort(key=lambda x: -x[0])
    return [{"source": "diary", "kind": key.split(":")[0], "text": ln} for _, key, ln in scored[:CAPS["diary"]]]


def _work(tenant: str, conv: str, query: str) -> list[dict]:
    from .config import get_settings
    if not getattr(get_settings(), "coder_enabled", True):
        return []
    from .coder import search as cs
    from .fence import chats_in
    allowed = chats_in(tenant, conv) if conv else None
    rows = cs.search(tenant, query, limit=CAPS["work"] * 3).get("observations") or []
    if allowed is not None:                # the Session fence holds for the Coder vault too
        rows = [r for r in rows if r.get("conv") in allowed]
    full = {o["id"]: o for o in cs.get_observations([r["id"] for r in rows[:CAPS["work"]]])}
    out = []
    for r in rows[:CAPS["work"]]:
        o = full.get(r["id"], r)
        text = " - ".join(x for x in (o.get("title"), o.get("subtitle"), str(o.get("narrative") or "")[:300]) if x)
        out.append({"source": "work", "id": r["id"], "when": r.get("created_at"), "text": text})
    return out


def _graph(tenant: str, query: str) -> list[dict]:
    from .agent import sandarbh_tools as S
    if not S._kg_path(tenant).exists():
        return []
    want = _words(query)
    if not want:
        return []
    con = S._kg_con(tenant)
    try:
        rows = con.execute("SELECT o.entity, o.text, e.type FROM observations o "
                           "LEFT JOIN entities e ON e.name = o.entity").fetchall()
    finally:
        con.close()
    scored = []
    for r in rows:
        text = f"{r['entity']} ({r['type'] or 'thing'}): {r['text']}"
        hit = len(want & _words(text))
        if hit:
            scored.append((hit / len(want), text))
    scored.sort(key=lambda x: -x[0])
    return [{"source": "graph", "text": t} for _, t in scored[:CAPS["graph"]]]


def _page(tenant: str, query: str) -> list[dict]:
    from . import aboutme, semantic
    from .fence import prefs
    if not prefs(tenant)["recall"]:
        return []
    lines = [ln.strip() for ln in (aboutme.get(tenant)["text"] or "").split("\n") if len(ln.strip()) > 8]
    ranked = semantic.rank(query, list(enumerate(lines)), top=CAPS["page"],
                           floor=0.42 if semantic.available() else 0.34)
    return [{"source": "page", "text": t} for _, t, _ in ranked]


def search_all(tenant: str, conversation_id: str, query: str, days: int | None = None,
               only: str = "any") -> dict[str, Any]:
    """Every store, one answer. A store that fails is named in `skipped`, never fatal."""
    if not (query or "").strip():
        return {"hits": [], "count": 0, "searched": []}
    from .fence import main_memory_ok
    main = main_memory_ok(conversation_id)   # v0.609 a Session on its own memory: no main page, no main graph
    jobs = {"fact": lambda: _facts(tenant, conversation_id, query),
            "chat": lambda: _chats(tenant, conversation_id, query, days),
            "diary": lambda: _diary(tenant, conversation_id, query, days),
            "work": lambda: _work(tenant, conversation_id, query),
            "graph": lambda: _graph(tenant, query) if main else [],
            "page": lambda: _page(tenant, query) if main else []}
    if only and only != "any":
        jobs = {k: v for k, v in jobs.items() if k == only}
    hits: list[dict] = []
    searched, skipped = [], []
    for name, job in jobs.items():
        try:
            got = job()
            searched.append(name)
            for h in got:
                h["from"] = LABELS[name]
            hits += got
        except Exception:
            log.exception("memory search: %s failed", name)
            skipped.append(name)
    return {"hits": hits, "count": len(hits), "searched": searched, **({"skipped": skipped} if skipped else {})}


def everything(tenant: str) -> dict[str, Any]:
    """One view of all of her memory, per store (the memory screen's 'sab kuch')."""
    from sqlalchemy import func, select
    from . import aboutme, life
    from .db import MemoryFact, session
    from .yaad import YaadItem
    out: dict[str, Any] = {}
    facts = life.memory_facts(tenant, 500)
    out["facts"] = [{"id": f.id, "text": f.text, "pinned": bool(f.pinned)} for f in facts]
    with session() as s:
        out["fact_count"] = s.scalar(select(func.count()).select_from(MemoryFact)
                                     .where(MemoryFact.tenant_id == tenant)) or 0
        out["chat_index_count"] = s.scalar(select(func.count()).select_from(YaadItem)
                                           .where(YaadItem.tenant_id == tenant)) or 0
    out["page"] = aboutme.get(tenant)["text"] or ""
    try:
        from .coder import store as cst
        cst.ensure()
        with cst.db() as c:
            out["work_notes"] = [dict(r) for r in c.execute(
                "SELECT id, title, created_at FROM observations WHERE tenant=? AND superseded_by=0 "
                "ORDER BY id DESC LIMIT 50", (tenant,)).fetchall()]
            out["work_note_count"] = c.execute("SELECT COUNT(*) FROM observations WHERE tenant=? "
                                               "AND superseded_by=0", (tenant,)).fetchone()[0]
    except Exception:
        log.exception("memory view: coder vault failed")
        out["work_notes"], out["work_note_count"] = [], 0
    try:
        from .agent import sandarbh_tools as S
        if S._kg_path(tenant).exists():
            con = S._kg_con(tenant)
            try:
                out["graph"] = [f"{r['entity']}: {r['text']}" for r in
                                con.execute("SELECT entity, text FROM observations ORDER BY id DESC LIMIT 50")]
                out["graph_count"] = con.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
            finally:
                con.close()
        else:
            out["graph"], out["graph_count"] = [], 0
    except Exception:
        log.exception("memory view: graph failed")
        out["graph"], out["graph_count"] = [], 0
    out["note"] = "Her chats themselves are not memory rows: they stay in her chat list until she deletes them."
    return out


def reset_all(tenant: str) -> dict[str, int]:
    """Claude's 'reset memory': every store forgets her - facts (pinned too), the chat index, the Coder vault's
    asks / tool rows / notes / summaries, the knowledge graph, the page. Her chats are NOT deleted, and her
    skills (how-to files she owns) are not memory and stay. Counts of what went."""
    from sqlalchemy import delete, select
    from .db import Conversation, MemoryFact, session
    from .yaad import YaadItem
    out = {"facts": 0, "chat_index": 0, "work": 0, "graph": 0, "page": 0}
    with session() as s:
        out["facts"] = s.execute(delete(MemoryFact).where(MemoryFact.tenant_id == tenant)).rowcount or 0
        out["chat_index"] = s.execute(delete(YaadItem).where(YaadItem.tenant_id == tenant)).rowcount or 0
        convs = set(s.scalars(select(Conversation.id).where(Conversation.tenant_id == tenant)).all())
    try:
        from .coder import store as cst
        cst.ensure()
        with cst.db() as c:
            convs |= {r[0] for r in c.execute(
                "SELECT conv FROM observations WHERE tenant=? UNION SELECT conv FROM tool_uses WHERE tenant=? "
                "UNION SELECT conv FROM sessions WHERE tenant=? UNION SELECT conv FROM summaries WHERE tenant=?",
                (tenant, tenant, tenant, tenant)).fetchall()}
        for conv in convs:
            got = cst.forget_conv(conv)
            out["work"] += got.get("observations", 0) + got.get("summaries", 0)
    except Exception:
        log.exception("memory reset: coder vault failed")
    try:
        from .agent import sandarbh_tools as S
        p = S._kg_path(tenant)
        if p.exists():
            con = S._kg_con(tenant)
            try:
                out["graph"] = con.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
            finally:
                con.close()
            p.unlink()
    except Exception:
        log.exception("memory reset: graph failed")
    try:
        from . import aboutme
        aboutme.ensure_table()
        from .db import session as _s
        with _s() as s:
            r = s.get(aboutme.AboutMe, tenant)
            if r is not None:
                s.delete(r)
                out["page"] = 1
    except Exception:
        log.exception("memory reset: page failed")
    log.info("memory reset for %s: %s", tenant, out)
    return out


def unremember(tenant: str, source: str, id: int | None = None, conversation_id: str = "", text: str = "") -> dict:
    """v0.612 YAAD SE: the 'Bhool jao' on one memory a reply used (Grok's remove-from-memory).
    fact = that fact and its copies; chat = that chat is never recalled again (it stays in her list - only its
    memory index goes); work = that work note; graph / page = the lines carrying the text."""
    from . import yaad
    from .db import Conversation, MemoryFact, session
    from .yaad import YaadItem
    from sqlalchemy import delete
    if source == "fact" and id:
        with session() as s:
            f = s.get(MemoryFact, int(id))
            if f is None or f.tenant_id != tenant:
                return {"ok": False, "why": "not found"}
            text = f.text
            s.delete(f)
        return {"ok": True, "source": "fact", "also_removed": yaad.forget_everywhere(tenant, text)}
    if source == "chat" and conversation_id:
        with session() as s:
            c = s.get(Conversation, conversation_id)
            if c is None or c.tenant_id != tenant:
                return {"ok": False, "why": "not found"}
            c.no_recall = True
            gone = s.execute(delete(YaadItem).where(YaadItem.tenant_id == tenant,
                                                    YaadItem.conversation_id == conversation_id)).rowcount or 0
        return {"ok": True, "source": "chat", "index_rows": gone,
                "note": "The chat itself stays in her list; it is never recalled into another chat."}
    if source == "work" and id:
        from .coder import store as cst
        cst.ensure()
        with cst.db(write=True) as c:
            n = c.execute("DELETE FROM observations WHERE id=? AND tenant=?", (int(id), tenant)).rowcount or 0
        return {"ok": bool(n), "source": "work"}
    if text:
        return {"ok": True, "source": source, "also_removed": yaad.forget_everywhere(tenant, text)}
    return {"ok": False, "why": "nothing to forget"}

