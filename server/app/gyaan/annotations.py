"""v0.512 Gyaan Annotations — her APPROVED jawabs (the Dify annotation-reply idea, rebuilt house-sized).

From the Dify READ (langgenius/dify @ 1.19.0, their 'annotations' / annotation-reply feature):
her most-asked questions get THE answer she approved, before any retrieval spends a token.
ZERO Dify code is here — their modified-Apache license bans multi-tenant use of the source and
the house is multi-tenant by birth. What is kept is the IDEA, on the gyaan rails.

How it works:
- she saves an approved answer for a question (`gyaan action=save_answer question=... text=...`);
- every gyaan_khojo ask checks these pairs FIRST: normalized exact match, else a difflib fuzzy
  match (stdlib, no new pip) at `gyaan_annotation_fuzzy` (default 0.92);
- a hit returns ONE source titled "Aapka approved jawab" with the save-date — honest provenance:
  she wrote it, it is not a live tool result and never claims to be one;
- a miss NEVER blocks: retrieval runs exactly as before.

Laws (enforced here, not in the prompt):
- only she (owner / approved:) writes — the gyaan tool's own gate stands before this is reached;
- every stored answer passes the house redaction (`norm.mask`): no Aadhaar / PAN / card /
  bank-account / OTP ever reaches the store;
- one tenant's pairs live in her own gyaan sqlite — another tenant's ask can never hit them;
- caps: `gyaan_annotation_max` pairs per tenant (default 200), question <= 500 chars,
  answer <= 4000 chars;
- enabled=false pairs are skipped; a pair can be switched off without deleting it;
- same normalized question asked again = the answer is REPLACED (one question, one approved jawab).

Counting: every hit bumps the pair's `hits` / `last_hit_at` and this module's STATS, so the
answer's use is visible (`gyaan action=answers` shows them). No evalset row is written here —
annotation quality rides the pair counters, honestly.
"""
from __future__ import annotations

import difflib
import json
import re
import time
import uuid
from typing import Any

from . import norm, store

STATS = {"saves": 0, "matches": 0, "exact": 0, "fuzzy": 0, "misses": 0}

_Q_CHARS = 500
_A_CHARS = 4000
_TABLE = ("CREATE TABLE IF NOT EXISTS gyaan_pairs (id TEXT PRIMARY KEY, q_norm TEXT, q_raw TEXT, "
          "answer TEXT, note TEXT, enabled INTEGER DEFAULT 1, hits INTEGER DEFAULT 0, "
          "last_hit_at REAL, created_at REAL, updated_at REAL)")
_INDEX = "CREATE INDEX IF NOT EXISTS gyaan_pairs_q ON gyaan_pairs (q_norm)"


def _cfg(key: str, default: Any) -> Any:
    from ..config import get_settings
    return getattr(get_settings(), key, default)


def q_norm(q: str) -> str:
    """The question's matching key: ASCII digits, lowercase, punctuation out, whitespace collapsed."""
    t = norm.ascii_digits(q or "").lower()
    t = re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)
    return re.sub(r"\s+", " ", t).strip()


# ---------------------------------------------------------------- store (in her own gyaan sqlite)

def save(tenant: str, question: str, answer: str, note: str = "") -> dict[str, Any]:
    question = (question or "").strip()
    answer = (answer or "").strip()
    if not question or not answer:
        return {"ok": False, "error": "both question and answer are needed"}
    if len(question) > _Q_CHARS:
        return {"ok": False, "error": f"question is too long ({len(question)} chars; cap {_Q_CHARS})"}
    if len(answer) > _A_CHARS:
        return {"ok": False, "error": f"answer is too long ({len(answer)} chars; cap {_A_CHARS})"}
    # the house redaction before anything is stored: no Aadhaar / PAN / card / bank / OTP ever lands
    answer, masked = norm.mask(answer)
    question, q_masked = norm.mask(question)
    masked = sorted(set(masked) | set(q_masked))
    max_pairs = int(_cfg("gyaan_annotation_max", 200) or 200)
    nq = q_norm(question)
    now_ = time.time()
    with store.db(tenant, write=True) as c:
        c.execute(_TABLE)
        c.execute(_INDEX)
        n = c.execute("SELECT COUNT(*) FROM gyaan_pairs").fetchone()[0]
        old = c.execute("SELECT id FROM gyaan_pairs WHERE q_norm = ?", (nq,)).fetchone()
        if old is None and n >= max_pairs:
            return {"ok": False, "error": f"the limit of approved answers ({max_pairs}) is full — "
                                          "remove an old one, then save the new one"}
        if old is not None:
            c.execute("UPDATE gyaan_pairs SET q_raw = ?, answer = ?, note = ?, updated_at = ? WHERE id = ?",
                      (question, answer, (note or "")[:300], now_, old["id"]))
            pid = old["id"]
            created = False
        else:
            pid = "pa_" + uuid.uuid4().hex[:12]
            c.execute("INSERT INTO gyaan_pairs (id, q_norm, q_raw, answer, note, enabled, created_at, updated_at) "
                      "VALUES (?,?,?,?,?,1,?,?)", (pid, nq, question, answer, (note or "")[:300], now_, now_))
            created = True
        STATS["saves"] += 1
    out = {"ok": True, "id": pid, "created": created, "question": question, "answer": answer[:200],
           "masked": masked, "note": ("Answer updated (the same question was already approved)" if not created
                                      else "Approved answer saved — when this question is asked, this answer comes first")}
    return out


def list_pairs(tenant: str, limit: int = 50) -> list[dict[str, Any]]:
    with store.db(tenant) as c:
        c.execute(_TABLE)
        rows = c.execute("SELECT * FROM gyaan_pairs ORDER BY updated_at DESC LIMIT ?",
                         (max(1, min(int(limit), 100)),)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["enabled"] = bool(d.get("enabled"))
        d["saved_at"] = time.strftime("%Y-%m-%d", time.localtime(d["updated_at"])) if d.get("updated_at") else ""
        out.append(d)
    return out


def delete(tenant: str, pair_id: str) -> dict[str, Any]:
    with store.db(tenant, write=True) as c:
        c.execute(_TABLE)
        gone = c.execute("DELETE FROM gyaan_pairs WHERE id = ?", (pair_id,)).rowcount
    if not gone:
        return {"ok": False, "error": "pair_id not found (see the ids with gyaan action=answers)"}
    return {"ok": True, "deleted": pair_id, "note": "Approved answer removed"}


def set_enabled(tenant: str, pair_id: str, enabled: bool) -> dict[str, Any]:
    with store.db(tenant, write=True) as c:
        c.execute(_TABLE)
        n = c.execute("UPDATE gyaan_pairs SET enabled = ?, updated_at = ? WHERE id = ?",
                      (1 if enabled else 0, time.time(), pair_id)).rowcount
    if not n:
        return {"ok": False, "error": "pair_id not found"}
    return {"ok": True, "id": pair_id, "enabled": enabled}


# ---------------------------------------------------------------- the match (runs BEFORE retrieval)

def _hit_card(pair: dict[str, Any]) -> dict[str, Any]:
    """A gyaan-shaped hit: flows through answer.register like any source, but the provenance
    line says exactly what it is — HER approved answer, not a document, not a live result."""
    return {"chunk_id": "ann_" + str(pair["id"]), "doc_id": "annotations", "title": "Your approved answer",
            "source": "answer", "kind": "answer", "page": 0,
            "at": time.strftime("%Y-%m-%d", time.localtime(pair.get("updated_at") or time.time())),
            "text": str(pair.get("answer") or ""), "link": "", "file_id": "",
            "fused": 1.0, "cover": 1.0, "cos": 1.0, "exact": True, "why": ["annotation"], "named": False}


def match(tenant: str, query: str) -> dict[str, Any]:
    """One check, two tiers: exact on the normalized question, else difflib fuzzy >= threshold.
    Returns {"hit": bool, "hit_card": {...}, "pair_id", "how"} — or {"hit": False} honestly."""
    query = (query or "").strip()
    if not query or not _cfg("gyaan_annotation_enabled", True):
        STATS["misses"] += 1
        return {"hit": False}
    nq = q_norm(query)
    if not nq:
        STATS["misses"] += 1
        return {"hit": False}
    with store.db(tenant) as c:
        c.execute(_TABLE)
        rows = c.execute("SELECT * FROM gyaan_pairs WHERE enabled = 1").fetchall()
    if not rows:
        STATS["misses"] += 1
        return {"hit": False}
    best, best_score, how = None, 0.0, ""
    for r in rows:
        pq = r["q_norm"] or ""
        if pq == nq:
            best, best_score, how = dict(r), 1.0, "exact"
            break
        ratio = difflib.SequenceMatcher(None, nq, pq).ratio()
        if ratio > best_score:
            best, best_score, how = dict(r), ratio, "fuzzy"
    thr = float(_cfg("gyaan_annotation_fuzzy", 0.92) or 0.92)
    if best is None or (how != "exact" and best_score < thr):
        STATS["misses"] += 1
        return {"hit": False}
    with store.db(tenant, write=True) as c:
        c.execute("UPDATE gyaan_pairs SET hits = hits + 1, last_hit_at = ? WHERE id = ?",
                  (time.time(), best["id"]))
    STATS["matches"] += 1
    STATS[how] += 1
    return {"hit": True, "hit_card": _hit_card(best), "pair_id": best["id"], "how": how,
            "score": round(best_score, 3), "q_raw": best.get("q_raw") or "",
            "saved_on": time.strftime("%Y-%m-%d", time.localtime(best.get("updated_at") or time.time()))}


def status(tenant: str) -> dict[str, Any]:
    with store.db(tenant) as c:
        c.execute(_TABLE)
        n = c.execute("SELECT COUNT(*) FROM gyaan_pairs").fetchone()[0]
        on = c.execute("SELECT COUNT(*) FROM gyaan_pairs WHERE enabled = 1").fetchone()[0]
    return {"pairs": n, "enabled": on, "cap": int(_cfg("gyaan_annotation_max", 200) or 200),
            "fuzzy": float(_cfg("gyaan_annotation_fuzzy", 0.92) or 0.92), "stats": dict(STATS)}
