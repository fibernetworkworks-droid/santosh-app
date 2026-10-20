"""v0.59 A bill photo / PDF -> a bill card: who it is from, amount, due date, consumer no., bill no.

Text comes from the PDF itself, MarkItDown or OCR (app/ocr.py). invoice2data (MIT) runs our templates in
app/billtemplates/ (electricity: MSEDCL, Tata Power, Adani, BEST, BESCOM, TNEB, BSES, Goa; telecom: BSNL, Jio, Airtel,
Vi; gas: MGL, IGL, MNGL; plus a generic one for any bill with the usual labels). A new layout the templates don't know
falls back to the generic labels; the avatar can still read the full text itself.
Read only: the card offers a reminder before the due date; paying stays with the owner (Bazar bill pay / her own app).
"""
from __future__ import annotations

import logging
import re
import tempfile
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

log = logging.getLogger("santosh.bills")
logging.getLogger("invoice2data").setLevel(logging.CRITICAL)      # "Failed to parse field" for every missing label
TEMPLATES = Path(__file__).parent / "billtemplates"
BILL_WORDS = re.compile(r"(?i)bill|invoice|amount\s+(?:payable|due)|due\s+date|consumer|देय|बिल")


@lru_cache(maxsize=1)
def _templates() -> dict[str, Any]:
    from invoice2data.extract.loader import read_templates
    out = {}
    for t in read_templates(str(TEMPLATES)):
        out[t["template_name"].rsplit(".", 1)[0]] = t
    return out


def _which(text: str) -> str:
    for key, t in _templates().items():
        m = t.get("match") or ""
        if key != "generic" and m and re.search(m, text):
            return key
    return "generic"


def _iso(v: Any) -> str | None:
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d")
    return None


def parse(text: str) -> dict[str, Any] | None:
    """{biller, kind, amount, due_date, bill_date, consumer_no, bill_no, days_left, template} or None (not a bill)."""
    text = (text or "")[:20000]
    if len(text) < 30 or not BILL_WORDS.search(text):
        return None
    try:
        from invoice2data import extract_data
        from invoice2data.input import text as text_input
    except Exception as e:          # library missing: the avatar still reads the text itself
        log.info("invoice2data: %s", e)
        return None
    key = _which(text)
    out: dict[str, Any] = {}
    for k in ([key, "generic"] if key != "generic" else ["generic"]):
        tpl = _templates().get(k)
        if not tpl:
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(text)
            path = f.name
        try:
            out = extract_data(path, templates=[tpl], input_module=text_input) or {}
        except Exception as e:
            log.info("bill parse %s: %s", k, e)
            out = {}
        finally:
            Path(path).unlink(missing_ok=True)
        if out.get("amount"):
            break
    if not out.get("amount"):
        return None
    due = _iso(out.get("date_due"))
    bill = {"biller": out.get("issuer") if key != "generic" else "", "kind": out.get("kind") or "other",
            "amount": round(float(out["amount"]), 2), "due_date": due, "bill_date": _iso(out.get("date")),
            "consumer_no": re.sub(r"[\s\-]", "", str(out.get("consumer_no") or "")) or None,
            "bill_no": str(out.get("invoice_number") or "").upper() or None, "template": key}
    if due:
        bill["days_left"] = (date.fromisoformat(due) - date.today()).days
    from .india.money import inr
    bill["say"] = (f"{bill['biller'] or 'Bill'}: {inr(bill['amount'])}" + (f", aakhri tareekh {due}" if due else "") +
                   (" (aaj aakhri din hai)" if due and bill["days_left"] == 0 else
                    f" ({bill['days_left']} din baaki)" if due and bill["days_left"] > 0 else
                    " (tareekh nikal chuki hai)" if due else "") + ".")
    bill["next"] = ("Due date se 2 din pehle reminder laga sakte hain (create_reminder). Payment owner khud karegi "
                    "(Bazar bill pay ya apna app); Hoola paise nahi bhejta.")
    return {k: v for k, v in bill.items() if v not in (None, "")}
