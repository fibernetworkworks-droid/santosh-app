"""v0.402 REVIEW CARD - how good is Developer Sahayak's PR review, and do the ECC specialists make it better?
(owner: "GO ECC PHASE 1")

`python -m app.quality review [--modes old,new] [--k 1] [--only id,id] [--label x]`; vps-ops job `review_card`.
Each practice PR (review_tasks.PRS) is reviewed by the SAME function her real reviews use (devsahayak.service.explore_review)
against an in-memory copy of the shop repo at the PR head - no GitHub, nothing posted. Two modes:
  old = the v0.377 exploring review (dev_spec_review off)
  new = + ECC specialists (reviewer discipline, language reviewer, focused security / silent-failure / test passes)
Marks per run: caught (a medium / high comment within N lines of the planted line, on its file), quiet (a clean PR got no
medium / high comment), false alarms (medium / high comments matching no planted problem), nits (low comments), verdict
(request_changes on a planted bug, comment on a clean PR). --k runs every PR k times per mode (pass@k style)."""
from __future__ import annotations

import difflib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from . import code_repos as CR
from . import review_tasks as RT
from .codecard import MemGh

PARALLEL = 4


def _patch(old: str, new: str) -> str:
    lines = list(difflib.unified_diff(old.splitlines(), new.splitlines(), lineterm="", n=3))
    return "\n".join(ln for ln in lines if not ln.startswith(("---", "+++")))


def pr_inputs(pr: dict) -> tuple[dict[str, str], list[str], dict[str, set[int]]]:
    """The PR head's files, the diff parts and the added-lines map, built exactly like service.review builds them."""
    from ..devsahayak import rules as R
    head = {**CR.DUKAAN, **pr["files"]}
    parts, added_lines = [], {}
    for path, new in pr["files"].items():
        old = CR.DUKAAN.get(path, "")
        patch = _patch(old, new)
        added = R.patch_added(patch)
        added_lines[path] = {ln for ln, _ in added}
        shown = "\n".join(f"[L{ln}] +{tx}" for ln, tx in added)[:8000]
        parts.append(f'<pr_diff file="{path}" status="{"modified" if old else "added"}" additions="{len(added)}">\n'
                     f'{shown}\n</pr_diff>')
    return head, parts, added_lines


def spot_line(pr: dict) -> int:
    """The line of the planted problem in the PR head's file."""
    b = pr["bug"]
    for i, ln in enumerate(pr["files"][b["path"]].splitlines(), 1):
        if b["spot"] in ln:
            return i
    raise ValueError(f"{pr['id']}: spot not found")


def _said(c: dict) -> str:
    return f"{c.get('severity')} {c.get('path')}:{c.get('line')} - {' '.join(str(c.get('body') or '').split())[:220]}"


def score(pr: dict, out: dict) -> dict[str, Any]:
    comments = [c for c in out.get("comments") or [] if not str(c.get("body") or "").startswith("[Hoola check]")]
    real = [c for c in comments if c.get("severity") in ("medium", "high")]
    row: dict[str, Any] = {"id": pr["id"], "bug": bool(pr["bug"]), "comments": len(comments),
                           "nits": sum(1 for c in comments if c.get("severity") not in ("medium", "high")),
                           "verdict": out.get("verdict") or "comment"}
    if pr["bug"]:
        line, near = spot_line(pr), int(pr["bug"].get("near", 3))
        hits = [c for c in real if c.get("path") == pr["bug"]["path"] and abs(int(c.get("line") or 0) - line) <= near]
        row["caught"] = bool(hits)
        row["false_alarms"] = len([c for c in real if c not in hits])
        row["alarms"] = [_said(c) for c in real if c not in hits][:5]
        row["verdict_ok"] = row["verdict"] == "request_changes"
        row["right"] = row["caught"] and row["verdict_ok"]
    else:
        row["false_alarms"] = len(real)
        row["alarms"] = [_said(c) for c in real][:5]   # v0.410 what the alarm SAID, so a fair point can be told from a wrong one
        row["quiet"] = not real
        row["verdict_ok"] = row["verdict"] != "request_changes"
        row["right"] = row["quiet"] and row["verdict_ok"]
    return row


def run_pr(pr: dict) -> dict[str, Any]:
    from ..devsahayak import service as S
    head, parts, added = pr_inputs(pr)
    pr_text = f"<pr>\nRepo hoola/reviewcard PR: {pr['title']}\nBy: practice\n{pr['body']}\n</pr>"
    t0 = time.time()
    try:
        out = S.explore_review(MemGh(head), "hoola/reviewcard", "head0000", pr_text, parts, added, "", "")
    except Exception as e:  # noqa: BLE001 - one broken review never stops the card
        return {"id": pr["id"], "bug": bool(pr["bug"]), "right": False, "error": str(e)[:200], "comments": 0, "nits": 0,
                "false_alarms": 0, "verdict": "", "seconds": round(time.time() - t0)}
    row = score(pr, out)
    lp = out.get("loop") or {}
    row.update(seconds=round(time.time() - t0), steps=lp.get("steps", 0), passes=lp.get("passes") or ["main"])
    return row


def _mode(name: str, prs: list[dict], k: int, parallel: int) -> dict[str, Any]:
    from ..config import get_settings
    st = get_settings()
    old = getattr(st, "dev_spec_review", False)
    setattr(st, "dev_spec_review", name == "new")      # modes run one after another, so this switch is never shared
    try:
        with ThreadPoolExecutor(max_workers=max(1, parallel)) as ex:
            rows = list(ex.map(run_pr, [p for p in prs for _ in range(max(1, k))]))
    finally:
        setattr(st, "dev_spec_review", old)
    bugs, clean = [r for r in rows if r["bug"]], [r for r in rows if not r["bug"]]
    return {"mode": name, "runs": len(rows), "right": sum(r["right"] for r in rows),
            "caught": sum(bool(r.get("caught")) for r in bugs), "bug_runs": len(bugs),
            "quiet": sum(bool(r.get("quiet")) for r in clean), "clean_runs": len(clean),
            "false_alarms": sum(r["false_alarms"] for r in rows), "nits": sum(r["nits"] for r in rows),
            "verdicts_ok": sum(bool(r.get("verdict_ok")) for r in rows),
            "steps_avg": round(sum(r.get("steps", 0) for r in rows) / max(1, len(rows)), 1), "rows": rows}


def card(modes: list[str] | None = None, k: int = 1, only: list[str] | None = None, parallel: int = PARALLEL) -> dict:
    prs = [p for p in RT.PRS if not only or p["id"] in only]
    t0 = time.time()
    out = {"kind": "review", "set": RT.SET, "k": k, "prs": len(prs),
           "modes": [_mode(m, prs, k, parallel) for m in (modes or ["old", "new"])]}
    out["minutes"] = round((time.time() - t0) / 60, 1)
    return out


def save(cd: dict, label: str = "") -> dict:
    from .toolchoice import _dir
    cd = {**cd, "label": label, "at": int(time.time())}
    name = f"review-{time.strftime('%Y%m%d-%H%M%S')}.json"
    (_dir() / name).write_text(json.dumps(cd, ensure_ascii=False, indent=1))
    cd["file"] = name
    return cd


def lines(cd: dict) -> list[str]:
    out = [f"Review card (set v{cd['set']}, {cd['prs']} PRs x{cd['k']}, {cd.get('minutes', 0)} min):"]
    for m in cd["modes"]:
        out.append(f"  {m['mode']:>3}: {m['right']}/{m['runs']} right · caught {m['caught']}/{m['bug_runs']} planted bugs · "
                   f"quiet on {m['quiet']}/{m['clean_runs']} clean PRs · false alarms {m['false_alarms']} · nits {m['nits']} · "
                   f"verdicts {m['verdicts_ok']}/{m['runs']} · {m['steps_avg']} steps")
    if len(cd["modes"]) == 2:
        a, b = cd["modes"]
        better = (b["right"] - a["right"], a["false_alarms"] - b["false_alarms"])
        out.append(f"  {b['mode']} vs {a['mode']}: {better[0]:+d} right, {better[1]:+d} fewer false alarms")
    for m in cd["modes"]:
        for r in m["rows"]:
            if not r["right"]:
                why = r.get("error") or (("missed the bug" if not r.get("caught") else "") if r["bug"] else
                                         f"{r['false_alarms']} false alarm(s) on a clean PR")
                if r["bug"] and r.get("caught") and not r.get("verdict_ok"):
                    why = "caught, but verdict was not request_changes"
                if not r["bug"] and r.get("quiet") and not r.get("verdict_ok"):
                    why = "quiet, but verdict was request_changes"
                out.append(f"  MISS [{m['mode']}] {r['id']} - {why}")
                out += [f"      said: {x}" for x in r.get("alarms") or []]
    return out
