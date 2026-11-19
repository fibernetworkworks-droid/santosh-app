"""P8 MUQABLA (compare): the same ask as two prompts, side by side.

1. Comparing the two PROMPTS is free and runs in code: each side's score, what each has that the other lacks, which
   parts are her own words, what differs. Nothing is sent to an engine.
2. Running both sides is offered only where Hoola itself makes the result on this page (a picture, a script), and only
   after the PRICE is shown: `quote` gives each side's credits and where the figure comes from, and `run` refuses
   unless it is handed back that exact quote (its token = a hash of the two prompts and the price). A changed prompt
   or a changed price needs a new quote. Everything else (websites, apps, code, chat) is compared as prompts only.
3. Her pick is written down as SHAPE (which slots each side had, from where, their scores, who won) - never her words -
   and the winner's ledger run gets her thumb up.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, as_utc, new_id, now, session
from . import anatomy as A
from . import brief as B
from . import dialect as D

RUNNABLE = ("image", "script")
SIDES = ("a", "b")


class CompareError(ValueError):
    pass


class PromptCompare(Base):
    """One comparison she ran or judged. Shape only: no prompt text, no facts."""
    __tablename__ = "prompt_compares"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    section: Mapped[str] = mapped_column(String(20), default="")
    a_hash: Mapped[str] = mapped_column(String(16), default="")
    b_hash: Mapped[str] = mapped_column(String(16), default="")
    a_score: Mapped[int] = mapped_column(Integer, default=0)
    b_score: Mapped[int] = mapped_column(Integer, default=0)
    a_slots: Mapped[str] = mapped_column(Text, default="{}")      # slot -> source
    b_slots: Mapped[str] = mapped_column(Text, default="{}")
    ran: Mapped[str] = mapped_column(String(10), default="")       # '' = prompts only | 'both'
    credits: Mapped[int] = mapped_column(Integer, default=0)
    refs: Mapped[str] = mapped_column(Text, default="{}")          # side -> engine ids (jobs / items)
    runs: Mapped[str] = mapped_column(Text, default="{}")          # side -> ledger run id
    pick: Mapped[str] = mapped_column(String(10), default="")      # a | b | same
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    picked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_OK: set[int] = set()


def ensure_table() -> None:
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _OK:
        PromptCompare.__table__.create(eng, checkfirst=True)
        _OK.add(id(eng))


# ---------------------------------------------------------------- 1. the free comparison
def _side(b: dict[str, Any]) -> dict[str, Any]:
    sc = B.score(b)
    out = D.render(b)
    return {"brief": b, "score": sc, "out": out, "hash": B.hash_of(b)}


def pair(a: Any, b: Any) -> dict[str, Any]:
    """Both prompts checked and compared in code. They must be the same kind of prompt."""
    ba, bb = B.validate(a), B.validate(b)
    if ba["section"] != bb["section"]:
        raise CompareError("Compare two prompts of the same kind - a picture with a picture, a script with a script.")
    sa, sb = _side(ba), _side(bb)
    sec = ba["section"]
    rows = []
    for s in A.slots(sec):
        k = s["key"]
        va, vb = (ba["slots"].get(k) or {}), (bb["slots"].get(k) or {})
        if not va and not vb:
            continue
        rows.append({"key": k, "label": s["label"], "required": bool(s.get("required")),
                     "a": va.get("value", ""), "a_source": va.get("source", ""),
                     "b": vb.get("value", ""), "b_source": vb.get("source", ""),
                     "same": B.norm(va.get("value", "")) == B.norm(vb.get("value", ""))})
    fa = {f["text"] for f in ba.get("facts") or []}
    fb = {f["text"] for f in bb.get("facts") or []}
    notes = []
    if sa["score"]["score"] != sb["score"]["score"]:
        hi = "A" if sa["score"]["score"] > sb["score"]["score"] else "B"
        notes.append(f"{hi} is more complete ({max(sa['score']['score'], sb['score']['score'])} against "
                     f"{min(sa['score']['score'], sb['score']['score'])}). A complete prompt is not always the better result - "
                     "run both or judge by eye.")
    if fa - fb:
        notes.append("Only A carries: " + ", ".join(sorted(fa - fb)) + ".")
    if fb - fa:
        notes.append("Only B carries: " + ", ".join(sorted(fb - fa)) + ".")
    if sa["hash"] == sb["hash"]:
        notes.append("The two prompts are the same. Change one side first.")
    return {"section": sec, "a": sa, "b": sb, "rows": rows, "notes": notes, "runnable": sec in RUNNABLE,
            "why_not": "" if sec in RUNNABLE else _why_not(sec)}


def _why_not(sec: str) -> str:
    where = {"web": "the Web Studio", "app": "the App Studio", "code": "Hoola Code"}.get(sec, "the Hoola chat")
    return (f"This kind of prompt runs in {where}, so Hoola compares the two prompts here and you run the one you choose "
            "there. Pictures and scripts can be run side by side on this page.")


# ---------------------------------------------------------------- 2. price first
def _credits_of_inr(inr: float) -> int:
    from .. import usage
    from ..credits import plans as P
    usd = inr / max(1.0, float(usage.usd_inr()))
    return max(1, int(round(usd / P.USD_PER_CREDIT)))


def _credits_of_usd(usd: float) -> int:
    from ..credits import plans as P
    return max(1, int(round(usd / P.USD_PER_CREDIT)))


def side_price(b: dict[str, Any], quality: str = "fast") -> dict[str, Any]:
    """What ONE side costs to run, with the source of the figure. Image = the picture engine's own list price; script =
    an estimate from the writer model's token price (her tier may route it to another model)."""
    sec = b["section"]
    if sec == "image":
        from .. import photogen
        q = "best" if quality == "best" else "fast"
        inr = float(photogen.COST_INR[q])
        return {"credits": _credits_of_inr(inr), "basis": f"the picture engine's list price for one {q} picture",
                "estimate": False}
    if sec == "script":
        from .. import usage
        from ..config import get_settings
        from ..create import service as cs
        model = str(getattr(get_settings(), "studio_plan_model", "") or "")
        text = D.render(b)["prompt"]
        tok_in = (len(cs.SCRIPT_SYSTEM) + len(text) + 200) // 4
        usd = usage.cost(model, tok_in=tok_in, tok_out=2000) if model else 0.0
        if usd <= 0:
            usd = 0.03
            basis = "an estimate (the writer model's price is not on the server's list)"
        else:
            basis = f"an estimate for {model}: about {tok_in} words in, 2,000 out"
        return {"credits": _credits_of_usd(usd), "basis": basis, "estimate": True}
    raise CompareError(_why_not(sec))


def _token(pr: dict[str, Any], quality: str, credits: int) -> str:
    raw = json.dumps([pr["a"]["hash"], pr["b"]["hash"], quality, credits], sort_keys=True)
    return hashlib.sha256(("hoola-compare:" + raw).encode()).hexdigest()[:24]


def quote(a: Any, b: Any, quality: str = "fast") -> dict[str, Any]:
    pr = pair(a, b)
    if not pr["runnable"]:
        raise CompareError(pr["why_not"])
    if pr["a"]["hash"] == pr["b"]["hash"]:
        raise CompareError("The two prompts are the same. Change one side first.")
    pa, pb = side_price(pr["a"]["brief"], quality), side_price(pr["b"]["brief"], quality)
    total = pa["credits"] + pb["credits"]
    return {"a": pa, "b": pb, "total": total, "quality": quality, "token": _token(pr, quality, total),
            "say": f"Running both costs about {total} credits ({pa['credits']} + {pb['credits']}). Nothing runs until you confirm."}


# ---------------------------------------------------------------- 3. run both, then her pick
def _shape(b: dict[str, Any]) -> str:
    return json.dumps({k: v.get("source", "") for k, v in (b.get("slots") or {}).items()})


def record(tenant: str, pr: dict[str, Any], ran: str = "", credits: int = 0, refs: dict | None = None,
           runs: dict | None = None) -> str:
    ensure_table()
    with session() as s:
        c = PromptCompare(id=new_id("pcm"), tenant_id=tenant, section=pr["section"], a_hash=pr["a"]["hash"],
                          b_hash=pr["b"]["hash"], a_score=int(pr["a"]["score"]["score"]),
                          b_score=int(pr["b"]["score"]["score"]), a_slots=_shape(pr["a"]["brief"]),
                          b_slots=_shape(pr["b"]["brief"]), ran=ran, credits=int(credits),
                          refs=json.dumps(refs or {}), runs=json.dumps(runs or {}))
        s.add(c)
        s.flush()
        return c.id


def check_token(a: Any, b: Any, quality: str, token: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """The quote she saw must be the quote that runs: same prompts, same quality, same price."""
    q = quote(a, b, quality)
    if not token or token != q["token"]:
        raise CompareError("The price changed or was not shown. Look at the new price and confirm again.")
    return pair(a, b), q


def pick(tenant: str, cid: str, side: str) -> dict[str, Any]:
    """Her choice: 'a', 'b' or 'same'. The winner's ledger run gets her thumb up; the shape is kept for learning."""
    if side not in ("a", "b", "same"):
        raise CompareError("Pick A, B or 'about the same'.")
    ensure_table()
    with session() as s:
        c = s.get(PromptCompare, cid)
        if c is None or c.tenant_id != tenant:
            raise KeyError(cid)
        c.pick, c.picked_at = side, now()
        runs = json.loads(c.runs or "{}")
    if side in SIDES and runs.get(side):
        try:
            from . import ledger as L
            L.thumb(tenant, runs[side], "up")
        except Exception:       # noqa: BLE001 - the ledger never blocks her pick
            pass
    return view(tenant, cid)


def view(tenant: str, cid: str) -> dict[str, Any]:
    ensure_table()
    with session() as s:
        c = s.get(PromptCompare, cid)
        if c is None or c.tenant_id != tenant:
            raise KeyError(cid)
        return {"id": c.id, "section": c.section, "a_score": c.a_score, "b_score": c.b_score, "ran": c.ran,
                "credits": c.credits, "refs": json.loads(c.refs or "{}"), "pick": c.pick,
                "at": as_utc(c.created_at).isoformat() if c.created_at else None}


def tally(tenant: str | None = None) -> dict[str, Any]:
    """How often the more complete prompt won her pick - the first honest test of the Prompt Score from her own eyes."""
    ensure_table()
    with session() as s:
        q = select(PromptCompare).where(PromptCompare.pick != "")
        if tenant:
            q = q.where(PromptCompare.tenant_id == tenant)
        rows = list(s.execute(q).scalars())
    decided = [r for r in rows if r.pick in SIDES and r.a_score != r.b_score]
    hi_won = sum(1 for r in decided if (r.pick == "a") == (r.a_score > r.b_score))
    return {"picked": len(rows), "decided": len(decided), "higher_score_won": hi_won,
            "rate": round(hi_won / len(decided), 2) if len(decided) >= 5 else None,
            "note": "Shown from 5 picks where the scores differed." if len(decided) < 5 else ""}
