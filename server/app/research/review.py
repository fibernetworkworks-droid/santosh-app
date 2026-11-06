"""v0.480 R9 HELD REVIEW - a second model reads the report against its own sources before she sees it (the v0.436 held-answer pattern, with the dossier as its evidence).

The code checks (R3: every figure is a note's or a calculation's, cited to the right source) cannot see WORDING: "grew every year" from one reading, "will" from a trend, a
cause nobody sourced, a NOT-CONFIRMED item stated as fact. This is the layer for that. It runs AFTER the code checks pass, sees the dossier's notes with the page's own
words (not the truncated tail of the chat's tool evidence the generic reviewer gets), returns at most four named problems, and its answer goes through the same ONE fix
round. A reviewer that fails, times out or answers badly NEVER blocks the answer."""
from __future__ import annotations

import asyncio
import json
import logging
import re

log = logging.getLogger("santosh.research.review")

STATS = {"reviewed": 0, "found": 0, "failed": 0}

REVIEW_SYSTEM = """You are the REVIEWER of a research report written for a small-business owner. You do not rewrite it. You compare it with the NOTES it was written from.
Each note is a claim with the source page's own words, a confidence, and sometimes a flag (NOT VERIFIED / figure not in the quoted words). Then come the items the research could NOT confirm.

Find only REAL problems of these kinds:
1. A statement of fact the notes' words do not support, or support only in a narrower case (e.g. "grew every year" when the notes give one reading; "market leader" when a note gives one company's own claim).
2. Wording stronger than the evidence: all / always / never / will / proves / because / the reason is - where the notes only show a figure or a single source.
3. A contradiction with a note.
4. A NOT-CONFIRMED item, or a note flagged NOT VERIFIED, presented as fact (stating it AS unconfirmed is correct and is not a problem).
5. A comparison, ranking, total or percentage that no note or calculation carries.
6. A caveat the notes carry (the period a figure is about, a disagreement between sources, 'estimate') missing where the report relies on that figure.

Do NOT flag style, length, structure, language, or things the report already marks as unconfirmed. If it is sound, say so.
Reply ONLY JSON: {"ok": true|false, "problems": ["quote ~8 words of the sentence, then what is wrong in one sentence", ... at most 4]}"""


def digest(dossier: dict, limit: int = 24000) -> str:
    """The notes + the gaps, in the shape the reviewer reads."""
    out = [f"QUESTION: {str(dossier.get('question') or '')[:400]}", "", "NOTES:"]
    for f in dossier.get("fields", []):
        flag = "" if f["verified"] and f["supported"] else (" [NOT VERIFIED: the quoted words were not on the page]" if not f["verified"] else " [FIGURE NOT IN THE QUOTED WORDS]")
        out.append(f"- [{f.get('n')}] ({f['confidence']}) {f['claim']}{(' - period: ' + f['date']) if f.get('date') else ''}{flag}\n    page's words: \"{str(f['excerpt'])[:260]}\"")
    calcs = [c for t in dossier.get("tasks", []) for c in t.get("calcs", []) if c.get("ok")]
    if calcs:
        out += ["", "CALCULATIONS (code that really ran):"] + [f"- {c['purpose']}: {str(c['output'])[:160]}" for c in calcs]
    gaps = [p for t in dossier.get("tasks", []) for p in re.split(r";\s+", str(t.get("unresolved") or "")) if p.strip()]
    out += ["", "NOT CONFIRMED by the research:"] + ([f"- {g[:200]}" for g in gaps] or ["- (none listed)"])
    txt = "\n".join(out)
    return txt if len(txt) <= limit else txt[:limit] + "\n...[cut]"


async def review_report(question: str, draft: str, dossier: dict, settings) -> list[str]:
    """[] = nothing found (or the reviewer failed - it never blocks). Otherwise up to four named problems for the ONE fix round."""
    if not getattr(settings, "research_review", True) or not dossier or not dossier.get("fields"):
        return []
    try:
        from ..agent.santosh import get_client
        model = getattr(settings, "hard_check_model", "") or settings.anthropic_model
        user = f"{digest(dossier)}\n\nREPORT:\n{str(draft)[:12000]}"
        resp = await asyncio.wait_for(get_client().messages.create(model=model, max_tokens=700, system=REVIEW_SYSTEM, messages=[{"role": "user", "content": user}]),
                                      timeout=float(getattr(settings, "hard_check_timeout_s", 60)))
        raw = "".join(str(b.get("text") if isinstance(b, dict) else getattr(b, "text", "")) for b in resp.content)
        m = re.search(r"\{.*\}", raw, re.S)
        v = json.loads(m.group(0)) if m else {}
        STATS["reviewed"] += 1
        if v.get("ok") is False:
            probs = [str(p)[:400] for p in (v.get("problems") or []) if str(p).strip()][:4]
            if probs:
                STATS["found"] += 1
            return probs
        return []
    except Exception as e:      # noqa: BLE001 - a failing reviewer is no reviewer, never a block
        STATS["failed"] += 1
        log.info("research review failed: %s", e)
        return []
