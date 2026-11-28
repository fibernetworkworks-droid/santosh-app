"""v0.999 A BIG JOB AS LINKED GITHUB ISSUES, from ECC's epic commands (affaan-m/ECC epic-decompose / epic-publish /
epic-sync, MIT; the idea is theirs, the code is Hoola's own and uses her own GitHub token through gh.py).

1. /epic <the big job, or #123 for an issue that already describes it>: the coder reads the repo and breaks the job into
   small tasks (each one change a reviewer can read in one sitting, with what "done" means and what it waits for), and
   hands the breakdown to Hoola with the `epic` tool. Nothing is created on GitHub: she sees the list as a card.
2. Her tap (Create the issues) = her message /epic-publish: Hoola, in code, creates one issue per task, then the parent
   issue with a checklist that links every task issue (or adds the checklist to the #issue she named). Each task issue
   says which issues it waits for. Once created, the numbers are kept on the session.
3. /epic-sync: Hoola reads every task issue's state from GitHub and ticks the parent's checklist to match (closed =
   ticked), and says what is done, what is open and what is unblocked now.
Creating issues is outward-facing, so it happens only on her own command - the coder can never publish. Switch:
`dev_epic` (default on).
"""
from __future__ import annotations

import re
from typing import Any

CREDIT = "(adapted from ECC's epic commands)"
MAX_TASKS = 20

TOOL = {
    "name": "epic",
    "description": ("Hand Hoola the breakdown of a big job into small GitHub-issue-sized tasks (ONLY when she typed "
                    "/epic). Each task: a short title, a body with what to change and how to know it is done, and the "
                    "numbers (1-based) of the tasks it waits for. Hoola shows her the list; she decides whether to create "
                    "the issues. This creates nothing on GitHub."),
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "The big job in a few words (the parent issue's title)."},
            "summary": {"type": "string", "description": "Two or three sentences: the goal and how the tasks get there."},
            "tasks": {"type": "array", "maxItems": MAX_TASKS, "items": {
                "type": "object",
                "properties": {"title": {"type": "string"},
                               "body": {"type": "string", "description": "What to change, which files, and the check that says it is done."},
                               "depends_on": {"type": "array", "items": {"type": "integer"},
                                              "description": "Numbers of earlier tasks in this list it waits for."}},
                "required": ["title", "body"]}},
        },
        "required": ["title", "tasks"],
    },
}


def on() -> bool:
    try:
        from ..config import get_settings
        return bool(getattr(get_settings(), "dev_epic", True))
    except Exception:  # noqa: BLE001
        return True


def parse_cmd(words: str) -> tuple[str, str]:
    """('plan' | 'publish' | 'sync' | '', the rest of her words)."""
    m = re.match(r"^\s*/epic(?:-(decompose|publish|sync))?\b\s*(.*)$", words or "", re.I | re.S)
    if not m:
        return "", ""
    kind = (m.group(1) or "decompose").lower()
    return {"decompose": "plan", "publish": "publish", "sync": "sync"}[kind], m.group(2).strip()


def plan_text(rest: str, issue: str) -> str:
    return ("<her_command>/epic</her_command>\nShe wants this big job broken into small, linked GitHub issues " + CREDIT
            + ". The job:\n<her_epic>" + (rest or "(see the issue below)")[:3000] + "</her_epic>\n"
            + (f"<issue>\n{issue[:6000]}\n</issue>\n" if issue else "")
            + "Read the repo enough to plan for real (the files, how it is built and tested). Then call the epic tool "
            "ONCE with the breakdown: 2 to " + str(MAX_TASKS) + " tasks, in the order to do them, each small enough for "
            "one pull request a reviewer can read in one sitting; each body names the files, what changes, and the check "
            "that proves it is done; depends_on lists the earlier tasks it truly waits for. Change NO file. In done, say in "
            "one line how many tasks and that she can tap Create the issues (or type /epic-publish) to put them on GitHub.")


def clean(inp: dict[str, Any]) -> dict[str, Any]:
    tasks = []
    for i, x in enumerate((inp.get("tasks") or [])[:MAX_TASKS]):
        if not isinstance(x, dict) or not str(x.get("title") or "").strip():
            continue
        dep = sorted({int(d) for d in (x.get("depends_on") or []) if str(d).lstrip("-").isdigit() and 0 < int(d) <= i})
        tasks.append({"n": len(tasks) + 1, "title": str(x["title"]).strip()[:120], "body": str(x.get("body") or "")[:4000],
                      "depends_on": dep})
    return {"title": str(inp.get("title") or "").strip()[:120] or "Epic", "summary": str(inp.get("summary") or "")[:2000],
            "tasks": tasks}


def propose(ses: Any, inp: dict[str, Any], parent: int = 0) -> tuple[str, dict[str, Any]]:
    """The coder's breakdown: kept on the session (replacing an unpublished one), shown to her as a card."""
    plan = clean(inp)
    if len(plan["tasks"]) < 2:
        return "Not kept: give at least 2 tasks, each with a title and a body.", {}
    old = (ses.meta.get("epic") or {})
    if old.get("issues"):
        return ("Not kept: this session already published an epic to GitHub (#" + str(old.get("parent")) + "). "
                "Use /epic-sync to follow it."), {}
    plan.update({"parent": int(parent or 0), "issues": {}, "published": False})
    ses.meta["epic"] = plan
    ses.save_meta()
    ev = {"k": "epic", "title": plan["title"], "summary": plan["summary"], "tasks": plan["tasks"], "published": False}
    return (f"Kept the breakdown: {len(plan['tasks'])} tasks. Nothing is on GitHub yet - she decides with Create the issues "
            "(/epic-publish)."), ev


def _body(task: dict[str, Any], nums: dict[int, int], parent: int) -> str:
    waits = [f"#{nums[d]}" for d in task["depends_on"] if d in nums]
    return (task["body"].strip() + "\n\n"
            + (f"Waits for: {', '.join(waits)}\n" if waits else "")
            + (f"Part of #{parent}\n" if parent else "")
            + "\n_Planned with Hoola Code._")


def checklist(plan: dict[str, Any], done: set[int] | None = None) -> str:
    done = done or set()
    rows = []
    for t in plan["tasks"]:
        num = plan["issues"].get(str(t["n"]))
        tick = "x" if num and num in done else " "
        waits = [f"#{plan['issues'][str(d)]}" for d in t["depends_on"] if str(d) in plan["issues"]]
        rows.append(f"- [{tick}] #{num} {t['title']}" + (f" (waits for {', '.join(waits)})" if waits else "") if num
                    else f"- [ ] {t['title']}")
    return "<!-- hoola-epic -->\n## Tasks\n" + "\n".join(rows) + "\n<!-- /hoola-epic -->"


def _merge_body(old: str, block: str) -> str:
    if "<!-- hoola-epic -->" in (old or ""):
        return re.sub(r"<!-- hoola-epic -->.*?<!-- /hoola-epic -->", lambda _m: block, old, flags=re.S)
    return ((old or "").rstrip() + "\n\n" + block).strip()


def publish(g: Any, repo: str, ses: Any) -> tuple[str, dict[str, Any]]:
    """Her /epic-publish: the task issues, then the parent with the checklist. Safe to run again after a failure:
    an issue already created is never created twice."""
    plan = ses.meta.get("epic") or {}
    if not plan.get("tasks"):
        return "There is no breakdown to publish. Type /epic <the big job> first.", {}
    issues: dict[str, int] = plan.setdefault("issues", {})
    made, failed = 0, ""
    try:
        for t in plan["tasks"]:
            if str(t["n"]) in issues:
                continue
            nums = {int(k): v for k, v in issues.items()}
            r = g.req("POST", f"/repos/{repo}/issues", body={"title": t["title"], "body": _body(t, nums, plan.get("parent") or 0)})
            issues[str(t["n"])] = int(r.get("number") or 0)
            made += 1
            ses.save_meta()                                 # each number kept at once: a failure never duplicates
        block = checklist(plan)
        if plan.get("parent"):
            cur = g.req("GET", f"/repos/{repo}/issues/{int(plan['parent'])}")
            g.req("PATCH", f"/repos/{repo}/issues/{int(plan['parent'])}", body={"body": _merge_body(cur.get("body") or "", block)})
        else:
            r = g.req("POST", f"/repos/{repo}/issues", body={"title": plan["title"], "body": (plan.get("summary") or "").strip()
                                                              + "\n\n" + block + "\n\n_Planned with Hoola Code._"})
            plan["parent"] = int(r.get("number") or 0)
        plan["published"] = True
    except Exception as e:  # noqa: BLE001 - say what happened; what was created is kept
        failed = f"{e.__class__.__name__}: {str(e)[:300]}"
    ses.meta["epic"] = plan
    ses.save_meta()
    ev = {"k": "epic", "title": plan["title"], "summary": plan.get("summary", ""), "tasks": plan["tasks"],
          "issues": issues, "parent": plan.get("parent") or 0, "published": bool(plan.get("published")), "repo": repo}
    if failed:
        return (f"Created {made} issue(s), then GitHub refused: {failed}. What was created is kept - /epic-publish again "
                "finishes the rest without making any twice."), ev
    return (f"Created {made} task issue(s) and the parent #{plan['parent']} with its checklist on {repo}."), ev


def sync(g: Any, repo: str, ses: Any) -> tuple[str, dict[str, Any]]:
    plan = ses.meta.get("epic") or {}
    if not plan.get("issues") or not plan.get("parent"):
        return "This session has no published epic. /epic, then Create the issues, first.", {}
    states: dict[int, str] = {}
    for num in plan["issues"].values():
        try:
            states[int(num)] = str((g.req("GET", f"/repos/{repo}/issues/{int(num)}") or {}).get("state") or "open")
        except Exception:  # noqa: BLE001
            states[int(num)] = "unknown"
    done = {n for n, s in states.items() if s == "closed"}
    try:
        cur = g.req("GET", f"/repos/{repo}/issues/{int(plan['parent'])}")
        g.req("PATCH", f"/repos/{repo}/issues/{int(plan['parent'])}", body={"body": _merge_body(cur.get("body") or "", checklist(plan, done))})
        wrote = True
    except Exception:  # noqa: BLE001
        wrote = False
    ready = []
    for t in plan["tasks"]:
        num = plan["issues"].get(str(t["n"]))
        if num and num not in done and all(plan["issues"].get(str(d)) in done for d in t["depends_on"]):
            ready.append(f"#{num} {t['title']}")
    plan["states"] = {str(k): v for k, v in states.items()}
    ses.meta["epic"] = plan
    ses.save_meta()
    ev = {"k": "epic", "title": plan["title"], "summary": plan.get("summary", ""), "tasks": plan["tasks"],
          "issues": plan["issues"], "parent": plan["parent"], "published": True, "states": plan["states"], "repo": repo}
    return (f"#{plan['parent']}: {len(done)} of {len(states)} tasks closed. "
            + ("Ready to start now: " + "; ".join(ready[:6]) + ". " if ready else "")
            + ("The parent's checklist is updated." if wrote else "The parent's checklist could not be updated.")), ev
