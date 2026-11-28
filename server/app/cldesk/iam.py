"""Cloud access policies read for the ways they let too much in: AWS IAM policies (identity, resource and role trust policies -
one document, a list, a name-to-document map, or `aws iam get-account-authorization-details`), Google Cloud IAM policies
(`gcloud ... get-iam-policy --format=json`) and Azure role assignments (`az role assignment list`). Full admin, every action of a
service, Allow with NotAction or NotResource, write actions on every resource, the actions that let someone give themselves more
access, PassRole to any role, a public principal with no condition, a GitHub OIDC trust with no subject condition, allUsers,
primitive owner / editor roles, and Owner at subscription scope. Read only - it changes nothing."""
from __future__ import annotations

import json
import re
from urllib.parse import unquote
from typing import Any

from .common import ClInputError, finder, finish


class IamError(ClInputError):
    pass


ESCALATE = ("iam:createpolicyversion", "iam:setdefaultpolicyversion", "iam:attachuserpolicy", "iam:attachrolepolicy", "iam:attachgrouppolicy",
            "iam:putuserpolicy", "iam:putrolepolicy", "iam:putgrouppolicy", "iam:createaccesskey", "iam:createloginprofile", "iam:updateloginprofile",
            "iam:updateassumerolepolicy", "iam:addusertogroup", "iam:createuser", "iam:createrole", "lambda:updatefunctioncode", "sts:assumerole")
SENSITIVE = ("iam", "sts", "kms", "organizations", "secretsmanager", "account")
READ = re.compile(r"^[a-z0-9-]+:(get|list|describe|view|read|search|lookup|batchget|head|select|scan|query)", re.I)


def _l(v: Any) -> list:
    return v if isinstance(v, list) else [] if v is None else [v]


def _docs(data: Any, name: str = "policy") -> list[tuple[str, dict[str, Any]]]:
    """Every AWS policy document in what she pasted, with a name for it."""
    out: list[tuple[str, dict[str, Any]]] = []
    if isinstance(data, list):
        for i, d in enumerate(data):
            out += _docs(d, f"{name}[{i + 1}]" if not (isinstance(d, dict) and (d.get("PolicyName") or d.get("RoleName"))) else name)
        return out
    if not isinstance(data, dict):
        return out
    if "Statement" in data:
        return [(name, data)]
    for k in ("PolicyDocument", "AssumeRolePolicyDocument", "Document"):
        if isinstance(data.get(k), (dict, str)):
            d = data[k]
            if isinstance(d, str):
                try:
                    d = json.loads(unquote(d))
                except ValueError:
                    continue
            nm = data.get("PolicyName") or data.get("RoleName") or data.get("UserName") or name
            out += _docs(d, nm + (" (trust)" if k == "AssumeRolePolicyDocument" else ""))
    for k in ("UserDetailList", "RoleDetailList", "GroupDetailList", "Policies"):
        for e in data.get(k) or []:
            nm = e.get("RoleName") or e.get("UserName") or e.get("GroupName") or e.get("PolicyName") or k
            for p in e.get("RolePolicyList") or e.get("UserPolicyList") or e.get("GroupPolicyList") or []:
                out += _docs(p, f"{nm} / {p.get('PolicyName', 'inline')}")
            if e.get("AssumeRolePolicyDocument"):
                out += _docs({"AssumeRolePolicyDocument": e["AssumeRolePolicyDocument"], "RoleName": nm})
            for v in e.get("PolicyVersionList") or []:
                if v.get("IsDefaultVersion"):
                    out += _docs({"Document": v.get("Document"), "PolicyName": nm})
    if not out and all(isinstance(v, dict) and "Statement" in v for v in data.values()) and data:
        for k, v in data.items():
            out.append((str(k), v))
    return out


def _aws(docs: list[tuple[str, dict[str, Any]]], add) -> list[dict[str, Any]]:
    rows = []
    for name, d in docs:
        for i, st in enumerate(_l(d.get("Statement"))):
            if not isinstance(st, dict):
                continue
            sid = st.get("Sid") or f"#{i + 1}"
            where = f"{name} {sid}"
            eff = st.get("Effect", "Allow")
            raw = [str(a) for a in _l(st.get("Action"))]
            acts = [a.lower() for a in raw]
            nacts = _l(st.get("NotAction"))
            res = [str(r) for r in _l(st.get("Resource"))]
            nres = _l(st.get("NotResource"))
            pr = st.get("Principal")
            cond = st.get("Condition") or {}
            flags = []
            if eff == "Allow":
                any_res = "*" in res
                if any(a in ("*", "*:*") for a in acts) and any_res:
                    flags.append("full admin")
                    add("bad", "Full admin", f"{where} allows every action on every resource.", "Grant the services and resources this needs, and nothing else.", where)
                else:
                    for a in acts:
                        if a.endswith(":*"):
                            svc = a.split(":")[0]
                            flags.append(f"all of {svc}")
                            add("bad" if svc in SENSITIVE and any_res else "warn", "All actions", f"{where} allows every {svc} action" + (" on every resource." if any_res else "."),
                                f"List the {svc} actions it needs.", where)
                    if any_res:
                        esc = [a for a in acts if a in ESCALATE]
                        if esc:
                            flags.append("escalation")
                            add("bad", "Can raise its own access", f"{where} allows {', '.join(esc[:4])} on every resource - enough to give itself more access.",
                                "Limit these to named resources, or remove them.", where)
                        if "iam:passrole" in acts:
                            flags.append("passrole *")
                            add("bad", "PassRole to any role", f"{where} can pass any role to a service - including an admin role.", "Name the roles it may pass (Resource: the role ARNs).", where)
                        wr = [a for a in acts if a and not READ.match(a) and not a.endswith(":*") and a not in ESCALATE and a != "iam:passrole" and a not in ("*", "*:*")]
                        if wr and not pr:
                            flags.append("write on *")
                            add("warn", "Writes everywhere", f"{where} allows {', '.join(wr[:4])}{' ...' if len(wr) > 4 else ''} on every resource.", "Name the resources.", where)
                if nacts:
                    flags.append("NotAction")
                    add("warn", "Allow with NotAction", f"{where} allows everything except {', '.join(map(str, nacts[:3]))} - new actions are allowed by default.",
                        "Allow a list of actions instead.", where)
                if nres:
                    flags.append("NotResource")
                    add("warn", "Allow with NotResource", f"{where} allows on every resource except {', '.join(map(str, nres[:2]))}.", "Name the resources instead.", where)
                if pr is not None:
                    pv = pr if isinstance(pr, str) else pr.get("AWS") if isinstance(pr, dict) else None
                    pvs = [str(x) for x in _l(pv)]
                    if "*" in pvs or pr == "*":
                        if cond:
                            flags.append("public + condition")
                            add("info", "Public with a condition", f"{where} lets anyone in, limited by a condition ({', '.join(list(cond)[:2])}).", "Check the condition really narrows it.", where)
                        else:
                            flags.append("public")
                            add("bad", "Open to anyone", f"{where} lets anyone on the internet {', '.join(acts[:3]) or 'in'}.", "Name the accounts or roles, or add a condition.", where)
                    fed = [str(x) for x in _l(pr.get("Federated"))] if isinstance(pr, dict) else []
                    if any("token.actions.githubusercontent.com" in f for f in fed):
                        keys = " ".join(k for v in cond.values() if isinstance(v, dict) for k in v)
                        if ":sub" not in keys:
                            flags.append("github oidc, no subject")
                            add("bad", "GitHub can assume it from any repo", f"{where} trusts GitHub's OIDC with no subject condition - any GitHub repository can take this role.",
                                "Add a StringLike condition on token.actions.githubusercontent.com:sub for your repo and branch.", where)
                    ext = [p for p in pvs if re.match(r"arn:aws:iam::\d{12}:", p) or re.fullmatch(r"\d{12}", p)]
                    if ext:
                        flags.append("other accounts")
                        if "sts:externalid" not in json.dumps(cond).lower() and any("assumerole" in a for a in acts):
                            add("info", "Another account", f"{where} trusts {', '.join(ext[:2])}.", "If that is a vendor, require an ExternalId.", where)
            rows.append({"where": where, "effect": eff, "actions": raw[:12] or [f"NOT {x}" for x in nacts[:6]], "resources": res[:6] or [f"NOT {x}" for x in nres[:4]],
                         "principal": pr if isinstance(pr, (str, type(None))) else json.dumps(pr)[:160], "condition": bool(cond), "flags": flags})
    return rows


PRIMITIVE = {"roles/owner": "bad", "roles/editor": "warn"}
IMPERSONATE = ("roles/iam.serviceaccounttokencreator", "roles/iam.serviceaccountuser", "roles/iam.workloadidentityuser", "roles/resourcemanager.projectiamadmin",
               "roles/iam.securityadmin")


def _gcp(data: dict[str, Any], add, name: str = "policy") -> list[dict[str, Any]]:
    rows = []
    for b in data.get("bindings") or []:
        role_s = str(b.get("role", ""))
        role = role_s.lower()
        mem = [str(m) for m in b.get("members") or []]
        cond = bool(b.get("condition"))
        flags = []
        pub = [m for m in mem if m in ("allUsers", "allAuthenticatedUsers")]
        if pub:
            flags.append("public")
            add("bad", "Open to anyone", f"{role} is granted to {', '.join(pub)} - anyone on the internet" + (" with a Google account." if pub == ["allAuthenticatedUsers"] else "."),
                "Remove allUsers / allAuthenticatedUsers unless this is meant to be public.", role)
        if role in PRIMITIVE:
            flags.append("primitive")
            add(PRIMITIVE[role], "Basic role", f"{role} goes to {len(mem)} member(s): {', '.join(mem[:3])}{' ...' if len(mem) > 3 else ''}.",
                "Use predefined roles for what each needs; keep owner to a break-glass group.", role)
        if role in IMPERSONATE and not cond:
            flags.append("impersonation")
            add("warn", "Can act as service accounts", f"{role} at this level lets {', '.join(mem[:3])} act as any service account here.",
                "Grant it on the one service account they need, not the whole project.", role)
        personal = [m for m in mem if re.search(r"@(gmail|googlemail|yahoo|outlook|hotmail)\.", m)]
        if personal:
            flags.append("personal account")
            add("info", "Personal account", f"{role} goes to personal account(s): {', '.join(personal[:3])}.", "Use the organisation's accounts so access ends with the job.", role)
        rows.append({"where": name, "effect": "grant", "actions": [role_s], "resources": ["(this resource)"], "principal": ", ".join(mem[:6]) + (" ..." if len(mem) > 6 else ""),
                     "condition": cond, "flags": flags})
    return rows


def _azure(data: list[dict[str, Any]], add) -> list[dict[str, Any]]:
    rows = []
    for a in data:
        role = str(a.get("roleDefinitionName") or a.get("roleDefinitionId") or "")
        scope = str(a.get("scope") or "")
        who = str(a.get("principalName") or a.get("principalId") or "")
        ptype = str(a.get("principalType") or "")
        flags = []
        wide = scope in ("/", "") or re.fullmatch(r"/subscriptions/[^/]+/?", scope) or "/managementGroups/" in scope
        if role in ("Owner", "User Access Administrator", "Role Based Access Control Administrator") and wide:
            flags.append("admin at subscription")
            add("bad" if scope in ("/", "") or "/managementGroups/" in scope else "warn", "Owner over everything",
                f"{who} ({ptype or 'principal'}) is {role} at {scope or 'the root'} - it can grant itself and anyone else any access.",
                "Grant Owner on a resource group, keep subscription Owner to a few people with Privileged Identity Management.", who)
        elif role == "Contributor" and wide:
            flags.append("contributor at subscription")
            add("info", "Contributor over everything", f"{who} is Contributor at {scope} - it can change every resource there.", "Narrow it to the resource groups it needs.", who)
        rows.append({"where": f"{who} @ {scope}", "effect": "assign", "actions": [role], "resources": [scope], "principal": f"{who} {ptype}".strip(), "condition": bool(a.get("condition")),
                     "flags": flags})
    return rows


def analyse(text: str) -> dict[str, Any]:
    t = str(text or "").strip()
    if not t:
        raise IamError("Paste a policy: AWS IAM JSON, `gcloud ... get-iam-policy --format=json`, or `az role assignment list`.")
    chunks = [c for c in re.split(r"(?m)^##\s+.*$", t) if c.strip()] if re.search(r"(?m)^##\s+", t) else [t]
    names = re.findall(r"(?m)^##\s+(.*)$", t)
    issues, add = finder()
    rows: list[dict[str, Any]] = []
    kinds = set()
    for i, ch in enumerate(chunks):
        try:
            data = json.loads(ch)
        except ValueError as e:
            raise IamError(f"The JSON could not be read: {e}")
        nm = names[i].strip() if i < len(names) else "policy"
        if isinstance(data, dict) and "bindings" in data:
            kinds.add("gcp")
            rows += _gcp(data, add, nm if nm != "policy" else "IAM policy")
        elif isinstance(data, list) and data and isinstance(data[0], dict) and ("roleDefinitionName" in data[0] or "roleDefinitionId" in data[0]):
            kinds.add("azure")
            rows += _azure(data, add)
        else:
            docs = _docs(data, nm)
            if not docs:
                raise IamError("No policy found - AWS needs Statement, Google Cloud needs bindings, Azure needs roleDefinitionName.")
            kinds.add("aws")
            rows += _aws(docs, add)
    if not rows:
        raise IamError("The policy has no statements or bindings.")
    flagged = [r for r in rows if r["flags"]]
    res = {"kinds": sorted(kinds), "statements": len(rows), "flagged": len(flagged), "rows": rows[:500],
           "verdict": f"{len(rows)} statement(s) or grant(s), {len(flagged)} with a problem"}
    res["note"] = ("Read from the policy text alone: a permissions boundary, a service control policy or a deny elsewhere can still narrow what these "
                   "allow, and conditions are reported, not evaluated. Nothing is changed.")
    return finish(res, issues)
