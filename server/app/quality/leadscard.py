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
def _blocked_mod():
    from ..crawl import blocked as _b
    return _b


def _claudemd_amended() -> bool:
    """The plan's non-negotiable: the rule-text amendment rides the commit that builds the lane. The card reads
    the repo's CLAUDE.md (both layouts: server/ subdir or flat) and demands the amended sentence present AND
    the old blanket ban gone. The needles are wrap-tolerant (whitespace-collapsed) - editors re-wrap, the rule
    text itself may not move."""
    from pathlib import Path
    here = Path(__file__).resolve()
    for cand in (here.parents[3] / "CLAUDE.md", here.parents[2] / "CLAUDE.md"):
        if cand.exists():
            try:
                flat = " ".join(cand.read_text(encoding="utf-8", errors="ignore").split())
            except Exception:        # noqa: BLE001
                return False
            return ("A LEADS scrape lane for PUBLIC BUSINESS LISTING DATA is allowed BY THE OWNER'S EXPLICIT ASK"
                    in flat
                    and "opt-in per tenant and OFF by default" in flat
                    and "Official routes only: no scraping, no unofficial MCP" not in flat)
    return False


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
    # 3. an unbuilt lane is refused BY NAME with its phase (no stub, no pretending). v0.543.0: the by-name
    # witness was VENDOR (P4). v0.544.0: VENDOR is BUILT - the plan section 4 sources ladder is COMPLETE - so
    # the refusal witness becomes an UNKNOWN lane name (still refused by name, "koi lane hi nahi hai"), and a
    # new guard proves the ladder itself: every lane name is built, nothing left promising a later phase.
    p = S.plan("__leadscard__", "Nagpur contractors", ["BOGUS_LANE"], "Nagpur")
    out["lane_refused_by_name"] = (not p["ok"]) and "BOGUS_LANE" in json.dumps(p.get("refused_lanes", []))
    out["ladder_complete"] = (set(R.LANE_BUILT) == set(R.LANES) and not R.LANE_ARRIVES
                              and all(R.LANE_BUILT.get(l) for l in R.LANES))
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
    # 3d. v0.543.0: the P3 SCRAPE lane is REALLY wired - and the walls the amended rule names are in the code
    try:
        from ..leads import grid as _grid, gmaps_parse as _gp, scrape as _sc
        gpsrc, scsrc, gsrc = inspect.getsource(_gp), inspect.getsource(_sc), inspect.getsource(_grid)
        out["scrape_built"] = (R.LANE_BUILT.get("SCRAPE") == "P3" and hasattr(S, "run_scrape")
                               and hasattr(S, "set_scrape_optin") and hasattr(_gp, "places")
                               and hasattr(_grid, "bbox_cells") and hasattr(_grid, "choose_zoom"))
        out["scrape_opt_in_default_off"] = (not S.scrape_opted_in("__leadscard__")
                                            and hasattr(_sc, "GOOGLE_MIN_INTERVAL"))
        out["scrape_optin_refused"] = True
        p2 = S.plan("__leadscard__", "Nagpur contractors", ["SCRAPE"], "Nagpur")
        out["scrape_optin_refused"] = (not p2["ok"]) and "OFF" in json.dumps(p2.get("why", []), ensure_ascii=False) \
            and "opt-in" in json.dumps(p2.get("why", []), ensure_ascii=False).lower()
        out["scrape_uses_existing_stack"] = ("scrape_tools" in scsrc and "_guard_url" in scsrc and "_fetch" in scsrc
                                             and "httpx" not in scsrc and "requests.get" not in scsrc
                                             and "aiohttp" not in scsrc and "playwright" not in scsrc.lower())
        out["scrape_politeness"] = (_sc.GOOGLE_MIN_INTERVAL >= 1.0 and _sc.MAX_CONCURRENCY == 2
                                    and "robots" in scsrc and "_polite" in scsrc)
        out["scrape_faces_public_site"] = ("maps/search" in gpsrc and
                                           "googleapis" not in gpsrc + scsrc + gsrc)   # public website, never the API
        out["scrape_abort_on_block"] = ("why_blocked" in src and "ABORTED" in src
                                        and "blocked" in inspect.getsource(_blocked_mod()))
        out["scrape_store_boundary"] = ("IDX_REVIEW_COUNT" in gpsrc and "review text" in gpsrc.lower()
                                        and "STORE_BOUNDARY" in gpsrc)   # the parser's own wall, in its source
        out["rule_text_amended"] = _claudemd_amended()
    except Exception as e:      # noqa: BLE001 - a card never dies on its own check
        log.info("scrape guards could not run: %s", e)
        out["scrape_built"] = False
    # 3e. v0.544.0: the P4 VENDOR lane is REALLY wired (config-gated, priced before the run) and the SCALE
    # half is real too (the graph fan-out enrich + the honest store-backend answer)
    try:
        from ..leads import vendor as _vd, scale as _scale
        from types import SimpleNamespace as _NS
        vsrc = inspect.getsource(_vd)
        out["vendor_built"] = (R.LANE_BUILT.get("VENDOR") == "P4" and hasattr(S, "run_vendor")
                               and hasattr(_vd, "search") and hasattr(_vd, "contract"))
        # the gate fired FOR REAL on the default settings: no vendor named -> refusal names the exact config
        p3 = S.plan("__leadscard__", "Nagpur contractors", ["VENDOR"], "Nagpur")
        ok_now, ready = p3.get("ok"), p3.get("ok") and "vendor" in p3
        out["vendor_gate_holds"] = ((not ok_now and "LEADS_VENDOR_" in json.dumps(p3.get("why", []),
                                                                        ensure_ascii=False))
                                     or ready)   # configured env: the card proves the gate passed cleanly
        # the PRICE gate fired FOR REAL on a fake settings object (price 0 -> no ceiling possible)
        fst = _NS(leads_vendor_name="acme-leads", leads_vendor_base_url="https://api.acme.example",
                  leads_vendor_api_key="k", leads_vendor_price_per_row_inr=0.0,
                  leads_vendor_run_cap_inr=2000.0, leads_vendor_terms_ack="acme-leads")
        okp, whyp, kindp = _vd.check("__leadscard__", 100, fst)
        out["vendor_price_named"] = (not okp and kindp == "config"
                                     and "LEADS_VENDOR_PRICE_PER_ROW_INR" in whyp)
        # the RUN-CAP gate fired FOR REAL: 20,000 x Rs 0.5 = Rs 10,000 > Rs 1,000 cap -> refused at plan time
        fst2 = _NS(leads_vendor_name="acme-leads", leads_vendor_base_url="https://api.acme.example",
                   leads_vendor_api_key="k", leads_vendor_price_per_row_inr=0.5,
                   leads_vendor_run_cap_inr=1000.0, leads_vendor_terms_ack="acme-leads")
        okc, whyc, kindc = _vd.check("__leadscard__", 20_000, fst2)
        out["vendor_cap_named"] = (not okc and kindc == "cap" and "LEADS_VENDOR_RUN_CAP_INR" in whyc)
        # the vendor's rows obey the SAME provenance law: a row without its own source_url is refused
        out["vendor_provenance_required"] = ("source_url" in json.dumps(_vd.contract())
                                             and 'raw.get("source_url")' in src)
        out["vendor_cost_honest"] = ("cost_reported_by_vendor" in src and "reported" in vsrc
                                     and "ESTIMATE" in vsrc)   # vendor-reported vs estimate, said on the bill
        # SCALE: the fan-out walk is the HOOLA GRAPH (static fan-out edges + join barrier + bounded in-flight)
        ssrc = inspect.getsource(_scale)
        out["enrich_fanout_built"] = ("fanout" in inspect.signature(S.enrich).parameters
                                      and "StateGraph" in ssrc and "add_edge" in ssrc and "Semaphore" in ssrc
                                      and "join" in ssrc)
        out["store_backend_named"] = (_scale.store_backend()["engine"] in ("sqlite", "postgresql")
                                      and "country_scale" in json.dumps(_scale.store_backend()))
    except Exception as e:      # noqa: BLE001 - a card never dies on its own check
        log.info("vendor guards could not run: %s", e)
        out["vendor_built"] = False
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
    if g == "vendor_off":
        ok = any(w in low for w in ("vendor", "configure", "config", "terms", "price", "key", "cap", "ceiling",
                                    "set", "nahi", "refuse", "refused", "pehle", "naam"))
        return {"right": ok and "kar dunga" not in low and "bhej dunga" not in low,
                "misses": [] if ok else ["acted as if a vendor run could start with no vendor configured"]}
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
