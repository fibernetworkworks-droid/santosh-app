"""v0.814 APP ENGINE 1 - ONE tool, `app_engine`, for the React apps of the Web Studio (L8 of LOVABLE_STUDIO_PLAN.md).

The plan's tool set (5.3) as actions of one tool: view / search / edit_lines / write / rename / delete /
add_dependency / logs / build, plus create / list / status / tokens / check. Every write goes through
appengine/rules.py (paths, safety, design drift): a refused write changes nothing and names the line and the fix.
Going live is NOT here - it is her tap in the Studio. In Plan / Chat mode only the reading actions run."""
from __future__ import annotations

import asyncio
import json
from typing import Any

from .tools import Ctx, ToolError

READS = {"list", "status", "view", "search", "logs", "files", "check", "cloud", "cloud_rows", "scan", "tests", "branches", "design", "work"}
# v0.999.322 the done check: plan / done change nothing in the app, so they run in every mode
GATE = {"plan", "done"}
# v0.999.322 the changes the done check, her locks and the fingerprints watch
EDITS = {"write", "edit_lines", "rename", "delete", "add_dependency", "tokens", "design_new", "design_import", "render_mode",
         "cloud_change"}
CHANGES = {"create", "write", "edit_lines", "rename", "delete", "add_dependency", "tokens", "build", "cloud_change", "branch_new",
           "design_new", "design_import", "render_mode"}

APPENGINE_TOOLS = [
    {"name": "app_engine", "description": (
        "[APP ENGINE] Real React apps (React 18 + TypeScript + Vite + Tailwind v4) built in Hoola's locked box - for "
        "web APPS with screens, forms, lists, dashboards (a brochure website stays with the `website` tool). Work "
        "like a careful engineer: action=view or search BEFORE you change a file; action=edit_lines for small exact "
        "changes (edits=[{search, replace, first_line?, last_line?}] - the search text must appear exactly once, in "
        "the line range if given; a line that is just '...' inside search skips a long middle; line numbers are the "
        "ORIGINAL file's, so several edits from one view are fine); action=write for a new file or a full rewrite; "
        "rename / delete; add_dependency only from the vetted list; tokens to change colours / corners / fonts "
        "(values {bg, surface, ink, primary, accent, radius, head, body} as #rrggbb / number / sans|serif|rounded|mono, "
        "or palette calm|warm|fresh|bold|night). RULES the tool enforces: colours only as tokens (bg-bg bg-surface "
        "bg-primary text-ink text-muted text-primary border-line ...), never a hex / rgb colour, a Tailwind palette "
        "colour (bg-blue-500, text-white) or a one-off [value]; no outside address (no fetch to http...; data will come "
        "through src/lib/hoola.ts, not connected yet - keep sample data on the page and say it is sample); pages in "
        "src/pages, routes in src/App.tsx, shared parts in src/components (the kit: src/components/ui = the full "
        "shadcn-style set incl. select, date-picker, accordion, sheet, dropdown-menu, carousel, chart; src/components/"
        "blocks = one React block per section type (hero, services-grid, pricing-table, faq, contact-block, "
        "screen-dashboard, screen-table ...) with `variants` and sample defaults - build pages from blocks, passing her "
        "real words as props). DESIGN (v0.999.58): every new app has its OWN design genome (direction, colours from one "
        "brand hue checked for readability in light AND dark, bundled fonts incl. Indian scripts, corners, shadow, "
        "density, motion, imagery) in DESIGN.md + tokens.css; action=design shows it; action=design_new {hue 0-360 or "
        "colour #rrggbb, direction (a style name or her words), mode light|dark, fonts {display, text}, genes {...}} "
        "makes a new one; action=design_import {design_md} brings in her DESIGN.md from any tool - never edit "
        "tokens.css or DESIGN.md by hand. Your changes are built (and shown to her) only when your turn ends or you call "
        "action=build - so finish the whole change set, then call action=build and read its answer before you say it is "
        "done; a failed build names file and line, and action=logs also lists errors the preview itself reported (with "
        "the app's file and line). When she selected a part, her message names its file:line - view that line first. "
        "Going live is HER tap in the Studio - never claim it is live. `app` = the app's id or number (the Studio "
        "turn already names it). HOOLA CLOUD (saved data + sign-in): action=cloud shows its lists, rules in plain words and "
        "the rule audit; action=cloud_change changes=[...] applies changes as ONE run - ops: add_list {key, label, fields: "
        "[{key, label, type: text|long_text|number|phone|email|date|choice|yes_no|url, required, options, admin_only, "
        "private}], rules: {create: public|member|admin, read: public|members|own|admin, update: own|admin, delete: "
        "own|admin}, samples}, add_field {list, ...field}, add_option {list, field, option}, hide_field / show_field "
        "{list, field}, hide_list / show_list {list}, label {list, field?, label}, rules {list, create?, read?, update?, "
        "delete?}, signup {on}. Only ADDITIVE changes: drop / rename / type change / remove_option are never done by you "
        "(they wait for her 'I accept data loss' tap; use hide + add instead). Personal data (email, phone, name, address) "
        "is never readable by anyone on the internet by you: such a change waits as a 'Let anyone read this' card in the "
        "Studio's Cloud tab, and only her tap there opens it. The app uses it ONLY "
        "via src/lib/hoola.ts: hoola.db.collection(\"list\").list() / create / update / remove, hoola.auth.signUp / "
        "signIn / signOut / me / onChange; every rule is checked on the server. action=cloud_rows {list} reads the PREVIEW "
        "(sample) data only - her visitors' live data is never read by you. PROOF BEFORE 'DONE': after you change a rule "
        "the rules are played against the real rule engine and the answer says if they held; after a build of an app "
        "that saves data a real browser walks it at phone and desktop size - read those lines, and never say it is done "
        "while one says FAILED. action=tests plays the rules now; action=scan (what=quick|deep) lists what would block "
        "going live: personal data readable by anyone, secrets in the code, failing rules or browser walk. BRANCHES: "
        "action=branch_new {name} starts a named copy of the app (own preview + own sample data, never live) to try a bigger "
        "change safely - then work in it with app=<the branch id>; action=branches lists them with what accepting would "
        "bring in and any part changed in both. Accepting a branch into the app (or discarding it) is HER tap in the Studio. "
        "PAGES GO OUT PRE-RENDERED (v0.999.64): every page is rendered to finished HTML at build, so put ONE <Seo title "
        "description jsonLd> (from @/lib/seo) on every page, link pages with <Link to> and never touch window / document "
        "while a component renders. render (create, or action=render_mode {render}): 'site' for a website (shop, "
        "clinic, portfolio, wedding, blog, course...) = plain HTML pages that load code only for ISLANDS (a component "
        "file in src/components or src/islands that starts with \"use client\"; - forms, booking, accordions, carts, "
        "filters; plain-data props only) and a page wrapped in <AppPage> runs as the full app (sign-in, live data); "
        "'app' for something people work in (dashboard, portal, tool, game) = the whole app in the browser. The build's "
        "answer lists the pre-rendered pages and any that could not be rendered (fix those). AUTOFIX (v0.999.65): every "
        "write is repaired by code before the rules read it - palette colours / hex / one-off [values] onto the tokens, "
        "transition-all, emoji, alert(), a missing alt, two <h1> or a skipped heading level, a switched-off focus ring - "
        "and the answer says what it fixed (file:line was -> now): write it that way next time. What it cannot fix "
        "(a browser <select> / date box / confirm(), unsafe code, outside imports) is still refused with file:line. "
        "PLAN, CHECK, THEN DONE (v0.999.322): before your first change to an app in this chat, action=plan {goal, steps "
        "(1-6), criteria [{id, description}] (1-8 things she will see working), preview (true for anything with screens)}; "
        "changes without a recorded plan are refused. Every answer then ends with NEXT: the one thing to do. When the "
        "work is built and checked, action=done {outcome: complete, summary, criteria: [the plan's ids]} - it is refused "
        "unless, after your LAST change, a build passed with TypeScript clean, rule tests passed (if a rule changed), the "
        "browser check passed (preview / saved data) and the preview reported no errors; outcome blocked {summary} when "
        "you cannot finish. Never tell her it is done before action=done is accepted. action=work shows where the task "
        "stands. FINGERPRINTS: action=view returns the file's revision; an edit_lines or a rewrite of an existing file must "
        "be made on the file as you last read it in this chat (or pass revision) - if it changed since, the edit is refused "
        "and you view it again. The file must PARSE: a JS / TS file that does not is refused with line and column. HER "
        "LOCKS: a file or folder she locked in the Studio is never changed by you; tell her what you would change there "
        "and ask her to unlock it."),
     "input_schema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": sorted(READS | CHANGES | GATE)},
         "goal": {"type": "string", "description": "plan: what she asked for, in one or two sentences"},
         "steps": {"type": "array", "items": {"type": "string"}, "description": "plan: 1-6 short steps"},
         "criteria": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"},
                      "description": {"type": "string"}}, "required": ["id"]},
                      "description": "plan: 1-8 checks {id, description} she will see working; done: the plan's ids [{id}]"},
         "preview": {"type": "boolean", "description": "plan: true when the result must be seen working in the preview"},
         "outcome": {"type": "string", "enum": ["complete", "blocked"], "description": "done: complete, or blocked when you cannot finish"},
         "summary": {"type": "string", "description": "done: what changed (or what blocks it), in plain words"},
         "revision": {"type": "string", "description": "edit_lines / write: the revision action=view returned (optional; the "
                      "tool remembers the last one you read in this chat)"},
         "app": {"type": "string", "description": "the app id or number (default: the app this Studio chat is about)"},
         "name": {"type": "string", "description": "create: the app's name; branch_new: the branch's name"},
         "brief": {"type": "string", "description": "create: what she asked for, in her words"},
         "palette": {"type": "string", "enum": ["calm", "warm", "fresh", "bold", "night"]},
         "values": {"type": "object", "description": "tokens: {bg, surface, ink, primary, accent: #rrggbb, radius: number, head, body}"},
         "path": {"type": "string", "description": "a file, e.g. src/pages/Home.tsx"},
         "to": {"type": "string", "description": "rename: the new path"},
         "code": {"type": "string", "description": "write: the whole file"},
         "edits": {"type": "array", "items": {"type": "object", "properties": {
             "search": {"type": "string"}, "replace": {"type": "string"},
             "first_line": {"type": "integer"}, "last_line": {"type": "integer"}}, "required": ["search", "replace"]}},
         "from_line": {"type": "integer"}, "to_line": {"type": "integer"},
         "query": {"type": "string", "description": "search: text to find"},
         "package": {"type": "string", "description": "add_dependency: a vetted package name"},
         "changes": {"type": "array", "items": {"type": "object"}, "description": "cloud_change: the Hoola Cloud changes, applied as one run"},
         "list": {"type": "string", "description": "cloud_rows: the list to read (preview data)"},
         "hue": {"type": "number", "description": "design_new: the brand hue 0-360"},
         "colour": {"type": "string", "description": "design_new: her exact brand colour #rrggbb (kept when it reads)"},
         "direction": {"type": "string", "description": "design_new: a style (editorial_calm, bold_modern, warm_local, "
                       "luxury_dark, playful_bright, minimal_swiss, festive_traditional, tech_gradient, organic_natural, "
                       "corporate_trust) or her own words for the feel"},
         "mode": {"type": "string", "enum": ["light", "dark"]},
         "fonts": {"type": "object", "description": "design_new: {display, text} bundled font families"},
         "genes": {"type": "object", "description": "design_new: change single genes of the current design, e.g. "
                   "{\"shape\": {\"radius\": 4}, \"motion\": \"calm\", \"density\": \"airy\"}"},
         "design_md": {"type": "string", "description": "design_import: a whole DESIGN.md (YAML tokens between --- lines + rules)"},
         "render": {"type": "string", "enum": ["site", "app"], "description": "create / render_mode: site = pre-rendered "
                    "pages + islands (websites); app = the whole app in the browser"}},
         "required": ["action"]}},
]

APPENGINE_LABELS = {"app_engine": "Working on the app"}


def _default_app(app: str) -> str:
    if app:
        return str(app)
    from . import turnmode as TM
    a = TM.APP.get()
    if not a:
        raise ToolError("Which app? Give app=<id or number> (action=list shows them).")
    return a


def _gate_on(name: str) -> bool:
    from ..config import get_settings
    return bool(getattr(get_settings(), name, True))


def _call(ctx: Ctx, action: str, app: str, kw: dict[str, Any]) -> dict[str, Any]:
    """v0.999.322 the done check, her locks and the file fingerprints around every action (appengine/donegate.py)."""
    from ..appengine import donegate as DG, herlocks as HL, service as AE
    if action in ("list", "status", "create"):
        return _run(ctx, action, app, kw)
    t, conv = ctx.tenant_id, ctx.conversation_id or ""
    a = _default_app(app)
    r = AE._load(t, a)
    try:
        if action == "plan":
            return DG.record_plan(r, conv, {"goal": kw.get("goal"), "steps": kw.get("steps"), "criteria": kw.get("criteria"),
                                            "preview": kw.get("preview", True)})
        if action == "done":
            return DG.complete(r, conv, kw.get("outcome") or "complete", kw.get("summary") or "", kw.get("criteria") or [])
        if action == "work":
            st = DG.progress(r, conv)
            return {**st, "say": ("No task is open on this app in this chat." if st["status"] == "none" else
                                  f"Task {st.get('status')}" + (f"; NEXT: {st['next']}" if st.get("next") else ""))}
        path = AE.RL.norm(kw.get("path") or "") if kw.get("path") else ""
        if action in EDITS:
            if _gate_on("app_engine_done_gate") and not DG.has_plan(r, conv):
                raise ToolError("Record your plan first: action=plan {goal, steps, criteria: [{id, description}], preview}. "
                                "Nothing was changed.")
            if action in ("write", "edit_lines", "delete", "rename"):
                to = AE.RL.norm(kw.get("to") or "") if action == "rename" and kw.get("to") else ""
                HL.guard(r, path, to)
            if action in ("write", "edit_lines") and path:
                cur = AE.file_revision(r, path)
                if cur:
                    want = str(kw.get("revision") or "") or DG.seen(r, conv, path) or None
                    if want is None and _gate_on("app_engine_read_first"):
                        raise ToolError(f"View {path} first (action=view), so the change is made on what is in the file "
                                        "now. Nothing was written.")
                    kw = {**kw, "_expect": want}
    except (DG.GateError, HL.LockError, AE.RL.RuleError) as e:
        raise ToolError(str(e))
    res = _run(ctx, action, a, kw)
    try:
        _after(r, conv, action, path, kw, res)
    except Exception:                                    # noqa: BLE001 - the record never breaks the tool's answer
        import logging
        logging.getLogger("santosh.appengine").warning("done-check record failed", exc_info=True)
    if action in (READS - {"work"}) | EDITS | {"build"} and isinstance(res, dict):
        nl = DG.next_line(r, conv)
        if nl:
            res = {**res, "say": (str(res.get("say") or "") + " " + nl).strip()}
    return res


def _after(r, conv: str, action: str, path: str, kw: dict[str, Any], res: Any) -> None:
    from ..appengine import donegate as DG, service as AE
    if not isinstance(res, dict):
        return
    if action == "view" and res.get("revision"):
        DG.mark_seen(r, conv, res.get("path") or path, res["revision"])
    if action in ("write", "edit_lines") and res.get("revision"):
        DG.mark_seen(r, conv, res.get("file") or path, res["revision"])
    if action == "rename":
        to = str(res.get("to") or "")
        if to:
            DG.mark_seen(r, conv, to, AE.file_revision(r, to), old=path)
    if action == "delete":
        DG.mark_seen(r, conv, path, "")
    if action in EDITS:
        rules = action == "cloud_change" and any(str((c or {}).get("op")) in ("add_list", "rules")
                                                 for c in (kw.get("changes") or []) if isinstance(c, dict))
        DG.note(r, conv, "edit", file=res.get("file") or res.get("to") or path or action, action=action, rules=rules or None)
        if action == "cloud_change" and isinstance(res.get("rule_tests"), dict):
            DG.note(r, conv, "rules", ok=bool(res["rule_tests"].get("ok")))
    if action == "tests":
        DG.note(r, conv, "rules", ok=bool(res.get("ok")))
    if action == "build":
        rr = AE._load(r.tenant_id, r.id)
        try:
            lb = json.loads(rr.last_build or "{}")
        except ValueError:
            lb = {}
        ok = res.get("built") is not False and bool(lb.get("ok")) and not res.get("queued")
        DG.note(r, conv, "build", ok=ok, types_ok=bool(lb.get("types_ok")), version=int(rr.version or 0))
        bc = res.get("browser_check")
        if isinstance(bc, dict) and ok:
            DG.note(r, conv, "browser", ran=bool(bc.get("ran")), ok=bool(bc.get("ok")), why=str(bc.get("why") or "")[:200] or None)


def _run(ctx: Ctx, action: str, app: str, kw: dict[str, Any]) -> dict[str, Any]:
    from ..appengine import service as AE
    from ..config import get_settings
    if not getattr(get_settings(), "app_engine", True):
        raise ToolError("The App Engine is switched off on this server.")
    t = ctx.tenant_id
    if action == "list":
        return {"apps": AE.list_(t)}
    if action == "status":
        return AE.status()
    if action == "create":
        from . import turnmode as TM
        conv = ctx.conversation_id if TM.APP.get() == "" else ""
        return AE.create(t, kw.get("name") or "", kw.get("brief") or "", kw.get("palette") or "",
                         kw.get("values") or None, conversation_id=conv, render=kw.get("render") or "")
    a = _default_app(app)
    if action == "files":
        r = AE._load(t, a)
        return {"files": AE.files_list(r)}
    if action == "view":
        return AE.read_file(t, a, kw.get("path") or "", kw.get("from_line") or 0, kw.get("to_line") or 0)
    if action == "search":
        return AE.search(t, a, kw.get("query") or "")
    if action == "logs":
        return AE.logs(t, a)
    if action == "check":
        return AE.check_all(AE._load(t, a))
    if action == "write":
        return AE.write(t, a, kw.get("path") or "", kw.get("code") or "", expect=kw.get("_expect"))
    if action == "edit_lines":
        return AE.edit_lines(t, a, kw.get("path") or "", kw.get("edits") or [], expect=kw.get("_expect"))
    if action == "rename":
        return AE.rename(t, a, kw.get("path") or "", kw.get("to") or "")
    if action == "delete":
        return AE.delete(t, a, kw.get("path") or "")
    if action == "add_dependency":
        return AE.add_dependency(t, a, kw.get("package") or "")
    if action == "tokens":
        return AE.set_tokens(t, a, kw.get("values") or {}, kw.get("palette") or "")
    if action == "design":
        return AE.get_design(t, a)
    if action == "design_new":
        return AE.set_design(t, a, hue=kw.get("hue"), direction=kw.get("direction") or "", mode=kw.get("mode") or "",
                             pin=kw.get("colour") or "", fonts=kw.get("fonts") or None, genes=kw.get("genes") or None)
    if action == "design_import":
        if not kw.get("design_md"):
            raise ToolError("design_import needs design_md = the whole DESIGN.md text.")
        return AE.set_design(t, a, design_md=kw["design_md"])
    if action == "render_mode":
        if not kw.get("render"):
            raise ToolError("render_mode needs render = site or app.")
        return AE.set_render(t, a, kw["render"])
    if action in ("branches", "branch_new"):
        from ..appengine import branches as BR
        if action == "branches":
            return BR.listing(t, a)
        return BR.create(t, a, kw.get("name") or "")
    if action == "build":
        res = AE.wait_build(t, a)
        return _prove(t, a, res, ctx.conversation_id or "")
    if action in ("scan", "tests"):
        from ..appengine import saboot as SB
        r = AE._load(t, a)
        if action == "tests":
            rt = SB.rule_tests(r)
            return {**{k: rt[k] for k in ("ok", "count", "failed", "lists")}, "say": SB.say_rule_tests(rt)}
        if not int(r.version or 0):
            raise ToolError("Build the app first; a scan reads a built version.")
        return SB.deep(r, int(r.version)) if str(kw.get("what") or "quick") == "deep" else SB.quick(r, int(r.version))
    if action in ("cloud", "cloud_rows", "cloud_change"):
        from ..appengine import cloud as CL
        r = AE._load(t, a)
        try:
            if action == "cloud":
                o = CL.overview(r)
                return {k: o[k] for k in ("schema", "audit", "pending", "pending_public", "datasets", "not_built")}
            if action == "cloud_rows":
                return {"dataset": "preview", "rows": CL.owner_rows(r, "preview", kw.get("list") or "", 50)}
            changes = kw.get("changes") or []
            changes = [changes] if isinstance(changes, dict) else changes
            # v0.999.12 B7 GATES IN CODE: the model can never say yes for her - confirm_public is dropped here AND refused in
            # apply_changes (from_model); a list with personal data goes public only from her tap in the Cloud tab
            changes = [{k: v for k, v in c.items() if k != "confirm_public"} if isinstance(c, dict) else c for c in changes]
            out = CL.apply_changes(r, changes, "hoola", from_model=True)
            if any(str(c.get("op")) in ("add_list", "rules") for c in changes if isinstance(c, dict)):
                from ..appengine import saboot as SB     # v0.832 a rule changed: play the rules against the real engine before 'done'
                rt = SB.rule_tests(r)
                out["rule_tests"] = {k: rt[k] for k in ("ok", "count", "failed", "lists")}
                out["say"] = (out.get("say") or "") + " " + SB.say_rule_tests(rt) + ("" if rt["ok"] else " Do NOT say this is done.")
            return out
        except CL.CloudError as e:
            if action == "cloud_change" and isinstance(e.data, dict) and e.data.get("destructive"):
                CL.queue_pending(r, e.data["destructive"])
                raise ToolError(str(e) + " The data-loss card is now waiting in the Studio's Cloud tab; tell her what it "
                                "would delete and that it is her choice.")
            if action == "cloud_change" and isinstance(e.data, dict) and e.data.get("flag") == "public_personal":
                CL.queue_public(r, changes, str(e.data.get("list") or ""), list(e.data.get("fields") or []))
                raise ToolError(str(e) + " A card 'Let anyone read this' is now waiting in the Studio's Cloud tab; tell her "
                                "which personal fields anyone could read, and that only her tap there can do it.")
            raise ToolError(str(e))
    raise ToolError(f"Unknown action '{action}'.")



def _prove(t: str, a: str, res: dict, conv: str = "") -> dict:
    """v0.832 SABOOT: after a good build of an app that saves data, the browser walks it before 'done' is said
    (v0.999.322: also when the open task's plan says the preview must be seen working)."""
    from ..appengine import cloud as CL, donegate as DG, saboot as SB, service as AE
    try:
        if res.get("built") is False:
            return res
        r = AE._load(t, a)
        st = DG.progress(r, conv)
        wants = bool(st.get("status") == "working" and (st.get("plan") or {}).get("preview"))
        if not int(r.version or 0) or not (CL.schema(r).get("lists") or wants):
            return res
        b = SB.browser_check(r)
        res = dict(res)
        res["browser_check"] = {k: b.get(k) for k in ("ran", "ok", "problems", "why")}
        res["say"] = (res.get("say") or "") + " " + SB.say_browser(b) + ("" if b.get("ok") or not b.get("ran") else " Fix this before you say it is done.")
    except Exception as e:                                  # noqa: BLE001  a proof that cannot run must not break the build answer
        res = dict(res)
        res["browser_check"] = {"ran": False, "why": str(e)[:200]}
    return res

async def app_engine(ctx: Ctx, action: str, app: str = "", **kw: Any) -> dict:
    from ..appengine import service as AE
    from . import turnmode as TM
    action = str(action or "").strip().lower()
    if action in ("publish", "go_live", "unpublish"):
        raise ToolError("Going live is her tap in the Studio (App > Publish), never this tool. Tell her the version is "
                        "ready and where the button is.")
    if action in CHANGES and action not in GATE and TM.MODE.get() in ("plan", "chat"):
        TM.STATS["refused"] += 1
        raise ToolError(TM.refusal(f"app_engine action={action}"))
    if action in CHANGES and ctx.actor not in ("owner",) and not str(ctx.actor).startswith("approved:"):
        raise ToolError("Only the owner's own turns change an app.")
    tok = AE.TURN_CONV.set(ctx.conversation_id or "")       # v0.825 the HMR gate: this turn's writes wait for its end
    try:
        return await asyncio.to_thread(_call, ctx, action, app, kw)
    except AE.AppEngineError as e:
        raise ToolError(str(e))
    finally:
        AE.TURN_CONV.reset(tok)


APPENGINE_HANDLERS = {"app_engine": app_engine}
