"""F11 of docs/FINANCE_GLOBAL_PLAN.md - Digital Assets (employee 18; tool `digital_assets`), for a person up to a crypto firm, any country.

  gains        crypto gains from her buys, sells, swaps (a swap = a sale of one coin and a buy of the other at the value of the day),
               income received in coins (staking, airdrops, pay) and fees paid in coins; transfers between her own wallets are not
               sales. Matched by HER country's method (from memory - check this): GB same day / 30 days / pool, US first in first out
               (no wash-sale rule for crypto), IN first in first out with losses not set off, DE first in first out with coins held
               more than a year marked exempt, AU first in first out with the 12-month line, CA average cost with superficial losses.
               The tax itself is not worked out.
  wallet       an address checked before money is sent: its shape for the chain, the Bitcoin checksum, an address made to look like
               one she uses (poisoning), and the signs of a wallet-draining request in a message.
  stablecoin   accepting payment in a stablecoin: the coin amount for an invoice at HER rate, and a price that has left its peg.
  reserve      a stablecoin's reserve against the coins in circulation: coverage, the assets outside HER eligible list, concentration.
  custody      a custodian's books against the wallet balances she pastes: client ledger totals per coin against what the wallets
               hold, the shortfall or surplus, and each client's line.
  travel_rule  a transfer checked for the originator and beneficiary details required above HER threshold.
  token_dd     a token's due-diligence checks: supply held by the top wallets, a mint authority still open, an audit, locks.
  surveillance trades checked for self-trades, round trips between linked accounts, and volume far above the coin's own normal.
  returns      the counts a licensing return asks for, from her own transactions by type and period.

Hoola never holds a key, signs or sends a transaction. Not financial or tax advice."""
from __future__ import annotations

import hashlib
import re
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .. import laws as L
from . import investments as IV


class DigitalError(ValueError):
    pass


ZERO = Decimal(0)
NOT_CONFIRMED = " (from memory - not confirmed, check this)"
NEVER = "Hoola never holds a key, signs or sends a transaction: you do, from your own wallet."

CRYPTO = {
    "GB": {"method": "uk_share_id", "name": "same day, then 30 days, then the pool - as for shares"},
    "US": {"method": "fifo", "rule_days": 0, "name": "first in, first out; the wash-sale rule does not apply to crypto", "long_months": 12},
    "IN": {"method": "fifo", "rule_days": 0, "name": "first in, first out; a loss is not set off against a gain", "no_loss_offset": True},
    "DE": {"method": "fifo", "rule_days": 0, "name": "first in, first out; coins held more than a year are exempt", "exempt_months": 12},
    "AU": {"method": "fifo", "rule_days": 0, "name": "first in, first out; the discount may apply when held at least 12 months",
           "long_months": 12},
    "CA": {"method": "average", "name": "average cost (adjusted cost base) with the superficial-loss rule"},
}


def _n(v: Any, what: str, lo: float | None = None) -> Decimal:
    try:
        x = Decimal(str(v).replace(",", "").strip())
    except Exception:
        raise DigitalError(f"{what}: a number.")
    if not x.is_finite():
        raise DigitalError(f"{what}: a number.")
    if lo is not None and x < Decimal(str(lo)):
        raise DigitalError(f"{what}: not below {lo}.")
    return x


def money(x: Decimal) -> float:
    return float(Decimal(x).quantize(Decimal("0.01"), ROUND_HALF_UP))


# ---- gains -------------------------------------------------------------------------------------------------------------------

def _to_trades(events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    trades, income, transfers = [], [], 0
    for i, e in enumerate(events):
        t = str(e.get("type") or "").lower()
        d = str(e.get("date") or "")[:10]
        if t == "transfer":
            transfers += 1
            continue
        asset = str(e.get("asset") or "").upper()
        qty = _n(e.get("qty"), f"events[{i}].qty", 0)
        val = _n(e.get("value"), f"events[{i}].value (in your currency, on the day)", 0)
        if qty <= 0:
            raise DigitalError(f"events[{i}].qty: more than 0.")
        price = val / qty
        if t in ("buy", "income"):
            trades.append({"date": d, "side": "buy", "qty": qty, "price": price, "symbol": asset})
            if t == "income":
                income.append({"date": d, "asset": asset, "qty": float(qty), "value": money(val), "kind": e.get("kind") or "income"})
        elif t in ("sell", "fee"):
            trades.append({"date": d, "side": "sell", "qty": qty, "price": price, "symbol": asset})
        elif t == "swap":
            gq = _n(e.get("get_qty"), f"events[{i}].get_qty", 0)
            ga = str(e.get("get_asset") or "").upper()
            if not ga or gq <= 0:
                raise DigitalError(f"events[{i}]: a swap needs get_asset and get_qty.")
            trades.append({"date": d, "side": "sell", "qty": qty, "price": price, "symbol": asset})
            trades.append({"date": d, "side": "buy", "qty": gq, "price": val / gq, "symbol": ga})
        else:
            raise DigitalError(f"events[{i}].type: buy | sell | swap | income | fee | transfer.")
    return trades, income, transfers


def gains(a: dict[str, Any]) -> dict[str, Any]:
    country = str(a.get("country") or "").upper()
    rule = CRYPTO.get(country)
    if not rule and not a.get("method"):
        raise DigitalError("country: " + ", ".join(CRYPTO) + " - or method: fifo | average | uk_share_id (yours).")
    trades, income, transfers = _to_trades(a.get("events") or [])
    if not trades:
        raise DigitalError("events: [{date, type buy|sell|swap|income|fee|transfer, asset, qty, value, get_asset, get_qty}].")
    args = {"trades": trades, "method": a.get("method") or rule["method"]}
    if a.get("method"):
        pass
    elif "rule_days" in rule:
        args["rule_days"] = rule["rule_days"]
    else:
        args["country"] = country
        args.pop("method")
    r = IV.lots(args)
    rule = rule or {}
    for d in r["disposals"]:
        for p in d.get("parts") or []:
            acq = p.get("acquired")
            if not acq:
                continue
            held_long = date.fromisoformat(d["date"]) > IV._months_after(date.fromisoformat(acq), 12)
            if rule.get("exempt_months"):
                p["exempt"] = held_long
            if rule.get("long_months"):
                p["term"] = "long" if held_long else "short"
    counted = []
    for d in r["disposals"]:
        g = Decimal(str(d["gain"]))
        if rule.get("exempt_months") and d.get("parts"):
            g = sum((Decimal(str(p["gain"])) for p in d["parts"] if not p.get("exempt")), ZERO)
        counted.append(g)
    pos = sum((g for g in counted if g > 0), ZERO)
    neg = sum((g for g in counted if g < 0), ZERO)
    out = {"country": country or None, "method_from": "your method" if a.get("method") else rule.get("name", "") + NOT_CONFIRMED,
           "disposals": r["disposals"], "holdings": r["holdings"], "gains": money(pos), "losses": money(neg),
           "net": money(pos if rule.get("no_loss_offset") else pos + neg), "income": income,
           "income_total": money(sum((Decimal(str(x["value"])) for x in income), ZERO)), "own_transfers_ignored": transfers,
           "tax": "The tax on these gains and on the income is not worked out here: it needs your rate."}
    if rule.get("no_loss_offset"):
        out["note"] = "Losses are listed but not taken off the gains" + NOT_CONFIRMED
    if rule.get("exempt_months"):
        out["exempt_gain"] = money(sum((Decimal(str(p["gain"])) for d in r["disposals"] for p in d.get("parts") or [] if p.get("exempt")), ZERO))
    return out


# ---- wallet safety -----------------------------------------------------------------------------------------------------------

_B32 = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def _bech32_ok(addr: str) -> bool:
    s = addr.lower()
    if "1" not in s:
        return False
    hrp, data = s.rsplit("1", 1)
    if not data or any(c not in _B32 for c in data):
        return False
    vals = [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp] + [_B32.index(c) for c in data]
    gen = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for v in vals:
        b = chk >> 25
        chk = (chk & 0x1ffffff) << 5 ^ v
        for k in range(5):
            chk ^= gen[k] if ((b >> k) & 1) else 0
    return chk in (1, 0x2bc830a3)        # bech32 (v0) or bech32m (v1+)


_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _b58check_ok(addr: str) -> bool:
    n = 0
    for c in addr:
        if c not in _B58:
            return False
        n = n * 58 + _B58.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    raw = b"\x00" * (len(addr) - len(addr.lstrip("1"))) + raw
    if len(raw) < 5:
        return False
    body, chk = raw[:-4], raw[-4:]
    return hashlib.sha256(hashlib.sha256(body).digest()).digest()[:4] == chk


def _shape(addr: str, chain: str) -> tuple[bool, str]:
    if chain == "bitcoin":
        if addr.lower().startswith("bc1"):
            return _bech32_ok(addr), "bech32 checksum"
        if re.fullmatch(r"[13][1-9A-HJ-NP-Za-km-z]{25,34}", addr):
            return _b58check_ok(addr), "base58 checksum"
        return False, "not a Bitcoin address shape"
    if chain in ("ethereum", "evm", "polygon", "bsc", "base", "arbitrum"):
        return bool(re.fullmatch(r"0x[0-9a-fA-F]{40}", addr)), "0x + 40 hex (the mixed-case checksum is not checked here)"
    if chain == "tron":
        return bool(re.fullmatch(r"T[1-9A-HJ-NP-Za-km-z]{33}", addr)) and _b58check_ok(addr), "base58 checksum"
    if chain == "solana":
        return bool(re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", addr)), "base58, 32-44 characters"
    raise DigitalError("chain: bitcoin | ethereum (or another EVM chain) | tron | solana.")


_DRAIN = [(r"\b(seed|recovery) phrase\b|\b(12|24)[- ]word\b|\bprivate key\b", "asks for a seed phrase or private key: never share it"),
          (r"\b(approve|approval|setapprovalforall|permit|unlimited)\b", "asks you to approve spending: check the amount and the contract"),
          (r"\b(airdrop|claim (your|free))\b", "a free airdrop or claim link"),
          (r"\b(validate|sync|rectify|migrate) (your )?wallet\b", "asks you to 'validate' or 'sync' a wallet"),
          (r"\b(support|admin).{0,25}(dm|direct message|telegram|whatsapp)\b", "'support' reaching out in a private message"),
          (r"\b(double|guaranteed|giveaway)\b", "a giveaway or doubling promise")]


def wallet(a: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    addr = str(a.get("address") or "").strip()
    if addr:
        ok, how = _shape(addr, str(a.get("chain") or "").lower())
        out["address"] = {"valid_shape": ok, "checked": how}
        look = []
        for k in a.get("known") or []:
            k = str(k).strip()
            if k and k != addr and k[:4].lower() == addr[:4].lower() and k[-4:].lower() == addr[-4:].lower():
                look.append(k)
        out["looks_like_yours_but_is_not"] = look
        if look:
            out["warning"] = "This address starts and ends like one you use but is different: it may be a poisoning address."
    if a.get("message"):
        out["signs"] = [why for rx, why in _DRAIN if re.search(rx, str(a["message"]), re.I)]
    if not out:
        raise DigitalError("address + chain (and known: the addresses you use) or message.")
    out["never"] = NEVER
    return out


def stablecoin(a: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if a.get("invoice") is not None:
        inv = _n(a["invoice"], "invoice", 0)
        rate = _n(a.get("rate"), "rate (your currency per coin, yours)", 0)
        if rate <= 0:
            raise DigitalError("rate: above 0.")
        fee = _n(a.get("network_fee") or 0, "network_fee (in coins)", 0)
        coins = inv / rate
        out["payment"] = {"coins": float(coins.quantize(Decimal("0.000001"), ROUND_HALF_UP)), "with_fee": float((coins + fee).quantize(Decimal("0.000001"), ROUND_HALF_UP))}
    if a.get("prices"):
        peg = _n(a.get("peg") or 1, "peg", 0)
        tol = _n(a.get("tolerance_pct") or 0.5, "tolerance_pct", 0)
        off = [{"at": p.get("at"), "price": float(_n(p.get("price"), "prices.price", 0)),
                "off_pct": money((_n(p.get("price"), "price", 0) - peg) / peg * 100)} for p in a["prices"]]
        out["peg"] = {"off_peg": [x for x in off if abs(x["off_pct"]) > float(tol)], "tolerance_pct": float(tol)}
    if not out:
        raise DigitalError("invoice + rate, or prices.")
    return out


def reserve(a: dict[str, Any]) -> dict[str, Any]:
    supply = _n(a.get("supply"), "supply (coins in circulation)", 0)
    eligible = {str(x).lower() for x in a.get("eligible") or []}
    if not eligible:
        raise DigitalError("eligible: the asset types your rules allow in the reserve (e.g. cash, tbill_3m, reverse_repo).")
    total = good = ZERO
    bad, by_holder = [], defaultdict(lambda: ZERO)
    for i, r in enumerate(a.get("assets") or []):
        v = _n(r.get("value"), f"assets[{i}].value", 0)
        total += v
        by_holder[str(r.get("held_at") or "-")] += v
        if str(r.get("type") or "").lower() in eligible:
            good += v
        else:
            bad.append({"type": r.get("type"), "value": money(v)})
    conc = [{"held_at": k, "pct": money(v / total * 100)} for k, v in by_holder.items()] if total else []
    lim = _n(a["max_per_holder_pct"], "max_per_holder_pct", 0) if a.get("max_per_holder_pct") is not None else None
    return {"supply": money(supply), "reserve": money(total), "eligible_reserve": money(good),
            "coverage_pct": money(good / supply * 100) if supply else None, "fully_backed": good >= supply,
            "shortfall": money(supply - good) if good < supply else 0.0, "not_eligible": bad, "by_holder": conc,
            "over_holder_limit": [c["held_at"] for c in conc if lim is not None and c["pct"] > float(lim)]}


def custody(a: dict[str, Any]) -> dict[str, Any]:
    led = defaultdict(lambda: ZERO)
    per = defaultdict(list)
    for i, r in enumerate(a.get("ledger") or []):
        coin = str(r.get("asset") or "").upper()
        q = _n(r.get("qty"), f"ledger[{i}].qty")
        led[coin] += q
        per[coin].append({"client": r.get("client"), "qty": float(q)})
    chain = defaultdict(lambda: ZERO)
    for i, w in enumerate(a.get("wallets") or []):
        chain[str(w.get("asset") or "").upper()] += _n(w.get("balance"), f"wallets[{i}].balance", 0)
    rows = []
    for c in sorted(set(led) | set(chain)):
        d = chain[c] - led[c]
        rows.append({"asset": c, "clients_are_owed": float(led[c]), "wallets_hold": float(chain[c]), "difference": float(d),
                     "status": "short" if d < 0 else "surplus" if d > 0 else "matched"})
    neg = [{"asset": c, **x} for c, xs in per.items() for x in xs if x["qty"] < 0]
    return {"assets": rows, "short": [r["asset"] for r in rows if r["status"] == "short"], "negative_client_lines": neg,
            "says": "A shortfall means the wallets hold less than clients are owed: it is an incident, not a rounding."}


TR_FIELDS = {"originator_name", "originator_account", "beneficiary_name", "beneficiary_account"}
TR_FULL = {"originator_address_or_id"}


def travel_rule(a: dict[str, Any]) -> dict[str, Any]:
    thr = _n(a.get("threshold"), "threshold (your rule, in your currency)", 0)
    out = []
    for i, t in enumerate(a.get("transfers") or []):
        v = _n(t.get("value"), f"transfers[{i}].value", 0)
        need = set(TR_FIELDS) | (TR_FULL if v >= thr else set())
        miss = sorted(k for k in need if not str(t.get(k) or "").strip())
        out.append({"id": t.get("id"), "value": money(v), "above_threshold": v >= thr, "missing": miss, "ok": not miss})
    return {"transfers": out, "held": [x["id"] for x in out if not x["ok"]],
            "from": "FATF Recommendation 16 shape; your country's rule decides the fields and the threshold" + NOT_CONFIRMED}


def token_dd(a: dict[str, Any]) -> dict[str, Any]:
    flags = []
    supply = _n(a["supply"], "supply", 0) if a.get("supply") is not None else None
    top = a.get("top_holders") or []
    if supply and top:
        share = sum((_n(h.get("qty"), "top_holders.qty", 0) for h in top[:10]), ZERO) / supply * 100
        lim = _n(a.get("max_top10_pct") or 50, "max_top10_pct", 0)
        if share > lim:
            flags.append(f"the top 10 wallets hold {money(share)}% of the supply (your limit {float(lim)}%)")
    for k, msg in (("mint_authority_open", "new tokens can still be minted"), ("freeze_authority_open", "holders' tokens can be frozen"),
                   ("upgradeable", "the contract can be changed by its owner")):
        if a.get(k):
            flags.append(msg)
    for k, msg in (("audited", "no audit report named"), ("team_known", "the team is not known by name"),
                   ("liquidity_locked", "the trading liquidity is not locked")):
        if a.get(k) is False:
            flags.append(msg)
    return {"flags": flags, "level": "high" if len(flags) >= 3 else "some" if flags else "none found",
            "says": "Checks on what you gave; the token's own documents and contract decide."}


def _ts(s: Any) -> datetime:
    try:
        return datetime.fromisoformat(str(s).replace("Z", ""))
    except ValueError:
        raise DigitalError("time: as YYYY-MM-DDTHH:MM.")


def surveillance(a: dict[str, Any]) -> dict[str, Any]:
    links = defaultdict(set)
    for grp in a.get("linked") or []:
        for x in grp:
            links[str(x)] |= {str(y) for y in grp}
    trades = a.get("trades") or []
    self_t, rounds = [], []
    win = timedelta(minutes=int(_n(a.get("window_minutes") or 30, "window_minutes", 0)))
    parsed = [{**t, "_t": _ts(t.get("time")), "buyer": str(t.get("buyer")), "seller": str(t.get("seller"))} for t in trades]
    for t in parsed:
        if t["buyer"] == t["seller"] or t["seller"] in links.get(t["buyer"], set()):
            self_t.append(t.get("id"))
    for i, x in enumerate(parsed):
        for y in parsed[i + 1:]:
            if y["_t"] - x["_t"] > win:
                continue
            if x.get("asset") == y.get("asset") and x["buyer"] == y["seller"] and x["seller"] == y["buyer"] and x["buyer"] != x["seller"]:
                rounds.append([x.get("id"), y.get("id")])
    vol = defaultdict(lambda: defaultdict(lambda: ZERO))
    for t in parsed:
        vol[str(t.get("asset"))][t["_t"].date()] += _n(t.get("qty"), "trades.qty", 0)
    spikes = []
    mult = _n(a.get("spike_multiple") or 5, "spike_multiple", 1)
    for asset, days in vol.items():
        ds = sorted(days)
        for k, d in enumerate(ds):
            prior = [days[x] for x in ds[max(0, k - 7):k]]
            if len(prior) >= 3 and statistics.median(prior) > 0 and days[d] > mult * Decimal(statistics.median(prior)):
                spikes.append({"asset": asset, "date": d.isoformat(), "volume": float(days[d]), "usual": float(statistics.median(prior))})
    return {"self_trades": self_t, "round_trips": rounds, "volume_spikes": spikes,
            "says": "Alerts to look at, not findings: a person decides whether anything is reported."}


def returns(a: dict[str, Any]) -> dict[str, Any]:
    per = str(a.get("period") or "quarter")
    out = defaultdict(lambda: defaultdict(lambda: {"count": 0, "value": ZERO}))
    for i, t in enumerate(a.get("transactions") or []):
        d = date.fromisoformat(str(t.get("date"))[:10])
        key = f"{d.year}-Q{(d.month - 1) // 3 + 1}" if per == "quarter" else f"{d.year}-{d.month:02d}"
        x = out[key][str(t.get("type") or "other")]
        x["count"] += 1
        x["value"] += _n(t.get("value") or 0, f"transactions[{i}].value", 0)
    return {"periods": {p: {k: {"count": v["count"], "value": money(v["value"])} for k, v in sorted(t.items())} for p, t in sorted(out.items())}}


ACTIONS = ("gains", "wallet", "stablecoin", "reserve", "custody", "travel_rule", "token_dd", "surveillance", "returns", "methods")
_KEYISH = re.compile(r"sign|send|transfer|withdraw|broadcast|swap_now|buy|sell|place|order|execute|import_key|seed|private_key|stake_now|bridge")


def run(tenant: str, action: str, a: dict[str, Any], actor: str = "owner") -> dict[str, Any]:
    a = dict(a)
    if _KEYISH.search(str(action).lower()):
        raise L.Refused("move_money", NEVER)
    for k in a:
        if re.search(r"seed|mnemonic|private_?key|secret", str(k), re.I):
            raise DigitalError("Never give Hoola a seed phrase or a private key: nothing here needs one.")
    if action == "methods":
        out = {"methods": CRYPTO, "from": "Hoola's table" + NOT_CONFIRMED}
    elif action in ACTIONS:
        out = globals()[action](a)
    else:
        raise DigitalError("action: " + ", ".join(ACTIONS))
    out.setdefault("not_advice", L.NOT_ADVICE)
    return out
