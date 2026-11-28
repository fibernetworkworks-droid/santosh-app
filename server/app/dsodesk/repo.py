"""A GitHub repository's guard rails read from its own settings: paste `gh api repos/OWNER/REPO` (secret scanning, push protection,
Dependabot security updates, visibility, forking) and `gh api repos/OWNER/REPO/branches/BRANCH/protection` (reviews required, stale
reviews dismissed, code owners, the last pusher not approving their own push, status checks, admins included, signed commits,
force pushes and deletion, linear history, conversations resolved). Each against her own minimum; a branch GitHub says is not
protected is said plainly. Read only - nothing is changed."""
from __future__ import annotations

import json
import re
from typing import Any

from .common import DsoInputError, finder, finish


class RepoError(DsoInputError):
    pass


def _en(v: Any) -> bool:
    if isinstance(v, dict):
        return bool(v.get("enabled") if "enabled" in v else v.get("status") == "enabled")
    return bool(v)


def analyse(text: str, min_reviews: int = 1, need_checks: str = "") -> dict[str, Any]:
    t = str(text or "").strip()
    if not t:
        raise RepoError("Paste `gh api repos/OWNER/REPO` and `gh api repos/OWNER/REPO/branches/main/protection` output (put '## name' before each).")
    chunks = [c for c in re.split(r"(?m)^##\s+.*$", t) if c.strip()]
    repo, prot, branch_msg = None, None, ""
    for c in chunks:
        try:
            d = json.loads(c)
        except ValueError as e:
            raise RepoError(f"The JSON could not be read: {e}")
        if not isinstance(d, dict):
            continue
        if "full_name" in d or "security_and_analysis" in d:
            repo = d
        elif any(k in d for k in ("required_pull_request_reviews", "required_status_checks", "enforce_admins", "allow_force_pushes")):
            prot = d
        elif str(d.get("message", "")).lower().startswith("branch not protected"):
            branch_msg = "not protected"
        elif "message" in d:
            branch_msg = str(d["message"])[:120]
    if repo is None and prot is None and not branch_msg:
        raise RepoError("Neither a repository nor a branch protection answer was found.")
    issues, add = finder()
    checks: list[dict[str, Any]] = []

    def ck(area: str, name: str, ok: bool | None, say: str, sev: str = "warn", fix: str = "") -> None:
        checks.append({"area": area, "name": name, "ok": ok, "say": say})
        if ok is False:
            add(sev, name, say, fix)
    info: dict[str, Any] = {}
    if repo:
        sa = repo.get("security_and_analysis") or {}
        info = {"repo": repo.get("full_name", ""), "visibility": repo.get("visibility") or ("private" if repo.get("private") else "public"),
                "default_branch": repo.get("default_branch", ""), "archived": bool(repo.get("archived"))}
        pub = info["visibility"] == "public"
        ck("Repository", "Secret scanning", _en(sa.get("secret_scanning")) if sa else None,
           "Secret scanning is " + ("on." if _en(sa.get("secret_scanning")) else "off - keys pushed to the repository are not caught."), "warn",
           "Settings > Code security: turn on secret scanning.")
        ck("Repository", "Push protection", _en(sa.get("secret_scanning_push_protection")) if sa else None,
           "Push protection is " + ("on." if _en(sa.get("secret_scanning_push_protection")) else "off - a push with a key in it is not blocked."), "warn",
           "Turn on push protection.")
        ck("Repository", "Dependabot security updates", _en(sa.get("dependabot_security_updates")) if sa else None,
           "Dependabot security updates are " + ("on." if _en(sa.get("dependabot_security_updates")) else "off - vulnerable dependencies get no pull request."), "info",
           "Turn on Dependabot security updates.")
        if not sa:
            add("info", "Security settings not shown", "The answer has no security_and_analysis - the token may not have admin rights on the repository.",
                "Run it with a token that can read the repository's settings.")
        if pub and repo.get("allow_forking") is not False:
            checks.append({"area": "Repository", "name": "Forks", "ok": None, "say": "Public and forkable - pull requests from forks run your pull_request workflows."})
    if branch_msg == "not protected":
        add("bad", "Branch not protected", "GitHub says the branch is not protected - anyone with write access can push to it directly, force-push or delete it.",
            "Settings > Branches (or Rules): protect the default branch.")
        checks.append({"area": "Branch", "name": "Protected", "ok": False, "say": "The branch is not protected."})
    elif branch_msg:
        add("info", "Branch protection unreadable", f"GitHub answered: {branch_msg}", "Use a token with admin rights, or check rulesets (gh api repos/O/R/rulesets).")
    if prot:
        rv = prot.get("required_pull_request_reviews")
        n = int((rv or {}).get("required_approving_review_count") or 0)
        ck("Branch", "Reviews", bool(rv) and n >= min_reviews, f"{n} approving review(s) required" + ("." if rv and n >= min_reviews else f" - your minimum is {min_reviews}."),
           "bad" if not rv else "warn", f"Require at least {min_reviews} approving review(s).")
        if rv:
            ck("Branch", "Stale reviews dismissed", bool(rv.get("dismiss_stale_reviews")), "New commits " + ("dismiss" if rv.get("dismiss_stale_reviews") else "do not dismiss") + " earlier approvals.",
               "warn", "Turn on: dismiss stale approvals when new commits are pushed.")
            ck("Branch", "Code owners", bool(rv.get("require_code_owner_reviews")), "Code owners' review is " + ("required." if rv.get("require_code_owner_reviews") else "not required."), "info",
               "Add a CODEOWNERS file and require code owner review.")
            ck("Branch", "Last push approved by someone else", bool(rv.get("require_last_push_approval")),
               "The last pusher " + ("cannot approve their own push." if rv.get("require_last_push_approval") else "can approve a push of their own."), "info", "Turn on: require approval of the most recent push.")
        sc = prot.get("required_status_checks")
        ctx = sorted(set((sc or {}).get("contexts") or []) | {c.get("context") for c in (sc or {}).get("checks") or [] if c.get("context")})
        ck("Branch", "Status checks", bool(ctx), (f"{len(ctx)} check(s) must pass: {', '.join(ctx[:6])}." if ctx else "No checks must pass before merging."), "warn",
           "Require your CI checks (tests, the security gate) to pass.")
        want = [x.strip() for x in str(need_checks or "").split(",") if x.strip()]
        miss = [w for w in want if w not in ctx]
        if miss:
            add("warn", "Required check missing", f"Not required on the branch: {', '.join(miss)}.", "Add them to the required status checks.")
        if sc:
            ck("Branch", "Up to date before merging", bool(sc.get("strict")), "Branches " + ("must" if sc.get("strict") else "need not") + " be up to date before merging.", "info",
               "Turn on: require branches to be up to date.")
        ck("Branch", "Admins included", _en(prot.get("enforce_admins")), "Admins " + ("follow" if _en(prot.get("enforce_admins")) else "can skip") + " these rules.", "warn",
           "Turn on: do not allow bypassing the settings.")
        ck("Branch", "No force pushes", not _en(prot.get("allow_force_pushes")), "Force pushes are " + ("allowed - history can be rewritten." if _en(prot.get("allow_force_pushes")) else "blocked."),
           "bad", "Block force pushes.")
        ck("Branch", "No deletion", not _en(prot.get("allow_deletions")), "Deleting the branch is " + ("allowed." if _en(prot.get("allow_deletions")) else "blocked."), "bad", "Block deletion.")
        ck("Branch", "Signed commits", _en(prot.get("required_signatures")), "Signed commits are " + ("required." if _en(prot.get("required_signatures")) else "not required."), "info",
           "Require signed commits.")
        ck("Branch", "Conversations resolved", _en(prot.get("required_conversation_resolution")), "Review comments " + ("must" if _en(prot.get("required_conversation_resolution")) else "need not") + " be resolved before merging.", "info",
           "Turn on: require conversation resolution.")
        ck("Branch", "Linear history", _en(prot.get("required_linear_history")), "Linear history is " + ("required." if _en(prot.get("required_linear_history")) else "not required."), "info", "")
    ok = sum(1 for c in checks if c["ok"] is True)
    tot = sum(1 for c in checks if c["ok"] is not None)
    res = {**info, "checks": checks, "passed": ok, "total": tot, "protected": bool(prot) if not branch_msg else False, "min_reviews": min_reviews,
           "verdict": (f"{info.get('repo') + ': ' if info.get('repo') else ''}{ok} of {tot} guard rails in place") + ("; the branch is not protected" if branch_msg == "not protected" else "")}
    res["note"] = "Read from the API answers you pasted. Rulesets (gh api repos/O/R/rulesets) can add rules the classic branch protection does not show."
    return finish(res, issues)
