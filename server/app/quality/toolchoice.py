"""v0.242 SAHI AUZAAR - the tool-choice card: does Hoola pick the RIGHT tool for each ask?

Two cards over app/quality/tool_asks.py:
- router_card(): free, no model - for every ask, is a right tool IN VIEW and is a wrong family kept out?
- live_card(): ONE real brain call per ask with exactly what a chat turn sends (the slim guide of the routed families
  + the routed tool list); the FIRST tool it asks for is scored. Nothing runs: the tool_use is read, never dispatched,
  so no mail, card, job or charge ever comes out of it. A tool_search pick is followed once (what it would open).
`python -m app.quality tools [--live] [--brain claude|glm]`; GET /api/quality/tools shows the saved cards.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from .tool_asks import ASKS, TOOL_SET_V

log = logging.getLogger("santosh.quality.tools")


def _dir():
    from .run import _dir as d
    return d()


def router_card(asks: list[dict] | None = None) -> dict[str, Any]:
    from ..agent import admit
    from ..agent.tools import TOOLS
    from ..config import get_settings
    st = get_settings()
    rows = []
    for a in asks or ASKS:
        plan = admit.plan_for(a["text"], st)
        names = {t["name"] for t in plan.specs()} if plan else {t["name"] for t in TOOLS}
        fams = set(plan.families) if plan else {"*"}
        seen = [t for t in a["ok"] if t in names]
        wrong = [f for f in a.get("bad") or () if f in fams]
        rows.append({"id": a["id"], "in_view": bool(seen), "wrong": wrong, "tools": len(names),
                     "why": dict(getattr(plan, "why", {}) or {})})
    n = len(rows)
    return {"kind": "router", "set": TOOL_SET_V, "asks": n,
            "right_in_view": sum(r["in_view"] for r in rows), "wrong_loaded": sum(bool(r["wrong"]) for r in rows),
            "median_tools": sorted(r["tools"] for r in rows)[n // 2] if n else 0, "rows": rows}


async def _first_pick(a: dict, brain: str, settings) -> dict[str, Any]:
    from ..agent import admit, santosh
    from ..agent.prompts import system_prompt
    plan = admit.plan_for(a["text"], settings)
    fams = frozenset(plan.families) if plan is not None else None
    system = system_prompt(settings.wa_dry_run, "", None, families=fams if settings.prompt_slim else None)
    tools = plan.specs() if plan is not None else santosh.TOOLS
    t0 = time.monotonic()
    try:
        blocks, _stop, used = await santosh._think(brain, system, [{"role": "user", "content": a["text"]}],
                                                   settings, tools, max_tokens=700)
    except Exception as e:
        return {"id": a["id"], "error": str(e)[:200]}
    pick = next((b for b in blocks if b.get("type") == "tool_use"), None)
    out: dict[str, Any] = {"id": a["id"], "brain": used, "ms": int((time.monotonic() - t0) * 1000),
                           "pick": pick["name"] if pick else "", "ok": a["ok"]}
    if pick and pick["name"] == "tool_search" and plan is not None:
        need = str((pick.get("input") or {}).get("need") or "")
        opened = admit.plan_for("", settings)
        opened.admit_families(admit.route(need, settings))
        out["searched"] = need[:120]
        out["found"] = any(t["name"] in a["ok"] for t in opened.specs())
    out["right"] = bool(pick and pick["name"] in a["ok"]) or bool(out.get("found"))
    if not pick:
        out["words"] = " ".join(str(b.get("text") or "") for b in blocks if b.get("type") == "text")[:200]
    return out


async def live_card(asks: list[dict] | None = None, brain: str = "") -> dict[str, Any]:
    from ..agent import llm
    from ..config import get_settings
    st = get_settings()
    brain = brain or llm.choose([])
    rows = [await _first_pick(a, brain, st) for a in asks or ASKS]
    done = [r for r in rows if "error" not in r]
    return {"kind": "live", "set": TOOL_SET_V, "brain": brain, "asks": len(rows), "answered": len(done),
            "right": sum(r["right"] for r in done), "via_search": sum(bool(r.get("found")) for r in done),
            "no_tool": sum(not r["pick"] for r in done), "errors": len(rows) - len(done), "rows": rows}


def save(card: dict, label: str = "") -> dict:
    card = {**card, "label": label, "at": int(time.time())}
    name = f"tools-{card['kind']}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    (_dir() / name).write_text(json.dumps(card, ensure_ascii=False, indent=1))
    card["file"] = name
    return card


def saved() -> list[dict]:
    out = []
    for p in sorted(_dir().glob("tools-*.json"), reverse=True)[:30]:
        try:
            d = json.loads(p.read_text())
            out.append({"file": p.name, "kind": d.get("kind"), "at": d.get("at"), "label": d.get("label"),
                        "asks": d.get("asks"), "right": d.get("right", d.get("right_in_view")), "brain": d.get("brain")})
        except Exception:
            continue
    return out


def lines(card: dict) -> list[str]:
    n = card.get("asks") or 0
    if card.get("kind") == "router":
        out = [f"Tool choice (router, set v{card['set']}): right tool in view {card['right_in_view']}/{n}, "
               f"wrong family loaded {card['wrong_loaded']}/{n}, median {card['median_tools']} tools a turn"]
        out += [f"  - {r['id']}: {'MISSING right tool' if not r['in_view'] else 'wrong ' + ', '.join(r['wrong'])}"
                for r in card["rows"] if not r["in_view"] or r["wrong"]]
        return out
    out = [f"Tool choice (live, {card.get('brain')}, set v{card['set']}): right first pick "
           f"{card['right']}/{card['answered']} (of them via tool_search {card['via_search']}), "
           f"answered in words {card['no_tool']}, errors {card['errors']}"]
    out += [f"  - {r['id']}: picked {r.get('pick') or '(no tool)'}, right = {', '.join(r['ok'])}"
            for r in card["rows"] if "error" not in r and not r["right"]]
    return out
