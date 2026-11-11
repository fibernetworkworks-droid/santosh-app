"""v0.470 Phase 11 PROOF - the MAPS card: does the Google Maps work ANSWER her, and what did each answer cost?

Two cards over `app/quality/maps_asks.py`, the same shape as the tool / hard / coding cards:

- free_card(): no model, no Google, no key. For every ask: is a right maps tool IN VIEW and is a wrong family kept
  out; is every one of the 20 maps / listing / own-map tools REACHABLE at all (registered AND brought into view by
  some real ask - the v0.393 lesson: green tests never prove a feature can be reached); are the licence / money
  guards present in the code; and what would one answer COST, from mapsbill's own price list. CI can pin it.
- live_card(): ONE real turn per ask on the tenant "__quality__" (never her chats), scored IN CODE, with the RUPEES
  each answer really spent read from mapsbill before and after the turn. Needs a real Maps key and a model; without
  them the rows come back as errors rather than as a pass.

The geo answers are COMPUTED here from the coordinates the ask itself carries (the same haversine the server uses),
so this card never checks a reply against a fact remembered about the world.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from .maps_asks import ASKS, MAPS_SET_V

log = logging.getLogger("santosh.quality.maps")

# The whole Maps surface after Phases 1-10. A name here that is not registered, or that no ask can reach, is a
# finding - that is the point of the list.
MAPS_TOOLS = ("maps_search", "maps_directions", "maps_navigate", "maps_nearby", "maps_place", "maps_nearest",
              "maps_address_check", "maps_pata", "maps_route_plan", "maps_links", "maps_snap", "maps_kharcha",
              "solar_check", "gbp_locations", "gbp_numbers",
              "ownmap_import", "ownmap_list", "ownmap_near", "ownmap_pin", "ownmap_delete")

# What one answer of each kind spends, as SKUs. Priced by mapsbill, never by a number typed here.
SKUS: dict[str, tuple[str, ...]] = {}


def _skus() -> dict[str, tuple[str, ...]]:
    global SKUS
    if SKUS:
        return SKUS
    from .. import mapsbill as B
    SKUS = {
        "maps_search": (B.SKU_TEXT_ENT,), "maps_nearby": (B.SKU_NEARBY_PRO,), "maps_place": (B.SKU_DETAILS_ENT,),
        "maps_directions": (B.SKU_GEOCODE, B.SKU_GEOCODE, B.SKU_ROUTES), "maps_navigate": (B.SKU_GEOCODE,),
        "maps_nearest": (B.SKU_GEOCODE, B.SKU_MATRIX), "maps_route_plan": (B.SKU_GEOCODE, B.SKU_OPT),
        "maps_address_check": (B.SKU_ADDRESS_ENT,), "maps_pata": (B.SKU_GEOCODE,),
        "maps_links": (B.SKU_GEOCODE, B.SKU_STREETVIEW_META), "maps_snap": (B.SKU_ROADS,),
        "solar_check": (B.SKU_GEOCODE, B.SKU_SOLAR), "maps_kharcha": (), "gbp_locations": (), "gbp_numbers": (),
        "ownmap_import": (), "ownmap_list": (), "ownmap_near": (B.SKU_GEOCODE,), "ownmap_pin": (B.SKU_GEOCODE,),
        "ownmap_delete": (),
    }
    return SKUS


def price_of(tool: str, n: int = 1) -> dict[str, Any]:
    """What one call of this tool costs at the full rate, from mapsbill's own table (the free monthly allowance is
    deliberately ignored here: a card that prints 0 while the allowance lasts would hide the real bill)."""
    from .. import mapsbill as B
    skus = _skus().get(tool, ())
    inr = 0.0
    for s in skus:
        inr += B.price_inr(s, n * (10 if s == B.SKU_MATRIX else 1))      # the matrix bills per element: 10 candidates
    return {"tool": tool, "skus": list(skus), "inr": round(inr, 4),
            "assumed": [s for s in skus if s in B.ASSUMED_TIER], "unsourced": [s for s in skus if s in B.unsourced()]}


# ---------------------------------------------------------------- the answer key, computed (never remembered)
def _km(a: dict, b: dict) -> float:
    from .. import maps
    return maps._km({"lat": a["lat"], "lng": a["lng"]}, {"lat": b["lat"], "lng": b["lng"]})


def key_for(ask: dict) -> dict[str, Any]:
    """The right answer to a geo ask, worked out from the ask's own coordinates."""
    if ask["kind"] != "geo":
        return {}
    src = ask["from"]
    d = sorted(((round(_km(src, p), 1), p["name"]) for p in ask["points"]))
    if ask["check"] == "nearest":
        return {"want": [d[0][1]], "not": [n for _, n in d[1:]], "km": {n: k for k, n in d}}
    if ask["check"] == "within":
        r = float(ask["radius_km"])
        return {"want": [n for k, n in d if k <= r], "not": [n for k, n in d if k > r], "km": {n: k for k, n in d}}
    if ask["check"] == "order":
        return {"order": [n for _, n in d], "km": {n: k for k, n in d}}
    if ask["check"] == "km":
        return {"km_want": round(_km(src, ask["points"][0]), 1), "km": {n: k for k, n in d}}
    return {}


def _score_geo(ask: dict, reply: str) -> dict[str, Any]:
    key, low = key_for(ask), str(reply or "").lower()
    misses = []
    if ask["check"] == "km":
        from .hard_card import numbers
        want = key["km_want"]
        ok = any(abs(f - want) <= max(2.0, want * 0.03) for f in numbers(reply or ""))   # 3% or 2 km
        return {"right": ok, "misses": [] if ok else [f"distance not within 3% of {want} km"], "key": want}
    if ask["check"] == "order":
        at = [(low.find(n.lower()), n) for n in key["order"]]
        if any(i < 0 for i, _ in at):
            misses.append("missing " + ", ".join(n for i, n in at if i < 0))
        elif [n for _, n in sorted(at)] != key["order"]:
            misses.append("wrong order: said " + " > ".join(n for _, n in sorted(at)))
        return {"right": not misses, "misses": misses, "key": key["order"]}
    for n in key["want"]:
        if n.lower() not in low:
            misses.append(f"did not name {n}")
    # a wrong one claimed as the answer: it appears and the right one does not, or (nearest) it is called the closest
    for n in key["not"]:
        if n.lower() in low and ask["check"] == "within":
            misses.append(f"included {n} (outside the radius)")
    return {"right": not misses, "misses": misses, "key": key["want"]}


# ---------------------------------------------------------------- the guards (licence + money)
_LEAD_WORDS = ("nahi de sakta", "nahi kar sakta", "nahi bana sakta", "allowed nahi", "ijazat nahi", "terms",
               "licence", "license", "cannot", "not allowed", "mana", "refus")
_LINK_WORDS = ("google.com/maps", "maps.google", "link")
_PLAN_WORDS = ("aapki haan", "aap tay", "assign nahi", "sirf plan", "proposed", "propose", "tay nahi kiya",
               "aapke tap", "confirm")


def guards_in_code() -> dict[str, Any]:
    """Is each guard PRESENT in the code (free)? Whether she really gets it is the live card's job."""
    import inspect

    from .. import maps, mapsbill
    from ..agent import maps_tools, prompts
    out: dict[str, Any] = {}
    src_tools = inspect.getsource(maps_tools)
    src_maps = inspect.getsource(maps)
    # 1. no exportable list of businesses: the rule rides in the tool result AND in the prompt she is answered from
    src_prompt = inspect.getsource(prompts)
    out["refuse_lead_list"] = ("never save" in src_tools.lower()
                               and "never save maps results as a list" in src_prompt.lower())
    # 2. a map NEVER becomes a stored picture: no static-map or Street View image URL exists anywhere in maps.py
    out["link_not_picture"] = ("staticmap" not in src_maps and "streetview?" not in src_maps
                               and "streetview/metadata" in src_maps and "view_link" in src_maps)
    # 3. the day's plan only proposes
    out["plan_proposes_only"] = "PROPOSED" in src_tools and "nothing was assigned" in src_tools
    # 4. a place with no solar imagery is reported, not filled in
    out["solar_not_covered"] = '"covered": False' in src_maps and ("andaza nahi" in src_tools.lower() or "will not guess" in src_tools.lower())
    # 5. the cap refuses BEFORE spending - the only guard that can be proved by running it here
    before = mapsbill.would_exceed("__mapscard__", mapsbill.SKU_TEXT_ENT, 1)
    out["cap_refuses"] = (not before) and _cap_fires()
    return out


def _cap_fires() -> bool:
    """With the day's room spent and the free allowance gone, does charge() REFUSE instead of overspending?"""
    from .. import mapsbill
    try:
        mapsbill.ensure_tables()
        free = dict(mapsbill._FREE_INDIA)
        mapsbill._FREE_INDIA[mapsbill.SKU_TEXT_ENT] = 0
        try:
            from ..config import get_settings
            st = get_settings()
            cap, st.maps_daily_inr = st.maps_daily_inr, 0.0001
            try:
                mapsbill.charge("__mapscard__", mapsbill.SKU_TEXT_ENT, 1_000_000)
                return False                      # it spent: the guard is gone
            except mapsbill.MapsCapped:
                return True
            finally:
                st.maps_daily_inr = cap
        finally:
            mapsbill._FREE_INDIA.clear()
            mapsbill._FREE_INDIA.update(free)
    except Exception as e:          # noqa: BLE001 - a card never dies on its own check
        log.info("maps card cap check could not run: %s", e)
        return False


def _score_rule(ask: dict, reply: str, tools: list[str]) -> dict[str, Any]:
    low = str(reply or "").lower()
    g = ask["guard"]
    if g == "refuse_lead_list":
        ok = any(w in low for w in _LEAD_WORDS)
        return {"right": ok, "misses": [] if ok else ["did not refuse the exportable list, or did not say why"]}
    if g == "link_not_picture":
        ok = any(w in low for w in _LINK_WORDS)
        return {"right": ok, "misses": [] if ok else ["no Google Maps link offered"]}
    if g == "plan_proposes_only":
        ok = any(w in low for w in _PLAN_WORDS)
        return {"right": ok, "misses": [] if ok else ["did not say the order is only a proposal / needs her yes"]}
    if g == "solar_not_covered":
        ok = ("solar_check" in tools) and ("nahi" in low or "not covered" in low or "data" in low)
        return {"right": ok, "misses": [] if ok else ["did not ask Google, or filled in a roof it has no data for"]}
    if g == "cap_refuses":
        ok = any(w in low for w in ("budget", "kharch", "cap", "seema", "limit"))
        return {"right": ok, "misses": [] if ok else ["did not name the budget as the reason"]}
    return {"right": False, "misses": ["unknown guard " + g]}


# ---------------------------------------------------------------- the free card
def free_card(asks: list[dict] | None = None) -> dict[str, Any]:
    from ..agent import admit
    from ..agent.tools import HANDLERS, TOOLS
    from ..config import get_settings
    st = get_settings()
    names_all = {t["name"] for t in TOOLS}
    rows, seen_in_view = [], set()
    for a in asks or ASKS:
        plan = admit.plan_for(a["text"], st)
        names = {t["name"] for t in plan.specs()} if plan else names_all
        fams = set(plan.families) if plan else {"*"}
        in_view = [t for t in a["ok"] if t in names]
        seen_in_view |= {t for t in MAPS_TOOLS if t in names}
        pr = price_of(a["ok"][0])
        rows.append({"id": a["id"], "kind": a["kind"], "in_view": bool(in_view), "found": in_view,
                     "wrong": [f for f in a.get("bad") or () if f in fams], "tools": len(names),
                     "inr": pr["inr"], "skus": pr["skus"], "assumed": pr["assumed"]})
    missing = [t for t in MAPS_TOOLS if t not in names_all or t not in HANDLERS]
    unreachable = [t for t in MAPS_TOOLS if t not in seen_in_view and t not in missing]
    guards = guards_in_code()
    n = len(rows)
    return {"kind": "free", "set": MAPS_SET_V, "asks": n,
            "right_in_view": sum(r["in_view"] for r in rows), "wrong_loaded": sum(bool(r["wrong"]) for r in rows),
            "tools": len(MAPS_TOOLS), "registered": len(MAPS_TOOLS) - len(missing), "not_registered": missing,
            "reachable": len(MAPS_TOOLS) - len(missing) - len(unreachable), "unreachable": unreachable,
            "guards_ok": sum(1 for v in guards.values() if v), "guards": guards,
            "inr_all_asks": round(sum(r["inr"] for r in rows), 2),
            "dearest": sorted(({"id": r["id"], "inr": r["inr"]} for r in rows), key=lambda x: -x["inr"])[:3],
            "rows": rows}


# ---------------------------------------------------------------- the live card
async def _one(ask: dict, tenant: str) -> dict[str, Any]:
    from .. import mapsbill
    from ..agent import santosh
    from .hard_card import _Catch, _failed
    from .run import _calls_of, _new_conv
    conv = _new_conv(tenant)
    before = mapsbill.usage(tenant)["inr"]
    t0 = time.time()
    catch = _Catch()
    root = logging.getLogger()
    root.addHandler(catch)
    try:
        reply = await santosh.run_turn(conv, ask["text"], tenant_id=tenant)
    except Exception as e:      # noqa: BLE001 - one broken ask is a row, not a dead card
        return {"id": ask["id"], "kind": ask["kind"], "error": str(e)[:200], "right": False, "inr": 0.0}
    finally:
        root.removeHandler(catch)
    spent = round(mapsbill.usage(tenant)["inr"] - before, 4)
    if _failed(conv):
        why = [x for x in catch.lines if "error ref" in x or "refused" in x] or catch.lines
        return {"id": ask["id"], "kind": ask["kind"], "right": False, "inr": spent,
                "error": (why[-1] if why else (reply or "turn failed"))[:300], "log": catch.lines[-6:], "conv": conv}
    tools = [str(c.get("tool")) for c in _calls_of(conv)]
    if ask["kind"] == "geo":
        row = _score_geo(ask, reply or "")
    elif ask["kind"] == "rule":
        row = _score_rule(ask, reply or "", tools)
    else:
        hit = [t for t in tools if t in a_ok(ask)]
        row = {"right": bool(hit), "misses": [] if hit else [f"used {', '.join(tools[:4]) or 'no tool'}"], "used": hit}
    row.update({"id": ask["id"], "kind": ask["kind"], "inr": spent, "tools": tools[:20],
                "maps_tools": [t for t in tools if t in MAPS_TOOLS], "seconds": round(time.time() - t0, 1),
                "reply": (reply or "")[:1000], "conv": conv})
    return row


def a_ok(ask: dict) -> set[str]:
    return set(ask["ok"]) | set(ask.get("also") or ())


async def live_card(asks: list[dict] | None = None, tenant: str = "") -> dict[str, Any]:
    from .run import TENANT
    items = asks or ASKS
    rows: list[dict] = []
    for a in items:
        rows.append(await _one(a, tenant or TENANT))
        if len(rows) >= 3 and all("error" in r for r in rows):
            break                     # three dead turns: print the cause, do not waste the rest
    done = [r for r in rows if "error" not in r]
    by = lambda k: [r for r in done if r["kind"] == k]   # noqa: E731
    return {"kind": "live", "set": MAPS_SET_V, "asks": len(rows), "planned": len(items), "answered": len(done),
            "right": sum(r["right"] for r in done),
            "geo_right": sum(r["right"] for r in by("geo")), "geo_asks": len(by("geo")),
            "tool_right": sum(r["right"] for r in by("tool")), "tool_asks": len(by("tool")),
            "rule_right": sum(r["right"] for r in by("rule")), "rule_asks": len(by("rule")),
            "errors": len(rows) - len(done), "inr": round(sum(r.get("inr", 0.0) for r in rows), 4),
            "inr_per_answer": round(sum(r.get("inr", 0.0) for r in done) / len(done), 4) if done else None,
            "median_s": sorted(r["seconds"] for r in done)[len(done) // 2] if done else None, "rows": rows}


# ---------------------------------------------------------------- picking, saving, printing
def pick(only: str = "", limit: int = 0, kind: str = "") -> list[dict]:
    items = [a for a in ASKS if not kind or a["kind"] == kind]
    if only:
        want = {x.strip() for x in only.split(",") if x.strip()}
        items = [a for a in items if a["id"] in want]
    return items[:limit] if limit else items


def save(card: dict, label: str = "") -> dict:
    from .run import _dir
    card = {**card, "label": label, "at": int(time.time())}
    name = f"mapscard-{card['kind']}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    (_dir() / name).write_text(json.dumps(card, ensure_ascii=False, indent=1))
    card["file"] = name
    return card


def saved() -> list[dict]:
    from .run import _dir
    out = []
    for p in sorted(_dir().glob("mapscard-*.json"), reverse=True)[:30]:
        try:
            d = json.loads(p.read_text())
            out.append({"file": p.name, "kind": d.get("kind"), "at": d.get("at"), "label": d.get("label"),
                        "asks": d.get("asks"), "right": d.get("right"), "inr": d.get("inr")})
        except Exception:
            continue
    return out


def lines(card: dict) -> list[str]:
    if card.get("kind") == "free":
        g = card["guards"]
        out = [f"Maps card (free, set v{card['set']}): right tool in view {card['right_in_view']}/{card['asks']}, "
               f"wrong family loaded {card['wrong_loaded']}, tools registered {card['registered']}/{card['tools']}, "
               f"reachable from a real ask {card['reachable']}/{card['tools']}, guards {card['guards_ok']}/{len(g)}, "
               f"one of every answer would cost about Rs {card['inr_all_asks']} at full rate"]
        if card["not_registered"]:
            out.append("  NOT REGISTERED: " + ", ".join(card["not_registered"]))
        if card["unreachable"]:
            out.append("  never in view for any ask: " + ", ".join(card["unreachable"]))
        out += [f"  guard off: {k}" for k, v in g.items() if not v]
        out += [f"  - {r['id']}: no right tool in view (ok: {', '.join(x for x in r['skus']) or 'free'})"
                for r in card["rows"] if not r["in_view"]]
        out += [f"  - {r['id']}: wrong family in view: {', '.join(r['wrong'])}" for r in card["rows"] if r["wrong"]]
        out.append("  dearest answers: " + ", ".join(f"{d['id']} Rs {d['inr']}" for d in card["dearest"]))
        return out
    out = [f"Maps card (live, set v{card['set']}): RIGHT {card['right']}/{card['answered']} "
           f"(geo {card['geo_right']}/{card['geo_asks']}, tool {card['tool_right']}/{card['tool_asks']}, "
           f"guards {card['rule_right']}/{card['rule_asks']}), errors {card['errors']}, spent Rs {card['inr']}"
           + (f", Rs {card['inr_per_answer']} an answer" if card.get("inr_per_answer") is not None else "")
           + (f", median {card['median_s']} s" if card.get("median_s") is not None else "")]
    if card.get("planned") and card["planned"] > card["asks"]:
        out.append(f"  STOPPED after {card['asks']} of {card['planned']}: every turn failed")
    first = next((r for r in card["rows"] if "error" in r and r.get("log")), None)
    if first:
        out.append("  first failure, the server's own log lines:")
        out += [f"    | {x}" for x in first["log"]]
    for r in card["rows"]:
        if "error" in r:
            out.append(f"  - {r['id']}: ERROR {r['error']}")
        elif not r["right"]:
            out.append(f"  - {r['id']}: " + "; ".join(r.get("misses") or ["wrong"]) + f" (Rs {r.get('inr', 0)})")
    return out
