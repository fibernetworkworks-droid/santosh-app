"""G9 of docs/LANGGRAPH_TURN_PLAN.md - Hoola Code's honest "done" (G3's rule) and its end notice told once (G5's record).

Hoola Code has its own engine (engine.py / brain.py / service.py) and never runs on the chat's turn graph, so the G3
check node never sees a coding round. Before G9 the end of a round was said from the task's status and the model's own
finishing words (its `explain` / `test_plan`): "fixed, all tests pass" was shown even when the last test command in the
box exited 1 and CI was still running.

WHY A DEVSAHAYAK-SIDE FACT BUILDER (and not turnfacts.step_facts / verdicts directly): turnfacts builds a fact from a
chat tool_use + its tool_result + its G1 ledger row and judges a claim through `draftcheck.family_of` (the chat tools
that send / book / pay). A coding round has none of those: its evidence is box commands with exit codes (the session's
structured `steps`), a commit + push that really returned a sha (`head_sha` / `branch`), a PR object GitHub gave back
(`pr_number` / `pr_url`), CI's state as read from GitHub (`ci`) and the local lab check (`proof`). So the facts are
built here from the task row, in THE SAME SHAPE and vocabulary as G3 ({id, tool, step, effect, ledger, object, error},
effect did / failed / ambiguous / stopped, verdict true / failed / unknown / stopped / none - `turnfacts.DONE_LIKE` /
`NEVER_DONE` are the same tuples), and the claims of the model's words are judged ONLY by those facts.

A claim with no backing fact is never "done": the task card carries `truth` (confirmed / the claims and why) and
`tell_end` says "not confirmed" instead of "ready". The facts come from the row, never from the words; the words are
only searched for WHAT was claimed.

TOLD ONCE: `tell_end`'s notice goes through `turndeliver.once(key, "push", ...)` with the key
    devsahayak:<task>:r<rounds>.<ci_round>.<self_round>:<status>:<head sha 12>
= one key per finished round outcome. A resumed run (service._resume_cut_runs) that ends in the same state, a second
call, a restart between the send and its stamp - none tells it again; a NEW round (a revise, a CI fix round, an own
review round, a new push) has a new key and is told once.

Switch `dev_truth` (default on); off = tell_end and task_view exactly as before G9."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

log = logging.getLogger("santosh.devsahayak.truth")

STATS = {"judged": 0, "unconfirmed": 0, "told": 0, "already_told": 0}

_TEST_CMD = re.compile(r"(?i)\b(pytest|py\.test|unittest|tox|nox|(npm|yarn|pnpm|bun)\s+(run\s+)?test|jest|vitest|mocha|"
                       r"go\s+test|cargo\s+test|mvn\s+(-\S+\s+)*test|gradlew?\s+test|flutter\s+test|dart\s+test|rspec|"
                       r"phpunit|make\s+(check|test)|ctest|dotnet\s+test|swift\s+test|mix\s+test)\b")
# what the model's words claim, and which fact kind would make the claim true
_CLAIMS = (
    ("tests", re.compile(r"(?i)\b(all\s+(the\s+)?)?tests?\s+(now\s+|all\s+)?(pass(es|ed|ing)?|green|succeed(ed|s)?|ok)\b|"
                         r"\bpass(es|ed|ing)?\s+(all\s+)?(the\s+)?tests\b|\btests?\s+are\s+(passing|green)\b|"
                         r"\bci\s+(is\s+)?(green|pass(es|ed|ing)?)\b")),
    ("pr", re.compile(r"(?i)\b(pr|pull\s+request)\b[^.!?\n]{0,30}\b(is\s+)?(ready|open(ed)?|created|up)\b|"
                      r"\b(opened|created|raised)\s+(a|the)\s+(pr|pull\s+request)\b")),
    ("push", re.compile(r"(?i)\b(pushed|committed\s+and\s+pushed)\b")),
    ("fixed", re.compile(r"(?i)\b(fixed|resolved|solved)\b|\bis\s+fixed\b")),
)
# a sentence that only plans, asks or hedges is not a claim ("run pytest - all tests should pass")
_NOT_CLAIM = re.compile(r"(?i)\b(should|will|would|must|could|may|might|expect(ed)?|make\s+sure|ensure|verify|"
                        r"not|n't|never|unable|cannot|unverified|untested|if|once|after\s+(you|she)|to\s+be|"
                        r"run\s+|please)\b|\?")
_SENT = re.compile(r"(?<=[.!?])\s+|\n+")
_EXIT = re.compile(r"\(exit (-?\d+|None)\)\s*$")


def on() -> bool:
    try:
        from ..config import get_settings
        return bool(getattr(get_settings(), "dev_truth", True))
    except Exception:   # noqa: BLE001
        return False


def _j(v: Any, d: Any) -> Any:
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v) if v else d
    except (TypeError, ValueError):
        return d


def _fact(fid: str, tool: str, effect: str, step: int = 0, obj: str = "", error: str = "") -> dict[str, Any]:
    """One fact in turnfacts' shape. `ledger` is always '' (a coding round has no G1 ledger row)."""
    return {"id": fid, "tool": tool, "step": step, "effect": effect, "ledger": "", "object": obj[:120],
            "error": error[:160]}


def _tests(t: Any) -> list[dict[str, Any]]:
    """Test commands this session really ran in the box (structured bash steps, else the round's trail)."""
    out: list[dict[str, Any]] = []
    for i, ev in enumerate(_j(getattr(t, "steps", "") or "", [])):
        if not isinstance(ev, dict):
            continue
        if ev.get("k") == "stopped":
            out.append(_fact(f"step{i}", "stop", "stopped", i, error="stopped by her"))
            continue
        if ev.get("k") != "bash" or not _TEST_CMD.search(str(ev.get("cmd") or "")):
            continue
        rc, timed = ev.get("rc"), bool(ev.get("timed_out"))
        if timed or rc is None:
            eff, err = "ambiguous", "timed out - the result is not known"
        elif int(rc) == 0:
            eff, err = "did", ""
        else:
            eff, err = "failed", f"exit code {rc}"
        out.append(_fact(f"step{i}", "test", eff, i, str(ev.get("cmd") or ""), err))
    if out:
        return out
    trail = ((_j(getattr(t, "found", "") or "", {}) or {}).get("loop") or {}).get("trail") or []
    for i, line in enumerate(trail):
        line = str(line)
        if not line.startswith("bash: ") or not _TEST_CMD.search(line):
            continue
        m = _EXIT.search(line)
        rc = m.group(1) if m else "None"
        eff = "ambiguous" if rc == "None" else ("did" if rc == "0" else "failed")
        out.append(_fact(f"trail{i}", "test", eff, i, line[6:], "" if eff == "did" else
                         ("the result is not known" if eff == "ambiguous" else f"exit code {rc}")))
    return out


def facts(t: Any) -> list[dict[str, Any]]:
    """Everything that really happened in this session, read from the task row (never from the model's words)."""
    fs = _tests(t)
    pf = _j(getattr(t, "proof", "") or "", {}) or {}
    st = str(pf.get("state") or "")
    if st in ("checked_local", "proven_local"):
        fs.append(_fact("lab", "test", "did", obj=str(pf.get("cmd") or "lab check")))
    elif st in ("check_failed_local", "still_failing"):
        fs.append(_fact("lab", "test", "failed", obj=str(pf.get("cmd") or "lab check"), error="the lab check failed"))
    ch = _j(getattr(t, "changes", "") or "", [])
    if ch:
        fs.append(_fact("changes", "change", "did", obj=f"{len(ch)} file(s)"))
    if getattr(t, "head_sha", "") and getattr(t, "branch", ""):
        fs.append(_fact("push", "push", "did", obj=f"{t.branch}@{str(t.head_sha)[:12]}"))
    if int(getattr(t, "pr_number", 0) or 0) > 0:
        fs.append(_fact("pr", "pr", "did", obj=str(getattr(t, "pr_url", "") or f"#{t.pr_number}")))
    ci = _j(getattr(t, "ci", "") or "", {}) or {}
    cst = str(ci.get("state") or "")
    if cst == "success":
        fs.append(_fact("ci", "ci", "did", obj=str(getattr(t, "head_sha", "") or "")[:12]))
    elif cst == "failure":
        fs.append(_fact("ci", "ci", "failed", error="CI failed: " + ", ".join(str(x) for x in (ci.get("failed") or [])[:3])))
    elif cst in ("pending", "queued", "in_progress"):
        fs.append(_fact("ci", "ci", "ambiguous", error="CI is still running"))
    if str(getattr(t, "status", "")) == "cancelled":
        fs.append(_fact("stop", "stop", "stopped", error="stopped by her"))
    return fs


def claims(text: str) -> list[str]:
    """The kinds of "done" the words claim (tests / pr / push / fixed). Plans, questions and hedges are not claims."""
    found: list[str] = []
    for sent in _SENT.split(str(text or "")):
        s = sent.strip()
        if not s or _NOT_CLAIM.search(s):
            continue
        for kind, rx in _CLAIMS:
            if kind not in found and rx.search(s):
                found.append(kind)
    return found


def _latest(fs: list[dict[str, Any]], tool: str) -> dict[str, Any] | None:
    got = [f for f in fs if f["tool"] == tool]
    return got[-1] if got else None


def verdict(kind: str, fs: list[dict[str, Any]]) -> tuple[str, str]:
    """(true | failed | unknown | stopped | none, why) - G3's verdict words, from the facts only."""
    from ..agent import turnfacts as TF
    if any(f["effect"] == "stopped" for f in fs) and kind != "pr":
        return "stopped", "she stopped this run"
    if kind == "tests":
        ci, test = _latest(fs, "ci"), _latest(fs, "test")
        best = ci if ci is not None and ci["effect"] in TF.DONE_LIKE else (test or ci)
        if best is None:
            return "none", "no test command ran and CI has not reported"
        if ci is not None and ci["effect"] == "failed":
            return "failed", ci["error"]
        if best["effect"] in TF.DONE_LIKE:
            return "true", ("CI passed" if best["tool"] == "ci" else f"'{best['object'][:60]}' exited 0")
        if best["effect"] == "failed":
            return "failed", f"the last test run failed ({best['error']})"
        return "unknown", best["error"] or "the test result is not known"
    if kind in ("pr", "push"):
        f = _latest(fs, kind)
        if f is None:
            return "none", ("no pull request exists for this session" if kind == "pr" else "nothing was pushed")
        return ("true", f["object"]) if f["effect"] in TF.DONE_LIKE else ("unknown", f["error"])
    if kind == "fixed":
        if _latest(fs, "change") is None:
            return "none", "no file was changed"
        test = _latest(fs, "test")
        ci = _latest(fs, "ci")
        for f in (ci, test):
            if f is not None and f["effect"] == "failed":
                return "failed", f["error"] or "the check failed"
        return "true", "files changed and no check failed"
    return "none", ""


def judge(t: Any) -> dict[str, Any]:
    """The task card's `truth`: what the round claims, each claim's verdict from the facts, and one honest line."""
    STATS["judged"] += 1
    fs = facts(t)
    kinds = claims(" ".join(str(x or "") for x in (getattr(t, "explain", ""), getattr(t, "test_plan", ""))))
    if str(getattr(t, "status", "")) == "pr_open" and "pr" not in kinds:
        kinds.insert(0, "pr")                         # the end notice itself says "the pull request is ready"
    rows = []
    for k in kinds:
        v, why = verdict(k, fs)
        rows.append({"claim": k, "verdict": v, "why": why})
    bad = [r for r in rows if r["verdict"] != "true"]
    if bad:
        STATS["unconfirmed"] += 1
    words = {"tests": "tests pass", "pr": "the pull request is ready", "push": "it was pushed", "fixed": "it is fixed"}
    line = "" if not bad else ("Not confirmed: " + "; ".join(f"'{words.get(r['claim'], r['claim'])}' - {r['why']}"
                                                            for r in bad[:3]) + ".")
    return {"confirmed": not bad, "claims": rows, "facts": fs, "line": line}


def end_key(t: Any) -> str:
    """One key per finished round outcome (see the module text)."""
    return (f"devsahayak:{t.id}:r{int(t.rounds or 0)}.{int(t.ci_round or 0)}.{int(t.self_round or 0)}:"
            f"{t.status}:{str(t.head_sha or '')[:12]}")


def tell_once(t: Any, conv: str, send) -> bool | None:
    """turndeliver's record for this end notice: None = it was already told (nothing sent now)."""
    from ..agent import turndeliver as TD
    key = end_key(t)
    TD.record(key, str(getattr(t, "tenant_id", "") or ""), conv or "", thread=f"devsahayak:{t.id}", kind="dev",
              job_key=f"devsahayak:{t.id}", job_state=str(t.status or ""), outcome=str(t.status or ""), mark=0)
    got = TD.once(key, "push", send)
    STATS["already_told" if got is None else "told"] += 1
    return got
