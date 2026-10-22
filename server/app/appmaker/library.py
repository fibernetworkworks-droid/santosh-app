"""v0.128 The app prompt library: the website library's 1,000 business types x 10 app goals x 10 app design styles =
1,00,000 ready app briefs (screens with one of 306 screen designs each, tabs, main flow, palette, fonts, motion, the
questions that matter and the store / India rules for that trade).

A few words ("kirana ki app", "क्लिनिक का ऐप", "gym app membership wala") are matched with the website library's matcher
(Hinglish / Devanagari / misspellings / meaning); the app goal is guessed from her words, else the trade's default.

Learning: approved designs add counts (style chosen, screens kept / removed, questions that mattered) per business type;
the counts reorder the next owner's suggestions. Counts only, never anyone's words."""
from __future__ import annotations

import hashlib
import logging
import re
import threading
from typing import Any

from ..site import library as SL
from ..site import taxonomy as ST
from . import colors as CL
from . import designsys as DS
from . import fonts as FN
from . import taxonomy as T

log = logging.getLogger("santosh.app")
_LOCK = threading.Lock()
APP_WORDS = {"app", "apps", "application", "mobile app", "android", "iphone", "ios", "ऐप", "एप", "अ‍ॅप", "एप्लिकेशन"}


def _norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^\wऀ-ॿ\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def counts() -> dict[str, int]:
    f = SL.fields()
    return {"fields": len(f), "industries": len(ST.INDUSTRIES), "goals": len(T.GOALS), "styles": len(T.STYLES),
            "briefs": len(f) * len(T.GOALS) * len(T.STYLES), "screen_types": len(T.SCREENS) + len(T.CODE_SCREENS),
            "screen_designs": sum(len(s["variants"]) for s in T.SCREENS.values()), "motion_presets": len(T.MOTION),
            "palettes": len(CL.palettes()), "font_pairs": len(FN.pairs()), "font_families": len(FN.catalog()),
            **{f"ds_{k}": v for k, v in DS.counts().items()}}


def _clean_text(text: str) -> str:
    """Drop the 'app' words so the website matcher looks only at the business words."""
    t = " " + _norm(text) + " "
    for w in sorted(APP_WORDS, key=len, reverse=True):
        t = t.replace(f" {w} ", " ")
    return t.strip()


def guess_goal(text: str, default: str = "") -> str:
    t = " " + _norm(text) + " "
    best, score = "", 0
    for gid, g in T.GOALS.items():
        s = sum(1 for w in g["words"] if f" {_norm(w)} " in t)
        if s > score:
            best, score = gid, s
    return best or default


def default_goal(field: str) -> str:
    f = SL.fields().get(field)
    if not f:
        return "shop"
    ind = T.INDUSTRY.get(f["industry"]) or {"goal": "shop"}
    own = T.SITE_GOAL_TO_APP.get(f["goal"])
    site_default = ST.INDUSTRIES[f["industry"]]["goal"]
    # a field card that differs from its industry (cake studio = enquiry inside food shops) keeps its own leaning
    if own and f["goal"] != site_default:
        return own
    return ind["goal"]


def understand(text: str) -> dict[str, Any]:
    """Her short ask -> {field, goal, styles (3 looks), alternatives, ask}."""
    words = _clean_text(text)
    m = SL.match(words or text)
    if not m:
        return {"field": "", "goal": guess_goal(text, "shop"), "styles": ["clean_commerce", "soft_pastel", "bold_blocks"],
                "alternatives": [], "ask": "App kis kaam / dukaan ke liye hai? (jaise: kirana, clinic, coaching, gym)"}
    best = m[0]
    f = SL.fields()[best["id"]]
    goal = guess_goal(text, default_goal(best["id"]))
    ask = ""
    if len(m) > 1 and m[1]["score"] >= best["score"] * 0.92 and m[1]["industry"] != best["industry"]:
        ask = f"{best['en']} ya {m[1]['en']}?"
    return {"field": best["id"], "field_label": f["en"], "industry": f["industry"], "goal": goal,
            "styles": styles_for(best["id"]), "score": best["score"], "alternatives": m[1:4], "ask": ask}


# ---------------------------------------------------------------- learning (counts only)
def _stats(field: str) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {"style": {}, "screen": {}, "drop": {}, "question": {}, "goal": {}}
    try:
        from sqlalchemy import select
        from ..db import session
        from .models import AppLibStat
        with session() as s:
            for r in s.scalars(select(AppLibStat).where(AppLibStat.field == field)).all():
                out.setdefault(r.kind, {})[r.key] = r.count
    except Exception:
        log.debug("app lib stats unavailable", exc_info=True)
    return out


def learn(field: str, kind: str, keys: list[str], weight: int = 1) -> None:
    """kind = style | screen | drop | question | goal. Counts only."""
    if not field or kind not in ("style", "screen", "drop", "question", "goal"):
        return
    from sqlalchemy import select
    from ..db import session
    from .models import AppLibStat
    with _LOCK, session() as s:
        for k in {str(x)[:60] for x in keys if x}:
            r = s.scalars(select(AppLibStat).where(AppLibStat.field == field, AppLibStat.kind == kind,
                                                   AppLibStat.key == k)).first()
            if r is None:
                s.add(AppLibStat(field=field, kind=kind, key=k, count=weight))
            else:
                r.count = (r.count or 0) + weight


def styles_for(field: str) -> list[str]:
    f = SL.fields().get(field)
    base = list((T.INDUSTRY.get(f["industry"]) or {}).get("styles") or []) if f else []
    base = base or ["clean_commerce", "soft_pastel", "bold_blocks"]
    learned = _stats(field).get("style", {}) if f else {}
    for st in sorted(learned, key=lambda k: -learned[k]):
        if st in T.STYLES and st not in base[:1]:
            base = [base[0], st] + [x for x in base[1:] if x != st]
            break
    out: list[str] = []
    for s in base + list(T.STYLES):
        if s not in out:
            out.append(s)
        if len(out) == 3:
            break
    return out


# ---------------------------------------------------------------- the 1,00,000 briefs
def _pick(seed: str, items: list[Any]) -> Any:
    return items[int(hashlib.sha1(seed.encode()).hexdigest()[:8], 16) % len(items)]


def palettes_for(style_moods: list[str], trade_moods: list[str], n: int = 3, seed: str = "") -> list[str]:
    """The style's moods count double (a luxury look stays dark even for a sweet shop), the trade's moods break ties."""
    a, b = set(style_moods), set(trade_moods)
    P = CL.palettes()
    ranked = sorted(P, key=lambda p: (-(2 * len(a & set(P[p]["moods"])) + len(b & set(P[p]["moods"]))),
                                                hashlib.sha1((seed + p).encode()).hexdigest()))
    return ranked[:n]


def brief_id(field: str, goal: str, style: str) -> str:
    return f"{field}.{goal}.{style}"


def screen_text(sid: str) -> str:
    if sid in T.SCREENS:
        return T.SCREENS[sid]["label"]
    return T.CODE_SCREENS.get(sid, {}).get("label", sid)


def brief(field: str, goal: str = "", style: str = "") -> dict[str, Any]:
    F = SL.fields()
    if field not in F:
        raise KeyError(field)
    f = F[field]
    ind = ST.INDUSTRIES[f["industry"]]
    goal = goal if goal in T.GOALS else default_goal(field)
    style = style if style in T.STYLES else styles_for(field)[0]
    g, st = T.GOALS[goal], T.STYLES[style]
    seed = brief_id(field, goal, style)
    learned = _stats(field)
    screens = list(g["screens"])
    drops = learned.get("drop", {})
    keeps = learned.get("screen", {})
    # a screen most owners of this trade removed is left out (never a tab or a flow step)
    screens = [s for s in screens if not (drops.get(s, 0) >= 3 and drops.get(s, 0) > keeps.get(s, 0)
                                          and s not in g["tabs"] and s not in g["flow"])]
    designs = {s: _pick(seed + s, T.SCREENS[s]["variants"]) for s in screens}
    pal = palettes_for(st["moods"], ind["moods"], 3, seed)
    fonts = FN.pairs()[st["fonts"]]
    legal = list(f["legal"])
    rules = [T.STORE_RULES[x] for x in legal if x in T.STORE_RULES] + list(T.GENERAL_RULES)
    questions = list(ind["questions"])
    lq = learned.get("question", {})
    if lq:
        questions.sort(key=lambda q: -lq.get(q, 0))
    code = T.code_screens_for(goal)
    text = "\n".join([
        f"APP BRIEF {seed}",
        f"Business type: {f['en']} ({f['hi']}); industry: {ind['label']}. People also call it: {', '.join(f['aliases'][:6])}.",
        f"App goal: {g['label']} - {g['brief']}",
        f"Design style: {st['label']} - do: {st['do']}; don't: {st['dont']}; corner radius {st['radius']}px; cards: "
        f"{st['card']} ({DS.CARDS[st['card']]}); buttons: {st['button']}; header: {st['header']} ({DS.HEADERS[st['header']]}); "
        f"navigation: {DS.NAV[st['nav']]['label']} ({DS.NAV[st['nav']]['desc']}); FAB: {DS.FAB[st['fab']]['label']}; "
        f"screen transition: {st['transition']}; texture: {st['texture'] or 'none'}.",
        f"Fonts: headings {fonts['head']}, body {fonts['body']}, Devanagari {fonts['deva']}.",
        f"Palette candidates: {', '.join(pal)}.",
        "Motion: " + "; ".join(f"{m} ({T.MOTION[m]})" for m in st["motion"]),
        "Bottom tabs: " + ", ".join(screen_text(s) for s in g["tabs"]),
        "Main flow: " + " -> ".join(screen_text(s) for s in g["flow"]),
        "Screens: " + "; ".join(f"{T.SCREENS[s]['label']}: {designs[s]}" for s in screens),
        "Made by code (don't design): " + ", ".join(T.CODE_SCREENS[s]["label"] for s in code),
        f"Trust signals to use (only the ones she confirms): {', '.join(ind['trust'])}.",
        "Rules: " + " ".join(rules),
    ])
    return {"id": seed, "field": field, "field_label": f["en"], "field_hi": f["hi"], "industry": f["industry"],
            "industry_label": ind["label"], "goal": goal, "goal_label": g["label"], "style": style, "style_label": st["label"],
            "screens": screens, "designs": designs, "tabs": list(g["tabs"]), "flow": list(g["flow"]), "code_screens": code,
            "palettes": pal, "fonts": st["fonts"], "font_names": fonts,
            "structure": {k: st[k] for k in ("nav", "fab", "card", "button", "header", "transition", "texture")}, "motion": list(st["motion"]), "radius": st["radius"],
            "nav": st["nav"], "trust": ind["trust"], "questions": questions[:5], "legal": legal, "rules": rules,
            "accounts": g["accounts"], "money": g["money"], "text": text}


def browse(industry: str = "", q: str = "", limit: int = 60, offset: int = 0) -> dict[str, Any]:
    F = SL.fields()
    ids = [m["id"] for m in SL.match(_clean_text(q) or q, top=limit)] if q else \
        [fid for fid, f in F.items() if not industry or f["industry"] == industry]
    total = len(ids)
    ids = ids[offset:offset + limit]
    inds = [{"id": k, "label": v["label"], "fields": sum(1 for f in F.values() if f["industry"] == k)}
            for k, v in ST.INDUSTRIES.items()]
    return {"industries": inds, "total": total,
            "fields": [{"id": fid, "en": F[fid]["en"], "hi": F[fid]["hi"], "industry": F[fid]["industry"],
                        "goal": default_goal(fid), "goal_label": T.GOALS[default_goal(fid)]["label"],
                        "styles": styles_for(fid)} for fid in ids],
            "goals": [{"id": k, "label": v["label"], "screens": len(v["screens"])} for k, v in T.GOALS.items()],
            "styles": [{"id": k, "label": v["label"]} for k, v in T.STYLES.items()], "counts": counts()}
