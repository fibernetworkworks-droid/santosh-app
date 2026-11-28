"""A GitHub Actions access guard for her policies: on every pull request that touches her policy folder it reads each JSON policy
file (AWS IAM policy documents and trust policies, Google Cloud IAM policies) and fails the check when one allows every action on
every resource, lets anyone in with no condition, passes any role, allows with NotAction, grants a public member or a basic owner
role, or trusts GitHub's OIDC with no subject condition - the list written to the run's summary. It needs no cloud access and
reads only the files in the pull request's checkout; nothing is applied and nothing is pushed."""
from __future__ import annotations

import re
from typing import Any

from .common import ClInputError
from .iam import ESCALATE


class CiError(ClInputError):
    pass


GUARD = r'''import glob, json, os, sys
ESCALATE = @ESCALATE@
ROOT = @ROOT@
fail, rows = [], []
def L(v):
    return v if isinstance(v, list) else [] if v is None else [v]
def docs(d):
    if isinstance(d, list):
        for x in d:
            yield from docs(x)
    elif isinstance(d, dict):
        if "Statement" in d:
            yield d
        for k in ("PolicyDocument", "AssumeRolePolicyDocument", "Document"):
            if isinstance(d.get(k), dict):
                yield d[k]
def check(path, d):
    if isinstance(d, dict) and "bindings" in d:
        for b in d["bindings"]:
            m = b.get("members") or []
            if any(x in ("allUsers", "allAuthenticatedUsers") for x in m):
                fail.append(f"{path}: {b.get('role')} is granted to everyone")
            if b.get("role") == "roles/owner":
                fail.append(f"{path}: roles/owner is granted ({', '.join(m[:3])})")
        return
    for doc in docs(d):
        for i, st in enumerate(L(doc.get("Statement"))):
            if not isinstance(st, dict) or st.get("Effect", "Allow") != "Allow":
                continue
            w = f"{path} {st.get('Sid') or '#' + str(i + 1)}"
            a = [str(x).lower() for x in L(st.get("Action"))]
            r = [str(x) for x in L(st.get("Resource"))]
            p, c = st.get("Principal"), st.get("Condition") or {}
            if any(x in ("*", "*:*") for x in a) and "*" in r:
                fail.append(f"{w}: every action on every resource")
            if "*" in r and "iam:passrole" in a:
                fail.append(f"{w}: iam:PassRole on every role")
            esc = [x for x in a if x in ESCALATE and x != "sts:assumerole"]
            if "*" in r and esc:
                fail.append(f"{w}: {', '.join(esc[:3])} on every resource")
            if st.get("NotAction"):
                fail.append(f"{w}: Allow with NotAction")
            pv = p if isinstance(p, str) else (p or {}).get("AWS") if isinstance(p, dict) else None
            if (p == "*" or "*" in [str(x) for x in L(pv)]) and not c:
                fail.append(f"{w}: open to anyone with no condition")
            fed = [str(x) for x in L((p or {}).get("Federated"))] if isinstance(p, dict) else []
            if any("token.actions.githubusercontent.com" in f for f in fed):
                keys = " ".join(k for v in c.values() if isinstance(v, dict) for k in v)
                if ":sub" not in keys:
                    fail.append(f"{w}: GitHub OIDC trust with no subject condition")
files = sorted(set(glob.glob(os.path.join(ROOT, "**", "*.json"), recursive=True)))
for f in files:
    try:
        d = json.load(open(f))
    except ValueError:
        continue
    before = len(fail)
    check(os.path.relpath(f), d)
    rows.append(f"| {os.path.relpath(f)} | {'FAIL' if len(fail) > before else 'ok'} |")
with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a") as s:
    s.write(f"## Access guard\n\n{len(files)} policy file(s), {len(fail)} problem(s).\n\n" + ("| file | |\n|---|---|\n" + "\n".join(rows) + "\n" if rows else ""))
for f in fail:
    print("::error::" + f)
print(f"{len(files)} file(s) checked, {len(fail)} problem(s)")
sys.exit(1 if fail else 0)
'''


def workflow(policy_dir: str = "policies", runner: str = "ubuntu-24.04") -> dict[str, Any]:
    d = str(policy_dir or "policies").strip()
    if not re.fullmatch(r"[\w./\-]{1,160}", d) or ".." in d or d.startswith("/"):
        raise CiError("Policy folder: a path inside the repository, such as iam/policies.")
    d = d.rstrip("/")
    if not re.fullmatch(r"[\w.\-]{1,40}", str(runner or "")):
        raise CiError("Runner: a runner label such as ubuntu-24.04.")
    guard = GUARD.replace("@ESCALATE@", repr(tuple(ESCALATE))).replace("@ROOT@", repr(d))
    body = "\n".join("          " + ln if ln else "" for ln in guard.splitlines())
    yml = f"""name: Access guard
# Added by you from the Cloud Engineer desk. It reads the policy files in this pull request and fails the check
# when one lets too much in. It needs no cloud access and changes nothing.
on:
  pull_request:
    paths:
      - "{d}/**"
permissions:
  contents: read
jobs:
  guard:
    runs-on: {runner}
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - name: Check the policies
        shell: python3 {{0}}
        run: |
{body}
"""
    return {"file": ".github/workflows/access-guard.yml", "yaml": yml, "policy_dir": d, "runner": runner,
            "steps": ["Add the file to your repository's .github/workflows folder in a pull request.",
                      f"Keep your policy JSON files under {d}/ (AWS policy documents, trust policies, or Google Cloud IAM policies).",
                      "In the repository settings, make 'Access guard' a required check so a failing pull request cannot be merged."],
            "note": "The guard reads only the files in the pull request; it needs no keys and no cloud role."}
