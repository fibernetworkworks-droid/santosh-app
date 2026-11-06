"""v0.540.0 LEADS card - does the lead generation engine ANSWER her, and do the walls really stand?

Two cards over `app/quality/lead_asks.py`, the mapscard shape:

- free_card(): no model, no network, no key. For every ask: is the right leads tool IN VIEW (admit.plan_for on her
  exact words) and are the six tools REGISTERED and REACHABLE at all (the v0.393 lesson); are the guards PRESENT
  in the code - the provenance gate, the plan-time cap (fired FOR REAL on a huge ask), the unbuilt lanes refused
  by name, the official lanes (P1) actually wired, the consent=False campaign hand-off, the opt-out honouring,
  and an engine whose own service module contains no sending machinery at all. CI pins this card.
- live_card(): ONE real turn per ask on the tenant "__quality__" (never her chats), scored IN CODE. Needs a model;
  without one the rows come back as errors rather than as a pass.

The card never checks a reply against a fact remembered about the world - every "right answer" here is code."""
from __future__ import annotations

import inspect
import json
import logging
import time
from typing import Any

from .lead_asks import ASKS, LEADS_SET_V

log = logging.getLogger("santosh.quality.leads")

LEADS_TOOLS = ("leads_run", "leads_status", "leads_list", "leads_export", "leads_forget", "leads_enrich")


# ---------------------------------------------------------------- the guards (present in the code, fired for real)
def guards_in_code() -> dict[str, Any]:
    from .. import leadscap
    from ..agent import leads_tools
    from ..leads import rules as R
    from ..leads import service as S
    src = inspect.getsource(S)
    src_tools = inspect.getsource(leads_tools)
    out: dict[str, Any] = {}
    # 1. the provenance gate: no source -> no row (the message names it, the add path enforces it)
    out["provenance_gate"] = ("source_url khaali hai" in src and 'source_lane not in R.LANES' in src)
    # 2. the cap refuses AT PLAN TIME - fired FOR REAL on a 50,000-row ask, the number named in the refusal
    try:
        leadscap.check_run("__leadscard__", 50_000)
        out["cap_refuses"] = False
    except leadscap.LeadsCapped as e:
        out["cap_refuses"] = "5,000" in str(e)
    except Exception as e:      # noqa: BLE001 - a card never dies on its own check
        log.info("leadscap check could not run: %s", e)
        out["cap_refuses"] = False
    # 3. an unbuilt lane is refused BY NAME with its phase (no stub, no pretending)
    p = S.plan("__leadscard__", "Nagpur contractors", ["SCRAPE"], "Nagpur")
    out["lane_refused_by_name"] = (not p["ok"]) and "SCRAPE" in json.dumps(p.get("refused_lanes", [])) \
        and "P3" in json.dumps(p.get("why", []), ensure_ascii=False)
    # 3b. v0.541.0: the official lanes are REALLY wired (REGISTRY = IndiaMART MCP, OFFICIAL_API = the existing
    # maps tools) - and the service still holds no second Google client (only maps/indiamart imports, no httpx)
    out["official_lanes_built"] = (R.LANE_BUILT.get("REGISTRY") == "P1" and R.LANE_BUILT.get("OFFICIAL_API") == "P1"
                                   and hasattr(S, "run_indiamart") and hasattr(S, "run_places"))
    out["no_second_google_client"] = "places.googleapis" not in src and "maps.googleapis" not in src
    # 3c. v0.542.0: the P2 enrich pass is REALLY wired, through the EXISTING stack, with the walls in its source
    try:
        from ..leads import enrich as _en
        esrc = inspect.getsource(_en)
        out["enrich_built"] = (hasattr(S, "enrich") and hasattr(_en, "site_pass") and hasattr(_en, "grade_email")
                               and hasattr(_en, "best_email"))
        out["enrich_uses_existing_stack"] = ("scrape_tools" in esrc and "prune" in esrc and "blocked" in esrc
                                             and "httpx" not in esrc and "requests.get" not in esrc
                                             and "aiohttp" not in esrc)   # no second fetch client of any kind
        out["no_smtp_probe"] = ("smtplib" not in esrc.lower() and "aiosmtplib" not in esrc.lower()
                                and "import smtplib" not in esrc)   # no mail-probe library, deliverability via DNS only
        out["email_grade_vocab"] = (R.EMAIL_GRADES == ("pakka", "sadak_tak", "galat")
                                    and hasattr(_en, "DISPOSABLE_DOMAINS"))
        out["enrich_cap_named"] = "LEADS_ENRICH_ROWS_PER_RUN" in inspect.getsource(leads_tools) or \
                                  "enrich_rows_per_run" in src
    except Exception as e:      # noqa: BLE001 - a card never dies on its own check
        log.info("enrich guards could not run: %s", e)
        out["enrich_built"] = False
    # 4. the campaign hand-off pre-fills consent False and writes the ledger; the engine itself never sends
    out["consent_false_handoff"] = "opted_in=False" in src.replace(" ", "") or "opted_in=False" in src
    out["engine_never_sends"] = ("httpx" not in src and "requests.post" not in src and "smtplib" not in src
                                 and "set_whatsapp" not in src)
    out["outreach_is_ledger"] = "kind=\"campaign_list\"" in src or 'kind="campaign_list"' in src
    # 5. forget + opt-out exist and the export honours opt-out by default
    out["forget_exists"] = "def forget(" in src
    out["opt_out_default_export"] = "opt_out: bool | None = False" in src
    # 6. the tool descriptions themselves carry the walls (what the model sees is part of the guard)
    out["tools_carry_never_send"] = "NAHI bhejta" in src_tools or "never" in src_tools.lower()
    # 7. the store boundary is written where a later session would look (the v0.389 trap law)
    out["store_boundary_written"] = bool(R.STORE_BOUNDARY) and "review TEXT" in " ".join(R.STORE_BOUNDARY)
    return out


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
        in_view = [t for t in (a.get("ok") or ()) if t in names]   # rule asks carry a guard, not a tool list
        seen_in_view |= {t for t in LEADS_TOOLS if t in names}
        rows.append({"id": a["id"], "kind": a["kind"], "had_ok": bool(a.get("ok")),
                     "in_view": bool(in_view), "found": in_view, "tools": len(names)})
    missing = [t for t in LEADS_TOOLS if t not in names_all or t not in HANDLERS]
    unreachable = [t for t in LEADS_TOOLS if t not in seen_in_view and t not in missing]
    guards = guards_in_code()
    tool_rows = [r for r in rows if r["had_ok"]]
    return {"kind": "free", "set": LEADS_SET_V, "asks": len(rows),
            "tool_asks": len(tool_rows),
            "right_in_view": sum(r["in_view"] for r in tool_rows), "tools": len(LEADS_TOOLS),
            "registered": len(LEADS_TOOLS) - len(missing), "not_registered": missing,
            "reachable": len(LEADS_TOOLS) - len(missing) - len(unreachable), "unreachable": unreachable,
            "guards_ok": sum(1 for v in guards.values() if v), "guards": guards, "rows": rows}


# ---------------------------------------------------------------- the live card
_LEAD_REFUSE = ("nahi kar sakta", "nahi bhej", "refuse", "refused", "cap", "seema", "limit", "off", "band",
                "P3", "P1", "built nahi", "nahi bana", "ijazat", "allowed nahi", "cannot", "not allowed",
                "consent", "aapke tap", "aapki haan", "purani list", "apna data", "her data", "her_data")


def _score_rule(ask: dict, reply: str, tools: list[str]) -> dict[str, Any]:
    low = str(reply or "").lower()
    g = ask["guard"]
    if g == "cap_refuses":
        ok = any(w in low for w in ("5000", "5,000", "cap", "seema", "limit", "chhota")) and any(
            w in low for w in ("refuse", "nahi", "cannot", "refused"))
        return {"right": ok, "misses": [] if ok else ["did not refuse the 50,000-row ask with the cap named"]}
    if g == "lane_off":
        ok = any(w in low for w in ("off", "band", "P3", "uski haan", "aapki haan", "built nahi", "abhi nahi",
                                    "opt-in", "not built", "not allowed", "scrape nahi"))
        return {"right": ok, "misses": [] if ok else ["did not say the scrape lane is OFF / needs her word (P3)"]}
    if g == "never_sends":
        ok = any(w in low for w in ("nahi bhej", "khud nahi", "engine nahi", "campaign desk", "aapke tap",
                                    "aapki haan", "consent", "list ban gayi", "draft", "not send", "never sends",
                                    "hand-off", "handoff"))
        return {"right": ok, "misses": [] if ok else ["acted as if the engine itself would message the leads"]}
    if g == "official_first":
        ok = any(w in low for w in ("apna data", "her data", "purani", "official", "sarkari", "registry",
                                    "indiamart", "places", "P0", "P1", "pehle"))
        return {"right": ok, "misses": [] if ok else ["did not name the sources ladder (her data first, then official lanes)"]}
    if g == "enrich_smtp":
        ok = any(w in low for w in ("smtp", "probe", "nahi", "not built", "spam", "dns", "mx", "grade"))
        return {"right": ok and "kar dunga" not in low and "kar deta" not in low,
                "misses": [] if ok else ["agreed to SMTP-probe the emails (spam infrastructure, rules.NEVER)"]}
    if g == "enrich_dead_site":
        ok = any(w in low for w in ("dead", "mari", "band", "galat", "nahi khul", "down", "grade", "note",
                                    "record", "crash nahi", "dead_site"))
        return {"right": ok, "misses": [] if ok else ["a dead site must be a recorded result (galat), not a crash"]}
    return {"right": False, "misses": ["unknown guard " + g]}


async def _one(ask: dict, tenant: str) -> dict[str, Any]:
    from ..agent import santosh
    from .hard_card import _Catch, _failed
    from .run import _calls_of, _new_conv
    conv = _new_conv(tenant)
    t0 = time.time()
    catch = _Catch()
    root = logging.getLogger()
    root.addHandler(catch)
    try:
        reply = await santosh.run_turn(conv, ask["text"], tenant_id=tenant)
    except Exception as e:      # noqa: BLE001 - one broken ask is a row, not a dead card
        return {"id": ask["id"], "kind": ask["kind"], "error": str(e)[:200], "right": False}
    finally:
        root.removeHandler(catch)
    if _failed(conv):
        why = [x for x in catch.lines if "error ref" in x or "refused" in x] or catch.lines
        return {"id": ask["id"], "kind": ask["kind"], "right": False,
                "error": (why[-1] if why else (reply or "turn failed"))[:300], "log": catch.lines[-6:], "conv": conv}
    tools = [str(c.get("tool")) for c in _calls_of(conv)]
    if ask["kind"] == "rule":
        row = _score_rule(ask, reply or "", tools)
    else:
        hit = [t for t in tools if t in set(ask["ok"])]
        row = {"right": bool(hit), "misses": [] if hit else [f"used {', '.join(tools[:4]) or 'no tool'}"], "used": hit}
    row.update({"id": ask["id"], "kind": ask["kind"], "tools": tools[:12],
                "leads_tools": [t for t in tools if t in LEADS_TOOLS], "seconds": round(time.time() - t0, 1),
                "reply": (reply or "")[:800], "conv": conv})
    return row


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
    return {"kind": "live", "set": LEADS_SET_V, "asks": len(rows), "planned": len(items), "answered": len(done),
            "right": sum(r["right"] for r in done),
            "tool_right": sum(r["right"] for r in by("tool")), "tool_asks": len(by("tool")),
            "rule_right": sum(r["right"] for r in by("rule")), "rule_asks": len(by("rule")),
            "errors": len(rows) - len(done),
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
    name = f"leadscard-{card['kind']}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    (_dir() / name).write_text(json.dumps(card, ensure_ascii=False, indent=1))
    card["file"] = name
    return card


def saved() -> list[dict]:
    from .run import _dir
    out = []
    for p in sorted(_dir().glob("leadscard-*.json"), reverse=True)[:30]:
        try:
            d = json.loads(p.read_text())
            out.append({"file": p.name, "kind": d.get("kind"), "at": d.get("at"), "label": d.get("label"),
                        "asks": d.get("asks"), "right": d.get("right")})
        except Exception:
            continue
    return out


def lines(card: dict) -> list[str]:
    if card.get("kind") == "free":
        g = card["guards"]
        out = [f"Leads card (free, set v{card['set']}): right tool in view {card['right_in_view']}/{card['asks']}, "
               f"tools registered {card['registered']}/{card['tools']}, "
               f"reachable from a real ask {card['reachable']}/{card['tools']}, guards {card['guards_ok']}/{len(g)}"]
        if card["not_registered"]:
            out.append("  NOT REGISTERED: " + ", ".join(card["not_registered"]))
        if card["unreachable"]:
            out.append("  never in view for any ask: " + ", ".join(card["unreachable"]))
        out += [f"  guard off: {k}" for k, v in g.items() if not v]
        out += [f"  - {r['id']}: no right tool in view" for r in card["rows"] if not r["in_view"]]
        return out
    out = [f"Leads card (live, set v{card['set']}): RIGHT {card['right']}/{card['answered']} "
           f"(tool {card['tool_right']}/{card['tool_asks']}, guards {card['rule_right']}/{card['rule_asks']}), "
           f"errors {card['errors']}"
           + (f", median {card['median_s']} s" if card.get("median_s") is not None else "")]
    first = next((r for r in card["rows"] if "error" in r and r.get("log")), None)
    if first:
        out.append("  first failure, the server's own log lines:")
        out += [f"    | {x}" for x in first["log"]]
    for r in card["rows"]:
        if "error" in r:
            out.append(f"  - {r['id']}: ERROR {r['error']}")
        elif not r["right"]:
            out.append(f"  - {r['id']}: " + "; ".join(r.get("misses") or ["wrong"]))
    return out
