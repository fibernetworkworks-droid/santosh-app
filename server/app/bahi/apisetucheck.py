"""`python -m app.bahi.apisetucheck [GSTIN]` - does the owner's API Setu GSTN access work? (vps-ops `apisetu_check`).

Prints how the two pasted keys LOOK (length, hidden dots, spaces - never a value), makes ONE taxpayer lookup and says PASS / FAIL
with the plain reason, and records the reply's SHAPE (keys + types only) to data/bahi/apisetu_shape.json. The taxpayer record of
the looked-up GSTIN is public GST data, so its name / status / dates are printed.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import get_settings
from . import apisetu
from .wb import clean

# Used when APISETU_TEST_GSTIN is empty: WhiteBooks' GST test GSTIN if set, else a GSTIN with a valid check digit that public
# GST lookup providers use in their own examples. Any answer other than "keys refused" proves the keys work.
FALLBACK_GSTIN = "33AAACC1206D1ZN"
_KEYS = (("APISETU_CLIENT_ID", "apisetu_client_id"), ("APISETU_API_KEY", "apisetu_api_key"))


def shape_path() -> Path:
    return Path("data") / "bahi" / "apisetu_shape.json"


def _shape(v: Any) -> Any:
    if isinstance(v, dict):
        return {k: _shape(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_shape(v[0])] if v else []
    return type(v).__name__


def paste_check() -> list[dict[str, Any]]:
    st = get_settings()
    out = []
    for name, attr in _KEYS:
        raw = str(getattr(st, attr, "") or "")
        if not raw:
            out.append({"name": name, "set": False, "ok": False, "note": "missing"})
            continue
        v = clean(raw)
        notes, bad = [], False
        if v != raw:
            notes.append("spaces / quotes / line end around it (Hoola strips them)")
        if any(ch in v for ch in "\u2022\u25cf\u00b7*") or not v.isascii():
            notes.append("has dots or non-keyboard characters - copied from a hidden field? copy it again with the copy button")
            bad = True
        if " " in v:
            notes.append("has a space inside")
            bad = True
        out.append({"name": name, "set": True, "ok": not bad,
                    "note": f"{len(v)} characters" + ("; " + "; ".join(notes) if notes else "")})
    return out


def test_gstin(arg: str = "") -> str:
    st = get_settings()
    return (clean(arg) or clean(st.apisetu_test_gstin) or clean(st.whitebooks_sandbox_gst_gstin) or FALLBACK_GSTIN).upper()


def run(arg: str = "") -> dict[str, Any]:
    res: dict[str, Any] = {"paste": paste_check(), "base": apisetu.base(), "gstin": test_gstin(arg)}
    if not apisetu.configured():
        res.update(result="SKIP", line="APISETU_CLIENT_ID and APISETU_API_KEY are not both in the VPS .env")
        return res
    try:
        raw = apisetu.taxpayer(res["gstin"], raw=True)
    except apisetu.ApiSetuError as e:
        keys_ok = e.code in ("record_not_found", "no_record")   # API Setu answered about this taxpayer = the keys got through
        res.update(result="PASS" if keys_ok else "FAIL", code=e.code, status=e.status, line=e.message, keys_accepted=keys_ok)
        return res
    rec = apisetu._plain(raw)
    res.update(result="PASS", keys_accepted=True, record=rec, line="keys accepted; GSTN answered the lookup")
    p = shape_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "base": res["base"],
                             "shape": _shape(raw)}, indent=1), encoding="utf-8")
    res["shape_saved"] = str(p)
    return res


def main(argv: list[str]) -> int:
    r = run(argv[0] if argv else "")
    print("== how the pasted keys look (never the values)")
    for p in r["paste"]:
        print(f"  {'set    ' if p['set'] else 'missing'}  {p['name']}: {p['note']}")
    print(f"== lookup  {r['base']}/taxpayers/{r['gstin']}")
    print(f"  {r['result']}  {r['line']}" + (f"  (HTTP {r['status']}, {r['code']})" if r.get("status") else ""))
    rec = r.get("record")
    if rec:
        for k in ("legal_name", "status", "constitution", "taxpayer_type", "registered_on", "cancelled_on",
                  "state_jurisdiction", "centre_jurisdiction"):
            print(f"    {k:20} {rec.get(k) or '-'}")
        print(f"    {'activities':20} {', '.join(rec.get('activities') or []) or '-'}")
        print(f"  reply shape saved to {r['shape_saved']}")
    if r["result"] == "PASS" and r.get("code") in ("record_not_found", "no_record"):
        print("  (the keys work; GSTN just has no taxpayer with this GSTIN - set APISETU_TEST_GSTIN to a real, registered GSTIN - e.g. your own - and run apisetu_check again to see a record)")
    return 0 if r["result"] == "PASS" else (0 if r["result"] == "SKIP" else 1)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
