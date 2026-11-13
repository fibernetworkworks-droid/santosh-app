"""v0.877 HOOLA AGENT API - keys, wallet and one tool call.

Laws (each has a test):
  - A key is shown ONCE; only its sha256 is kept. A revoked key, a suspended wallet or a switched-off API = no call.
  - A key acts ONLY as its own company's tenant and ONLY for catalogue tools (and only those the key lists, if it lists any).
  - Money is whole micro-INR. The price is charged BEFORE the tool runs, in one transaction with its ledger row; a failed or
    timed-out call is refunded the same way (one refund per request). The balance can never go below zero.
  - The wallet balance equals the sum of the ledger (`check_invariant`). The ledger is append-only.
  - Arguments and results are never stored: only metadata (tool, status, charge, ms, error code).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from ..aiapps.keys import Limiter
from ..db import now, session
from . import catalog as CAT
from .models import HapiCall, HapiKey, HapiLedger, HapiWallet, ensure_tables

PREFIX = "hk_live_"
MAX_KEYS = 20
BOUNDS = {"rpm": (1, 600), "rph": (1, 50000), "concurrent": (1, 20)}
MAX_ARGS_BYTES = 100_000
MAX_RESULT_CHARS = 200_000
CALL_TIMEOUT_S = 120
LIMITER = Limiter()


class ApiError(Exception):
    """An error the caller sees: HTTP status + a short machine code + a human line."""

    def __init__(self, status: int, code: str, message: str, retry_after: int = 0):
        super().__init__(message)
        self.status, self.code, self.message, self.retry_after = status, code, message, retry_after


@dataclass
class Key:
    id: str
    tenant_id: str
    name: str
    tail: str
    tools: list[str]
    rpm: int
    rph: int
    concurrent: int
    daily_limit_micro: int | None


def enabled() -> bool:
    try:
        from ..config import get_settings
        return bool(getattr(get_settings(), "hoola_api_enabled", False))
    except Exception:       # noqa: BLE001
        return False


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _view(k: HapiKey) -> dict[str, Any]:
    return {"id": k.id, "name": k.name, "tail": k.tail, "revoked": bool(k.revoked), "tools": json.loads(k.tools or "[]"),
            "limits": {"rpm": k.rpm, "rph": k.rph, "concurrent": k.concurrent,
                       "daily_limit_micro_inr": k.daily_limit_micro},
            "last_used": k.last_used_at.isoformat() if k.last_used_at else "",
            "created": k.created_at.isoformat() if k.created_at else ""}


def _bound(name: str, v: Any, default: int) -> int:
    lo, hi = BOUNDS[name]
    try:
        n = int(default if v is None else v)
    except (TypeError, ValueError):
        raise ApiError(400, "invalid_request", f"{name} must be a whole number ({lo}-{hi}).")
    if n < lo or n > hi:
        raise ApiError(400, "invalid_request", f"{name} must be between {lo} and {hi}.")
    return n


# ---------------------------------------------------------------- keys (portal side)
def create_key(tenant: str, name: str = "", tools: Any = None, rpm: Any = None, rph: Any = None, concurrent: Any = None,
               daily_limit_inr: Any = None) -> dict[str, Any]:
    ensure_tables()
    allowed = [] if tools in (None, "", []) else tools
    if not isinstance(allowed, list) or any(not isinstance(t, str) for t in allowed):
        raise ApiError(400, "invalid_request", "tools must be a list of tool names (or empty for every catalogue tool).")
    bad = [t for t in allowed if t not in CAT.CATALOG]
    if bad:
        raise ApiError(400, "invalid_request", f"Not in the Hoola API catalogue: {', '.join(bad[:5])}.")
    cap = None
    if daily_limit_inr not in (None, ""):
        try:
            cap = int(round(float(daily_limit_inr) * CAT.INR))
        except (TypeError, ValueError):
            raise ApiError(400, "invalid_request", "daily_limit_inr must be a number.")
        if cap < 0:
            raise ApiError(400, "invalid_request", "daily_limit_inr cannot be negative.")
    key = PREFIX + secrets.token_urlsafe(32)
    with session() as s:
        n = s.query(HapiKey).filter(HapiKey.tenant_id == tenant, HapiKey.revoked.is_(False)).count()
        if n >= MAX_KEYS:
            raise ApiError(409, "too_many_keys", f"You already have {MAX_KEYS} keys; revoke one first.")
        k = HapiKey(tenant_id=tenant, name=str(name or "API key").strip()[:80] or "API key", key_hash=_hash(key),
                    tail=key[-4:], tools=json.dumps(sorted(set(allowed))), rpm=_bound("rpm", rpm, 60),
                    rph=_bound("rph", rph, 2000), concurrent=_bound("concurrent", concurrent, 5), daily_limit_micro=cap)
        s.add(k)
        s.flush()
        out = _view(k)
    return {**out, "key": key, "says": "Copy this key now - it is shown only once. Hoola keeps only a fingerprint of it."}


def list_keys(tenant: str) -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        rows = s.query(HapiKey).filter(HapiKey.tenant_id == tenant).order_by(HapiKey.created_at.desc()).all()
        return [_view(k) for k in rows]


def revoke_key(tenant: str, kid: str) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        k = s.get(HapiKey, kid)
        if k is None or k.tenant_id != tenant:
            raise ApiError(404, "not_found", "That key was not found.")
        k.revoked = True
        out = _view(k)
    LIMITER.forget(kid)
    return {**out, "says": f"Key ...{out['tail']} is revoked; calls with it now fail."}


def resolve(token: str) -> Key:
    """A presented bearer token -> its Key, or ApiError 401 (unknown / revoked) / 403 (wallet suspended)."""
    ensure_tables()
    token = str(token or "").strip()
    if not token.startswith(PREFIX) or len(token) > 120:
        raise ApiError(401, "invalid_api_key", "Missing, unknown or revoked Hoola API key.")
    with session() as s:
        k = s.query(HapiKey).filter(HapiKey.key_hash == _hash(token)).first()
        if k is None or k.revoked:
            raise ApiError(401, "invalid_api_key", "Missing, unknown or revoked Hoola API key.")
        w = s.get(HapiWallet, k.tenant_id)
        if w is not None and w.suspended:
            raise ApiError(403, "account_suspended", "This account is suspended. Contact Hoola.")
        k.last_used_at = now()
        return Key(k.id, k.tenant_id, k.name, k.tail, json.loads(k.tools or "[]"), k.rpm, k.rph, k.concurrent,
                   k.daily_limit_micro)


# ---------------------------------------------------------------- wallet + ledger
def _wallet(s, tenant: str) -> HapiWallet:
    w = s.get(HapiWallet, tenant)
    if w is None:
        w = HapiWallet(tenant_id=tenant, balance_micro=0)
        s.add(w)
        s.flush()
    return w


def balance(tenant: str) -> dict[str, Any]:
    ensure_tables()
    with session() as s:
        w = _wallet(s, tenant)
        return {"balance_micro_inr": int(w.balance_micro), "balance_inr": w.balance_micro / CAT.INR,
                "suspended": bool(w.suspended)}


def credit(tenant: str, amount_micro: int, type_: str, ref_type: str, ref_id: str, note: str = "") -> dict[str, Any]:
    """Add money (topup / refund / adjustment +). One row per (type, ref): repeating the same event changes nothing."""
    ensure_tables()
    if not isinstance(amount_micro, int) or isinstance(amount_micro, bool) or amount_micro <= 0:
        raise ApiError(400, "invalid_request", "amount must be a positive whole number of micro-INR.")
    try:
        with session() as s:
            w = _wallet(s, tenant)
            w.balance_micro = int(w.balance_micro) + amount_micro
            s.add(HapiLedger(tenant_id=tenant, type=type_, amount_micro=amount_micro, balance_after_micro=w.balance_micro,
                             ref_type=ref_type, ref_id=ref_id, note=note[:200]))
            s.flush()
            return {"applied": True, "balance_micro_inr": int(w.balance_micro)}
    except IntegrityError:
        return {"applied": False, "balance_micro_inr": int(balance(tenant)["balance_micro_inr"]),
                "says": "That event was already recorded; nothing changed."}


def _debit(tenant: str, amount_micro: int, ref_id: str) -> int:
    """Take the price: ONE atomic conditional update + its ledger row in the same transaction. Returns the new balance."""
    with session() as s:
        _wallet(s, tenant)
        res = s.execute(update(HapiWallet).where(HapiWallet.tenant_id == tenant, HapiWallet.balance_micro >= amount_micro,
                                                 HapiWallet.suspended.is_(False))
                        .values(balance_micro=HapiWallet.balance_micro - amount_micro))
        if res.rowcount == 0:
            raise ApiError(402, "insufficient_balance", "Not enough balance in the wallet for this call. Top up and retry.")
        bal = int(s.scalar(select(HapiWallet.balance_micro).where(HapiWallet.tenant_id == tenant)))
        s.add(HapiLedger(tenant_id=tenant, type="charge", amount_micro=-amount_micro, balance_after_micro=bal,
                         ref_type="request", ref_id=ref_id))
        return bal


def ledger(tenant: str, limit: int = 100) -> list[dict[str, Any]]:
    ensure_tables()
    with session() as s:
        rows = (s.query(HapiLedger).filter(HapiLedger.tenant_id == tenant).order_by(HapiLedger.id.desc())
                .limit(max(1, min(int(limit or 100), 500))).all())
        return [{"id": r.id, "type": r.type, "amount_micro_inr": int(r.amount_micro),
                 "balance_after_micro_inr": int(r.balance_after_micro), "ref": f"{r.ref_type}:{r.ref_id}", "note": r.note,
                 "at": r.created_at.isoformat()} for r in rows]


def check_invariant(tenant: str) -> dict[str, Any]:
    """balance == sum of the ledger. A mismatch is a critical alert in production."""
    ensure_tables()
    with session() as s:
        bal = int(_wallet(s, tenant).balance_micro)
        total = int(s.scalar(select(func.coalesce(func.sum(HapiLedger.amount_micro), 0))
                             .where(HapiLedger.tenant_id == tenant)) or 0)
    return {"ok": bal == total, "balance_micro_inr": bal, "ledger_sum_micro_inr": total}


# ---------------------------------------------------------------- usage
def _spent_today(key_id: str) -> int:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    with session() as s:
        return int(s.scalar(select(func.coalesce(func.sum(HapiCall.charged_micro), 0))
                            .where(HapiCall.key_id == key_id, HapiCall.created_at >= start)) or 0)


def usage(tenant: str, days: int = 7) -> dict[str, Any]:
    ensure_tables()
    days = max(1, min(int(days or 7), 90))
    since = datetime.now(timezone.utc) - timedelta(days=days)
    with session() as s:
        rows = s.query(HapiCall).filter(HapiCall.tenant_id == tenant, HapiCall.created_at >= since).all()
        by: dict[str, dict[str, int]] = {}
        for r in rows:
            b = by.setdefault(r.name, {"calls": 0, "failed": 0, "charged_micro_inr": 0})
            b["calls"] += 1
            b["failed"] += 1 if r.status != "ok" else 0
            b["charged_micro_inr"] += int(r.charged_micro)
        recent = sorted(rows, key=lambda r: r.created_at, reverse=True)[:50]
        return {"days": days, "calls": len(rows), "charged_micro_inr": sum(v["charged_micro_inr"] for v in by.values()),
                "by_tool": by,
                "recent": [{"id": r.id, "tool": r.name, "status": r.status, "charged_micro_inr": int(r.charged_micro),
                            "ms": r.ms, "error": r.error_code, "at": r.created_at.isoformat()} for r in recent]}


def _log(k: Key, rid: str, name: str, status: str, charged: int, ms: int, code: str = "") -> None:
    try:
        with session() as s:
            s.add(HapiCall(id=rid, tenant_id=k.tenant_id, key_id=k.id, name=name[:60], status=status, charged_micro=charged,
                           ms=ms, error_code=code[:40]))
    except Exception:       # noqa: BLE001 - a log failure must never lose a settled call
        pass


# ---------------------------------------------------------------- one call
def _clean(out: Any) -> Any:
    """Make a tool result JSON-safe and bounded."""
    text = json.dumps(out, default=str, ensure_ascii=False)
    if len(text) > MAX_RESULT_CHARS:
        return {"truncated": True, "text": text[:MAX_RESULT_CHARS]}
    return json.loads(text)


def _validate_args(name: str, args: Any) -> dict[str, Any]:
    if args is None:
        args = {}
    if not isinstance(args, dict):
        raise ApiError(400, "invalid_request", "arguments must be a JSON object.")
    if len(json.dumps(args, default=str)) > MAX_ARGS_BYTES:
        raise ApiError(413, "request_too_large", "arguments are too large.")
    schema = (CAT.schemas().get(name) or {}).get("input_schema") or {}
    try:
        import jsonschema
        jsonschema.validate(args, schema)
    except ImportError:     # pragma: no cover
        pass
    except Exception as e:  # noqa: BLE001 - jsonschema.ValidationError
        raise ApiError(400, "invalid_request", f"arguments do not match the tool's schema: {str(e).splitlines()[0][:200]}")
    return args


async def call_tool(k: Key, name: str, args: Any) -> dict[str, Any]:
    """Run one catalogue tool as the key's company. Raises ApiError; on success returns the result + the charge."""
    if not enabled():
        raise ApiError(503, "api_disabled", "The Hoola API is not switched on yet.")
    if name not in CAT.CATALOG or name not in CAT.schemas():
        raise ApiError(404, "tool_not_found", f"No such tool in the Hoola API: {name}.")
    if k.tools and name not in k.tools:
        raise ApiError(403, "tool_not_allowed", "This key is not allowed to use that tool.")
    args = _validate_args(name, args)
    price = CAT.prices()[name]
    if k.daily_limit_micro is not None and await asyncio.to_thread(_spent_today, k.id) + price > k.daily_limit_micro:
        raise ApiError(429, "daily_limit_reached", "This key's daily spend limit is reached.")
    rid = "hr_" + uuid.uuid4().hex[:16]
    t0 = time.monotonic()
    from ..aiapps.keys import LimitError
    try:
        with LIMITER.call(k):
            charged = price
            if price:
                try:
                    await asyncio.to_thread(_debit, k.tenant_id, price, rid)
                except ApiError:
                    await asyncio.to_thread(_log, k, rid, name, "rejected", 0, 0, "insufficient_balance")
                    raise
            try:
                from ..agent import tools as T
                ctx = T.Ctx(tenant_id=k.tenant_id, conversation_id="", actor="api:" + k.id)
                out = await asyncio.wait_for(T.dispatch(name, args, ctx), timeout=CALL_TIMEOUT_S)
                result = _clean(out)
                if isinstance(result, dict) and (result.get("error") or result.get("ok") is False
                                                 or result.get("status") == "waiting_owner"):
                    # the house rule: ok False = the tool did not do the job -> the customer is not charged
                    raise T.ToolError(str(result.get("error") or result.get("say") or result.get("note")
                                          or "the tool could not do this")[:300])
            except Exception as e:      # noqa: BLE001 - any failure of the tool = the customer is not charged
                if price:
                    await asyncio.to_thread(credit, k.tenant_id, price, "refund", "request", rid, f"{name} failed")
                ms = int((time.monotonic() - t0) * 1000)
                code = "timeout" if isinstance(e, asyncio.TimeoutError) else "tool_error"
                await asyncio.to_thread(_log, k, rid, name, "failed", 0, ms, code)
                raise ApiError(504 if code == "timeout" else 502, code,
                               ("The tool took too long." if code == "timeout" else f"The tool failed: {str(e)[:200]}")
                               + " You were not charged.")
    except LimitError as e:
        raise ApiError(429, "rate_limited", str(e), e.retry_after)
    ms = int((time.monotonic() - t0) * 1000)
    await asyncio.to_thread(_log, k, rid, name, "ok", charged, ms)
    return {"request_id": rid, "tool": name, "result": result, "charged_micro_inr": charged, "charged_inr": charged / CAT.INR}
