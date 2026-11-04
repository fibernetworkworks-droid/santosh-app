"""CLAUDE SKILLS P5 - the SKILLS card: do the imported skills actually REACH the model and get followed?

Same two-card shape as the maps / tool / hard cards (`python -m app.quality skills [--live]`):

- free_card(): no model, no keys. On a tenant holding the 10 starters, the 31 BYOX skills and the Claude pack,
  for every ask: is the right skill in the injected top 2; is `skill_manage` callable on that turn (the same
  admission function the server runs - the v0.393 lesson: a feature that cannot be reached is not shipped); can
  the file the skill points at really be opened; and does an UNRELATED ask leave the pack out. CI can pin it.
- live_card(): one real turn per ask on a dedicated tenant (never her chats). Spies on the store record which skill
  and which file the model really opened and whether it saved a skill; the reply is scored on the skill's own
  markers, and on honesty for the two skills that cannot run code here. Rupees per answer come from the run meter.
  Needs a model key; without one every row is an ERROR, never a pass.

NOT a quality judgement of the writing: a marker proves the skill's guidance reached the reply, not that the reply
is good. The scorer says so in its output.
"""
from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from typing import Any

from .skills_asks import ASKS, PACK, SKILLS_SET_V

log = logging.getLogger("santosh.quality.skills")
CARD_TENANT = "__skillcard__"


def _seed(tenant: str) -> None:
    from ..coder import skill_packs
    skill_packs.seed(tenant)
    skill_packs.seed_byox(tenant)
    skill_packs.seed_claude(tenant)


def _low(s: Any) -> str:
    return str(s or "").lower()


def _score_text(ask: dict, reply: str) -> dict[str, Any]:
    low, misses = _low(reply), []
    marks = [m for m in ask.get("markers", []) if m.lower() in low]
    if len(marks) < int(ask.get("min_markers", 1)):
        misses.append(f"reply shows {len(marks)} of the skill's markers (needs {ask.get('min_markers', 1)})")
    honest = None
    if ask.get("limit_markers"):
        honest = any(m.lower() in low for m in ask["limit_markers"])
        if not honest:
            misses.append("did not admit it cannot run/test this here (honesty ask)")
    return {"markers": marks, "honest": honest, "text_ok": not misses, "misses": misses}


# ---------------------------------------------------------------- the free card
def free_card(asks: list[dict] | None = None, tenant: str = CARD_TENANT) -> dict[str, Any]:
    from ..agent import admit
    from ..config import get_settings
    from ..coder import inject, skills_store
    st = get_settings()
    _seed(tenant)
    have = {s["name"] for s in skills_store.listing(tenant)}
    rows = []
    for a in asks or ASKS:
        top2 = [r["name"] for r in inject._matched(tenant, a["text"])]
        plan = admit.plan_for(a["text"], st)
        admitted = inject.admit_tool(plan, tenant, a["text"]) if plan is not None else False
        names = {t["name"] for t in plan.specs()} if plan is not None else {"skill_manage"}
        row = {"id": a["id"], "kind": a["kind"], "skill": a["skill"], "top2": top2,
               "tool_in_view": "skill_manage" in names}
        if a["kind"] == "pos":
            row["in_top2"] = a["skill"] in top2
            row["files_ok"] = True
            for rel in a.get("reads", []):
                try:
                    skills_store.read_file(tenant, a["skill"], rel)
                except Exception:       # noqa: BLE001
                    row["files_ok"] = False
            row["ok"] = bool(row["in_top2"] and row["tool_in_view"] and row["files_ok"])
        else:
            row["pack_pulled"] = [n for n in top2 if n in PACK]
            row["ok"] = not row["pack_pulled"]
        row["admitted_by_match"] = admitted
        rows.append(row)
    pos = [r for r in rows if r["kind"] == "pos"]
    neg = [r for r in rows if r["kind"] == "neg"]
    return {"kind": "free", "set": SKILLS_SET_V, "asks": len(rows), "skills_on_tenant": len(have),
            "pack_missing": [n for n in PACK if n not in have],
            "pos": len(pos), "in_top2": sum(r["in_top2"] for r in pos),
            "tool_in_view": sum(r["tool_in_view"] for r in pos),
            "files_ok": sum(r["files_ok"] for r in pos), "neg": len(neg),
            "neg_clean": sum(r["ok"] for r in neg),
            "neg_tool_forced": sum(1 for r in neg if r["admitted_by_match"]),
            "ok": sum(r["ok"] for r in rows), "rows": rows}


# ---------------------------------------------------------------- the live card
@contextmanager
def spy():
    """Record what the model really did to the skill store during one turn."""
    from ..coder import skills_store as S
    seen = {"read": [], "files": [], "created": []}
    o_read, o_file, o_create = S.read, S.read_file, S.create

    def read(tenant, name):
        seen["read"].append(name)
        return o_read(tenant, name)

    def read_file(tenant, name, rel):
        seen["files"].append(f"{name}:{rel}")
        return o_file(tenant, name, rel)

    def create(tenant, name, desc, body):
        seen["created"].append(name)
        return o_create(tenant, name, desc, body)

    S.read, S.read_file, S.create = read, read_file, create
    try:
        yield seen
    finally:
        S.read, S.read_file, S.create = o_read, o_file, o_create


async def _one(ask: dict, tenant: str) -> dict[str, Any]:
    from .. import usage
    from ..agent import santosh
    from .hard_card import _Catch, _failed
    from .run import _new_conv
    conv = _new_conv(tenant)
    t0, catch = time.time(), _Catch()
    root = logging.getLogger()
    root.addHandler(catch)
    try:
        with spy() as seen, usage.run_meter() as meter:
            reply = await santosh.run_turn(conv, ask["text"], tenant_id=tenant)
    except Exception as e:      # noqa: BLE001 - one broken ask is a row, not a dead card
        return {"id": ask["id"], "kind": ask["kind"], "error": str(e)[:200], "right": False, "inr": 0.0}
    finally:
        root.removeHandler(catch)
    inr = round(float(meter.get("usd", 0.0)) * usage.usd_inr(), 4)
    if _failed(conv):
        why = [x for x in catch.lines if "error ref" in x or "refused" in x] or catch.lines
        return {"id": ask["id"], "kind": ask["kind"], "right": False, "inr": inr,
                "error": (why[-1] if why else (reply or "turn failed"))[:300], "log": catch.lines[-6:]}
    opened = [n for n in seen["read"] if n in PACK]
    if ask["kind"] == "neg":
        row = {"right": not opened, "misses": [f"opened pack skill {', '.join(opened)} on an unrelated ask"] if opened else []}
    else:
        row = _score_text(ask, reply or "")
        misses = list(row["misses"])
        row["opened"] = ask["skill"] in seen["read"]
        if not row["opened"]:
            misses.append(f"never opened {ask['skill']} (opened: {', '.join(seen['read']) or 'nothing'})")
        want_files = [f"{ask['skill']}:{r}" for r in ask.get("reads", [])]
        row["files_ok"] = all(w in seen["files"] for w in want_files)
        if not row["files_ok"]:
            misses.append("did not open " + ", ".join(w.split(":", 1)[1] for w in want_files if w not in seen["files"]))
        if ask.get("must_not_create") and seen["created"]:
            misses.append("saved a skill before the user said yes: " + ", ".join(seen["created"]))
        row["right"] = not misses
        row["misses"] = misses
    row.update({"id": ask["id"], "kind": ask["kind"], "inr": inr, "read": seen["read"][:6],
                "files": seen["files"][:6], "seconds": round(time.time() - t0, 1), "reply": (reply or "")[:900]})
    return row


async def live_card(asks: list[dict] | None = None, tenant: str = "") -> dict[str, Any]:
    from .run import TENANT
    tenant = tenant or TENANT
    _seed(tenant)
    items = asks or ASKS
    rows: list[dict] = []
    for a in items:
        rows.append(await _one(a, tenant))
        if len(rows) >= 3 and all("error" in r for r in rows):
            break                     # three dead turns: print the cause, do not waste the rest
    done = [r for r in rows if "error" not in r]
    pos = [r for r in done if r["kind"] == "pos"]
    neg = [r for r in done if r["kind"] == "neg"]
    return {"kind": "live", "set": SKILLS_SET_V, "asks": len(rows), "planned": len(items), "answered": len(done),
            "right": sum(r["right"] for r in done),
            "opened": sum(bool(r.get("opened")) for r in pos), "pos": len(pos),
            "files_ok": sum(bool(r.get("files_ok")) for r in pos),
            "honest": sum(1 for r in pos if r.get("honest")), "honest_asks": sum(1 for r in pos if r.get("honest") is not None),
            "neg_clean": sum(r["right"] for r in neg), "neg": len(neg),
            "errors": len(rows) - len(done), "inr": round(sum(r.get("inr", 0.0) for r in rows), 4),
            "inr_per_answer": round(sum(r.get("inr", 0.0) for r in done) / len(done), 4) if done else None,
            "rows": rows}


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
    name = f"skillscard-{card['kind']}-{time.strftime('%Y%m%d-%H%M%S')}.json"
    (_dir() / name).write_text(json.dumps(card, ensure_ascii=False, indent=1))
    card["file"] = name
    return card


def lines(card: dict) -> list[str]:
    if card.get("kind") == "free":
        out = [f"Skills card (free, set v{card['set']}): right skill in the injected top 2 {card['in_top2']}/{card['pos']}, "
               f"skill_manage callable {card['tool_in_view']}/{card['pos']}, files open {card['files_ok']}/{card['pos']}, "
               f"unrelated asks leave the pack out {card['neg_clean']}/{card['neg']}, "
               f"skill_manage admitted on unrelated asks {card['neg_tool_forced']} (only because a starter skill matched), skills on tenant {card['skills_on_tenant']}"]
        if card["pack_missing"]:
            out.append("  PACK MISSING: " + ", ".join(card["pack_missing"]))
        for r in card["rows"]:
            if not r["ok"]:
                why = (f"top 2 was {r['top2']}" if r["kind"] == "pos" and not r.get("in_top2")
                       else "skill_manage not callable" if r["kind"] == "pos" and not r["tool_in_view"]
                       else "file did not open" if r["kind"] == "pos" else f"pulled {r['pack_pulled']}")
                out.append(f"  - {r['id']}: {why}")
        out.append("  (free card = reachability only; whether a model follows the skill needs --live)")
        return out
    out = [f"Skills card (live, set v{card['set']}): RIGHT {card['right']}/{card['answered']} "
           f"(opened the skill {card['opened']}/{card['pos']}, opened the file it needed {card['files_ok']}/{card['pos']}, "
           f"honest about limits {card['honest']}/{card['honest_asks']}, unrelated asks clean {card['neg_clean']}/{card['neg']}), "
           f"errors {card['errors']}, spent Rs {card['inr']}"
           + (f", Rs {card['inr_per_answer']} an answer" if card.get("inr_per_answer") is not None else "")]
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
    out.append("  (markers prove the skill's guidance reached the reply, not that the writing is good)")
    return out
