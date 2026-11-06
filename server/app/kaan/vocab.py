"""KAAN W3 custom vocabulary: her terms, two honest mechanisms.

From the upstream whisper repository read (v20250625): whisper has NO hard vocabulary biasing.
`initial_prompt` conditions the decoder with a prompt window - a SOFT hint that can slip on
borderline audio. Deterministic replacement (fix_to) is the hard mechanism: word-boundary,
case-insensitive, every application counted and named in the row note - nothing is applied
silently, and the stored map makes any fix reversible by reading vocab_list. Zero dependencies,
zero network (port law + inertness law).
"""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select

from ..db import new_id, now, session
from .models import KaanVocab

MAX_TERM = 120          # one term / fix_to cap (chars)
PROMPT_CAP = 800        # initial_prompt cap (chars) - whisper's prompt window is ~224 tokens; stay well under


# ---------------------------------------------------------------- CRUD
def add(tenant: str, term: str, fix_to: str = "", note: str = "") -> dict[str, Any]:
    """Add (or update) one term for this tenant. fix_to "" = hint only; else deterministic replacement."""
    term, fix_to, note = (term or "").strip(), (fix_to or "").strip(), (note or "").strip()
    if not term:
        raise ValueError("term khaali nahi ho sakta - shabd dijiye.")
    if len(term) > MAX_TERM or len(fix_to) > MAX_TERM:
        raise ValueError(f"term / fix_to {MAX_TERM} char tak lete hain.")
    if fix_to == term:
        raise ValueError("fix_to term jaisa hi hai - replacement ko badlav hi nahi bacha; fix_to khaali chhodiye (hint only).")
    with session() as s:
        r = s.scalars(select(KaanVocab).where(KaanVocab.tenant_id == tenant,
                                              KaanVocab.term_key == term.lower())).first()
        updated = r is not None
        if r is None:
            r = KaanVocab(id=new_id("kv"), tenant_id=tenant, term_key=term.lower())
            s.add(r)
        r.term, r.fix_to, r.note = term, fix_to, note
        r.updated_at = now()
        s.commit()
        out = {"id": r.id, "term": r.term, "fix_to": r.fix_to, "note": r.note, "updated": updated}
    return out


def list_vocab(tenant: str) -> dict[str, Any]:
    with session() as s:
        rows = s.scalars(select(KaanVocab).where(KaanVocab.tenant_id == tenant)
                         .order_by(KaanVocab.created_at.asc())).all()
        items = [{"term": r.term, "fix_to": r.fix_to, "note": r.note,
                  "created_at": r.created_at.isoformat() if r.created_at else ""} for r in rows]
    return {"items": items, "n": len(items),
            "note": "term = initial_prompt hint (soft, can slip); fix_to = deterministic replacement (counted, honest)."}


def remove(tenant: str, term: str) -> dict[str, Any]:
    term = (term or "").strip()
    with session() as s:
        r = s.scalars(select(KaanVocab).where(KaanVocab.tenant_id == tenant,
                                              KaanVocab.term_key == term.lower())).first()
        if not r:
            raise ValueError(f"'{term}' vocab mein nahi mili - kuch hata nahi (list action se dekhein).")
        s.delete(r)
        s.commit()
    return {"removed": term, "ok": True}


def count(tenant: str) -> int:
    with session() as s:
        return len(s.scalars(select(KaanVocab.id).where(KaanVocab.tenant_id == tenant)).all())


# ---------------------------------------------------------------- the two mechanisms
def prompt_for(tenant: str) -> tuple[str, int, int]:
    """(prompt, n_terms_total, n_truncated) - terms joined ', ', capped at PROMPT_CAP (oldest kept first)."""
    with session() as s:
        terms = [r.term for r in s.scalars(select(KaanVocab).where(KaanVocab.tenant_id == tenant)
                                           .order_by(KaanVocab.created_at.asc())).all()]
    if not terms:
        return "", 0, 0
    out: list[str] = []
    used = 0
    for t in terms:
        add_n = len(t) + (2 if out else 0)
        if used + add_n > PROMPT_CAP:
            break
        out.append(t)
        used += add_n
    return ", ".join(out), len(terms), len(terms) - len(out)


def fixes_for(tenant: str) -> dict[str, str]:
    """{term: fix_to} - only entries with a real replacement (fix_to set and different)."""
    with session() as s:
        rows = s.scalars(select(KaanVocab).where(KaanVocab.tenant_id == tenant)).all()
    return {r.term: r.fix_to for r in rows if r.fix_to and r.fix_to != r.term}


def apply_out(text: str, segs: list[dict[str, Any]], fixes: dict[str, str]) -> tuple[str, list[dict[str, Any]], dict[str, int], int]:
    """Deterministic fixes on the full text + each segment text (word tokens stay raw - timing data).
    Word-boundary + case-insensitive; returns (text, segs, per_term_counts, total)."""
    if not fixes or not (text or segs):
        return text, segs, {}, 0
    per: dict[str, int] = {}

    def rep(s: str) -> str:
        for term, fix in fixes.items():
            pat = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
            s, k = pat.subn(lambda _m: fix, s)      # lambda: fix is literal, no backslash surprises
            if k:
                per[term] = per.get(term, 0) + k
        return s

    text2 = rep(text or "")
    segs2 = [{**sg, "text": rep(sg.get("text", ""))} for sg in (segs or [])]
    return text2, segs2, per, sum(per.values())
