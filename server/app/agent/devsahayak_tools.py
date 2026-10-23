"""Developer Sahayak tools. `dev_dekho` only reads; `dev` does the work in HER GitHub repo on a hoola/* branch + PR. Merge, deploy,
posting a review and opening a PR on a public repo only make a CARD: her tap in the app decides (the tool can never). The GitHub
token is never taken here (only in the app)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

DEV_TOOLS = [
    {"name": "dev", "description": (
        "Software developer in the owner's OWN GitHub repos (official API, her token set in the app; never ask for the token in chat). "
        "Work always goes on a hoola/<task> branch + pull request; tests run in HER CI, never on this server. "
        "action=write (new code / feature: text = what she wants), fix (bug: text = her words + error / stack trace / log pasted, or "
        "issue = issue number; Hoola finds the files, explains in Hinglish and opens a fix PR WITH a test), tests (write tests for code "
        "she names), docs (README / docstrings / API docs), explain (only explain a bug, no PR). files = paths she names (optional), repo "
        "= owner/name (default: her default repo). action=revise (task + text: change the PR by her words), fix_ci (task: CI failed -> "
        "try a fix commit), refresh (task: PR + CI state), cancel (task). action=review (repo + pr: review her / her team's PR -> a DRAFT "
        "review card; it goes to GitHub only on her tap). action=merge (task or repo + pr, method merge|squash|rebase) and action=deploy "
        "(repo, workflow, ref, inputs) ONLY prepare a card for HER tap: say 'card bheja hai', never that it is merged / deployed. "
        "action=repo_add (repo, deploy_workflow = her workflow_dispatch file, deploy_ref) | repo_remove | settings (review_post draft|"
        "direct, ask_before_pr, draft_pr, allow_workflows, merge_method, max_files, max_lines, rules, default_repo; owner only)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["write", "fix", "tests", "docs", "explain", "revise", "fix_ci", "refresh", "cancel", "review",
                                               "merge", "deploy", "repo_add", "repo_remove", "settings"]},
         "text": {"type": "string", "description": "Her exact words / the error, stack trace or log (data, pasted as is)"},
         "repo": {"type": "string"}, "issue": {"type": "integer"}, "files": {"type": "array", "items": {"type": "string"}},
         "task": {"type": "string", "description": "D-0001 or the PR number"}, "pr": {"type": "integer"},
         "method": {"type": "string", "enum": ["merge", "squash", "rebase"]}, "workflow": {"type": "string"}, "ref": {"type": "string"},
         "inputs": {"type": "object"}, "deploy_workflow": {"type": "string"}, "deploy_ref": {"type": "string"}, "notes": {"type": "string"},
         "review_post": {"type": "string", "enum": ["draft", "direct"]}, "ask_before_pr": {"type": "boolean"}, "draft_pr": {"type": "boolean"},
         "allow_workflows": {"type": "boolean"}, "merge_method": {"type": "string"}, "max_files": {"type": "integer"},
         "max_lines": {"type": "integer"}, "rules": {"type": "string"}, "default_repo": {"type": "string"}},
         "required": ["action"]}},
    {"name": "dev_dekho", "description": (
        "Read developer work (nothing changes). what=tasks (her Hoola PRs / jobs, status) | task (task: diff, explanation, CI, checks) | "
        "repos | prs (repo: open pull requests) | reviews | actions (merge / deploy cards and results) | settings | rules."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["tasks", "task", "repos", "prs", "reviews", "actions", "settings", "rules"]},
         "task": {"type": "string"}, "repo": {"type": "string"}, "status": {"type": "string"}},
         "required": ["what"]}},
]
DEV_LABELS = {"dev": "Code par kaam kar raha hoon", "dev_dekho": "Repo aur PR dekh raha hoon"}


def _s(v: Any) -> str:
    return "" if v is None else str(v)


def _owner(ctx: Ctx) -> bool:
    a = getattr(ctx, "actor", "owner") or "owner"
    return a == "owner" or a.startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..devsahayak import rules as R
    from ..devsahayak import service as S
    t, conv = ctx.tenant_id, ctx.conversation_id
    actor = getattr(ctx, "actor", "owner") or "owner"
    if actor.startswith("customer:"):
        raise ToolError("Yeh kaam graahak ke liye nahi.")
    for v in a.values():
        if isinstance(v, str) and R.looks_token(v):
            raise ToolError("GitHub token chat / tool mein kabhi nahi: sirf app ke Developer > Niyam mein. Is token ko turant badal dijiye.")
    try:
        if action in S.KINDS:
            return S.start(t, action, _s(a.get("text")), _s(a.get("repo")), int(a.get("issue") or 0),
                           [str(x) for x in (a.get("files") or []) if x][:10], conv, actor)
        if action == "revise":
            return S.revise(t, _s(a.get("task")), _s(a.get("text")), conv)
        if action == "fix_ci":
            return S.fix_ci(t, _s(a.get("task")))
        if action == "refresh":
            return S.refresh(t, _s(a.get("task")))
        if action == "cancel":
            return S.cancel(t, _s(a.get("task")))
        if action == "review":
            return S.review(t, _s(a.get("repo")), int(a.get("pr") or 0), conv)
        if action == "merge":
            v = S.merge_request(t, _s(a.get("repo")), int(a.get("pr") or 0), _s(a.get("method")), _s(a.get("task")), conv)
            v["status_note"] = "CARD ONLY: merge happens only when she taps the card. Do not say it is merged."
            return v
        if action == "deploy":
            inp = a.get("inputs") if isinstance(a.get("inputs"), dict) else {}
            v = S.deploy_request(t, _s(a.get("repo")), _s(a.get("workflow")), _s(a.get("ref")), inp, conv)
            v["status_note"] = "CARD ONLY: deploy starts only when she taps the card. Do not say it is deployed."
            return v
        if action == "repo_add":
            if not _owner(ctx):
                raise ToolError("Repo sirf owner jod sakti hain.")
            return S.add_repo(t, _s(a.get("repo")), _s(a.get("deploy_workflow")), _s(a.get("deploy_ref")), _s(a.get("notes")))
        if action == "repo_remove":
            if not _owner(ctx):
                raise ToolError("Sirf owner.")
            return S.remove_repo(t, _s(a.get("repo")))
        if action == "settings":
            if not _owner(ctx):
                raise ToolError("Niyam sirf owner badal sakti hain.")
            keys = ("review_post", "ask_before_pr", "draft_pr", "allow_workflows", "merge_method", "max_files", "max_lines", "rules", "default_repo")
            return S.save_settings(t, **{k: a[k] for k in keys if k in a})
    except (S.DevError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("action galat")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..devsahayak import rules as R
    from ..devsahayak import service as S
    t = ctx.tenant_id
    try:
        if what == "tasks":
            return {"tasks": S.tasks(t, _s(a.get("status")))}
        if what == "task":
            return S.get_task(t, _s(a.get("task")))
        if what == "repos":
            return {"repos": S.repos(t)}
        if what == "prs":
            return {"prs": S.open_prs(t, _s(a.get("repo")))}
        if what == "reviews":
            return {"reviews": S.reviews(t, _s(a.get("status")))}
        if what == "actions":
            return {"actions": S.actions(t, status=_s(a.get("status")))}
        if what == "settings":
            return S.settings(t)
        if what == "rules":
            return {"never": list(R.NEVER), "owasp_2025": R.OWASP, "limits": R.LIMITS}
    except (S.DevError, ValueError) as ex:
        raise ToolError(str(ex))
    raise ToolError("what galat")


async def dev(ctx: Ctx, action, **a: Any):
    return await asyncio.to_thread(_act, ctx, str(action), a)


async def dev_dekho(ctx: Ctx, what, **a: Any):
    return await asyncio.to_thread(_read, ctx, str(what), a)


DEV_HANDLERS = {"dev": dev, "dev_dekho": dev_dekho}

# the brief's MOD_* names (same objects)
DEVSAHAYAK_TOOLS, DEVSAHAYAK_LABELS, DEVSAHAYAK_HANDLERS = DEV_TOOLS, DEV_LABELS, DEV_HANDLERS
