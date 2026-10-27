"""v0.132: the approved design -> the generator's spec (tokens, screens, icons, fonts, the app's starting data)."""
from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any

from .. import kit as K
from .. import taxonomy as T

log = logging.getLogger("santosh.appmaker.android")

# ---------------------------------------------------------------- icons: the design's SVG line icons as path strings
_ATTR = re.compile(r'(\w+)="([^"]*)"')


def _f(v: float) -> str:
    return ("%.2f" % v).rstrip("0").rstrip(".")


def svg_to_paths(body: str) -> list[str]:
    out: list[str] = []
    for tag, attrs in re.findall(r"<(path|circle|rect)\b([^>]*)/?>", body):
        a = {k: v for k, v in _ATTR.findall(attrs)}
        try:
            if tag == "path":
                out.append(a["d"])
            elif tag == "circle":
                cx, cy, r = float(a["cx"]), float(a["cy"]), float(a["r"])
                out.append(f"M{_f(cx - r)} {_f(cy)}a{_f(r)} {_f(r)} 0 1 0 {_f(2 * r)} 0a{_f(r)} {_f(r)} 0 1 0 {_f(-2 * r)} 0z")
            else:
                x, y, w, h = float(a["x"]), float(a["y"]), float(a["width"]), float(a["height"])
                rx = min(float(a.get("rx") or 0), w / 2, h / 2)
                if rx <= 0:
                    out.append(f"M{_f(x)} {_f(y)}h{_f(w)}v{_f(h)}h{_f(-w)}z")
                else:
                    out.append(f"M{_f(x + rx)} {_f(y)}h{_f(w - 2 * rx)}a{_f(rx)} {_f(rx)} 0 0 1 {_f(rx)} {_f(rx)}"
                               f"v{_f(h - 2 * rx)}a{_f(rx)} {_f(rx)} 0 0 1 {_f(-rx)} {_f(rx)}h{_f(-(w - 2 * rx))}"
                               f"a{_f(rx)} {_f(rx)} 0 0 1 {_f(-rx)} {_f(-rx)}v{_f(-(h - 2 * rx))}a{_f(rx)} {_f(rx)} 0 0 1 {_f(rx)} {_f(-rx)}z")
        except (KeyError, ValueError):
            continue
    return out


def icon_paths() -> dict[str, list[str]]:
    return {name: svg_to_paths(body) for name, body in K.ICONS.items()}


# ---------------------------------------------------------------- colours / fonts
def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def mix(a: str, b: str, t: float) -> str:
    """t of colour a over colour b."""
    try:
        ra, rb = _rgb(a), _rgb(b)
    except (ValueError, IndexError):
        return b
    return "#" + "".join(f"{round(x * t + y * (1 - t)):02X}" for x, y in zip(ra, rb))


def with_tints(tk: dict[str, Any]) -> dict[str, Any]:
    out = dict(tk)
    bg = out.get("bg") or "#FFFFFF"
    out.setdefault("tint", mix(out.get("primary") or "#3355FF", bg, 0.12))
    out.setdefault("tint_2", mix(out.get("accent") or "#FF8800", bg, 0.14))
    if isinstance(out.get("alt"), dict) and out["alt"]:
        a = dict(out["alt"])
        abg = a.get("bg") or "#111111"
        a.setdefault("tint", mix(a.get("primary") or out.get("primary") or "#3355FF", abg, 0.18))
        a.setdefault("tint_2", mix(a.get("accent") or out.get("accent") or "#FF8800", abg, 0.18))
        a.setdefault("on_primary", out.get("on_primary"))
        a.setdefault("on_accent", out.get("on_accent"))
        out["alt"] = a
    return out


def fonts_ttf(tk: dict[str, Any], out_dir: Path) -> dict[str, dict[str, str]]:
    """Head + body latin faces as TTF (Android res/font takes ttf / otf only). Missing glyphs (Devanagari ...) fall back to
    the phone's own Noto fonts. No fontTools / brotli -> the phone's default font (said in the build notes)."""
    out: dict[str, dict[str, str]] = {}
    try:
        from fontTools.ttLib import TTFont
    except Exception:
        return out
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        files = K.font_files(tk, "en")
    except Exception:
        log.debug("font files", exc_info=True)
        return out
    for slot, fam in (("head", tk.get("head")), ("body", tk.get("body"))):
        for f_fam, sub, w, path in files:
            if f_fam != fam or sub != "latin" or w not in (400, 700):
                continue
            dst = out_dir / f"{slot}_{w}.ttf"
            try:
                if not dst.exists():
                    p = Path(path)
                    if p.suffix.lower() in (".ttf", ".otf"):
                        dst.write_bytes(p.read_bytes())
                    else:
                        ft = TTFont(str(p))
                        ft.flavor = None
                        ft.save(str(dst))
                out.setdefault(slot, {})[str(w)] = str(dst)
            except Exception:
                log.info("font %s %s not converted", fam, w, exc_info=True)
    return out


# ---------------------------------------------------------------- the app's starting data (her facts + sample records)
DEMO = {
    "products": [("Classic pack", 120, "Best seller"), ("Family size", 249, "Value"), ("Fresh special", 89, "New"),
                 ("Combo offer", 399, "Combo"), ("Mini pack", 49, "Everyday"), ("Premium box", 599, "Gift")],
    "services": [("Consultation", 300, "30 min"), ("Full service", 999, "90 min"), ("Quick check", 149, "15 min"),
                 ("Home visit", 499, "60 min")],
    "courses": [("Foundation batch", 2500, "Mon-Fri 5 pm"), ("Weekend batch", 1800, "Sat-Sun 10 am"), ("Test series", 900, "Online")],
    "plans": [("Monthly", 999, "1 month"), ("Quarterly", 2599, "3 months"), ("Yearly", 8999, "12 months")],
    "events": [("Opening day", 0, "Sat 6 pm"), ("Workshop", 499, "Sun 11 am"), ("Festive meet", 199, "Next Friday")],
    "orders": [("Order #1042", 468, "Delivered"), ("Order #1043", 249, "On the way"), ("Order #1044", 120, "Packed")],
    "bookings": [("Consultation", 300, "Tomorrow 11:00"), ("Quick check", 149, "Fri 4:30 pm")],
    "posts": [("Welcome to our community", 0, "Today"), ("This week's update", 0, "Yesterday")],
    "entries": [("Groceries on credit", 640, "12 Oct"), ("Payment received", -500, "15 Oct")],
}
GOAL_LISTS = {"shop": ["products", "orders"], "food_order": ["products", "orders"], "booking": ["services", "bookings"],
              "learning": ["courses"], "membership": ["plans"], "service_request": ["services", "orders"],
              "khata": ["entries", "products"], "catalogue": ["products"], "events": ["events"], "community": ["posts", "events"]}
SECRET_FIELD = re.compile(r"(?i)(password|pin|otp|cvv|card|aadhaar|pan|account_no|ifsc|salary|token|secret)")


def _demo_record(ent: str, fields: list[dict[str, Any]], i: int) -> dict[str, Any]:
    rec: dict[str, Any] = {"id": f"{ent}-{i + 1}"}
    for f in fields:
        n, t = f["name"], f["type"]
        if SECRET_FIELD.search(n) or t in ("pii", "ref", "file", "json"):
            continue
        if t in ("text", "long"):
            rec[n] = f"{n.replace('_', ' ').capitalize()} {i + 1}"
        elif t == "enum":
            opts = f.get("values") or ["open"]
            rec[n] = opts[i % len(opts)]
        elif t in ("money", "decimal"):
            rec[n] = round(250 + 137.5 * i, 2)
        elif t == "int":
            rec[n] = 3 + i * 2
        elif t in ("date", "datetime", "time"):
            rec[n] = f"2026-11-{(i % 27) + 1:02d}" + (" 10:30" if t == "datetime" else "")
        elif t == "bool":
            rec[n] = i % 2 == 0
        elif t == "phone":
            rec[n] = f"98{i:02d}0 0{i:04d}"[:11]
        elif t == "email":
            rec[n] = f"person{i + 1}@example.com"
        elif t == "point":
            rec[n] = {"lat": 18.52 + i * 0.01, "lng": 73.85 + i * 0.012}
    rec.setdefault("name", rec.get("title") or rec.get("code") or f"{ent.replace('_', ' ').capitalize()} {i + 1}")
    return rec


def privacy_paras(name: str, goal: str, f: dict[str, Any]) -> list[str]:
    kept = K.DATA_KEPT.get(goal) or K.DATA_KEPT["shop"]
    contact = f.get("grievance_email") or f.get("email") or f.get("phone") or ""
    return [f"This app is run by {name or 'the business'}. This policy says what we collect, why, and your choices.",
            "# What we collect", "; ".join(kept) + ".",
            "# Why", "Only to provide the service you ask for (orders, bookings, reminders, bills) and to answer you. We do "
            "not sell or rent your details and we do not show ads from other companies.",
            "# Who else sees it", "Nobody, except service providers that help us run the app (hosting, messages) under "
            "contract, and authorities when the law requires. Payments are made in your own UPI app; we never see your card or UPI PIN.",
            "# How long", "While your account is active; bills are kept as tax law requires. Delete your account any time from Profile.",
            "# Your rights", "See, correct or delete your details and withdraw consent (Digital Personal Data Protection Act, "
            "2023). If we do not resolve a complaint you may approach the Data Protection Board of India.",
            "# Contact", contact or "-"]


PUBLIC_FACTS = ("name", "tagline", "about", "phone", "whatsapp", "email", "address", "hours", "upi_id", "instagram", "website",
                "legal_name", "gstin", "grievance_officer", "grievance_phone", "grievance_email", "owner")


def public_facts(facts: dict[str, Any], name: str) -> dict[str, Any]:
    f = {k: str(facts[k])[:400] for k in PUBLIC_FACTS if facts.get(k)}
    regs = facts.get("registrations") or {}
    if regs.get("gstin") and not f.get("gstin"):
        f["gstin"] = str(regs["gstin"])[:20]
    f["name"] = name or f.get("name") or "App"
    if f.get("grievance_officer"):
        f["grievance_name"] = f["grievance_officer"]
    return f


def seed(name: str, goal: str, facts: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    """{facts, lists, demo_lists}: her real public facts and products; everything else is clearly-marked sample data."""
    f = public_facts(facts, name)
    f["privacy"] = privacy_paras(name, goal, facts)
    lists: dict[str, list[dict[str, Any]]] = {}
    demo: list[str] = []
    prods = [p for p in (facts.get("products") or []) if isinstance(p, dict) and p.get("name")]
    goods = [p for p in prods if (p.get("kind") or "goods") != "service"]
    servs = [p for p in prods if (p.get("kind") or "goods") == "service"]
    if goods:
        lists["products"] = [{"id": f"p{i + 1}", "name": p["name"], "price": p.get("price") or 0, "unit": p.get("unit") or "",
                              "category": p.get("category") or ""} for i, p in enumerate(goods[:60])]
    if servs:
        lists["services"] = [{"id": f"s{i + 1}", "name": p["name"], "price": p.get("price") or 0, "unit": p.get("unit") or ""}
                             for i, p in enumerate(servs[:60])]
    for ln in GOAL_LISTS.get(goal, []):
        if ln not in lists:
            lists[ln] = [{"id": f"{ln[:2]}{i + 1}", "name": n, "price": p, "desc": d, "status": d if ln in ("orders",) else "",
                          "when": d if ln in ("bookings", "events", "posts", "entries") else "", "category": d if ln == "products" else ""}
                         for i, (n, p, d) in enumerate(DEMO[ln])]
            demo.append(ln)
    bp = plan.get("blueprint") or {}
    if bp.get("complex"):
        from .. import datamodel as D
        mods = bp.get("modules") or []
        ents = [e for e in D.entities_for(mods) if e in D.ENTITIES and D.ENTITIES[e][0] != "core"]
        sens = set((bp.get("data") or {}).get("sensitive") or [])
        for e in ents[:30]:
            if e in sens or e in lists:
                continue
            fields = D.parse_fields(D.ENTITIES[e][2])
            lists[e] = [_demo_record(e, fields, i) for i in range(6)]
            demo.append(e)
    return {"facts": f, "lists": lists, "demo_lists": demo}


def list_fields(sd: dict[str, Any]) -> dict[str, list[str]]:
    """For the model: which lists exist and the keys their records carry."""
    out = {}
    for n, rows in (sd.get("lists") or {}).items():
        keys: list[str] = []
        for r in rows[:3]:
            keys += [k for k in r if k not in keys]
        out[n] = keys[:14]
    return out


# ---------------------------------------------------------------- the whole spec
def app_id_for(project_id: str) -> str:
    return "in.hoola.preview.a" + hashlib.sha256(project_id.encode()).hexdigest()[:12]


def screens_of(plan: dict[str, Any], screens: dict[str, dict[str, Any]], sd: dict[str, Any]) -> list[dict[str, Any]]:
    labels = plan.get("labels") or {}
    names = set((sd.get("lists") or {}).keys())
    out = []
    for sid in plan.get("screens", []):
        s = screens.get(sid) or {}
        sp = s.get("spec") or {}
        gos = sorted(set(re.findall(r'data-go=["\']([\w-]+)["\']', s.get("html") or "")))
        known = set(plan.get("screens", []))
        acts = [a for a in (sp.get("actions") or []) if a.get("go") in known]
        for g in gos:
            if g in known and g != sid and not any(a.get("go") == g for a in acts):
                acts.append({"label": labels.get(g) or (T.SCREENS.get(g) or {}).get("label") or g, "go": g})
        words = " ".join([sid] + [str(x) for x in sp.get("data") or []]).lower()
        lists = [n for n in names if n.rstrip("s") in words or n in words]
        out.append({"id": sid, "label": labels.get(sid) or (T.SCREENS.get(sid) or {}).get("label") or sid,
                    "icon": K.TAB_ICON.get(sid) or K.GO_ICON.get(sid) or "", "purpose": sp.get("purpose") or "",
                    "lists": lists[:3], "actions": acts[:8], "tab": sid in plan.get("tabs", []),
                    "data": sp.get("data") or [], "components": sp.get("components") or []})
    return out


def fab_of(tk: dict[str, Any], goal: str, plan: dict[str, Any], labels: dict[str, str]) -> dict[str, Any]:
    kind = tk.get("fab") or "none"
    target, ic = K.PRIMARY.get(goal, ("", "plus"))
    known = set(plan.get("screens", []))
    if kind == "none":
        return {}
    if target not in known:
        target = next((s for s in plan.get("flow", []) if s in known and s not in plan.get("tabs", [])), "")
        if not target:
            return {}
    lab = labels.get(target) or (T.SCREENS.get(target) or {}).get("label") or target
    acts = []
    if kind in ("speed_dial", "menu"):
        cand = [s for s in plan.get("flow", []) + plan.get("screens", []) if s in known and s not in plan.get("tabs", [])]
        acts = [{"label": labels.get(a) or (T.SCREENS.get(a) or {}).get("label") or a, "icon": K.GO_ICON.get(a, "dot"), "go": a}
                for a in list(dict.fromkeys([target] + cand))[:3]]
    return {"label": lab, "icon": ic, "go": target, "actions": acts}


def build(project: Any, plan: dict[str, Any], tokens: dict[str, Any], facts: dict[str, Any], screens: dict[str, dict[str, Any]],
          work: Path, version_code: int, base_url: str, app_key: str) -> dict[str, Any]:
    tk = with_tints(tokens)
    sd = seed(project.name, project.goal, facts, plan)
    labels = plan.get("labels") or {}
    scr = screens_of(plan, screens, sd)
    start = plan.get("start") or ("home" if "home" in plan.get("screens", []) else (plan.get("tabs") or plan.get("screens") or [""])[0])
    return {"app": {"name": project.name or facts.get("name") or "App", "app_id": app_id_for(project.id),
                    "version_code": version_code, "version_name": f"{project.version}.{version_code % 100}",
                    "language": project.language or "en", "base_url": base_url, "app_key": app_key},
            "tokens": tk, "structure": {k: tk.get(k) for k in ("nav", "fab", "card", "button", "header", "transition")},
            "tabs": plan.get("tabs", []), "start": start, "flow": plan.get("flow", []),
            "code_screens": [c for c in plan.get("code_screens", []) if c != "splash"] + (["splash"] if "splash" in plan.get("code_screens", []) else []),
            "screens": scr, "fab": fab_of(tk, project.goal, plan, labels), "icons": icon_paths(),
            "app_icon": (K.PRIMARY.get(project.goal) or ("", "store"))[1] if project.goal in K.PRIMARY else "store",
            "fonts": fonts_ttf(tk, work / "fonts"), "seed": sd}
