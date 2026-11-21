"""v0.999.93 read the step records of the PC card's FAILED jobs (vps-ops pc_trace).

    python -m app.quality.pctrace_read [card file] [--all] [--steps N]

Finds the newest PC card in data/quality, and for every job that did not pass prints what the PC really did, step by
step, from data/pc_trace (written by pc/trace.py): the tool, what it said it was doing, the masked arguments, the window,
the model's one-line thought and how long the step took. A card from before v0.999.93 has no job ids: its jobs are found
by the practice run and the task's words. Read only; prints nothing secret (arguments were masked when written)."""
from __future__ import annotations

import json
import os
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
    run, ask = str(card.get("practice_run") or ""), asks.get(str(row.get("id")), "")
    tail = ask.split("{P}", 1)[1][:40] if "{P}" in ask else ask[:40]
    best = None
    for d, meta in metas:
        task = str(meta.get("task") or "")
        if tail and tail in task and (not run or run in task):
            if best is None or (meta.get("started") or 0) > (best[1].get("started") or 0):
                best = (d, meta)
    return best[0] if best else None


def report(card_path: Path, trace_root: Path, show_all: bool = False, max_steps: int = 40) -> list[str]:
    card = json.loads(card_path.read_text())
    rows = card.get("rows") or []
    metas, asks = _metas(trace_root), _asks()
    lines = [f"== card {card_path.name}: {card.get('exam', '')} on {card.get('pc', '')}, practice run "
             f"{card.get('practice_run') or '-'}, {sum(1 for r in rows if r.get('ok'))}/{len(rows)} passed"]
    for r in rows:
        if r.get("ok") and not show_all:
            continue
        lines.append("")
        lines.append(f"### {r.get('id')}: {'PASS' if r.get('ok') else 'FAIL'} {r.get('status', '')} "
                     f"{r.get('seconds', '')}s {r.get('steps', '')} steps - {str(r.get('why') or r.get('reason') or '')[:160]}")
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
