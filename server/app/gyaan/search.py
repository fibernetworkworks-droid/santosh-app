"""Gyaan search: one call, several cheap retrievers fused by rank, then a gate that says "nahi mila" instead of guessing.

  1. ID router   GSTIN / phone / IFSC / invoice codes / long numbers in the question -> exact SQL lookup (no model)
  2. BM25        FTS5 over whole Hindi / Marathi / English words, for the question AND the model's 2-3 rewrites
                 (Devanagari, Roman Hinglish, English) - the research's biggest Indic fix
  3. Trigram     FTS5 trigram over a spelling-forgiving Roman key (kya / kyaa, bijli / बिजली)
  4. Meaning     cosine over the owner's int8 vectors (same model as the chunks)
  5. Yaad        her chats and calls (Hoola ki yaad), not copied, searched in place
  6. Names       v0.135 people / firms the question names (any spelling / script) -> every chunk that names them
  -> reciprocal rank fusion (k = 60, no training) -> max 3 chunks per document -> optional API rerank (text chat only,
  never in a voice call) -> confidence gate (word coverage / meaning / exact ID / rerank score)."""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from . import ents, norm, store

log = logging.getLogger("santosh.gyaan")
K = 60
POOL = 50
_VC: dict[str, tuple] = {}
_VLOCK = threading.Lock()
_BACKFILLED: set[str] = set()
STATS = {"searches": 0, "found": 0, "nahi_mila": 0, "id_hits": 0, "reranked": 0, "ms_total": 0}


def drop_cache(tenant: str) -> None:
    with _VLOCK:
        _VC.pop(tenant, None)


def _matrix(tenant: str, c, model: str):
    import numpy as np
    from .embed import dequantize_rows
    ver = store.version(c)
    with _VLOCK:
        hit = _VC.get(tenant)
        if hit and hit[0] == ver and hit[1] == model:
            return hit[2], hit[3]
    rows = c.execute("SELECT chunk_id, dim, q, scale FROM vecs WHERE model=?", (model,)).fetchall()
    if not rows:
        return None, None
    dim = rows[0]["dim"]
    rows = [r for r in rows if r["dim"] == dim]
    ids = np.asarray([r["chunk_id"] for r in rows], dtype=np.int64)
    m = dequantize_rows([r["q"] for r in rows], [r["scale"] for r in rows], dim)
    n = np.linalg.norm(m, axis=1, keepdims=True)
    n[n == 0] = 1
    m = (m / n).astype(np.float32)
    with _VLOCK:
        _VC[tenant] = (ver, model, ids, m)
    return ids, m


def _fts_query(terms: list[str]) -> str:
    seen: list[str] = []
    for t in terms:
        t = t.replace('"', "").strip()
        if t and t not in seen:
            seen.append(t)
    return " OR ".join(f'"{t}"' for t in seen[:28])


def variants(query: str, queries: list[str] | None = None) -> list[str]:
    vs = [query] + [q for q in (queries or []) if isinstance(q, str) and q.strip()][:4]
    out: list[str] = []
    for v in vs:
        v = norm.ascii_digits(v.strip())
        if v and v not in out:
            out.append(v)
        if norm.has_devanagari(v):
            t = norm.translit(v)
            if t not in out:
                out.append(t)
    return out


def _coverage(qwords: list[list[str]], text: str) -> float:
    """Share of the question's content words found in the chunk (any script / spelling variant counts)."""
    if not qwords:
        return 0.0
    low = norm.ascii_digits(text).lower()
    ph = norm.phon(text)
    nums = set(norm.numbers(text))
    got = 0
    for alts in qwords:
        for w in alts:
            if w in low or (len(w) >= 3 and norm.phon(w) in ph) or (w.replace(".", "").isdigit() and w in nums):
                got += 1
                break
    return got / len(qwords)


def search(tenant: str, query: str, queries: list[str] | None = None, sources: list[str] | None = None,
           days: int | None = None, top: int = 8, fast: bool = False, memory: bool = True,
           conversation_id: str = "") -> dict[str, Any]:
    from ..config import get_settings
    st = get_settings()
    t0 = time.time()
    STATS["searches"] += 1
    query = (query or "").strip()
    if not query:
        return {"status": "nahi_mila", "hits": [], "say": "Kya dhoondhna hai, bataiye."}
    vs = variants(query, queries)
    # the question's content words, each with its spellings in the other variants (counted once)
    qwords: list[list[str]] = []
    for w in norm.words(query):
        qwords.append([w, norm.translit(w)])
    for v in vs[1:]:
        for w in norm.words(v):
            if not any(w in alts or norm.phon(w) == norm.phon(a) for alts in qwords for a in alts):
                qwords.append([w])
    lists: dict[str, list] = {}
    from . import embed
    e = embed.embedder()
    if tenant not in _BACKFILLED:                 # files added before v0.135 get their names once
        _BACKFILLED.add(tenant)
        try:
            from .ingest import ents_backfill
            ents_backfill(tenant)
        except Exception as ex:
            log.info("gyaan: name backfill skipped: %s", ex)
    names: list[str] = []
    with store.db(tenant) as c:
        # 1. exact identifiers
        idv = []
        for v in vs:
            idv += [x[1] for x in norm.ids(v)]
            idv += [n for n in re.findall(r"\d{5,18}", v)]
        idv = list(dict.fromkeys(idv))
        if idv:
            qs = ",".join("?" * len(idv))
            lists["id"] = [r[0] for r in c.execute(f"SELECT DISTINCT chunk_id FROM ids WHERE value IN ({qs}) LIMIT 30", idv)]
            if lists["id"]:
                STATS["id_hits"] += 1
        # 1b. names (people / firms) the question mentions
        try:
            eids, names = ents.match(c, vs)
            if eids:
                lists["name"] = eids
        except Exception as ex:
            log.info("gyaan name match failed: %s", ex)
        # 2. BM25 over whole words, all variants
        terms = [w for v in vs for w in norm.words(v)] + [n for v in vs for n in norm.numbers(v)]
        fq = _fts_query(terms)
        if fq:
            try:
                lists["bm25"] = [r[0] for r in c.execute("SELECT rowid FROM fts WHERE fts MATCH ? ORDER BY bm25(fts) LIMIT ?",
                                                         (fq, POOL))]
            except Exception as ex:
                log.info("gyaan fts query failed: %s", ex)
        # 3. trigram over the spelling-forgiving key
        if store.has_tri(c):
            tterms = [norm.phon(w) for v in vs for w in norm.words(v)]
            tq = _fts_query([t for t in tterms if len(t) >= 3])
            if tq:
                try:
                    lists["tri"] = [r[0] for r in c.execute("SELECT rowid FROM tri WHERE tri MATCH ? ORDER BY bm25(tri) LIMIT ?",
                                                            (tq, POOL))]
                except Exception as ex:
                    log.info("gyaan trigram query failed: %s", ex)
        # 4. meaning
        cos_of: dict[int, float] = {}
        if e is not None:
            ids_, m = _matrix(tenant, c, e.name)
            if ids_ is not None:
                qv, _ = embed.safe_embed([vs[0]] + vs[1:2], "query")
                if qv is not None:
                    import numpy as np
                    sims = m @ qv.T
                    best = sims.max(axis=1)
                    order = np.argsort(-best)[:POOL]
                    lists["meaning"] = [int(ids_[i]) for i in order]
                    cos_of = {int(ids_[i]): float(best[i]) for i in order}
        # fuse (an exact ID match counts double)
        score: dict[int, float] = {}
        why: dict[int, list[str]] = {}
        for name, lst in lists.items():
            w = 2.0 if name == "id" else (1.5 if name == "name" else 1.0)
            for rank, cid in enumerate(lst):
                score[cid] = score.get(cid, 0.0) + w / (K + rank + 1)
                why.setdefault(cid, []).append(name)
        cand = sorted(score, key=lambda x: -score[x])[:POOL]
        rows = {}
        if cand:
            qs = ",".join("?" * len(cand))
            for r in c.execute(f"SELECT c.id, c.doc_id, c.page, c.text, c.prefix, d.title, d.source, d.kind, d.at, d.added, d.meta, d.scope "
                               f"FROM chunks c JOIN docs d ON d.id=c.doc_id WHERE c.id IN ({qs})", cand):
                rows[r["id"]] = r
    since = (datetime.now(timezone.utc) - timedelta(days=days)) if days else None
    hits: list[dict[str, Any]] = []
    per_doc: dict[str, int] = {}
    for cid in cand:
        r = rows.get(cid)
        if r is None:
            continue
        if sources and r["source"] not in sources:
            continue
        if since:
            when = r["at"] or datetime.fromtimestamp(r["added"], timezone.utc).date().isoformat()
            if when and when < since.date().isoformat():
                continue
        if per_doc.get(r["doc_id"], 0) >= 3:
            continue
        per_doc[r["doc_id"]] = per_doc.get(r["doc_id"], 0) + 1
        meta = json.loads(r["meta"] or "{}")
        cover = _coverage(qwords, r["prefix"] + " " + r["text"])
        hits.append({"chunk_id": cid, "doc_id": r["doc_id"], "title": r["title"], "source": r["source"], "kind": r["kind"],
                     "page": r["page"], "at": r["at"], "text": r["text"], "link": meta.get("link", ""),
                     "file_id": meta.get("file_id", ""), "fused": round(score[cid], 5), "cover": round(cover, 2),
                     "cos": round(cos_of.get(cid, 0.0), 3), "exact": "id" in why.get(cid, []), "why": why.get(cid, []),
                     "named": "name" in why.get(cid, [])})
    # 5. her chats and calls (Hoola ki yaad), searched in place
    if memory and (not sources or "chat" in sources):
        try:
            from .. import yaad
            # v0.246 FENCE: from a chat, only chats of the same Session
            for i, y in enumerate(yaad.search(tenant, query, top=5, days=days, conversation_id=conversation_id)):
                cover = _coverage(qwords, y.get("text") or "")
                hits.append({"chunk_id": f"y{y.get('ref') or i}", "doc_id": "yaad", "title": "Pichhli baat (" + (y.get("kind") or "chat") + ")",
                             "source": "chat", "kind": y.get("kind") or "chat", "page": 0, "at": (y.get("at") or "")[:10],
                             "text": (y.get("text") or "")[:1500], "link": "", "file_id": "", "fused": 1.0 / (K + i + 2),
                             "cover": round(cover, 2), "cos": float(y.get("score") or 0), "exact": False, "why": ["memory"]})
        except Exception as ex:
            log.info("gyaan: yaad search skipped: %s", ex)
    hits.sort(key=lambda h: -h["fused"])
    hits = hits[:max(top * 3, 20)]
    # optional API rerank (text chat only)
    reranked = False
    if hits and not fast:
        sc = embed.rerank(query, [h["title"] + "\n" + h["text"] for h in hits])
        if sc:
            for h, s in zip(hits, sc):
                h["rerank"] = round(s, 3)
            hits.sort(key=lambda h: -h["rerank"])
            reranked = True
            STATS["reranked"] += 1
    # confidence gate
    hash_model = e is not None and e.name.startswith("hash")
    min_cos = 9.0 if hash_model else st.gyaan_min_cos      # hash vectors have no meaning to trust on their own
    for h in hits:
        if reranked:
            ok = h.get("rerank", 0) >= st.gyaan_min_rerank
        else:
            ok = h["exact"] or h["cover"] >= st.gyaan_min_cover or h["cos"] >= min_cos
        h["ok"] = bool(ok)
    good = [h for h in hits if h["ok"]][:top]
    STATS["ms_total"] += int((time.time() - t0) * 1000)
    if not good:
        STATS["nahi_mila"] += 1
        near = list(dict.fromkeys(h["title"] for h in hits[:5]))
        return {"status": "nahi_mila", "hits": [], "near": near, "searched": list(lists), "reranked": reranked,
                "say": "Aapke Gyaan (files, Drive, mail, purani baatein) mein iska pakka jawab nahi mila."}
    STATS["found"] += 1
    return {"status": "found", "hits": good, "searched": list(lists), "reranked": reranked, "names": names[:8],
            "ms": int((time.time() - t0) * 1000)}
