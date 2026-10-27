"""v0.59 IFSC -> bank + branch (razorpay/ifsc, MIT code; data from RBI / NPCI lists, public).

- Shipped: `ifsc_codes.json.gz` = every valid IFSC per bank + bank names (validity check works offline).
- Branch details (address, city, MICR, UPI/NEFT/RTGS/IMPS): data/ifsc/by-bank/<BANK>.json from the project's monthly
  release `by-bank.tar.gz` (refresh() downloads it; deploy/setup_ocr.sh runs it once); else Razorpay's free IFSC API.
An IFSC is a branch code, not account data: it is fine to look up and show.
"""
from __future__ import annotations

import gzip
import io
import json
import re
import tarfile
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent
DATA = Path("data") / "ifsc"
RELEASE = "https://github.com/razorpay/ifsc/releases/latest/download/by-bank.tar.gz"
API = "https://ifsc.razorpay.com/{code}"
_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
_transport = None    # tests


@lru_cache(maxsize=1)
def _codes() -> dict[str, Any]:
    d = json.loads(gzip.open(HERE / "ifsc_codes.json.gz", "rt").read())
    sets: dict[str, tuple[set, set]] = {}
    for bank, items in d["codes"].items():
        nums = {int(x) for x in items if isinstance(x, int)}
        strs = {str(x) for x in items if not isinstance(x, int)}
        sets[bank] = (nums, strs)
    return {"sets": sets, "names": d["names"]}


def bank_name(prefix: str) -> str:
    return _codes()["names"].get((prefix or "")[:4].upper(), "")


def valid(code: str) -> bool:
    code = (code or "").strip().upper()
    if not _RE.match(code):
        return False
    s = _codes()["sets"].get(code[:4])
    if not s:
        return False
    tail = code[5:]
    return (tail.isdigit() and int(tail) in s[0]) or tail in s[1]


def _local(code: str) -> dict[str, Any] | None:
    f = DATA / "by-bank" / f"{code[:4]}.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text()).get(code)
    except Exception:
        return None


def _online() -> bool:
    from ..config import get_settings
    return bool(getattr(get_settings(), "ifsc_refresh", True)) or _transport is not None


def _api(code: str) -> dict[str, Any] | None:
    if not _online():
        return None
    import httpx
    try:
        with httpx.Client(timeout=10, transport=_transport) as c:
            r = c.get(API.format(code=code), headers={"User-Agent": "Hoola/0.59"})
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def lookup(code: str) -> dict[str, Any]:
    code = (code or "").strip().upper().replace(" ", "")
    if not _RE.match(code):
        return {"ifsc": code, "valid": False, "say": "IFSC 11 akshar ka hota hai: 4 bank ke akshar, phir 0, phir 6 (jaise SBIN0001234)."}
    ok = valid(code)
    row = _local(code) or (_api(code) if ok else None)
    out: dict[str, Any] = {"ifsc": code, "valid": ok or bool(row), "bank": bank_name(code)}
    if row:
        out |= {"bank": row.get("BANK") or out["bank"], "branch": row.get("BRANCH"), "address": row.get("ADDRESS"),
                "city": row.get("CITY"), "district": row.get("DISTRICT"), "state": row.get("STATE"), "micr": row.get("MICR"),
                "upi": row.get("UPI"), "neft": row.get("NEFT"), "rtgs": row.get("RTGS"), "imps": row.get("IMPS")}
    if not out["valid"]:
        out["say"] = "Yeh IFSC RBI ki list mein nahi mila — ek baar dobara check kijiye."
    return {k: v for k, v in out.items() if v not in (None, "")}


def refresh() -> int:
    """Downloads the monthly by-bank release into data/ifsc/by-bank (skips if fresher than 25 days)."""
    marker = DATA / "by-bank" / ".fetched"
    if marker.exists() and time.time() - marker.stat().st_mtime < 25 * 86400:
        return 0
    import httpx
    with httpx.Client(timeout=120, follow_redirects=True, transport=_transport) as c:
        r = c.get(RELEASE)
    r.raise_for_status()
    n = 0
    (DATA / "by-bank").mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(r.content), mode="r:gz") as tf:
        for m in tf.getmembers():
            name = Path(m.name).name
            if m.isfile() and re.fullmatch(r"[A-Z0-9]{4}\.json", name):          # only plain bank files, no paths
                f = tf.extractfile(m)
                if f:
                    (DATA / "by-bank" / name).write_bytes(f.read())
                    n += 1
    marker.write_text(str(n))
    return n


def refresh_in_background() -> None:
    import logging
    import threading

    def run():
        time.sleep(90)
        try:
            n = refresh()
            if n:
                logging.getLogger("santosh.ifsc").info("IFSC branch files: %s banks", n)
        except Exception as e:
            logging.getLogger("santosh.ifsc").info("IFSC refresh: %s", e)
    threading.Thread(target=run, daemon=True, name="ifsc-refresh").start()
