"""v0.999.93 read the step records of the PC card's FAILED jobs (vps-ops pc_trace).

    python -m app.quality.pctrace_read [card file] [--all] [--steps N]

Finds the newest PC card in data/quality, and for every job that did not pass prints what the PC really did, step by
step, from data/pc_trace (written by pc/trace.py): the tool, what it said it was doing, the masked arguments, the window,
the model's one-line thought and how long the step took. A card from before v0.999.93 has no job ids: its jobs are found
by the practice run and the task's words. Read only; prints nothing secret (arguments were masked when written)."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


def _cards(root: Path) -> list[Path]:
    return sorted(root.glob("pccard-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)


def _asks() -> dict[str, str]:
    try:
        from . import pccard_browser, pccard_portal
        d = {t["id"]: t["ask"] for t in list(pccard_browser.TASKS) + list(pccard_portal.TASKS)}
        if "login_handoff" in d:
            d["login_code"] = d["login_handoff"]         # its name in set v1 (same words)
        return d
    except Exception:   # noqa: BLE001
        return {}


def _metas(trace_root: Path) -> list[tuple[Path, dict]]:
    out = []
    for m in trace_root.glob("*/*/meta.json"):
        try:
            out.append((m.parent, json.loads(m.read_text())))
        except Exception:   # noqa: BLE001
            continue
    return out


def find_job(row: dict, card: dict, metas: list[tuple[Path, dict]], asks: dict[str, str]) -> Path | None:
    if row.get("job"):
        for d, meta in metas:
            if d.name == row["job"]:
                return d
        return None          # a card with job ids never borrows another run's record (it showed an older run's job once)
    run, ask = str(card.get("practice_run") or ""), asks.get(str(row.get("id")), "")
    tail = ask.split("{P}", 1)[1][:40] if "{P}" in ask else ask[:40]
    best = None
    for d, meta in metas:
        task = str(meta.get("task") or "")
        if tail and tail in task and (not run or run in task):
            if best is None or (meta.get("started") or 0) > (best[1].get("started") or 0):
                best = (d, meta)
    return best[0] if best else None


_PC_LOG = re.compile(r"pc task|pc act|pc brain|pc step|pc rescue|pc think|asks her|got her answer|BrainSlow|CreditLow|402|timed? ?out|Traceback|ERROR", re.I)
_TS = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)")


def _log_tail(n: int = 80000) -> list[str]:
    """v0.999.107 the server's own log (pm2) - the PC lines say where a job's minutes went (a model step, a screenshot,
    an action). Read only; nothing secret is written there."""
    path = Path(os.environ.get("PCTRACE_LOG") or os.path.expanduser("~/.pm2/logs/santosh-error.log"))
    try:
        with path.open("rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(max(0, size - 24_000_000))
            return fh.read().decode("utf-8", "replace").splitlines()[-n:]
    except OSError:
        return []


def server_lines(meta: dict, log_lines: list[str], limit: int = 40) -> list[str]:
    """The PC lines of the server log written while this job ran (by time; 'pc brain' lines carry no job id)."""
    import datetime as _dt
    t0, t1 = float(meta.get("started") or 0), float(meta.get("ended") or 0) or (float(meta.get("started") or 0) + 900)
    if not t0 or not log_lines:
        return []
    out = []
    for ln in log_lines:
        m = _TS.match(ln)
        if not m or not _PC_LOG.search(ln):
            continue
        try:
            ts = _dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=_dt.timezone.utc).timestamp()
        except ValueError:
            continue
        if t0 - 2 <= ts <= t1 + 2:
            out.append(ln[:260])
    return out[-limit:]


def credit_out(rows: list[dict]) -> int:
    """Jobs that stopped because the AI account ran out of credit (not Hoola's doing - the card says so first)."""
    return sum(1 for r in rows if "credit is low" in str(r.get("why") or r.get("reason") or "").lower())


def report(card_path: Path, trace_root: Path, show_all: bool = False, max_steps: int = 40) -> list[str]:
    card = json.loads(card_path.read_text())
    rows = card.get("rows") or []
    metas, asks = _metas(trace_root), _asks()
    log_lines = _log_tail()
    lines = [f"== card {card_path.name}: {card.get('exam', '')} on {card.get('pc', '')}, practice run "
             f"{card.get('practice_run') or '-'}, {sum(1 for r in rows if r.get('ok'))}/{len(rows)} passed"]
    if credit_out(rows):
        lines.append(f"!! {credit_out(rows)} job(s) stopped because the OpenRouter credit ran out - add credit at "
                     "openrouter.ai, then run the exam again; those jobs say nothing about Hoola")
    for r in rows:
        if r.get("ok") and not show_all:
            continue
        lines.append("")
        lines.append(f"### {r.get('id')}: {'PASS' if r.get('ok') else 'FAIL'} {r.get('status', '')} "
                     f"{r.get('seconds', '')}s {r.get('steps', '')} steps - {str(r.get('why') or r.get('reason') or '')[:160]}")
        if r.get("approval_asked"):
            lines.append(f"   approval it asked for: {str(r['approval_asked'])[:200]}")
        if r.get("asked_q"):
            lines.append(f"   it asked her: {str(r['asked_q'])[:200]}")
        if r.get("blocked_said"):
            lines.append("   the site refused this cloud computer and Hoola said so (a job for her own PC)")
        d = find_job(r, card, metas, asks)
        if d is None:
            lines.append("   (no step record found for this job)")
            continue
        meta = json.loads((d / "meta.json").read_text())
        lines.append(f"   job {d.name}: status {meta.get('status')}, summary: {str(meta.get('summary') or '')[:300]}")
        prev = meta.get("started") or 0
        steps = []
        if (d / "steps.jsonl").exists():
            for ln in (d / "steps.jsonl").read_text().splitlines():
                try:
                    steps.append(json.loads(ln))
                except Exception:   # noqa: BLE001
                    continue
        for s in steps[:max_steps]:
            took = round(float(s.get("t") or 0) - float(prev or 0), 1) if prev else ""
            prev = s.get("t") or prev
            args = json.dumps(s.get("args") or {}, ensure_ascii=False)[:180]
            lines.append(f"   {s.get('n')}. +{took}s {s.get('tool')} {args} | {str(s.get('action') or '')[:90]}"
                         + (f" | window: {str(s.get('window'))[:60]}" if s.get("window") else ""))
            if s.get("thought"):
                lines.append(f"      thinks: {str(s['thought'])[:220]}")
        if len(steps) > max_steps:
            lines.append(f"   ... {len(steps) - max_steps} more steps")
        srv = server_lines(meta, log_lines)
        if srv:
            lines.append("   server log while it ran (where the time went):")
            lines.extend("     " + x for x in srv)
    return lines


def main(argv: list[str]) -> int:
    base = Path(os.environ.get("HOOLA_CORE", "."))
    q = base / "data" / "quality"
    trace_root = Path(os.environ.get("PC_TRACE_DIR") or (base / "data" / "pc_trace"))
    args = [a for a in argv if not a.startswith("--")]
    show_all = "--all" in argv
    n = 40
    for a in argv:
        if a.startswith("--steps="):
            n = max(5, min(int(a.split("=", 1)[1] or 40), 200))
    card = Path(args[0]) if args else (_cards(q) or [None])[0]
    if card is None or not card.exists():
        print("no PC card found in", q)
        return 1
    print("\n".join(report(card, trace_root, show_all, n)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
