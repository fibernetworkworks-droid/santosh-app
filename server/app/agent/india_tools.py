"""v0.59 Tools: `pdf_tools` (merge / pages / rotate / smaller / signature check on the owner's PDFs) and `india_info`
(holidays per state, panchang / tithi / next ekadashi, IFSC, PIN code, rupees in words, lakh format, GSTIN check)."""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from typing import Any

from .tools import Ctx, ToolError

INDIA_TOOLS = [
    {"name": "pdf_tools", "description": (
        "Work on the owner's PDFs (file_id from attached files or made documents): action=merge (file_ids, in order), "
        "pages (pick / reorder pages, pages='1-3,5'), rotate (degrees 90/180/270, optional pages), smaller (shrink photos "
        "inside so it fits WhatsApp / email limits), info, verify (digital signature: who signed, when, changed after "
        "signing?). Makes a NEW file (pc_file card) and returns its file_id; the original stays. Locked (password) PDFs "
        "can't be opened: never ask for the password; tell her to save an unlocked copy from her phone."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["merge", "pages", "rotate", "smaller", "info", "verify"]},
         "file_id": {"type": "string"}, "file_ids": {"type": "array", "items": {"type": "string"}},
         "pages": {"type": "string", "description": "e.g. 1-3,5 or 2-"}, "degrees": {"type": "integer"},
         "name": {"type": "string", "description": "Name for the new file"}},
         "required": ["action"]}},
    {"name": "india_info", "description": (
        "Indian calendar and money facts, offline and exact: action=holidays (year, month, state or city), day (date: "
        "holiday? bank likely closed? + panchang), panchang (date, city: tithi, paksha, nakshatra, amanta month, sunrise), "
        "next (what=ekadashi|purnima|amavasya|sankashti|pradosh|shivratri|chaturthi|ashtami, count), ifsc (code -> bank, "
        "branch, address, UPI/NEFT), pincode (pin -> real or not), words (amount -> rupees in words, lang hinglish|hi|en), "
        "format (amount -> ₹12,34,567 and '12.35 lakh'), gstin (check a GSTIN). Use it instead of web search for these. "
        "Muhurat / rahu kaal are not given (traditions differ)."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["holidays", "day", "panchang", "next", "ifsc", "pincode", "words", "format", "gstin"]},
         "date": {"type": "string", "description": "YYYY-MM-DD (default today); 'kal' = tomorrow"},
         "year": {"type": "integer"}, "month": {"type": "integer"}, "state": {"type": "string"}, "city": {"type": "string"},
         "what": {"type": "string"}, "count": {"type": "integer"}, "code": {"type": "string"},
         "amount": {"type": "number"}, "lang": {"type": "string", "enum": ["hinglish", "hi", "en"]}},
         "required": ["action"]}},
]
INDIA_LABELS = {"pdf_tools": "PDF par kaam kar raha hoon", "india_info": "Calendar / bank dekh raha hoon"}


def _day(s: str) -> date:
    from ..india.days import IST
    today = datetime.now(IST).date()
    s = (s or "").strip().lower()
    if s in ("", "aaj", "today"):
        return today
    if s in ("kal", "tomorrow"):
        return today + timedelta(days=1)
    if s in ("parso",):
        return today + timedelta(days=2)
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        raise ToolError("date YYYY-MM-DD mein dijiye")


def _india(action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..india import days, ifsc, money, pincode
    city, state = a.get("city") or "", a.get("state") or ""
    if action == "holidays":
        d = _day(a.get("date") or "")
        y = int(a.get("year") or d.year)
        items = days.holidays_for(y, state, city, a.get("month"))
        return {"year": y, "state": days.state_code(state, city), "holidays": items[:60],
                "note": "Gazetted + state ki chhutti (holidays library). Bank ki pakki list RBI ki hoti hai."}
    if action == "day":
        return days.day_info(_day(a.get("date") or ""), state, city)
    if action == "panchang":
        return days.panchang(_day(a.get("date") or ""), city)
    if action == "next":
        out = days.next_tithi(a.get("what") or "ekadashi", _day(a.get("date") or ""), int(a.get("count") or 3), city)
        if not out:
            raise ToolError("what = ekadashi | purnima | amavasya | sankashti | pradosh | shivratri | chaturthi | ashtami")
        return {"what": a.get("what") or "ekadashi", "dates": out, "hint": "Chahein to inke reminder laga sakte hain."}
    if action == "ifsc":
        return ifsc.lookup(a.get("code") or "")
    if action == "pincode":
        return pincode.info(a.get("code") or "")
    if action in ("words", "format"):
        if a.get("amount") is None:
            raise ToolError("amount chahiye")
        amt = float(a["amount"])
        return {"amount": amt, "inr": money.inr(amt), "short": money.short(amt),
                "words": money.rupees_words(amt, a.get("lang") or "hinglish"), "words_en": money.rupees_words(amt, "en")}
    if action == "gstin":
        return money.gstin_info(a.get("code") or "")
    raise ToolError("unknown action")


async def india_info(ctx: Ctx, action, **a):
    return await asyncio.to_thread(_india, str(action), a)


def _pdf(ctx: Ctx, action: str, file_id: str, file_ids: list, pages: str, degrees: int, name: str) -> dict[str, Any]:
    from .. import pdftools
    from .make_tools import _deliver, _owner_bytes, _safe
    try:
        if action == "merge":
            ids = [str(x) for x in (file_ids or ([file_id] if file_id else []))][:20]
            files = [_owner_bytes(ctx, x) for x in ids]
            data = pdftools.merge(files)
            base = name or (files[0][0].rsplit(".", 1)[0] + " + " + str(len(files) - 1))
        else:
            if not file_id:
                raise ToolError("file_id chahiye")
            fname, src = _owner_bytes(ctx, str(file_id))
            if action == "info":
                return pdftools.info(src) | {"name": fname}
            if action == "verify":
                return pdftools.verify(src) | {"name": fname}
            if action == "pages":
                data = pdftools.pick(src, pages)
                base = name or f"{fname.rsplit('.', 1)[0]} (pages {pages})"
            elif action == "rotate":
                data = pdftools.rotate(src, int(degrees or 90), pages or "")
                base = name or fname.rsplit(".", 1)[0]
            elif action == "smaller":
                data = pdftools.shrink(src)
                if len(data) >= len(src):
                    return {"name": fname, "size": len(src), "say": "Isse chhoti nahi ho paayi (photos pehle se chhoti hain)."}
                base = name or f"{fname.rsplit('.', 1)[0]} (chhoti)"
            else:
                raise ToolError("action = merge | pages | rotate | smaller | info | verify")
    except pdftools.PdfError as e:
        raise ToolError(str(e))
    view = _deliver(ctx, _safe(base, ".pdf"), data, "pdf_tools")
    out = {"file_id": view.get("file_id"), "name": view.get("name"), "size": len(data)}
    try:
        out["pages"] = pdftools.info(data)["pages"]
    except Exception:
        pass
    return out


async def pdf_tools(ctx: Ctx, action, file_id="", file_ids=None, pages="", degrees=0, name="", **_):
    return await asyncio.to_thread(_pdf, ctx, str(action), str(file_id or ""), list(file_ids or []), str(pages or ""),
                                   int(degrees or 0), str(name or ""))


INDIA_HANDLERS = {"pdf_tools": pdf_tools, "india_info": india_info}
