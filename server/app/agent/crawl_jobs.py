"""v0.486.0 CRAWL JOBS — the background crawl lane (owner: "PHASE 2 END TO END").

The Firecrawl /crawl idea, house-sized, on the v0.481 FIRECRAWL CORE lane: a WHOLE site section wanted
offline — the agent queues a job (crawl_start), the worker tick (~20 s) picks it up and crawls politely
in the background, and the agent reads progress (crawl_status, check/stop) and results (crawl_results)
on later turns. Design borrowed from Firecrawl's NuQ queue + crawl checkpointing, ZERO Firecrawl code
(the engine is AGPL-3.0 and never enters this tree).

Storage: per-tenant SQLite beside the rest of the scrape lane's memory — data/scraping/<tenant>/crawl.db
(crawl_jobs + crawl_pages). The queue is discovered by the worker by globbing those files, one row per job.

House rules kept:
- HTTP ONLY: the background lane never launches a browser (MEM-CURE RAM discipline; stealth stays the
  foreground doors' business). A blocked page is recorded honestly and the crawl moves on.
- robots.txt respected per URL (scrape_respect_robots), SSRF guard per URL, small politeness sleeps.
- Checkpoint + heartbeat: every page writes the frontier (queue + seen) back to the job row, so a pm2
  restart or a crash resumes FROM THE CHECKPOINT (the v0.475 research-runner shape: a running job that
  has not heartbeated for scrape_crawl_stale_s is picked up again; scrape_crawl_tries starts, then failed).
- Write-through: every successful page read also lands in the per-tenant PAGE cache (v0.481), so the
  foreground scrape door serves those pages with zero outbound afterwards.
- The queue never breaks a scrape: best-effort everywhere, honest errors in the rows.

Tools (3): crawl_start / crawl_status (check|stop) / crawl_results. Registry 523 -> 526.
"""
import asyncio
import json
import logging
import re
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from . import scrape_tools as st          # the one lane: guards, fetch core, page cache, masking

log = logging.getLogger("santosh.crawl_jobs")
from .tools import Ctx, ToolError

_CRAWL_PAGES_CAP = 50        # hard page budget per job (max_pages param clamps to this)
_PAGE_CHARS = 20_000         # stored markdown/text cap per page
_QUEUE_CAP = 500             # frontier cap inside a job
_RESULT_CHARS = 8_000        # markdown cap per page in crawl_results listings
_KEEP_JOBS = 10              # finished jobs kept per tenant (older ones are forgotten)
_polite_s = 0.35             # sleep between two fetches of the same crawl (tests may shrink it)
_RUNNING: set[str] = set()   # "tenant:job_id" currently alive in this process
_TASKS: set["asyncio.Task"] = set()


# --------------------------------------------------------------------------- store (per-tenant sqlite)

def _db_path(tenant_id: str) -> Path:
    return Path(st._tenant_dir(tenant_id)) / "crawl.db"


def _con(tenant_id: str) -> sqlite3.Connection:
    con = sqlite3.connect(str(_db_path(tenant_id)), timeout=10)
    con.execute("CREATE TABLE IF NOT EXISTS crawl_jobs (id TEXT PRIMARY KEY, seed TEXT, include TEXT, "
                "max_pages INTEGER, status TEXT, tries INTEGER DEFAULT 0, fetched INTEGER DEFAULT 0, "
                "pages_done INTEGER DEFAULT 0, error TEXT, note TEXT, checkpoint TEXT, "
                "created_at REAL, updated_at REAL)")
    con.execute("CREATE TABLE IF NOT EXISTS crawl_pages (job_id TEXT, url TEXT, seq INTEGER, status INTEGER, "
                "title TEXT, markdown TEXT, text TEXT, note TEXT, fetched_at REAL, "
                "PRIMARY KEY (job_id, url))")
    return con


def _job_row(r: sqlite3.Row) -> dict[str, Any]:
    d = dict(r)
    try:
        d["checkpoint"] = json.loads(d.get("checkpoint") or "{}")
    except Exception:
        d["checkpoint"] = {}
    return d


def create_job(tenant_id: str, seed: str, include: str = "", max_pages: int = 20) -> dict[str, Any]:
    """Queue a crawl. An already queued/running job for the SAME seed is returned as-is (idempotent).
    The row carries an internal _created flag so the tool can say 'new' vs 'already there' honestly."""
    now_ = time.time()
    con = _con(tenant_id)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute("SELECT * FROM crawl_jobs WHERE seed = ? AND status IN ('queued','running') "
                          "ORDER BY created_at DESC LIMIT 1", (seed,)).fetchone()
        if row is not None:
            out = _job_row(row)
            out["_created"] = False
            return out
        jid = "cj_" + uuid.uuid4().hex[:12]
        con.execute("INSERT INTO crawl_jobs (id, seed, include, max_pages, status, tries, created_at, updated_at, "
                    "checkpoint) VALUES (?,?,?,?,?,0,?,?,?)",
                    (jid, seed, include or "", int(max_pages), "queued", now_, now_,
                     json.dumps({"queue": [seed], "seen": [seed]})))
        con.commit()
        out = _job_row(con.execute("SELECT * FROM crawl_jobs WHERE id = ?", (jid,)).fetchone())
        out["_created"] = True
        return out
    finally:
        con.close()


def get_job(tenant_id: str, job_id: str) -> dict[str, Any] | None:
    con = _con(tenant_id)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute("SELECT * FROM crawl_jobs WHERE id = ?", (job_id,)).fetchone()
        return _job_row(row) if row is not None else None
    finally:
        con.close()


def latest_job(tenant_id: str) -> dict[str, Any] | None:
    con = _con(tenant_id)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute("SELECT * FROM crawl_jobs ORDER BY created_at DESC LIMIT 1").fetchone()
        return _job_row(row) if row is not None else None
    finally:
        con.close()


def stop_job(tenant_id: str, job_id: str) -> bool:
    con = _con(tenant_id)
    try:
        cur = con.execute("UPDATE crawl_jobs SET status = 'stopped', updated_at = ? "
                          "WHERE id = ? AND status IN ('queued','running')", (time.time(), job_id))
        con.commit()
        return cur.rowcount > 0
    finally:
        con.close()


def _save(tenant_id: str, job_id: str, **fields) -> None:
    """Heartbeat / checkpoint / progress write (one small transaction)."""
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields)
    con = _con(tenant_id)
    try:
        con.execute(f"UPDATE crawl_jobs SET {sets} WHERE id = ?", (*fields.values(), job_id))
        con.commit()
    finally:
        con.close()


def put_page(tenant_id: str, job_id: str, url: str, seq: int, status: int, title: str,
             markdown: str, text: str, note: str = "") -> None:
    con = _con(tenant_id)
    try:
        con.execute("INSERT OR REPLACE INTO crawl_pages (job_id, url, seq, status, title, markdown, text, "
                    "note, fetched_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (job_id, url, int(seq), int(status), (title or "")[:500],
                     (markdown or "")[:_PAGE_CHARS], (text or "")[:_PAGE_CHARS], (note or "")[:300], time.time()))
        con.commit()
    finally:
        con.close()


def pages(tenant_id: str, job_id: str, offset: int = 0, limit: int = 5, url: str = "") -> tuple[list[dict], int]:
    con = _con(tenant_id)
    con.row_factory = sqlite3.Row
    try:
        total = con.execute("SELECT COUNT(*) FROM crawl_pages WHERE job_id = ?", (job_id,)).fetchone()[0]
        if url:
            rows = con.execute("SELECT * FROM crawl_pages WHERE job_id = ? AND url = ?",
                               (job_id, url)).fetchall()
        else:
            rows = con.execute("SELECT * FROM crawl_pages WHERE job_id = ? ORDER BY seq LIMIT ? OFFSET ?",
                               (job_id, int(limit), int(offset))).fetchall()
        return [dict(r) for r in rows], int(total)
    finally:
        con.close()


def forget_old(tenant_id: str, keep_days: int = 7) -> int:
    """Finished jobs (and their pages) older than keep_days go; per tenant at most _KEEP_JOBS stay."""
    cut = time.time() - max(1, int(keep_days)) * 86400
    gone = 0
    con = _con(tenant_id)
    try:
        old = [r[0] for r in con.execute(
            "SELECT id FROM crawl_jobs WHERE status NOT IN ('queued','running') AND updated_at < ?", (cut,))]
        for jid in old:
            con.execute("DELETE FROM crawl_pages WHERE job_id = ?", (jid,))
            con.execute("DELETE FROM crawl_jobs WHERE id = ?", (jid,))
            gone += 1
        extra = con.execute("SELECT id FROM crawl_jobs WHERE status NOT IN ('queued','running') "
                            "ORDER BY updated_at DESC LIMIT -1 OFFSET ?", (_KEEP_JOBS,)).fetchall()
        for (jid,) in extra:
            con.execute("DELETE FROM crawl_pages WHERE job_id = ?", (jid,))
            con.execute("DELETE FROM crawl_jobs WHERE id = ?", (jid,))
            gone += 1
        con.commit()
    finally:
        con.close()
    return gone


# --------------------------------------------------------------------------- worker side (global queue)

def candidates(stale_s: int) -> list[tuple[str, str]]:
    """(tenant, job_id) to run now: queued jobs, plus running ones whose heartbeat stopped (stalled)."""
    out: list[tuple[str, str]] = []
    root = Path("data") / "scraping"
    if not root.is_dir():
        return out
    now_ = time.time()
    for db in sorted(root.glob("*/crawl.db")):
        tenant = db.parent.name
        try:
            con = sqlite3.connect(str(db), timeout=5)
            con.row_factory = sqlite3.Row
            rows = con.execute("SELECT id, status, updated_at FROM crawl_jobs "
                               "WHERE status = 'queued' OR (status = 'running' AND updated_at < ?) "
                               "ORDER BY created_at LIMIT 8", (now_ - max(30, int(stale_s)),)).fetchall()
            con.close()
            out.extend((tenant, r["id"]) for r in rows)
        except Exception:
            continue
    return out


def claim(tenant_id: str, job_id: str, tries_max: int) -> bool:
    """One conditional UPDATE = the claim. Tries exhausted -> the job is failed honestly."""
    con = _con(tenant_id)
    try:
        cur = con.execute("UPDATE crawl_jobs SET status = 'running', tries = tries + 1, updated_at = ? "
                          "WHERE id = ? AND status IN ('queued','running') AND tries < ?",
                          (time.time(), job_id, max(1, int(tries_max))))
        con.commit()
        if cur.rowcount > 0:
            return True
        cur2 = con.execute("UPDATE crawl_jobs SET status = 'failed', error = ?, updated_at = ? "
                           "WHERE id = ? AND status IN ('queued','running')",
                           ("tries bhar gaye — site baar baar crawl nahi ho payi", time.time(), job_id))
        con.commit()
        if cur2.rowcount > 0:
            # wave 10: a crawl that used up its tries went "failed" in silence - she learned it only by asking crawl_status
            try:
                row = con.execute("SELECT seed FROM crawl_jobs WHERE id = ?", (job_id,)).fetchone()
                from .. import convs, events
                conv = convs.notice_chat(tenant_id)   # v0.714
                if conv:
                    events.notify(conv, f"Crawl ({(row[0] if row else '')[:80]}) kai baar ki koshish ke baad bhi nahi "
                                        f"ho paya, isliye band kar diya (job {job_id}).")
            except Exception:   # noqa: BLE001
                pass
        return False
    finally:
        con.close()


# --------------------------------------------------------------------------- the runner

def _harvest(page: Any, base_url: str, start_host: str, include: str | None) -> list[str]:
    """Same-site links off one page (the scrape_map shape), unfiltered by robots (caller decides)."""
    pat = None
    if include:
        try:
            pat = re.compile(include)
        except re.error:
            pat = None
    out: list[str] = []
    try:
        anchors = page.css("a[href]")[:400]
    except Exception:
        return out
    for a in anchors:
        href = a.attrib.get("href") or ""
        if href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        nxt = urljoin(base_url, href).split("#")[0]
        try:
            nu = urlparse(nxt)
        except Exception:
            continue
        if nu.scheme not in ("http", "https") or (nu.hostname or "") != start_host:
            continue
        if pat is not None and not pat.search(nu.geturl()):
            continue
        out.append(nu.geturl())
    return out


def _read_page(page: Any) -> tuple[str, str, str]:
    """(title, markdown, text) off a fetched page, both content forms capped."""
    try:
        t = page.css("title")
        title = (t[0].text.strip() if t else "")
    except Exception:
        title = ""
    try:
        md = page.markdown()
    except Exception:
        md = ""
    try:
        txt = page.get_all_text(separator="\n")
    except Exception:
        txt = ""
    return title, (md or "")[:_PAGE_CHARS], (txt or "")[:_PAGE_CHARS]


def _save_cp(tenant_id: str, job_id: str, queue: list[str], seen: list[str], cp: dict[str, Any]) -> str:
    """The frontier back into the job row: queue + seen + the running counters."""
    payload = {"queue": queue[:_QUEUE_CAP], "seen": seen[:_QUEUE_CAP]}
    for k in ("errors", "skipped_robots", "last_block"):
        if cp.get(k) is not None:
            payload[k] = cp[k]
    return json.dumps(payload)


def _pick_next(queue: list, cp: dict, question: str, mode: str, seed: str, include: str | None):
    """Which url to read next. v0.537 item 3: best-first when she asked a QUESTION (the most promising link
    first), plain FIFO otherwise - so a crawl with no question behaves exactly as it did before.

    The frontier is rebuilt from the queue each tick rather than held in memory: this job is resumed from a
    SQLite checkpoint after a restart, so anything not in the checkpoint does not exist.
    """
    if not queue:
        return None
    if mode != "best" or not question:
        return queue.pop(0)
    try:
        from ..crawl.frontier import Filters, Frontier
        f = Frontier(keywords=_keywords(question),
                     filters=Filters(same_host_as=seed, include=(include or "")), mode="best")
        for u in queue:
            f.push(u)
        for txt in (cp.get("learned") or [])[-20:]:
            f.learn(str(txt))
        got = f.pop()
        if got is None:
            return queue.pop(0)
        url = got[0]
        if url in queue:
            queue.remove(url)
        return url
    except Exception:
        log.exception("frontier failed; falling back to fifo")
        return queue.pop(0)


def _keywords(question: str) -> list[str]:
    from ..crawl.bm25 import words
    return words(question)[:12]


def _enough_yet(cp: dict, question: str) -> tuple[bool, str, dict]:
    """v0.537 item 1: has it read enough to answer her question? (stop?, why, metrics)

    Only ever asked when she gave a question - a crawl told to mirror a section still stops on its page
    budget alone, as it always did.
    """
    if not question:
        return False, "", {}
    try:
        from ..crawl.enough import EnoughConfig, Knowledge, confidence, should_stop
        k = Knowledge(query=question)
        for item in (cp.get("learned") or []):
            k.add(str(item.get("url", "")), str(item.get("text", "")))
        k.confidence_history = list(cp.get("conf_history") or [])
        cfg = EnoughConfig(max_pages=10_000)      # the JOB's page budget is the real ceiling, not this
        stop, why = should_stop(k, cfg)
        cp["conf_history"] = k.confidence_history[-20:]
        return stop, why, confidence(k, cfg)
    except Exception:
        log.exception("enough-check failed; the crawl carries on")
        return False, "", {}


async def run_job(tenant_id: str, job_id: str) -> None:
    """The checkpointed polite BFS. One page = one heartbeat. Stop/failure are honest, never silent."""
    try:
        while True:
            row = get_job(tenant_id, job_id)
            if row is None or row["status"] in ("stopped", "done", "failed"):
                return
            cp = row.get("checkpoint") or {}
            queue = list(cp.get("queue") or [])
            seen = list(cp.get("seen") or [])
            if not queue and not seen:
                queue, seen = [row["seed"]], [row["seed"]]
            if not queue or row["fetched"] >= int(row["max_pages"] or 0):
                _save(tenant_id, job_id, status="done", updated_at=time.time(),
                      note=(f"last block: {cp['last_block']}" if cp.get("last_block") else ""))
                return
            include = (row["include"] or "").strip() or None
            start_host = urlparse(row["seed"]).hostname or ""
            # v0.537 items 1 + 3: the frontier decides WHICH url next, and the question (if she gave one)
            # decides WHETHER to carry on. Both are rebuilt from the checkpoint every tick, because this
            # job must survive a pm2 restart and resume from where it stopped.
            question = (cp.get("question") or "").strip()
            mode = (cp.get("mode") or "bfs").strip().lower()
            url = _pick_next(queue, cp, question, mode, row["seed"], include)
            if url is None:
                _save(tenant_id, job_id, status="done", updated_at=time.time(),
                      note="frontier mein koi padhne layak url nahi bacha")
                return
            seq = int(row["fetched"]) + 1
            # guards first: a queued url that fails the guard is recorded, the crawl moves on
            try:
                url = await asyncio.to_thread(st._guard_url, url)
            except ToolError as e:
                put_page(tenant_id, job_id, url, seq, 0, "", "", "", note=f"guard: {str(e)[:140]}")
                cp["errors"] = int(cp.get("errors") or 0) + 1
                _save(tenant_id, job_id, checkpoint=_save_cp(tenant_id, job_id, queue, seen, cp),
                      fetched=seq, updated_at=time.time())
                await asyncio.sleep(_polite_s)
                continue
            if not await st._robots_ok(url):
                cp["skipped_robots"] = int(cp.get("skipped_robots") or 0) + 1
                _save(tenant_id, job_id, checkpoint=_save_cp(tenant_id, job_id, queue, seen, cp),
                      fetched=seq, updated_at=time.time())
                await asyncio.sleep(_polite_s)
                continue
            try:
                page = await asyncio.to_thread(st._fetch, url, tenant_id)
            except Exception as e:
                put_page(tenant_id, job_id, url, seq, 0, "", "", "", note=f"fetch failed: {str(e)[:140]}")
                cp["errors"] = int(cp.get("errors") or 0) + 1
                _save(tenant_id, job_id, checkpoint=_save_cp(tenant_id, job_id, queue, seen, cp),
                      fetched=seq, updated_at=time.time())
                await asyncio.sleep(_polite_s)
                continue
            blk = await asyncio.to_thread(st._blocked, page)
            status = int(getattr(page, "status", 0) or 0)
            if blk:
                # HTTP-only lane: a block is recorded and the crawl moves on (stealth stays foreground-only)
                put_page(tenant_id, job_id, url, seq, status, "", "", "", note=f"blocked ({blk})")
                cp["errors"] = int(cp.get("errors") or 0) + 1
                cp["last_block"] = str(blk)[:140]
            elif status >= 400:
                put_page(tenant_id, job_id, url, seq, status, "", "", "", note=f"HTTP {status}")
                cp["errors"] = int(cp.get("errors") or 0) + 1
            else:
                title, md, txt = await asyncio.to_thread(_read_page, page)
                put_page(tenant_id, job_id, getattr(page, "url", "") or url, seq, status, title, md, txt)
                await asyncio.to_thread(st._cache_put_page, tenant_id, page)   # warm the v0.481 page cache
                if question:
                    learned = list(cp.get("learned") or [])
                    learned.append({"url": getattr(page, "url", "") or url, "text": (txt or md or "")[:4000]})
                    cp["learned"] = learned[-30:]          # bounded: the checkpoint is JSON in a row
                for nxt in _harvest(page, getattr(page, "url", "") or url, start_host, include):
                    if nxt in seen or len(queue) >= _QUEUE_CAP:
                        continue
                    seen.append(nxt)
                    queue.append(nxt)
            done_now = int(row.get("pages_done") or 0) + (0 if (blk or status >= 400) else 1)
            stop_enough, why_enough, metrics = _enough_yet(cp, question)
            if metrics:
                cp["confidence"] = metrics
            _save(tenant_id, job_id, checkpoint=_save_cp(tenant_id, job_id, queue, seen, cp),
                  fetched=seq, pages_done=done_now, updated_at=time.time())
            if stop_enough:
                # The whole point of item 1: a crawl that has the answer stops instead of spending the
                # rest of its budget. The REASON is recorded, because a crawl that stops must say why.
                _save(tenant_id, job_id, status="done", updated_at=time.time(), note=why_enough)
                return
            await asyncio.sleep(_polite_s)
    except asyncio.CancelledError:
        try:                      # honest + resumable: the next tick picks the checkpoint up again
            _save(tenant_id, job_id, status="queued", updated_at=time.time(),
                  error="worker band hua — agle tick se checkpoint se aage")
        except Exception:
            pass
        raise
    except Exception as e:
        try:
            _save(tenant_id, job_id, status="queued", updated_at=time.time(), error=str(e)[:300])
        except Exception:
            pass
        # claim() fails it honestly once tries are exhausted; until then the next tick resumes the checkpoint


# --------------------------------------------------------------------------- tick (worker entry)

def _bg_done(t: "asyncio.Task") -> None:
    _TASKS.discard(t)


async def tick() -> int:
    """The worker slot (~20 s, worker.scrape_crawl_jobs): start queued crawls, resume stalled ones, forget old."""
    from ..config import get_settings
    s = get_settings()
    if not getattr(s, "scrape_crawl_enabled", True):
        return 0
    running = len(_RUNNING)
    budget = max(0, int(getattr(s, "scrape_crawl_max_running", 1)) - running)
    if budget <= 0:
        return 0
    started = 0
    for tenant, jid in candidates(int(getattr(s, "scrape_crawl_stale_s", 180))):
        if started >= budget:
            break
        key = f"{tenant}:{jid}"
        if key in _RUNNING:
            continue
        if not claim(tenant, jid, int(getattr(s, "scrape_crawl_tries", 3))):
            continue
        _RUNNING.add(key)
        t = asyncio.ensure_future(run_job(tenant, jid))
        _TASKS.add(t)

        def _done(_t, key=key):
            _TASKS.discard(_t)
            _RUNNING.discard(key)
        t.add_done_callback(_done)
        started += 1
    if started == 0:
        try:
            root = Path("data") / "scraping"
            if root.is_dir():
                for db in sorted(root.glob("*/crawl.db")):
                    forget_old(db.parent.name, int(getattr(s, "scrape_crawl_keep_days", 7)))
        except Exception:
            pass
    return started


async def drain() -> None:
    """Await whatever the last tick spawned (tests use this; harmless in the worker)."""
    if _TASKS:
        await asyncio.gather(*list(_TASKS), return_exceptions=True)


# --------------------------------------------------------------------------- tools

def _fmt_job(row: dict[str, Any]) -> dict[str, Any]:
    cp = row.get("checkpoint") or {}
    return {"job_id": row["id"], "seed": row["seed"], "status": row["status"], "tries": row["tries"],
            "max_pages": row["max_pages"], "fetched": row["fetched"], "pages_stored": row["pages_done"],
            "queue_left": len(cp.get("queue") or []), "errors": int(cp.get("errors") or 0),
            "skipped_by_robots": int(cp.get("skipped_robots") or 0),
            "last_block": cp.get("last_block") or "", "error": row.get("error") or "",
            "age_s": int(time.time() - float(row.get("updated_at") or 0)),
            "note": row.get("note") or ""}


async def crawl_start(ctx: Ctx, url, max_pages=20, include=None, question=None, **_):
    """Queue a background crawl of one site section (the Firecrawl /crawl idea): polite BFS, robots
    honoured, HTTP only, checkpointed — the worker tick picks it up within ~20 s.

    v0.537: give `question` and the crawl changes character — it reads the most PROMISING link next
    instead of the next one in line, and it STOPS when the pages answer the question rather than
    spending the whole page budget. Without a question the behaviour is byte-for-byte what it was."""
    from ..config import get_settings
    s = get_settings()
    if not getattr(s, "scrape_crawl_enabled", True):
        raise ToolError("Background crawl is VPS par band hai (scrape_crawl_enabled=false) — scrape_site / scrape_map abhi ke liye use karein")
    seed = await asyncio.to_thread(st._guard_url, url)
    if not await st._robots_ok(seed):
        raise ToolError("Is site ke robots.txt ne bots ko mana kiya hai (respect_robots on)")
    try:
        want = max(1, min(int(max_pages or 20), _CRAWL_PAGES_CAP))
    except Exception:
        want = 20
    row = create_job(ctx.tenant_id, seed, str(include or ""), want)
    fresh = bool(row.pop("_created", False))
    q = str(question or "").strip()[:300]
    if q and fresh:
        cp = dict(row.get("checkpoint") or {})
        cp["question"] = q
        cp["mode"] = str(getattr(s, "scrape_crawl_question_mode", "best") or "best").lower()
        _save(ctx.tenant_id, row["id"], checkpoint=json.dumps(cp), updated_at=time.time())
    return st._masked({"job_id": row["id"], "seed": row["seed"], "status": row["status"],
                       "max_pages": int(row["max_pages"]),
                       "already_running": not fresh,
                       **({"question": q, "mode": cp["mode"]} if q and fresh else {}),
                       "note": ("Crawl queue ho gaya — worker ise ~20 s mein uthayega, phir crawl_status se progress aur "
                                "crawl_results se pages dekhein" if fresh
                                else "Yeh seed pehle se queued/running hai — wahi job aage badhega (naya job nahi bana)")
                       + (" Question diya hai, to sabse kaam ka link pehle padhega aur jawab milte hi ruk jayega."
                          if q and fresh else "")})


async def crawl_status(ctx: Ctx, job_id="", action="check", **_):
    """Progress of a background crawl (no job_id = the latest one). action='stop' stops it politely
    between pages — fetched pages stay usable."""
    act = str(action or "check").lower()
    if act not in ("check", "stop"):
        act = "check"
    row = get_job(ctx.tenant_id, str(job_id)) if job_id else latest_job(ctx.tenant_id)
    if row is None:
        raise ToolError("Koi crawl job nahi mila — pehle crawl_start chalayein, ya job_id sahi dein")
    stopped = False
    if act == "stop":
        stopped = stop_job(ctx.tenant_id, row["id"])
        row = get_job(ctx.tenant_id, row["id"]) or row
    out = _fmt_job(row)
    out["action"] = act
    if act == "stop":
        out["note"] = ("Job ruk gaya (ya pehle se ruka hua tha) — jitne pages nikal chuke hain woh crawl_results mein hai"
                       if stopped else "Yeh job pehle se chal nahi raha — crawl_results se jo mila woh dekhein")
    return st._masked(out)


async def crawl_results(ctx: Ctx, job_id="", offset=0, limit=5, url="", **_):
    """Pages a finished/running crawl has stored: title + markdown (capped), paginated. One page poora
    chahiye to url=<that page> dein."""
    row = get_job(ctx.tenant_id, str(job_id)) if job_id else latest_job(ctx.tenant_id)
    if row is None:
        raise ToolError("Koi crawl job nahi mila — pehle crawl_start chalayein")
    try:
        off = max(0, int(offset or 0))
    except Exception:
        off = 0
    try:
        lim = max(1, min(int(limit or 5), 10))
    except Exception:
        lim = 5
    rows, total = pages(ctx.tenant_id, row["id"], off, lim, str(url or ""))
    cap = _PAGE_CHARS if url else _RESULT_CHARS
    out_pages = [{"url": r["url"], "status": r["status"], "title": r["title"],
                  "markdown": st._cap(r["markdown"] or r["text"] or "", cap),
                  "note": r["note"] or ""} for r in rows]
    return st._masked({"job_id": row["id"], "status": row["status"], "seed": row["seed"],
                       "total_pages": total, "offset": off, "count": len(out_pages), "pages": out_pages,
                       "note": ("Aur pages chahiye to offset aage badhayein" if off + len(out_pages) < total else "")})


CRAWL_TOOLS = [
    {"name": "crawl_start", "description": (
        "Crawl a website section IN THE BACKGROUND (v0.486, the Firecrawl /crawl idea): Hoola queues a polite "
        "same-site crawl (BFS, robots.txt honoured, HTTP only, small delays, checkpointed), the worker picks it "
        "up within ~20 s, and the agent reads progress with crawl_status and the stored pages with crawl_results "
        "on later turns. Use when MANY pages are wanted (a whole catalogue, notices, docs) and per-turn scrape "
        "calls would be slow — up to 50 pages per job, 'include' regex narrows the urls. JS-only sites stay with "
        "browse_web."),
     "input_schema": {"type": "object", "properties": {
         "url": {"type": "string", "description": "Where the crawl starts (homepage or a section url)"},
         "max_pages": {"type": "integer", "description": "Page budget, default 20, cap 50"},
         "include": {"type": "string", "description": "Regex the crawled urls must match, e.g. '/product/'"},
         "question": {"type": "string", "description": (
             "What she actually wants to know (e.g. 'what are the GST rates on cement'). Give this and the "
             "crawl reads the most promising link next instead of the next one in line, and STOPS as soon "
             "as the pages answer it — so a 50-page budget is not spent when the answer arrived on page 3. "
             "Leave it out to mirror a whole section.")}},
         "required": ["url"]}},
    {"name": "crawl_status", "description": (
        "Progress of a background crawl job (v0.486): status (queued/running/done/failed/stopped), pages "
        "fetched vs budget, queue left, robots skips, errors, last block. action='stop' politely stops it "
        "between pages — already-fetched pages stay readable via crawl_results. No job_id = the latest job."),
     "input_schema": {"type": "object", "properties": {
         "job_id": {"type": "string", "description": "From crawl_start; empty = latest job of this tenant"},
         "action": {"type": "string", "enum": ["check", "stop"], "description": "check (default) or stop"}},
         }},
    {"name": "crawl_results", "description": (
        "Pages a background crawl has STORED (v0.486): title + markdown per page, paginated (offset/limit, max "
        "10 per call). Works while the crawl is still running (partial results) and after it finished. One "
        "specific page poora chahiye to url=<page url> dein. Use with crawl_start / crawl_status."),
     "input_schema": {"type": "object", "properties": {
         "job_id": {"type": "string", "description": "From crawl_start; empty = latest job of this tenant"},
         "offset": {"type": "integer", "description": "Skip this many stored pages (default 0)"},
         "limit": {"type": "integer", "description": "Pages per call, default 5, cap 10"},
         "url": {"type": "string", "description": "One specific page's full content instead of a listing"}},
         }},
]

CRAWL_LABELS = {"crawl_start": "Site ka background crawl shuru kar raha hoon",
                "crawl_status": "Crawl ki progress dekh raha hoon",
                "crawl_results": "Crawl ke results nikaal raha hoon"}

CRAWL_HANDLERS = {"crawl_start": crawl_start, "crawl_status": crawl_status, "crawl_results": crawl_results}
