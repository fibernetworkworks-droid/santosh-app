"""G1 of docs/SUPPORT_GLOBAL_PLAN.md: ONE business brain for Customer Support and the Telecaller.

Both employees keep their own tables (nothing is moved or lost): Support's answers (`seva_entries`) and the Telecaller's
sources + facts (`callcentre_sources` / `callcentre_facts`). This module is the one reader both use:
- `support_facts` - the Telecaller's approved facts, read by Support's `answer()` when its own answers have none;
- `line_entries` - Support's live answers, read by the Telecaller's `knowledge.search` on calls.

And what the knowledge itself gains:
- versions: every change of an answer is kept (who, when, why); any version can be put back (a new version, her tap);
- an owner and a "review by" date per answer: after the date Hoola stops using it until someone looks again;
- stale: an answer read from a web page is marked stale when the page changes; stale answers are not used until she
  checks them (re-read or "still right");
- help-center import: a public Zendesk help center by its address, or an export file (JSON / CSV with title + body:
  Freshdesk, Intercom, Confluence, Notion and the rest) -> DRAFT answers;
- suggestions from solved tickets: the same question solved again and again with the team's own reply -> a suggestion
  (question, the reply, how many tickets) she approves or dismisses;
- live lookups for a customer: an approved Telecaller live source asked with THAT customer's own number only.
"""
from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import logging
import re
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, new_id, now, session

log = logging.getLogger("santosh.seva")

STALE_CHECK_H = 24
SUGGEST_MIN = 2           # the same question solved at least this many times
SUGGEST_SIM = 0.45
SUGGEST_DAYS = 120


class SevaEntryVersion(Base):
    """One saved state of one answer (append-only)."""
    __tablename__ = "seva_entry_versions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("sev"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    entry_id: Mapped[str] = mapped_column(String(40), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    question: Mapped[str] = mapped_column(Text, default="")
    answer: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(8), default="live")
    by: Mapped[str] = mapped_column(String(80), default="owner")
    why: Mapped[str] = mapped_column(String(40), default="added")      # added | edited | approved | restored | checked | read again
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SevaSuggestion(Base):
    """A question her team solved again and again; open until she approves (-> a live answer) or dismisses it."""
    __tablename__ = "seva_suggestions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("ssg"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    key: Mapped[str] = mapped_column(String(32), index=True)
    question: Mapped[str] = mapped_column(Text, default="")
    answer: Mapped[str] = mapped_column(Text, default="")
    tickets: Mapped[str] = mapped_column(Text, default="[]")
    count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(10), default="open")    # open | approved | dismissed
    entry_id: Mapped[str] = mapped_column(String(40), default="")
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SevaPageWatch(Base):
    """A web page answers were read from: its text hash, so a change can mark those answers stale."""
    __tablename__ = "seva_page_watch"
    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("spw"))
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    url: Mapped[str] = mapped_column(String(600), default="")
    hash: Mapped[str] = mapped_column(String(32), default="")
    changed: Mapped[bool] = mapped_column(Boolean, default=False)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BrainError(Exception):
    pass


_READY: set[int] = set()


def _ensure() -> None:
    """Self-heal: the tables exist even where init_db ran before this module was imported."""
    from .. import db as _db
    eng = getattr(_db, "_engine", None)
    if eng is not None and id(eng) not in _READY:
        for m in (SevaEntryVersion, SevaSuggestion, SevaPageWatch):
            m.__table__.create(eng, checkfirst=True)
        _READY.add(id(eng))


def _S():
    from . import service as S
    return S


def _aware(d: datetime | None) -> datetime | None:
    from datetime import timezone
    if d is None:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _today(tenant: str) -> str:
    return _S()._local(tenant).date().isoformat()


# ---------------------------------------------------------------- usable (one rule for both employees)
def usable(e, today: str) -> bool:
    """A live answer reaches a customer only if it is not stale and its review date has not passed."""
    if e.status != "live" or getattr(e, "stale", False):
        return False
    rb = getattr(e, "review_by", "") or ""
    return not rb or rb >= today


# ---------------------------------------------------------------- versions
def record(s, e, by: str = "owner", why: str = "edited") -> None:
    """Called inside the same session that changed the entry."""
    e.version = int(getattr(e, "version", 0) or 0) + 1
    s.add(SevaEntryVersion(tenant_id=e.tenant_id, entry_id=e.id, version=e.version, question=e.question, answer=e.answer,
                           status=e.status, by=(by or "owner")[:80], why=why[:40]))


def history(tenant: str, entry_id: str) -> dict:
    _ensure()
    S = _S()
    with session() as s:
        e = s.get(S.SevaEntry, entry_id)
        if e is None or e.tenant_id != tenant:
            raise BrainError("This answer was not found.")
        rows = s.scalars(select(SevaEntryVersion).where(SevaEntryVersion.entry_id == entry_id)
                         .order_by(SevaEntryVersion.version.desc())).all()
        return {"entry": S._entry_view(e), "versions": [{"version": r.version, "question": r.question, "answer": r.answer,
                "status": r.status, "by": r.by, "why": r.why, "at": _aware(r.at).isoformat()} for r in rows]}


def restore(tenant: str, entry_id: str, version: int, by: str = "owner") -> dict:
    """Her tap: an earlier version becomes the answer again (kept as a new version)."""
    _ensure()
    S = _S()
    with session() as s:
        e = s.get(S.SevaEntry, entry_id)
        if e is None or e.tenant_id != tenant:
            raise BrainError("This answer was not found.")
        v = s.scalars(select(SevaEntryVersion).where(SevaEntryVersion.entry_id == entry_id,
                                                     SevaEntryVersion.version == int(version))).first()
        if v is None:
            raise BrainError("No such version.")
        e.question, e.answer, e.stale, e.updated_at = v.question, v.answer, False, now()
        record(s, e, by, "restored")
        return S._entry_view(e) | {"say": f"Version {v.version} is the answer again (saved as version {e.version})."}


def meta(tenant: str, entry_id: str, owner: str | None = None, review_by: str | None = None, checked: bool = False,
         by: str = "owner") -> dict:
    """Owner of the answer, its review date, or "still right" after a stale flag / a passed review date."""
    S = _S()
    with session() as s:
        e = s.get(S.SevaEntry, entry_id)
        if e is None or e.tenant_id != tenant:
            raise BrainError("This answer was not found.")
        if owner is not None:
            e.owner = S._clean(owner, 120)
        if review_by is not None:
            rb = str(review_by).strip()
            if rb:
                try:
                    date.fromisoformat(rb)
                except ValueError:
                    raise BrainError("Give the review date as YYYY-MM-DD.")
            e.review_by = rb
        if checked:
            e.stale = False
            if e.review_by and e.review_by < _today(tenant):
                e.review_by = ""
            _ensure()
            record(s, e, by, "checked")
        e.updated_at = now()
        return S._entry_view(e) | {"say": "Saved."}


# ---------------------------------------------------------------- one brain: each employee reads the other's knowledge
def support_facts(tenant: str, question: str, k: int = 3) -> list[dict]:
    """The Telecaller's approved facts for a question (what Support may also say)."""
    try:
        from ..callcentre import knowledge as K
        hits = K.search(tenant, question, k, with_support=False)
    except Exception:   # noqa: BLE001 - one brain never breaks the other
        log.exception("telecaller facts read failed")
        return []
    return hits


COVER_MIN = 0.6     # share of the customer's own words a fact must hold before it answers them


def covers(question: str, text: str) -> bool:
    """A fact answers only when it holds most of what was asked - one shared word ("AC") is not enough
    ("price of the window AC" must never get the split AC's price)."""
    from ..callcentre.knowledge import words_of
    q = set(words_of(question))
    if not q:
        return False
    w = set(words_of(text))
    hit = {x for x in q if x in w or (len(x) > 4 and any(y.startswith(x[:5]) for y in w))}
    return len(hit) >= 2 and len(hit) / len(q) >= COVER_MIN


def line_entries(tenant: str, question: str, k: int = 3) -> list[dict]:
    """Support's live, usable answers for a question, scored like the Telecaller's facts (for calls)."""
    from ..callcentre.knowledge import words_of
    S = _S()
    q = set(words_of(question))
    if not q:
        return []
    today = _today(tenant)
    out = []
    with session() as s:
        for e in s.scalars(select(S.SevaEntry).where(S.SevaEntry.tenant_id == tenant, S.SevaEntry.status == "live")).all():
            if not usable(e, today):
                continue
            tw = set(words_of(e.question + " " + " ".join(S._j(e.aliases, []))))
            w = tw | set(words_of(e.answer))
            hit = sum(2 if x in tw else 1 for x in q if x in w)
            if hit:
                out.append((hit / (len(q) + 1), e))
    out.sort(key=lambda x: -x[0])
    return [{"kind": "policy" if e.kind == "policy" else "faq", "title": e.question, "text": e.answer, "score": round(sc, 2),
             "from": "Customer Support"} for sc, e in out[:k] if sc >= 0.25]


# ---------------------------------------------------------------- stale (web pages that changed)
def _hash(text: str) -> str:
    return hashlib.sha256(re.sub(r"\s+", " ", text or "").strip().encode()).hexdigest()[:24]


def watch(tenant: str, url: str, text: str) -> None:
    """kb_import from a page: remember how the page read."""
    _ensure()
    with session() as s:
        w = s.scalars(select(SevaPageWatch).where(SevaPageWatch.tenant_id == tenant, SevaPageWatch.url == url[:600])).first()
        if w is None:
            w = SevaPageWatch(tenant_id=tenant, url=url[:600])
            s.add(w)
        w.hash, w.changed, w.checked_at = _hash(text), False, now()


def check_pages(tenant: str | None = None, limit: int = 20, fetch=None) -> int:
    """Worker: read each watched page again (once a day); a changed page marks its answers stale."""
    _ensure()
    S = _S()
    cut = now() - timedelta(hours=STALE_CHECK_H)
    with session() as s:
        q = select(SevaPageWatch)
        if tenant:
            q = q.where(SevaPageWatch.tenant_id == tenant)
        due = [(w.id, w.tenant_id, w.url, w.hash) for w in s.scalars(q).all()
               if w.checked_at is None or _aware(w.checked_at) < cut][:limit]
    n = 0
    for wid, t, url, old in due:
        try:
            text = fetch(url) if fetch else S._source_text(t, url=url)[0]
        except Exception:   # noqa: BLE001 - a page that does not open is not "changed"
            with session() as s:
                w = s.get(SevaPageWatch, wid)
                w.checked_at = now()
            continue
        h = _hash(text)
        with session() as s:
            w = s.get(SevaPageWatch, wid)
            w.checked_at = now()
            if h != old:
                w.changed, w.hash = True, h
                src = f"website: {url[:200]}"
                for e in s.scalars(select(S.SevaEntry).where(S.SevaEntry.tenant_id == t, S.SevaEntry.source == src)).all():
                    if not e.stale:
                        e.stale = True
                        n += 1
    if n:
        log.info("seva stale: %d answers marked after page changes", n)
    return n


# ---------------------------------------------------------------- help-center import
def _strip(h: str) -> str:
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h or "", flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>|</p>|</li>|</h\d>", "\n", t, flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", t)).strip()


def _articles_from_file(name: str, data: bytes) -> list[dict]:
    low = (name or "").lower()
    out: list[dict] = []
    if low.endswith(".json"):
        try:
            d = json.loads(data.decode("utf-8", "ignore"))
        except ValueError:
            raise BrainError("This JSON file could not be read.")
        items = d if isinstance(d, list) else next((d[k] for k in ("articles", "solutions", "items", "results", "pages", "data")
                                                    if isinstance(d, dict) and isinstance(d.get(k), list)), [])
        for it in items:
            if not isinstance(it, dict):
                continue
            title = it.get("title") or it.get("name") or it.get("question") or ""
            body = it.get("body") or it.get("description") or it.get("content") or it.get("answer") or it.get("text") or ""
            if isinstance(body, dict):
                body = body.get("storage", {}).get("value", "") if isinstance(body.get("storage"), dict) else json.dumps(body)
            out.append({"title": str(title), "body": _strip(str(body))})
    elif low.endswith(".csv"):
        rows = csv.DictReader(io.StringIO(data.decode("utf-8-sig", "ignore")))
        for r in rows:
            r = {(k or "").strip().lower(): (v or "") for k, v in r.items()}
            title = r.get("title") or r.get("name") or r.get("question") or ""
            body = r.get("body") or r.get("description") or r.get("content") or r.get("answer") or r.get("text") or ""
            out.append({"title": title, "body": _strip(body)})
    else:
        raise BrainError("Send the help-center export as a .json or .csv file (title + body).")
    return [a for a in out if a["title"].strip() and a["body"].strip()]


def _zendesk(url: str) -> tuple[str, list[dict]]:
    """A PUBLIC Zendesk help center: its own articles API (no key; only public articles)."""
    from urllib.parse import urlparse

    from ..callcentre import knowledge as K
    host = urlparse(url if "://" in url else "https://" + url).hostname or ""
    if not host:
        raise BrainError("Give the help center's address, e.g. https://help.yourbusiness.com")
    K._guard_host("https://" + host)
    nxt, out, pages = f"https://{host}/api/v2/help_center/articles.json?per_page=100", [], 0
    while nxt and pages < 5:
        try:
            r = K._get(nxt)
            d = r.json()
        except (K.KbError, ValueError) as e:
            raise BrainError(f"The help center did not answer as a Zendesk help center ({e}).")
        for a in d.get("articles") or []:
            if a.get("draft"):
                continue
            out.append({"title": str(a.get("title") or ""), "body": _strip(str(a.get("body") or ""))})
        nxt = d.get("next_page") or ""
        if nxt:
            K._guard_host(nxt)
        pages += 1
    return host, [a for a in out if a["title"] and a["body"]]


def import_helpcenter(tenant: str, url: str = "", data: bytes | None = None, name: str = "", by: str = "owner") -> dict:
    """Help-center articles -> DRAFT answers (she approves them like any other draft)."""
    S = _S()
    if data is not None:
        arts, src = _articles_from_file(name, data), f"help center file: {(name or 'file')[:120]}"
    elif url:
        host, arts = _zendesk(url)
        src = f"help center: {host}"
    else:
        raise BrainError("Give the help center's address or its export file.")
    made = 0
    for a in arts[:400]:
        q, body = S._clean(a["title"], 500), S._clean(a["body"], 3000)
        if not q or not body or S._secret(body):
            continue
        kind = "policy" if re.search(r"refund|return|cancel|warranty|exchange|policy|terms", q + " " + body[:300], re.I) else "faq"
        try:
            S.kb_add(tenant, q, body, kind, [], source=src, status="draft", by=by)
            made += 1
        except S.SevaError:
            continue
    return {"count": made, "source": src, "say": (f"{made} articles read as drafts from {src}. Check and approve them in Knowledge; "
                                                   "only then do customers get them.") if made else "No articles with a title and text were found."}


# ---------------------------------------------------------------- suggestions from solved tickets
def _team_reply(notes: list[dict]) -> str:
    """The last public reply a PERSON of her team wrote (not Hoola's own status lines)."""
    for n in reversed(notes or []):
        who = str(n.get("from") or "")
        if n.get("public") and who and not who.startswith(("hoola", "customer", "system", "auto")):
            t = str(n.get("text") or "").strip()
            t = re.sub(r"^To the customer:\s*", "", t)
            t = re.sub(r"\s*\(draft: you send it\)$", "", t).strip()
            if len(t) >= 12:
                return t
    return ""


def suggestions(tenant: str, refresh: bool = True) -> list[dict]:
    """Questions solved at least SUGGEST_MIN times with a team reply, not yet in the knowledge."""
    _ensure()
    S = _S()
    from . import rules as R
    if refresh:
        since = S.clock() - timedelta(days=SUGGEST_DAYS)
        with session() as s:
            rows = s.scalars(select(S.SevaTicket).where(S.SevaTicket.tenant_id == tenant,
                                                        S.SevaTicket.status.in_(("resolved", "closed")),
                                                        S.SevaTicket.updated_at >= since)).all()
            solved = [(t.number, t.text, _team_reply(S._j(t.notes, []))) for t in rows]
        groups: list[dict] = []
        for num, text, rep in solved:
            if not rep:
                continue
            for g in groups:
                if R.similarity(text, g["question"]) >= SUGGEST_SIM:
                    g["tickets"].append(num)
                    g["answer"] = rep
                    break
            else:
                groups.append({"question": text, "answer": rep, "tickets": [num]})
        live = S.kb_list(tenant, status="live")
        with session() as s:
            for g in groups:
                if len(g["tickets"]) < SUGGEST_MIN or S._secret(g["answer"]):
                    continue
                if any(R.similarity(g["question"], e["question"]) >= S.HIGH for e in live):
                    continue
                key = hashlib.sha256(R.norm(g["question"])[:160].encode()).hexdigest()[:24]
                old = s.scalars(select(SevaSuggestion).where(SevaSuggestion.tenant_id == tenant, SevaSuggestion.key == key)).first()
                if old is None:
                    s.add(SevaSuggestion(tenant_id=tenant, key=key, question=S._clean(g["question"], 500),
                                         answer=S._clean(g["answer"], 1500), tickets=json.dumps(g["tickets"][:20]),
                                         count=len(g["tickets"])))
                elif old.status == "open":
                    old.answer, old.tickets, old.count = S._clean(g["answer"], 1500), json.dumps(g["tickets"][:20]), len(g["tickets"])
    with session() as s:
        rows = s.scalars(select(SevaSuggestion).where(SevaSuggestion.tenant_id == tenant, SevaSuggestion.status == "open")
                         .order_by(SevaSuggestion.count.desc())).all()
        return [{"id": r.id, "question": r.question, "answer": r.answer, "count": r.count, "tickets": json.loads(r.tickets or "[]")}
                for r in rows]


def suggestion_decide(tenant: str, sid: str, yes: bool, question: str = "", answer: str = "", by: str = "owner") -> dict:
    """Her tap: approve (she may edit the words first) -> a live answer; or dismiss for good."""
    _ensure()
    S = _S()
    with session() as s:
        r = s.get(SevaSuggestion, sid)
        if r is None or r.tenant_id != tenant or r.status != "open":
            raise BrainError("This suggestion is not open.")
        if not yes:
            r.status = "dismissed"
            return {"dismissed": sid, "say": "Dismissed; it will not be suggested again."}
        q, a, n = question or r.question, answer or r.answer, r.count
    try:
        e = S.kb_add(tenant, q, a, "faq", [], source=f"solved tickets ({n})", status="live", by=by)
    except S.SevaError as ex:
        raise BrainError(str(ex))
    with session() as s:
        r = s.get(SevaSuggestion, sid)
        r.status, r.entry_id = "approved", e["id"]
    return e | {"say": "Added to Knowledge; customers get this answer from now on."}


# ---------------------------------------------------------------- live lookups bound to the asking customer
def _phone_of(customer_key: str) -> str:
    k = str(customer_key or "")
    if k.startswith(("wa:", "phone:", "tel:")):
        return re.sub(r"\D", "", k.split(":", 1)[1])
    return ""


def customer_lookup(tenant: str, question: str, customer_key: str, value: str = "") -> dict | None:
    """When knowledge has no answer and an approved live lookup fits the question, ask it with THIS customer's own number.
    None = no lookup fits (the normal 'unknown' path goes on)."""
    phone = _phone_of(customer_key)
    if not phone:
        return None
    try:
        from ..callcentre import knowledge as K
        from ..callcentre.knowledge import words_of
        live = K.live_sources(tenant)
    except Exception:   # noqa: BLE001
        return None
    q = set(words_of(question))
    best, score = None, 0
    for src in live:
        w = set(words_of(src["lookup"] + " " + src["name"]))
        hit = len(q & w)
        if hit > score:
            best, score = src, hit
    if best is None or score < 1:
        return None
    got = K.lookup(tenant, best["id"], phone, value)
    if got.get("error"):
        return {"status": "lookup_failed", "reply": "", "source": f"Live lookup: {best['name']}",
                "say": got["error"]}
    return {"status": "looked_up", "reply": "", "rows": got.get("rows") or [], "found": bool(got.get("found")),
            "source": f"Live lookup: {best['name']} (this customer's own number)",
            "say": "Tell the customer only what these rows say. If nothing was found, say so and hand it to a person."}


# ---------------------------------------------------------------- the Knowledge page's extra parts
def overview(tenant: str) -> dict:
    """Stale / review-due answers, the Telecaller's sources (shared), open suggestions, watched pages."""
    _ensure()
    S = _S()
    today = _today(tenant)
    with session() as s:
        es = s.scalars(select(S.SevaEntry).where(S.SevaEntry.tenant_id == tenant, S.SevaEntry.status == "live")).all()
        stale = [S._entry_view(e) for e in es if e.stale]
        due = [S._entry_view(e) for e in es if not e.stale and e.review_by and e.review_by < today]
        pages = [{"url": w.url, "changed": w.changed, "checked": _aware(w.checked_at).isoformat() if w.checked_at else ""}
                 for w in s.scalars(select(SevaPageWatch).where(SevaPageWatch.tenant_id == tenant)).all()]
    try:
        from ..callcentre import knowledge as K
        shared = [{"id": x["id"], "name": x["name"], "kind": x["kind"], "mode": x["mode"], "status": x["status"], "facts": x["facts"]}
                  for x in K.sources(tenant)]
    except Exception:   # noqa: BLE001
        shared = []
    return {"stale": stale, "review_due": due, "shared": shared, "suggestions": suggestions(tenant), "pages": pages}
