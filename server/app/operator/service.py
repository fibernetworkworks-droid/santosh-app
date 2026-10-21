"""v0.67 Hoola Computer Operator: jobs on websites that Hoola does for the owner in its own browser.

    chat / call / routine / staff  --tool computer_operator-->  OperatorTask (queued)
    run_job: its own small agent loop (Claude, operator tools only)  -->  Operator (Playwright Chromium, her profile)
             asks her on the phone (operator_ask card + push + live view)  <--  she answers / types / presses
             downloads -> her files (pc_file cards), proof, a learned recipe, a note in the chat

Jobs run on the app's own event loop (one per owner at a time, OPERATOR_MAX_JOBS browsers per server). The browser,
the jobs' waits and the owner's desk calls all live on that loop.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from sqlalchemy import select

from ..config import get_settings
from ..db import session
from .browser import Approval, Operator, OperatorError, fmt_snapshot, site_of
from .memory import Memory, run_recipe
from .models import OperatorTask
from . import tools as T

log = logging.getLogger("santosh.operator")

ACTIVE = {"queued", "running", "waiting"}
MAIN_LOOP: asyncio.AbstractEventLoop | None = None
_ops: dict[str, tuple[Any, Operator]] = {}      # tenant -> (loop, operator)
_running: dict[str, asyncio.Task] = {}          # task id -> asyncio task
_cancel: set[str] = set()
_sem: dict[int, asyncio.Semaphore] = {}


class OperatorJobError(Exception):
    pass


def _st():
    return get_settings()


def _j(s: str, default: Any) -> Any:
    try:
        v = json.loads(s or "")
        return v if v is not None else default
    except ValueError:
        return default


def home(tenant: str) -> Path:
    safe = re.sub(r"[^\w-]", "_", tenant)[:64] or "default"
    p = Path("data") / "operator" / safe
    p.mkdir(parents=True, exist_ok=True)
    return p


def memory(tenant: str) -> Memory:
    return Memory(home(tenant))


def available() -> bool:
    if not getattr(_st(), "operator_on", True):
        return False
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------- the owner's browser (one per owner)
async def operator(tenant: str) -> Operator:
    loop = asyncio.get_running_loop()
    have = _ops.get(tenant)
    if have and have[0] is loop:
        return have[1]
    st = _st()
    op = Operator(home(tenant), allow_private=bool(st.operator_allow_private), headless=bool(st.operator_headless),
                  executable=st.operator_chromium or "", keep_days=int(st.operator_audit_days or 14),
                  browser=str(getattr(st, "operator_browser", "auto") or "auto"))
    op.on_human_request = lambda a, t=tenant: _asked(t, a)
    op.fetch_upload = lambda fid, t=tenant, o=op: _fetch_upload(t, o, fid)
    _ops[tenant] = (loop, op)
    return op


async def shutdown() -> None:
    loop = asyncio.get_running_loop()
    for t, (lp, op) in list(_ops.items()):
        if lp is loop:
            try:
                await op.shutdown()
            except Exception:
                pass
        _ops.pop(t, None)


async def _fetch_upload(tenant: str, op: Operator, file_id: str) -> Path:
    from ..mailbox.service import MailError, _file_row
    try:
        f = _file_row(tenant, file_id)
    except MailError as e:
        raise OperatorError(str(e)) from None
    src = Path(f.stored_path or "")
    if not src.is_file():
        raise OperatorError("That file is no longer on the server; ask the owner to attach it again.")
    dst = op.home / "uploads" / re.sub(r"[^\w.\- ]", "_", f.name or file_id)[:100]
    dst.write_bytes(src.read_bytes())
    return dst


# ---------------------------------------------------------------- views, events
def view(row: OperatorTask) -> dict[str, Any]:
    return {"id": row.id, "status": row.status, "task": row.task[:600], "stage": row.stage, "steps": row.steps,
            "url": row.url, "site": site_of(row.url) if row.url else "", "title": row.title,
            "pending": _j(row.pending, None), "summary": row.summary, "proof": _j(row.proof, []),
            "outputs": _j(row.outputs, []), "recipe": row.recipe, "log": _j(row.log, [])[-12:], "error": row.error,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None}


def _home_conv(tenant: str) -> str:
    try:
        from ..net.service import home_conv
        return home_conv(tenant)
    except Exception:
        return ""


def _publish(row: OperatorTask, kind: str = "operator_task", payload: dict | None = None) -> None:
    from ..events import bus
    try:
        bus.publish(row.conversation_id or _home_conv(row.tenant_id), kind, payload if payload is not None else view(row))
    except Exception:
        pass


def _note(row: OperatorTask, text: str) -> None:
    from ..events import notify
    try:
        notify(row.conversation_id or _home_conv(row.tenant_id), text)
    except Exception:
        pass


def _set(task_id: str, publish: bool = True, **cols: Any) -> OperatorTask:
    with session() as s:
        row = s.get(OperatorTask, task_id)
        if row is None:
            raise OperatorJobError("No such job")
        for k, v in cols.items():
            if k in ("pending", "proof", "outputs", "log") and not isinstance(v, str):
                v = json.dumps(v, ensure_ascii=False) if v is not None else ""
            setattr(row, k, v)
        s.flush()
        s.expunge(row)
    if publish:
        _publish(row)
    return row


def get(tenant: str, task_id: str) -> dict[str, Any]:
    with session() as s:
        row = s.get(OperatorTask, task_id)
        if row is None or row.tenant_id != tenant:
            raise OperatorJobError("Yeh kaam nahi mila")
        return view(row)


def listing(tenant: str, limit: int = 20) -> list[dict[str, Any]]:
    with session() as s:
        rows = s.scalars(select(OperatorTask).where(OperatorTask.tenant_id == tenant)
                         .order_by(OperatorTask.created_at.desc()).limit(limit)).all()
        return [view(r) for r in rows]


def active(tenant: str) -> dict[str, Any] | None:
    with session() as s:
        row = s.scalars(select(OperatorTask).where(OperatorTask.tenant_id == tenant, OperatorTask.status.in_(ACTIVE))
                        .order_by(OperatorTask.created_at.desc())).first()
        return view(row) if row else None


# ---------------------------------------------------------------- start / cancel
def start(tenant: str, task: str, start_url: str = "", file_ids: list[str] | None = None, conversation_id: str = "",
          created_by: str = "owner") -> dict[str, Any]:
    task = re.sub(r"\s+", " ", task or "").strip()
    if len(task) < 6:
        raise OperatorJobError("Kya karna hai, thoda saaf bataiye (website + kaam).")
    if not available():
        raise OperatorJobError("Computer Operator is server par abhi chalu nahi hai (Playwright / Chromium nahi mila).")
    from .. import idvault, pii
    # v0.75 Aadhaar / PAN / other ID numbers go into her Pehchaan Locker; the job text keeps only {id:...} references
    task, _saved = idvault.capture(tenant, task)
    secrets = [k for k in pii.find(task) if k in ("otp_pin", "password", "card", "cvv")]
    if secrets:
        raise OperatorJobError(f"Kaam ke text mein {pii.describe(secrets)} mat likhiye; woh aap khud page par bharengi.")
    if start_url:
        from .guard import url_problem
        why = url_problem(start_url, bool(_st().operator_allow_private))
        if why:
            raise OperatorJobError(f"Yeh link nahi khul sakta: {why}")
    cur = active(tenant)
    if cur:
        raise OperatorJobError(f"Ek kaam pehle se chal raha hai ({cur['task'][:80]}). Pehle use poora / band hone dijiye.")
    files = []
    if file_ids:
        from ..mailbox.service import MailError, _file_row
        for fid in file_ids[:8]:
            try:
                f = _file_row(tenant, fid)
            except MailError as e:
                raise OperatorJobError(str(e)) from None
            files.append({"file_id": f.id, "name": f.name, "size": f.size})
    with session() as s:
        row = OperatorTask(tenant_id=tenant, conversation_id=conversation_id or _home_conv(tenant), task=task[:3000],
                           start_url=start_url or "", files=json.dumps(files), created_by=created_by[:64],
                           stage="Line mein")
        s.add(row)
        s.flush()
        s.expunge(row)
    _publish(row)
    submit(row.id)
    return view(row)


def submit(task_id: str) -> None:
    if not bool(getattr(_st(), "operator_worker", True)):
        return                                   # tests run run_job() themselves
    loop = MAIN_LOOP
    if loop is None or loop.is_closed():
        log.warning("operator: no app loop yet; job %s waits", task_id)
        return

    def go() -> None:
        t = loop.create_task(_safe_run(task_id))
        _running[task_id] = t
        t.add_done_callback(lambda _t: _running.pop(task_id, None))
    loop.call_soon_threadsafe(go)


async def _safe_run(task_id: str) -> None:
    try:
        await run_job(task_id)
    except asyncio.CancelledError:
        _set(task_id, status="cancelled", stage="Rok diya", pending=None)
        raise
    except Exception as e:
        log.exception("operator job %s", task_id)
        try:
            row = _set(task_id, status="failed", stage="Ruk gaya", pending=None, error=str(e)[:300])
            _note(row, f"Website ka kaam poora nahi ho paya: {row.error}")
        except Exception:
            pass


def cancel(tenant: str, task_id: str) -> dict[str, Any]:
    v = get(tenant, task_id)
    if v["status"] not in ACTIVE:
        return v
    _cancel.add(task_id)
    have = _ops.get(tenant)
    if have:
        for a in have[1].approvals.values():
            if a.status == "pending":
                a.status = "rejected"
                a.event.set()
    if v["status"] == "queued" and task_id not in _running:
        row = _set(task_id, status="cancelled", stage="Rok diya", pending=None)
        return view(row)
    return get(tenant, task_id)


def resume_pending() -> int:
    """A server restart loses the browser mid-way: jobs that were running stop honestly (her logins stay saved)."""
    with session() as s:
        ids = [r.id for r in s.scalars(select(OperatorTask).where(OperatorTask.status.in_(ACTIVE))).all()]
    for i in ids:
        row = _set(i, status="stopped", stage="Server restart", pending=None,
                   error="Server restart hua, browser band ho gaya. Dobara boliye; seekha hua kaam wahin se tez chalega.")
        _note(row, f"Website ka kaam ruk gaya (server restart): {row.task[:120]}. Dobara boliye to phir se karunga.")
    return len(ids)


# ---------------------------------------------------------------- the owner's answers (cards + desk)
async def _asked(tenant: str, a: Approval) -> None:
    """A request for the owner: the card in the chat (push) + the live job shows it."""
    t = active(tenant)
    if not t:
        return
    pend = a.public()
    row = _set(t["id"], status="waiting", stage=f"Aapka intezaar: {a.reason[:120]}", pending=pend)
    _publish(row, "operator_ask", {**pend, "task_id": row.id, "task": row.task[:200], "site": site_of(row.url or pend.get("url", ""))})


async def resolve(tenant: str, request_id: str, status: str, answer: str = "") -> dict[str, Any]:
    have = _ops.get(tenant)
    if not have:
        raise OperatorJobError("Browser band hai; yeh sawaal ab purana ho gaya.")
    op = have[1]
    try:
        a = await op.resolve_human(request_id, "approved" if status == "approved" else "rejected", answer)
    except OperatorError as e:
        raise OperatorJobError(str(e)) from None
    t = active(tenant)
    if t:
        _publish(_set(t["id"], publish=False, status="running", stage="Aage badh raha hoon", pending=None),
                 "operator_ask", {**a.public(), "task_id": t["id"]})
        _publish(_row(t["id"]))
    return a.public()


def _row(task_id: str) -> OperatorTask:
    with session() as s:
        row = s.get(OperatorTask, task_id)
        s.expunge(row)
        return row


def _live_session(tenant: str):
    have = _ops.get(tenant)
    if not have:
        return None, None
    op = have[1]
    return op, op.sessions.get("main")


async def frame(tenant: str) -> bytes:
    op, s = _live_session(tenant)
    if not s:
        raise OperatorJobError("Abhi koi browser khula nahi hai")
    try:
        return await op.screenshot(s, quality=55)
    except Exception:
        if s.last_shot:
            return s.last_shot
        raise OperatorJobError("Page ki photo nahi mili")


async def owner_input(tenant: str, kind: str, x: float = 0, y: float = 0, text: str = "", key: str = "") -> dict[str, Any]:
    """Her own hands in the live view: tap, type (e.g. card details on a payment page), keys. Never logged as text and
    never shown to the model."""
    op, s = _live_session(tenant)
    if not s:
        raise OperatorJobError("Abhi koi browser khula nahi hai")
    if kind == "click":
        await op.owner_click(s, x, y)
    elif kind == "type":
        await op.owner_type(s, text)
    elif kind == "key":
        await op.owner_key(s, key)
    return {"ok": True, "url": s.page.url}


def recipes(tenant: str) -> list[dict[str, Any]]:
    return memory(tenant).find("", limit=100)["recipes"]


def forget_recipe(tenant: str, name: str) -> bool:
    from .memory import slug
    m = memory(tenant)
    p = m.recipe_path(name)
    if not p.exists():
        return False
    for old in p.parent.glob(f"{slug(name)}*.json"):
        old.unlink(missing_ok=True)
    return True


# ---------------------------------------------------------------- the job
class Job:
    def __init__(self, row: OperatorTask, op: Operator, mem: Memory):
        self.row = row
        self.op = op
        self.mem = mem
        self.s = None
        self.finished: dict[str, Any] | None = None
        self.saved_recipe = ""
        self.log: list[str] = []
        self.files = {f["file_id"] for f in _j(row.files, [])}

    async def sess(self, create: bool = False):
        if self.s is None or self.s.name not in self.op.sessions:
            if not create:
                self.s = await self.op.session("main", create=False)
            else:
                self.s = await self.op.session("main")
        return self.s

    def step(self, text: str) -> None:
        self.log.append(text[:160])
        del self.log[:-40]


def _system(row: OperatorTask, mem: Memory) -> str:
    from ..avatar import service as av
    try:
        name = (av.get(row.tenant_id) or {}).get("name") or "Hoola"
    except Exception:
        name = "Hoola"
    files = _j(row.files, [])
    lines = [T.GUIDE.replace("{name}", name)]
    if files:
        lines.append("Files the owner gave for this job (upload by file_id): " +
                     "; ".join(f"{f['name']} (file_id={f['file_id']})" for f in files))
    from .. import idvault
    ids = idvault.summary_for_model(row.tenant_id)
    lines.append("ID LOCKER (her Pehchaan Locker; numbers are masked for you): " + (ids or "empty") +
                 ". To fill an ID box use fill(ref, value='{id:...}') with the reference: the real number goes only "
                 "into the box (official .gov.in / .nic.in sites directly; any other site asks her once). Missing ID: "
                 "ask_owner(kind='question') - her answer comes back as a reference.")
    found = mem.find(row.task, limit=3)
    if found["recipes"]:
        lines.append("Recipes that may fit: " + "; ".join(f"{r['name']} (variables: {', '.join(r['variables'])})"
                                                          for r in found["recipes"] if r["score"] >= 0.3) or "none")
    return "\n\n".join(lines)


async def _brain(system: str, history: list[dict]) -> tuple[list[dict], str]:
    from ..agent import llm
    from ..agent.santosh import _claude_ready, _think
    brain = "claude" if _claude_ready() else llm.choose(history)
    st = _st()
    blocks, stop, _ = await _think(brain, system, history, st, T.TOOLS)
    return blocks, stop


async def run_job(task_id: str) -> dict[str, Any]:
    row = _row(task_id)
    if row.status != "queued":
        return view(row)
    loop_id = id(asyncio.get_running_loop())
    sem = _sem.setdefault(loop_id, asyncio.Semaphore(max(1, int(_st().operator_max_jobs or 2))))
    async with sem:
        if task_id in _cancel:
            return view(_set(task_id, status="cancelled", stage="Rok diya"))
        op = await operator(row.tenant_id)
        op.id_tenant = row.tenant_id
        job = Job(row, op, memory(row.tenant_id))
        _set(task_id, status="running", stage="Shuru kar raha hoon")
        try:
            return await _loop(job)
        finally:
            try:     # the browser closes after every job (her logins stay saved in its profile folder)
                await op.shutdown()
            except Exception:
                pass
            if _ops.get(row.tenant_id, (None, None))[1] is op:
                _ops.pop(row.tenant_id, None)
            _cancel.discard(task_id)


async def _loop(job: Job) -> dict[str, Any]:
    from ..agent.breaker import Breaker
    row = job.row
    st = _st()
    system = _system(row, job.mem)
    intro = f"Task from the owner: {row.task}"
    if row.start_url:
        intro += f"\nStart at: {row.start_url}"
    history: list[dict] = [{"role": "user", "content": intro}]
    br = Breaker(max_calls=int(st.operator_max_steps or 120) + 30)
    final = ""
    for n in range(int(st.operator_max_steps or 120)):
        if row.id in _cancel:
            return _end(job, "cancelled", "Aapne rok diya.")
        T.trim_history(history)
        blocks, stop = await _brain(system, history)
        history.append({"role": "assistant", "content": blocks})
        texts = [b["text"] for b in blocks if b.get("type") == "text" and b.get("text", "").strip()]
        if texts:
            final = "\n".join(texts).strip()
        if stop != "tool_use":
            break
        results = []
        for b in blocks:
            if b.get("type") != "tool_use":
                continue
            name, args = b["name"], b.get("input") or {}
            held = None if name in T.READ_TOOLS else br.before(name, args)
            if held:
                results.append({"type": "tool_result", "tool_use_id": b["id"], "content": held, "is_error": True})
                continue
            _set(row.id, stage=T.LABELS.get(name, name), steps=n + 1, log=job.log, **_where(job))
            try:
                out = await asyncio.wait_for(_tool(job, name, args), timeout=int(st.operator_wait_owner_s or 900) + 180)
                ok = not (isinstance(out, dict) and (out.get("ok") is False or out.get("error")))
                br.after(name, ok)
                results.append({"type": "tool_result", "tool_use_id": b["id"], "content": _mask_result(T.as_result(out))})
            except OperatorError as e:
                br.after(name, False)
                results.append({"type": "tool_result", "tool_use_id": b["id"], "content": str(e), "is_error": True})
            except asyncio.TimeoutError:
                br.after(name, False)
                results.append({"type": "tool_result", "tool_use_id": b["id"], "content": "That took too long; read the page and decide.", "is_error": True})
            except asyncio.CancelledError:
                raise
            except Exception as e:
                br.after(name, False)
                log.exception("operator tool %s", name)
                results.append({"type": "tool_result", "tool_use_id": b["id"], "content": f"error: {type(e).__name__}: {str(e)[:300]}", "is_error": True})
            if job.finished is not None:
                break
        history.append({"role": "user", "content": results})
        if job.finished is not None or br.stopped or row.id in _cancel:
            break
    if row.id in _cancel:
        return _end(job, "cancelled", "Aapne rok diya.")
    if job.finished is not None:
        ok = job.finished.get("ok", True) is not False
        return await _wrap(job, "done" if ok else "failed", job.finished.get("summary") or final, job.finished)
    if br.stopped:
        return await _wrap(job, "failed", f"Atak gaya ({br.stopped}). {final}".strip(), {})
    return await _wrap(job, "failed" if not final else "done", final or "Kaam poora nahi ho paya.", {})


def _mask_result(content):
    """v0.75 identity numbers on pages / in answers never reach the model in full."""
    from .browser import mask_ids
    if isinstance(content, str):
        return mask_ids(content)
    if isinstance(content, list):
        return [{**c, "text": mask_ids(c["text"])} if isinstance(c, dict) and c.get("type") == "text" else c for c in content]
    return content


def _where(job: Job) -> dict[str, str]:
    try:
        if job.s is not None and job.s.name in job.op.sessions:
            return {"url": job.s.page.url}
    except Exception:
        pass
    return {}


async def _wrap(job: Job, status: str, summary: str, fin: dict) -> dict[str, Any]:
    """Downloads -> her files, a recipe learned from a good run, the note in the chat."""
    row = job.row
    outputs = []
    s = job.op.sessions.get("main")
    if s:
        from ..mailbox.service import store_bytes
        from ..pc.service import public_file
        for d in s.downloads:
            if not d.get("file"):
                continue
            p = Path(d["file"])
            if not p.is_file():
                continue
            data = p.read_bytes()
            danger = False
            try:
                from ..filecheck import real_type
                danger = bool(real_type(p.name, data).get("danger"))
            except Exception:
                pass
            if danger:
                outputs.append({"name": p.name, "refused": "file ke andar program / script hai"})
                continue
            f = store_bytes(row.tenant_id, p.name, data, "to_phone")
            pf = public_file(f)
            outputs.append({"file_id": f.id, "name": f.name, "size": f.size, "url": pf["url"]})
            _publish(row, "pc_file", {**pf, "source": "operator"})
        if status == "done" and not job.saved_recipe and len([t for t in s.trace if t.get("action") != "human"]) >= 4:
            try:
                r = job.mem.from_trace(s, _recipe_name(row.task), row.task)
                job.saved_recipe = r["name"]
            except Exception:
                log.exception("auto recipe")
    proof = [str(p)[:200] for p in (fin.get("proof") or [])][:10]
    text = summary.strip()[:3000]
    row2 = _set(row.id, status=status, stage={"done": "Ho gaya", "failed": "Poora nahi hua"}.get(status, status),
                summary=text, proof=proof, outputs=outputs, recipe=job.saved_recipe, pending=None, log=job.log,
                error="" if status == "done" else (fin.get("pending") or "")[:300])
    lines = [("Website ka kaam ho gaya: " if status == "done" else "Website ka kaam poora nahi hua: ") + text]
    if proof:
        lines.append("Saboot: " + " | ".join(proof))
    if fin.get("pending"):
        lines.append("Baaki: " + str(fin["pending"])[:300])
    if outputs:
        lines.append("Files: " + ", ".join(o["name"] for o in outputs))
    if job.saved_recipe:
        lines.append(f"Yeh kaam seekh liya ('{job.saved_recipe}'): agli baar tez hoga.")
    _note(row2, "\n".join(lines))
    try:
        from ..voice import inject
        inject(row2.conversation_id, f"(Computer Operator: {status}. {text[:600]}. Tell the user in one or two short lines.)")
    except Exception:
        pass
    return view(row2)


def _end(job: Job, status: str, text: str) -> dict[str, Any]:
    row = _set(job.row.id, status=status, stage="Rok diya" if status == "cancelled" else status, pending=None,
               summary=text, log=job.log)
    _note(row, f"Website ka kaam rok diya: {row.task[:120]}")
    return view(row)


def _recipe_name(task: str) -> str:
    words = re.sub(r"[^\w\s]", " ", task).split()
    return " ".join(words[:8])[:60] or "website kaam"


# ---------------------------------------------------------------- tool handlers (inside one job)
async def _tool(job: Job, name: str, a: dict[str, Any]) -> Any:
    op = job.op
    if name == "open":
        s = await job.sess(create=True)
        r = await op.goto(s, str(a.get("url", "")))
        job.step(f"Khola: {site_of(r.get('url', ''))}")
        return r
    if name in ("web_search", "read_url", "youtube_howto"):
        return await _research(name, a)
    if name in ("recipe_find", "recipe_show", "site_notes", "site_note_add", "playbook_get", "playbook_save"):
        return _memory_tool(job, name, a)
    if name == "finish":
        job.finished = {"summary": str(a.get("summary", ""))[:3000], "proof": a.get("proof") or [],
                        "pending": str(a.get("pending", ""))[:500], "ok": a.get("ok", True)}
        return {"ok": True}
    if name == "recipe_run":
        return await _recipe_run(job, a)
    s = await job.sess(create=False)
    if name == "page":
        return fmt_snapshot(await op.snapshot(s), with_text=a.get("with_text", True) is not False)
    if name == "look":
        from ..agent.santosh import _claude_ready
        if not _claude_ready():
            return {"ok": False, "error": "no picture model here; use page()"}
        return {"_image": await op.screenshot(s, full_page=bool(a.get("full_page"))), "note": f"Page: {s.page.url}"}
    if name == "click":
        r = await op.act(s, "click", str(a.get("ref", "")), approval_id=a.get("approval_id") or None)
        job.step(f"Click: {r.get('target') or a.get('ref')}" if r.get("ok") else f"Ruka: {r.get('blocked')}")
        return r
    if name == "fill":
        r = await op.act(s, "type" if a.get("slowly") else "fill", str(a.get("ref", "")), value=str(a.get("value", "")),
                         var=a.get("var") or None)
        if r.get("ok"):
            job.step(f"Bhara: {r.get('target')}")
        return r
    if name == "select":
        return await op.act(s, "select", str(a.get("ref", "")), value=str(a.get("option", "")))
    if name == "check":
        return await op.act(s, "check", str(a.get("ref", "")), value=str(a.get("checked", True)))
    if name == "upload":
        fid = str(a.get("file_id", ""))
        if fid not in job.files:
            return {"ok": False, "error": "Only files the owner gave for this job can be uploaded. Ask her (ask_owner question) to attach it in the chat."}
        r = await op.act(s, "upload", str(a.get("ref", "")), value=fid, var=a.get("var") or None)
        job.step(f"File lagayi: {r.get('value')}")
        return r
    if name == "press":
        return await op.act(s, "press", a.get("ref") or None, value=str(a.get("key", "Enter")))
    if name == "hover":
        return await op.act(s, "hover", str(a.get("ref", "")))
    if name == "scroll":
        return await op.scroll(s, str(a.get("direction", "down")), a.get("ref") or None)
    if name == "wait_for":
        return await op.wait_for(s, a.get("text") or None, a.get("seconds"), bool(a.get("gone")))
    if name == "find_text":
        return await op.find_text(s, str(a.get("text", "")))
    if name == "back":
        await s.page.go_back(wait_until="domcontentloaded")
        s.trace.append({"action": "back"})
        return {"ok": True, "page": fmt_snapshot(await op.snapshot(s))}
    if name == "tabs":
        _ = s.page
        return {"active": s.active, "tabs": [{"index": i, "url": p.url, "title": await p.title()} for i, p in enumerate(s.pages)]}
    if name == "switch_tab":
        _ = s.page
        i = int(a.get("index", 0))
        if not 0 <= i < len(s.pages):
            raise OperatorError("No such tab")
        s.active = i
        await s.page.bring_to_front()
        return {"ok": True, "page": fmt_snapshot(await op.snapshot(s))}
    if name == "tables":
        return {"tables": await op.extract_tables(s)}
    if name == "downloads":
        return {"files": [{k: v for k, v in d.items() if k != "file"} for d in s.downloads]}
    if name == "trace":
        return {"steps": [{"step": i, **{k: v for k, v in st.items() if k != "value"}} for i, st in enumerate(s.trace)]}
    if name == "recipe_save":
        r = job.mem.from_trace(s, str(a.get("name", "")) or _recipe_name(job.row.task), str(a.get("task", job.row.task)),
                               a.get("literal_steps"), a.get("variable_steps"), str(a.get("notes", "")))
        job.saved_recipe = r["name"]
        return {"saved": r["name"], "version": r["version"], "site": r["site"], "steps": len(r["steps"]),
                "variables": r["variables"], "owner_steps": r["human_steps"]}
    if name == "ask_owner":
        return await _ask(job, s, a)
    raise OperatorError(f"Unknown tool {name}")


async def _ask(job: Job, s, a: dict[str, Any]) -> dict[str, Any]:
    op = job.op
    req = await op.request_human(s, str(a.get("kind", "question")), str(a.get("reason", "")), a.get("ref") or None,
                                 a.get("options") or None)
    job.step(f"Aapse poocha: {req.reason[:80]}")
    return await _wait_owner(job, s, req)


async def _wait_owner(job: Job, s, req: Approval) -> dict[str, Any]:
    op = job.op
    got = await op.wait_human(req.id, float(_st().operator_wait_owner_s or 900))
    _set(job.row.id, status="running", stage="Aage badh raha hoon", pending=None)
    d = got.public()
    if d.get("answer"):          # v0.75 an ID number in her answer goes to the locker; the model gets the reference
        from .. import idvault
        d["answer"], _ = idvault.capture(job.row.tenant_id, str(d["answer"]))
    if got.status == "expired":
        d["next"] = "She did not answer in time. Finish with what is done and what is left (finish ok=false)."
    elif got.status == "rejected":
        d["next"] = "She said NO. Do not do it. Ask what she wants instead, or finish."
    elif got.kind == "approve" and got.ref and ((op.sessions.get(got.session) and op.sessions[got.session].refs.get(got.ref)) or {}).get("id_field"):
        d["next"] = f"Approved: fill(ref='{got.ref}', value=<the {{id:...}} reference>, approval_id='{got.id}') now."
    elif got.kind == "approve":
        d["next"] = f"Approved: click(ref='{got.ref}', approval_id='{got.id}') now - only that button."
    elif got.kind in ("payment", "takeover"):
        d["next"] = "She says she did it herself. Read the page to see the result."
    elif got.kind in ("otp", "captcha", "secret"):
        d["next"] = "She typed it into the box (you can't see it). Now press the page's next / verify / login button."
    if got.status != "pending" and "main" in op.sessions:
        try:
            d["page"] = fmt_snapshot(await op.snapshot(op.sessions["main"]))
        except Exception:
            log.exception("operator: page after the owner's answer")
    return d


async def _recipe_run(job: Job, a: dict[str, Any]) -> dict[str, Any]:
    s = await job.sess(create=True)
    name = str(a.get("name", ""))
    variables = a.get("variables") or {}
    start = int(a.get("start_step") or 0)
    approval = None
    for _ in range(40):
        r = await run_recipe(job.op, job.mem, s, name, variables, start, approval)
        if r.get("status") != "waiting_human":
            if r.get("status") == "done":
                job.step(f"Seekha hua kaam poora: {name}")
            return r
        req = job.op.approvals.get(r["request"]["id"])
        got = await _wait_owner(job, s, req)
        if got.get("status") != "approved":
            return {"status": "stopped", "reason": got.get("next", ""), "done": r.get("done", []),
                    "resume_step": r.get("resume_step")}
        start = int(r.get("resume_step") or 0)
        approval = got["id"] if got.get("kind") == "approve" else None
    return {"status": "needs_help", "reason": "too many owner steps in a row"}


def _memory_tool(job: Job, name: str, a: dict[str, Any]) -> Any:
    m = job.mem
    if name == "recipe_find":
        return m.find(str(a.get("query", "")), a.get("site") or None)
    if name == "recipe_show":
        return m.load(str(a.get("name", "")))
    if name == "site_notes":
        return m.site_notes(str(a.get("site", ""))) or "No notes yet."
    if name == "site_note_add":
        return {"ok": True, "site": m.site_note_add(str(a.get("site", "")), str(a.get("note", ""))[:400])}
    if name == "playbook_get":
        return m.playbook_get(str(a.get("task", ""))) or "No playbook yet. Research it."
    if name == "playbook_save":
        return {"ok": True, "playbook": m.playbook_save(str(a.get("task", "")), str(a.get("steps_markdown", ""))[:8000],
                                                        [str(u)[:300] for u in (a.get("sources") or [])][:12])}
    raise OperatorError(name)


async def _research(name: str, a: dict[str, Any]) -> Any:
    from .. import web
    try:
        if name == "web_search":
            return await web.google_search(str(a.get("query", ""))[:300])
        if name == "read_url":
            r = await web.open_website(str(a.get("url", "")))
            if isinstance(r, dict) and "text" in r:
                r["text"] = str(r["text"])[:12000]
            return r
        return await _youtube(str(a.get("url", "")), str(a.get("question", "")))
    except web.WebError as e:
        return {"ok": False, "error": str(e)}


async def _youtube(url: str, question: str) -> dict[str, Any]:
    """Gemini watches the YouTube link itself (the official route used by Hoola Reels): steps shown in the video."""
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", url or "")
    if not m:
        return {"ok": False, "error": "Not a YouTube video link"}
    st = _st()
    if not st.gemini_api_key:
        return {"ok": False, "error": "Video dekhne ke liye GEMINI_API_KEY chahiye"}
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=st.gemini_api_key)
    model = getattr(st, "reels_gemini_model", "") or st.youtube_gemini_model or "gemini-2.5-flash"
    prompt = ("This is a how-to video about doing something on a website. List the exact steps it shows (pages, "
              "buttons, fields, documents, fees, mistakes to avoid), with timestamps. " + (question or ""))
    try:
        r = await asyncio.wait_for(client.aio.models.generate_content(model=model, contents=types.Content(role="user", parts=[
            types.Part(file_data=types.FileData(file_uri=f"https://www.youtube.com/watch?v={m.group(1)}")),
            types.Part(text=prompt)])), timeout=120)
    except Exception as e:
        return {"ok": False, "error": f"video not readable: {str(e)[:200]}"}
    return {"url": url, "steps": (r.text or "")[:8000]}
