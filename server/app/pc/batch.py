"""v0.885 REPEAT JOBS on Hoola's own PC - the same portal work for every row of her sheet, human in the loop.

Owner (13 Nov 2026): Hoola PC is "BEST FOR LEGACY PORTALS AND GOV PORTALS WHERE NEED A HUGE REPEATED MANUAL WORK",
then "Shared pool AND HUMAN IN LOOP".

How it runs:
1. Her task has {Column} blanks; the rows come from her Excel / CSV in the chat (or a list). Every blank must be a
   column, checked before anything starts.
2. ROW 1 runs like any Hoola PC task: every submit asks her (the normal confirm card), she watches it live.
3. Row 1 done -> a confirm card with the proof screenshot: "Row 1 ho gaya ... baaki N rows chalaun?". Nothing more runs
   until her tap. No tap = the job waits (hoola_pc_batch go asks the card again - the model can never approve it).
4. Rows 2..N run one after another on the same Hoola PC (her logins stay open); a submit of the same kind needs no new
   card, but money, deletes, installs and settings still ask her every time. An OTP / CAPTCHA is asked like always.
5. Three rows failing in a row pauses the job and tells her why. A server restart pauses it too: the row that was cut
   is marked 'check on the portal' (it may or may not have been submitted - never submitted twice by Hoola).
6. At the end: one Excel sheet in her chat - every row, what happened, the proof screenshot link, files it sent.
"""
from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import re
import secrets
import time
from pathlib import Path
from typing import Any

from ..config import get_settings
from .hub import HOOLA_PC_KIND

log = logging.getLogger("santosh.pc")

RUNNERS: dict[str, asyncio.Task] = {}
_BLANK = re.compile(r"\{([^{}]{1,60})\}")
FAIL_RUN = 3                      # rows failing in a row before the job pauses


class BatchError(Exception):
    pass


def _tell(conv: str, text: str) -> None:
    """One line in her chat; a failure to write it never stops the job."""
    try:
        from ..events import notify
        notify(conv, text)
    except Exception:
        log.exception("hoola batch note failed")


def _dir() -> Path:
    d = Path(get_settings().pc_files_dir).parent / "hoola_batches"   # beside the PC files (kept across restarts)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _path(bid: str) -> Path:
    if not re.fullmatch(r"hb_[a-f0-9]{10}", bid or ""):
        raise BatchError("No such repeat job.")
    return _dir() / f"{bid}.json"


def save(b: dict[str, Any]) -> None:
    b["updated"] = time.time()
    tmp = _path(b["id"]).with_suffix(".tmp")
    tmp.write_text(json.dumps(b, ensure_ascii=False))
    tmp.replace(_path(b["id"]))


def load(tenant: str, bid: str) -> dict[str, Any]:
    p = _path(bid)
    if not p.exists():
        raise BatchError("No such repeat job.")
    b = json.loads(p.read_text())
    if b.get("tenant") != tenant:
        raise BatchError("No such repeat job.")
    return b


def mine(tenant: str) -> list[dict[str, Any]]:
    out = []
    for p in sorted(_dir().glob("hb_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:30]:
        try:
            b = json.loads(p.read_text())
        except ValueError:
            continue
        if b.get("tenant") == tenant:
            out.append(b)
    return out


# ------------------------------------------------------------------ rows
def _cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if hasattr(v, "strftime"):
        return v.strftime("%d-%m-%Y")
    return str(v).strip()


def rows_from_bytes(name: str, data: bytes, sheet: str = "") -> tuple[list[str], list[dict[str, str]]]:
    """Header row + data rows of an Excel / CSV file (empty rows skipped)."""
    low = name.lower()
    table: list[list[str]] = []
    if low.endswith((".xlsx", ".xlsm")):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        ws = wb[sheet] if sheet and sheet in wb.sheetnames else wb.worksheets[0]
        for r in ws.iter_rows(values_only=True):
            table.append([_cell(v) for v in r])
    elif low.endswith((".csv", ".txt", ".tsv")):
        text = data.decode("utf-8-sig", "replace")
        dialect = csv.excel_tab if low.endswith(".tsv") or text.count("\t") > text.count(",") else csv.excel
        table = [[c.strip() for c in r] for r in csv.reader(io.StringIO(text), dialect)]
    else:
        raise BatchError("Rows can come from an Excel (.xlsx) or CSV file.")
    table = [r for r in table if any(c for c in r)]
    if len(table) < 2:
        raise BatchError("The file needs a header row and at least one row below it.")
    head = [h or f"Column {i + 1}" for i, h in enumerate(table[0])]
    rows = [{head[i]: (r[i] if i < len(r) else "") for i in range(len(head))} for r in table[1:]]
    return head, rows


def _col(columns: list[str], name: str) -> str | None:
    want = " ".join(name.lower().split())
    return next((c for c in columns if " ".join(c.lower().split()) == want), None)


def blanks(task: str, columns: list[str]) -> tuple[list[str], list[str]]:
    """(blanks that are columns, blanks that are not)."""
    names = list(dict.fromkeys(m.strip() for m in _BLANK.findall(task)))
    ok = [n for n in names if _col(columns, n)]
    return ok, [n for n in names if not _col(columns, n)]


def fill(task: str, columns: list[str], row: dict[str, str]) -> str:
    return _BLANK.sub(lambda m: row.get(_col(columns, m.group(1).strip()) or "", m.group(0)), task)


def row_task(b: dict[str, Any], i: int) -> str:
    n, total = i + 1, len(b["rows"])
    row = b["rows"][i]
    vals = "; ".join(f"{k} = {v}" for k, v in row.items() if v)[:1500]
    head = (f"REPEAT JOB row {n} of {total}" + (" (the FIRST row - she is watching; ask her before every submit)"
                                               if i == 0 else " (do it exactly like row 1)") + ".\n")
    return head + fill(b["task"], b["columns"], row) + f"\nThis row's values: {vals}"


# ------------------------------------------------------------------ start / run
async def create(tenant: str, conv: str, task: str, file_id: str = "", rows: Any = None, sheet: str = "") -> dict:
    task = str(task or "").strip()
    if len(task) < 10:
        raise BatchError("Write the job once, with {Column} blanks for what changes per row.")
    if file_id:
        from ..mailbox import service as ms
        try:
            f = ms._file_row(tenant, str(file_id))
        except Exception as e:
            raise BatchError(str(e))
        data = await asyncio.to_thread(Path(f.stored_path).read_bytes)
        columns, table = await asyncio.to_thread(rows_from_bytes, f.name, data, str(sheet or ""))
        source = f.name
    elif isinstance(rows, list) and rows and all(isinstance(r, dict) for r in rows):
        columns = list(dict.fromkeys(str(k) for r in rows for k in r))
        table = [{c: _cell(r.get(c)) for c in columns} for r in rows]
        source = "list"
    else:
        raise BatchError("Give the rows: her Excel / CSV file from the chat (file_id) or a list of rows.")
    limit = int(getattr(get_settings(), "hoola_batch_max_rows", 500) or 500)
    if len(table) > limit:
        raise BatchError(f"{len(table)} rows is more than {limit} in one repeat job - split the file.")
    ok, bad = blanks(task, columns)
    if bad:
        raise BatchError(f"These blanks are not columns of the sheet: {', '.join(bad)}. Columns: {', '.join(columns)}.")
    if not ok:
        raise BatchError("The job has no {Column} blank, so every row would do the same thing. "
                         f"Put the changing parts in braces, e.g. {{{columns[0]}}}. Columns: {', '.join(columns)}.")
    b = {"id": "hb_" + secrets.token_hex(5), "tenant": tenant, "conv": conv, "task": task[:3000], "columns": columns,
         "rows": table, "source": source, "results": [None] * len(table), "state": "row1", "go": False, "pc": "",
         "created": time.time()}
    save(b)
    _spawn(b)
    log.info("hoola batch %s start tenant=%s rows=%d blanks=%s | %s", b["id"], tenant, len(table), ok, task[:160])
    return summary(b)


def _spawn(b: dict[str, Any]) -> None:
    old = RUNNERS.get(b["id"])
    if old is not None and not old.done():
        return
    RUNNERS[b["id"]] = asyncio.create_task(_run(b["tenant"], b["id"]))


async def _row(b: dict[str, Any], i: int, batch_ok: bool) -> dict[str, Any]:
    from . import operator
    r = await operator.start(b["tenant"], b["conv"], row_task(b, i), wait=0, kind=HOOLA_PC_KIND, pc=b.get("pc") or "",
                             quiet=(i > 0), batch_ok=batch_ok)
    op = operator.get(b["tenant"], r["session_id"])
    b["live"] = r["session_id"]
    save(b)
    if op is None:
        return {"row": i + 1, "status": "failed", "summary": "could not start"}
    await op.done_event.wait()
    if op.device_id:
        b["pc"] = op.device_id          # the next rows stay on this PC (her portal login is open there)
    return {"row": i + 1, "status": op.status, "summary": (op.summary or op.reason or "")[:500],
            "proof": (op.proof or {}).get("url", ""), "files": list(op.sent_files)[-5:], "session": op.id,
            "at": time.time(), "auto_ok": op.batch_auto}


async def _run(tenant: str, bid: str) -> None:
    b = load(tenant, bid)
    try:
        if b["results"][0] is None:
            b["state"] = "row1"
            save(b)
            res = await _row(b, 0, batch_ok=False)
            b["results"][0] = res
            save(b)
            if res["status"] != "done":
                b["state"] = "stopped"
                save(b)
                _tell(b["conv"], f"Repeat job: row 1 poora nahi hua ({res['summary'][:200] or res['status']}). "
                                  "Baaki rows shuru nahi ki - pehle row 1 theek karein.")
                return
        if not b.get("go"):
            if not await ask_go(b):
                return
        b["state"] = "running"
        save(b)
        fails = 0
        for i in range(len(b["rows"])):
            b = load(tenant, bid)
            if b.get("state") != "running":
                return
            if b["results"][i] is not None:
                continue
            res = await _row(b, i, batch_ok=True)
            b = {**load(tenant, bid), "pc": b.get("pc", "")}
            b["results"][i] = res
            fails = fails + 1 if res["status"] != "done" else 0
            save(b)
            if res["status"] == "cancelled":
                b["state"] = "stopped"
                save(b)
                _tell(b["conv"], f"Repeat job rok diya gaya (row {i + 1} par). {_counts(b)}")
                return
            if fails >= FAIL_RUN:
                b["state"] = "paused"
                save(b)
                _tell(b["conv"], f"Repeat job ruk gaya: {FAIL_RUN} rows lagatar fail hui (row {i + 1}: "
                                  f"{res['summary'][:200]}). {_counts(b)} Theek karke boliye 'repeat job chalu karo'.")
                return
        b["state"] = "done"
        save(b)
        await finish(b)
    except asyncio.CancelledError:
        try:
            b = load(tenant, bid)
            if b.get("state") in ("row1", "running", "waiting_go"):
                b["state"] = "stopped"
                save(b)
        except Exception:
            pass
        raise
    except Exception as e:
        log.exception("hoola batch %s failed", bid)
        try:
            b = load(tenant, bid)
            b["state"], b["error"] = "paused", f"{type(e).__name__}: {e}"[:300]
            save(b)
            _tell(b["conv"], f"Repeat job ruk gaya ({b['error'][:150]}). {_counts(b)}")
        except Exception:
            pass


async def ask_go(b: dict[str, Any]) -> bool:
    """The human in the loop: her tap on a card after she saw row 1 (never the model)."""
    from . import operator
    op = operator.get(b["tenant"], (b["results"][0] or {}).get("session") or b.get("live") or "")
    b["state"] = "waiting_go"
    save(b)
    left = len(b["rows"]) - sum(1 for r in b["results"] if r)
    first = b["results"][0] or {}
    what = (f"Repeat job: row 1 ho gaya ({first.get('summary', '')[:160]}). Proof screenshot chat mein hai. Baaki "
            f"{left} rows isi tarah chalaun? Same tarah ka submit apne aap hoga; paise / delete / OTP par phir bhi poochunga.")
    if op is None:
        _tell(b["conv"], what + " (Haan ke liye boliye: 'repeat job chalao'.)")
        return False
    ok = await operator.ask_tap(op, what)
    b = load(b["tenant"], b["id"])
    if not ok:
        b["state"] = "waiting_go"
        save(b)
        _tell(b["conv"], "Repeat job: baaki rows abhi nahi chalayi. Jab chalani ho, boliye 'repeat job chalao'.")
        return False
    b["go"], b["state"] = True, "running"
    save(b)
    return True


def _counts(b: dict[str, Any]) -> str:
    rs = [r for r in b["results"] if r]
    done = sum(1 for r in rs if r["status"] == "done")
    return f"{done} ho gayi, {len(rs) - done} nahi hui, {len(b['rows']) - len(rs)} baaki."


def sheet_bytes(b: dict[str, Any]) -> bytes:
    import openpyxl
    from openpyxl.styles import Font
    base = (getattr(get_settings(), "public_base_url", "") or "").rstrip("/")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Results"
    head = ["Row", *b["columns"], "Result", "What happened", "Proof screenshot", "Files sent to chat"]
    ws.append(head)
    for c in ws[1]:
        c.font = Font(bold=True)
    word = {"done": "Done", "partial": "Not finished", "failed": "Failed", "cancelled": "Stopped",
            "unknown": "CHECK ON PORTAL"}
    for i, row in enumerate(b["rows"]):
        r = b["results"][i] or {}
        proof = r.get("proof") or ""
        ws.append([i + 1, *[row.get(c, "") for c in b["columns"]], word.get(r.get("status"), "Not run"),
                   r.get("summary", ""), (base + proof) if proof else "", ", ".join(r.get("files") or [])])
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = min(48, max(10, *(len(str(c.value or "")) for c in col)))
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


async def finish(b: dict[str, Any]) -> None:
    from . import pool
    data = await asyncio.to_thread(sheet_bytes, b)
    f = await asyncio.to_thread(pool.store_bytes, b["tenant"], b.get("pc", ""),
                                f"repeat-job-{time.strftime('%d%b-%H%M')}.xlsx", data)
    pool.publish(b["conv"], f, "Repeat job results (every row)")
    _tell(b["conv"], f"Repeat job poora: {_counts(b)} Har row ka nateeja aur proof Excel mein hai.")


# ------------------------------------------------------------------ her controls
def summary(b: dict[str, Any]) -> dict[str, Any]:
    rs = [r for r in b["results"] if r]
    return {"batch_id": b["id"], "state": b["state"], "rows": len(b["rows"]), "columns": b["columns"],
            "done": sum(1 for r in rs if r["status"] == "done"), "not_done": sum(1 for r in rs if r["status"] != "done"),
            "left": len(b["rows"]) - len(rs), "source": b.get("source", ""),
            "next": {"row1": "Row 1 is running on Hoola PC - she watches it and approves its submit.",
                     "waiting_go": "Row 1 is done; the job waits for HER tap on the card to run the other rows.",
                     "running": "The rows are running one by one.",
                     "paused": "Paused - tell her why (see the last results); continue only when she says so.",
                     "stopped": "Stopped.", "done": "Finished - the result sheet is in her chat."}.get(b["state"], ""),
            "last": [r for r in rs][-3:]}


async def control(tenant: str, bid: str, action: str) -> dict[str, Any]:
    b = load(tenant, bid)
    if action == "status":
        return summary(b)
    if action == "stop":
        b["state"] = "stopped"
        save(b)
        from . import operator
        sid = b.get("live")
        if sid:
            operator.stop(tenant, sid)
        t = RUNNERS.get(bid)
        if t is not None and not t.done():
            t.cancel()
        return summary(b)
    if action in ("go", "resume"):
        running = RUNNERS.get(bid)
        if running is not None and not running.done():
            return {**summary(b), "note": "It is already running / waiting for her tap on the card."}
        if b["state"] == "done":
            return summary(b)
        if action == "resume" and not b.get("go"):
            action = "go"
        if b["state"] in ("paused", "stopped") and b.get("go"):
            b["state"] = "running"
            save(b)
        elif not b.get("go"):
            b["state"] = "waiting_go"      # the runner asks her card again; only HER tap lets the rows run
            save(b)
        _spawn(b)
        return {**summary(b), "note": "Started again." if b.get("go") else
                "Her confirm card is shown again - the rows run only after her tap."}
    raise BatchError("action is start, status, go, resume or stop")


def sweep_after_restart() -> int:
    """A server restart killed every runner: a job that was running is PAUSED, the row that was cut is marked
    'check on the portal' (it may have been submitted - Hoola never submits it a second time by itself)."""
    n = 0
    for p in _dir().glob("hb_*.json"):
        try:
            b = json.loads(p.read_text())
        except ValueError:
            continue
        if b.get("state") not in ("row1", "running", "waiting_go") or (RUNNERS.get(b["id"]) and not RUNNERS[b["id"]].done()):
            continue
        cut = next((i for i, r in enumerate(b["results"]) if r is None), None)
        if cut is not None and b.get("state") in ("row1", "running"):
            b["results"][cut] = {"row": cut + 1, "status": "unknown", "summary": "cut by a server restart - check this "
                                 "row on the portal", "at": time.time()}
        b["state"] = "paused"
        save(b)
        n += 1
        try:
            _tell(b["conv"], f"Repeat job server restart se ruk gaya" + (f" (row {cut + 1} beech mein kata - portal "
                              "par check kar lijiye)" if cut is not None else "") + f". {_counts(b)} Aage chalane ke "
                              "liye boliye 'repeat job chalu karo'.")
        except Exception:
            pass
    return n
