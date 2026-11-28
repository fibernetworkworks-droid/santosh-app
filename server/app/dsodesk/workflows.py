"""GitHub Actions workflows read for the ways a pipeline is attacked: third-party actions not pinned to a full commit SHA (a moved tag
runs someone else's code with the job's secrets), no top-level permissions or write-all, pull_request_target / workflow_run that
check out and run the pull request's own code with secrets in reach, event text (issue titles, PR bodies, branch names, commit
messages) put straight into a shell, secrets set for the whole workflow, self-hosted runners on public pull requests, curl | bash,
the checkout token kept on disk, and jobs with no time limit. Paste one workflow or several (`## path` before each). Read only."""
from __future__ import annotations

import re
from typing import Any

import yaml

from .common import DsoInputError, finder, finish


class WorkflowError(DsoInputError):
    pass


SHA = re.compile(r"^[0-9a-f]{40}$")
TRUSTED = ("actions/", "github/")
# event text an outsider controls; put into a run: line it becomes shell code
UNTRUSTED = re.compile(r"\$\{\{\s*(github\.event\.(issue\.(title|body)|pull_request\.(title|body|head\.ref|head\.label|head\.repo\.default_branch)|"
                       r"comment\.body|review\.body|review_comment\.body|pages\.[^}]*\.page_name|commits\.[^}]*\.(message|author\.(email|name))|"
                       r"head_commit\.(message|author\.(email|name))|workflow_run\.(head_branch|head_commit\.message|display_title)|discussion\.(title|body))"
                       r"|github\.head_ref)\s*\}\}")
CURL_SH = re.compile(r"\b(curl|wget)\b[^\n|]*\|\s*(sudo\s+)?(ba|z)?sh\b|\biex\s*\(\s*(irm|iwr|new-object)", re.I)
RISKY_TRIGGERS = ("pull_request_target", "workflow_run")


# line rules shared with the CI guard: (id, severity, pattern, what, fix)
LINE_RULES: list[tuple[str, str, str, str, str]] = [
    ("unpinned-action", "warn", r"^\s*-?\s*uses:\s*(?!\./)(?!docker://)([\w.-]+/[\w./-]+)@(?![0-9a-f]{40}\b)(\S+)", "A third-party action not pinned to a full commit SHA",
     "Pin it: uses: owner/action@<40-character SHA> # vX.Y"),
    ("script-injection", "bad", UNTRUSTED.pattern, "Event text an outsider controls is put into the workflow", "Pass it through env: and use \"$VAR\" in the script."),
    ("write-all", "bad", r"^\s*permissions:\s*write-all\s*$", "permissions: write-all", "Grant only what each job needs, e.g. contents: read."),
    ("curl-sh", "warn", CURL_SH.pattern, "A script downloaded and run in one step", "Download, check its checksum, then run it - or use a pinned action."),
]


def _docs(text: str) -> list[tuple[str, str]]:
    t = str(text or "").strip()
    if not t:
        raise WorkflowError("Paste a workflow from .github/workflows (several: put '## path' before each).")
    if re.search(r"(?m)^##\s+\S", t):
        parts = re.split(r"(?m)^##\s+(\S+).*$", t)
        out = [(parts[i].strip(), parts[i + 1][1:] if parts[i + 1].startswith("\n") else parts[i + 1]) for i in range(1, len(parts) - 1, 2) if parts[i + 1].strip()]
        return out
    return [("workflow.yml", t)]


def _on(d: dict[str, Any]) -> dict[str, Any]:
    on = d.get("on", d.get(True))
    if isinstance(on, str):
        return {on: {}}
    if isinstance(on, list):
        return {x: {} for x in on}
    return on if isinstance(on, dict) else {}


def analyse(text: str, trusted_owners: str = "") -> dict[str, Any]:
    owners = tuple(TRUSTED) + tuple(o.strip().rstrip("/") + "/" for o in str(trusted_owners or "").split(",") if o.strip())
    issues, add = finder()
    files, actions = [], {}
    for path, src in _docs(text):
        try:
            d = yaml.safe_load(src)
        except yaml.YAMLError as e:
            raise WorkflowError(f"{path}: the YAML could not be read - {str(e).splitlines()[0][:120]}")
        if not isinstance(d, dict) or "jobs" not in d:
            raise WorkflowError(f"{path}: not a GitHub Actions workflow (no jobs).")
        on = _on(d)
        trig = sorted(map(str, on))
        risky = [t for t in trig if t in RISKY_TRIGGERS]
        fl: list[str] = []
        lines = src.split("\n")
        # line rules with line numbers
        for n, ln in enumerate(lines, 1):
            for rid, sev, pat, what, fix in LINE_RULES:
                m = re.search(pat, ln, re.I if rid == "curl-sh" else 0)
                if not m:
                    continue
                if rid == "unpinned-action":
                    act = m.group(1)
                    actions.setdefault(act + "@" + m.group(2), {"action": act, "ref": m.group(2), "files": set()})["files"].add(path)
                    if act.lower().startswith(owners):
                        continue
                fl.append({"unpinned-action": "unpinned action", "script-injection": "script injection", "curl-sh": "curl | bash"}.get(rid, rid))
                add(sev, what, f"{path}:{n}: {ln.strip()[:140]}", fix, f"{path}:{n}")
        for n, ln in enumerate(lines, 1):
            m = re.search(r"^\s*-?\s*uses:\s*(?!\./)([\w.-]+/[\w./-]+)@([0-9a-f]{40})\b", ln)
            if m:
                actions.setdefault(m.group(1) + "@" + m.group(2)[:12], {"action": m.group(1), "ref": m.group(2)[:12] + "…", "files": set(), "pinned": True})["files"].add(path)
        perms = d.get("permissions")
        jobs = d.get("jobs") or {}
        if perms is None and not all(isinstance(j, dict) and "permissions" in j for j in jobs.values()):
            fl.append("no permissions")
            add("warn", "No permissions set", f"{path} sets no permissions - the token gets the repository's default, often read and write to everything.",
                "Add at the top: permissions: contents: read - then grant more per job.", path)
        if isinstance(perms, dict) and any(v == "write" for v in perms.values()) and len([v for v in perms.values() if v == "write"]) >= 4:
            add("warn", "Wide permissions", f"{path} grants write to {', '.join(k for k, v in perms.items() if v == 'write')} for every job.", "Move write rights to the jobs that need them.", path)
        env_all = d.get("env") or {}
        sec_env = [k for k, v in env_all.items() if isinstance(v, str) and "secrets." in v]
        if sec_env:
            fl.append("secrets for every job")
            add("warn", "Secrets for every job", f"{path} puts {', '.join(sec_env[:4])} in the workflow's env - every step of every job can read them.", "Set secrets only on the step that uses them.", path)
        for jn, j in jobs.items():
            if not isinstance(j, dict):
                continue
            steps = j.get("steps") or []
            ro = str(j.get("runs-on", ""))
            if "self-hosted" in ro and any(t in trig for t in ("pull_request", "pull_request_target")):
                fl.append("self-hosted on PRs")
                add("bad", "Self-hosted runner on pull requests", f"{path} job {jn} runs pull requests on a self-hosted runner - a fork's code runs on your machine.",
                    "Use GitHub-hosted runners for pull requests, or ephemeral, isolated runners.", f"{path}:{jn}")
            if "timeout-minutes" not in j and "uses" not in j:
                fl.append("no timeout")
            for st in steps if isinstance(steps, list) else []:
                if not isinstance(st, dict):
                    continue
                u = str(st.get("uses", ""))
                w = st.get("with") or {}
                if u.startswith("actions/checkout"):
                    ref = str(w.get("ref", ""))
                    if risky and re.search(r"github\.event\.(pull_request\.head\.(sha|ref)|workflow_run\.head_(sha|branch))|github\.head_ref|refs/pull/", ref):
                        fl.append("runs PR code with secrets")
                        add("bad", "Runs the pull request's code with secrets", f"{path} job {jn}: {'/'.join(risky)} checks out the pull request's own code ({ref}) - it runs with the base repository's secrets and write token.",
                            "Use pull_request for building PR code; keep pull_request_target for labelling / commenting without checking out the PR.", f"{path}:{jn}")
                    if str(w.get("persist-credentials", "true")).lower() != "false":
                        fl.append("token kept on disk")
        if "no timeout" in fl:
            add("info", "No time limit", f"{path} has jobs with no timeout-minutes - a stuck job runs (and bills) for 6 hours.", "Set timeout-minutes on each job.", path)
        if "token kept on disk" in fl:
            add("info", "Checkout token kept", f"{path} keeps the checkout token in .git/config for later steps.", "Set persist-credentials: false unless a later step pushes.", path)
        if risky and "runs PR code with secrets" not in fl:
            add("info", "Privileged trigger", f"{path} uses {', '.join(risky)} - it runs with secrets for pull requests from forks.", "Keep it from checking out or running the pull request's code.", path)
        files.append({"path": path, "name": d.get("name") or path, "triggers": trig, "jobs": len(jobs), "flags": sorted(set(fl)),
                      "permissions": perms if isinstance(perms, (str, dict)) else None})
    acts = sorted(({"action": v["action"], "ref": v["ref"], "pinned": bool(v.get("pinned")), "trusted": v["action"].lower().startswith(owners), "files": sorted(v["files"])}
                   for v in actions.values()), key=lambda a: (a["pinned"], a["trusted"], a["action"]))
    un = [a for a in acts if not a["pinned"] and not a["trusted"]]
    res = {"files": files, "actions": acts, "unpinned": len(un), "pinned": sum(1 for a in acts if a["pinned"]),
           "verdict": f"{len(files)} workflow(s), {len(acts)} action reference(s), {len(un)} third-party not pinned"}
    res["note"] = ("Read from the YAML you pasted. Actions owned by GitHub (actions/, github/)" + (" and your trusted owners" if trusted_owners else "")
                   + " are not asked to be pinned; pinning them too is stricter still.")
    return finish(res, issues)
