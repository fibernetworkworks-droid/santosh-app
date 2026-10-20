"""Hoola Work Theatre: turns real tool calls into a 3D scene the phone shows while Hoola works.

Every tool call publishes a ``work`` event: {id, tool, scene, phase, label, data}
  phase: start (tool began) · done · waiting (needs the owner's tap) · error
  scene: email · browser · payment · bluetooth · network · pc · work (anything else)
  data:  short, display-only facts taken from the tool's real input / output (senders and subjects, the site, the
         biller and amount, the TV, the other avatar, the PC app and fields). Nothing is invented: a missing fact is
         simply left out and the scene shows its neutral state.

Privacy: data is display text for the owner's own phone, but it is still cut short, stripped of control characters
and any long digit run (account, consumer, card, phone numbers) is masked to its last 4 digits. PIN/OTP/password-like
fields are never copied.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

SCENES = ("email", "browser", "payment", "bluetooth", "network", "pc", "work")
_CTRL = re.compile(r"[\x00-\x1f\x7f​-‏‪-‮⁦-⁩]")
_DIGITS = re.compile(r"\d[\d\s-]{5,}\d")
_SECRET_KEYS = re.compile(r"(^|_)(pin|upi_pin|otp|pass|password|passwd|cvv|token|secret|key|api_key|aadhaar|card|card_number)(_|$)", re.I)
PAY_TOOLS = {"fetch_bill", "pay_bill", "place_order", "send_money", "checkout", "pay"}


def scene_for(tool: str, args: dict[str, Any] | None = None) -> str:
    t = tool or ""
    if t.startswith("email_") or t in ("gmail_check",):
        return "email"
    if t in ("browse_web", "browse_result", "open_website"):
        return "browser"
    if t in ("bluetooth", "tv_remote", "music_control", "ac_control"):
        return "bluetooth"
    if t.startswith("hoola_"):
        return "network"
    if t.startswith("pc_") or t == "tally_report":
        return "pc"
    if t == "bazar_run" and str((args or {}).get("tool", "")) in PAY_TOOLS:
        return "payment"
    return "work"


def _txt(v: Any, n: int = 60) -> str:
    s = _CTRL.sub(" ", str(v or ""))
    s = _DIGITS.sub(lambda m: "••••" + re.sub(r"\D", "", m.group())[-4:], s)
    return re.sub(r"\s+", " ", s).strip()[:n]


def _find(obj: Any, keys: tuple[str, ...], depth: int = 0) -> Any:
    """First value under any of these keys, searching nested dicts/lists (skips secret-looking keys)."""
    if depth > 4:
        return None
    if isinstance(obj, dict):
        for k in keys:
            if k in obj and obj[k] not in (None, "", [], {}):
                return obj[k]
        for k, v in obj.items():
            if _SECRET_KEYS.search(str(k)):
                continue
            r = _find(v, keys, depth + 1)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj[:20]:
            r = _find(v, keys, depth + 1)
            if r is not None:
                return r
    return None


def _rows(obj: Any, depth: int = 0) -> list[dict[str, Any]]:
    """Mail-like rows {from, subject} from a tool result."""
    if depth > 4:
        return []
    if isinstance(obj, list) and obj and isinstance(obj[0], dict) and ("subject" in obj[0] or "from" in obj[0]):
        return [{"from": _txt(i.get("from") or i.get("sender"), 28), "subject": _txt(i.get("subject"), 44),
                 "hot": bool(i.get("important") or i.get("urgent") or i.get("priority") in ("high", "urgent"))}
                for i in obj[:6] if isinstance(i, dict)]
    if isinstance(obj, dict):
        for k, v in obj.items():
            r = _rows(v, depth + 1)
            if r:
                return r
    if isinstance(obj, list):
        for v in obj[:10]:
            r = _rows(v, depth + 1)
            if r:
                return r
    return []


def _money(v: Any) -> str:
    try:
        x = float(str(v).replace(",", "").replace("₹", "").strip())
    except (TypeError, ValueError):
        return _txt(v, 16)
    s = f"{x:,.2f}".rstrip("0").rstrip(".")
    # Indian grouping: 1,23,456
    whole, _, frac = s.partition(".")
    w = whole.replace(",", "")
    if len(w) > 3:
        head, tail = w[:-3], w[-3:]
        head = ",".join([head[max(0, i - 2):i] for i in range(len(head), 0, -2)][::-1])
        w = f"{head},{tail}"
    return "₹" + w + (f".{frac}" if frac else "")


def brief(tool: str, args: dict[str, Any] | None, out: Any = None) -> dict[str, Any]:
    """Display-only facts for the scene, from the real call."""
    a = {k: v for k, v in (args or {}).items() if not _SECRET_KEYS.search(str(k))}
    scene = scene_for(tool, a)
    d: dict[str, Any] = {}
    if scene == "email":
        rows = _rows(out)
        if rows:
            d["rows"] = rows
        total = _find(out, ("total", "count"))
        if isinstance(total, int):
            d["total"] = total
        counts = _find(out, ("counts",))
        if isinstance(counts, dict):
            d["groups"] = {_txt(k, 16): int(v) for k, v in list(counts.items())[:4] if isinstance(v, int)}
        acct = _find(out, ("account",)) or a.get("account")
        if acct:
            d["account"] = _txt(acct, 40)
        if a.get("to"):
            d["to"] = _txt(a.get("to"), 40)
    elif scene == "browser":
        site = a.get("site") or a.get("url") or _find(out, ("url", "site"))
        if site:
            host = urlparse(site if "//" in str(site) else f"https://{site}").hostname or str(site)
            d["url"] = _txt(host, 48)
        if a.get("goal") or a.get("query"):
            d["goal"] = _txt(a.get("goal") or a.get("query"), 70)
        res = _find(out, ("answer", "result", "summary", "message"))
        if isinstance(res, str) and res:
            d["result"] = _txt(res, 70)
        st = _find(out, ("status",))
        if isinstance(st, str):
            d["status"] = _txt(st, 20)
    elif scene == "payment":
        d["action"] = _txt(a.get("tool"), 24)
        biller = _find(out, ("biller", "biller_name", "merchant", "payee", "shop", "pack_name", "name")) or a.get("pack_id")
        if biller:
            d["biller"] = _txt(biller, 32)
        amt = _find(out, ("amount", "total", "bill_amount", "grand_total"))
        if amt is not None:
            d["amount"] = _money(amt)
        due = _find(out, ("due_date", "due"))
        if due:
            d["due"] = _txt(due, 20)
        ref = _find(out, ("consumer_number", "consumer", "account_number", "ca_number"))
        if ref:
            d["ref"] = "••••" + re.sub(r"\D", "", str(ref))[-4:] if re.search(r"\d{4}", str(ref)) else _txt(ref, 20)
    elif scene == "bluetooth":
        d["action"] = _txt(a.get("action") or (a.get("app") and f"open {a.get('app')}") or
                           (a.get("search") and f"search {a.get('search')}") or ",".join(map(str, a.get("keys") or [])), 40)
        if a.get("repeat"):
            d["repeat"] = max(1, min(20, int(a.get("repeat") or 1)))
        dev = a.get("device") or a.get("tv") or _find(out, ("device",))
        if isinstance(dev, dict):
            dev = dev.get("name")
        if dev:
            d["device"] = _txt(dev, 32)
        d["kind"] = {"tv_remote": "tv", "music_control": "speaker", "ac_control": "ac"}.get(tool, "bluetooth")
        devs = _find(out, ("devices",))
        if isinstance(devs, list):
            d["found"] = [_txt(x.get("name"), 24) for x in devs[:5] if isinstance(x, dict)]
    elif scene == "network":
        peer = a.get("to") or a.get("who") or a.get("handle") or _find(out, ("peer", "label", "to", "from"))
        if peer:
            d["peer"] = _txt(peer, 32)
        kind = a.get("kind") or a.get("action")
        if kind:
            d["kind"] = _txt(kind, 20)
    elif scene == "pc":
        if a.get("goal"):
            d["goal"] = _txt(a.get("goal"), 80)
        app = a.get("app") or _find(out, ("app", "window"))
        if app:
            d["app"] = _txt(app, 24)
        d["tally"] = tool == "tally_report" or "tally" in str(a.get("goal", "")).lower()
        fields = _find(out, ("fields",))
        if isinstance(fields, dict):
            d["fields"] = [[_txt(k, 18), _txt(v, 24)] for k, v in list(fields.items())[:5] if not _SECRET_KEYS.search(str(k))]
    if scene in ("work", "payment", "network", "pc", "browser", "bluetooth"):
        msg = _find(out, ("message", "say", "phone"))
        if isinstance(msg, str) and msg and "result" not in d:
            d["note"] = _txt(msg, 70)
    return d


def phase_of(out: Any) -> str:
    if isinstance(out, dict):
        if out.get("needs_approval") or out.get("status") in ("needs_approval", "pending_tap", "waiting"):
            return "waiting"
        if out.get("status") in ("failed", "no_answer"):
            return "error"
    return "done"


def event(call_id: str, tool: str, label: str, phase: str, args: dict[str, Any] | None = None, out: Any = None,
          error: str = "") -> dict[str, Any]:
    ev = {"id": call_id, "tool": tool, "scene": scene_for(tool, args), "phase": phase, "label": _txt(label, 60),
          "data": brief(tool, args, out)}
    if error:
        ev["error"] = _txt(error, 120)
    return ev
