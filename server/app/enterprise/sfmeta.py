"""Salesforce Metadata deploy - the part a CRM architect's job actually needs, which Tooling API cannot do.

v0.367 shipped the CRM desk calling itself "100% read and write". That claim was WRONG, and Salesforce's own
documentation says so:

    "CRUD operations on the following Tooling API objects in an active org generate the error
     `Save or update not supported in active organizations`: ApexClass, ApexComponent, ApexPage,
     ApexTrigger, CustomField, CustomObject."
    developer.salesforce.com/docs/atlas.en-us.api_tooling.meta/api_tooling/intro_crud_operations.htm

So in her LIVE org, Tooling could not create a field or an object at all. On top of that CustomObject is
read-only by either protocol, Profile and PermissionSet have no write path, and Layout is SOAP-only. That is
most of a CRM architect's work.

The fix is Metadata REST - `deployRequest` - and it is a good fit rather than a grudging one:

  POST /services/data/vXX.0/metadata/deployRequest     multipart: a `json` part + a `file` part (the zip)
  GET  /services/data/vXX.0/metadata/deployRequest/{id}?includeDetails=true    poll until deployResult.done
  POST /services/data/vXX.0/metadata/deployRequest/{validatedId}               quick-deploy a validation
  developer.salesforce.com/docs/atlas.en-us.api_meta.meta/api_meta/meta_rest_intro.htm

Three things make it fit the engine we already have:
  - it takes the SAME Bearer token - no SOAP envelope, no WSDL, no second credential, no new dependency;
  - `checkOnly: true` IS a real dry run: "A validation enables you to verify the results of tests that would
    be generated in a deployment, but doesn't commit any changes";
  - a successful validation can be QUICK-DEPLOYED for 10 days without re-running tests, which maps exactly
    onto dry run -> HER TAP -> execute.

Production rules are Salesforce's, not ours, and they are enforced here in code:
  - `rollbackOnError` "must be set to true if you're deploying to a production org" -> forced true;
  - `allowMissingFiles` "Don't set this argument for deployment to production orgs" -> forced false;
  - `purgeOnDelete` "only works in Developer Edition or sandbox orgs" -> never sent;
  - a config-only package runs no tests by default, so we leave testLevel unset unless Apex is in the package.

NOT VERIFIED live: no Salesforce org has answered this code. The shapes come from Salesforce's documentation.
What is deliberately NOT built, and refused rather than faked:
  - field-level edits. CustomField, ValidationRule and RecordType are NOT separate files - they live inside
    the parent `objects/<Obj>.object`. Deploying a hand-built object file holding only one field risks the
    rest of her object, and Metadata REST has no `retrieve` to merge against (retrieve is SOAP-only). So a
    field change is refused with the reason, instead of shipped as a guess.
  - destructiveChanges.xml. Hoola refuses delete at any size, so the delete manifest is never emitted.
"""
from __future__ import annotations

import io
import json
import logging
import re
import zipfile
from typing import Any
from xml.sax.saxutils import escape

log = logging.getLogger("santosh.enterprise.sfmeta")

API = "68.0"                 # Winter '27 was current at v0.388; the URL version and package.xml must match
PIN = "64.0"                 # what we actually call: a release or two back, inside the 3-year support window
MAX_FILES = 10000            # Salesforce: "You can deploy or retrieve up to 10,000 files at once"
MAX_ZIP = 39 * 1024 * 1024   # "The maximum size of the deployed or retrieved .zip file is 39 MB"

# Each metadata type's own documented folder and suffix. A TABLE, not an if-chain.
#   whole_file True  = the component IS one file we can write end to end
#   whole_file False = it lives inside another file, so we refuse rather than guess
TYPES: dict[str, dict[str, Any]] = {
    "ApexClass":      {"dir": "classes",       "ext": ".cls",           "meta": True,  "whole_file": True},
    "ApexTrigger":    {"dir": "triggers",      "ext": ".trigger",       "meta": True,  "whole_file": True},
    "ApexPage":       {"dir": "pages",         "ext": ".page",          "meta": True,  "whole_file": True},
    "Flow":           {"dir": "flows",         "ext": ".flow",          "meta": False, "whole_file": True},
    "Layout":         {"dir": "layouts",       "ext": ".layout",        "meta": False, "whole_file": True},
    "PermissionSet":  {"dir": "permissionsets", "ext": ".permissionset", "meta": False, "whole_file": True},
    "Profile":        {"dir": "profiles",      "ext": ".profile",       "meta": False, "whole_file": True},
    "CustomObject":   {"dir": "objects",       "ext": ".object",        "meta": False, "whole_file": True},
    "CustomField":    {"dir": "objects",       "ext": ".object",        "meta": False, "whole_file": False,
                       "inside": "CustomObject"},
    "ValidationRule": {"dir": "objects",       "ext": ".object",        "meta": False, "whole_file": False,
                       "inside": "CustomObject"},
    "RecordType":     {"dir": "objects",       "ext": ".object",        "meta": False, "whole_file": False,
                       "inside": "CustomObject"},
}
APEX_TYPES = ("ApexClass", "ApexTrigger", "ApexPage")


class MetaError(Exception):
    pass


def _name_ok(n: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_\-. ]{1,120}", n or ""))


# ---------------------------------------------------------------- the package
def package_xml(components: list[dict[str, Any]], version: str = PIN) -> str:
    """The manifest. Salesforce "references the components listed in the manifest, not the directories in the
    .zip file", so this file - not the zip layout - is what actually decides what is deployed."""
    by_type: dict[str, list[str]] = {}
    for c in components:
        t, n = str(c.get("type") or ""), str(c.get("name") or "")
        if t not in TYPES:
            raise MetaError(f"'{t}' is not in Hoola's deploy. What is: " + ", ".join(sorted(TYPES)))
        if not _name_ok(n):
            raise MetaError(f"'{n}' is not a valid name.")
        by_type.setdefault(t, []).append(n)
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<Package xmlns="http://soap.sforce.com/2006/04/metadata">']
    for t in sorted(by_type):
        out.append("    <types>")
        for n in sorted(set(by_type[t])):
            out.append(f"        <members>{escape(n)}</members>")
        out.append(f"        <name>{escape(t)}</name>")
        out.append("    </types>")
    out.append(f"    <version>{escape(version)}</version>")
    out.append("</Package>")
    return "\n".join(out) + "\n"


def build_zip(components: list[dict[str, Any]], version: str = PIN) -> bytes:
    """Build the deploy zip in memory. Every component must bring its OWN complete body - we never invent the
    XML of a thing we were not given, and we never emit a partial object file."""
    for c in components:
        t = str(c.get("type") or "")
        spec = TYPES.get(t)
        if spec and not spec["whole_file"]:
            raise MetaError(
                f"{t} has no file of its own - it lives inside the '{spec['inside']}' file. "
                "Sending one part without its whole file can put the rest of your object at risk, "
                "and Metadata REST has no 'retrieve' for us to read the old file and "
                "merge it. So Hoola does not send this on a guess: give the whole CustomObject, or make this change "
                "in a sandbox through Tooling.")
        if not str(c.get("body") or "").strip():
            raise MetaError(f"{t} '{c.get('name')}' has no body.")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("package.xml", package_xml(components, version))
        for c in components:
            t, n = str(c["type"]), str(c["name"])
            spec = TYPES[t]
            z.writestr(f"{spec['dir']}/{n}{spec['ext']}", str(c["body"]))
            if spec["meta"]:
                z.writestr(f"{spec['dir']}/{n}{spec['ext']}-meta.xml", _meta_xml(version))
    data = buf.getvalue()
    n_files = len(components) * 2 + 1
    if n_files > MAX_FILES:
        raise MetaError(f"Salesforce takes {MAX_FILES} files at once; there are {n_files}.")
    if len(data) > MAX_ZIP:
        raise MetaError(f"The zip is {len(data) // (1024 * 1024)} MB; the Salesforce limit is 39 MB.")
    return data


def _meta_xml(version: str) -> str:
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">\n'
            f'    <apiVersion>{escape(version)}</apiVersion>\n'
            '    <status>Active</status>\n'
            '</ApexClass>\n')


# ---------------------------------------------------------------- options
def deploy_options(env: str, components: list[dict[str, Any]], test_level: str = "") -> dict[str, Any]:
    """Salesforce's production rules, applied in code. She cannot talk us out of them and neither can a
    prompt, because they are the vendor's requirements, not our policy."""
    has_apex = any(str(c.get("type")) in APEX_TYPES for c in components)
    prod = (env or "").lower() == "production"
    o: dict[str, Any] = {"singlePackage": True, "ignoreWarnings": False,
                         "allowMissingFiles": False,          # documented: do not set for production
                         "rollbackOnError": True if prod else True,
                         "checkOnly": False}
    # "The test level is enforced regardless of the types of components that are present" - so an unset level
    # on a config-only package is RIGHT: it runs no tests. We only set one when Apex is in the package.
    lvl = (test_level or "").strip()
    if lvl:
        if lvl not in ("NoTestRun", "RunSpecifiedTests", "RunLocalTests", "RunAllTestsInOrg"):
            raise MetaError("testLevel NoTestRun | RunSpecifiedTests | RunLocalTests | RunAllTestsInOrg")
        if prod and lvl == "NoTestRun":
            raise MetaError("No NoTestRun in production - Salesforce runs all local tests itself.")
        o["testLevel"] = lvl
    elif has_apex and prod:
        o["testLevel"] = "RunLocalTests"                       # Salesforce's own production default
    return o


# ---------------------------------------------------------------- the calls
def _base(ep: Any) -> str:
    return str(ep.base_url).rstrip("/")


def _headers(ep: Any) -> dict[str, str]:
    from ..bazar.security import vault
    if not getattr(ep, "auth_enc", ""):
        raise MetaError("No credential found for this org.")
    secret = vault().open(ep.auth_enc)
    kind = getattr(ep, "auth_kind", "bearer")
    if kind != "bearer":
        raise MetaError("A Metadata deploy needs an OAuth bearer token.")
    return {"Authorization": "Bearer " + secret}


def _url(ep: Any, tail: str = "") -> str:
    root = f"{_base(ep)}/services/data/v{PIN}/metadata/deployRequest"
    return root + (("/" + tail.lstrip("/")) if tail else "")


def validate(ep: Any, components: list[dict[str, Any]], test_level: str = "") -> dict[str, Any]:
    """The DRY RUN, and a real one: components are checked and tests are executed, nothing is committed."""
    opts = deploy_options(getattr(ep, "env", "test"), components, test_level)
    opts["checkOnly"] = True
    return _submit(ep, components, opts)


def deploy(ep: Any, components: list[dict[str, Any]], test_level: str = "") -> dict[str, Any]:
    opts = deploy_options(getattr(ep, "env", "test"), components, test_level)
    opts["checkOnly"] = False
    return _submit(ep, components, opts)


def _submit(ep: Any, components: list[dict[str, Any]], opts: dict[str, Any]) -> dict[str, Any]:
    import httpx
    zip_bytes = build_zip(components)
    files = {
        # the two parts are named exactly `json` and `file` - Salesforce rejects anything else
        "json": (None, json.dumps({"deployOptions": opts}), "application/json"),
        "file": ("deploy.zip", zip_bytes, "application/zip"),
    }
    with httpx.Client(timeout=180) as c:
        res = c.post(_url(ep), headers=_headers(ep), files=files)
    data = _json(res)
    if res.status_code >= 300:
        raise MetaError(f"Salesforce answered {res.status_code}: " + json.dumps(data, default=str)[:400])
    return {"deploy": str(data.get("id") or ""), "checkOnly": bool(opts.get("checkOnly")),
            "options": opts, "zip_bytes": len(zip_bytes), "status": _result(data).get("status", "Pending")}


def quick_deploy(ep: Any, validated_id: str) -> dict[str, Any]:
    """Her tap, after a clean validation: deploy the ALREADY-VALIDATED run without re-running its tests.
    Valid for 10 days, and only if the coverage rules were met - otherwise Salesforce refuses and we say so
    rather than silently building a fresh full deploy she did not approve."""
    import httpx
    if not re.fullmatch(r"[A-Za-z0-9]{15,18}", validated_id or ""):
        raise MetaError("The deploy id is not valid.")
    with httpx.Client(timeout=120) as c:
        res = c.post(_url(ep, validated_id), headers=_headers(ep))
    data = _json(res)
    if res.status_code >= 300:
        raise MetaError(
            f"Quick deploy did not go through ({res.status_code}): " + json.dumps(data, default=str)[:300]
            + " - a 10-day-old preview or test coverage may be the reason. Take a new preview.")
    return {"deploy": str(data.get("id") or validated_id), "status": _result(data).get("status", "Pending")}


def poll(ep: Any, deploy_id: str) -> dict[str, Any]:
    """One look at a running deploy. A deploy with tests takes minutes, so the caller keeps the id and comes
    back - it NEVER resubmits, because resubmitting is how a deploy happens twice."""
    import httpx
    if not re.fullmatch(r"[A-Za-z0-9]{15,18}", deploy_id or ""):
        raise MetaError("The deploy id is not valid.")
    with httpx.Client(timeout=90) as c:
        res = c.get(_url(ep, deploy_id), headers=_headers(ep), params={"includeDetails": "true"})
    data = _json(res)
    if res.status_code >= 300:
        raise MetaError(f"Salesforce answered {res.status_code}: " + json.dumps(data, default=str)[:300])
    r = _result(data)
    out: dict[str, Any] = {
        "deploy": deploy_id, "status": r.get("status", ""), "done": bool(r.get("done")),
        "hue": r.get("numberComponentsDeployed", 0), "kul": r.get("numberComponentsTotal", 0),
        "galtiyan": r.get("numberComponentErrors", 0),
        "test_hue": r.get("numberTestsCompleted", 0), "test_kul": r.get("numberTestsTotal", 0),
        "test_fail": r.get("numberTestErrors", 0), "kya_chal_raha": r.get("stateDetail", "") or "",
    }
    if r.get("errorMessage"):
        out["kyon"] = str(r.get("errorMessage"))[:400]
    det = r.get("details") if isinstance(r.get("details"), dict) else {}
    out["jo_fail_hue"] = [{"file": f.get("fileName"), "kya": f.get("problem"),
                           "line": f.get("lineNumber")}
                          for f in _list(det.get("componentFailures"))][:30]
    tests = det.get("runTestResults") if isinstance(det.get("runTestResults"), dict) else {}
    out["test_jo_fail_hue"] = [{"class": f.get("name"), "method": f.get("methodName"),
                                "kya": (f.get("message") or "")[:300]}
                               for f in _list(tests.get("failures"))][:20]
    if not out["jo_fail_hue"]:
        out.pop("jo_fail_hue")
    if not out["test_jo_fail_hue"]:
        out.pop("test_jo_fail_hue")
    return out


def cancel(ep: Any, deploy_id: str) -> dict[str, Any]:
    import httpx
    if not re.fullmatch(r"[A-Za-z0-9]{15,18}", deploy_id or ""):
        raise MetaError("The deploy id is not valid.")
    with httpx.Client(timeout=60) as c:
        res = c.post(_url(ep, deploy_id), headers=_headers(ep), json={"deployResult": {"status": "Canceling"}})
    return {"deploy": deploy_id, "status": res.status_code}


def _json(res: Any) -> Any:
    try:
        return res.json()
    except ValueError:
        return {"text": (res.text or "")[:2000]}


def _result(data: Any) -> dict[str, Any]:
    if isinstance(data, dict) and isinstance(data.get("deployResult"), dict):
        return data["deployResult"]
    return data if isinstance(data, dict) else {}


def _list(v: Any) -> list[dict[str, Any]]:
    if isinstance(v, dict):
        return [v]
    return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else []
