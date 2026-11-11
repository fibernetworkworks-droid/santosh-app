"""D7 workflows (docs/DOCUMENT_KIT_PLAN.md D7): a chain of pdf_kit steps run as ONE job, saved under her own name and
run again on one file or a whole batch.

Only steps that need no yes from her in the middle are allowed (no redaction preview, no AI, no password page in the
middle of a chain). Each step's in-between file stays in memory; only the last step's files reach her chat. The rules
here are checked BEFORE anything runs, so a broken chain never half-runs."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from .core import DocError

MAX_STEPS = 12
MAX_SAVED = 50
MAX_BATCH = 50

FIRST = ("merge", "to_pdf", "interleave")                  # many files (or pictures / Office) in -> one PDF
MIDDLE = ("rotate", "remove", "extract", "organize", "reverse", "compress", "repair", "page_numbers", "watermark",
          "header_footer", "crop", "add", "highlight", "metadata", "bookmarks", "flatten", "nup", "booklet", "fit",
          "grayscale", "sanitize", "ocr", "pdfa", "form_fill", "sign")
LAST = ("protect", "split", "to_images", "to_word", "to_excel", "to_powerpoint", "to_text")
STEPS = FIRST + MIDDLE + LAST
NEVER = {"redact": "redaction needs her yes on a preview first - run redact on its own",
         "redact_apply": "redaction needs her yes on a preview first",
         "unlock": "an open password is typed only on its own one-time page - unlock first, on its own",
         "summarize": "AI steps are asked on their own", "ask": "AI steps are asked on their own",
         "translate": "AI steps are asked on their own", "smart_split": "AI steps are asked on their own",
         "compare": "compare takes two versions, on its own", "sign_request": "a signing request is sent on its own",
         "web_to_pdf": "a web page is printed on its own, then the workflow runs on it"}
NO_ARGS = ("file_id", "file_ids", "action", "steps", "name")    # a step never names its own input file

PRESETS: dict[str, dict[str, Any]] = {
    "ca": {"title": "For the CA", "line": "Join, number the pages, make it under 5 MB, lock it",
           "steps": [{"action": "merge"}, {"action": "page_numbers"}, {"action": "compress", "target_kb": 5000},
                     {"action": "protect"}]},
    "portal": {"title": "Exam / job portal", "line": "Photos to one PDF, then under 200 KB",
               "steps": [{"action": "to_pdf", "page_size": "a4"}, {"action": "compress", "target_kb": 200}]},
    "scan": {"title": "Clean scan", "line": "Pictures to one PDF, make the words searchable, smaller",
             "steps": [{"action": "to_pdf", "page_size": "a4"}, {"action": "ocr"}, {"action": "compress"}]},
    "whatsapp": {"title": "Send on WhatsApp", "line": "Smaller than WhatsApp's limit",
                 "steps": [{"action": "compress", "target_kb": 15000}]},
    "office": {"title": "Office copy", "line": "Page numbers, a CONFIDENTIAL mark, no hidden data",
               "steps": [{"action": "page_numbers"}, {"action": "watermark", "text": "CONFIDENTIAL"},
                         {"action": "sanitize"}]},
}


def check(steps: Any) -> list[dict[str, Any]]:
    """The chain, cleaned, or a plain DocError naming the step and why. Nothing has run when this refuses."""
    if not isinstance(steps, list) or not steps:
        raise DocError("A workflow needs steps: a list like [{action: 'merge'}, {action: 'compress', target_kb: 2000}].")
    if len(steps) > MAX_STEPS:
        raise DocError(f"A workflow can have up to {MAX_STEPS} steps; this one has {len(steps)}.")
    out = []
    for i, st in enumerate(steps, 1):
        if isinstance(st, str):
            st = {"action": st}
        if not isinstance(st, dict):
            raise DocError(f"Step {i} must be {{action: ..., options}}.")
        act = str(st.get("action") or "").strip().lower()
        if act in NEVER:
            raise DocError(f"Step {i} ({act}) cannot be inside a workflow: {NEVER[act]}.")
        if act not in STEPS:
            raise DocError(f"Step {i}: '{act}' is not a workflow step. Steps: {', '.join(STEPS)}.")
        if act in FIRST and i != 1:
            raise DocError(f"Step {i} ({act}) takes the starting files, so it can only be step 1.")
        if act in LAST and i != len(steps):
            raise DocError(f"Step {i} ({act}) makes the final files, so it can only be the last step.")
        if act == "protect" and str(st.get("password") or "hoola") == "mine":
            raise DocError("Inside a workflow the lock uses a password Hoola makes (shown once on its own page). "
                           "For her own password, lock the result on its own with password=mine.")
        if act == "sign" and str(st.get("mode") or "place") != "place":
            raise DocError("Inside a workflow only her signature picture can be placed (sign mode=place); a digital "
                           "signature is added on its own, last.")
        out.append({"action": act, **{k: v for k, v in st.items() if k != "action" and k not in NO_ARGS}})
    return out


def describe(steps: list[dict[str, Any]]) -> str:
    def one(s: dict) -> str:
        opts = ", ".join(f"{k}={v}" for k, v in s.items() if k != "action")
        return s["action"] + (f" ({opts})" if opts else "")
    return " -> ".join(one(s) for s in steps)


# ------------------------------------------------------------------------------------------ her saved workflows
def _dir() -> Path:
    from .sign import _dir as base
    return base("dockit_flows")


def _safe_tenant(tenant: str) -> str:
    t = re.sub(r"[^A-Za-z0-9_.-]", "_", str(tenant or ""))[:80]
    if not t:
        raise DocError("No account.")
    return t


def _key(name: str) -> str:
    k = re.sub(r"[^a-z0-9]+", "-", str(name or "").strip().lower()).strip("-")[:60]
    if not k:
        raise DocError("Give the workflow a name, like 'CA ke liye'.")
    return k


def _load(tenant: str) -> dict[str, Any]:
    p = _dir() / f"{_safe_tenant(tenant)}.json"
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


def _write(tenant: str, data: dict[str, Any]) -> None:
    p = _dir() / f"{_safe_tenant(tenant)}.json"
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False))
    tmp.replace(p)


def save(tenant: str, name: str, steps: Any) -> dict[str, Any]:
    clean = check(steps)
    data = _load(tenant)
    k = _key(name)
    was = k in data
    if not was and len(data) >= MAX_SAVED:
        raise DocError(f"She already has {MAX_SAVED} saved workflows; delete one first.")
    data[k] = {"name": str(name).strip()[:80], "steps": clean, "saved": int(time.time()),
               "runs": int((data.get(k) or {}).get("runs") or 0)}
    _write(tenant, data)
    return {"saved": data[k]["name"], "key": k, "steps": describe(clean), "replaced": was}


def listing(tenant: str) -> dict[str, Any]:
    mine = [{"key": k, "name": v["name"], "steps": describe(v["steps"]), "runs": v.get("runs", 0)}
            for k, v in sorted(_load(tenant).items(), key=lambda kv: -int(kv[1].get("saved") or 0))]
    ready = [{"key": k, "name": v["title"], "line": v["line"], "steps": describe(v["steps"])} for k, v in PRESETS.items()]
    return {"mine": mine, "ready_made": ready}


def find(tenant: str, name: str) -> tuple[str, list[dict[str, Any]]]:
    """Her saved workflow first, then a ready-made one; the steps are checked again (rules may have tightened)."""
    k = _key(name)
    mine = _load(tenant)
    if k in mine:
        return mine[k]["name"], check(mine[k]["steps"])
    if k in PRESETS:
        return PRESETS[k]["title"], check(PRESETS[k]["steps"])
    for v in mine.values():                     # her words may differ a little from the key
        if _key(v["name"]) == k:
            return v["name"], check(v["steps"])
    names = [v["name"] for v in mine.values()] + list(PRESETS)
    raise DocError(f"No workflow called '{name}'. Hers / ready-made: {', '.join(names) or 'none yet'}.")


def counted(tenant: str, name: str) -> None:
    data = _load(tenant)
    k = _key(name)
    if k in data:
        data[k]["runs"] = int(data[k].get("runs") or 0) + 1
        _write(tenant, data)


def delete(tenant: str, name: str) -> dict[str, Any]:
    data = _load(tenant)
    k = _key(name)
    if k not in data:
        raise DocError(f"No saved workflow called '{name}'.")
    gone = data.pop(k)["name"]
    _write(tenant, data)
    return {"deleted": gone}
