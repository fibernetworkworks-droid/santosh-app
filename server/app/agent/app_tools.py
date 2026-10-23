"""v0.128 App Sahayak tools. `app_banao` designs her native app (every screen, tap-through prototype) before any app is
built; `app_dekho` only reads. Plan, look and 'Design pakka' are HER choices on the cards (the tool can do them only when
the owner herself clearly says so)."""
from __future__ import annotations

import asyncio
from typing import Any

from .tools import Ctx, ToolError

APP_TOOLS = [
    {"name": "app_banao", "description": (
        "Design HER business a premium NATIVE mobile app (Android + iPhone look) and show her EVERY screen as a tap-through "
        "prototype BEFORE anything is built. A few words are enough: the 1 lakh app brief library knows 1,000 kinds of "
        "business x 10 app goals x 10 premium styles. action=new: brief (her words, e.g. 'kirana dukaan ki app, ghar pe "
        "delivery'), name, goal (shop|food_order|booking|learning|membership|service_request|khata|catalogue|events|"
        "community; or a COMPLEX staff / admin app archetype: crm, field_sales, field_service, helpdesk, hrms, field_force, "
        "inventory, pos_retail, distribution, manufacturing_erp, procurement, logistics_tms, delivery_driver, fleet, isp_ops, "
        "telecom_tower, gis_survey, asset_utility, construction_pm, project_mgmt, hospital_his, clinic_emr, lab_lims, school_erp, "
        "coaching_admin, hotel_pms, restaurant_ops, real_estate_crm, society_mgmt, security_guard, facility_mgmt, iot_monitor, "
        "agri_fpo, dairy_collection, ngo_field, audit_inspection, collections, accounts_erp, intranet, events_ops, warehouse_wms, "
        "multi_branch, gym_admin; guessed from her words), style (optional), answers {name, phone, whatsapp, address, hours, upi_id}. Returns the PLAN "
        "card (screens, tabs, main flow, legal screens made by code; complex apps also get the BLUEPRINT: data tables, org levels, "
        "roles + permission matrix, approval chain, login plan, phone features with Play / App Store status - features the stores "
        "don't allow (reading SMS / call log, all files, accessibility, exact alarms) are NEVER promised: say what is used instead) "
        "+ up to 3 questions: ask them in ONE message (or "
        "ask_form). action=answer: app + answers. action=plan_ok: ONLY when she clearly said haan to the plan (+ drop: "
        "screens she doesn't want) -> Home screen in 3 looks (a few minutes; cards update by themselves, don't poll). "
        "action=look: app + index (0-2) she chose (+ colors_from) -> every screen is designed while she watches the board. "
        "action=change: app + instruction (her words: 'cart mein coupon hatao', 'rang halka', 'booking screen add karo', "
        "'tabs mein offers', 'store keeper role add karo', 'region ke neeche zone bhi', 'passkey login bhi', 'vendor table mein "
        "GST number') -> only those screens redesign; roles / levels / login / data / phone-feature changes redraw nothing. action=approve: ONLY when she herself says 'design pakka' "
        "(+ hash from the card) - freezes the design for the real app build. action=android: on an APPROVED design, builds the REAL "
        "native Android app (Kotlin + Jetpack Compose): every screen written from its approved design, compiled on Hoola's build "
        "machine (not this server; a few minutes, compile errors fixed by itself, a screen that won't compile gets a simple "
        "version), signed with the app's own preview key -> an APK card with 'Phone pe install karo' (Android's own Install screen) "
        "+ the project ZIP (opens in Android Studio). redo (screen ids) rewrites only those screens. No build machine set up -> "
        "only the ZIP (say so). Nothing goes to Play Store here. action=stop / resume / delete*. "
        "Never invent prices, phone numbers or reviews ([blank] instead); never card / CVV / UPI PIN / password fields; payments = "
        "UPI to her own UPI ID. iPhone build and store publishing come in later versions. (* owner only)"),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["new", "answer", "plan_ok", "look", "change", "approve", "android", "stop", "resume", "delete"]},
         "app": {"type": "string", "description": "app number (A-0001) or name; empty = the latest"},
         "brief": {"type": "string"}, "name": {"type": "string"}, "goal": {"type": "string"}, "style": {"type": "string"},
         "answers": {"type": "object"}, "index": {"type": "integer"}, "colors_from": {"type": "integer"},
         "instruction": {"type": "string"}, "drop": {"type": "array", "items": {"type": "string"}}, "hash": {"type": "string"},
         "redo": {"type": "array", "items": {"type": "string"}}},
         "required": ["action"]}},
    {"name": "app_dekho", "description": (
        "Read her app designs (nothing changes). what=apps | app (app: board, screens, checks, preview link, versions) | "
        "checks (app) | spec (app: the frozen design contract: tokens, tabs, every screen's purpose / data / actions) | "
        "library (q or industry: business types with their app goal) | brief (field, goal, style: the full ready app brief) | "
        "understand (q: what a short ask means: business type, app goal, 3 looks) | design_system (the menu she can pick from: "
        "navigation types incl. side bar / floating bar / rail / top tabs, FAB types incl. speed dial, cards incl. glass, headers, "
        "buttons, textures, motion, 3D, colour schemes, fonts (q = font search, script = devanagari / tamil / ...)) | archetypes "
        "(the 43 complex app kinds with modules / roles) | capabilities (every Android / iPhone feature with Play + App Store "
        "status and the allowed alternative; q filters) | login (sign-in methods + security rules) | blueprint (app: data tables, "
        "roles matrix, levels, login plan, features, schema files + ER page) | schema (app: the PostgreSQL schema text). To change an "
        "app's structure use app_banao action=change with her words (screens are not redrawn for structure / mode / font). "
        "android (app: the native build: status, screens written / compiled / simple, rounds, APK link + size, ZIP)."),
     "input_schema": {"type": "object", "properties": {
         "what": {"type": "string", "enum": ["apps", "app", "checks", "spec", "library", "brief", "understand", "design_system",
                                             "archetypes", "capabilities", "login", "blueprint", "schema", "android"]},
         "app": {"type": "string"}, "q": {"type": "string"}, "script": {"type": "string"}, "industry": {"type": "string"}, "field": {"type": "string"},
         "goal": {"type": "string"}, "style": {"type": "string"}},
         "required": ["what"]}},
]
APP_LABELS = {"app_banao": "App design bana raha hoon", "app_dekho": "App design dekh raha hoon"}
_OWNER_ONLY = {"delete"}
_TAP_LIKE = {"plan_ok", "look", "approve"}


def _owner(ctx: Ctx) -> bool:
    return ctx.actor == "owner" or str(ctx.actor).startswith("approved:")


def _act(ctx: Ctx, action: str, a: dict[str, Any]) -> dict[str, Any]:
    from ..appmaker import service as S
    t, ref, conv = ctx.tenant_id, str(a.get("app") or ""), ctx.conversation_id or ""
    if action in _OWNER_ONLY and not _owner(ctx):
        raise ToolError("Sirf maalkin yeh kar sakti hain.")
    if action in _TAP_LIKE and not _owner(ctx):
        raise ToolError("Plan / look / design pakka sirf maalkin chunti hain (app ke card par).")
    if action == "new":
        v = S.new(t, str(a.get("brief") or ""), conv, str(a.get("name") or ""), "", str(a.get("goal") or ""),
                  str(a.get("style") or ""), a.get("answers") if isinstance(a.get("answers"), dict) else None)
        return {k: v.get(k) for k in ("id", "number", "name", "status", "field_label", "goal_label", "plan", "questions",
                                      "understood", "say")}
    if action == "answer":
        return S.answer(t, ref, a.get("answers") if isinstance(a.get("answers"), dict) else {})
    if action == "plan_ok":
        v = S.approve_plan(t, ref, conv, a.get("drop") if isinstance(a.get("drop"), list) else None)
        return {"status": v["status"], "say": "Home screen ke 3 looks ban rahe hain; card par aa jayenge (poll mat kariye)."}
    if action == "look":
        cf = a.get("colors_from")
        v = S.choose_look(t, ref, int(a.get("index") or 0), int(cf) if cf is not None else None, conv)
        return {"status": v["status"], "preview": v["preview"],
                "say": "Screens banana shuru. Har screen ban-te hi board aur prototype mein dikhegi."}
    if action == "change":
        return S.change(t, ref, str(a.get("instruction") or ""), conv)
    if action == "approve":
        h = str(a.get("hash") or "") or S.get(t, ref).get("hash", "")
        v = S.approve(t, ref, h)
        return {"status": v["status"], "version": v["version"], "say": v["say"]}
    if action == "android":
        from ..appmaker.android import service as AN
        redo = [str(x) for x in a.get("redo") or []] if isinstance(a.get("redo"), list) else None
        v = AN.build(t, ref, conv, redo)
        return {"status": v["status"], "runner": v["runner"], "say": v["say"] + " Card apne aap badlega (poll mat kariye)."}
    if action == "stop":
        return S.stop(t, ref)
    if action == "resume":
        return S.resume(t, ref)
    if action == "delete":
        return S.delete(t, ref)
    raise ToolError(f"Unknown action {action}")


async def app_banao(ctx: Ctx, action: str, **a) -> Any:
    from ..appmaker import service as S
    try:
        return await asyncio.to_thread(_act, ctx, action, a)
    except (S.AppError, KeyError) as e:
        raise ToolError(str(e) or "Nahi mila")


def _read(ctx: Ctx, what: str, a: dict[str, Any]) -> Any:
    from ..appmaker import library as L
    from ..appmaker import service as S
    t, ref = ctx.tenant_id, str(a.get("app") or "")
    if what == "apps":
        return {"apps": S.apps(t)}
    if what == "app":
        v = S.get(t, ref)
        v.pop("facts", None)
        return v
    if what == "checks":
        return S.get(t, ref).get("checks")
    if what == "spec":
        return S.spec(t, ref)
    if what == "library":
        return L.browse(str(a.get("industry") or ""), str(a.get("q") or ""), 30)
    if what == "brief":
        b = L.brief(str(a.get("field") or ""), str(a.get("goal") or ""), str(a.get("style") or ""))
        return {k: b[k] for k in ("id", "field_label", "goal_label", "style_label", "screens", "tabs", "flow", "code_screens",
                                  "questions", "text")}
    if what == "understand":
        return L.understand(str(a.get("q") or ""))
    if what == "design_system":
        from ..appmaker import colors as CL
        from ..appmaker import designsys as DS
        from ..appmaker import fonts as FN
        from ..appmaker import taxonomy as TX
        lab = lambda d: {k: (x.get("label") if isinstance(x, dict) else x) for k, x in d.items()}     # noqa: E731
        q, script = str(a.get("q") or ""), str(a.get("script") or "")
        return {"counts": L.counts(), "styles": {k: x["label"] for k, x in TX.STYLES.items()}, "nav": lab(DS.NAV), "fab": lab(DS.FAB),
                "cards": lab(DS.CARDS), "headers": lab(DS.HEADERS), "buttons": lab(DS.BUTTONS), "textures": DS.TEXTURES,
                "transitions": sorted({m["web"] for m in DS.MOTION.values() if m["kind"] == "transition"}),
                "three_d": list(DS.THREE_D), "colour_schemes": list(CL.SCHEMES),
                "fonts": [f["family"] for f in FN.families(script=script, q=q)][:40]}
    if what == "archetypes":
        from ..appmaker import taxonomy as TX
        return {"archetypes": [{"id": k, "label": g["label"], "modules": g["modules"], "roles": g["roles"], "screens": len(g["screens"]),
                                "brief": g["brief"]} for k, g in TX.GOALS.items() if g.get("complex")], "counts": L.counts()}
    if what == "capabilities":
        from ..appmaker import capabilities as CP
        q = str(a.get("q") or "").lower()
        rows = [c for c in CP.catalog() if not q or q in (c["label"] + " " + c["hi"] + " " + c["id"]).lower()]
        return {"capabilities": rows[:70], "legend": {"play": CP.PLAY_LABEL, "ios": CP.IOS_LABEL}}
    if what == "login":
        from ..appmaker import auth as AU
        return {"methods": AU.METHODS, "policy": AU.POLICY}
    if what == "blueprint":
        return S.blueprint(t, ref)
    if what == "android":
        from ..appmaker.android import service as AN
        return AN.get(t, ref)
    if what == "schema":
        data, _ct = S.blueprint_file(t, ref, "schema.sql")
        txt = data.decode()
        return {"schema_sql": txt[:12000], "truncated": len(txt) > 12000, "chars": len(txt)}
    raise ToolError(f"Unknown what {what}")


async def app_dekho(ctx: Ctx, what: str, **a) -> Any:
    from ..appmaker import service as S
    try:
        return await asyncio.to_thread(_read, ctx, what, a)
    except (S.AppError, KeyError) as e:
        raise ToolError(str(e) or "Nahi mila")


APP_HANDLERS = {"app_banao": app_banao, "app_dekho": app_dekho}
