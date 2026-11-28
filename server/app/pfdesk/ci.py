"""A GitHub Actions plan guard for her infrastructure: on every pull request it runs terraform init and plan in her folder, turns
the plan into JSON, and fails when the plan would destroy or replace a data store (databases, buckets, disks, keys - plus the
types she adds) or destroy more resources than she allows - the list written to the run's summary. Cloud access comes from the
repository's own OIDC role or secrets, set by her; nothing is applied and nothing is pushed."""
from __future__ import annotations

import re
from typing import Any

from .common import PfInputError
from .tfplan import SETTINGS_OF, STATEFUL


class CiError(PfInputError):
    pass


GUARD = r'''import json, os, sys
STATEFUL = @STATEFUL@
SETTINGS_OF = @SETTINGS@
EXTRA = @EXTRA@
MAX = @MAX@
d = json.load(open(sys.argv[1]))
def stateful(t):
    t = t.lower()
    if t.endswith(SETTINGS_OF):
        return any(t == e or t.startswith(e) for e in EXTRA)
    return any(x in t for x in STATEFUL) or any(t == e or t.startswith(e) for e in EXTRA)
rows, fail, destroys = [], [], 0
for rc in d.get("resource_changes") or []:
    a = (rc.get("change") or {}).get("actions") or []
    if rc.get("mode") == "data" or "delete" not in a:
        continue
    destroys += 1
    k = "replace" if "create" in a else "destroy"
    if stateful(rc.get("type", "")):
        fail.append(f"{rc['address']} would be {k}d - a data store")
        rows.append(f"| {rc['address']} | {k} | FAIL |")
    else:
        rows.append(f"| {rc['address']} | {k} | |")
if MAX is not None and destroys > MAX:
    fail.append(f"{destroys} resources would be destroyed - over the limit of {MAX}")
with open(os.environ.get("GITHUB_STEP_SUMMARY", os.devnull), "a") as s:
    s.write(f"## Plan guard\n\n{destroys} resource(s) destroyed or replaced.\n\n" + ("| resource | action | |\n|---|---|---|\n" + "\n".join(rows) + "\n" if rows else ""))
print("\n".join(rows) or "nothing destroyed")
for f in fail:
    print("::error::" + f)
sys.exit(1 if fail else 0)
'''


def workflow(tf_dir: str = ".", tf_version: str = "1.9.5", max_destroy: Any = 0, protected: str = "", runner: str = "ubuntu-24.04",
             var_file: str = "", tofu: bool = False) -> dict[str, Any]:
    d = str(tf_dir or ".").strip()
    if not re.fullmatch(r"[\w./\-]{1,160}", d) or ".." in d or d.startswith("/"):
        raise CiError("Terraform folder: a path inside the repository, such as infra/prod.")
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(tf_version or "")):
        raise CiError("Terraform version: a full version such as 1.9.5.")
    vf = str(var_file or "").strip()
    if vf and (not re.fullmatch(r"[\w./\-]{1,160}", vf) or ".." in vf or vf.startswith("/")):
        raise CiError("Variables file: a path inside the repository, such as prod.tfvars.")
    try:
        mx = None if str(max_destroy).strip() in ("", "none") else int(float(max_destroy))
    except (TypeError, ValueError):
        raise CiError("Destroy limit: a whole number (0 = no destroys at all).")
    if mx is not None and not 0 <= mx <= 100000:
        raise CiError("Destroy limit: 0 or more.")
    extra = [x.strip().lower() for x in str(protected or "").split(",") if x.strip()]
    if any(not re.fullmatch(r"[a-z0-9_]{2,80}", x) for x in extra):
        raise CiError("Protected types: resource type names such as aws_route53_zone, separated by commas.")
    if not re.fullmatch(r"[\w.\-]{1,40}", str(runner or "")):
        raise CiError("Runner: a runner label such as ubuntu-24.04.")
    tool = "tofu" if tofu else "terraform"
    py = GUARD.replace("@STATEFUL@", repr(list(STATEFUL))).replace("@SETTINGS@", repr(SETTINGS_OF)).replace("@EXTRA@", repr(extra)).replace("@MAX@", repr(mx))
    py = "\n".join(("          " + ln) if ln else "" for ln in py.splitlines())
    setup = (f"""      - uses: opentofu/setup-opentofu@v1
        with:
          tofu_version: "{tf_version}"
""" if tofu else f"""      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "{tf_version}"
          terraform_wrapper: false
""")
    yaml = f"""name: Plan guard
# Made by Hoola's Platform Engineer desk. Plans every pull request and fails when the plan destroys or replaces a data store
# or destroys more than {mx if mx is not None else 'any number of'} resource(s). It never applies.
on:
  pull_request:
    paths: ["{d.rstrip('/')}/**"]
  workflow_dispatch:
permissions:
  contents: read
  id-token: write   # for your cloud's OIDC login step, if you add one
jobs:
  plan:
    runs-on: {runner}
    timeout-minutes: 30
    defaults:
      run:
        working-directory: {d}
    steps:
      - uses: actions/checkout@v4
{setup}      # Add your cloud login here (e.g. aws-actions/configure-aws-credentials with role-to-assume) - never keys in this file.
      - name: Init
        run: {tool} init -input=false -lock=false
      - name: Plan
        run: {tool} plan -input=false -lock=false -out=plan.out{(' -var-file=' + vf) if vf else ''}
      - name: Plan as JSON
        run: {tool} show -json plan.out > plan.json
      - name: Guard
        run: |
          python3 - plan.json <<'PY'
{py}
          PY
"""
    return {"file": ".github/workflows/plan-guard.yml", "yaml": yaml, "guard": py,
            "note": ("Put it at .github/workflows/plan-guard.yml and add your cloud login step (an OIDC role is better than stored keys). "
                     "The plan runs with -lock=false so a pull request never blocks a real apply; give the role read-only access. "
                     "Make the check required in branch protection so a destroying change cannot merge without a person looking.")}
